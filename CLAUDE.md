# CLAUDE.md — Smart OPD Management System

This file auto-loads when Claude Code opens this project folder. It is the project's "AI brief" — what we are building, how, and how to help the developer.

## Who is building this

**Prince** — learning Django from scratch by building this project as the teaching vehicle. Important context for any AI assistant working here:

- The developer **types every line of code themselves**. Do not pre-scaffold apps, models, views, or templates. Do not run `django-admin startproject` for them.
- Teach **step-by-step**: every command and file gets an explanation of **what** it does, **why** Django needs it, and **how** it fits the bigger picture.
- Frontend templates are built using **Stitch** (AI UI tool) and **Antigravity IDE**. Backend/Django is the learning focus — frontend is mostly drag-and-drop.
- Treat the developer as beginner-to-intermediate. Explain MVT pattern, migrations, ORM, DRF concepts as we encounter them. Do not assume framework knowledge.

## What we are building

A hospital **Out-Patient Department (OPD)** management system with 4 user roles. Full feature spec and permission matrix live in `opd_roles_and_final_structure.html` at the project root — open that file for the source of truth on roles, features, and notifications.

### Roles at a glance

| Role | URL prefix | Core job |
|------|-----------|----------|
| **Doctor** | `/doctor/*` | Set availability, see appointments, write prescriptions, request lab tests, view results |
| **Receptionist / Admin** | `/reception/*` | Manage patients & doctors, book on behalf, view all appointments, dashboard stats |
| **Lab Technician** | `/lab/*` | View pending tests, upload PDF/image results, generate branded lab reports |
| **Patient** | `/patient/*` | Find doctors, book/cancel appointments, view prescriptions & lab results, medical history |

### Key permission rules (from the spec)

- Only **Receptionist** manages other users
- Only **Doctor** writes prescriptions and requests lab tests
- Only **Lab Tech** uploads test results
- **Patient** and **Doctor** receive email notifications; only Patient gets the 24-hour appointment reminder (via Celery Beat)

## Tech stack

**Backend:**
- Django 5
- Django REST Framework
- SimpleJWT (token auth for API)
- drf-spectacular (auto-generated API docs)
- django-filter (query filtering)
- Celery + Redis (background tasks, scheduled reminders)
- ReportLab (PDF generation for prescriptions and lab reports)
- Pillow (image handling for lab result uploads)
- python-decouple (read `.env` file)
- psycopg2-binary (PostgreSQL driver)
- Whitenoise (static file serving in production)
- Gunicorn (production WSGI server)

**Frontend:**
- Django templates (rendered server-side)
- Static files (CSS / JS / images) via Whitenoise
- HTML drafted in Stitch, polished in Antigravity IDE

**Database:**
- Local dev: SQLite (Django default — zero config)
- Production: PostgreSQL on Render free tier

**Deployment:**
- Render (no Docker — Render auto-detects Python)
- `requirements.txt` at project root
- `Procfile` inside `backend/` with: `web: gunicorn config.wsgi --chdir backend`
- Auto-deploy on push to `main`

## Folder structure (target)

```
opd-project/                       ← GitHub repo root
├── backend/
│   ├── config/                    ← Django project config
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── apps/                      ← All Django apps live here
│   │   ├── accounts/              ← CustomUser + auth
│   │   ├── appointments/          ← Booking, availability, scheduling
│   │   ├── lab/                   ← Tests, results, PDF reports
│   │   ├── prescriptions/         ← Prescription writing & viewing
│   │   ├── notifications/         ← In-app + email + Celery tasks
│   │   └── api/                   ← Centralized DRF endpoints
│   ├── media/                     ← User uploads (gitignored)
│   ├── .env                       ← Secrets (gitignored)
│   ├── .env.example               ← Template for `.env`
│   ├── manage.py
│   └── Procfile                   ← Render needs this
├── frontend/
│   ├── templates/                 ← Django reads from here
│   │   ├── base.html
│   │   ├── accounts/
│   │   ├── appointments/
│   │   ├── lab/
│   │   ├── prescriptions/
│   │   ├── dashboard/
│   │   └── notifications/
│   ├── static/                    ← Django reads from here
│   │   ├── css/
│   │   ├── js/
│   │   └── img/
│   └── stitch_exports/            ← Raw HTML from Stitch (untouched)
├── requirements.txt               ← MUST be at root level for Render
├── .gitignore
└── README.md
```

**Critical Django settings to point at `frontend/`:**

```python
# backend/config/settings.py
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/

TEMPLATES = [{
    'DIRS': [BASE_DIR.parent / 'frontend' / 'templates'],
}]
STATICFILES_DIRS = [BASE_DIR.parent / 'frontend' / 'static']
MEDIA_ROOT = BASE_DIR / 'media'
```

## Conventions

- **All folder names lowercase** — Render runs Linux, which is case-sensitive. `Backend/` and `backend/` are different folders on Linux but the same on Windows. Lowercase avoids deploy-time surprises.
- `requirements.txt` lives at the **root**, not inside `backend/` — Render auto-detects Python projects only when `requirements.txt` is at the repo root.
- `Procfile` lives inside `backend/` — it uses `--chdir backend` so Gunicorn finds `config.wsgi`.
- `.env` is **never committed**. `.env.example` lists the keys (no values) so other developers know what to set.
- One feature = one Django app inside `backend/apps/` — keep apps small and single-purpose.

## Notification matrix (from the spec)

| Event | Recipient | Channel |
|-------|----------|---------|
| Booking confirmed | Patient | Email + in-app |
| 24-hour reminder | Patient | Email (Celery Beat) |
| Test requested | Lab Technician | In-app |
| Result uploaded | Patient + Doctor | In-app + email |
| Appointment cancelled | Doctor | In-app |
| Appointment confirmed | Patient | In-app |
| Prescription written | Patient | In-app |
| Walk-in registered | Receptionist | In-app only |

## Teaching roadmap

Where we are in the learning journey. Update this as we progress.

- [x] **Step 1** — Python virtual environment (`venv`) ✅ Python 3.14.2 in `.venv/`
- [x] **Step 2** — Install Django, freeze `requirements.txt` ✅ Django 6.0.6
- [x] **Step 3** — `django-admin startproject` and tour the scaffold ✅ `backend/config/` exists
- [x] **Step 4** — First `runserver`, understand WSGI ✅ Rocket page seen
- [x] **Step 5** — `settings.py` walkthrough ✅ `TEMPLATES['DIRS']`, `TIME_ZONE='Asia/Kolkata'`, `STATICFILES_DIRS`, `STATIC_ROOT`, `MEDIA_URL`, `MEDIA_ROOT` all wired
- [x] **Step 5.5** — Git & GitHub industry workflow ✅ `.git/` re-init in project root, `.gitignore`, first commit on `main`, GitHub repo created and pushed, branching strategy + Conventional Commits established
- [x] **Step 6** — Create the `accounts` app ✅ Scaffold (`backend/apps/__init__.py` + `backend/apps/accounts/`) + `name = 'apps.accounts'` + INSTALLED_APPS registration done. Warning `staticfiles.W004` resolved by recreating empty `frontend/static/` + `frontend/templates/`. `manage.py check` returns `no issues`. Two commits already pushed to `feature/accounts-app`.
- [x] **Step 7** — Build the `CustomUser` model with a role field ✅ `AUTH_USER_MODEL = 'accounts.CustomUser'` set in settings.py BEFORE any migration. `CustomUser(AbstractUser)` model with fields: `email` (overridden `unique=True`), `phone` (`CharField(max_length=10)` + Indian-mobile regex validator), `role` (`TextChoices` enum: DOCTOR/RECEPTION/LAB/PATIENT, default PATIENT). `@property phone_with_code` returns `+91XXXXXXXXXX` for SMS APIs. `manage.py check` clean. Two commits pushed to `feature/accounts-app`.
- [x] **Step 8** — Migrations (`makemigrations` vs `migrate`) ✅ `makemigrations accounts` generated `0001_initial.py` (14 columns: 3 ours + 11 inherited from `AbstractUser`, dependency on `auth.0012`). `migrate` applied 19 migrations in order (2 contenttypes + 12 auth + 1 ours + 3 admin + 1 sessions). `backend/db.sqlite3` created with `accounts_customuser` table (NOT `auth_user` — routed via `AUTH_USER_MODEL`). "18 unapplied migrations" warning finally gone. Migration file committed; DB file gitignored.
- [x] **Step 9** — Django admin + superuser ✅ `CustomUser` registered in `backend/apps/accounts/admin.py` via `UserAdmin` subclass (gives password-hashing form, change-password URL, two-form add/edit pattern). `fieldsets` and `add_fieldsets` both APPEND a "Hospital info" section (`role`, `phone`) using tuple concatenation so default auth/permissions/dates sections survive. `list_display`, `list_filter`, `search_fields` configured. First superuser created via `createsuperuser` (email REQUIRED because `unique=True`). Admin login at `/admin/` verified — list page columns, role/staff/active filters, all 5 fieldsets working. Confirmed UTC-in-DB + IST-on-display architecture (`USE_TZ=True` + `TIME_ZONE='Asia/Kolkata'`) is correct, not a bug.
- [x] **Step 10** — URLs and views ✅ New branch `feature/auth-views` created from `main`. Created `backend/apps/accounts/urls.py` with `app_name = 'accounts'` + 3 routes (`login/`, `logout/`, `register/`). Wired root `backend/config/urls.py` to `include('apps.accounts.urls')` under `accounts/` prefix. Wrote placeholder FBV views in `backend/apps/accounts/views.py` returning `HttpResponse('... — coming in Step 12')`. `runserver` verified — all 3 URLs return 200, `/accounts/foo/` returns 404, `/` returns 404 (welcome rocket page gone forever now that we have real routes — expected, not a bug). Two commits pushed: `feat(accounts): add urls.py with login/logout/register routes` + `feat(accounts): add placeholder login/logout/register views`. Tutorial `10-urls-and-views.md` written (9 sections covering request lifecycle, two-level URLconf, `path()` anatomy + converters, `include()` + `app_name` namespacing, `reverse()` / `{% url %}` rule, FBV vs CBV trade-off, `HttpResponse` vs `render()`, browser verification, two-commit split).
- [x] **Step 11** — Templates pointing at `frontend/templates` ✅ `frontend/templates/base.html` written — shared shell with `{% load static %}`, viewport meta, `<title>{% block title %}Smart OPD{% endblock %}</title>`, `{% static 'css/main.css' %}` link, nav with `{% url 'accounts:login' %}` + `{% url 'accounts:register' %}`, `{% block content %}{% endblock %}` hole, footer. Three child templates in `frontend/templates/accounts/` — `login.html` (username + password + Register link), `register.html` (6 fields: username, email, phone with `pattern="[6-9][0-9]{9}"` Indian-mobile UX hint, role dropdown PATIENT/DOCTOR/RECEPTION/LAB, password, password_confirm — note: 4-role dropdown is Step 12 fix-up since production = only PATIENT self-registers, others created by receptionist), `logout.html` (confirmation + two next-action links). All POST forms carry `{% csrf_token %}` (verified via View Source = hidden `csrfmiddlewaretoken` input). `views.py` swapped from `HttpResponse` to `render(request, 'accounts/<name>.html')` for all three views. `runserver` verified — shared header/footer on all 3 pages, `{% url %}` links resolve, no `NoReverseMatch`. Three atomic commits on `feature/auth-views`: `feat(accounts): add base.html template with nav + content block`, `feat(accounts): add login/register/logout templates`, `refactor(accounts): swap placeholder HttpResponse for render() with templates`.
- [x] **Step 12** — Auth forms (login, register, profile) ✅ `RegisterForm(forms.ModelForm)` with `clean_password_confirm()` match validation + `set_password()` hashing in `save()` + hard-coded `role='PATIENT'` (defense layer 3). Four real views: `login_view` (authenticate+login+redirect, bad-creds re-render with error), `register_view` (form save + auto-login), `logout_view` (`@require_POST`, Django 5+ rule), `profile_view` (`@login_required`). Three auth settings wired: `LOGIN_URL='accounts:login'`, `LOGIN_REDIRECT_URL='accounts:profile'`, `LOGOUT_REDIRECT_URL='accounts:login'`. `register.html` locked to PATIENT (dropdown removed, `Meta.fields` excludes role, server-side force) — 3-layer defense in depth. `login.html` + `register.html` both render `{% if form.errors %}` / `{% if error %}` blocks. `profile.html` shows username/role/email/phone + POST logout button. `/` → `RedirectView` to login (Day 8 homepage 404 finally dead). Browser-verified full flow including duplicate-username/email errors via `ModelForm` `unique=True` auto-validation. Four atomic commits pushed: `feat(accounts): add RegisterForm...`, `feat(accounts): wire real login/logout/register/profile views + auth settings`, `refactor(accounts): lock register form to PATIENT role + render form errors`, `feat(config): redirect / to accounts:login`. Tutorial `12-auth-forms.md` written in expert-teacher voice (11 sections). Step 12 spanned 3 sessions (Day 10 teach, Day 11 ~60% code, Day 12 finish).
- [ ] **Step 13** — `appointments` app (models with foreign keys, ORM queries) — **BIG step, chunked 13a → 13d, single branch `feature/appointments-app`, single PR #3 at end (Option A)**
  - [x] **Step 13a** — Scaffold + `Appointment` model + admin + migration ✅ (Day 14, 2026-06-23). New branch `feature/appointments-app` from `main`. `startapp appointments` + `apps.py` patched (`name='apps.appointments'`, `default_auto_field`) + `'apps.appointments'` in `INSTALLED_APPS`. `Appointment` model: 2 FKs to `settings.AUTH_USER_MODEL` — `patient` (CASCADE, `related_name='patient_appointments'`) + `doctor` (PROTECT, `related_name='doctor_appointments'`) — plus `appointment_date` / `time_slot` / `status` (TextChoices PENDING/CONFIRMED/CANCELLED, default PENDING) / `notes` (blank=True) / `created_at` (auto_now_add). `Meta.ordering` + `__str__`. Admin: `list_display`, `list_filter`, `search_fields` with FK traversal, `autocomplete_fields = ('patient','doctor')` (works because `CustomUserAdmin` has `search_fields` from Step 9), `date_hierarchy`. `0001_initial.py` generated + migrated cleanly. Browser-verified. **3 atomic commits** on `feature/appointments-app`: `cd682a4`, `e7cc6c8`, `d139f37`. Tutorial `13-appointments-app.md` covers 13a content only (per Day 14 NEW per-sub-step incremental-tutorial rule).
  - [x] **Step 13b** — Patient-side booking views + URLs + templates ✅ (Day 15, 2026-06-24). `BookAppointmentForm(forms.ModelForm)` — `Meta.fields = ['doctor','appointment_date','time_slot','notes']` (patient + status deliberately excluded — defense in depth), dynamic doctor queryset in `__init__` restricts dropdown to DOCTOR-role users, HTML5 `type=date` + `type=time` widgets for native pickers. Four FBVs: `doctor_list` (queryset + lazy eval), `book_appointment` (GET/POST pattern, `form.save(commit=False)` → `appointment.patient = request.user` → `save()` server-side ownership lock), `my_appointments` (`request.user.patient_appointments.select_related('doctor').all()` — kills N+1, 1 query not N+1), `cancel_appointment` (`@login_required` + `@require_POST` stack, ownership-scoped `get_object_or_404(Appointment, id=..., patient=request.user)` blocks IDOR). `urls.py` with `app_name='appointments'` + 4 named routes; wired under `appointments/` in root URLconf. 3 templates extending `base.html`. Browser-verified full flow (browse → book → list → cancel). **2 atomic commits** on `feature/appointments-app`: `e53da63 feat(appointments): add patient booking views + form + urls`, `e4dd1bf feat(appointments): add patient templates (doctor list, book, my appointments)`. Tutorial 13b appended to `13-appointments-app.md` (9 halves + Day 15 silent-failure typo Gotchas table). Day 15 NEW typo patterns added to memory: lowercase `class meta`, space inside `'appointments: name'`, letter-transposition in URL converter (`appointmetn_id`), missing `%` in `{% url ... }`. All silent at `manage.py check`, all crash at first request.
  - [x] **Step 13c** — Doctor view (today's appointments, cancel) + role-based redirect + role-aware nav ✅ (Day 16, 2026-07-06). `doctor_today` view: `request.user.doctor_appointments.filter(appointment_date=date.today()).select_related('patient')` — reverse FK from doctor side, JOIN patient (page prints patient name). `cancel_appointment` WIDENED — ownership `Q(patient=request.user) | Q(doctor=request.user)` (either party cancels, one endpoint/one auth rule = narrow-waist) + redirect BUG FIX: doctor's `patient_appointments` is empty so old `redirect('appointments:my_appointments')` bounced doctors to blank page — branch `if user.role=='DOCTOR' → doctor_today else my_appointments`. `login_view` role-aware: DOCTOR → `appointments:doctor_today`, else `accounts:profile`. `base.html` nav role-aware (`{% if user.is_authenticated %}` + role branch — patient sees Find-a-Doctor + My-Appointments, doctor sees Today's-Appointments, both Profile + POST-logout). **Design: dashboard = nav links for now**, real dashboard page deferred to Step 15+ when doctor gets availability/prescriptions/lab. New route `doctor/today/`. New template `doctor_today.html`. Browser-verified doctor + patient flows + cross-party cancel. **2 atomic commits**: `ece0c99 feat(appointments): add doctor today view + widen cancel to patient-or-doctor`, `3586cf4 feat(accounts): role-based login redirect + role-aware nav`. Day 16 NEW typo patterns: enum-vs-field casing (`Model.Status.X` vs `Model.status`), namespace singular/plural (`appointment:` vs `appointments:`), wrong-namespace on shared name (`profile` is `accounts` not `appointments`), add-without-delete (duplicate `<nav>`). Session-persistence non-bug diagnosed + self-resolved (login page showed auth nav because session cookie still valid — not a bypass).
  - [x] **Step 13d** — Receptionist book-on-behalf + global appointment list + filters + confirm action ✅ (Day 17, 2026-07-09). `ReceptionBookingForm(forms.ModelForm)` — EXPOSES `patient` in `Meta.fields` (the field patient/doctor forms hide; reception books on behalf) + dynamic dual querysets in `__init__` (patient→PATIENT, doctor→DOCTOR). `reception_book` view role-gated (`if role != 'RECEPTION': raise Http404`), `form.save()` direct (no commit=False — patient is on the form). `confirm_appointment` view (`@require_POST`, `PENDING → CONFIRMED`, guard on from-state) — reception any row / doctor own (`doctor=request.user`); patient's `doctor=me` lookup 404s so patients can't confirm (no explicit block). `appointment_list` view — role-gated, UNSCOPED `Appointment.objects.select_related('patient','doctor')`, conditional GET-param filters (status/doctor/date via `request.GET.get()` + `if` chain — no django-filter dep). `cancel_appointment` widened 3rd time (reception any). Shared `_redirect_after_action(request)` helper (reception→list, doctor→today, patient→mine) — extracted because redirect IS identical across cancel+confirm; lookup NOT extracted because scopes diverge. `login_view` RECEPTION → `appointments:appointment_list`. `base.html` reception nav branch. Accept button on PENDING rows (doctor_today + appointment_list). New routes `reception/book/`, `confirm/<int:id>/`, `all/`. Browser-verified all roles + role-gate 404s. **3 atomic commits**: `851b11a`, `3a6a353`, `8cd7e94`. Day 17 typos: view-name plural/singular mismatch (`confirm_appointments` vs URL `confirm_appointment`), `erros` (missing r → silent empty render). **STEP 13 COMPLETE → PR #3.**
- [x] **Step 13e** — Appointment lifecycle + doctor time-split views ✅ (Days 18–19, 2026-07-09/10, branch `feature/appointments-lifecycle` → PR #4). **13e-i**: `Status` += `COMPLETED` (migration 0002) + `NO_SHOW` (migration 0003, user-requested mid-session) — both `AlterField` (choices change = migration even though SQLite column unchanged). `complete_appointment` + `no_show_appointment` views (`@require_POST`, `CONFIRMED →` terminal, reception any / doctor own, from-state guard, `_redirect_after_action`). Routes `complete/<int:id>/` + `no-show/<int:id>/`. Terminal-state-aware buttons (PENDING→Accept+Cancel, CONFIRMED→Complete+No-show+Cancel, terminal→dash) in doctor_today + appointment_list; user-caught bug in my_appointments patient cancel (`!= CANCELLED` → `== PENDING or == CONFIRMED`). Lifecycle final: 3 terminal states (COMPLETED/NO_SHOW/CANCELLED). **13e-ii**: `doctor_history` (`appointment_date__lte=today`, Meta ordering newest-first) + `doctor_upcoming` (`__gt=today`, `order_by` soonest-first override) — `<=`/`>` partition calendar, today lands in history. 2 templates (+Date column; upcoming CONFIRMED = Cancel only — can't complete future visit) + 2 doctor nav links. Concepts: `__lte`/`__gt` lookups (field-vs-operator after `__`). **5 feat commits**: `a3a64c5`, `debc235`, `d8721db` (13e-i) + `2cf0acc`, `aa669ae` (13e-ii). Days 18–19 typo patterns NEW: context-dict key misspelling (`'appiontments'` → silently empty page), `<form action="post"` duplicate-attribute (browser keeps first action → GET to literal "post" URL). Tutorial `13e-appointments-lifecycle.md` (all 13e in one write per Day 18 user override). Browser-verified.
- [ ] **Step 14** — DRF layer, chunked 14a → 14d, branch `feature/drf-api` → PR #5
  - [x] **Step 14a** — Double-booking prevention ✅ (Day 20, 2026-07-11). Branch openers: already-authenticated guard on login/register (inline `if request.user.is_authenticated: redirect` — user first tried `@login_required` on login_view = infinite redirect loop, caught before commit) + `appointments/` URL-prefix pluralization (zero breakage — all links via `{% url %}`). `UniqueConstraint(fields=['doctor','appointment_date','time_slot'], condition=~Q(status='CANCELLED'), name='unique_doctor_slot', violation_error_message=...)` in `Appointment.Meta` → migration `0004` (failed first on existing duplicate rows — cleaned via admin, re-ran). **Django subtlety discovered**: conditional constraint referencing non-form field (`status`) is SILENTLY SKIPPED by ModelForm validation (FieldError swallowed) → duplicate booking gave 500 IntegrityError not form error. Fix: shared `_validate_slot_free(cleaned_data)` helper (`.exists()` query mirroring constraint) + form-wide `clean()` in both booking forms. Known ceiling: same-second race still 500s, DB constraint catches it. Browser-verified: duplicate → red error, cancelled slot → re-bookable. Session-persistence question answered (DB-backed sessions + new guard = auto-land on profile). **Zero typos in user-typed code — first clean sheet.** Commits: `1d2c55d` (guard), `8e32b50` (prefix), + constraint/forms commit. Tutorial `14-drf-api.md` NEW (14a section).
  - [x] **Step 14b** — Install DRF + first serializer ✅ (Day 21, 2026-07-12). `pip install djangorestframework` (3.17.1) + froze `requirements.txt` + `'rest_framework'` in INSTALLED_APPS. `AppointmentSerializer(serializers.ModelSerializer)` in NEW `backend/apps/appointments/serializers.py` (kept in appointments app, NOT a separate `api/` app — one serializer doesn't justify it). `read_only_fields = ['id','status','created_at']` (status only moves via lifecycle views; id/created_at server-owned). FKs serialize as IDs by default. Shell-tested before any view: `AppointmentSerializer(Appointment.objects.first()).data` → correct JSON dict (patient/doctor as PK ints, status PENDING, created_at ISO+05:30 IST). 2 commits: `chore(api): install djangorestframework + ignore local status file`, `feat(api): add AppointmentSerializer`. Concept: serializer = ModelForm-for-JSON (same Meta shape; `validate_<f>`/`validate` mirror `clean_<f>`/`clean`). Tutorial 14b appended.
  - [x] **Step 14c** — Role-scoped `AppointmentViewSet` + router ✅ (Day 22, 2026-07-13). **Structure decision (user-driven)**: created a DEDICATED `api` app (`backend/apps/api/` — views.py + urls.py) instead of per-app API files; user wanted industry-standard org-by-layer (see [[feedback-architecture-preference]]). `api` app owns viewsets + router; each feature app keeps its serializer (`appointments/serializers.py`). `AppointmentViewSet(viewsets.ModelViewSet)` — `serializer_class` + `permission_classes=[IsAuthenticated]` + `get_queryset()` role-branch (reception all / doctor own via doctor_appointments / patient own via patient_appointments, all select_related) + `perform_create(serializer.save(patient=self.request.user))`. `DefaultRouter().register('appointments', AppointmentViewSet, basename='appointment')` in `api/urls.py`; mounted `path('api/', include('apps.api.urls'))`. Mount stays `/api/` (no v1 — user call). Browsable API verified all 5 cases (anon 403, patient/doctor/reception scoped lists, other-id 404 via get_queryset). Concepts: ViewSet=5 CRUD from one class (override hooks only), get_queryset scopes list+retrieve (retrieve IDOR-safe for free), router auto-routes, `basename` REQUIRED when overriding get_queryset (no queryset attr to infer from), browsable API + content negotiation (Accept header picks HTML vs JSON). **Day 22 typos**: `router.register(..., 'AppointmentViewSet', ...)` (quoted class = str → `AttributeError: 'str' has no get_extra_actions` at import), `user.roel` (→ AttributeError at request). NEW grep entry: attribute names on request.user/model instances. Commit `a3b207e`.
  - [x] **Step 14d** — SimpleJWT token auth ✅ (Day 23, 2026-07-14). `pip install djangorestframework-simplejwt`. `REST_FRAMEWORK` settings block: `DEFAULT_AUTHENTICATION_CLASSES` = (JWTAuthentication, SessionAuthentication) — JWT first for API clients, Session kept for browsable API; `DEFAULT_PERMISSION_CLASSES` = (IsAuthenticated,) global. `TokenObtainPairView` `/api/token/` + `TokenRefreshView` `/api/token/refresh/` in `api/urls.py` (SimpleJWT built-in views, zero code). Verified full flow via curl (Git Bash 2nd terminal): POST creds → access+refresh; `Authorization: Bearer <access>` on `/api/appointments/` → scoped JSON from cookieless client; no header → 401. Concepts: JWT stateless (signed user-id in token, no DB session lookup) vs session (DB row each req); access short/high-exposure + refresh long/low-exposure pair. **django-filter DECISION: SKIPPED** (YAGNI — API list already role-scoped, no client needs filtering; add FilterSet to api viewset if ever needed). Typo: `token/refresh` missing trailing slash (POST can't APPEND_SLASH-redirect → would 404). Commit `9a2eeae`.
  - [x] **Step 14e** — drf-spectacular auto API docs ✅ (Day 23, 2026-07-14). `pip install drf-spectacular` + `'drf_spectacular'` in INSTALLED_APPS + `'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema'` in REST_FRAMEWORK. 3 routes in `api/urls.py`: `schema/` (SpectacularAPIView — raw OpenAPI YAML), `docs/` (SpectacularSwaggerView — interactive Swagger UI, README screenshot), `redoc/` (SpectacularRedocView). Introspects serializers+viewsets → all endpoints auto-listed. Browser-verified `/api/docs/` renders all routes. **STEP 14 COMPLETE (14a–14e) → PR #5.**
- [ ] **Step 15** — `lab`, `prescriptions`, `notifications` apps
- [ ] **Step 16** — Celery + Redis for background tasks. **USER-REQUESTED (Day 18)**: time-based auto-transitions via Celery Beat — stale PENDING past its slot → CANCELLED (or new EXPIRED/NO_SHOW status). NOTE: do NOT auto-complete CONFIRMED (confirmed ≠ visited; no-show would be falsely "completed") — humans mark Complete manually (13e-i).
- [ ] **Step 17** — Whitenoise, static & media in production
- [ ] **Step 18** — Render deploy

### Day 1 recap (2026-06-06)

Steps 1–5 complete. Local Django app runs cleanly. Settings wired to `frontend/templates`, `frontend/static`, `backend/media`, Indian timezone. Tutorial files written: `tutorial/01-python-venv.md` through `tutorial/05-settings.md`.

### Day 2 recap (2026-06-09)

- Step 5.5 done — Git workflow tutorial written, repo pushed to GitHub, branching strategy locked in. User did the `.git/` cleanup + re-init themselves (misplaced `.git/` at home folder caused `git status` to list the entire user profile).
- Empty-folder gotcha — chose Option 2 (no `.gitkeep`); empty `frontend/templates/` and `frontend/static/` exist locally only to silence `staticfiles.W004`; subfolders will appear on GitHub when real Stitch templates arrive.
- Step 6 started on `feature/accounts-app` branch. Scaffold + INSTALLED_APPS done. `manage.py check` flagged **1 issue** — text not yet captured. Commits + push to branch still pending.

### Day 3 recap (2026-06-10)

- `staticfiles.W004` warning fixed — recreated empty `frontend/templates/` + `frontend/static/`. `manage.py check` now clean (`no issues`).
- Confirmed `default_auto_field = 'django.db.models.BigAutoField'` was missing from `apps.py` (Django 6 / `startapp` quirk). User added it manually — correct convention.
- Tutorial `tutorial/06-accounts-app.md` written. `tutorial/README.md` index updated.
- Step 6 officially closed.

### Day 4 recap (2026-06-11)

- Step 7 done in a 45-min session.
- `AUTH_USER_MODEL` set in settings.py BEFORE any migration (critical sequencing).
- `CustomUser(AbstractUser)` with `email` (unique), `phone` (10-digit Indian, regex-validated), `role` (TextChoices: DOCTOR/RECEPTION/LAB/PATIENT, default PATIENT).
- User asked about email/phone fields proactively (good instinct) — added `phone_with_code` property to return `+91XXXXXXXXXX` for SMS APIs without polluting the DB column.
- User asked about Indian-only mobile format — added `^[6-9]\d{9}$` regex validator (TRAI rule: Indian mobile numbers start with 6/7/8/9, exactly 10 digits).
- Two commits pushed to `feature/accounts-app`. Tutorial `07-custom-user.md` written. CLAUDE.md + tutorial/README.md updated.

### Day 5 recap (2026-06-12)

- Step 8 done in a short session.
- `makemigrations accounts` → generated `0001_initial.py` (14 columns: 11 inherited from `AbstractUser` + 3 ours: `email` unique, `phone` with regex, `role` TextChoices).
- Walked through the migration file in detail — dependency on `auth.0012`, the `CreateModel` operation, the `UserManager` attachment that gives us `objects.create_user()` and `objects.create_superuser()` for free.
- `migrate` → applied 19 migrations in dependency order. `backend/db.sqlite3` (135 KB) created. Confirmed `db.sqlite3` is invisible to `git status` (gitignored), only the migration file appears.
- Migration committed with `feat(accounts): add initial migration for CustomUser table` and pushed.
- "18 unapplied migrations" warning from Step 4 is finally gone forever.

### Day 6 recap (2026-06-13)

- Step 9 done. `backend/apps/accounts/admin.py` written: subclassed `UserAdmin` (not `ModelAdmin` — critical for password hashing); appended `'Hospital info'` section to both `fieldsets` (edit form) and `add_fieldsets` (create form) using tuple concatenation so default sections survive; set `list_display = ('username','email','role','phone','is_staff')`, `list_filter = ('role','is_staff','is_active')`, `search_fields = ('username','email','phone')`.
- First superuser created via `python manage.py createsuperuser`. Email now REQUIRED (because `unique=True`). Credentials live in gitignored `db.sqlite3` — never reach Git.
- Admin login at `/admin/` verified — list page columns, sidebar filters, all 5 fieldsets ("auth / personal / permissions / important dates / Hospital info") all rendering correctly.
- **Timezone gotcha solved by understanding, not by changing anything.** User noticed DB `last_login` showed `17:49 UTC` while wall clock said `23:26 IST`. The 5h30m offset = IST = UTC + 5:30. Django stores UTC in DB (because `USE_TZ=True`) and renders in `TIME_ZONE='Asia/Kolkata'` (admin's "Important dates" section confirmed). Industry-standard architecture — never change either setting (would break Celery 24-hour reminder in Step 16).
- One commit pushed: `feat(accounts): register CustomUser in admin with role+phone fieldsets`.
- Tutorial `09-admin-superuser.md` written. Index + roadmap updated.
- **Minor typo to fix:** line 11 of `admin.py` has `'Hopital info'` (missing `s`) — cosmetic but inconsistent with line 13's `'Hospital info'`. Will get a small `fix(accounts):` commit before opening the PR.

### Day 7 recap (2026-06-14) — FIRST PULL REQUEST MERGED 🎯

- Final Step 9 polish: tutorial `09-admin-superuser.md` written (8 sections: why admin, superuser bootstrap, `is_superuser` vs `role`, `UserAdmin` vs `ModelAdmin`, admin file line-by-line, `fieldsets` vs `add_fieldsets`, UTC-vs-IST timestamp architecture, verify + commit + gotchas).
- Docs commit landed: `docs(step-9): tutorial + roadmap mark admin+superuser complete`.
- `'Hopital info'` typo on line 11 of `admin.py` corrected → `'Hospital info'`. User did this as a `--amend` + force-push to the existing `feat(accounts):` commit instead of a separate `fix(accounts):` commit — granular history slightly compressed but result is clean.
- **First Pull Request opened, reviewed, merged.** Title: `feat(accounts): CustomUser model + admin + migration`. PR #1. Squash-or-merge: default "Create a merge commit". Result on `main`: `ca987d5 Merge pull request #1 from prince220504/feature/accounts-app`. All 7 branch commits (Steps 6 → 9 + AUTH_USER_MODEL + typo fix) now in `main`'s history.
- Local sync: `git checkout main && git pull` brought the merge commit + fast-forward down.
- Branch cleanup: `git branch -d feature/accounts-app` (local) + `git push origin --delete feature/accounts-app` (remote) — both succeeded cleanly. `git branch -a` now shows only `main` and `remotes/origin/main`.
- **This was the user's first-ever PR.** Zero errors, full flow followed (branch → push → PR → review own diff → merge → confirm → sync local → delete branch). The accounts module is officially feature-complete and merged.
- Session ended early to mark the milestone — user explicitly chose to start Step 10 fresh tomorrow rather than push on.

### Day 8 recap (2026-06-15)

- Branch `feature/auth-views` created from `main`. Step 10 done in one focused session.
- **Concept teach FIRST** (per Day 8 resume plan): full request lifecycle diagram + URLconf tree (root → app via `include()`) + `path()` converters + `app_name` namespacing + `reverse()`/`{% url %}` rule + FBV vs CBV trade-off. User answered concept-check questions afterwards (Q1 + Q2 wrong, Q3 right) — re-reading caught both. Good honest feedback loop.
- Code: created `backend/apps/accounts/urls.py` with `app_name='accounts'` + 3 routes. Wired `backend/config/urls.py` with `include('apps.accounts.urls')` under `accounts/` prefix. Replaced empty `views.py` boilerplate with 3 FBV placeholders returning `HttpResponse('... — coming in Step 12')`.
- Verified all 3 URLs return 200 + `/accounts/foo/` returns 404. User asked the great diagnostic question "why does `/` return 404 now?" — explained the welcome-rocket-only-when-empty-URLconf rule (it's gone forever now, expected, not a bug). Logged this as a curiosity-pattern moment.
- Three commits pushed to `feature/auth-views`: `feat(accounts): add urls.py with login/logout/register routes`, `feat(accounts): add placeholder login/logout/register views`, `docs(step-10): tutorial + roadmap mark URLs and views complete`. Minor typos in two feat commit messages (`logout.register`, `logour`) left as-is — cosmetic, low cost to keep history honest rather than force-push.
- Tutorial `10-urls-and-views.md` written (9 sections covering request lifecycle, two-level URLconf, `path()` anatomy, `include()` + `app_name`, `reverse()`/`{% url %}` rule, FBV vs CBV, `HttpResponse` vs `render()`, browser verification, two-commit split).
- Session ended after Step 10 — user explicitly chose to stop here and resume Step 11 fresh next session.

### Day 9 recap (2026-06-18)

- Step 11 done across one session (taught concepts first, then code in 3 commits).
- **Concept teach FIRST**: `TEMPLATES['DIRS']` (already wired Step 5), template inheritance (`{% extends %}` + `{% block %}`), `{% url %}` tag (never-hardcode rule from Step 10 carried forward), `{% load static %}` + `{% static %}`, `{% csrf_token %}` (CSRF attack story explained — hidden input + cookie double-check), context dict shape.
- Concept-check answered: Q1 partial (got folder direction right, missed `templates/` subfolder), Q2 right (URL-rename tolerance), Q3 partial (CSRF intent right but mixed up "attacker reads cookie" with Django's 403 rejection mechanic). Re-reading caught both gaps.
- Files: `frontend/templates/base.html` (CLEAN — 2 typos caught + fixed: `device-widht`, `Mangement`), `frontend/templates/accounts/login.html` (CLEAN — 2 typos caught + fixed: `mehtod`, stray apostrophe in `type="'text"`), `frontend/templates/accounts/register.html` (had 5 typos — leading `-` on extends, stray apostrophes in 3 attributes, `{% url 'accounts:login %'}` quote placement — user fixed 4, Claude fixed line 12 via Edit), `frontend/templates/accounts/logout.html` (CLEAN — zero typos). `views.py` swap from `HttpResponse` to `render()` had 1 typo (`account/register.html` missing `s`) — user caught + fixed before Claude could Edit.
- **Typo pattern observed Day 9**: stray apostrophes from IDE autocomplete (Antigravity quirk). Expect when pair-typing HTML with quoted attributes.
- Three atomic commits on `feature/auth-views`: `feat(accounts): add base.html template with nav + content block`, `feat(accounts): add login/register/logout templates`, `refactor(accounts): swap placeholder HttpResponse for render() with templates`. User initially said "wrap for today, don't commit partial work" — decision pattern noted: full-step commits over WIP commits. Then user changed mind and pushed through to commits same session.
- Tutorial `11-templates.md` written in **simpler language with concrete examples** per explicit user feedback ("from past few learning you are using every diffcult word and language for teaching i want you use some easy word and language while teaching and give examples for clartiy and better understanding"). 9 sections: what a template is, why `frontend/templates/` (settings lookup), shared shell idea (block/extends with diagram), `base.html` line by line, the 3 child templates, `{% csrf_token %}` in 60 seconds (attack story, then defense), `HttpResponse` vs `render()` + context dict bridge, browser verification checklist, three-commit split + why `refactor` not `feat` for commit 3.
- **Known security flaw flagged for Step 12**: `register.html` exposes all 4 role options in dropdown. Real flow = only PATIENT self-registers; doctors/reception/lab created by receptionist via admin. Will be fixed alongside auth form Python in Step 12.

### Day 10 partial recap (2026-06-19)

- Branch `feature/auth-views`, clean tree, last commit `175ad6f docs: claude.md`.
- All 8 Step 12 concepts taught in **expert-teacher voice** (Day 9 refined rule applied — real Django terms + worked examples + "why it matters" closer): `authenticate()`/`login()` split, password hashing (PBKDF2 + `set_password`/`check_password`), sessions (session key + `django_session` table + `SessionMiddleware`), `forms.Form` vs `forms.ModelForm`, `clean_<fieldname>()` hook, `@login_required` decorator, role-based redirect (`_role_home_url()` helper + `LoginView.get_success_url()` for CBV), **lock register to PATIENT in two layers** (HTML drop + server-side `user.role='PATIENT'` force in `RegisterForm.save()`).
- Two concept-check rounds, 6 questions. 5 right + 1 mechanic-wrong (Q2 round-2: user thinks `return confirm` prevents the password mismatch — actually the `if password != confirm` block detects mismatch; the `return` is Django's form contract that REPLACES `cleaned_data['X']` with the returned value. Forget the return → silent data loss). Same "right intent, wrong mechanic" pattern as Day 9 CSRF Q3. Flagged to re-explain Day 11 before writing `forms.py`.
- **NO CODE WRITTEN.** Working tree stays clean per full-step-commits rule. User stopped session because of other work after concept teach landed.
- Code phase pending (Day 11): `forms.py`, `views.py` rewrite, `register.html` PATIENT-lock, `login.html` errors, `config/urls.py` homepage redirect, 4 commits, tutorial `12-auth-forms.md` (early-Steps voice), docs commit, PR #2.

### Teaching adjustment noted Day 10

"Right intent, wrong mechanic" pattern hit twice now (Day 9 CSRF, Day 10 `clean_X` return). User absorbs the GOAL of a feature on first pass but loses the GEARS. **When explaining a mechanism from now on, spend an extra sentence on "what physically happens in memory/db/network when this fires"**. Don't only say "this prevents X" — say "this prevents X by physically doing Y at moment Z". The mechanic sticks when the user can mentally animate it.

### Day 11 resume point

1. Open Claude Code in project folder. This file auto-loads. Confirm on `feature/auth-views` (`git branch` shows `* feature/auth-views`). Clean tree.
2. **5-minute concept refresher** — quick recap via the Concept → Code-that-uses-it mapping table from Day 10 teach. User reads, confirms still loaded.
3. **Targeted re-explain `clean_X` return mechanic** (Day 10 Q2 round-2 was wrong). Show pseudocode `cleaned_data['password_confirm'] = self.clean_password_confirm()` — return value is what Django writes back; forget = `None`. Must land before writing the method.
4. **Step 12 — Auth forms (login, register, profile).** Add real Python logic behind the HTML forms from Step 11.
   - Teach concepts FIRST (use **simple language + concrete examples** per Day 9 feedback):
     - `django.contrib.auth.authenticate()` and `login()` — what each does, why they're separate.
     - Password hashing — never store plain passwords; Django uses PBKDF2 by default.
     - Sessions — how Django remembers "this browser is Prince" after login (signed cookie + session table).
     - Django Forms vs ModelForms — `RegisterForm(forms.ModelForm)` for the CustomUser create flow.
     - `@login_required` decorator — gate views that need auth.
     - `LoginView` and `LogoutView` CBVs — when to subclass vs hand-roll.
     - **Role-based redirect after login** — override `get_success_url()` to branch on `request.user.role` → `/doctor/`, `/reception/`, `/lab/`, `/patient/`.
     - **Restrict register dropdown to PATIENT only** — production flow = only patients self-register; staff accounts created by receptionist via admin.
   - Then code:
     - `backend/apps/accounts/forms.py` — new file. `RegisterForm(forms.ModelForm)` with username/email/phone/password/password_confirm; `clean_password_confirm()` for match check; `save(commit=False)` to hash password via `set_password()`. Force `role = 'PATIENT'` in save — ignore any role posted from the dropdown.
     - `backend/apps/accounts/views.py` — swap `login_view` to subclass `LoginView` (or keep FBV using `authenticate()` + `login()`). Add real `register_view` FBV that handles GET (render form) + POST (validate + save + auto-login). Add `@login_required` to wherever profile lands.
     - `backend/apps/accounts/urls.py` — possibly add profile route.
     - Update `register.html` — drop the role dropdown OR lock it to read-only Patient. Add `{{ form.errors }}` rendering.
     - Update `login.html` — render `{{ form.errors }}` for bad credentials.
     - Optionally add a logout POST flow (Django 5+ requires POST for logout).
   - Wire homepage `/` → `RedirectView` to `accounts:login` while we're at it (Day 8 noted `/` returns 404 — fixable now).
3. Verify in browser: register a new PATIENT, log in with those credentials, see them in `/admin/` with role=PATIENT and a hashed password.
4. Expected commits on `feature/auth-views`:
   - `feat(accounts): add RegisterForm with password hashing + match validation`
   - `feat(accounts): wire real login/logout/register views`
   - `refactor(accounts): lock register form to PATIENT role (security)`
   - `feat(config): redirect / to accounts:login`
5. End with `tutorial/12-auth-forms.md` (use **simple language + worked examples** per Day 9 feedback) + index update + roadmap update + docs commit.
6. **After Step 12, OPEN PR #2** — the entire auth module is now mergeable as one unit (URLs + views + templates + forms + Python auth logic).
7. After PR #2 merge: delete `feature/auth-views` local + remote, sync `main`, start Step 13 (`appointments` app) on new branch `feature/appointments-app`.

### Day 11 partial recap (2026-06-20) — Step 12 Python phase ~60% done

- Branch `feature/auth-views`, working tree DIRTY (4 files modified, nothing committed). Per Day 9 full-step-commits rule — leave as-is overnight.
- 5-min concept refresher delivered (Concept → Code-that-uses-it mapping table). Targeted re-explain of `clean_X()` return mechanic (Day 10 Q2 round-2 gap) BEFORE writing `clean_password_confirm()` — user got it right in the file. Mechanic gap closed.
- **`backend/apps/accounts/forms.py`** (NEW, CLEAN) — `RegisterForm(forms.ModelForm)`. `password` + `password_confirm` declared manually with `widget=forms.PasswordInput`. `Meta.fields = ['username','email','phone']` (role excluded — defense layer zero). `clean_password_confirm()` with mandatory `return confirm`. `save()` overridden: `super().save(commit=False)` → `set_password()` (hash) → `user.role = 'PATIENT'` (force, server-side) → `if commit: user.save()` → `return user`. One typo caught + fixed during typing (`'usename'` → `'username'`).
- **`backend/apps/accounts/views.py`** (REWRITTEN, has 1 TYPO) — `login_view` (authenticate + login + redirect, bad-creds re-render with `{'error': ...}`), `register_view` (RegisterForm POST → save → auto-login), `logout_view` (`@require_POST`, logout + redirect), `profile_view` (`@login_required`, renders `'accounts/profiel.html'` ← **TYPO, should be `profile.html`**, will 500 after login redirect).
- **`backend/apps/accounts/urls.py`** (MODIFIED, CLEAN but collapsed to 1 line) — added `path('profile/', views.profile_view, name='profile')`. Cosmetic ugliness, not broken.
- **`backend/config/settings.py`** (MODIFIED, has 1 BREAKING TYPO) — added `LOGIN_URL = 'accounts:login'` + `LOGIN_REDIRECT_URL = 'accounts:profile'` + (intended) `LOGOUT_REDIRECT_URL = 'accounts:login'`. User typed `LOGIN_REDIRECT_URL` TWICE — second instance overwrites first. **Effect**: login redirect goes to `accounts:login` not `profile`. Day 12 must rename the 3rd line to `LOGOUT_REDIRECT_URL`.
- **2 typos must be fixed before runserver verify** — both flagged in `[[project-opd-progress]]` Day 11 partial section.

### Day 11 scope signal
User wrapped saying "this step 12 way big from my thinking". Step 12 is now spanning 3 sessions (Day 10 teach, Day 11 ~60% code, Day 12 finish). For Step 13 (appointments — also multi-file + multi-concept), pre-warn that scope likely splits across 2-3 sessions and offer sub-step split (13a models, 13b views, 13c forms) before starting. Honor session-length limits over arbitrary step boundaries.

### Day 12 recap (2026-06-21) — STEP 12 COMPLETE, PR #2 READY

- **First 5 min**: fixed 2 Day-11 typos. `backend/apps/accounts/views.py:38` `'accounts/profiel.html'` → `'accounts/profile.html'`. `backend/config/settings.py` second `LOGIN_REDIRECT_URL` → `LOGOUT_REDIRECT_URL`. Verified via `git diff`.
- **`register.html` PATIENT lock + form.errors block**: user dropped 4-role `<select>` block, typed `<p>Account type: <strong>Patient</strong></p>`. Typed `{% if form.errors %}` loop. **Two typos caught by Claude** (`form.error` → `form.errors`, `form.errors.item` → `form.errors.items`) — both silent failures (loop would render nothing). Fixed via Edit.
- **`login.html` error render**: user typed `{% if error %}<p style="color:red;">{{error}}</p>{% endif %}` above form. Clean — zero typos.
- **`profile.html` created**: user typed extends + welcome + role/email/phone + POST logout form with `{% csrf_token %}`. Clean — zero typos.
- **`backend/config/urls.py`**: user typed `from django.views.generic import RedirectView` import + `path('', RedirectView.as_view(url='/accounts/login/'))` route. Clean (missing trailing comma on last list item — Python tolerates, style nit only).
- **Browser verify — ALL PASS** (10/10):
  - `/` → 302 → login. Register flow → auto-login → profile shows username + role=PATIENT. POST logout works. Wrong password shows red error. Correct creds → profile. `/admin/` shows `pbkdf2_sha256$...` hash + role=PATIENT. Mismatched passwords show `password_confirm: Passwords don't match`. `/profile/` while logged out → `?next=...` bounce. **Bonus**: duplicate username/email errors ALSO render (ModelForm auto-validates `unique=True`).
- **4 atomic commits pushed** (HEAD `8b11ed8`):
  - `bdbfee6 feat(accounts): add RegisterForm with password hashing + match validation` (forms.py)
  - `ef2ebc7 feat(accounts): wire real login/logout/register/profile views + auth settings` (views.py + urls.py accounts + settings.py + profile.html)
  - `d249d06 refactor(accounts): lock register form to PATIENT role + render form errors` (register.html + login.html)
  - `8b11ed8 feat(config): redirect / to accounts:login` (config/urls.py)
- **Tutorial `12-auth-forms.md` written** in expert-teacher voice (`07-custom-user.md` voice anchor). 11 sections: `authenticate`/`login` split, PBKDF2 hashing + cardinal rule, sessions in 60s + HttpOnly cookie, `ModelForm` + `clean_X` hook + return contract, `@login_required`/`@require_POST` decorators, 3-layer PATIENT defense in depth, 4 views walkthrough, auth settings, `RedirectView`, browser verify (10-step checklist), 4-commit split with rationale. Includes Gotchas + "Where each future feature plugs in" + 3-line Revise.
- **Typo pattern Day 12**: 2 typos in user-typed `form.errors` block — `.error` (missing s), `.item` (missing s). Silent-failure category — page renders fine but feature dead. Same IDE-quirk pattern flagged Day 9 still active. Claude must read user-typed template loops carefully — Django won't crash on missing attr / wrong method name, just renders empty.
- **Pending Day 12 (still to do)**: docs commit (`docs(step-12): tutorial + roadmap mark auth forms complete`) + push + **OPEN PR #2** + merge + delete `feature/auth-views` local+remote + sync `main`.

### Day 13 resume point

1. Confirm PR #2 merged, on `main`, `git pull` synced, `feature/auth-views` deleted local + remote.
2. **Step 13 sub-step plan** (per Day 11 scope-signal note — Step 13 is multi-file, multi-concept, will likely span 2-3 sessions): pre-warn user, offer split before starting.
   - **13a**: `appointments` app scaffold + `Appointment` model with `ForeignKey` (Patient, Doctor) + `Availability` model + migrations. Teach: ORM, `ForeignKey`, `related_name`, `on_delete`, `Meta.ordering`, `__str__`.
   - **13b**: views (doctor: see today's appointments / cancel; patient: book; receptionist: book-on-behalf) + URL routing per role. Teach: querysets, `filter`/`exclude`/`get`, `Q` objects, `select_related` to avoid N+1.
   - **13c**: forms + templates for booking flow + role-based redirect after login (override `login_view` to branch on `user.role` → `/doctor/`, `/reception/`, `/lab/`, `/patient/`). Teach: dynamic form choices, model-bound forms with FK fields.
3. New branch `feature/appointments-app` from `main`.
4. Maintain expert-teacher voice (Day 9 refined rule) + "what physically happens" mechanic detail (Day 10 teaching adjustment).

### Day 13 recap (2026-06-22) — PR #2 MERGED + chunking rule established

- **PR #2 merged** via GitHub web UI. URL: https://github.com/prince220504/Smart-Opd-Managment-System/pull/2. Merge commit `5447b75` landed on `main`. All 5 commits from `feature/auth-views` (4 feat + 1 docs) now in main's history.
- **Local cleanup**: `git checkout main && git pull && git branch -d feature/auth-views && git push origin --delete feature/auth-views`. `git branch -a` clean (only `main` + `remotes/origin/main`).
- **Step 12 officially shipped.** Full auth module live: register → login → logout → profile + 3-layer PATIENT lock + `/` → login redirect + 11-section tutorial.
- **NEW DURABLE RULE — step chunking** (full rule block at "Step chunking rule" section below; also saved as memory `feedback_step_chunking.md`). Triggered after Step 12 ran 3 sessions (Day 10 teach, Day 11 ~60% code, Day 12 finish). Verbatim user statement: *"we already step 12 has too much thing in one step so from now maybe every step should be that big ? right if right then we should work according to that ok so first we note how much we work in single day apporx 1 to 1:30 hour we work on this project so based on this we disturibates our steps in small part... this chunks thing only apply to big steps if in future any step come which is not big as step 12 or 13 then we dont do this chunks thing... we make sub step in way that it got complete in 1 hr or 1:30 hr ok"*. **Option A** chosen for branch/PR strategy: one branch + one PR per parent step (NOT per sub-step). User reasoning: *"pull require time"*. BIG step definition: 4+ files OR 5+ concepts OR 2+ hrs OR multi-feature. Pre-session scope check + hard stop at 1:30 budget enforced.
- **Step 13a scope AGREED** for next session (~1:15 hr): app scaffold + `Appointment` model + admin + migration. 3 concepts (`ForeignKey`/`related_name`/`on_delete`). 3 atomic commits on new branch `feature/appointments-app`. NOT in 13a: `Availability` model, views, templates, booking forms.
- CLAUDE.md updated with chunking rule block but docs commit deferred — user wrapped Day 13 before pushing it. Day 14 first action.

### Day 14 recap (2026-06-23) — STEP 13a SHIPPED + incremental tutorial rule

- **First action**: Day 13's pending docs commit shipped: `a8f0666 docs: add step chunking rule for big steps (1-1:30 hr sub-steps)` on `main`. New branch `feature/appointments-app` created from `main` at that HEAD.
- **Scaffold (commit `cd682a4 feat(appointments): scaffold app + register in INSTALLED_APPS`)**: `python manage.py startapp appointments` inside `backend/apps/`. Patched `apps.py` — added `default_auto_field = 'django.db.models.BigAutoField'` + changed `name = 'apps.appointments'` (dotted import path so Django resolves the app under `backend/apps/`). User initially typed `'django.db.models/BigAutoField'` (slash instead of dot) — caught + fixed. `'apps.appointments'` added to `INSTALLED_APPS` right after `'apps.accounts'`. `manage.py check` returned `System check identified no issues (0 silenced).`
- **`Appointment` model (commit `e7cc6c8 feat(appointments): add Appointments model with revertable unit`)** — 5 fields + Status enum + Meta.ordering + `__str__`:
  - `patient = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='patient_appointments')` — orphan appointments make no sense if patient deletes account.
  - `doctor = ForeignKey(..., on_delete=PROTECT, related_name='doctor_appointments')` — PROTECT (not CASCADE) because prescription / lab-result / audit trail must survive doctor retirement.
  - `appointment_date = DateField()`, `time_slot = TimeField()` — deliberate split (not one `DateTimeField`) so `(doctor, date, slot)` uniqueness validates cleanly + filter queries stay timezone-simple.
  - `status = CharField(max_length=20, choices=Status.choices, default=Status.PENDING)` where `Status(TextChoices) = PENDING/CONFIRMED/CANCELLED`. Same enum pattern as `CustomUser.Role` (Step 7).
  - `notes = TextField(blank=True)`, `created_at = DateTimeField(auto_now_add=True)`. `Meta.ordering = ['-appointment_date', '-time_slot']`. `__str__` returns `"{patient} -> {doctor} on {date} {time}"`.
  - **3 typos caught during user typing** — all crash-level `AttributeError`: line 22 `models.DataField()` → `DateField()`, line 24 `models.ChatField` → `CharField`, line 31 `models.DataTimeField` → `DateTimeField`. Same Antigravity IDE silent-character-drop pattern from Days 9–12. Crash-level (not silent like Day 12 `form.errors` plurals). Rule active: grep typed Python lines for `Data/Date`, `Chat/Char`, punctuation drops before declaring clean.
- **Admin (commit `d139f37 feat(appointments): register Appointment in admin with autocomplete + filters`)** — CLEAN, zero typos. `@admin.register(Appointment)` + `AppointmentAdmin(admin.ModelAdmin)` with `list_display`, `list_filter` (status / date / doctor sidebar), `search_fields` with FK-traversal (`patient__username` / `doctor__username` / `notes`), `autocomplete_fields = ('patient', 'doctor')` (works because `CustomUserAdmin` already had `search_fields` from Step 9 — would have failed startup otherwise), `date_hierarchy = 'appointment_date'`.
- **Migrate**: `makemigrations appointments` → `0001_initial.py`. `migrate` applied cleanly (`Applying appointments.0001_initial... OK`). `appointments_appointment` table now in `db.sqlite3`. Browser-verified admin shows autocomplete search widgets for patient/doctor + Status dropdown with `Pending` default + `date_hierarchy` bar at top of change-list.
- **Concept-check 3/3 RIGHT first try** — first concept-check round with NO mechanic gap. Days 9 (CSRF) + 10 (`clean_X` return) both had right-intent-wrong-mechanic gaps. Day 10 teaching adjustment ("animate what physically happens in memory/db/network") appears to be working — keep applying.
- **NEW DURABLE RULE Day 14 — incremental tutorial writing** (saved as memory `feedback_incremental_tutorial.md`). Verbatim user statement: *"look write tutorial of step 13 till 13a so at end you don't have load to write all at once so from now on we write tutorial till where we completed ok update memory and write tutorial we commit now because it can create inconsistency in github"*. Rule: at end of EACH sub-step, write tutorial covering ONLY that sub-step's content + update `tutorial/README.md` index + update CLAUDE.md roadmap + update memory + ship docs commit. Two costs solved: (a) prose-load fatigue at end of parent step, (b) GitHub doc-vs-code inconsistency window. Compatible with chunking rule (Option A still holds — PR opens at parent-step completion, sub-step docs commits ship intra-branch).
- **Tutorial `tutorial/13-appointments-app.md` written** for 13a only. 7 halves + 3 FK concepts (`ForeignKey`/`on_delete`/`related_name`) with worked examples + "why it matters" closers + Gotchas + "Where each future feature plugs in" + 3-line Revise + Next pointer to 13b. Voice anchored on `tutorial/07-custom-user.md` (expert-teacher).
- **Pending docs commit** (final Day 14 action): `git add CLAUDE.md tutorial/13-appointments-app.md tutorial/README.md && git commit -m "docs(step-13a): tutorial + roadmap mark appointments model + admin complete" && git push`.
- **Stray `end` file at repo root** — empty, untracked, shell-typo artifact. Delete (`rm end`) or ignore. Not blocking docs commit.

### Day 15 recap (2026-06-24) — STEP 13b SHIPPED

- **Branch**: `feature/appointments-app`, started at HEAD `f6f7186 docs(step-13a)`. Working tree clean at session start.
- **5 concepts taught** (expert-teacher voice + Day 10 animated-mechanic rule): (1) QuerySet lazy eval + 6 triggers + chaining + cache, (2) `ModelForm` with FK + dynamic queryset in `__init__` as security defense layer, (3) `select_related` to JOIN-away N+1 (30 rows → 31 queries vs 1 query), (4) `get_object_or_404` + ownership scoping clause to block IDOR, (5) decorator stacking `@login_required` + `@require_POST` and why login decorator must be outermost.
- **Concept-check 3/3 first try BUT 2 partial gaps**:
  - Q1 (lazy QuerySet) — got *lazy* right, missed *WHEN* SQL fires. Re-explained 6 triggers (iteration, `list()`, slice-with-step, `len()`, `bool()`, template loop). Day 10 "animate what physically happens" rule worked — second pass landed.
  - Q3 (`select_related` math) — wrote "without selected_related 60+1" for 30 appointments. Idea right (without = many, with = 1) but arithmetic wrong. Correct = 30+1 = 31. Cosmetic only.
- **forms.py** (commit `e53da63`): `BookAppointmentForm(forms.ModelForm)`. Excludes `patient` + `status` from `Meta.fields` (defense layer 1). Dynamic `__init__` restricts `self.fields['doctor'].queryset = User.objects.filter(role='DOCTOR')` (defense layer 2). HTML5 widget overrides for date/time native pickers. **Silent bug caught**: line 8 `class meta:` lowercase — Django ignores, form would `ValueError` at first instantiation. Fixed.
- **views.py** (same commit): 4 FBVs — `doctor_list` (browse), `book_appointment` (GET/POST pattern, `commit=False` + server-side `appointment.patient = request.user` = defense layer 3), `my_appointments` (`.select_related('doctor')`), `cancel_appointment` (decorator stack + ownership-scoped `get_object_or_404`). **Silent bug caught**: line 51 `redirect('appointments: my_appointments')` — stray space inside string. Edit applied first time, edit got reverted somehow before runserver test, hit `NoReverseMatch` at first cancel click, fixed second time.
- **urls.py NEW** (same commit): `app_name='appointments'` + 4 routes. **Silent bug caught**: line 10 `<int:appointmetn_id>` letter-transposition would `TypeError` at first cancel click. Fixed before runserver.
- **config/urls.py wire-in** (same commit): added `path('appointments/', include('apps.appointments.urls'))` BUT user typed `appointment/` (singular) — not broken (URL names still reverse via `app_name` namespace), just inconsistent with tutorial copy. Decided to leave as-is — fixing would re-rewrite all browser URLs and break nothing.
- **3 templates** (commit `e4dd1bf`): `doctor_list.html`, `book.html`, `my_appointments.html`. **Silent bugs caught**: `doctor_list.html` line 14 missing `%` before closing `}` in `{% url 'appointments:book' doctor.id }` would `TemplateSyntaxError`. Line 19 `docotor` cosmetic. Both fixed before runserver. `my_appointments.html` initially saved with singular filename — IDE tab showed stale name; disk had correct plural already. False alarm.
- **Browser-verified full patient flow**: register PATIENT → browse `/appointment/doctors/` → click "Book appointment" → form with native date/time picker → submit → redirect to `/appointment/mine/` → row visible with status=Pending → click Cancel → confirm popup → status flips to Cancelled, Cancel button gone for that row.
- **2 atomic commits pushed**: `e53da63 feat(appointments): add patient booking views + form + urls` + `e4dd1bf feat(appointments): add patient templates (doctor list, book, my appointments)`.
- **Tutorial appended** to `13-appointments-app.md` — 9 halves (QuerySet lazy + ModelForm FK + N+1 + IDOR-prevention + decorator stack + 4 views walkthrough + URL layer + 3 templates walkthrough + 2-commit rationale) + Day 15 Gotchas table covering all 5 silent-failure typo patterns (lowercase `class meta`, space inside reverse strings, transposed URL converter names, missing `%` in template tags, plural drops on `.items`/`.errors`).
- **Day 15 typo pattern** added to memory: ALL 4 caught typos this session were silent at `manage.py check` and at runserver boot — all surfaced only at first real request. Rule: grep typed strings for these patterns before declaring "no issues":
  1. `class meta` (lowercase) in any `ModelForm`/`Meta`.
  2. Whitespace inside quoted URL names — `'app: name'`, `'app : name'`.
  3. Letter transposition in URL converter param names (`appointmetn_id` for `appointment_id`).
  4. Missing `%` in `{% url ... %}` closing.
  5. Plural drops — `form.error` vs `form.errors`, `.item` vs `.items` (Day 12 carryover).

### Day 16 recap (2026-07-06) — STEP 13c SHIPPED

- **Branch**: `feature/appointments-app`, started clean at `36de9d9 docs(step-13b)`. Now 8 commits (6 feat + 2 docs after this docs commit lands).
- **5 concepts taught** (expert-teacher voice + animated mechanic): (1) doctor reverse FK `doctor_appointments` mirror of patient side, (2) `date.today()` filter + clock-trust caveat, (3) `Q` objects for OR queries, (4) role-based login dispatch, (5) widened cancel ownership with `Q`.
- **Concept-check 4/5** — Q1/Q3/Q4/Q5 right first try. Q2 (clock off by 1 day → doctor sees wrong day) had a mechanic gap: user said "today is actual date," missed that `date.today()` blindly trusts the system clock. Re-explained. Day 10 animated-mechanic rule applied.
- **USER DESIGN DECISION**: dashboard = nav links, NOT a dedicated dashboard page. Doctor gets role-aware nav now; real dashboard page deferred to Step 15+ when doctor has availability/prescriptions/lab features. Also: patient nav previously had NO links to `/appointments/doctors/` + `/appointments/mine/` — added them to `base.html` role-aware nav. Ponytail-clean (dropped `doctor_dashboard` view + page + route from original 13c plan = 5 files not 7).
- **Files**: `appointments/views.py` (add `doctor_today` + widen `cancel_appointment` with `Q` + redirect fix), `appointments/urls.py` (add `doctor/today/`), `accounts/views.py` (role-based login redirect), `base.html` (role-aware nav), `doctor_today.html` (NEW).
- **REDIRECT BUG FIX (correctness, not cosmetic)**: widening cancel to doctors exposed that `redirect('appointments:my_appointments')` bounces a doctor to an empty page (`patient_appointments` empty for doctors). Fixed with role branch → `doctor_today` for doctors.
- **6 silent typos caught this session** — all passed `manage.py check`, all crash at first request:
  1. `Appointment.status.CANCELLED` (lowercase field vs `Status` enum) → `AttributeError`
  2. `'appointment:doctor_today'` (singular namespace) → `NoReverseMatch`
  3. `'appointment:my_appointments'` (singular — regression from working plural) → `NoReverseMatch`
  4. `{% url 'appointments:doctor_list %'}` (quote/`%`/`}` scramble, Day 9 pattern) → `TemplateSyntaxError`
  5. `'appointments:profile'` (wrong namespace — profile is in `accounts`) → `NoReverseMatch`
  6. duplicate `<nav>` block (added new, didn't delete old) → no crash, wrong links shown
- **Session-persistence non-bug**: user alarmed login page showed authenticated nav "without logging in." Diagnosed = valid session cookie from earlier testing, `user.is_authenticated` True even on `/login/`. NOT a bypass (incognito confirms). Optional guard (`if request.user.is_authenticated: redirect` at top of login/register views) deferred to 13d. User retested, self-resolved when session cleared.
- **2 atomic commits pushed**: `ece0c99 feat(appointments): add doctor today view + widen cancel to patient-or-doctor`, `3586cf4 feat(accounts): role-based login redirect + role-aware nav`.
- **Tutorial 13c appended** to `13-appointments-app.md` (7 halves + Day 16 Gotchas table + dashboard-as-nav decision recorded). README index → `⏳ In progress (13a + 13b + 13c done)`.
- **New typo patterns for grep list**: enum-vs-field casing, namespace singular/plural, wrong-namespace-on-shared-name, add-without-delete block edits.

### Day 17 recap (2026-07-09) — STEP 13d SHIPPED, STEP 13 COMPLETE → PR #3

- **Branch**: `feature/appointments-app`, both 13d-i + 13d-ii done in one session (user chose to push through both). 3 new feat commits (`851b11a`, `3a6a353`, `8cd7e94`) + docs commit = branch now ~13 commits.
- **13d-i (reception book + confirm)**: `ReceptionBookingForm` exposes `patient` in `Meta.fields` (only diff from `BookAppointmentForm` — that's the whole "book for anyone vs self" distinction) + dual `__init__` querysets. `reception_book` role-gated view. `confirm_appointment` (`PENDING→CONFIRMED`, reception any / doctor own, patient 404s naturally via `doctor=me` scope). Widened cancel to reception. `_redirect_after_action` helper (extract identical redirect, NOT the divergent lookup). Accept button on doctor_today PENDING rows. Reception nav branch.
- **13d-ii (global list + filters)**: `appointment_list` role-gated, UNSCOPED `Appointment.objects.select_related('patient','doctor')`, conditional GET-param filters (status/doctor/date via `request.GET.get()` + `if` chain, no django-filter dep). RECEPTION login redirect → list. Accept/Cancel buttons on list rows.
- **Concept-checks**: 13d-i 3/4 (Q3 role-vs-ownership auth model needed re-explain — user thought `request.user` filters, actually it's the role gate at the view door). 13d-ii 3/3 with 2 detail fixes (Q1 same role-gate point, Q3 URL param format). Corrected Q4 teaching mid-session: cancel+confirm do NOT share a lookup helper (scopes diverge — patient cancels but can't confirm); only the redirect is shared.
- **Day 17 typos**: `confirm_appointments` (plural view name vs singular URL ref → AttributeError at boot); `erros` (missing r → silent empty render). Both caught.
- **Design note**: patient "book" nav is "Find a Doctor" (must pick doctor first — `book_appointment` needs `doctor_id`). User briefly asked to relabel, then self-reverted — kept "Find a Doctor". No standalone patient book link possible.
- **3 atomic commits + docs commit**. STEP 13 COMPLETE (13a+13b+13c+13d).
- **BRANCH STRATEGY CONFIRMED (Day 17)**: one parent step = one branch = one PR. Step 13 → `feature/appointments-app` → PR #3. Step 13e → NEW branch `feature/appointments-lifecycle` → PR #4. Step 14 DRF → NEW branch → PR #5.
- **USER-REQUESTED Step 13e (Day 17)**: (1) `COMPLETED` status — `CONFIRMED → COMPLETED`, Complete button on CONFIRMED rows, doctor own / reception any, needs migration. (2) Doctor time-split views — history (`appointment_date__lte=today`, past+today) + upcoming (`__gt=today`, future). Doctor's "today" view stays. Deferred: DRF (Step 14, user said later).

### Day 18 recap (2026-07-09) — PR #3 MERGED + STEP 13e-i SHIPPED (COMPLETED + NO_SHOW)

- **PR #3 merged** — merge commit `49887e7` on `main`. Step 13 (13a–13d) fully in main. `feature/appointments-app` deleted local+remote. Main synced.
- **NEW branch `feature/appointments-lifecycle`** from `main`. Branch strategy confirmed again: 13e → this branch → PR #4; Step 14 DRF → new branch → PR #5.
- **Model**: `Appointment.Status` += `COMPLETED` (migration `0002_alter_appointment_status`) + `NO_SHOW` (migration `0003_alter_appointment_status`). NO_SHOW added mid-session on user request ("if confirmed and patient didn't show up"). Both = `AlterField` — choices change tracks state, SQLite column unchanged. Concept taught: any `choices=` edit needs a migration even when the column looks identical.
- **Views** (mirror of confirm): `complete_appointment` (`CONFIRMED → COMPLETED`) + `no_show_appointment` (`CONFIRMED → NO_SHOW`). Both `@require_POST`, reception any / doctor own, guard on `== CONFIRMED` from-state, end with `_redirect_after_action`. Patient can't reach either (doctor=me scope 404s).
- **Routes**: `complete/<int:appointment_id>/` (name `complete`), `no-show/<int:appointment_id>/` (name `no_show`).
- **Terminal-state-aware buttons**: PENDING → Accept+Cancel; CONFIRMED → Complete+No-show+Cancel; terminal (COMPLETED/NO_SHOW/CANCELLED) → dash. Action cells rewritten in `doctor_today.html` + `appointment_list.html`. **User-caught bug**: `my_appointments.html` patient cancel still used `!= 'CANCELLED'` — showed Cancel on completed/no-show rows. Fixed to `== 'PENDING' or == 'CONFIRMED'`.
- **Lifecycle final**: `PENDING ─confirm→ CONFIRMED ─complete→ COMPLETED / ─no-show→ NO_SHOW`; any non-terminal `─cancel→ CANCELLED`. 3 terminal states.
- **Concept-check 3/3** (enum migration, from-state guard, terminal states). No mechanic gaps.
- **Day 18 typos**: `appointment:complete` + `appointment:no_show` (singular namespace → NoReverseMatch), `{% csrf token %}` missing underscore (→ 403 on POST, silent at `check`). All caught pre-verify.
- **3 atomic commits pushed**: `a3a64c5` (model + 2 migrations), `debc235` (views + routes), `d8721db` (templates). Browser-verified all roles.
- **USER OVERRIDE Day 18**: 13e docs written at END of full 13e (after 13e-ii), all together — NOT per-sub-step. Explicit exception to [[feedback-incremental-tutorial]] for 13e only ("we write doc at last when 13e fully complete so we commit all together"). 13e-i has code commits only, no docs commit.
- **Step 16 idea logged** (roadmap): Celery Beat auto-expire stale PENDING → CANCELLED/EXPIRED; never auto-complete CONFIRMED (confirmed ≠ visited).

### Day 19 recap (2026-07-10) — STEP 13e-ii SHIPPED, STEP 13e COMPLETE → PR #4

- **13e-ii**: `doctor_history` (`__lte=today`, past+today, Meta ordering newest-first) + `doctor_upcoming` (`__gt=today`, `order_by('appointment_date','time_slot')` soonest-first). Routes `doctor/history/` + `doctor/upcoming/`. 2 templates with Date column; upcoming CONFIRMED rows = Cancel only (can't complete a future visit). Doctor nav: Today's / History / Upcoming.
- **Concept taught**: `__lt`/`__lte`/`__gt`/`__gte` field lookups; `<=` + `>` partition the calendar (today → history). Concept-check skipped mid-way per user (answer folded into code walkthrough).
- **Day 19 typos caught (7)**: 2 context-dict key misspellings (`'appiontments'`/`'appintments'` in views.py — NEW pattern: silently empty page, template loops nonexistent variable), 3 singular namespaces in doctor_history.html, missing No-show button in history CONFIRMED branch, `<form action="post"` duplicate-attribute in doctor_upcoming.html (NEW pattern: browser keeps first action → GET to literal "post" → 404). All silent at `check`.
- **2 feat commits pushed**: `2cf0acc` (views+routes), `aa669ae` (templates+nav). Branch = 5 feat commits total.
- **USER-DEFERRED to Step 14 (Day 19)**: double-booking prevention — `UniqueConstraint(doctor, appointment_date, time_slot, condition=~Q(status='CANCELLED'))` + migration + friendly ValidationError in both booking forms. Logged in roadmap Step 14 line.
- **Docs**: tutorial `13e-appointments-lifecycle.md` NEW (all 13e in one write per Day 18 override), README index row added, roadmap 13e checked.
- **Modes note**: user turned caveman OFF Day 19 (normal prose), ponytail stays ON (lazy-build discipline).

### Day 20 recap (2026-07-11) — PR #4 MERGED + STEP 14a SHIPPED (double-booking fix)

- **PR #4 merged** (`1be41ee` on main) at session start (user did it end of Day 19). Branch deleted, main synced.
- **NEW branch `feature/drf-api`** for Step 14. Split agreed: 14a constraint / 14b DRF+serializer+ViewSet / 14c SimpleJWT / 14d write-ops+filters+docs.
- **Pre-branch surprise**: 2 files dirty on main — user had self-added `@login_required` on login/register views (= infinite redirect loop, anonymous users can never reach login; caught + explained before commit) + `appointments/` prefix pluralization (good, kept). Guard redone correctly inline (`if request.user.is_authenticated: redirect('accounts:profile')` first line of both views) — 13c-deferred polish now done.
- **14a shipped**: `UniqueConstraint` (doctor/date/slot, `condition=~Q(status='CANCELLED')`, `violation_error_message`) → migration 0004 (IntegrityError on existing dupes — user cleaned via admin, re-ran). **Django subtlety**: conditional constraint referencing non-form field (`status`) silently skipped by ModelForm validation → 500 instead of form error. Fixed with shared `_validate_slot_free` helper + form-wide `clean()` in both booking forms. Race ceiling documented (DB catches). Browser-verified all 4 cases.
- **Session-persistence Q answered**: DB-backed sessions (django_session + sessionid cookie) survive runserver restarts; landing on profile = the new guard. Same mechanic as Day 16, now consistent UX.
- **Zero typos in user-typed code this session — first clean sheet since typo tracking began (Day 9).**
- **Concept-check 2/2** (condition frees cancelled slot; race = both form checks pass before either INSERT).
- Commits on `feature/drf-api`: `1d2c55d` guard, `8e32b50` prefix, constraint+forms commit, docs commit.

### Day 21 recap (2026-07-12) — STEP 14b SHIPPED (DRF install + serializer) + status catalogue corrected

- **User-uploaded `OPD_PROJECT_STATUS.md`** (gitignored, local-only) — full feature catalogue. Corrected against real code: (1) **TimeSlot model does NOT exist** — catalogue claimed it done in 13a + listed in Key Files; reality is `Appointment` has `appointment_date` + `time_slot` as plain fields, no separate slot model. Fixed all references + flagged Step 15 as a real design decision (build TimeSlot model or keep field-based). (2) Marked 14-pre/14a/URL-prefix done. (3) Login redirects fixed to reality (PATIENT+LAB→profile, RECEPTION→/appointments/all/). (4) Versions: 6.0.6 / Python 3.14.2 / SQLite dev. (5) django-filter never installed. Adopted catalogue's good calls: step renumbering (15 lab / 16 prescriptions / 17 notifications / 18 dashboard / 19 deploy / 20 frontend), Django-6-built-in-Tasks over Celery for reminders (reconcile at Step 17), finer 14 split (14b serializers / 14c viewsets / 14d JWT+filters / 14e spectacular).
- **14b shipped**: `pip install djangorestframework` (3.17.1) + freeze + INSTALLED_APPS. `AppointmentSerializer(ModelSerializer)` in new `appointments/serializers.py` (NOT a separate api/ app — ponytail). `read_only_fields=['id','status','created_at']`. Shell-tested: `AppointmentSerializer(Appointment.objects.first()).data` → correct JSON (FKs as PK ints, status PENDING, created_at ISO+05:30). 2 commits: `chore(api): install djangorestframework + ignore local status file`, `feat(api): add AppointmentSerializer`.
- **Concept**: serializer = ModelForm-for-JSON (same Meta; `validate_<f>`/`validate` mirror `clean_<f>`/`clean`; `read_only_fields` = out-not-in).
- **Gotchas Day 21**: Bash tool's bare `python` = system Python (not `.venv`) → false "DRF not installed"; trust `manage.py check`. `http://127.0.0.1:5500/` = VS Code Live Server (static files), NOT Django — app is always `:8000`.
- **Modes**: caveman OFF, ponytail ON, model Opus. Zero code typos again.
- Tutorial 14b appended, README `⏳ (14a + 14b done)`, roadmap 14b checked.

### Day 22 recap (2026-07-13) — STEP 14c SHIPPED (role-scoped ViewSet + dedicated api app)

- **Dedicated `api` app created** (`backend/apps/api/`) — user-driven structure decision. User raised "separate api folder" at session start; I gave repeated YAGNI pushback across several turns before agreeing. User feedback: he WELCOMES debate (argument → better ideas) but the friction was re-opening the SAME point turn after turn instead of making the case once + landing on his call. Saved as [[feedback-architecture-preference]]. Structure: `api` app owns viewsets + router; feature apps keep serializers.
- **14c shipped**: `AppointmentViewSet(ModelViewSet)` in `api/views.py` (get_queryset role-branch + perform_create patient injection + IsAuthenticated), `DefaultRouter` in `api/urls.py`, mounted `/api/` in config/urls.py. `'apps.api'` in INSTALLED_APPS + apps.py dotted-path patch. Old `appointments/api_views.py`/`api_urls.py` (this session, uncommitted) deleted — never tracked, no git rm needed.
- **Browsable API verified 5/5**: anon→403, patient/doctor/reception→scoped lists, other-patient-id→404 (get_queryset scoping = free IDOR guard on retrieve).
- **Concept-check 3 Q**: Q1 ✓ (404 via get_queryset). Q2 basename — user didn't know; taught (DRF infers URL name from `queryset` attr; overriding `get_queryset()` method removes that → must pass basename). Q3 content negotiation — user confused it with role scoping; corrected (Accept header picks renderer HTML vs JSON, not request.user).
- **Day 22 typos (2)**: `router.register('appointments', 'AppointmentViewSet', ...)` quoted class → str → `AttributeError: 'str' object has no attribute 'get_extra_actions'` at import (traceback, not silent); `user.roel` → `AttributeError` at request (silent at check). NEW grep: attribute names on request.user/model instances.
- **Mount decision**: stays `/api/`, no `/v1/` (user call — "different folder so no need for version").
- **Commit `a3b207e`** `feat(api): role-scoped AppointmentViewSet + router in dedicated api app`. Modes: caveman OFF, ponytail ON, Opus.

### Day 23 recap (2026-07-14) — STEP 14d + 14e SHIPPED, STEP 14 COMPLETE → PR #5

- **14d SimpleJWT**: install + `REST_FRAMEWORK` settings (JWT + Session auth classes, IsAuthenticated global) + `/api/token/` + `/api/token/refresh/` (built-in views). Full flow curl-verified from cookieless client (Bearer header → scoped JSON; no header → 401). Concepts taught: JWT stateless (no DB lookup) vs session; access(short/high-exposure) + refresh(long/low-exposure) pair. Concept-check: Q1 ✓ (no DB lookup). Q2 — user gave roles but missed the exposure-vs-lifespan security point; corrected (access rides every request = short fuse; refresh rarely on wire = can live long). django-filter SKIPPED (YAGNI). Typo: `token/refresh` missing trailing slash. Commit `9a2eeae`.
- **14e drf-spectacular**: install + INSTALLED_APPS + DEFAULT_SCHEMA_CLASS + 3 routes (schema/docs/redoc). `/api/docs/` Swagger renders all endpoints auto. Zero typos.
- **Teaching moment**: user didn't know where curl goes ("browser search bar?") — explained curl = terminal command (new Git Bash terminal, not PowerShell whose curl differs), not the browser bar. User ran Option A (2nd terminal) successfully → JSON returned.
- **STEP 14 COMPLETE (14a–14e)**: booking integrity + serializer + role-scoped viewset/router + JWT + auto docs. All on `feature/drf-api`.
- Modes: caveman OFF, ponytail ON, Opus.

### Day 24 resume point — merge PR #5 → Step 15 (lab + availability, new branch)

1. **PR #5**: on `feature/drf-api` — title `feat(api): DRF layer — serializers, role-scoped viewset, JWT auth, Swagger docs (Step 14)`. Review own diff → merge → `git checkout main && git pull` → delete branch local+remote → confirm clean.
2. **Step 15 — lab module + doctor availability + auth extras** on NEW branch (catalogue name `feature/lab-and-availability`). BIG — pre-session scope check + sub-step split FIRST.
   - **FIRST DECISION (blocking)**: TimeSlot/Availability model — build a real slot model (FK doctor, date, start, end, max_patients) + doctor CRUD views, OR keep current field-based booking. Catalogue flagged it; no slot model exists today. Decide before lab work.
   - Then: LabTest + LabResult models, doctor request-lab-test (on CONFIRMED appts), lab pending-queue, lab upload result + status, ReportLab PDF lab report. Plus auth extras (forgot-password via Django built-in, profile photo).
3. **Reconcile**: CLAUDE.md Step 16 says Celery+Redis; catalogue says use Django 6 built-in Tasks for the 24hr reminder (fewer deps). Decide at Step 17 (notifications). Also note catalogue renumbered steps (15 lab / 16 prescriptions / 17 notifications / 18 dashboard / 19 deploy / 20 frontend) — CLAUDE.md roadmap still uses old numbers below Step 14; reconcile when starting Step 15.
4. `OPD_PROJECT_STATUS.md` (gitignored, local) = corrected feature catalogue; read for full map.
5. Modes carry: caveman OFF, ponytail ON. Grep list active (attribute typos, quoted-class-in-register, context-dict keys, etc.).

### Teaching-style rule (added Day 9, 2026-06-18 — REFINED same day)

**Two-part feedback from user, same session:**
1. First: "use some easy word and language while teaching and give examples for clartiy and better understanding"
2. Then refined: "use some technical word or diffcult word but also give example for understanding... use diffcult word or technical word where need if you are using unnesscery then it is not ok... think you are expert of this field and you are one type of teacher which make every topic look use and teache every person in way that he or she understand very easily"

**Net rule — bring back the early-Steps (01–07) voice:**

1. **Use real Django terms when the topic needs them.** `migration`, `ORM`, `decorator`, `serializer`, `middleware`, `signal`, `CSRF`, `URLconf`, `QuerySet`, `AbstractUser`, `MRO`, `field lookup` — these are the actual vocabulary of the job. Hiding them leaves Prince fluent only in our tutorials. Use the word, then teach the word.
2. **Always pair the term with a worked example.** Bold the term, define in one line, show a 2-3 line code block, close with one line on "why it matters". That four-beat structure was the Steps 1–7 voice — return to it.
3. **Cut jargon used for status, not teaching.** "Orthogonal", "ambient", "polymorphic", "idempotent", "directive" — drop unless the topic genuinely IS that thing. These signal expertise instead of building it in the reader.
4. **Expert-teacher voice.** Imagine a senior who has shipped 10 Django projects and now teaches first-years. Confident with vocabulary, patient with explanation. User comes out of each section knowing both the **word** AND the **thing**.

**Template:**

> **`<TERM>`** — one-line definition.
>
> ```python
> # 2-3 line code example showing the term in action
> ```
>
> Why it matters: one line on real-world consequence.

**Reference tutorials:**
- Target (early-Steps voice): `tutorial/03-startproject.md`, `tutorial/05-settings.md`, `tutorial/07-custom-user.md`
- Step 11 leaned too "simple" — over-corrected the first time. Step 12 should land at the early-Steps balance: real terms + worked examples + analogy when the plumbing is abstract.

## Step chunking rule (added Day 13, 2026-06-22 after Step 12 ran 3 sessions)

**Prince's real session budget = 1 hour to 1:30 hour.** Design steps to that, not to round numbers.

### BIG step → split. NOT BIG → keep whole.

A step is **BIG** if any one of these is true:
- 4+ new files to touch
- 5+ new concepts to teach
- Estimated 2+ hours of typing/verifying
- Spans multiple distinct features (model + views + templates + forms at once)

If BIG → split into sub-steps (`13a`, `13b`, ...) each sized to complete in 1–1:30 hr including concept teach + typing + browser verify + 1–3 commits.

If NOT BIG → one session, no chunking ceremony.

### Branch + PR strategy — Option A

**One branch + one PR per parent step**, not per sub-step. Reason: PR ceremony (open / review / merge / cleanup) costs 15-20 min. Doing it per sub-step would burn 60-80 min of git overhead per step. Roll sub-steps up.

Example for Step 13: branch `feature/appointments-app` lives across 4 sub-steps (13a/b/c/d). PR #3 opens only when 13d is done. Same pattern PR #2 used.

### Two enforced rules

1. **Pre-session scope check** — at session start, propose "today we'll do X (Y minutes)" + wait for user confirm before any code typed. If estimate off → resize plan, not session.
2. **Hard stop at session budget** — if 1:30 hits mid-code: (a) push WIP commit + flag in memory, OR (b) revert dirty changes + smaller next chunk. Never "just 15 more minutes" — that's how Step 12 leaked across 3 days.

## How to help

When the developer asks for help:

1. **Explain before code.** State what we are about to do and why. Then give the command or code to type.
2. **One step at a time.** Wait for confirmation before moving on.
3. **Refer back to this file** for stack, structure, and conventions — do not re-derive them.
4. **Refer to `opd_roles_and_final_structure.html`** for feature/permission details.
5. **Update the roadmap checkboxes** in this file when a step completes.
6. **Use the caveman voice for short summaries / headers** when the user has the `/caveman` skill active, but **always switch to clear prose for teaching explanations** — fragment ambiguity hurts a learner.
