# Step 14 — DRF API Layer

> **BIG step, chunked.** 14a = double-booking prevention (model + form layer, no DRF yet). 14b = DRF install + serializers + first ViewSet. 14c = SimpleJWT auth + permissions. 14d = write ops + filters + API docs. Branch `feature/drf-api` → PR #5 at the end. This file grows per sub-step.

# Step 14a — Double-Booking Prevention

## What we did here

1. Two carry-over fixes as branch openers: the login/register **already-authenticated guard** (deferred since 13c) and the `appointments/` URL-prefix pluralization.
2. `UniqueConstraint` on `(doctor, appointment_date, time_slot)` with a condition excluding CANCELLED — migration `0004`.
3. Discovered the constraint's form-validation gap → explicit `clean()` check in both booking forms with a shared helper.
4. Browser-verified: duplicate slot → friendly red error; cancelled slot → re-bookable.

---

## Half 1 — The branch openers (two small fixes)

**Already-authenticated guard.** First line of `login_view` and `register_view`:

```python
if request.user.is_authenticated:
    return redirect('accounts:profile')
```

A logged-in user visiting `/accounts/login/` now bounces to their profile instead of seeing a login form they can't meaningfully use (the Day 16 confusion, fixed properly).

**The trap we dodged first:** the initial attempt used `@login_required` on `login_view`. That decorator blocks *anonymous* users — exactly who the login page is for. Anonymous visitor → decorator redirects to `LOGIN_URL` → which is the login page → which redirects again → **infinite redirect loop, nobody can ever log in**. The guard must be the *reverse* check, inline in the view body. Decorators gate who may enter; this guard redirects who shouldn't linger.

**URL prefix pluralization.** `config/urls.py`: `appointment/` → `appointments/`. Zero breakage — every internal link goes through `{% url %}` names, which don't care about the prefix. Only browser-bar URLs changed. That's the payoff of the never-hardcode-URLs rule from Step 10.

---

## Half 2 — `UniqueConstraint` with a condition (partial unique index)

You know single-field `unique=True` (your `email`). For "no two rows may share this *combination*":

```python
# models.py
from django.db.models import Q

class Meta:
    ordering = ['-appointment_date', '-time_slot']
    constraints = [
        models.UniqueConstraint(
            fields=['doctor', 'appointment_date', 'time_slot'],
            condition=~Q(status='CANCELLED'),
            name='unique_doctor_slot',
            violation_error_message='This slot is already booked for this doctor.',
        )
    ]
```

What the migration physically creates: a **partial unique index** in SQLite — an index over `(doctor_id, appointment_date, time_slot)` covering only rows `WHERE NOT status = 'CANCELLED'`. Any INSERT or UPDATE that would produce a duplicate *active* row is rejected by the **database engine itself** with `IntegrityError`.

| Piece | Why |
|-------|-----|
| `condition=~Q(status='CANCELLED')` | Cancelled rows are invisible to the index → the slot frees the moment a booking cancels. Without it, a cancelled appointment blocks its slot forever. |
| `name='unique_doctor_slot'` | Required — names the index in the DB and in error messages. |
| COMPLETED / NO_SHOW still block | Correct — that slot really was consumed. Only CANCELLED re-opens it. |

**Why a DB constraint instead of only checking in the form:** the race. Two patients submit the same slot in the same second → both form checks run *before either row exists* → both pass → both INSERT. The DB serializes writes: the second INSERT fails, guaranteed, no matter how the requests interleave. A form check alone is a screen door.

**Migration gotcha we hit:** `migrate` failed with `IntegrityError` because the dev DB already contained duplicate active rows (from earlier double-booking tests). A constraint can't be created over data that violates it. Fix: delete/cancel the duplicates in `/admin/`, re-run `migrate`.

---

## Half 3 — The form-validation gap (a real Django subtlety)

Expected: `ModelForm.is_valid()` validates constraints → duplicate booking shows a form error. Reality: **500 `IntegrityError`**.

Why: when the form validates the constraint, it can only use fields *the form has*. Our condition references `status` — which is deliberately **not a form field**. Django hits the missing field while evaluating the condition and **silently skips the entire constraint check** (internally: the condition check raises `FieldError`, which is swallowed). Save proceeds, the DB constraint fires, 500.

Rule of thumb: **a conditional `UniqueConstraint` whose condition references a non-form field will not be validated by that form.** The DB still enforces it — but you get a crash page, not a friendly message.

---

## Half 4 — The fix: explicit `clean()` with a shared helper

```python
# forms.py
def _validate_slot_free(cleaned_data):
    doctor = cleaned_data.get('doctor')
    appt_date = cleaned_data.get('appointment_date')
    slot = cleaned_data.get('time_slot')
    if doctor and appt_date and slot:
        clash = (
            Appointment.objects
            .filter(doctor=doctor, appointment_date=appt_date, time_slot=slot)
            .exclude(status=Appointment.Status.CANCELLED)
            .exists()
        )
        if clash:
            raise forms.ValidationError('This slot is already booked for this doctor.')
```

Both booking forms get the same 4-line hook:

```python
    def clean(self):
        cleaned_data = super().clean()
        _validate_slot_free(cleaned_data)
        return cleaned_data
```

- **`clean()` (no suffix) is the form-wide hook** — runs after all per-field cleans, sees every field at once. Cross-field rules live here. (`clean_password_confirm()` from Step 12 was the per-field cousin.)
- `cleaned_data.get()` + the three-field guard — if a field already failed its own validation it's absent; skip our check and let its error show.
- `.exists()` — cheapest query possible: SQL `EXISTS`, no rows fetched.
- The helper mirrors the constraint exactly: same three fields, same CANCELLED exclusion. One definition, two forms.

**Known ceiling:** the same-second race still 500s — both requests can pass `.exists()` before either INSERTs. The DB constraint catches it; the rare ugly page isn't worth a try/except today. Two layers: form = friendly message for the 99.9% case, DB = correctness for the race.

---

## Bonus — why you're auto-logged-in after a server restart

Sessions live in the **database** (`django_session` table), not in the server process. Login writes a session row + hands the browser a `sessionid` cookie. Restarting `runserver` touches neither. Next visit: `SessionMiddleware` reads cookie → finds row → rehydrates `request.user`. Landing on profile specifically = the new guard bouncing you off the login page. Sessions expire after 2 weeks (`SESSION_COOKIE_AGE`), on POST logout, or never existed in incognito.

---

## Gotchas (Day 20)

- **`@login_required` on the login view = infinite redirect loop.** The decorator gates anonymous users away — from the one page that exists for them. Already-auth guards go inline, reversed.
- **Constraint over dirty data** — `migrate` fails if existing rows violate the new constraint. Clean the rows first.
- **Conditional constraint + form validation don't compose** when the condition references a non-form field — validation silently skipped, DB error leaks through. Pair every conditional `UniqueConstraint` with an explicit `clean()`.
- Zero typos in user-typed code this session — first clean sheet. Grep list stays active anyway.

---

## Revise (3-line summary)

1. **DB constraint = the truth.** `UniqueConstraint(doctor, date, slot, condition=~Q(status='CANCELLED'))` — partial unique index, race-proof, frees slots on cancel, blocks on completed/no-show.
2. **Form `clean()` = the manners.** Conditional constraints referencing non-form fields are silently skipped by form validation — add an explicit `.exists()` check in form-wide `clean()`, shared helper, both booking forms.
3. **Guards vs decorators.** `@login_required` on a login view loops forever; the already-authenticated bounce is an inline reverse check.

---

**Next:** 14b — install DRF, first serializer.

---

# Step 14b — DRF Install + First Serializer

## What we did here

1. Installed `djangorestframework`, froze it into `requirements.txt`, registered `'rest_framework'` in `INSTALLED_APPS`.
2. Wrote `AppointmentSerializer` (a `ModelSerializer`).
3. Proved it in the Django shell — a real appointment row → JSON dict — before writing any view.

---

## Half 1 — A serializer is a ModelForm for JSON

You already own this concept from Step 12. A `ModelForm` converts between HTTP form data and a model instance. A **serializer** does the same job between JSON and a model instance — the API's translator.

| Job | `ModelForm` | `Serializer` |
|-----|-------------|--------------|
| instance → output | HTML `<input>`s | JSON dict |
| incoming data → validated instance | form POST → `.save()` | JSON body → `.save()` |
| declare fields from a model | `class Meta: model, fields` | `class Meta: model, fields` (identical) |
| per-field validation | `clean_<field>()` | `validate_<field>()` |
| cross-field validation | `clean()` | `validate()` |

Same muscle memory. `ModelSerializer` auto-builds fields from the model exactly like `ModelForm` does.

---

## Half 2 — `AppointmentSerializer`

```python
# backend/apps/appointments/serializers.py
from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'doctor', 'appointment_date',
            'time_slot', 'status', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']
```

- **Same `Meta` shape** as your booking forms — `model` + `fields`.
- **`read_only_fields`** — the one new idea vs `ModelForm`. These go *out* in responses but are ignored on *input*: `id` and `created_at` are server-owned; `status` starts PENDING and only moves through the lifecycle views (confirm/complete/cancel), never set directly via the API.
- **FKs serialize as IDs by default** — `patient` and `doctor` become their primary keys (integers). Human-readable names are an opt-in for later (nested serializer or a `StringRelatedField`), skipped until a view actually needs them.

**Where the file lives:** inside the `appointments` app, next to the model — not a separate `api/` app. One serializer doesn't justify a new app and cross-app imports. Revisit if the API grows to span apps.

---

## Half 3 — Shell-test before building views

The lazy, correct way to verify a serializer: prove it in the shell before wiring a single URL.

```bash
python manage.py shell
```

```python
from apps.appointments.models import Appointment
from apps.appointments.serializers import AppointmentSerializer

a = Appointment.objects.first()
AppointmentSerializer(a).data
```

Output:

```python
{'id': 16, 'patient': 2, 'doctor': 4, 'appointment_date': '2026-07-12',
 'time_slot': '11:00:00', 'status': 'PENDING', 'notes': '',
 'created_at': '2026-07-11T20:09:08.397458+05:30'}
```

That dict **is** your API's JSON response. The ViewSet in 14c just wraps this — takes a queryset, runs each row through the serializer, returns the list. Seeing the shape now means 14c has no surprises.

Note the `created_at` — `+05:30` is IST, the timezone rendering from Step 6's `USE_TZ=True` + `TIME_ZONE='Asia/Kolkata'`. The DB stores UTC; the serializer renders IST. Same architecture, now visible in JSON.

---

## Gotchas (Day 21)

- **`pip freeze` location.** Run it from the repo root so `requirements.txt` lands at root (where Render reads it), not inside `backend/`.

---

## Revise (3-line summary)

1. **Serializer = ModelForm for JSON.** `ModelSerializer` with `class Meta: model, fields` — same shape you already know; `validate_<field>()` / `validate()` replace `clean_<field>()` / `clean()`.
2. **`read_only_fields`** ships fields out but ignores them on input — used for `id`, `status`, `created_at`. FKs serialize as IDs by default.
3. **Shell-test first.** `AppointmentSerializer(obj).data` returns the exact JSON your API will send — verify the shape before building the ViewSet.

---

**Next:** 14c — role-scoped `AppointmentViewSet` + `DefaultRouter` under `/api/`, browsable API.

---

# Step 14c — Role-Scoped ViewSet + Router

## What we did here

1. Created a dedicated `api` app (`backend/apps/api/`) to own the DRF layer — viewsets + router.
2. `AppointmentViewSet(ModelViewSet)` with role-scoped `get_queryset()` and server-side `perform_create()`.
3. `DefaultRouter` registering the viewset, mounted at `/api/`.
4. Verified the live browsable API across all four roles + the IDOR guard.

**Structure decision:** the `api` app owns viewsets + routing; each feature app keeps its own serializer (`appointments/serializers.py`). Clean separation — no cross-app model imports pile into one file, and adding a future app's API means adding its viewset here + its serializer there.

---

## Half 1 — ViewSet: all CRUD from one class

The HTML side needed a separate FBV per action (`doctor_list`, `book_appointment`, `cancel_appointment`...). A **ViewSet** collapses the five standard CRUD operations into one class:

```python
# backend/apps/api/views.py
from rest_framework import viewsets, permissions
from apps.appointments.models import Appointment
from apps.appointments.serializers import AppointmentSerializer


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'RECEPTION':
            return Appointment.objects.select_related('patient', 'doctor')
        if user.role == 'DOCTOR':
            return user.doctor_appointments.select_related('patient')
        return user.patient_appointments.select_related('doctor')

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)
```

`ModelViewSet` gives you five actions for free:

| HTTP | URL | Action |
|------|-----|--------|
| GET | `/api/appointments/` | `list` |
| POST | `/api/appointments/` | `create` |
| GET | `/api/appointments/5/` | `retrieve` |
| PUT/PATCH | `/api/appointments/5/` | `update` |
| DELETE | `/api/appointments/5/` | `destroy` |

You write zero of those. You override only the **hooks**: `get_queryset()` (which rows this user sees) and `perform_create()` (fill server-owned fields). `permission_classes = [IsAuthenticated]` → anonymous gets 401.

---

## Half 2 — `get_queryset()` scopes every action at once

This is the same patient/doctor/reception branching from the HTML views — but written **once** and reused by `list` *and* `retrieve` automatically.

The powerful part: **retrieve is scoped for free.** `GET /api/appointments/5/` internally runs `get_queryset().get(pk=5)`. If appointment 5 isn't in this user's queryset → 404. So a patient probing `/api/appointments/<someone-else's-id>/` gets 404 with no ownership check written in a detail method. The single `get_queryset()` guards all five actions — the same IDOR protection as your HTML `get_object_or_404(..., patient=request.user)`, now automatic and unforgettable.

`perform_create()` mirrors your HTML `commit=False` → set patient: a patient POSTing a new appointment has `patient` injected server-side from `request.user`, never trusted from the request body.

(LAB role falls to the last line → `patient_appointments` → empty. Fine; lab gets its own API surface later.)

---

## Half 3 — Router: auto-generated URLconf

Hand-written `urlpatterns` needed one `path()` per view. A **router** generates all of a viewset's routes from one registration:

```python
# backend/apps/api/urls.py
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet

router = DefaultRouter()
router.register('appointments', AppointmentViewSet, basename='appointment')

urlpatterns = router.urls
```

```python
# backend/config/urls.py
path('api/', include('apps.api.urls')),
```

`router.register('appointments', ...)` produces `/appointments/` (list+create) and `/appointments/<pk>/` (retrieve+update+destroy) — the whole CRUD table, no hand-written paths. Under the `/api/` mount that's `/api/appointments/`.

**Why `basename` is required here.** The router names the auto-generated URL patterns (`appointment-list`, `appointment-detail`). Normally DRF *infers* that name from the viewset's `queryset` **attribute** — reads the model off it. We don't set a `queryset` attribute; we override the `get_queryset()` **method** (rows depend on the request user). DRF can't call that method at URL-registration time (no request yet), so it can't infer the model or the name → error unless we pass `basename` explicitly. **Rule: override `get_queryset()` → you must set `basename`.**

---

## Half 4 — The browsable API + content negotiation

`DefaultRouter` + DRF's default renderer means visiting `/api/appointments/` **in a browser** returns a clickable HTML page — styled, with forms and buttons and a JSON preview — not raw JSON. A free API explorer; no Postman needed for manual testing.

That's **content negotiation**: the *same* URL returns different formats based on the request's `Accept` header —

| Client | `Accept` header | Gets back |
|--------|-----------------|-----------|
| Browser | `text/html` | Browsable HTML page |
| `requests` / fetch | `application/json` | Raw JSON |

The server reads the header and picks the renderer. Same data, same user, same URL — the format is negotiated, not role-based.

The browsable API authenticates via your normal **login session** (DRF's `SessionAuthentication`), which is why the verification below just uses the HTML login. Token auth (JWT) comes in 14d for script/mobile clients.

---

## Verification (all five passed)

| # | As | URL | Result |
|---|-----|-----|--------|
| 1 | anonymous | `/api/appointments/` | 403 — auth required |
| 2 | patient | `/api/appointments/` | only own appointments |
| 3 | doctor | `/api/appointments/` | only their appointments |
| 4 | reception | `/api/appointments/` | all appointments |
| 5 | patient | `/api/appointments/<other-id>/` | 404 — `get_queryset` scoping |

---

## Gotchas (Day 22)

- **Quoting the viewset in `register`.** `router.register('appointments', 'AppointmentViewSet', ...)` — the class name as a *string*. The router calls `.get_extra_actions()` on it → `AttributeError: 'str' object has no attribute 'get_extra_actions'` at import time. The URL prefix is a string; the viewset must be the imported class. (`'appointments'` quoted = correct; `AppointmentViewSet` quoted = wrong.)
- **Attribute-name typo (`user.roel`).** Passed `manage.py check`, then `AttributeError: 'CustomUser' object has no attribute 'roel'` at first request — attribute access resolves at call time, not import. New grep-list entry: attribute names on `request.user` / model instances.

---

## Revise (3-line summary)

1. **ViewSet = five CRUD actions from one class.** Override only the hooks: `get_queryset()` (visibility) + `perform_create()` (server-owned fields). `IsAuthenticated` blocks anonymous.
2. **`get_queryset()` scopes list AND retrieve.** Retrieve does `get_queryset().get(pk=...)`, so other people's IDs 404 automatically — IDOR protection written once, applied everywhere.
3. **Router auto-generates routes; `basename` required when you override `get_queryset()`** (DRF can't infer the model without a `queryset` attribute). `DefaultRouter` also gives the browsable API — HTML to browsers, JSON to scripts, chosen by content negotiation on the `Accept` header.

---

**Next:** 14d — SimpleJWT auth (`/api/token/` + refresh) so non-browser clients authenticate, API write operations, and the django-filter decision.
