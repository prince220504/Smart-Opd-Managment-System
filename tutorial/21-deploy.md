# Step 21 — Deploy (Whitenoise · Gunicorn · Neon Postgres · Render)

Day 48. The last step. The app has worked on `runserver` for 47 days; this step makes it work
on a machine that is not yours, for people who are not you.

---

## The one idea behind the whole step

Development and production are the **same code** reading **different values**.

Nothing here forks the project into a "dev version" and a "prod version". Every difference —
which database, which hostname, whether HTTPS is forced — is one environment variable. That is
why the whole step is mostly `settings.py` and almost no new logic.

---

## 1. Three packages that were missing

### Gunicorn — the real web server

**What:** the program that runs your Django code in production.

**Why:** `runserver` is a rehearsal-room piano. It handles one visitor at a time and Django's own
docs say never use it in production. Gunicorn starts several copies of your app and hands each
arriving visitor to a free one.

**How:**

```
gunicorn config.wsgi --chdir backend
```

`--chdir backend` because gunicorn runs from the repo root (where `requirements.txt` lives) but
`config/` sits one level down.

### Whitenoise — serves CSS/JS

**What:** static file serving, inside your app.

**Why:** this is the one that surprises everyone. `runserver` serves `main.css` as a *favour*, and
only while `DEBUG=True`. Turn DEBUG off and Django stops serving static files entirely — the site
loads with **zero styling**, no error, just a naked page.

**How:** one middleware line, second in the list:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    ...
]
```

Position matters. Middleware is a chain of reception desks a request passes through. Whitenoise
goes at the **entrance** so a request for `main.css` is answered and sent back immediately, without
Django opening a session, hitting the database for a user, or checking a CSRF token.

### psycopg — the Postgres driver

**What:** the translator between Django's ORM and Postgres' wire protocol.

**Why:** SQLite needed nothing because Python ships an SQLite driver built in. Postgres is a
separate server, so it needs a separate driver.

**Note:** use `psycopg[binary]` (version 3), not `psycopg2-binary`. On Python 3.14 psycopg2 has no
prebuilt wheels and pip would try to compile C source on Windows and fail. Django 6 supports
psycopg 3 with no settings change.

---

## 2. `collectstatic` and hashed filenames

**What:** copies every static file into one folder (`STATIC_ROOT`) and gives each a
content-hashed name.

**Analogy:** a hospital where supplies live in each department's own cupboard. Fine while a runner
can fetch from any cupboard. Before opening a 24-hour counter you **collect everything into one
stockroom** so the counter staff reach into exactly one place.

**Why hashed names:** browsers cache CSS hard. Ship a fix and returning users keep the old file for
days. Put a hash of the contents in the name — `main.1f65e521.css` — and changing one character
changes the filename, so the browser is forced to fetch it. Same contents = same name = cached
forever, free.

**How:**

```python
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
```

`Compressed` also writes a gzipped copy of every file. `Manifest` writes `staticfiles.json`, the
lookup table `{% static %}` reads to find the hashed name.

**Cost:** manifest storage is strict. `{% static 'css/typo.css' %}` for a file that doesn't exist
now **raises** instead of silently 404ing. That's a feature — a build error beats a live site with
no styling.

---

## 3. `ALLOWED_HOSTS` — not paperwork, a real attack

**What:** the list of domain names your site will answer to. Django compares the browser's `Host:`
header against it and returns `400` if it doesn't match.

**Why:** Django builds absolute URLs from the `Host:` header. Password-reset emails, for example.
If your site answers to *any* hostname, an attacker requests a reset for your account through a
domain they control, Django builds `https://evil.com/reset/<token>/` into the email, and the victim
clicks it — handing over the token.

Empty was safe only because Django ignores this setting while `DEBUG=True`.

```python
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
```

Environment variables are always strings — there is no list type in an env var — so the convention
is a comma-separated string you `.split(',')` back into a list.

---

## 4. One `DATABASES` block, two databases

```python
DATABASES = {
    'default': dj_database_url.parse(
        config('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3'),
        conn_max_age=600,
    )
}
```

**Why a package:** Neon/Render hand you the database as one string —
`postgres://user:pass@host:5432/dbname` — and Django wants a dict of six keys. The fiddly parts
(passwords containing `@`, missing ports, SSL flags) are exactly where hand-written parsing breaks.

**`.parse()` not `.config()`** — this is the trap that cost 20 minutes. `dj_database_url.config()`
reads **`os.environ` only**; it knows nothing about `.env` files. decouple reads `.env`. The two
never talk, so a `DATABASE_URL` in `.env` was invisible and the site silently stayed on SQLite.
`.parse()` takes the string you hand it, so `config()` does the lookup and both worlds work.

> **Rule: a library that reads `os.environ` directly is blind to your `.env` file.**
> Every setting in this project goes through `config()` — that includes ones you feed to a library.

**`conn_max_age=600`** — keep a connection open and reuse it for 10 minutes. Django's default opens
a fresh connection every request and throws it away. Nearly free for SQLite (a file on disk); for
Postgres it's a TCP handshake plus authentication, ~30ms, on *every* request.

**The fallback is the dev value.** No `DATABASE_URL` set → SQLite → a fresh clone of the repo runs
with almost no `.env` at all. Production is the side that overrides.

---

## 5. The HTTPS block

```python
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
```

**`SECURE_PROXY_SSL_HEADER` — the line that saves you from an infinite redirect loop.**
Render does not hand HTTPS to your app. Render's front server accepts the encrypted connection,
decrypts it, and forwards a **plain http** request to gunicorn. Django sees http, and with
`SECURE_SSL_REDIRECT = True` says "redirect to https" — the browser goes to https, Render decrypts
again, forwards plain http again, Django redirects again. Forever. `ERR_TOO_MANY_REDIRECTS`, the
single most common Django-on-Render failure. This line says *trust `X-Forwarded-Proto`*.

**`SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE`** — only send these cookies over an encrypted
connection. Without them one accidental http request leaks the session cookie in plain text, and
whoever holds that cookie **is** the logged-in user, no password needed.

**`SECURE_HSTS_SECONDS`** — tells the browser "for the next year, never even *try* http here." It
closes the gap *before* the redirect: normally the first request goes out over http and only then
gets redirected, and that first request is interceptable.

Treat HSTS with respect — it is the one setting here that **cannot be undone**. The browser obeys
it for a year regardless of what you change server-side. Safe on `.onrender.com`; on a custom
domain start at `3600`.

**The whole block is gated on `if not DEBUG:`** because every line breaks local development —
SSL redirect would bounce `http://127.0.0.1` to https where nothing is listening, and secure
cookies would stop you logging in over http.

---

## 6. Celery with no worker, and a clock from outside

The free tier has no Redis and no background worker. Celery was doing **two different jobs**, and
they get different answers.

### Job 1 — get email off the request

```python
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=False, cast=bool)
```

**What:** `.delay(id)` normally writes a message to Redis and returns instantly; a worker picks it
up later. Eager mode **runs the function right there**, in the web process, before returning.

**Analogy:** your booking view is a receptionist with letters to post. Normally she drops them in
the outbox and a courier collects them — she's free immediately. Eager means she walks to the
postbox herself before serving the next patient. Slower for that one patient, but the letters
definitely get posted and you employ no courier.

**Cost:** the booking POST waits ~1s for Gmail. Same task, same retry rules — only the queue step
is removed.

`CELERY_TASK_EAGER_PROPAGATES` is left off deliberately: if Gmail is down after 3 retries the
booking must still succeed. The appointment matters more than the email about it.

### Job 2 — the two daily jobs

"Run something once a day" doesn't need Celery, it needs a **clock**, and free clocks are
everywhere. A `@shared_task` function is still an ordinary Python function — the decorator only
*adds* `.delay()`. So an endpoint can call it directly:

```python
@require_GET
def run_daily_tasks(request):
    if not settings.CRON_KEY or not constant_time_compare(request.GET.get('key', ''), settings.CRON_KEY):
        raise Http404()
    return HttpResponse(
        f'reminders={send_appointment_reminders()} expired={expire_stale_appointments()}'
    )
```

A free cron service hits it once a day. Four decisions inside those five lines:

- **`constant_time_compare` not `!=`** — `!=` stops at the first differing character, so a wrong
  guess starting with the right letter takes measurably longer to reject, and an attacker reads the
  key out one character at a time. Same reasoning as Day 47's `set_password()` on the login
  not-found path.
- **`not settings.CRON_KEY` checked first** — a missing env var makes `CRON_KEY` `''`, and without
  this a request with `?key=` (empty) would match. **A forgotten env var must fail closed.**
- **`raise Http404()` not 403** — a 403 confirms the endpoint exists and invites guessing.
- **No `@login_required`** — a cron service has no session. The secret in the URL *is* the auth,
  which is why it must be `secrets.token_urlsafe(32)` and not something you'd type.

---

## 7. Media files in production

`static(settings.MEDIA_URL, ...)` returns an **empty list** when `DEBUG=False` — that's the
self-disabling dev helper from Day 27, and it's why lab PDFs 404'd the moment DEBUG went off.

```python
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
```

`serve` is the view underneath `static()`, used directly, so it runs in both modes. `re_path`
because the filename is a free-form path (`lab_results/report.pdf`) and `path()` converters can't
match slashes.

**Two known limits, written down rather than fixed:** Render's free disk is wiped on every deploy,
so uploads vanish; and media URLs have **no login check**, so anyone with the link can download a
lab result. Both are gaps, not surprises.

---

## 8. Building the live database from your laptop

Render's free tier gives no shell, so there is nowhere to run `migrate` or `createsuperuser` *on*
the server. You don't need one:

```
# temporarily in backend/.env
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/opd?sslmode=require
```

```
python backend\manage.py migrate          # 33 migrations, Day 1 to Day 47 replayed in 20 seconds
python backend\manage.py createsuperuser
```

Then **delete the line again**, or every local test writes into production.

**Migrations belong to the database, not the code.** Your SQLite has its own record of 33 applied,
Neon has its own. Same files, two independent ledgers — which is why Render's build command runs
`migrate` and honestly reports "No migrations to apply."

**Two databases on one Postgres server share nothing.** Two Django projects pointed at the *same*
database would collide on `django_migrations`, `django_content_type`, `auth_permission` and
`django_session` — identical names, one project's history overwriting the other's. A second
*database* on the same server is fully isolated. The last path segment of the URL is the whole
difference.

---

## 9. Render settings

| Field | Value |
|---|---|
| Build | `pip install -r requirements.txt && python backend/manage.py collectstatic --no-input && python backend/manage.py migrate` |
| Start | `gunicorn config.wsgi --chdir backend` |
| Root Directory | *empty* — `requirements.txt` is at the repo root, which is why CLAUDE.md insists it lives there |

Nine environment variables: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `DATABASE_URL`,
`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `CELERY_TASK_ALWAYS_EAGER=True`, `CRON_KEY`,
`PYTHON_VERSION=3.14.2`.

`CELERY_BROKER_URL` is deliberately absent — it has a default and is never dialled in eager mode.
Production secrets (`SECRET_KEY`, `CRON_KEY`) are generated fresh for Render and never written into
a file on the laptop.

---

## Gotchas

- **`db.sqllite3`** (double `l`). SQLite has no "database not found" error — a missing file is
  **created empty**. So a misspelled path doesn't fail, it silently hands you a blank database and
  your data appears to have vanished. Any other engine would have refused to connect.
- **`whitenoise.middelware`** — a bad dotted path in a settings list is an `ImportError` at boot.
  Loud, for once.
- **`HTTP_X_FORWARD_PROTO`** (missing `ED`) — just a string, never validated. Django looks for a
  header nobody sends, concludes the connection isn't secure, and `SECURE_SSL_REDIRECT` fires
  forever. Passes `check`, passes `check --deploy`, works perfectly locally because the block is
  switched off there. You'd find it staring at `ERR_TOO_MANY_REDIRECTS` on the live site.
- **`dj_database_url.config()` ignores `.env`** — see §4.
- **`runserver` vs `runserver 0.0.0.0:8000`** — plain `runserver` binds to `127.0.0.1` and only
  answers itself, so a phone on the same WiFi cannot reach it.
- **`x-render-routing: no-server`** is Render's answer, not Django's — the app was never involved.
  Usually a cold start on a spun-down free instance; wait a minute before debugging your code.

---

## WSGI vs ASGI (why gunicorn, not uvicorn)

Both are "the thing that runs your app" — Django and FastAPI are both just piles of functions.
The difference is the protocol.

**WSGI** = one consultation room, one patient at a time; the doctor **waits** with them through a
blood test. More concurrency = more rooms (gunicorn workers).
**ASGI** = a triage nurse who starts patient A, sends them for the test, and turns to B without
waiting.

WSGI is right here for three reasons:

1. **Every line of our code is synchronous.** Blocking code under uvicorn is *worse* — one
   `send_mail()` freezes the whole event loop and stops **every** request, not just that one.
2. **We already solved the waiting problem with Celery** — the queue and async solve overlapping
   problems; we picked the queue.
3. **No WebSockets.** A slow query is a patient who leaves after 2 seconds; a WebSocket is a patient
   who sits in the chair all afternoon and speaks once every ten minutes. At that duration ASGI
   stops being an optimisation and becomes the only thing that works.

`asgi.py` has existed since Day 3. If a live notification bell ever ships, the switch is one word.

**And the distinction worth keeping:** async changes **throughput** (how many at once), never
**latency** (how long one takes). Celery changes both, which is why it won.

---

## Revise

1. **Dev and prod are the same code reading different env values** — `config()` with a default, and
   the default is the dev value.
2. **DEBUG=False changes four things silently**: static files stop being served (Whitenoise fixes
   it), `ALLOWED_HOSTS` starts being enforced, media serving self-disables, and tracebacks become
   plain error pages. Run it locally *before* deploying.
3. **The proxy header line is not optional** — without `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`
   on a platform that terminates TLS is an infinite loop.
