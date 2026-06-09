# Step 2 — Install Django + freeze `requirements.txt`

## What we did here

Two micro-steps inside one big step:

1. Used `pip` to install Django into the active venv.
2. Used `pip freeze` to write the installed packages into `requirements.txt` at the project root.

## What is `pip`?

`pip` = **P**ip **I**nstalls **P**ackages. Python's official package manager. Ships with Python — no separate install.

`pip install <package>` downloads from **PyPI** (pypi.org — the Python Package Index, a public library of ~500,000 packages) and drops it into your active Python's `site-packages/` folder. With our venv active, that's `.venv/Lib/site-packages/`.

## What is Django?

Django is a **web framework** — a giant box of pre-written Python code that handles the boring parts of building a website:

- URL routing (which Python function answers `/login/` vs `/doctor/dashboard/`?)
- Database queries via an ORM (write Python objects, not raw SQL)
- Form validation (don't let users submit garbage to your DB)
- User authentication (login, sessions, password hashing — all free)
- Security headers (CSRF, XSS, clickjacking protection by default)
- A free auto-generated admin panel
- Migration system to evolve the DB schema safely

Django's design philosophy is **"batteries included"**: it ships with everything most apps need. Compare to Flask (a small framework where you assemble pieces yourself). For a multi-role hospital system with admin panel + auth + ORM needs, Django is the natural fit.

## What is `requirements.txt`?

A plain-text file listing every Python package the project depends on, with version numbers. One package per line:

```
asgiref==3.11.1
Django==6.0.6
sqlparse==0.5.5
tzdata==2026.2
```

Why we need it:

- **Reproducibility** — anyone (or future-you, or Render) runs `pip install -r requirements.txt` and gets the exact same packages.
- **Deployment** — Render scans the repo, finds `requirements.txt`, automatically installs everything before starting your app.
- **Documentation** — at a glance, you see what the project depends on.

The `==` operator **pins** an exact version, preventing the "works on my machine" disaster where a package gets a breaking update overnight and your Render deploy fails.

## How we did it

### 1. Confirmed venv was active

```bash
where python   # PowerShell / cmd
which python   # Git Bash
```

Path contained `.venv/Scripts/python.exe` → venv active.

### 2. Upgraded `pip` (good hygiene)

```bash
python -m pip install --upgrade pip
```

Bundled pip is sometimes outdated. New pip = faster installs, better error messages.

### 3. Installed Django

```bash
pip install django
```

Downloads the latest Django (6.0.6 as of now) and its sub-dependencies (`asgiref`, `sqlparse`, `tzdata`).

### 4. Verified Django installed

```bash
python -m django --version
```

Printed `6.0.6` → Django is alive inside the venv.

### 5. Froze into `requirements.txt`

```bash
pip freeze > requirements.txt
```

Redirected `pip freeze` output (every installed package with version) into the file at project root.

## Gotchas

- **Always activate venv before `pip install`.** Without venv, you pollute global Python — exactly the disaster venvs exist to prevent.
- **Don't `pip freeze` before installing your packages.** Freezing too early = empty/incomplete file.
- **Don't hand-edit `requirements.txt`.** Always go through `pip install` then `pip freeze >`. Hand-editing leads to typos and version drift.
- **`requirements.txt` must live at the project root**, not inside `backend/`. Render auto-detects Python only when this file is at the repo root.
- **Django 6.0 is bleeding-edge** (released Dec 2025). Most online tutorials still target Django 4.x / 5.x. 95% of what they show works identically; the 5% that differs we flag as we hit it.

## Verify before moving on

- [x] `pip list` shows `Django`
- [x] `python -m django --version` prints `6.0.6`
- [x] `requirements.txt` at root contains `Django==6.0.6` line
- [x] No errors during install

## What we have NOT done yet

- We haven't installed DRF, Celery, ReportLab, etc. — only Django itself. The other packages get added step-by-step as we need them. Don't install everything up front — you'll forget what each one does.
- We haven't created a Django project yet. That's Step 3.

## Revise (3-line summary)

1. `pip install django` downloads Django from PyPI into the active venv's `site-packages/`.
2. `requirements.txt` pins every installed package's exact version so the same setup can be rebuilt anywhere (locally, on Render, by another dev).
3. Generate it with `pip freeze > requirements.txt`; never hand-edit it; keep it at the project root.

---

**Next:** [Step 3 — `django-admin startproject` + scaffold tour](03-startproject.md)
