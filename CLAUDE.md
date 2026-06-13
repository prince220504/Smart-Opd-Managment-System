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
- [ ] **Step 10** — URLs and views (request → URL → view → response)
- [ ] **Step 11** — Templates pointing at `frontend/templates`
- [ ] **Step 12** — Auth forms (login, register, profile)
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

### Day 7 resume point

1. Confirm Day 6 docs commit landed: `git log --oneline -3` should show `docs(step-9): tutorial + roadmap mark admin+superuser complete` at top.
2. Fix the `'Hopital info'` typo in `backend/apps/accounts/admin.py` line 11 → `'Hospital info'`. Tiny commit: `fix(accounts): typo in admin fieldset heading`. Push.
3. **Open the first Pull Request** on GitHub for `feature/accounts-app`:
   - GitHub auto-detects the recent push and shows a "Compare & pull request" yellow banner — click it.
   - Title: `feat(accounts): CustomUser model + admin + migration`
   - Body: bullet the commits — Step 6 scaffold, Step 7 model + AUTH_USER_MODEL, Step 8 migration, Step 9 admin + superuser.
   - Click **"Create pull request"** → GitHub now shows the diff for the entire branch.
   - Scroll through own diff — last sanity check before merge.
   - Click **"Merge pull request"** → **"Confirm merge"**. The button shows the merge strategy (default "Create a merge commit" — that's fine for now).
   - Locally: `git checkout main && git pull` — sync the merged state.
   - Optionally delete branch: `git branch -d feature/accounts-app` (local) + `git push origin --delete feature/accounts-app` (remote).
4. **Step 10 (URLs and views)** starts on a new branch: `git checkout -b feature/auth-views`.
   - Wire `backend/config/urls.py` to include `backend/apps/accounts/urls.py`.
   - Write a tiny `accounts/views.py` (login/logout/register) — first time we see the request → URL → view → response cycle.
   - This is also the first step that needs templates from `frontend/templates/` — so it bridges backend + Stitch frontend.

## How to help

When the developer asks for help:

1. **Explain before code.** State what we are about to do and why. Then give the command or code to type.
2. **One step at a time.** Wait for confirmation before moving on.
3. **Refer back to this file** for stack, structure, and conventions — do not re-derive them.
4. **Refer to `opd_roles_and_final_structure.html`** for feature/permission details.
5. **Update the roadmap checkboxes** in this file when a step completes.
6. **Use the caveman voice for short summaries / headers** when the user has the `/caveman` skill active, but **always switch to clear prose for teaching explanations** — fragment ambiguity hurts a learner.
