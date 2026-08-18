<div align="center">

# 🏥 Smart OPD Management System

### A Complete Hospital Outpatient System — Four Roles, One Workflow

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white)](https://djangoproject.com)
[![DRF](https://img.shields.io/badge/DRF-3.17-A30000?style=for-the-badge&logo=django&logoColor=white)](https://django-rest-framework.org)
[![Celery](https://img.shields.io/badge/Celery-5.6-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Redis](https://img.shields.io/badge/Redis-Broker-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Tailwind](https://img.shields.io/badge/Tailwind-CDN-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://smart-opd-managment-system.onrender.com)

### 🌐 **[Live App → smart-opd-managment-system.onrender.com](https://smart-opd-managment-system.onrender.com)**

*Free instance — the first request may take ~50 seconds to wake the server.*

---

*Patient books → Reception confirms → Doctor consults, prescribes & orders tests → Lab uploads results → Everyone is notified automatically*

</div>

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 🩺 Doctor
- Today's consultations + 7-day activity chart
- **One consultation page** — write the prescription *and* order lab tests without leaving it
- Full patient records with test results inline
- Set working days, hours and unlimited breaks
- Own patient list, built from completed visits

</td>
<td width="50%">

### 🖥️ Reception / Admin
- Live dashboard — status breakdown, per-doctor load, today's schedule
- Book on behalf of any patient
- All appointments with filters + **CSV export**
- Patient registry and **walk-in registration**
- Confirm, start, complete or cancel any visit

</td>
</tr>
<tr>
<td width="50%">

### 🔬 Lab Technician
- New requests queue, separate from work in progress
- Upload PDF or image results with notes
- Searchable archive of every test ever run
- Marks results normal / abnormal at a glance

</td>
<td width="50%">

### 🙍 Patient
- Find a doctor by department, see their hours before booking
- Book, reschedule or cancel with a reason
- Prescriptions — **print to PDF** straight from the browser
- Lab results and a full medical history timeline

</td>
</tr>
</table>

### 🔥 Highlights

| Feature | Description |
|:--------|:------------|
| 🔐 **Login with email *or* username** | A custom auth backend tries username first, then email case-insensitively — no migration, admin untouched |
| 📧 **Password reset by email** | One-time links that expire in 3 days and kill themselves the moment they're used |
| 🔔 **9-event notification system** | In-app for everyone, email only for the three events that matter outside the app |
| ⏰ **Scheduled background jobs** | Celery Beat sends 24-hour reminders at 08:00 and auto-cancels stale bookings at 00:30 |
| 🛡️ **Ownership checks inside the query** | Every lookup carries its permission rule, so a guessed id returns 404 — never someone else's record |
| 📊 **Charts with zero libraries** | The doctor's weekly chart is drawn with `{% widthratio %}`; the reception charts use Chart.js via CDN |
| 🖨️ **PDFs without a PDF library** | The rendered prescription *is* the document — `window.print()` + a print stylesheet |
| 🔑 **JWT REST API** | Role-scoped, validated by the same rules as the web forms, documented with Swagger |

---

## 🛠️ Tech Stack

<div align="center">

| Layer | Technology | Purpose |
|:------|:-----------|:--------|
| 🌐 **Web Framework** | Django 6.0 | MVT, ORM, auth, admin |
| 🔌 **API** | Django REST Framework + SimpleJWT | Token-authenticated, role-scoped endpoints |
| 📖 **API Docs** | drf-spectacular | OpenAPI schema + Swagger UI |
| ⚙️ **Background Jobs** | Celery 5.6 + Redis | Emails, reminders, auto-cancellation |
| 🎨 **Frontend** | Django Templates + Tailwind (CDN) | Server-rendered, no build step |
| 🗄️ **Database** | SQLite (dev) · PostgreSQL on Neon (prod) | — |
| 🔒 **Config** | python-decouple | Secrets in `.env`, never in git |
| 📈 **Charts** | Chart.js (CDN) + `{% widthratio %}` | Reception analytics · doctor weekly bars |
| 📮 **Email** | django-anymail → Brevo API | HTTPS, because hosts block outbound SMTP |
| 📦 **Static Files** | Whitenoise | Hashed, compressed, served by the app itself |
| 🚀 **Hosting** | Render + gunicorn | Auto-deploy on push |

</div>

---

## 📁 Project Structure

```
📦 Smart OPD Management System
│
├── ⚙️ backend/
│   ├── config/                  # settings · urls · celery app
│   ├── apps/
│   │   ├── accounts/            # CustomUser, auth backend, profiles, registry
│   │   ├── appointments/        # appointments, availability, dashboards, CSV
│   │   ├── prescriptions/       # prescriptions (JSON medicines, printable)
│   │   ├── lab/                 # lab tests + results (file uploads)
│   │   ├── notifications/       # model, triggers, celery tasks
│   │   └── api/                 # DRF routers
│   ├── media/                   # uploaded lab results (gitignored)
│   ├── .env                     # secrets (gitignored)
│   └── manage.py
│
├── 🎨 frontend/
│   ├── templates/
│   │   ├── base.html            # sidebar shell, role-aware nav
│   │   ├── accounts/            # login, register, profile, password reset
│   │   └── appointments/
│   │       ├── patient/         # grouped by role, so it is obvious
│   │       ├── doctor/          # who each page belongs to
│   │       └── reception/
│   └── static/                  # css/main.css · js/main.js
│
└── 📄 requirements.txt
```

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      BROWSER (4 roles)                        │
│   Patient  ·  Doctor  ·  Reception  ·  Lab Technician         │
└───────────────────────────┬──────────────────────────────────┘
                            │  session auth          │ JWT
              ┌─────────────┴─────────────┐   ┌──────┴────────┐
              │      Django Views         │   │   DRF API     │
              │  role-scoped querysets    │   │  /api/docs/   │
              └─────────────┬─────────────┘   └──────┬────────┘
                            │                        │
                    ┌───────┴────────────────────────┘
                    │   shared validators (forms.py)
                    │   availability · slot conflicts
                    ▼
        ┌───────────────────────────────────────┐
        │              MODELS                    │
        │  CustomUser · Appointment · LabTest    │
        │  LabResult · Prescription · Notification│
        └───────────────┬───────────────────────┘
                        │
              ┌─────────┴──────────┐
              │  notify() service  │  ← single write path, all 9 events
              └─────────┬──────────┘
                        │ email=True
                        ▼
        ┌───────────────────────────────────────┐
        │        Celery  ──►  Redis broker       │
        │  send_email · reminders 08:00          │
        │  auto-cancel stale bookings 00:30      │
        └───────────────────────────────────────┘
```

---

## 🔔 Notification Matrix

> **The rule:** email is for people who are *not* in the app. In-app is for people who live in it.

| Event | In-App | Email |
|:------|:------:|:-----:|
| 📅 Appointment booked | Patient | ✅ Patient |
| ⏰ Reminder, 24 h before | Patient | ✅ Patient |
| 🔬 Result uploaded | Patient + Doctor | ✅ Patient only |
| ✔️ Appointment confirmed | Patient | — |
| ❌ Appointment cancelled | the other party | — |
| 🧪 Test requested | Lab technicians | — |
| 💊 Prescription written | Patient | — |
| 🚶 Walk-in registered | Reception | — |
| 🗑️ Stale booking auto-cancelled | Patient | — |

A doctor seeing 30 patients a day gets **in-app only** — mailing every result would train them to ignore the inbox entirely.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+ (built on 3.14)
- Docker (for Redis — optional, only needed for emails and scheduled jobs)
- A free [Brevo](https://brevo.com) account for sending email (verified sender + API key)

### Installation

**1. Clone the repo**
```bash
git clone https://github.com/prince220504/smart-opd-management-system.git
cd smart-opd-management-system
```

**2. Create the virtual environment & install**
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

**3. Set up environment variables**
```powershell
copy backend\.env.example backend\.env
```

Then edit `backend/.env`:
```env
SECRET_KEY=your-django-secret-key
DEBUG=True
BREVO_API_KEY=your-brevo-api-key
DEFAULT_FROM_EMAIL=your-verified-sender@example.com
CELERY_BROKER_URL=redis://localhost:6379/0
```

> Every key is read with **no fallback** — a missing one stops the server at boot instead of failing quietly at 2 a.m. `DATABASE_URL` and `ALLOWED_HOSTS` *do* have defaults, so a fresh clone runs on SQLite with nothing else configured.

**4. Migrate and create your first user**
```powershell
cd backend
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open **http://127.0.0.1:8000/** 🎉

---

## 👥 Creating the Four Roles

The superuser is an admin. Create working accounts in `/admin/` and set each one's **role** field:

| Role | Lands on | Can do |
|:-----|:---------|:-------|
| `PATIENT` | Patient dashboard | book, reschedule, cancel, view own records |
| `DOCTOR` | Doctor dashboard | consult, prescribe, order tests, set schedule |
| `RECEPTION` | Reception dashboard | manage everything, register walk-ins, export CSV |
| `LAB` | Lab dashboard | run tests, upload results |

Reception can also register patients directly from the app — no admin needed.

---

## ⚙️ Background Tasks

Redis is the message broker. Emails and scheduled jobs run through Celery.

```bash
docker run -d -p 6379:6379 --name opd-redis redis   # first time only
docker start opd-redis                               # every session after
```

Then **four terminals**:

| # | Terminal | Command |
|:-:|:---------|:--------|
| 1 | 🔴 Redis | `docker start opd-redis` |
| 2 | 🌐 Web | `python manage.py runserver` |
| 3 | ⚙️ Worker | `celery -A config worker -l info --pool=solo` |
| 4 | ⏰ Scheduler | `celery -A config beat -l info` |

> `--pool=solo` is **required on Windows** (no `os.fork()`). The worker does **not** auto-reload — restart it after editing `tasks.py` or `settings.py`.

The app runs perfectly without any of this — only emails and scheduled jobs pause. Queue failures are caught and logged, so a booking still saves when Redis is down.

**In production there is no Redis and no worker.** Two settings replace them:

| Half of the problem | Development | Production |
|:--------------------|:------------|:-----------|
| Send an email | `.delay()` → Redis → worker | `CELERY_TASK_ALWAYS_EAGER=True` runs it inline |
| Run something daily | Celery Beat | `GET /notifications/cron/daily/?key=…` from an external scheduler |

A `@shared_task` is still an ordinary Python function, so "send this email" only needs *someone* to call it — but "do this every day at 08:00" needs a clock, not a queue. The cron endpoint is guarded with `constant_time_compare` and returns **404** on a bad or missing key, so it never confirms it exists.

---

## 🔌 REST API

```bash
# 1. get a token
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "you", "password": "yours"}'

# 2. use it
curl http://127.0.0.1:8000/api/appointments/ \
  -H "Authorization: Bearer <access-token>"
```

**Interactive docs → http://127.0.0.1:8000/api/docs/**

The API enforces the same rules as the web pages:

| Rule | Behaviour |
|:-----|:----------|
| 🔍 Role-scoped queryset | Reception sees all · Doctor sees theirs · Patient sees theirs |
| 🔒 `patient` & `status` read-only | A PATCH cannot move an appointment to another account or self-complete a visit |
| 👨‍⚕️ `doctor` must be a doctor | A foreign key alone only checks the id exists, not the role |
| 🕐 Availability enforced | The serializer calls the *same* validators the booking form uses |
| 🚫 `DELETE` refused | Visits are cancelled, never erased — the record survives |

---

## 💡 Design Decisions

| Decision | Why |
|:---------|:----|
| **Availability validates, it doesn't generate slots** | Real OPD visits aren't fixed 15-minute blocks. A doctor sets hours and breaks; a patient picks any time inside them |
| **Age is stored, not date of birth** | A walk-in at the counter often doesn't know their DOB, and the desk needs the record created *now* |
| **Prescriptions print through the browser** | The rendered page already *is* the document — a PDF library would mean a second layout to maintain |
| **CSV, not Excel** | Excel opens CSV natively. `openpyxl` would be a dependency for nothing |
| **`display_name` as a model property** | `full_name or username` — works in emails, CSV exports and `__str__`, where a template filter cannot reach |
| **Email as an *option*, not a replacement** | Keeping `username` as the login field avoided a custom manager, a data migration, and a lockout risk |
| **Email over HTTPS, not SMTP** | Hosts block outbound ports 25/465/587 to stop spam. A blocked port *hangs* instead of failing, so a booking took the whole worker down until gunicorn killed it |
| **One codebase, two environments** | Dev and prod run identical code reading different env values — no `if PRODUCTION:` branches to drift apart |

---

## 🚀 Deployment

Live on **Render**, database on **Neon** (PostgreSQL), email through **Brevo**, daily tasks triggered by **cron-job.org**.

| Piece | Choice | Why |
|:------|:-------|:----|
| 🌐 **Host** | Render, no Docker | `Procfile` + `requirements.txt`, auto-deploy on push to `main` |
| 🗄️ **Database** | Neon PostgreSQL | Render's free Postgres expires after 30 days |
| 📦 **Static files** | Whitenoise, second in `MIDDLEWARE` | A CSS request is answered at the door, before sessions or auth run |
| 🔐 **HTTPS** | `SECURE_SSL_REDIRECT` + `SECURE_PROXY_SSL_HEADER` | Render terminates TLS upstream — without the header, Django thinks every request is insecure and redirects forever |
| 📮 **Email** | Brevo HTTP API | Outbound SMTP is blocked on the host |
| ⏰ **Daily jobs** | cron-job.org → the cron endpoint | No always-on process to run Beat |

Settings hold **no production branches**. `ALLOWED_HOSTS`, `DATABASE_URL` and `DEBUG` are read with `config()` and the *dev* value as the default, so a fresh clone runs locally with almost no `.env` while Render supplies real values. The only environment-shaped block is `if not DEBUG:`, which turns on the HTTPS settings.

Migrations were run **from a laptop** against Neon — the free tier has no shell, so `DATABASE_URL` goes into `.env` just long enough to run the command.

---

## 🗺️ Build Journey

| Phase | Focus | What Got Built |
|:---:|:------|:---------------|
| **1** | **Foundation & Auth** | Django project · `CustomUser` with roles · login, register, profiles · role-aware navigation |
| **2** | **Appointments** | Booking with IDOR-scoped views · six-state lifecycle · reception book-on-behalf · filters · double-booking constraint |
| **3** | **API Layer** | DRF serializers · role-scoped viewset in a dedicated `api` app · SimpleJWT · Swagger docs |
| **4** | **Availability** | Recurrence rules, hours and JSON breaks · validation shared by both booking forms |
| **5** | **Lab Module** | Test requests · technician queue · file uploads · results visible to patient and doctor |
| **6** | **Prescriptions** | JSON medicines with dynamic rows · doctor write page · patient view · browser printing |
| **7** | **Notifications** | Single `notify()` write path · 9 triggers · bell with unread count · Gmail SMTP · Celery + Redis + Beat |
| **8** | **Dashboards** | Reception analytics with conditional aggregation · Chart.js · medical history · CSV export |
| **9** | **Frontend Rebuild** | All 20 screens rebuilt from a Figma design · Tailwind · role-grouped templates · profile completion flow |
| **10** | **Auth Polish & Hardening** | Email-or-username login · password reset · API permission fixes · explicit role gates |
| **11** | **Deployment** | Whitenoise · gunicorn · Neon PostgreSQL · HTTPS settings · worker-less Celery · Brevo email · scheduled cron |

---

## 📌 Status

**Live and feature-complete across all four roles** → [smart-opd-managment-system.onrender.com](https://smart-opd-managment-system.onrender.com)

Known gaps, all deliberate for a free-tier deployment:

| Gap | Effect | Fix when it matters |
|:----|:-------|:--------------------|
| Uploaded files sit on ephemeral disk | Lab results vanish on every redeploy | Cloudinary or S3 |
| Media URLs have no login check | Anyone with the link can open a result | Serve files through a permission-checked view |
| No automated test suite | Every check so far was run by hand | pytest-django |
| Free instance sleeps after 15 min | ~50 s cold start | A scheduled ping keeps it awake |
| Replacing a lab result keeps the old file | Orphaned uploads accumulate | Delete on replace |

---

<div align="center">

**Built while learning Django from scratch — one step at a time**

*Star ⭐ this repo if you found it useful!*

<i>Designed & Developed by Prince</i>

</div>
