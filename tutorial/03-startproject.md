# Step 3 — `django-admin startproject` + Scaffold Tour

## What we did here

Ran **one command** that created the skeleton of a Django project — settings, URL routing, WSGI/ASGI entry points, and the `manage.py` control script. Then walked every generated file and learned its job.

This is the moment Django stopped being "a package we installed" and became "a project we are building."

## Key concept — Project vs App

Django has two levels of organization. This is the most important Django concept to internalize early.

| Term | Meaning | Our case |
|------|--------|----------|
| **Project** | The overall website. Holds settings, URL configuration, WSGI entry. There is exactly **one** project per Django website. | `config/` (lives inside `backend/`) |
| **App** | A self-contained feature module. Models, views, URLs, templates for one slice of functionality. One project contains **many** apps. | `accounts/`, `appointments/`, `lab/`, `prescriptions/`, `notifications/`, `api/` (coming) |

Today we created the **project**. The **apps** come in Step 6 onwards.

> Analogy: a project is a hospital building. Apps are departments inside it — pharmacy, radiology, billing. The building has the shared plumbing (lights, water, security). Each department handles its own work but plugs into the building's services.

## What is `django-admin`?

A command-line tool installed automatically when you `pip install django`. Lives inside `.venv/Scripts/django-admin.exe`. You use it once — to **bootstrap** a new project. After that, every command goes through `manage.py` (which is a thin wrapper around `django-admin` tied to your specific project's settings).

## The command we ran

```bash
django-admin startproject config backend
```

Read left to right:

| Part | Meaning |
|------|--------|
| `django-admin` | The bootstrap tool |
| `startproject` | The sub-command: "create a new project skeleton" |
| `config` | **Name of the Python package** that holds settings, urls, wsgi, asgi |
| `backend` | **Destination folder** (must already exist) |

After running, the layout became:

```
backend/                    ← destination (already existed, was empty)
├── manage.py               ← project control script
└── config/                 ← Python package named "config"
    ├── __init__.py
    ├── settings.py
    ├── urls.py
    ├── wsgi.py
    └── asgi.py
```

### Why `config` and not `opd_project`?

By default, `django-admin startproject opd_project` would name the inner package `opd_project`, and `settings.py` would have `ROOT_URLCONF = 'opd_project.urls'`. That couples the package name to the business name.

Using `config` is a popular convention because:
- The settings folder describes **what it is** (configuration), not **what the business is**.
- If the business renames "OPD" to "Hospital" tomorrow, you don't rename Python imports.
- `config.settings`, `config.urls`, `config.wsgi` reads cleanly.

## The five files Django created

### `manage.py`

A small script you run for every Django operation:

```bash
python manage.py runserver
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py startapp accounts
```

It does two things:
1. Sets the environment variable `DJANGO_SETTINGS_MODULE=config.settings` so Django knows which settings to load.
2. Hands the rest of the command-line args to Django's command system.

You'll touch `manage.py` constantly. You'll edit it almost never.

### `config/__init__.py`

An **empty file**. Its mere existence tells Python "this folder is a package — you can `import` things from it." Without this file, `import config.settings` would fail.

Modern Python (3.3+) supports "namespace packages" that don't need this file, but Django still creates it for clarity.

### `config/settings.py`

The big one. Every configurable knob of your Django app lives here:

- `DEBUG` — true in development, false in production
- `ALLOWED_HOSTS` — which domain names this app responds to
- `INSTALLED_APPS` — list of every app (built-in or yours) Django should activate
- `MIDDLEWARE` — request/response interceptors (auth, CSRF, sessions, etc.)
- `DATABASES` — DB connection info (SQLite by default, PostgreSQL on Render)
- `TEMPLATES` — where Django looks for HTML files
- `STATIC_URL` / `STATICFILES_DIRS` — where CSS/JS files live
- `AUTH_USER_MODEL` — which model represents users (we'll override later)
- `SECRET_KEY` — cryptographic key for signing sessions, cookies, password resets

Step 5 is a full tour of this file. For now, just know it's the brain.

### `config/urls.py`

The **root URL router**. When a request hits the server at `/login/` or `/doctor/dashboard/`, Django looks here first to figure out which view function should answer.

Default content includes only `/admin/` (the admin panel). We add our routes here in Step 10.

### `config/wsgi.py` and `config/asgi.py`

Two entry points for production web servers.

- **WSGI** (Web Server Gateway Interface) — the old, synchronous standard. Used by Gunicorn (our production server on Render). Our `Procfile` will say `gunicorn config.wsgi`.
- **ASGI** (Asynchronous Server Gateway Interface) — the newer async standard. Used if we ever add WebSockets or async views. We don't need it for OPD, but Django creates it anyway.

You'll never touch these files. They exist so Gunicorn knows how to call your Django app.

## A note on `where python` on Windows

`where python` lists **every** `python.exe` in your `PATH`, in resolution order. The **first** entry wins. A typical Windows result:

1. `.venv\Scripts\python.exe` ← **the active one** ✅
2. `C:\Program Files\Python314\python.exe` ← global install
3. `C:\Users\...\WindowsApps\python.exe` ← Microsoft Store stub

Linux/macOS equivalent `which python` shows only the first match. Windows `where` shows all matches — same logic, different display. The first one always wins.

## Gotchas

- **Destination folder must exist.** `django-admin startproject config backend` only works if `backend/` already exists. If skipped, you get `CommandError: Destination directory '...' does not exist`. Fix: `mkdir backend` first.
- **Don't run without the destination argument.** `django-admin startproject config` (no `backend`) creates `config/` at the current location and puts `manage.py` at the project root — pollutes the root. Always pass the destination.
- **Project name must be a valid Python identifier.** `config` works. `my-project` does NOT (hyphen is illegal in Python identifiers). Stick to lowercase letters and underscores.
- **You only do this once per project.** Re-running `startproject` refuses to overwrite. To start over, delete `backend/manage.py` and `backend/config/` and run again.

## Revise (3-line summary)

1. A Django **project** holds global config; **apps** are feature modules. One project, many apps.
2. `django-admin startproject config backend` creates `backend/manage.py` plus `backend/config/{__init__.py, settings.py, urls.py, wsgi.py, asgi.py}`.
3. `manage.py` is the daily-use script; `settings.py` is the brain; `urls.py` is the router; `wsgi.py` is the production server entry point.

---

**Next:** [Step 4 — First `runserver` + WSGI](04-runserver.md)
