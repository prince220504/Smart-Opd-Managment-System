# Step 7 — `CustomUser` Model with Role Field

## What we did here

1. Set `AUTH_USER_MODEL = 'accounts.CustomUser'` in `backend/config/settings.py` — **before** any migration ran.
2. Wrote the `CustomUser` model in `backend/apps/accounts/models.py` by subclassing `AbstractUser` and adding three fields:
   - `email` — overridden to be **required and unique** (for password reset)
   - `phone` — 10-digit Indian mobile, validated by regex
   - `role` — one of `DOCTOR`, `RECEPTION`, `LAB`, `PATIENT`
3. Added a `phone_with_code` property that prepends `+91` for SMS APIs.
4. Verified with `python manage.py check` (no issues).
5. Made two Conventional Commits on `feature/accounts-app`.

After this, Django **knows** what our user looks like, but no database table exists yet. That's Step 8 (migrations).

---

## Half 1 — Why a custom user from day 1

Django ships with a built-in `User` model. It has `username`, `email`, `password`, `first_name`, `last_name`, `is_staff`, `is_active`, `date_joined`, `last_login`. Good defaults — until your project needs **anything extra** (in our case, a `role`).

### The trap Django warns you about

> "Highly recommended to set up a custom user model, **even if the default User model is sufficient for you**." — Django docs

Why so emphatic? Because swapping the user model later is a one-way door:

| When you swap | Cost |
|---------------|------|
| Before first migration | Free — Django just uses your model |
| After first migration | Drop the entire database, lose all data, start over |

There's no "rename table" shortcut. Django's foreign keys to `auth_user` get baked in at first migration time.

**The rule:** if there's even a 1% chance you'll need to add a field to the user model later, set up a custom user **now**. Cost is zero. Cost of not doing it = catastrophic.

---

## Half 2 — `AbstractUser` vs `AbstractBaseUser`

Two ways to make a custom user. Pick correctly the first time.

| Base class | Gives you | Use when |
|------------|-----------|---------|
| **`AbstractUser`** ✅ | All of Django's default user fields (username, email, password, names, flags) + auth methods | You want Django's user + extras |
| `AbstractBaseUser` | Only password handling. You design every other field. | You're redesigning auth (e.g., login with phone instead of username) |

We're keeping username-based login and just adding fields → `AbstractUser`.

> **Heuristic:** 95% of Django projects should use `AbstractUser`. Reach for `AbstractBaseUser` only when you literally cannot have a `username` field.

---

## Half 3 — `AUTH_USER_MODEL` — the one setting that locks it in

```python
# backend/config/settings.py (at the bottom)
AUTH_USER_MODEL = 'accounts.CustomUser'
```

Format: `'<app_label>.<ModelName>'`

- **`accounts`** = the app label. Django auto-derives this from the last segment of `apps.py → name`. Even though `name = 'apps.accounts'`, the app label is just `accounts`.
- **`CustomUser`** = the model class name.

### Why this **must** come before the model exists

Django reads `AUTH_USER_MODEL` once at startup. Every other built-in app (admin, auth itself, contenttypes) sets up its foreign keys to the user table using whatever this setting points at. If you migrate before setting it, Django creates `auth_user`. Switching `AUTH_USER_MODEL` afterwards leaves dangling foreign keys → unrecoverable without a destructive reset.

> **Mnemonic:** *Settings before model. Model before migration. Migration before any other app.*

---

## Half 4 — The model, line by line

```python
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        DOCTOR = 'DOCTOR', 'Doctor'
        RECEPTION = 'RECEPTION', 'Receptionist'
        LAB = 'LAB', 'Lab Technician'
        PATIENT = 'PATIENT', 'Patient'

    phone_validator = RegexValidator(
        regex=r'^[6-9]\d{9}$',
        message='Enter a valid 10-digit Indian mobile number (must start with 6, 7, 8, or 9).',
    )

    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=10,
        validators=[phone_validator],
        blank=True,
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PATIENT,
    )

    @property
    def phone_with_code(self):
        return f"+91{self.phone}" if self.phone else ''

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
```

### `class Role(models.TextChoices)` — modern enum syntax

```python
DOCTOR = 'DOCTOR', 'Doctor'
```

Format: `KEY = 'db_value', 'Human-readable label'`

- `'DOCTOR'` → goes in the DB column
- `'Doctor'` → shown in admin dropdowns, forms, `get_role_display()`

`TextChoices` (added in Django 3.0) replaces the old tuple-of-tuples style. Cleaner, IDE-autocomplete-friendly, and gives you `Role.DOCTOR`, `Role.choices`, `Role.values`, `Role.labels` for free.

### `email = models.EmailField(unique=True)` — overriding the default

`AbstractUser` already has an `email` field — but it's **optional** and **non-unique**. We override it because:

- Password reset looks up users by email. Two users with the same email = ambiguous lookup = broken reset.
- OTP via email needs a guaranteed reachable address.

By redefining `email` in our subclass, our version wins.

### `phone` — Indian mobile validation

```python
phone_validator = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message='...',
)
```

A **validator** is a small rule Django runs against the value before saving. Bad input → clean error message before the DB sees it.

Regex breakdown:

| Part | Meaning |
|------|---------|
| `^` | Start of string |
| `[6-9]` | First char is 6, 7, 8, or 9 (TRAI rule for Indian mobile) |
| `\d{9}` | Exactly 9 more digits |
| `$` | End of string |

Stores only the 10 digits (e.g., `9876543210`). The `+91` is added at SMS-send time via the property.

### Why store 10 digits, not `+919876543210`?

| Approach | Pros | Cons |
|----------|------|------|
| Store 10 digits (our choice) | What user types = what's saved. No cleaning. Compact. | If we go international, need a `country_code` column |
| Store full E.164 | Future-proof for multi-country | Every save needs prefix logic; validation is harder |

For an India-only app, 10 digits is the right call. Adding a `country_code` column later (if we ever expand) is a 5-minute migration.

### `phone = models.CharField(...)` — not `IntegerField`!

**Always store phone numbers as strings.** Reasons:
- Leading zeros (`0987654321`) get dropped by integers
- Country codes have `+`
- Spaces, dashes, parentheses in user input
- You never do math on a phone number — it's a label, not a quantity

### `@property` — a computed attribute

```python
@property
def phone_with_code(self):
    return f"+91{self.phone}" if self.phone else ''
```

`@property` lets a method be called like an attribute:

```python
user.phone           # → "9876543210" (what's in DB)
user.phone_with_code # → "+919876543210" (no parentheses — looks like a field)
```

When we integrate Twilio/MSG91 later, we just use `user.phone_with_code`. The country code logic lives in **one place** — change it once if rules ever shift.

### `def __str__(self)` — how users appear in admin

```python
def __str__(self):
    return f"{self.username} ({self.get_role_display()})"
```

Admin lists, shell printouts, debug logs — anywhere a `CustomUser` is converted to string, this method runs. `get_role_display()` is **auto-generated** by Django for any field with `choices=` — returns the human label (`'Doctor'`), not the DB value (`'DOCTOR'`).

Example: `johndoe (Doctor)` instead of the default `<CustomUser object (1)>`.

---

## Half 5 — Verify and commit

```bash
cd backend
python manage.py check
# Expected: System check identified no issues (0 silenced).
```

`check` introspects all models and validates:
- Field types are valid
- `AUTH_USER_MODEL` resolves to an actual class
- Choices are well-formed
- No duplicate field names

If `AUTH_USER_MODEL` were misspelled, this is where you'd catch it.

### Two commits, two logical changes

```bash
# Commit 1: the setting (the permission slip)
git add backend/config/settings.py
git commit -m "feat(accounts): set AUTH_USER_MODEL to accounts.CustomUser"

# Commit 2: the model (the blueprint)
git add backend/apps/accounts/models.py
git commit -m "feat(accounts): add CustomUser model with role, email, phone fields"

git push
```

Each commit answers one question:
- "What did you change in settings?" → wired up the custom user pointer
- "What did you change in models?" → defined the actual user

Bundling them would muddy the history.

---

## Gotchas

- **Running `migrate` before setting `AUTH_USER_MODEL`** — kills the project. The default `auth_user` table gets created and switching later requires a DB reset. Rule: **settings first, model second, migration third.**
- **Forgetting `unique=True` on email** — password reset breaks because lookup returns multiple users. Always make email unique on custom users.
- **Storing phone as `IntegerField`** — drops leading zeros, can't store `+`, breaks international expansion. Always `CharField`.
- **Putting `+91` in the database column** — wastes space, makes display logic inconsistent. Keep it as a constant in the property (or in form templates).
- **Defining a field that already exists in `AbstractUser` without intent** — e.g., redefining `username` differently. Either override deliberately (like our `email`) or let `AbstractUser`'s version stand.
- **Mismatch between `AUTH_USER_MODEL` and `apps.py`'s `name`** — `AUTH_USER_MODEL = 'accounts.CustomUser'` uses the app label (auto-derived to `accounts`), not the dotted import path `apps.accounts`. Easy to confuse.

---

## Where each future feature plugs in

| Feature | When | How it uses our fields |
|---------|------|----------------------|
| Login (username + password) | Step 12 | Django's built-in `LoginView` — works out of the box |
| Registration form | Step 12 | Renders `username`, `email`, `phone` (`+91` static prefix), `role` (dropdown) |
| Forgot password → email link | Step 12 | Django's `PasswordResetView` — works because `email` is unique + required |
| OTP via email | Step 12 / 15 | Generates 6-digit code, emails using `user.email` |
| OTP via SMS | Step 15 | Twilio/MSG91 SMS to `user.phone_with_code` |
| Role-based redirects after login | Step 12 | `if user.role == 'DOCTOR': redirect('/doctor/dashboard')` |
| Role-based DRF permissions | Step 14 | Custom permission class checks `request.user.role == 'DOCTOR'` |

All of this works because today we built the right shape for the user.

---

## Revise (3-line summary)

1. **Custom user from day 1, always.** Subclass `AbstractUser`, set `AUTH_USER_MODEL = 'accounts.CustomUser'` in settings **before** the first migration — switching after migration requires destroying the database.
2. Our `CustomUser` adds three fields: `email` (overridden to `unique=True` for password reset), `phone` (`CharField(max_length=10)` with regex validator for Indian mobile), and `role` (`TextChoices` enum for the 4 hospital roles). The `+91` prefix lives in a `@property` (`phone_with_code`), not in the DB.
3. `models.TextChoices` is the modern way to declare choices; `@property` exposes computed values as attributes; `RegexValidator` enforces input format before DB save; `get_role_display()` is auto-generated by Django for any field with `choices=`.

---

**Next:** [Step 8 — Migrations (`makemigrations` vs `migrate`)](08-migrations.md) — **stays on `feature/accounts-app` branch**. We'll generate the migration file from `CustomUser` and apply it to create the actual database table.
