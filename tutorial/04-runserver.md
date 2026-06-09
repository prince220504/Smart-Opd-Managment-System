# Step 4 — First `runserver` + What WSGI Means

## What we did here

Started Django's **development server** with one command and visited the project in a browser for the first time. Saw the "🚀 The install worked successfully!" rocket page.

Along the way: learned what a web server actually does, what WSGI is, and why production uses a different server than this one.

## The command

```bash
cd backend
python manage.py runserver
```

Two things happen:

1. `manage.py` sets the env var so Django knows to load `config/settings.py`.
2. The `runserver` sub-command starts a tiny built-in web server on `http://127.0.0.1:8000/`.

Typical output:

```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).

You have 18 unapplied migration(s). ...
Run 'python manage.py migrate' to apply them.

December 06, 2026 - 22:50:00
Django version 6.0.6, using settings 'config.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

Plus one warning:

```
WARNING: This is a development server. Do not use it in a production setting.
```

Both are **normal and expected** — not errors. The "18 migrations" warning means the built-in apps' DB tables haven't been created yet (we fix in Step 8). The "do not use in production" is Django shouting at every dev that this server is dev-only.

## The request/response cycle

The most important diagram in web development:

```
Browser                          Django (runserver)
   |                                    |
   |  --- HTTP GET /  ----------------> |
   |                                    |
   |                            URL router (urls.py)
   |                                    |
   |                                view function
   |                                    |
   |                            HTTP Response
   |                            (HTML + status 200)
   |                                    |
   |  <--- HTTP 200 + HTML ------------ |
   |                                    |
Browser renders HTML
```

Every page load, every form submission, every API call follows this loop. Django's job is to turn an HTTP request into an HTTP response.

## What is `runserver`?

A **lightweight development-only** web server bundled with Django. You don't need Apache or Nginx during development. It's small, fast to start, and has two superpowers:

1. **Auto-reload** — when you save a `.py` file, the server restarts automatically.
2. **Helpful error pages** — when something crashes (and `DEBUG = True`), Django shows a beautiful page with full stack trace, local variables, and SQL queries.

> **Never use `runserver` in production.** It is single-threaded, has no SSL, no process manager, no security hardening. In production we run Gunicorn (a real WSGI server). Render handles all of that for us.

## What is WSGI?

**WSGI** (Web Server Gateway Interface) is a **calling convention** — a Python standard that defines how a web server should talk to a Python web framework.

It's just a function signature:

```python
def application(environ, start_response):
    # environ = dict with request data (URL, headers, body, ...)
    # start_response = callback to set status + response headers
    ...
    return [b"Hello world"]
```

Any WSGI server (Gunicorn, uWSGI, mod_wsgi) can call any WSGI framework (Django, Flask, Pyramid).

That's why `config/wsgi.py` exposes one variable:

```python
application = get_wsgi_application()
```

`runserver` itself is a small WSGI server — it uses `application` from `wsgi.py` under the hood. So does Gunicorn. The difference: `runserver` is simple and dev-friendly; Gunicorn is multi-process, production-grade.

This is why the `Procfile` will say:

```
web: gunicorn config.wsgi --chdir backend
```

We tell Gunicorn: "go into `backend/`, import `config.wsgi`, find the `application` variable, start serving."

## Port and binding

`runserver` defaults to `127.0.0.1:8000`.

- `127.0.0.1` (`localhost`) means "only this machine can connect." Safer for dev.
- `8000` is the default port. Any free port works.

Overrides:

```bash
python manage.py runserver 9000             # different port
python manage.py runserver 0.0.0.0:8000     # accept from any IP (phone on same wifi)
```

## How we did it

```bash
where python                # confirm venv
cd backend                  # manage.py lives here
python manage.py runserver  # boot server
# Visit http://127.0.0.1:8000/        → rocket page
# Visit http://127.0.0.1:8000/admin/  → admin login (don't try logging in yet)
# Ctrl+C to stop
```

## Gotchas

- **Run from the folder containing `manage.py`.** Run from project root and you get `can't open file 'manage.py'`. Either `cd backend` first, or `python backend/manage.py runserver`.
- **"Port 8000 is already in use"** — kill the other process or pick another port: `runserver 8001`.
- **"18 unapplied migrations" warning is NORMAL** — Django's built-in apps (`auth`, `admin`, `contenttypes`, `sessions`) have their own tables. We `migrate` in Step 8.
- **`db.sqlite3` will appear automatically** — first time the admin route is touched, Django creates the empty SQLite file. Add `*.sqlite3` to `.gitignore`.
- **Auto-reload limits** — `.py` edits reload the server; template `.html` edits don't need reload; `settings.py` edits sometimes need a manual restart.

## What we have NOT done yet

- No custom views. The rocket page is hardcoded inside Django.
- No DB tables. The 18-migrations warning is the proof.
- No user accounts. Admin form exists but no superuser yet.
- `settings.py` still uses defaults — not yet pointing at our `frontend/templates/`.

## Revise (3-line summary)

1. `python manage.py runserver` starts Django's dev-only server at `http://127.0.0.1:8000/`; it auto-reloads on file save and shows rich error pages.
2. Every web request follows: Browser → URL router → view function → HTTP response → Browser renders.
3. **WSGI** is the Python ↔ web-server calling convention; `wsgi.py` exposes the `application` variable that `runserver` (dev) and Gunicorn (prod) both call.

---

**Next:** [Step 5 — `settings.py` walkthrough](05-settings.md)
