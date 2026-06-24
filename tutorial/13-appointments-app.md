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

---

# Step 13b — Patient-Side Booking (Views + Form + URLs + Templates)

> **Sub-step of Step 13.** 13a built the spine (the model). 13b adds the first user-facing feature on top of it: a logged-in PATIENT can browse doctors, book an appointment, see their bookings, and cancel one. Doctor and receptionist flows land in 13c–13d.

## What we did here

1. Wrote `BookAppointmentForm` (a `ModelForm`) — exposes only the patient-fillable fields, restricts the doctor dropdown to actual DOCTOR-role users.
2. Wrote four function-based views in `backend/apps/appointments/views.py`: `doctor_list`, `book_appointment`, `my_appointments`, `cancel_appointment`.
3. Created `backend/apps/appointments/urls.py` with `app_name = 'appointments'` and four named routes.
4. Wired the appointments URLconf into `backend/config/urls.py` under the `appointments/` prefix.
5. Wrote three templates under `frontend/templates/appointments/` — `doctor_list.html`, `book.html`, `my_appointments.html`.
6. Verified the full patient flow in the browser: browse → book → list → cancel.
7. Made **two atomic Conventional Commits** on `feature/appointments-app` (backend logic, then templates).

After 13b, a PATIENT account can complete a full booking lifecycle through the UI — without the receptionist or admin shell.

---

## Half 1 — The `QuerySet`, lazy on purpose

Every line of view code in 13b ultimately calls one of these:

```python
User.objects.filter(role='DOCTOR').order_by('username')
request.user.patient_appointments.select_related('doctor').all()
```

Each returns a **`QuerySet`** — a Python object that *describes* a database query but has not yet *executed* it. Print one and you see SQL-ish text, not rows. That deferral is called **laziness**, and it's the single most important runtime fact about Django's ORM.

### When the SQL actually fires

A `QuerySet` is inert until something forces it to materialize. Six common triggers:

| Trigger | Example | Why it fires |
|---------|---------|--------------|
| Iteration | `for doctor in doctors:` | Python calls `__iter__` → ORM runs the query |
| `list()` | `list(doctors)` | Same — needs all rows at once |
| Slicing with step | `doctors[::2]` | Needs the whole result to slice |
| `len()` | `len(doctors)` | Counts rows — runs `SELECT COUNT(*)` |
| `bool()` | `if doctors:` or `{% if doctors %}` | Checks if any row exists |
| Template loop | `{% for doctor in doctors %}` | Same as Python iteration |

In `doctor_list.html` the database is hit at the moment the `{% for doctor in doctors %}` runs — not when the view assigns the variable. That's why the view body is allowed to do:

```python
doctors = User.objects.filter(role='DOCTOR').order_by('username')   # no SQL yet
return render(request, 'appointments/doctor_list.html', {'doctors': doctors})
```

…with zero database calls inside the view. The render-then-iterate path means we can keep view bodies cheap.

### Chaining + caching

QuerySets are **chainable** — every call returns a new QuerySet, so you can stack filters:

```python
User.objects.filter(role='DOCTOR').exclude(is_active=False).order_by('username')
```

Only one SQL query fires (when something finally consumes it). And after a QuerySet runs once, it **caches** the result on the instance — a second `for ... in same_qs:` does not re-query the DB.

> **Why it matters:** the lazy + chainable + cached combo lets us write view code that looks expensive but runs cheap. Tutorial Q1 lesson: don't ask *what* a QuerySet is — ask *when* it fires.

---

## Half 2 — `ModelForm` with a `ForeignKey` field

The booking form has to render a doctor dropdown. We could hand-build a `forms.Form` with a `ModelChoiceField`, but `ModelForm` knows how to do it from the model definition:

```python
# backend/apps/appointments/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import Appointment

User = get_user_model()


class BookAppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['doctor', 'appointment_date', 'time_slot', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date'}),
            'time_slot': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = User.objects.filter(role='DOCTOR')
```

Four things to notice.

### `class Meta` — capital `M`, every letter

Django introspects this nested class to wire up the form. **Lowercase `meta` is silently ignored** — the form will look like it works at import time, then explode at first instantiation with `ValueError: ModelForm has no model class specified.` We hit this bug in 13b. Always grep your `ModelForm` for `class Meta` (capital M) before declaring clean.

### `fields = ['doctor', 'appointment_date', 'time_slot', 'notes']` — explicit allow-list

The model has more fields (`patient`, `status`, `created_at`). We list ONLY the ones the patient should fill. **Two fields are deliberately excluded:**

| Excluded field | Why | Where it gets set |
|----------------|-----|-------------------|
| `patient` | Otherwise an attacker could POST `patient=<another user id>` and book on their behalf | Server-side in the view: `appointment.patient = request.user` |
| `status` | Defaults to `PENDING` from the model; no reason to let the patient choose `CONFIRMED` | Model default |

This is **defense in depth** — same pattern as the PATIENT-lock in Step 12 register form. Don't trust the client to omit dangerous fields; never expose them in the first place.

### The dynamic queryset in `__init__`

`ModelForm` by default would populate the `doctor` dropdown with **every `CustomUser` in the database** — patients, receptionists, lab techs, all mixed together. We override `__init__` to narrow it:

```python
self.fields['doctor'].queryset = User.objects.filter(role='DOCTOR')
```

What physically happens: when the form is instantiated, the `doctor` field's `queryset` attribute is replaced with the filtered one. Django uses that queryset both when **rendering** the dropdown (`<option>` per matching row) AND when **validating** the submitted form (the chosen doctor's PK must appear in the queryset). So the filter is both UX and security — an attacker who POSTs a non-DOCTOR user's PK will get a "Select a valid choice" form error, not a successful booking.

### The widget overrides

```python
widgets = {
    'appointment_date': forms.DateInput(attrs={'type': 'date'}),
    'time_slot': forms.TimeInput(attrs={'type': 'time'}),
}
```

By default Django renders dates and times as plain `<input type="text">`. We force `type="date"` and `type="time"` so the browser shows its native date/time picker. Zero JavaScript, zero CSS — browser does the work.

> **Why it matters:** `ModelForm` saves you 30 lines of validation per model. The cost is one rule — **always restrict FK fields with a queryset in `__init__`**, or the form leaks every row of the target table into the HTML.

---

## Half 3 — `select_related` and the N+1 query problem

In `my_appointments` view:

```python
appointments = request.user.patient_appointments.select_related('doctor').all()
```

Without `select_related`, this is what would happen at template render time:

```
SELECT * FROM appointments_appointment WHERE patient_id = 1;    -- 1 query
-- then for EACH row in the loop:
SELECT * FROM accounts_customuser WHERE id = 5;                 -- query 2
SELECT * FROM accounts_customuser WHERE id = 7;                 -- query 3
SELECT * FROM accounts_customuser WHERE id = 12;                -- query 4
-- ...one extra query per appointment
```

That's the **N+1 problem** — 1 query for the parent list + N queries for the related rows. For a patient with 30 appointments → **31 queries** to render one page.

With `select_related('doctor')`:

```sql
SELECT appointments_appointment.*, accounts_customuser.*
FROM   appointments_appointment
JOIN   accounts_customuser ON appointment.doctor_id = customuser.id
WHERE  appointment.patient_id = 1;
```

**One query.** The JOIN pulls every doctor row in the same SQL roundtrip. The template's `{{ appt.doctor.username }}` then reads from already-loaded data — pure Python attribute access, no extra SQL.

| Pages worth of appointments | Without `select_related` | With `select_related` |
|----------------------------|--------------------------|----------------------|
| 30 rows | 31 queries | 1 query |
| 100 rows | 101 queries | 1 query |

`select_related` is only for `ForeignKey` and `OneToOne` (anything that can be JOINed). For `ManyToMany` and reverse-FK queries, use `prefetch_related` (separate query, joined in Python).

> **Why it matters:** N+1 is the most common Django performance bug in the wild. Anytime a template loop dereferences a FK (`{{ thing.related.attr }}`), the view body must have `select_related('related')`. No exceptions.

---

## Half 4 — `get_object_or_404` + ownership scoping

In `cancel_appointment`:

```python
appointment = get_object_or_404(
    Appointment,
    id=appointment_id,
    patient=request.user,
)
```

Two concerns rolled into one call.

**Concern 1 — fetch or 404.** `Model.objects.get(...)` raises `DoesNotExist` (becomes a 500 page) when the row is missing. `get_object_or_404` raises Django's `Http404` (becomes a clean 404 page) instead. Always use it inside views that look up by URL parameter.

**Concern 2 — ownership scoping.** The keyword `patient=request.user` makes the lookup **filter by who's logged in, not just by ID**. Effect:

- Patient A clicks Cancel on their own appointment → row found → cancelled.
- Patient A crafts a POST to `/appointments/cancel/<patient B's appointment id>/` → row NOT found under patient A → 404.

Without the `patient=request.user` filter, A could cancel B's appointments by guessing IDs. This is a **horizontal privilege escalation** flaw and it has a textbook OWASP name: **Insecure Direct Object Reference (IDOR)**. The fix is exactly this — always include the ownership clause in the lookup.

> **Why it matters:** every "modify someone's data via a URL parameter" view in Django needs the ownership clause baked into the lookup. Bolt-on permission checks later (`if obj.owner != request.user: raise PermissionDenied`) are an OK fallback, but they're easier to forget. Do it in the lookup.

---

## Half 5 — Decorator stacking: `@login_required` + `@require_POST`

```python
@login_required
@require_POST
def cancel_appointment(request, appointment_id):
    ...
```

Two decorators. Order matters.

| Decorator | What it guards | Failure mode |
|-----------|---------------|--------------|
| `@login_required` | Anonymous user → redirect to `LOGIN_URL` with `?next=...` | 302 redirect |
| `@require_POST` | Non-POST request method → 405 Method Not Allowed | 405 response |

Reading them **bottom-up** is how Python applies them: `cancel_appointment` first becomes `require_POST(cancel_appointment)`, then becomes `login_required(require_POST(cancel_appointment))`. So at request time the **outermost** decorator runs first: login check, then method check, then the view body.

If you flipped them (`@require_POST` outermost, `@login_required` inner), an anonymous user sending GET would get a 405 instead of a clean redirect — confusing UX. Login check first, always.

**Why `@require_POST` on cancel**: cancelling is a state-mutating operation. The HTTP spec says GET requests must be **safe and idempotent** (no side effects). A GET-triggered state change can be fired by a browser pre-fetch, a crawler, or a `<img src="/cancel/3/">` injected by an attacker into another page (CSRF-adjacent attack). Forcing POST closes that door. The Step 12 logout view enforced this same rule.

---

## Half 6 — The four patient views, line by line

```python
# backend/apps/appointments/views.py
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import BookAppointmentForm
from .models import Appointment

User = get_user_model()


@login_required
def doctor_list(request):
    doctors = User.objects.filter(role='DOCTOR').order_by('username')
    return render(request, 'appointments/doctor_list.html', {'doctors': doctors})


@login_required
def book_appointment(request, doctor_id):
    doctor = get_object_or_404(User, id=doctor_id, role='DOCTOR')

    if request.method == 'POST':
        form = BookAppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = request.user
            appointment.save()
            return redirect('appointments:my_appointments')
    else:
        form = BookAppointmentForm(initial={'doctor': doctor})

    return render(request, 'appointments/book.html', {'form': form, 'doctor': doctor})


@login_required
def my_appointments(request):
    appointments = (
        request.user.patient_appointments.select_related('doctor').all()
    )
    return render(request, 'appointments/my_appointments.html', {'appointments': appointments})


@login_required
@require_POST
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user,
    )

    if appointment.status != Appointment.Status.CANCELLED:
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()

    return redirect('appointments:my_appointments')
```

### `doctor_list` — the browse page

One queryset, one render. Already covered in Half 1 (lazy eval). `order_by('username')` makes the listing deterministic — same order every refresh.

### `book_appointment` — the classic Django form view pattern

This is the **GET-vs-POST pattern** you'll write 50 times. Memorize the shape:

```python
if request.method == 'POST':
    form = SomeForm(request.POST)
    if form.is_valid():
        # ... save, redirect
        return redirect(...)
else:
    form = SomeForm()       # blank form for GET

return render(request, 'template.html', {'form': form})
```

Two paths through the view:

| Request | Branch | What happens |
|---------|--------|--------------|
| GET `/book/3/` | `else:` | Blank form rendered with `initial={'doctor': doctor}` so dropdown is pre-selected |
| POST `/book/3/` with valid data | inner `if form.is_valid()` true | Save + redirect (302) → `/mine/` |
| POST `/book/3/` with invalid data | inner `if` false, fall through to `render()` | Form re-rendered WITH bound data + `form.errors` populated |

The `commit=False` step is the **defense-in-depth** moment:

```python
appointment = form.save(commit=False)   # build the object, don't INSERT yet
appointment.patient = request.user      # force the field that's not in the form
appointment.save()                       # NOW insert
```

`form.save(commit=False)` returns an unsaved `Appointment` instance. We attach the patient server-side, then save. The `patient` field is not in `Meta.fields`, so even if an attacker injected a `patient=<other id>` POST param it would be ignored — and our explicit assignment then wins.

### `my_appointments` — already covered

The `select_related('doctor')` part is Half 3.

### `cancel_appointment` — already covered

The decorator stack is Half 5, the ownership scoping is Half 4.

The `if appointment.status != Appointment.Status.CANCELLED:` guard is a tiny optimization — skip a redundant DB write if the row is already cancelled. Not strictly necessary; clarifies intent.

---

## Half 7 — The URL layer

```python
# backend/apps/appointments/urls.py
from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('book/<int:doctor_id>/', views.book_appointment, name='book'),
    path('mine/', views.my_appointments, name='my_appointments'),
    path('cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel'),
]
```

```python
# backend/config/urls.py — one line added
path('appointments/', include('apps.appointments.urls')),
```

Three things worth pinning:

- **`app_name = 'appointments'` is what makes `'appointments:my_appointments'` resolvable.** Without it, every `{% url %}` and `redirect()` call in templates and views fails with `NoReverseMatch`.
- **The URL converter name MUST match the view kwarg name.** `<int:doctor_id>` → view signature must be `def book_appointment(request, doctor_id):`. Mismatch (a transposition like `appointmetn_id`) = `TypeError: got an unexpected keyword argument` at request time. `manage.py check` won't catch it.
- **`reverse()` strings cannot contain stray whitespace inside the quotes.** `redirect('appointments: my_appointments')` (space after the colon) fails with `NoReverseMatch: Reverse for ' my_appointments' not found.` The leading-space view name is not registered. `check` won't catch this either.

---

## Half 8 — The three templates, line by line

### `doctor_list.html` — the browse page

```django
{% extends 'base.html' %}

{% block title %}Find a Doctor - Smart OPD{% endblock %}

{% block content %}
<h1>Available Doctors</h1>

{% if doctors %}
<ul>
    {% for doctor in doctors %}
    <li>
        <strong>Dr. {{ doctor.username }}</strong>
        {% if doctor.email %} - {{ doctor.email }}{% endif %}
        <a href="{% url 'appointments:book' doctor.id %}">Book appointment</a>
    </li>
    {% endfor %}
</ul>
{% else %}
    <p>No doctor available right now.</p>
{% endif %}
{% endblock %}
```

Notice `{% url 'appointments:book' doctor.id %}` — the second token (`doctor.id`) is the **positional arg** that fills `<int:doctor_id>` in the URL pattern. Forget it and you get `NoReverseMatch: Reverse for 'book' with no arguments not found`.

### `book.html` — the form page

```django
{% extends 'base.html' %}

{% block title %}Book with Dr. {{ doctor.username }} - Smart OPD {% endblock %}

{% block content %}
<h1>Book Appointment</h1>
<p>Doctor: <strong>Dr. {{ doctor.username }}</strong></p>

{% if form.errors %}
    <div style="color:red">
        {% for field, errors in form.errors.items %}
        <p>{{ field }}: {{ errors|join:", " }}</p>
        {% endfor %}
    </div>
{% endif %}

<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Confirm Booking</button>
</form>

<p><a href="{% url 'appointments:doctor_list' %}">Back to doctors</a></p>
{% endblock %}
```

The plural traps from Step 12 are still live: `form.errors` (not `.error`), `form.errors.items` (not `.item`). Both render empty without raising — silent failures, the worst kind.

`{{ form.as_p }}` wraps each field in `<p>` tags. Quick layout, fine for learning. Production would render fields individually for full CSS control.

### `my_appointments.html` — the list + cancel page

The interesting line per row:

```django
<form method="post" action="{% url 'appointments:cancel' appt.id %}" style="display:inline;">
    {% csrf_token %}
    <button type="submit" onclick="return confirm('Cancel this appointment?');">Cancel</button>
</form>
```

One mini-form per row. Each posts to its own URL (`/appointments/cancel/<row id>/`). The `display:inline` keeps it from breaking the table cell. `onclick="return confirm(...)"` is client-side double-check; the real safeguard is the `@require_POST` + ownership scoping in the view.

`{{ appt.get_status_display }}` is the auto-generated method on `TextChoices` — returns `"Pending"` (human label), not `"PENDING"` (DB value). Same magic on `CustomUser.get_role_display()`.

---

## Half 9 — Two atomic commits, then push

```bash
# Commit 1: backend logic — form + views + URLs (all four files belong together)
git add backend/apps/appointments/forms.py \
        backend/apps/appointments/views.py \
        backend/apps/appointments/urls.py \
        backend/config/urls.py
git commit -m "feat(appointments): add patient booking views + form + urls"

# Commit 2: templates
git add frontend/templates/appointments/
git commit -m "feat(appointments): add patient templates (doctor list, book, my appointments)"

git push origin feature/appointments-app
```

Why two not three: forms.py and views.py and urls.py are one **logical unit** — the backend booking flow. Splitting them would create intermediate commits that don't compile a working feature (form with no view that uses it, view with no URL routing to it). Templates are the UI layer and can be reviewed independently.

Branch stays on `feature/appointments-app`. **No PR yet** — Option A: one PR per parent step, opens after 13d.

---

## Gotchas (Day 15 silent-failure typo pattern)

Every typo in 13b shared one shape: **`manage.py check` and runserver boot both passed clean, and the bug surfaced only at the first real request.** The IDE (Antigravity) auto-completion is the common cause. Always scan these before declaring "no issues":

| Typo | Where it hides | What crashes | Why `check` misses it |
|------|---------------|--------------|----------------------|
| `class meta:` (lowercase) | `ModelForm.Meta` | `ValueError: ModelForm has no model class specified` on form instantiation | Lowercase `meta` is a valid nested class name; Django just never looks for it |
| Space inside `'appointments: name'` | `redirect()`, `reverse()`, `{% url %}` | `NoReverseMatch: Reverse for ' name' not found` | URL name strings are not resolved at boot |
| Letter transposition in URL converter name (`<int:appointmetn_id>`) | `urls.py path()` | `TypeError: view() got an unexpected keyword argument` | Both names are valid Python identifiers in isolation |
| Missing `%` in template tag (`{% url ... doctor.id}`) | Any template | `TemplateSyntaxError: Unclosed tag` on first render | Templates aren't compiled at boot, only at first render |
| `form.error` / `form.errors.item` (missing `s`) | Templates | Renders empty silently, feature dead but no error | Django's template language never errors on missing attributes |

Defense: before commit, grep your typed strings for those patterns. None of them cost the parser anything to check; all of them cost an end-user a 500 page.

Other gotchas from 13b:

- **Forgetting `commit=False` on `form.save()`** — `appointment.patient` never gets set, `IntegrityError: NOT NULL constraint failed: appointments_appointment.patient_id`. Always: `commit=False` → assign fields → `save()`.
- **Not narrowing the FK queryset in `__init__`** — every `CustomUser` row appears in the dropdown, including other patients and lab techs. Security + UX bug.
- **Forgetting `select_related`** — page loads slowly with no clear culprit. Install `django-debug-toolbar` if you ever need to count queries; for now the rule is "every FK dereferenced in a template loop must be select_related'd in the view."
- **Skipping the ownership clause in `get_object_or_404`** — IDOR vulnerability. Attacker cancels other patients' appointments by guessing IDs. Always include the `patient=request.user` clause.

---

## Where each future feature plugs in

| Feature | Sub-step | How it builds on 13b |
|---------|----------|----------------------|
| Doctor "today's appointments" page | 13c | Mirror image — `request.user.doctor_appointments.filter(appointment_date=today).select_related('patient')` |
| Doctor cancels an appointment | 13c | Same `cancel` URL pattern, different ownership clause (`doctor=request.user`) |
| Role-based login redirect | 13c | Override `login_view` to branch on `request.user.role` — `/doctor/`, `/reception/`, `/lab/`, `/patient/` |
| Receptionist book-on-behalf | 13d | New view + form that lets receptionist set `patient=<some user>` (the field that's currently locked) |
| Receptionist global appointment list + filters | 13d | `Appointment.objects.select_related('patient', 'doctor').filter(<filter form>)` |
| 24-hour reminder email | Step 16 | Celery Beat queries `Appointment.objects.filter(appointment_date=tomorrow, status='CONFIRMED')` |
| DRF API for booking | Step 14 | Same `BookAppointmentForm` logic translates to a `BookAppointmentSerializer` |

---

## Revise (3-line summary)

1. **Patient booking flow shipped end-to-end** — `doctor_list` browse → `book_appointment` GET/POST form → `my_appointments` list with `select_related('doctor')` → `cancel_appointment` POST-only with ownership-scoped `get_object_or_404`. All four views `@login_required`.
2. **`BookAppointmentForm` is the security spine** — `Meta.fields` excludes `patient` and `status`, dynamic queryset in `__init__` restricts the doctor dropdown to DOCTOR users, and the view's `commit=False` + `appointment.patient = request.user` enforces server-side ownership. Three layers, same defense-in-depth pattern as Step 12 register.
3. **Day 15 typo lesson** — `manage.py check` clean does NOT mean the file is bug-free. Lowercase `class meta`, stray space inside reverse strings, transposed letters in URL converter names, missing `%` in template tags, plural drops on `form.errors.items` — all silent at boot, all 500 at request time. Grep typed strings before commit.

---

**Next:** Step 13c — doctor-side view (today's appointments + doctor cancel) + role-based redirect on login. **Stays on `feature/appointments-app` branch.** PR #3 still waits for 13d.
