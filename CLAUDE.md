# CLAUDE.md — Smart OPD Management System

Auto-loads when Claude Code opens this folder. Project brief + how to help. **Full day-by-day history lives in `PROJECT_LOG.md` (not auto-loaded).** Feature/permission source of truth: `opd_roles_and_final_structure.html`. Local feature catalogue: `OPD_PROJECT_STATUS.md` (gitignored).

## Who is building this

**Prince** — learning Django from scratch, this project is the teaching vehicle.
- **Types every line himself.** Never pre-scaffold apps/models/views/templates or run `startproject`/`startapp` for him.
- Teach step-by-step: **what** / **why** / **how** for each command + file. Beginner-to-intermediate; explain MVT, migrations, ORM, DRF as they come up.
- Frontend built in Stitch (AI UI) + Antigravity IDE — backend/Django is the learning focus.

## What we're building

Hospital **OPD** system, 4 roles:

| Role | prefix | Core job |
|------|--------|----------|
| **Doctor** | `/doctor/*` | availability, see appointments, prescriptions, request lab tests, view results |
| **Reception/Admin** | `/reception/*` | manage users, book on behalf, all appointments, dashboard |
| **Lab Tech** | `/lab/*` | pending tests, upload PDF/image results, branded reports |
| **Patient** | `/patient/*` | find doctors, book/cancel, view prescriptions & lab results, history |

**Permission rules**: only Reception manages users; only Doctor writes prescriptions + requests lab tests; only Lab Tech uploads results; Patient+Doctor get email, only Patient gets 24-hr reminder.

## Tech stack

- **Backend**: Django 6.0.6 · DRF · SimpleJWT · drf-spectacular · ReportLab (PDFs) · Pillow (images, when needed) · python-decouple · psycopg2-binary · Whitenoise · Gunicorn. django-filter/Celery: not installed — decide per step (django-filter skipped 14d; Celery-vs-Django6-Tasks decided at Step 18).
- **Frontend**: Django templates + static via Whitenoise; HTML drafted in Stitch, polished in Antigravity.
- **DB**: SQLite dev / PostgreSQL prod (Render). Python 3.14.2, venv in `.venv/`.
- **Deploy**: Render (no Docker). `requirements.txt` at repo root; `Procfile` in `backend/` (`web: gunicorn config.wsgi --chdir backend`). Auto-deploy on push to `main`.

## Folder structure

```
opd-project/                  ← repo root
├── backend/
│   ├── config/               ← settings.py, urls.py, wsgi.py
│   ├── apps/                  ← accounts, appointments, lab, prescriptions, notifications, api
│   ├── media/  (gitignored)   .env  (gitignored)  .env.example  manage.py  Procfile
├── frontend/
│   ├── templates/  (base.html + per-app dirs — Django reads here)
│   ├── static/     (css/js/img)   stitch_exports/
├── requirements.txt  (MUST be at root for Render)   .gitignore   README.md
```

Settings point at frontend: `TEMPLATES['DIRS']=[BASE_DIR.parent/'frontend'/'templates']`, `STATICFILES_DIRS=[.../'frontend'/'static']`, `MEDIA_ROOT=BASE_DIR/'media'`. `AUTH_USER_MODEL='accounts.CustomUser'`. `USE_TZ=True` + `TIME_ZONE='Asia/Kolkata'` (UTC in DB, IST on display).

## Conventions

- All folder names **lowercase** (Render = Linux, case-sensitive).
- `requirements.txt` at **root** (Render auto-detect); `Procfile` in `backend/` (`--chdir backend`).
- `.env` never committed; `.env.example` lists keys.
- One feature = one app in `backend/apps/`.
- **One parent step = one branch = one PR** (Option A). Commits: Conventional Commits, atomic. **User runs all git commands himself** — Claude gives commands only.

## Notification matrix (build in Step 18)

Booking confirmed → Patient (email+in-app) · 24-hr reminder → Patient (email) · Test requested → Lab Tech (in-app) · Result uploaded → Patient+Doctor (in-app+email) · Cancelled → Doctor (in-app) · Confirmed → Patient (in-app) · Prescription written → Patient (in-app) · Walk-in → Reception (in-app).

## Teaching roadmap

Steps 1–12 (foundation → auth): ✅ venv, Django, startproject, runserver, settings, git workflow, `accounts` app, `CustomUser` (role TextChoices), migrations, admin+superuser, URLs/views, templates, auth forms (login/register/profile, PATIENT-locked). Detail in `PROJECT_LOG.md` + `tutorial/`.

- [x] **Step 13** — `appointments` app ✅ (13a–13d, PR #3 `49887e7`). Appointment model (patient CASCADE / doctor PROTECT FKs, date+time_slot fields, status TextChoices), patient booking (ModelForm + IDOR-scoped views), doctor today-view, reception book-on-behalf + global list + filters + confirm. Role-aware nav + login redirect. `_redirect_after_action` helper.
- [x] **Step 13e** — lifecycle + time-split ✅ (PR #4 `1be41ee`). Status += COMPLETED + NO_SHOW (3 terminal states); complete/no-show views; terminal-state-aware buttons; `doctor_history` (`__lte`) + `doctor_upcoming` (`__gt`).
- [x] **Step 14** — DRF layer ✅ (14a–14e, PR #5 `299f45d`). Double-booking `UniqueConstraint` (excl CANCELLED) + form `clean()`; `AppointmentSerializer`; role-scoped `AppointmentViewSet` + router in dedicated `api` app; SimpleJWT (`/api/token/`); drf-spectacular (`/api/docs/`).
- [x] **Step 15** — availability + cancel reason ✅ (15a–15d, PR #6 `57f4f71`). Optional `cancel_reason` shown to all roles. `DoctorAvailability` (recurrence EVERYDAY/WEEKDAYS/MON_SAT/DATE + hours + JSON breaks) = **validation layer, NOT slots** (patient booking UX unchanged; `_validate_doctor_available` in both booking forms). Schedule setup w/ unlimited breaks (getlist+cloneNode) + first-login gate + view/update (`?edit=1`).
- [ ] **Step 16 — lab module** — branch `feature/lab-module` → PR #7.
  - [x] **16a** ✅ (Day 27) — `lab` app + `LabTest` (appointment/requested_by FK PROTECT, status REQUESTED/IN_PROGRESS/DONE, `ordering=['requested_at']`) + `LabResult` (**first OneToOneField** test→result CASCADE; **first FileField** `upload_to='lab_results/'`, no Pillow) + admin + dev media serving (`static(MEDIA_URL,...)`, self-disables when DEBUG=False). Migration `lab.0001`. Commits `acd3f69`, `f552368`.
  - [x] **16b** ✅ (Day 28) — `request_test` (doctor-only, scoped `doctor=me,status=CONFIRMED` lookup = auth, one-field POST no ModelForm) + `lab_queue` (LAB-gated, `status__in=['REQUESTED','IN_PROGRESS']` + `select_related('appointment__patient','requested_by')`, oldest-first). Routes `lab:queue`+`lab:request_test`, request-test buttons on doctor CONFIRMED rows (stub — real page Step 21), LAB nav + login redirect. Typo: `appointment:` singular. Commits `ca1227f`, `a1dd151`.
  - [x] **16c** ✅ (Day 29) — `LabResultForm` (ModelForm: result_file/notes/is_normal; test+uploaded_by server-set). `start_test` (LAB-gated, `@require_POST`, from-state in lookup `status=REQUESTED` → IN_PROGRESS) + `upload_result` (GET form/POST save, `LabResultForm(request.POST, request.FILES, instance=existing)` → create-or-update, flips test → DONE). `enctype="multipart/form-data"` + `request.FILES` = the 2 pieces that make files arrive. **OneToOne trap**: 2nd result → `IntegrityError UNIQUE test_id`; fixed with `instance=getattr(test,'result',None)` (RelatedObjectDoesNotExist subclasses AttributeError → getattr default works). Upload page + queue Start/Upload buttons. Typos: `IN_PORGRESS`, `{url` missing `%` (rendered literal into href → 404 with `%7Burl...`). Commits `9af644e`, `56da13b`.
  - [ ] **16d** — ReportLab branded PDF + FileResponse download.
- [ ] **Step 17 — prescriptions** — Prescription (OneToOne Appointment, medicines JSONField, only on COMPLETED), doctor write (dynamic rows = getlist pattern), patient view, PDF.
- [ ] **Step 18 — notifications + background tasks** — Notification model + 8 triggers (matrix) + bell + email. **DECIDE: Celery+Redis vs Django 6 built-in Tasks** (lean built-in) for 24-hr reminder + auto-expire stale PENDING → CANCELLED. NOTE: never auto-complete CONFIRMED (confirmed ≠ visited).
- [ ] **Step 19 — dashboard + exports + history** — reception stats (annotate/Count → Chart.js), patient history (prefetch_related), CSV/Excel.
- [ ] **Step 20 — deploy** — Whitenoise + prod settings (DEBUG off, env vars, PostgreSQL) + Render + live URL.
- [ ] **Step 21 — frontend + README (LAST)** — Stitch → Antigravity templates, **green/red availability calendar (deferred from Step 15 — DO NOT FORGET; native date input can't style dates, needs JS calendar)**, pro README (demo GIF, badges, Swagger shot).

## Last 2 days

**Day 28 (2026-07-19) — Step 16b shipped + CLAUDE.md restructure.** `request_test` (scoped lookup = auth) + `lab_queue` (LAB-gated, `status__in` + deep `select_related`). Request-test buttons on doctor CONFIRMED rows (stub; real page Step 21), LAB nav + login redirect. Also: split day-log into `PROJECT_LOG.md`, compressed CLAUDE.md 655→~120 lines (token efficiency rules). Typo: `appointment:` singular. Commits `ca1227f`, `a1dd151`, `c51dbe2`.

**Day 29 (2026-07-20) — Step 16c shipped.** `LabResultForm` + `start_test` (from-state in lookup) + `upload_result` (`request.FILES` + `enctype`, `instance=existing` → create-or-update). OneToOne trap hit + fixed (2nd result IntegrityError → `instance=getattr(test,'result',None)`). Upload page + queue Start/Upload buttons. Typos: `IN_PORGRESS`, `{url` missing `%` (literal tag in href → weird 404). Commits `9af644e`, `56da13b`.

## Day 30 resume point — Step 16d (ReportLab PDF) → PR #7

1. On `feature/lab-module`, clean, synced. **16d is the last sub-step of Step 16.**
2. **16d (~1–1:15)**: branded PDF lab report + download.
   - `pip install reportlab` + freeze requirements.txt.
   - `lab/views.py`: `download_report(request, test_id)` — build PDF in memory (`io.BytesIO` + `reportlab.pdfgen.canvas`), draw hospital header + patient name + test name + result/notes + normal/abnormal flag + technician + date; return `FileResponse(buffer, as_attachment=True, filename=...)`.
   - **Access scoping**: patient (own appointment), doctor (requested_by/appointment doctor), lab, reception — use a `Q(...) | Q(...)` ownership lookup like `cancel_appointment`; only when `test.status == DONE`.
   - Download button on: patient my_appointments (or a results page), doctor pages, lab queue history.
   - **New concepts**: `io.BytesIO` (in-memory file), ReportLab canvas drawing, `FileResponse(as_attachment=True)`.
3. Then docs + **PR #7** closes Step 16. Next: Step 17 prescriptions (same PDF pattern reused).

## Running grep-list (silent typos — pass `check`, crash at request)

Scan user-typed code before declaring clean: enum-vs-field casing (`Model.Status.X` vs `.status`, both definition + usage) · namespace singular/plural (`appointment:` vs `appointments:`) · wrong namespace on shared name (`profile` = accounts) · transposed model attrs (`ForeingKey`, `roel`) · **return/branch indentation in multi-branch views** (mis-indented return → wrong role lands + dead code; valid Python) · context-dict key misspelling (`'appiontments'` → silently empty page) · JSON key typos (`'ends'`) · `forms.erros`/`.error` plural drops · `{% csrf token %}` missing underscore · `' %}`→`%'}` scramble · missing `%` in `{% url %}` · `<form action="post">` (should be `method=`) · loose HTML between `<td>`s (`check` passes, renders wrong) · quoted class in `router.register` · missing trailing slash on POST routes.

## Teaching-style rule (Day 9)

Expert-teacher voice: use **real Django terms** when the topic needs them (migration, ORM, decorator, serializer, QuerySet, field lookup…), pair each with a **worked example** (bold term → 1-line def → 2-3 line code → "why it matters"). Cut status-jargon (orthogonal/idempotent/ambient). Day 10 addition: **animate the mechanic** — say what physically happens in memory/DB/network, not just "prevents X". Voice anchors: `tutorial/03,05,07`. Concept-check (2-3 Qs) after teaching; correct wrong mechanics honestly.

## Step chunking rule (Day 13)

Session budget = **1–1:30 hr**. BIG step (4+ files OR 5+ concepts OR 2+ hrs OR multi-feature) → split into sub-steps (13a…) each ~1–1:30 hr. Not big → one session. **One branch + one PR per parent step** (Option A). Enforced: (1) pre-session scope check + confirm before code; (2) hard stop at budget — WIP commit or revert, never "15 more min".

## Feedback rules (from memory)

- **Incremental tutorial** (Day 14): write tutorial + docs commit per sub-step, not bulk at parent end (exception: user may override, e.g. all-13e-together).
- **Architecture preference** (Day 22): user welcomes debate — make the technical case ONCE, then land on his call; don't re-litigate the same point across turns. He values clean industry structure (dedicated `api` app, org-by-layer).

## How to help

1. Explain before code; give the command/code to type.
2. One step at a time; wait for confirmation.
3. Refer to this file + `opd_roles_and_final_structure.html` — don't re-derive. Old step detail → `PROJECT_LOG.md`.
4. Update roadmap checkboxes when a step completes.
5. Typo-sweep user-typed code (grep-list above) before "no issues".
6. Caveman voice OK for summaries/headers when active; **clear prose for teaching**.

## Token efficiency (Day 28, revised Day 29)

- **`PROJECT_LOG.md` = complete history, appended EVERY working day at wrap** (not only when a day rolls off CLAUDE.md). Never auto-loaded — open only to debug an old step. Entry format: `### Day N (date) — Step X shipped` + one paragraph (what shipped, key gotcha, commits).
- **CLAUDE.md** keeps static info + roadmap + **last 2 days** (short recap) + resume point + rules. Adding a new day → drop the oldest of the two (it's already in PROJECT_LOG, so nothing to migrate).
- **Wrap checklist**: tutorial section → tutorial/README → CLAUDE.md (roadmap + 2-day window + next resume) → **PROJECT_LOG.md append** → memory buffers → docs commit.
- One running grep-list (above), not per-day copies. Reference files, don't repaste. Review `/memory` weekly, delete superseded entries.
