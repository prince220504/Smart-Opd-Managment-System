# Step 5 — `settings.py` Walkthrough (the brain of Django)

## What we did here

Two halves:

**Half 1 — Tour.** Read each section of `backend/config/settings.py` and learned what it does, why it exists, when to change it.

**Half 2 — Edit.** Made 4 small edits to wire Django to our `frontend/` folder and use Indian time.

After this, the project knows where to find templates and static files, and Indian timezone is set.

---

## Half 1 — Tour of `settings.py`

### `BASE_DIR`

```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
```

**What:** A `Path` object pointing to the **`backend/` folder** (parent of `config/`).

**Why:** Every later path (DB file, media folder, template folder) is written relative to `BASE_DIR`. Portable across machines.

**How:**
- `__file__` = path to this `settings.py`
- `.resolve()` = absolute path
- `.parent` = go up one folder → `config/`
- `.parent` again → `backend/`

So `BASE_DIR = backend/`. Therefore:
- `BASE_DIR / 'db.sqlite3'` → `backend/db.sqlite3`
- `BASE_DIR.parent` → project root
- `BASE_DIR.parent / 'frontend'` → our `frontend/` folder ✅

### `SECRET_KEY`

```python
SECRET_KEY = 'django-insecure-...'
```

Random string Django uses to sign cookies, sessions, password-reset tokens, CSRF tokens. The `django-insecure-` prefix means Django knows it's a dev key. Will move to `.env` before deploy.

### `DEBUG` and `ALLOWED_HOSTS`

```python
DEBUG = True
ALLOWED_HOSTS = []
```

- `DEBUG = True` — rich error pages with stack traces, local variables, SQL queries. Dangerous in production (leaks code paths).
- `ALLOWED_HOSTS = []` — list of domains Django responds to. Empty list works only when `DEBUG=True`. On Render → `['opd-app.onrender.com']`.

### `INSTALLED_APPS`

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
```

Every Django app — built-in or ours — that this project uses.

| App | What it does |
|-----|-------------|
| `admin` | Free admin panel at `/admin/` |
| `auth` | User accounts, login, sessions, password hashing |
| `contenttypes` | Generic relations — one model points to "any other model" |
| `sessions` | Server-side session storage |
| `messages` | One-time flash messages |
| `staticfiles` | Serves CSS/JS/images in dev; collects for prod |

Every new app we create gets added here.

### `MIDDLEWARE`

A pipeline of functions every request flows through *before* hitting your view, and every response flows through *after* leaving your view.

```
Request →  Security →  Session →  CSRF  → Auth  →  ...  →  Your View
Response ← X-Frame  ← Messages  ←  ...  ←  ←  ←  ←  ←  Your View
```

| Middleware | Job |
|-----------|-----|
| `SecurityMiddleware` | Security headers (HSTS, etc.) |
| `SessionMiddleware` | Loads `request.session` from DB |
| `CommonMiddleware` | URL normalization, append-slash |
| `CsrfViewMiddleware` | Protects POST forms from CSRF |
| `AuthenticationMiddleware` | Loads `request.user` from session |
| `MessageMiddleware` | Loads `request.messages` |
| `XFrameOptionsMiddleware` | Prevents clickjacking |

**Order matters.** Session must run before Auth because Auth reads from session.

### `ROOT_URLCONF`

```python
ROOT_URLCONF = 'config.urls'
```

Python import path to root URL config. Django imports `config.urls` to route incoming requests.

### `TEMPLATES`

```python
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [...],
    },
}]
```

- `BACKEND` — template engine (Django's own; alternative is Jinja2)
- `DIRS` — folders to search FIRST, in order
- `APP_DIRS = True` — also search each app's `templates/` subfolder
- `context_processors` — inject extra variables (`request`, `user`, `messages`) into every template

Default `DIRS = []` is wrong for us — Edit 1 fixes it.

### `WSGI_APPLICATION`

```python
WSGI_APPLICATION = 'config.wsgi.application'
```

Python path to the WSGI `application` object Gunicorn imports. Never change.

### `DATABASES`

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

DB connection config. SQLite for dev (zero setup, single file at `backend/db.sqlite3`). PostgreSQL for production.

### `AUTH_PASSWORD_VALIDATORS`

Rules applied when creating/changing passwords. Reject if:
1. Too similar to username/email
2. Shorter than 8 chars
3. In a list of 20,000 common passwords
4. All numeric

### Internationalization

```python
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'        # → changed to 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True
```

- `USE_TZ = True` — store ALL datetimes in UTC in DB; convert to local TZ for display. Critical for correctness.

### Static files

```python
STATIC_URL = 'static/'
```

URL prefix for static assets. Works for app-level `static/` folders only — we need `STATICFILES_DIRS` for project-level. Edit 3 fixes it.

---

## Half 2 — The 4 edits we made

### Edit 1 — Point `TEMPLATES['DIRS']` at `frontend/templates/`

```python
'DIRS': [BASE_DIR.parent / 'frontend' / 'templates'],
```

Tells Django to look in `frontend/templates/` before app-level template folders. Without this, `render(request, 'base.html')` throws `TemplateDoesNotExist`.

### Edit 2 — Change `TIME_ZONE` to Indian time

```python
TIME_ZONE = 'Asia/Kolkata'
```

Sets display TZ to IST (UTC+5:30). DB still stores UTC (`USE_TZ = True`); admin/templates/emails show IST.

### Edit 3 — Add `STATICFILES_DIRS` and `STATIC_ROOT`

```python
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR.parent / 'frontend' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

- `STATICFILES_DIRS` — extra folders Django searches in dev for static files (points at `frontend/static/`).
- `STATIC_ROOT` — destination folder `collectstatic` dumps everything into for prod.

**⚠️ Common typo:** `STATICIFILES_DIRS` (extra `I`) — Django won't error but will silently ignore the setting and styles won't load. Always double-check the spelling.

### Edit 4 — Add media settings

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

- `MEDIA_URL` — URL prefix for user-uploaded files (lab result PDFs, profile pics).
- `MEDIA_ROOT` — disk folder uploads are saved to. Maps to `backend/media/`.

**Static vs Media:** Static = devs ship them, baked into repo. Media = users create them at runtime, never in repo.

---

## Verify

```bash
cd backend
python manage.py runserver
```

- Rocket page at `http://127.0.0.1:8000/` still loads (200 OK)
- The "18 unapplied migrations" warning persists (fixed Step 8)
- `Not Found: /favicon.ico` (404) is harmless — every browser auto-requests a tab icon; we don't have one yet
- Saving `settings.py` triggers auto-reload — no manual restart needed

## Revise (3-line summary)

1. `settings.py` is the brain — `INSTALLED_APPS` lists every active app, `MIDDLEWARE` is the request/response pipeline, `TEMPLATES['DIRS']` tells Django where HTML lives, `DATABASES` configures DB connection.
2. Build all paths relative to `BASE_DIR` (which equals `backend/`) for portability — `BASE_DIR.parent` is the project root.
3. Our 4 edits wired Django to `frontend/templates`, `frontend/static`, `backend/media`, and `Asia/Kolkata` timezone.

---

**Next:** [Step 6 — Create the `accounts` app](06-accounts-app.md)
