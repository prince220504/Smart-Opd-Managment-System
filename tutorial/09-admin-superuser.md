# Step 9 — Django Admin + Superuser

## What we did here

1. Registered `CustomUser` in `backend/apps/accounts/admin.py` using `UserAdmin` from `django.contrib.auth.admin`.
2. Extended `fieldsets` (edit form) and `add_fieldsets` (create form) so the admin exposes our extra `role` and `phone` fields.
3. Set `list_display`, `list_filter`, `search_fields` so the user list page is useful, not just a wall of usernames.
4. Created the first superuser with `python manage.py createsuperuser` — email is now **required** (because `unique=True`).
5. Logged into `/admin/`, confirmed the `Users` section, the new "Hospital info" fieldset, and the role column on the list page.
6. Discovered that DB timestamps are stored in **UTC** but the admin renders them in **IST** — and that's correct, not a bug.

After this, the accounts module is **feature-complete** — model, migration, admin, superuser. Ready for the first Pull Request.

---

## Half 1 — Why we need an admin (and why Django ships one)

Every Django project gets a free admin interface at `/admin/`. It's a CRUD UI auto-generated from your models — list pages, edit forms, filters, search. For internal tools, it's often "good enough" to skip building a custom dashboard entirely.

We use it here for three reasons:

| Reason | What we get |
|--------|-------------|
| **Bootstrap users** | The very first user has to exist *before* any login form does. The admin is how we make that user. |
| **Internal CRUD** | Receptionist staff will manage doctors/patients via the admin in early phases — no custom UI needed yet. |
| **Debugging window** | Any model registered here gets a free inspector. Saves writing throwaway shell scripts. |

In production, only `is_staff=True` users can log in here. The admin is a privileged tool, not a public page.

---

## Half 2 — Superuser: solving the chicken-and-egg

**The bootstrap problem:** to log in, you need a user. To make a user via the UI, you need to log in. Deadlock.

Django solves it with `createsuperuser` — a CLI command that creates a user directly via the ORM, bypassing all UI:

```bash
python manage.py createsuperuser
# Username: prince
# Email: prince@example.com    ← REQUIRED (we made it unique)
# Phone (optional): 9876543210
# Password: ********
# Password (again): ********
```

That user is born with three flags set:

```python
is_active   = True   # account enabled
is_staff    = True   # can log into /admin/
is_superuser = True  # bypasses ALL permission checks
```

`is_superuser=True` is the magic flag — it means "skip every `has_permission()` check and just say yes." Once you have one superuser, you can use the admin to create everyone else with finer-grained roles.

### Bootstrap rules

- **Local dev** — run `createsuperuser` after the first `migrate`. Credentials only live in your gitignored `db.sqlite3`.
- **Production (Render, Step 18)** — SSH into the Render shell and run `createsuperuser` once, OR use `DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD` env vars + `createsuperuser --noinput`.
- **Never commit `db.sqlite3`** — it contains hashed passwords. We gitignored it back in Step 5.5.
- **Always pick a strong password** even in dev. Habit forms.

---

## Half 3 — `is_superuser` vs our `role` field — two independent concepts

This trips people up. We have **two** systems of "who can do what" running in parallel:

| System | Owned by | Field on user | Purpose |
|--------|---------|---------------|--------|
| **Django auth** | Framework | `is_active`, `is_staff`, `is_superuser` | Can this user log in at all? Can they reach the admin? Should permission checks be skipped? |
| **OPD business roles** | Us | `role` (DOCTOR / RECEPTION / LAB / PATIENT) | Which dashboard do they see? Can they write a prescription? Upload a lab result? |

They are **orthogonal**. A user can be:

- `role=DOCTOR` + `is_staff=False` → Dr. Mehta. Logs in at `/login/`, sees doctor dashboard. Cannot reach `/admin/`.
- `role=RECEPTION` + `is_staff=True` → Front-desk admin. Logs in at `/login/`, can also poke around `/admin/`.
- `role=PATIENT` + `is_superuser=True` → you, the dev. Patient role for testing patient flows; superuser flag for emergency admin access.

**Rule:** `role` answers "what feature area do you live in?" `is_superuser` answers "do permission checks apply to you?" Don't conflate them. In Step 14 (DRF permissions), our custom `IsDoctor` / `IsLabTech` checks will look at `request.user.role`. The framework's `request.user.has_perm(...)` checks will look at the auth flags.

---

## Half 4 — `UserAdmin` — and why we don't reach for `ModelAdmin`

Django's admin is built on `ModelAdmin` — a class you subclass for any model to declare list pages, forms, filters. For the User model specifically, the framework ships a specialized subclass: `UserAdmin` (in `django.contrib.auth.admin`).

```python
from django.contrib.auth.admin import UserAdmin  # NOT django.contrib.admin.ModelAdmin
```

`UserAdmin` extends `ModelAdmin` with three things you don't want to rewrite:

1. **The password-hashing form.** A plain `ModelAdmin` would render the password field as a normal text input — type a password, save it, and the *plaintext* gets stored in the DB. `UserAdmin` swaps in `ReadOnlyPasswordHashField` + a "change password" link that calls `set_password()` (which hashes via PBKDF2/argon2).
2. **Pre-configured fieldsets.** Auth info, personal info, permissions, important dates — already grouped sensibly.
3. **A separate "Add user" form** (the `add_fieldsets`). Creating a user needs different fields than editing one — you need to set the password initially via two-field confirm, then on edit you change it via the change-password link. `UserAdmin` already handles this two-form pattern.

**Rule:** any model that subclasses `AbstractUser` should register with `UserAdmin`, not `ModelAdmin`. Otherwise passwords leak in plaintext or break entirely.

---

## Half 5 — The admin file, line by line

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'phone', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone')

    fieldsets = UserAdmin.fieldsets + (
        ('Hospital info', {'fields': ('role', 'phone')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Hospital info', {'fields': ('role', 'phone')}),
    )
```

### `@admin.register(CustomUser)` — the decorator shortcut

Equivalent to:

```python
class CustomUserAdmin(UserAdmin):
    ...

admin.site.register(CustomUser, CustomUserAdmin)
```

Both register the model + admin class with the global admin site. The decorator is just less typing and keeps the binding visible at the top of the class.

### `list_display` — columns on the change-list page

```python
list_display = ('username', 'email', 'role', 'phone', 'is_staff')
```

Each entry is either a model field or a method on the admin class. This is what you see at `/admin/accounts/customuser/` — one column per tuple entry, one row per user.

Default `UserAdmin` shows `('username', 'email', 'first_name', 'last_name', 'is_staff')` — we replaced it because for a hospital, `role` and `phone` are more useful at a glance than first/last names.

### `list_filter` — the right-hand sidebar

```python
list_filter = ('role', 'is_staff', 'is_active')
```

Generates a sidebar with filter dropdowns. Click "Doctor" under role → list shrinks to just doctors. Click "Yes" under is_active → only enabled accounts. Backed by simple `WHERE` clauses — fast.

### `search_fields` — the top search bar

```python
search_fields = ('username', 'email', 'phone')
```

Adds a search box. Behind the scenes it builds `WHERE username ILIKE %term% OR email ILIKE %term% OR phone ILIKE %term%`. Don't list every field — too many breaks query performance. Pick the ones a user would actually search by.

### `fieldsets` — the edit form layout

```python
fieldsets = UserAdmin.fieldsets + (
    ('Hospital info', {'fields': ('role', 'phone')}),
)
```

`fieldsets` is a tuple of (section_title, options_dict) pairs. Django renders each section as a collapsible group on the edit form.

`UserAdmin.fieldsets` already contains:
1. `(None, {'fields': ('username', 'password')})` — auth
2. `(_('Personal info'), {'fields': ('first_name', 'last_name', 'email')})` — name + email
3. `(_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')})` — flags
4. `(_('Important dates'), {'fields': ('last_login', 'date_joined')})` — timestamps

By writing `UserAdmin.fieldsets + (...)` we **append** a fifth section ("Hospital info") without losing any of the originals. Tuple concatenation, immutable, safe.

**Why not just override fieldsets entirely?** Then we'd lose the auth/permissions/dates sections — a footgun, because removing the password field from `fieldsets` doesn't remove password handling, just hides it. Appending is the pattern.

### `add_fieldsets` — the create form layout

```python
add_fieldsets = UserAdmin.add_fieldsets + (
    ('Hospital info', {'fields': ('role', 'phone')}),
)
```

Same structure, but used only on the "Add user" form. `UserAdmin.add_fieldsets` is minimal — just `(None, {'fields': ('username', 'password1', 'password2')})` — because creating a user only needs the basics. Everything else gets filled in later via edit.

We append "Hospital info" here too so when a receptionist creates a doctor account, they can set role + phone immediately rather than create-then-edit.

---

## Half 6 — The UTC-vs-IST timestamp "bug" that wasn't

When we inspected `db.sqlite3` after the first login, `last_login` showed `17:49:24` while the wall clock said `23:26 IST`. Looked like a bug. It wasn't.

### What Django does

```python
# settings.py
TIME_ZONE = 'Asia/Kolkata'   # for DISPLAY
USE_TZ = True                # store in UTC
```

- **DB stores UTC always.** Every `DateTimeField` is saved as UTC.
- **Display converts to `TIME_ZONE`.** Admin, templates, forms — all auto-convert to Asia/Kolkata.

IST is UTC + 5:30. So `17:49 UTC + 5:30 = 23:19 IST` ≈ the wall clock. The numbers match.

### Verifying it works

In the admin, the "Important dates" section on a user shows `last_login` in **IST**, not UTC. That's the framework converting on render. Same for any template that displays a `DateTimeField`. The DB number is for storage; users never see it directly.

### Why UTC-in-DB is the industry standard

| Risk | UTC-in-DB | Local-time-in-DB |
|------|-----------|------------------|
| Daylight Saving spring/fall | Immune — UTC has no DST | Times jump by an hour twice a year, sometimes ambiguous |
| Server moves to another region | Data unchanged | Have to re-interpret every timestamp |
| Comparing timestamps across regions | `WHERE created_at > '2026-06-01'` just works | Each row needs timezone tagging |
| `EXTRACT(hour FROM ts)` for analytics | Universal | Region-dependent |

India doesn't observe DST, so for an India-only app the DST argument is weaker — but the other three apply, and consistency with global best-practice means any library or third-party tool (Celery, Sentry, log aggregators) "just works."

**Rule:** never set `USE_TZ=False`. Never change `TIME_ZONE` to UTC just because the DB shows UTC. The current setup is correct — change either and you'll break the Celery 24-hour appointment reminder in Step 16.

---

## Half 7 — Verifying everything

```bash
cd backend
python manage.py createsuperuser
# follow prompts — email required, phone optional

python manage.py runserver
# open http://127.0.0.1:8000/admin/
# log in with the credentials you just set
```

**Checklist:**

- ✅ Login page renders, accepts username + password.
- ✅ Home admin page shows an `ACCOUNTS` section with `Custom users` link.
- ✅ Change-list page has `Username | Email | Role | Phone | Staff` columns.
- ✅ Right sidebar has filters for `By role`, `By staff status`, `By active`.
- ✅ Search bar accepts text — try typing your username substring.
- ✅ Open your own user → edit form shows 5 sections including "Hospital info" with role + phone.
- ✅ "Important dates" section shows `last_login` and `date_joined` in IST.
- ✅ "Add user" button → form has 3 sections including "Hospital info".

If any of those fail, the likely cause is `UserAdmin` not being subclassed correctly or `fieldsets` being overridden instead of appended.

---

## Half 8 — The commit

```bash
git add backend/apps/accounts/admin.py
git commit -m "feat(accounts): register CustomUser in admin with role+phone fieldsets"
git push
```

Note: `db.sqlite3` (which now contains your superuser) is **gitignored from Step 5.5** — `git status` won't show it. Credentials never reach the remote.

---

## Gotchas

- **Subclassing `ModelAdmin` instead of `UserAdmin`** — passwords end up unhashed or the change-password form breaks. Always `UserAdmin` for any `AbstractUser` subclass.
- **Replacing `fieldsets` instead of appending** — silently removes the password / permissions / dates sections, breaking the admin in subtle ways. Use `UserAdmin.fieldsets + (...)`.
- **Forgetting `add_fieldsets`** — the "Add user" form won't show role/phone, so creating a user via admin will leave them blank. Both `fieldsets` and `add_fieldsets` need the append.
- **Committing `db.sqlite3`** — leaks hashed passwords + all PII. Stay gitignored.
- **Changing `TIME_ZONE` to UTC** to "fix" the DB timestamp display — breaks Celery scheduling, breaks template rendering, breaks user expectation everywhere. Trust the convert-on-display architecture.
- **`createsuperuser --noinput` in dev** — fails because email is required. Either pass `DJANGO_SUPERUSER_*` env vars or just run the interactive command.
- **Conflating `role` and `is_superuser`** — `role` is for UI routing and business permissions. `is_superuser` is the Django auth nuclear option. Use both for different reasons.

---

## Where each future feature plugs in

| Feature | When | How it uses admin/auth |
|---------|------|-------------------------|
| Login / Register forms | Step 12 | Use Django's `LoginView` + custom register; pre-existing superuser already there |
| Role-based redirects | Step 12 | After login, branch on `user.role` to send to /doctor/, /reception/, /lab/, /patient/ |
| Receptionist creates doctors | Step 13+ | Either custom form OR temporarily via /admin/ — that's the bootstrap pattern |
| DRF custom permissions | Step 14 | `IsDoctor`, `IsLabTech` etc. read `request.user.role` |
| Celery scheduled jobs | Step 16 | `USE_TZ=True` is REQUIRED for `apply_async(eta=...)` to schedule correctly across time zones |
| Render deploy | Step 18 | Run `createsuperuser` on the Render shell once, OR pass env vars + `--noinput` |

---

## Revise (3-line summary)

1. **Admin = free CRUD + login surface.** Register `CustomUser` with `UserAdmin` (not `ModelAdmin`) so password hashing + change-password flow + two-form (add vs edit) pattern come for free. `createsuperuser` solves the bootstrap chicken-and-egg.
2. **`fieldsets` controls the edit form, `add_fieldsets` controls the create form.** Always **append** with `UserAdmin.fieldsets + (...)` — never replace — so the auth/permissions/dates sections stay intact.
3. **`role` (ours) and `is_superuser` (Django's) are orthogonal.** `role` decides which dashboard a user sees and which features they can use; `is_superuser` decides whether Django skips permission checks. Keep them separate forever. And: `USE_TZ=True` stores DB times in UTC and displays them in `TIME_ZONE` (Asia/Kolkata). The DB number minus 5:30 = IST. Don't touch the setting.

---

**Next:** [Step 10 — URLs and views](10-urls-and-views.md) — starts a **new branch** `feature/auth-views` after we merge `feature/accounts-app` to `main` via the first Pull Request.
