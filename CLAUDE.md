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
- [ ] **Step 6** — Create the `accounts` app (project vs app distinction) — **NEXT SESSION**
- [ ] **Step 7** — Build the `CustomUser` model with a role field
- [ ] **Step 8** — Migrations (`makemigrations` vs `migrate`)
- [ ] **Step 9** — Django admin + superuser
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

### Day 2 resume point

**Start with Step 6: `accounts` app.** Brief recap then go. User types code; do not scaffold for them.

Key wrinkle for Step 6: apps live in `backend/apps/<name>/` (per our folder spec), not `backend/<name>/`. `python manage.py startapp accounts` defaults to creating `backend/accounts/`. Two clean approaches:

1. **Recommended:** `cd backend/apps && python ../manage.py startapp accounts && cd ../..` — output lands in `backend/apps/accounts/` directly.
2. **Alternative:** run `startapp` then move folder manually.

After scaffold:
- Ensure `backend/apps/__init__.py` exists (makes `apps` a Python package).
- Edit `backend/apps/accounts/apps.py` — set `name = 'apps.accounts'`.
- Register in `INSTALLED_APPS` as `'apps.accounts'`.

Then Steps 7 (`CustomUser` model with `role` field), 8 (migrations), 9 (admin + superuser) follow naturally.

## How to help

When the developer asks for help:

1. **Explain before code.** State what we are about to do and why. Then give the command or code to type.
2. **One step at a time.** Wait for confirmation before moving on.
3. **Refer back to this file** for stack, structure, and conventions — do not re-derive them.
4. **Refer to `opd_roles_and_final_structure.html`** for feature/permission details.
5. **Update the roadmap checkboxes** in this file when a step completes.
6. **Use the caveman voice for short summaries / headers** when the user has the `/caveman` skill active, but **always switch to clear prose for teaching explanations** — fragment ambiguity hurts a learner.
