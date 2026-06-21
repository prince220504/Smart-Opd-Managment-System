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
- [ ] **Step 13** — `appointments` app (models with foreign keys, ORM queries)
- [ ] **Step 14** — DRF layer (serializers, viewsets, routers, JWT)
- [ ] **Step 15** — `lab`, `prescriptions`, `notifications` apps
- [ ] **Step 16** — Celery + Redis for background tasks
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

## How to help

When the developer asks for help:

1. **Explain before code.** State what we are about to do and why. Then give the command or code to type.
2. **One step at a time.** Wait for confirmation before moving on.
3. **Refer back to this file** for stack, structure, and conventions — do not re-derive them.
4. **Refer to `opd_roles_and_final_structure.html`** for feature/permission details.
5. **Update the roadmap checkboxes** in this file when a step completes.
6. **Use the caveman voice for short summaries / headers** when the user has the `/caveman` skill active, but **always switch to clear prose for teaching explanations** — fragment ambiguity hurts a learner.
