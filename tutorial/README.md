# Tutorial — Smart OPD Management System

Step-by-step Django learning notes. Revise any time. Each file covers **what**, **why**, and **how** for one topic.

## Index

| # | Step | File | Status |
|---|------|------|--------|
| 1 | Python virtual environment (`venv`) | [01-python-venv.md](01-python-venv.md) | ✅ Done |
| 2 | Install Django + freeze `requirements.txt` | [02-install-django.md](02-install-django.md) | ✅ Done |
| 3 | `django-admin startproject` + scaffold tour | [03-startproject.md](03-startproject.md) | ✅ Done |
| 4 | First `runserver` + WSGI | [04-runserver.md](04-runserver.md) | ✅ Done |
| 5 | `settings.py` walkthrough | [05-settings.md](05-settings.md) | ✅ Done |
| 5.5 | Git & GitHub industry workflow | [05.5-git-workflow.md](05.5-git-workflow.md) | ✅ Done |
| 6 | Create the `accounts` app | [06-accounts-app.md](06-accounts-app.md) | ✅ Done |
| 7 | `CustomUser` model with role field | [07-custom-user.md](07-custom-user.md) | ✅ Done |
| 8 | Migrations (`makemigrations` vs `migrate`) | [08-migrations.md](08-migrations.md) | ✅ Done |
| 9 | Django admin + superuser | [09-admin-superuser.md](09-admin-superuser.md) | ✅ Done |
| 10 | URLs + views | [10-urls-and-views.md](10-urls-and-views.md) | ✅ Done |
| 11 | Templates pointing at `frontend/templates` | [11-templates.md](11-templates.md) | ✅ Done |
| 12 | Auth forms (login, register, profile) | [12-auth-forms.md](12-auth-forms.md) | ✅ Done |
| 13 | `appointments` app — models + booking + roles | [13-appointments-app.md](13-appointments-app.md) | ✅ Done (13a–13d) |
| 13e | Appointment lifecycle + doctor history/upcoming | [13e-appointments-lifecycle.md](13e-appointments-lifecycle.md) | ✅ Done |
| 14 | DRF layer (serializers, viewsets, JWT) | _coming_ | |
| 15 | `lab`, `prescriptions`, `notifications` apps | _coming_ | |
| 16 | Celery + Redis | _coming_ | |
| 17 | Whitenoise — static & media in production | _coming_ | |
| 18 | Render deploy | _coming_ | |

## How to use

- Read top-to-bottom — each step builds on the previous one
- **What → Why → How** is the pattern everywhere
- Code blocks are copy-paste safe
- "Gotchas" sections list mistakes to avoid
- "Revise" sections at the bottom of each file = 3-line summary for quick recall
