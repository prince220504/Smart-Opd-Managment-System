# Step 13a — `appointments` App + `Appointment` Model

> **Sub-step of Step 13.** Step 13 is BIG (multiple files, multiple concepts, multi-feature). Per the chunking rule in `CLAUDE.md`, it's split into `13a → 13d`. This file covers **only 13a**: the app scaffold, the `Appointment` model with two `ForeignKey`s to `CustomUser`, the admin registration, and the migration. Views, URLs, forms, templates, role-based redirect land in 13b–13d.

## What we did here

1. Created a fresh branch `feature/appointments-app` off `main` (PR #2 already merged, so `main` was up-to-date with all of Step 12).
2. Scaffolded the app — `python manage.py startapp appointments` inside `backend/apps/`, then patched `apps.py` so Django can find it on the dotted import path.
3. Registered `'apps.appointments'` in `INSTALLED_APPS` (`backend/config/settings.py`).
4. Wrote the `Appointment` model — two `ForeignKey`s into `CustomUser` (one for the patient, one for the doctor), date + time, a status enum (`PENDING`/`CONFIRMED`/`CANCELLED`), free-text notes, and a `created_at` audit timestamp.
5. Registered `Appointment` in the Django admin with `list_display`, `list_filter`, `search_fields`, `autocomplete_fields`, and `date_hierarchy`.
6. Generated `0001_initial.py` with `makemigrations appointments` and applied it with `migrate`.
7. Made **three atomic Conventional Commits** on `feature/appointments-app`.

After this sub-step, the database has an `appointments_appointment` table, the admin lists/searches/filters appointments, and we have a clean foundation to bolt views + forms + templates onto in 13b–13d.

---

## Half 1 — Why a separate `appointments` app

Django's golden rule for app boundaries: **one app = one bounded responsibility**. The `accounts` app owns identity (who can log in, what role they hold). Appointments are a separate concern — booking, status, scheduling. Mixing them would mean every change to scheduling rules touches the auth code and vice versa.

| Symptom | Cause | Cure |
|---------|-------|------|
| Models file grows past ~300 lines | Two unrelated concepts in one app | Split apps |
| Hard to delete a feature cleanly | Cross-app imports tangled | Apps too chatty |
| Admin file lists 12 unrelated models | One app doing too much | Split apps |

Hospital domain → roughly one app per "thing the receptionist can click in the menu": `accounts`, `appointments`, `lab`, `prescriptions`, `notifications`. Each will be 2–5 models, not 20.

> **Heuristic:** if you can describe the app's job in one short sentence, the boundary is right. "Stores appointments and their status." ✅

---

## Half 2 — Scaffolding the app the same way as `accounts`

```bash
cd backend/apps
python ../manage.py startapp appointments
cd ../..
```

That gives us `backend/apps/appointments/` with the standard skeleton: `__init__.py`, `admin.py`, `apps.py`, `migrations/`, `models.py`, `tests.py`, `views.py`.

### The one critical patch in `apps.py`

Django's `startapp` writes `name = 'appointments'`. That works only when the app lives at the repo top level. Ours lives under `backend/apps/`, so the dotted import path is `apps.appointments`. Fix it:

```python
# backend/apps/appointments/apps.py
from django.apps import AppConfig


class AppointmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.appointments'
```

Both fields matter:

| Line | What it does | What happens if you skip it |
|------|-------------|----------------------------|
| `default_auto_field = 'django.db.models.BigAutoField'` | Tells Django the auto-generated primary key column is a 64-bit integer (`BIGINT`), not 32-bit | Migration warns — and on a high-volume table you'd run out of 2.1B row IDs eventually |
| `name = 'apps.appointments'` | The Python import path Django uses to find the app | `ModuleNotFoundError: No module named 'appointments'` at startup |

> **Mnemonic:** *Dotted import path on the app, app label in `INSTALLED_APPS`.* Django auto-derives the app label (`appointments`) from the last segment of `name` — same trick `accounts` uses.

### Register in `INSTALLED_APPS`

```python
# backend/config/settings.py
INSTALLED_APPS = [
    # ...django built-ins...
    'apps.accounts',
    'apps.appointments',   # ← new
]
```

Then verify:

```bash
python manage.py check
# Expected: System check identified no issues (0 silenced).
```

If `check` is clean, Django has imported `apps.appointments`, called `AppointmentsConfig.ready()`, and is ready to see models inside `models.py`.

---

## Half 3 — Three new concepts for this sub-step

These three drive almost every Django model file from now on. Learn them once.

### Concept 1: `ForeignKey` — the one-to-many link

```python
patient = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='patient_appointments',
)
```

A `ForeignKey` is a column on **this** table that holds the primary key of a row in **another** table. Physically: the DB stores an integer column called `patient_id` that points at `accounts_customuser.id`. Logically: every `Appointment` instance has a `.patient` attribute that gives you back the full `CustomUser` object — Django runs the JOIN for you.

| Direction | Code | What you get |
|-----------|------|-------------|
| Appointment → User | `appointment.patient` | A single `CustomUser` |
| User → Appointments | `user.patient_appointments.all()` | A `QuerySet` of all that patient's appointments |

The first argument is the **target model**. We pass `settings.AUTH_USER_MODEL` (the string `'accounts.CustomUser'`) instead of importing `CustomUser` directly. Three reasons:

1. Avoids circular imports during Django's startup ordering.
2. If `AUTH_USER_MODEL` ever changes (it won't, but the docs are emphatic), every FK auto-updates.
3. Django convention — every Django book and tutorial uses this exact pattern. Don't fight it.

> **Why it matters:** every "Joe has many appointments" relationship in the system is a `ForeignKey`. Patient ↔ appointments, doctor ↔ appointments, doctor ↔ prescriptions, lab tech ↔ lab results — all the same shape.

### Concept 2: `on_delete` — what happens when the parent row dies

When you delete a `CustomUser`, the database needs a rule for what to do with the rows pointing at them. SQL leaves the rule up to you; Django forces you to spell it out at the field level. Five common options:

| Option | Effect | When to use |
|--------|--------|-------------|
| `CASCADE` | Delete the children too | Child has no meaning without parent. **Used for `patient`** — if a patient's account is deleted, their appointments become noise. |
| `PROTECT` | Refuse to delete the parent — raise `ProtectedError` | Parent deletion would lose business-critical data. **Used for `doctor`** — even if a doctor leaves, the prescription/lab-result trail must survive. |
| `SET_NULL` | Keep the child, set FK to `NULL`. Field must allow `null=True` | Parent is optional context — e.g., "created by" on logs. |
| `SET_DEFAULT` | Keep the child, set FK to a default sentinel value. Field needs `default=...` | Same as `SET_NULL`, but with a "system" placeholder. |
| `DO_NOTHING` | Database-side rule only. Django doesn't help — you risk integrity errors | Almost never. Only when you've configured an SQL-level rule yourself. |

Why we picked **different rules for `patient` and `doctor`**:

- **Patient is `CASCADE`** — if a patient deletes their account, their appointments lose meaning (no one to associate them with). Cascading prevents orphans.
- **Doctor is `PROTECT`** — if you tried to delete a doctor who still has appointments in the system, Django will block the deletion with `ProtectedError`. This is on purpose: prescriptions, lab results, and audit history must trace back to the prescribing doctor. You'd retire the account (set `is_active=False`), not delete the row.

> **Why it matters:** this is the single most consequential modelling decision in the file. Pick wrong and you either lose data you needed (`CASCADE` on the wrong side) or you can't clean up test rows (`PROTECT` everywhere). Always think: *if the parent disappears, does this child still make sense?*

### Concept 3: `related_name` — naming the reverse accessor

```python
patient = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='patient_appointments',
)

doctor = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.PROTECT,
    related_name='doctor_appointments',
)
```

Both FKs point at `CustomUser`. Without `related_name`, Django would try to give `CustomUser` two attributes called `appointment_set` — collision, hard error at startup. `related_name` lets us spell each side explicitly:

```python
patient.patient_appointments.all()   # all appointments where this user is the patient
doctor.doctor_appointments.all()     # all appointments where this user is the doctor
```

Two rules:

1. Whenever **two FKs from the same model point at the same target**, you must set distinct `related_name` values. Django enforces this at `check` time.
2. Even when only one FK points at a target, name the reverse explicitly. `patient_appointments` reads better than the default `appointment_set` everywhere it appears.

> **Why it matters:** in 13b, the doctor's "today's appointments" view will literally be `request.user.doctor_appointments.filter(appointment_date=today)`. The query reads like English because we named the reverse accessor today.

---

## Half 4 — The `Appointment` model line by line

```python
# backend/apps/appointments/models.py
from django.conf import settings
from django.db import models


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_appointments',
    )

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='doctor_appointments',
    )

    appointment_date = models.DateField()
    time_slot = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-appointment_date', '-time_slot']

    def __str__(self):
        return f"{self.patient.username} -> {self.doctor.username} on {self.appointment_date} {self.time_slot}"
```

### `class Status(models.TextChoices)` — the appointment lifecycle

Same enum pattern we used for `Role` on `CustomUser`. Three legal values:

| Value | When set | Who can transition |
|-------|----------|--------------------|
| `PENDING` | At creation (default) | Receptionist confirms → `CONFIRMED`; patient/receptionist cancels → `CANCELLED` |
| `CONFIRMED` | After receptionist confirmation | Either side cancels → `CANCELLED` |
| `CANCELLED` | Terminal | No further transitions |

`default=Status.PENDING` means every freshly booked appointment starts in `PENDING`. The transitions are enforced by views in 13b/13c, not by the model.

### `appointment_date` / `time_slot` — split fields on purpose

Two fields instead of one `DateTimeField` so we can:

- Filter "all of doctor X's appointments on date Y" with a single column equality check (`appointment_date=today`), no timezone math.
- Render the time-slot dropdown in the booking form against a fixed set of slot strings (`09:00`, `09:30`, ...) independent of date.
- Validate uniqueness later as `(doctor, appointment_date, time_slot)` — no two appointments for the same doctor at the same slot.

`DateField` stores `YYYY-MM-DD`. `TimeField` stores `HH:MM:SS`. Together they're enough to anchor a booking.

### `status = models.CharField(choices=..., default=...)` — same trick as `role`

`max_length=20` is comfortable headroom — longest value (`'CANCELLED'`) is 9 chars. Django gives us `appointment.get_status_display()` for free that returns the human label (`'Cancelled'`) instead of the DB value (`'CANCELLED'`).

### `notes = models.TextField(blank=True)` — optional free text

`TextField` is unlimited length (or whatever the DB caps at, typically gigabytes). `blank=True` means the form/admin accepts empty input — most appointments won't carry notes.

> Side note: `blank=True` is the **form/validation** rule. `null=True` is the **database** rule. For strings we keep `blank=True` only — empty string is a perfectly good "no value" sentinel; no need to allow SQL `NULL` too.

### `created_at = models.DateTimeField(auto_now_add=True)` — audit timestamp

Two related modifiers worth distinguishing now:

| Modifier | When it fires | Use case |
|----------|--------------|----------|
| `auto_now_add=True` | Once, at row creation | `created_at` audit timestamps |
| `auto_now=True` | Every time `.save()` runs | `updated_at` audit timestamps |

We only want creation time here — `auto_now=True` would silently rewrite the column every status change.

### `class Meta: ordering = ['-appointment_date', '-time_slot']`

Default sort order for any `Appointment.objects.all()` query: newest appointment first, then within a day, latest slot first. The `-` prefix means descending. Saves us writing `.order_by(...)` on every query.

### `__str__` — how an appointment prints

```python
prince -> dr_priya on 2026-07-01 11:30:00
```

Shows up in admin lists, shell debugging, log lines. The default `<Appointment object (7)>` is useless; this version tells you everything at a glance.

> **Why it matters:** `Meta.ordering` and `__str__` are quality-of-life code, not feature code. Both are easy to skip — and both make every later debugging session faster.

---

## Half 5 — Registering in the admin

```python
# backend/apps/appointments/admin.py
from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_date', 'time_slot', 'status', 'created_at')
    list_filter = ('status', 'appointment_date', 'doctor')
    search_fields = ('patient__username', 'doctor__username', 'notes')
    autocomplete_fields = ('patient', 'doctor')
    date_hierarchy = 'appointment_date'
```

Five admin tweaks, each earns its place:

| Option | What it does | Why for this model |
|--------|--------------|--------------------|
| `list_display` | Columns shown on the change-list page | Default shows only `__str__`. We want at-a-glance patient/doctor/when/status. |
| `list_filter` | Sidebar filter widgets | Receptionists will filter by status (`PENDING`) and by date. |
| `search_fields` | The top-of-page search box | `patient__username` uses the FK to search the related `CustomUser.username`. Double-underscore is Django's "follow the FK" syntax — same as in `filter()`. |
| `autocomplete_fields` | Replaces dropdown with type-to-search widget for FK fields | With hundreds of users, the default `<select>` becomes unusable. **Requires** `search_fields` on the target admin (`CustomUserAdmin` already sets it — `username`, `email`, `phone`). |
| `date_hierarchy` | Drill-down by year/month/day above the list | Lets the receptionist navigate "all appointments in Aug 2026 → 12 Aug" in two clicks. |

> **Gotcha** — `autocomplete_fields = ('patient', 'doctor')` fails at startup if the target model's admin doesn't define `search_fields`. We're safe because we set `search_fields = ('username', 'email', 'phone')` on `CustomUserAdmin` back in Step 9.

---

## Half 6 — Migrations, again

Same `makemigrations` → `migrate` flow as Step 8:

```bash
cd backend
python manage.py makemigrations appointments
# Migrations for 'appointments':
#   apps\appointments\migrations\0001_initial.py
#     + Create model Appointment

python manage.py migrate
# Operations to perform:
#   Apply all migrations: accounts, admin, appointments, auth, contenttypes, sessions
# Running migrations:
#   Applying appointments.0001_initial... OK
```

What the two commands physically do:

| Command | Writes | Reads |
|---------|--------|-------|
| `makemigrations` | A Python file at `backend/apps/appointments/migrations/0001_initial.py` describing the `CreateModel('Appointment', ...)` operation | The current `Appointment` class in `models.py` compared against the previous migration state |
| `migrate` | Rows into the `django_migrations` bookkeeping table + the actual `CREATE TABLE appointments_appointment (...)` SQL against `db.sqlite3` | The migration file just generated |

Two of the four columns the migration creates are FK columns named `patient_id` and `doctor_id` — Django auto-appends `_id` to FK columns at the DB level even though our Python attribute is just `patient`. That's why `Appointment.objects.filter(patient_id=7)` works alongside `Appointment.objects.filter(patient=user)`.

> **Verify in admin:** start `runserver`, log in to `/admin/`, click **Appointments → Add appointment**. The patient and doctor fields should show the autocomplete search widget (not the giant `<select>`). The `Status` field should show the three-option dropdown with `Pending` as the default.

---

## Half 7 — Three atomic commits

Three logical units, three commits — same rhythm as every previous step. Each commit should answer **one question** in the history:

```bash
# Commit 1: the scaffolding (skeleton only, no behavior)
git add backend/apps/appointments/ backend/config/settings.py
git commit -m "feat(appointments): scaffold app + register in INSTALLED_APPS"

# Commit 2: the model + auto-generated migration
git add backend/apps/appointments/models.py backend/apps/appointments/migrations/0001_initial.py
git commit -m "feat(appointments): add Appointment model with patient/doctor FKs + status lifecycle"

# Commit 3: admin
git add backend/apps/appointments/admin.py
git commit -m "feat(appointments): register Appointment in admin with autocomplete + filters"

git push -u origin feature/appointments-app
```

The split keeps each commit revertable. If the admin tweaks turn out wrong (say, `autocomplete_fields` errors at startup), we can revert commit 3 without losing the model or the migration. Bundling all three would make that surgery harder.

---

## Gotchas

- **Forgetting to patch `apps.py`'s `name`** — `startapp` writes `name = 'appointments'`. Without the `apps.` prefix, Django will fail with `ModuleNotFoundError` because the import path doesn't match the folder location.
- **Using `CASCADE` on the doctor FK** — would mean deleting a retired doctor wipes every prescription and lab-result trail attached to their appointments. Always `PROTECT` the side whose history must survive.
- **Skipping `related_name`** — two FKs to the same model collide on the default `appointment_set` accessor. Django raises `SystemCheckError` at startup. Always name the reverse accessor.
- **Storing the appointment as one `DateTimeField`** — makes "all of today's appointments" a timezone-fragile query. Split fields keep it simple and let us validate the slot independently of the date.
- **`autocomplete_fields` without target `search_fields`** — startup error. Target admin must have `search_fields` set or the autocomplete API has nothing to query.
- **`auto_now=True` on `created_at`** — silently rewrites the timestamp on every save. Always `auto_now_add=True` for creation timestamps; `auto_now=True` belongs on `updated_at`.
- **Importing `CustomUser` directly into another app's `models.py`** — risks circular import during Django startup. Always use `settings.AUTH_USER_MODEL` (a string), Django resolves it lazily.

---

## Where each future feature plugs in

| Feature | Sub-step | How it uses what we built |
|---------|----------|--------------------------|
| Patient books an appointment | 13b | `Appointment.objects.create(patient=request.user, doctor=..., appointment_date=..., time_slot=..., status=PENDING)` |
| Doctor's "today's appointments" page | 13c | `request.user.doctor_appointments.filter(appointment_date=today).select_related('patient')` |
| Doctor cancels an appointment | 13c | `appointment.status = Status.CANCELLED; appointment.save()` |
| Receptionist confirms a pending appointment | 13d | `Appointment.objects.filter(status='PENDING').update(status='CONFIRMED')` |
| 24-hour SMS/email reminder (Celery Beat) | Step 16 | Periodic task: `Appointment.objects.filter(appointment_date=tomorrow, status='CONFIRMED')` |
| Prescription FK to appointment | Step 15 | `prescription.appointment = ForeignKey(Appointment, on_delete=models.PROTECT)` — same `PROTECT` reasoning as our `doctor` FK |

The model written today is the spine that every later feature hangs off.

---

## Revise (3-line summary)

1. **App scaffolded + registered + migrated.** `startapp appointments` → patch `name = 'apps.appointments'` in `apps.py` → add to `INSTALLED_APPS` → `makemigrations` + `migrate` → `appointments_appointment` table exists in `db.sqlite3`.
2. **The `Appointment` model has two `ForeignKey`s into `CustomUser`** — `patient` with `on_delete=CASCADE` (orphans don't make sense) and `doctor` with `on_delete=PROTECT` (history must survive). Distinct `related_name`s (`patient_appointments`, `doctor_appointments`) let us spell the reverse query in English on the user side.
3. **Status enum + split date/time + audit timestamp + admin tweaks** — `TextChoices` for `PENDING/CONFIRMED/CANCELLED`, separate `DateField` + `TimeField` for clean filter queries, `auto_now_add=True` for `created_at`, and admin `autocomplete_fields` + `date_hierarchy` + `list_filter` so the receptionist's daily workflow is fast.

---

**Next:** Step 13b — patient-side booking views + URLs + templates. **Stays on `feature/appointments-app` branch.** No PR yet — Option A says one PR per parent step, so PR #3 opens after 13d, not now.
