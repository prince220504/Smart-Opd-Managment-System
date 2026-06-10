# Step 6 — Create the `accounts` App

## What we did here

1. Created a new branch `feature/accounts-app` (industry workflow — no work on `main`).
2. Made `backend/apps/` a Python package by adding `backend/apps/__init__.py`.
3. Ran `python manage.py startapp accounts apps/accounts` to scaffold the app **inside** `backend/apps/`.
4. Edited `backend/apps/accounts/apps.py` — changed `name = 'accounts'` to `name = 'apps.accounts'`.
5. Registered the app in `INSTALLED_APPS` as `'apps.accounts'`.
6. Ran into one harmless warning (`staticfiles.W004`), fixed it by recreating empty `frontend/static/` and `frontend/templates/`.
7. Noticed `default_auto_field` line was missing from `apps.py` — added it manually (correct convention).
8. Verified `python manage.py check` returns **no issues**.

After this, `accounts` is a real Django app that Django knows about, but it has zero models, views, or templates yet. The shell is built; we fill it in Steps 7–9.

---

## Half 1 — Project vs App (the most-asked Django question)

Before doing anything, lock in the distinction:

- A **project** = the *whole* Django site. It has one `settings.py`, one URL config, one database connection. In our case, that's `backend/config/`.
- An **app** = a *single feature* with its own models, views, templates, URLs. Apps are **plugged into** a project via `INSTALLED_APPS`. In our case: `accounts`, `appointments`, `lab`, `prescriptions`, `notifications`, `api`.

One project, many apps. Each app is small and single-purpose. Apps can be reused across projects (the famous example: `django.contrib.auth` is an app the Django team wrote once and every Django project plugs in).

> **Rule of thumb:** if it has its own models, it deserves its own app.

---

## Half 2 — Creating the branch (industry workflow)

From Step 5.5 onwards, every new module gets its own branch:

```bash
# Make sure main is up to date
git checkout main
git pull

# Create + switch to the feature branch
git checkout -b feature/accounts-app
```

All Step 6, 7, 8, 9 work happens on this branch. We merge to `main` only after the full accounts module (model, migration, admin, superuser) is working.

---

## Half 3 — `startapp` and the folder wrinkle

Django's normal command:

```bash
python manage.py startapp accounts
```

Run from `backend/`, this creates `backend/accounts/`. But our convention (set in `CLAUDE.md`) puts apps inside `backend/apps/`, so we need `backend/apps/accounts/` instead.

### Step A — make `apps/` a Python package

```bash
# Create the package marker (empty file)
touch backend/apps/__init__.py
```

**Why this matters:** Python recognizes a folder as an importable package only if it contains `__init__.py`. Without it, `import apps.accounts` would fail with `ModuleNotFoundError`. The file stays empty; its mere existence is the signal.

### Step B — `startapp` with a target directory

`startapp` accepts an optional second argument: the destination folder.

```bash
cd backend
python manage.py startapp accounts apps/accounts
```

This tells Django: "create an app called `accounts`, but put the files in `apps/accounts/` instead of the default `accounts/`."

### What `startapp` created — the 7 files

```
backend/apps/accounts/
├── __init__.py            ← marks accounts/ as a Python package
├── admin.py               ← register models with Django admin
├── apps.py                ← app config (name, label, default PK type)
├── models.py              ← database tables go here (empty for now)
├── tests.py               ← unit tests
├── views.py               ← request handlers (empty for now)
└── migrations/
    └── __init__.py        ← marks migrations/ as a package
```

Each file has one job. We'll fill them in over the next several steps.

---

## Half 4 — Fixing `apps.py` for the nested location

Open `backend/apps/accounts/apps.py`. Django generated this:

```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'          # ← problem: should be 'apps.accounts'
```

### The wrinkle

Because the app lives at `backend/apps/accounts/`, its import path is `apps.accounts` — not just `accounts`. The `name` attribute must match the import path **exactly**, otherwise Django can't find the app's models and migrations.

### The fix

```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'     # ✅ matches the import path
```

### About `default_auto_field`

Every database table needs a primary key (a unique ID column). If you don't define one in your model, Django auto-creates an `id` column for you. `default_auto_field` controls **what type** that auto-generated `id` is:

| Field type | Range | When used |
|------------|-------|-----------|
| `AutoField` | 32-bit (~2 billion rows max) | Legacy, before Django 3.2 |
| `BigAutoField` | 64-bit (~9 quintillion rows) | Modern default |

Django 3.2+ made `BigAutoField` the standard because hitting 2 billion rows is a real problem at scale. If the line is missing from `apps.py`, Django falls back to `DEFAULT_AUTO_FIELD` in `settings.py` (also `BigAutoField` by default), so functionally nothing breaks — but having it explicit per app is the convention.

> **Heads up:** `startapp` sometimes doesn't include this line. If yours is missing, add it manually. It's correct, expected behaviour to write it yourself.

---

## Half 5 — Registering the app in `INSTALLED_APPS`

Open `backend/config/settings.py` and find `INSTALLED_APPS`. Add `'apps.accounts'` at the bottom:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.accounts',          # ← our first app
]
```

**Why this matters:** Django doesn't auto-discover apps. Unless you list it here, Django won't:
- Look for models in this app (no DB table will be created)
- Pick up the app's admin registrations
- Pick up the app's templates or static files
- Run the app's migrations

`INSTALLED_APPS` is the master switch. Every new app we create gets added here.

> The string must match what's in `apps.py` → `name`. Both say `'apps.accounts'`. They must agree.

---

## Half 6 — The `staticfiles.W004` detour

When we ran `python manage.py check`, we got:

```
System check identified 1 issue (0 silenced).
?: (staticfiles.W004) The directory 'C:\...\frontend\static' in the STATICFILES_DIRS setting does not exist.
```

### What this warning means

In Step 5 we added:

```python
STATICFILES_DIRS = [BASE_DIR.parent / 'frontend' / 'static']
```

Django checks that every folder in `STATICFILES_DIRS` actually exists on disk at startup. If one is missing, it warns you (because in production, missing static folders mean missing CSS — silently).

### Why it suddenly appeared

We chose Option 2 in Step 5.5 — no `.gitkeep` placeholders. That means empty `frontend/static/` and `frontend/templates/` were **never tracked by Git**. When we switched branches (or did any clean-up), those untracked empty folders got wiped.

### The fix

Just recreate them:

```bash
mkdir -p frontend/templates frontend/static
```

Empty folders → Git still won't push them → warning gone locally. They'll show up on GitHub when real Stitch templates land.

### Re-run the check

```bash
cd backend
python manage.py check
```

Expected:

```
System check identified no issues (0 silenced).
```

✅ Clean.

---

## Half 7 — Commits and push

Two small Conventional Commits — one per logical change:

```bash
# Commit 1: the scaffold (new files)
git add backend/apps/__init__.py backend/apps/accounts/
git commit -m "feat(accounts): scaffold app via startapp into backend/apps/accounts"

# Commit 2: the registration (settings change)
git add backend/config/settings.py
git commit -m "feat(accounts): register apps.accounts in INSTALLED_APPS"

# Push the branch to GitHub (first push needs -u to set upstream)
git push -u origin feature/accounts-app
```

### Why two commits, not one?

Each commit should answer **one question**. Bundling unrelated changes makes the history harder to read and harder to revert.
- Commit 1 = "I added a new app"
- Commit 2 = "I plugged it into the project"

That's two separate decisions. Keep them separate.

> **Do NOT open the PR yet.** Steps 7 (CustomUser model), 8 (migrations), and 9 (admin + superuser) all live on this same branch. We merge to `main` only after Step 9 — that way the accounts module lands on `main` as one complete feature, not in half-built pieces.

---

## Gotchas

- **`name` mismatch in `apps.py`** — if `name = 'accounts'` but the app actually lives at `apps/accounts/`, Django can't import it. Symptom: weird errors during `makemigrations` or `migrate`. Fix: `name` must match the dotted import path.
- **Forgetting `__init__.py` in `apps/`** — without it, `import apps.accounts` fails. Add the empty file.
- **`startapp` without target dir** — running `python manage.py startapp accounts` from `backend/` creates `backend/accounts/`, not `backend/apps/accounts/`. Either pass the target dir or move the folder by hand.
- **Forgetting to add to `INSTALLED_APPS`** — the most common Django beginner bug. Symptom: models don't show up in admin, migrations don't run for the app, templates aren't found. Always remember to register.
- **Empty folders disappear** — Git doesn't track them. If you depend on a folder existing (like `frontend/static/`), either commit a placeholder file (`.gitkeep`) or recreate it after branch switches.
- **`default_auto_field` missing** — not strictly an error (falls back to settings), but conventional to set it per-app. Add it if `startapp` left it out.

---

## Revise (3-line summary)

1. A Django **project** is the whole site (one `settings.py`); an **app** is one feature with its own models/views/templates — plug apps into the project via `INSTALLED_APPS`.
2. To put apps inside `backend/apps/`, run `python manage.py startapp accounts apps/accounts` and set `name = 'apps.accounts'` in `apps.py` to match the import path; register as `'apps.accounts'` in `INSTALLED_APPS`.
3. `staticfiles.W004` is harmless and means a `STATICFILES_DIRS` folder doesn't exist on disk — just `mkdir` it; verify everything is clean with `python manage.py check`.

---

**Next:** [Step 7 — `CustomUser` model with role field](07-custom-user.md) — **stays on the same `feature/accounts-app` branch**. Critical: set `AUTH_USER_MODEL = 'accounts.CustomUser'` in `settings.py` **before** any migration runs.
