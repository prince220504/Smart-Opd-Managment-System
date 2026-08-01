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

- **Backend**: Django 6.0.6 · DRF · SimpleJWT · drf-spectacular · Pillow (images, when needed) · python-decouple · psycopg2-binary · Whitenoise · Gunicorn. django-filter/Celery/ReportLab: not installed — decide per step (django-filter skipped 14d; ReportLab built then removed at 16d — direct file download beat a generated PDF; Celery-vs-Django6-Tasks decided at Step 18).
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

## Notification matrix (amended Day 38 — email trimmed)

Booking created (both entry points) → Patient (**email**+in-app) · 24-hr reminder → Patient (email, 18e) · Test requested → Lab Tech (in-app) · Result uploaded → Patient (**email**+in-app) + Doctor (**in-app only**) · Cancelled → other party (in-app) · Confirmed → Patient (in-app) · Prescription written → Patient (in-app) · Walk-in → Reception (in-app).

**Rule (Prince's call, Day 38): email is for people who aren't in the app; in-app for people who live in it.** Doctor sees 30 consults/day with the tab open → mailing every result = alert fatigue → they stop reading email entirely. Original matrix said result→patient+doctor email; doctor email dropped. 3 of 8 events mail.

## Teaching roadmap

Steps 1–12 (foundation → auth): ✅ venv, Django, startproject, runserver, settings, git workflow, `accounts` app, `CustomUser` (role TextChoices), migrations, admin+superuser, URLs/views, templates, auth forms (login/register/profile, PATIENT-locked). Detail in `PROJECT_LOG.md` + `tutorial/`.

- [x] **Step 13** — `appointments` app ✅ (13a–13d, PR #3 `49887e7`). Appointment model (patient CASCADE / doctor PROTECT FKs, date+time_slot fields, status TextChoices), patient booking (ModelForm + IDOR-scoped views), doctor today-view, reception book-on-behalf + global list + filters + confirm. Role-aware nav + login redirect. `_redirect_after_action` helper.
- [x] **Step 13e** — lifecycle + time-split ✅ (PR #4 `1be41ee`). Status += COMPLETED + NO_SHOW (3 terminal states); complete/no-show views; terminal-state-aware buttons; `doctor_history` (`__lte`) + `doctor_upcoming` (`__gt`).
- [x] **Step 14** — DRF layer ✅ (14a–14e, PR #5 `299f45d`). Double-booking `UniqueConstraint` (excl CANCELLED) + form `clean()`; `AppointmentSerializer`; role-scoped `AppointmentViewSet` + router in dedicated `api` app; SimpleJWT (`/api/token/`); drf-spectacular (`/api/docs/`).
- [x] **Step 15** — availability + cancel reason ✅ (15a–15d, PR #6 `57f4f71`). Optional `cancel_reason` shown to all roles. `DoctorAvailability` (recurrence EVERYDAY/WEEKDAYS/MON_SAT/DATE + hours + JSON breaks) = **validation layer, NOT slots** (patient booking UX unchanged; `_validate_doctor_available` in both booking forms). Schedule setup w/ unlimited breaks (getlist+cloneNode) + first-login gate + view/update (`?edit=1`).
- [x] **Step 16 — lab module** ✅ (16a–16e, Day 31, PR #7) — branch `feature/lab-module`. Auth-extras (forgot-pw, profile-photo) that shared the old step title **moved to Step 21** (forgot-pw needs Step 18 SMTP; both frontend-shaped).
  - [x] **16a** ✅ (Day 27) — `lab` app + `LabTest` (appointment/requested_by FK PROTECT, status REQUESTED/IN_PROGRESS/DONE, `ordering=['requested_at']`) + `LabResult` (**first OneToOneField** test→result CASCADE; **first FileField** `upload_to='lab_results/'`, no Pillow) + admin + dev media serving (`static(MEDIA_URL,...)`, self-disables when DEBUG=False). Migration `lab.0001`. Commits `acd3f69`, `f552368`.
  - [x] **16b** ✅ (Day 28) — `request_test` (doctor-only, scoped `doctor=me,status=CONFIRMED` lookup = auth, one-field POST no ModelForm) + `lab_queue` (LAB-gated, `status__in=['REQUESTED','IN_PROGRESS']` + `select_related('appointment__patient','requested_by')`, oldest-first). Routes `lab:queue`+`lab:request_test`, request-test buttons on doctor CONFIRMED rows (stub — real page Step 21), LAB nav + login redirect. Typo: `appointment:` singular. Commits `ca1227f`, `a1dd151`.
  - [x] **16c** ✅ (Day 29) — `LabResultForm` (ModelForm: result_file/notes/is_normal; test+uploaded_by server-set). `start_test` (LAB-gated, `@require_POST`, from-state in lookup `status=REQUESTED` → IN_PROGRESS) + `upload_result` (GET form/POST save, `LabResultForm(request.POST, request.FILES, instance=existing)` → create-or-update, flips test → DONE). `enctype="multipart/form-data"` + `request.FILES` = the 2 pieces that make files arrive. **OneToOne trap**: 2nd result → `IntegrityError UNIQUE test_id`; fixed with `instance=getattr(test,'result',None)` (RelatedObjectDoesNotExist subclasses AttributeError → getattr default works). Upload page + queue Start/Upload buttons. Typos: `IN_PORGRESS`, `{url` missing `%` (rendered literal into href → 404 with `%7Burl...`). Commits `9af644e`, `56da13b`.
  - [x] **16d** ✅ (Day 30) — patient **My Tests** page (`my_tests` view: `appointment__patient=` filter + `select_related('appointment','result')`) showing test name/status/lab-tech note/result link. Design turn: built ReportLab branded-PDF download first, then **cut it** — tech's raw upload can carry real diagnostic content a text summary can't, and two downloads per test confused the UX; result link now points straight at `result.result_file.url`, `download_report` view/url/reportlab dependency removed entirely.
  - [x] **16e** ✅ (Day 31) — doctor-side test visibility. `test_detail` view (scoped `appointment__doctor=me` = IDOR guard) + template (name/status/normal/tech/date + `result_file.url` download). `doctor_today`/`doctor_records` loop `appt.lab_tests.all` — **loop OUTSIDE the status if/elif** (was gated behind CONFIRMED → vanished on COMPLETED rows where results matter); `{% empty %}` renders `-`. `prefetch_related('lab_tests__result')` (reverse FK one→many needs prefetch not select_related). `doctor_history`→`doctor_records` rename. Typos: `prefetech_related`, `test_details.html` mismatch, `appointment:` singular + missing `%` in `{% url %}`. **Closes Step 16.**
- [x] **Step 17 — prescriptions** ✅ (17a–17d, branch `feature/prescriptions`) — Prescription (OneToOne Appointment, medicines JSONField, only on COMPLETED), doctor write (dynamic rows = getlist pattern), patient view, PDF.
  - [x] **17a** ✅ (Day 32) — `prescriptions` app + `Prescription` model (OneToOne appt CASCADE = `appointment.prescription`; **first project `JSONField`** `medicines` default=list; diagnosis/advice/created_at) + admin + migration `0001`. COMPLETED-gate deferred to 17b view (not model). Zero typos.
  - [x] **17b** ✅ (Day 32) — doctor write page in `prescriptions` app: `PrescriptionForm` (diagnosis/advice; appointment+medicines NOT form fields) + `write_prescription` view (`get_object_or_404(..., doctor=me, status=COMPLETED)` = auth + COMPLETED-gate in one query; `instance=getattr(appt,'prescription',None)` = create-or-update, no OneToOne IntegrityError) + `getlist`×4 + `zip` + `if name:` → medicines JSON + cloneNode "+ Add medicine" + `prescriptions:write` route (config include) + COMPLETED-row button on doctor_records. Bug: `getElementByID` (JS case-sensitive → clone built but never appended, "+ Add" silently dead) → `getElementById`.
  - [x] **17c** ✅ (Day 33) — patient view page (`view_prescription`, `get_object_or_404(Prescription, appointment__id=id, appointment__patient=me)` = cross-FK IDOR lookup) + `prescriptions:view` route + read-only `view.html` (loops `medicines` JSON) + COMPLETED-row link on `my_appointments`. Doctor read-back = **nothing built** (17b write button already loads existing). UX: split doctor `Action` column → **Action / Tests / Prescription** on both `doctor_records` + `doctor_today` (latter gained a Prescription col). Killed reverse-OneToOne N+1: `select_related('...','prescription')` on both patient + doctor_today queries. Design: Request Test stays on CONFIRMED (live-consult order), not COMPLETED.
  - [x] **17d** ✅ (Day 34) — prescription "PDF" with **zero server code**. Chose `window.print()` + `@media print` CSS over ReportLab (the rendered HTML *is* the doc; no library/view/route/layout). `<style>` hides `header, footer, .no-print` on print; `<button onclick="window.print()">` → browser "Save as PDF". Default filename = `document.title`, so title block rebuilt to `Prescription -{patient}-{date|Y-m-d}` (browser only suggests). Also closed 17c gap: `view.html` never rendered `advice` → added `{% if prescription.advice %}` block. 3 silent template typos (Prince caught on test): `prescrition.advice` (missing `p` → blank under correct `{% if %}`), `prescription.appointment_date` in title (dropped `.appointment` hop). Template-only, no Python errors. **Closes Step 17.**
- [ ] **Step 18 — notifications + background tasks** 🚧 — Notification model + 8 triggers (matrix) + bell + email. **DECIDED (Day 35): Celery + Redis** (Prince's call over Django 6 Tasks) for 24-hr reminder + auto-expire stale PENDING → CANCELLED. NOTE: never auto-complete CONFIRMED (confirmed ≠ visited). Sub-step split: 18a model · 18b in-app triggers · 18c bell UI · 18d **email + decouple/.env** · 18e Celery/Redis background tasks (email moved 18c→18d Day 37; Celery split 18d→18e Day 38 — email alone was a full session).
  - [x] **18a** ✅ (Day 35) — `notifications` app + `Notification` model (recipient FK→AUTH_USER_MODEL CASCADE `related_name='notifications'`, message, `notification_type` TextChoices 6 cats BOOKING/REMINDER/TEST/RESULT/PRESCRIPTION/STATUS, `link` plain CharField = stored URL string not FK, `is_read`, `created_at`, `ordering=['-created_at']`) + admin (`recipient__username` search) + migration `0001`. Data layer only — no triggers/bell/email. Zero typos.
  - [x] **18b** ✅ (Day 36, commits `4deb381` + docs `34b519e`) — `notifications/services.py` `notify(recipient, message, notification_type, link='')` = **single write path** (chosen over 7× inline `objects.create` and over signals — signals fire on every save incl. admin) + **7 triggers**: book→patient · reception_book→patient · confirm→patient · cancel→**other party** (`[patient, doctor]` + `if user != request.user` = 2 lines covers all 3 canceller roles; Model `__eq__` compares PK, safe vs `SimpleLazyObject`) · request_test→**all LAB users** (`User.objects.filter(role='LAB')` loop, one row each — `is_read` is per-row) · upload_result→patient **+** doctor (2 calls not a loop — different links) · write_prescription→patient. `reverse()` = Python `{% url %}`, `args=[...]` for params (**`check` does NOT catch `NoReverseMatch`** — resolved all 5 in shell). **Rule: `notify()` after `.save()`, INSIDE the state guard** (guard = idempotency; outside it a refreshed POST double-writes). Typo: `appointment.patent` → AttributeError *after* file saved + 1st notify written (half-done write; `transaction.atomic()` later). Accepted dupe: `write_prescription` is create-or-update → edit re-notifies (noise not bug, judge in 18c). Tested 4/7 incl. the branchy cancel; rest verify free once bell renders.
  - [x] **18c** ✅ (Day 37, 6 commits →`e657a5a`) — bell + in-app delivery. `notification_list` (`user.notifications.all()` = 18a related_name, ordering free) + `open_notification` (IDOR in lookup `recipient=request.user`; flips `is_read` **and** redirects — one user action, one view; `redirect(link or 'notifications:list')` since `link` blank-able). Routes `notifications:list`/`:open` + config include. **First context processor** `unread_count` — `{}` for AnonymousUser (**must never raise: runs every render**), else `.count()` (not `len()`); dotted path in TEMPLATES; alternative = 20 view contexts. Bell in base.html outside role chain, `{% if unread_count %}` hides `(0)`. List tmpl: unread `<strong>`, `get_notification_type_display`, `{% empty %}`. **Dropdown skipped** (rows every request for rarely-opened panel). All 7 triggers browser-verified. **Bell exposed 2 latent bugs** (fixed): cancel sent both parties to `my_appointments` (patient FK → doctor saw empty table) → per-recipient ternary; `'prescription:write'` singular in doctor_today (17c, only renders on COMPLETED). **`link` = frozen string** — view fix doesn't repair old rows (`.update(link=reverse(...))`). Prescription-edit dupe: **keep** (edit *is* news). Typos: `user.notification` singular, `<storng>`.
  - [x] **18d** ✅ (Day 38, 4 commits →`9438051`) — **email + first secrets out of git**. `pip install python-decouple` (was in stack list, never installed) → `backend/.env` (gitignored via `*.env`) + `.env.example` (committed; `*.env` matches files *ending* `.env`, so `.example` is safe). `SECRET_KEY`/`DEBUG` moved out of settings — `config('KEY')` no default = **required, boots or crashes**; **`cast=bool` mandatory** (`bool('False')` is `True` → prod would run DEBUG on). `EMAIL_*` block, `DEFAULT_FROM_EMAIL = EMAIL_HOST_USER` (Gmail rejects a From it didn't authenticate). Built on `console.EmailBackend`, flipped one string to `smtp.EmailBackend` to go live. `notify(..., email=False)` = **keyword arg with default → all 7 existing calls untouched**; `Notification.Type(x).label` = `get_..._display` from Python; `from_email=None` → DEFAULT_FROM_EMAIL; `and recipient.email` guard (LAB user is blank). 3 call sites flagged (book · reception_book · upload_result→patient). `fail_silently=True` = placeholder for 18e Celery retry (mail failure must not 500 a saved booking). **Matrix amended — doctor result email dropped** (see rule above). Live Gmail send verified shell + browser. Typos: missing `EMAIL_PORT` (default 25 → would timeout only after SMTP switch), `return Notification` (class not row — `check` passes, invisible till a caller uses the return).
- [ ] **Step 19 — dashboard + exports + history** — reception stats (annotate/Count → Chart.js), patient history (prefetch_related), CSV/Excel.
- [ ] **Step 20 — deploy** — Whitenoise + prod settings (DEBUG off, env vars, PostgreSQL) + Render + live URL.
- [ ] **Step 21 — frontend + README (LAST)** — Stitch → Antigravity templates, **green/red availability calendar (deferred from Step 15 — DO NOT FORGET; native date input can't style dates, needs JS calendar)**, pro README (demo GIF, badges, Swagger shot). **Moved from Step 16 (Day 31): (a) forgot-password flow — Django `PasswordResetView` + reset templates, on top of Step 18 Gmail SMTP; (b) profile-photo upload — `ImageField` on CustomUser + Pillow + resize 400×400.**

## Last 2 days

**Day 37 (2026-07-30) — Step 18c.** Bell = notifications finally visible. Views: list (`user.notifications.all()`) + open (flip `is_read` → redirect to `link`; auth in the lookup). **First context processor** — the only way into `base.html` without touching ~20 view contexts; guard `is_authenticated` and return `{}` because it **runs on every render incl. the login page and must never raise**; `.count()` asks the DB for one int, `len(qs)` fetches rows to throw away. Dropdown skipped (ponytail). **Payoff: clickable notifications exposed 2 bugs invisible to `check` and shell** — cancel pointed a doctor at a patient-FK page (silently empty table) → per-recipient ternary; `'prescription:write'` singular from 17c, only renders on COMPLETED rows so it had never fired. 18a's string `link` **never re-resolves**: view fix left the old row wrong, needed `.update(link=reverse(...))` — and my first repair hardcoded the path and got it wrong, same lesson twice. All 7 triggers browser-verified. Prescription-edit dupe **kept**. Typos: `user.notification` (singular reverse accessor), `<storng>` (unknown tag → styling silently gone). Email pushed to 18d. 6 commits, split backend/frontend + new/edited per Prince's rule.

**Day 38 (2026-08-01) — Step 18d: email + secrets.** First credential this project keeps out of git. `python-decouple` (listed in the stack since Day 1, never actually installed) → `backend/.env` + committed `.env.example`; `SECRET_KEY`/`DEBUG` left `settings.py`. Two mechanics that bite silently: `config('KEY')` with **no default** means required — missing key refuses to boot, which is what you want from a secret; and **`cast=bool`** exists because `.env` values are strings and `bool('False')` is `True`, so a missing cast ships prod in DEBUG. Email built on `console.EmailBackend` (prints to the runserver terminal, sends nothing), then one string → `smtp.EmailBackend` for the live Gmail send. The shared `notify()` grew `email=False` — **a keyword arg with a default is how a helper with 7 callers takes new behaviour without touching any of them**. **Prince's design call: doctor gets no result email.** He argued a doctor with 30 patients/day drowns; correct — email is for people who aren't in the app, in-app is for people who live in it. Matrix amended, 3 of 8 events mail. `fail_silently=True` = deliberate placeholder for 18e's Celery retry: a dead SMTP server must not 500 a booking that already saved. Typos: no `EMAIL_PORT` (Django default 25 → would have timed out only *after* the SMTP switch), `return Notification` (class, not row — `check` passes; invisible until a caller uses the return value). Shell + browser verified, 4 commits.

## Day 39 resume point — Step 18e Celery + Redis

1. **New session** — `/clear`; point Claude at this resume + `PROJECT_LOG.md` Days 37–38 only.
2. **18e Celery + Redis** (decided Day 35 over Django 6 Tasks): 24-hr reminder → Patient (email, the `REMINDER` type is defined in 18a and still unused) + auto-expire stale PENDING → CANCELLED. **Never auto-complete CONFIRMED** (confirmed ≠ visited). Needs Redis running locally on Windows — check that first, it's the setup risk.
3. **Then move `notify()`'s `send_mail` into a task** so `fail_silently=True` can go and failures get retried instead of dropped.
4. Step 18 closes after 18e → merge `feature/notifications` → PR #8.

## Running grep-list (silent typos — pass `check`, crash at request)

Scan user-typed code before declaring clean: enum-vs-field casing (`Model.Status.X` vs `.status`, both definition + usage) · namespace singular/plural (`appointment:` vs `appointments:`) · wrong namespace on shared name (`profile` = accounts) · transposed model attrs (`ForeingKey`, `roel`) · **return/branch indentation in multi-branch views** (mis-indented return → wrong role lands + dead code; valid Python) · context-dict key misspelling (`'appiontments'` → silently empty page) · JSON key typos (`'ends'`) · `forms.erros`/`.error` plural drops · `{% csrf token %}` missing underscore · `' %}`→`%'}` scramble · missing `%` in `{% url %}` · `<form action="post">` (should be `method=`) · loose HTML between `<td>`s (`check` passes, renders wrong) · quoted class in `router.register` · missing trailing slash on POST routes · **reverse-accessor singular/plural** (`user.notification.all()` vs `related_name='notifications'` → AttributeError at request) · **misspelled HTML tag** (`<storng>` → browser renders unknown tag as plain inline, styling silently vanishes).

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

## Token efficiency (Day 28, revised Day 29, Day 30)

- **`PROJECT_LOG.md` = complete history, appended EVERY working day at wrap** (not only when a day rolls off CLAUDE.md). Never auto-loaded — open only to debug an old step. Entry format: `### Day N (date) — Step X shipped` + one paragraph (what shipped, key gotcha, commits).
- **CLAUDE.md** keeps static info + roadmap + **last 2 days** (short recap) + resume point + rules. Adding a new day → drop the oldest of the two (it's already in PROJECT_LOG, so nothing to migrate).
- **Wrap checklist**: tutorial section → tutorial/README → CLAUDE.md (roadmap + 2-day window + next resume) → **PROJECT_LOG.md append** → memory buffers → docs commit.
- One running grep-list (above), not per-day copies. Reference files, don't repaste. Review `/memory` weekly, delete superseded entries.
- **New session per parent step (Day 30)**: don't keep extending one long-running Claude Code session across unrelated sub-steps — each carried-forward turn re-sends the full conversation history (token tax scales with session length, not with the work left to do). Start a **new session** (`/clear` or new window) when beginning a new sub-step; point Claude only at this file's resume point (+ `PROJECT_LOG.md` if older detail is needed) instead of continuing an old thread.
