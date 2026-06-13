# Step 8 — Migrations (`makemigrations` vs `migrate`)

## What we did here

1. Ran `python manage.py makemigrations accounts` → Django generated `backend/apps/accounts/migrations/0001_initial.py` (the recipe).
2. Inspected the recipe — saw the 14 columns (3 ours + 11 inherited from `AbstractUser`), the dependency on `auth.0012`, and the `UserManager` attachment.
3. Ran `python manage.py migrate` → Django applied **19 migrations** in dependency order, creating `backend/db.sqlite3`.
4. The "18 unapplied migrations" warning from Step 4 is gone for good.
5. Committed only the migration file (the recipe). The DB file is gitignored.

After this, our `accounts_customuser` table physically exists in SQLite. It's empty — Step 9 creates the first user (a superuser).

---

## Half 1 — The cooking metaphor (lock this in your head)

Migrations are confusing until you separate "writing the recipe" from "cooking the food."

| Step | Django term | Command | What it touches |
|------|-------------|---------|----------------|
| 1. Write the recipe | Migration | `makemigrations` | A new `.py` file in `migrations/` |
| 2. Cook the food | Migrate | `migrate` | The actual `db.sqlite3` file |

Recipes go to Git. Cooked food (the database) does not. Every team member, every CI server, every production deploy re-cooks from the same committed recipes.

This separation is what makes Django safe to use in a team:
- You change a model → write a recipe → push to Git
- Teammate pulls → runs `migrate` → their DB matches yours exactly

Without migrations, schemas would drift the moment two developers worked on the same project.

---

## Half 2 — `makemigrations` in detail

```bash
python manage.py makemigrations accounts
```

### What Django does

1. Reads the **current state** of all models in the `accounts` app (just `CustomUser` right now).
2. Reads the **last applied migration** for `accounts` (none — this is the first).
3. **Diffs** the two states — what needs to change?
4. Writes a Python file describing those changes.

In our case, the diff is "everything" because there's no previous state. The recipe describes how to **create** the user table from scratch.

### The output you saw

```
Migrations for 'accounts':
  apps\accounts\migrations\0001_initial.py
    + Create model CustomUser
```

`+ Create model CustomUser` is the only operation. Simple recipe.

### Why only `accounts` in the command

`makemigrations` without an app name scans **all** installed apps. Passing `accounts` scopes it to just one app — safer, more deliberate. Industry habit: always pass the app name.

### Important — `makemigrations` does NOT touch the database

After this command:
- ✅ A new `.py` file exists
- ❌ `db.sqlite3` is unchanged (in fact, it didn't exist yet)
- ❌ No tables created

You wrote down a recipe. The stove is still off.

---

## Half 3 — Reading `0001_initial.py`

Open `backend/apps/accounts/migrations/0001_initial.py`. Every migration file has the same shape:

```python
class Migration(migrations.Migration):
    initial = True
    dependencies = [...]
    operations = [...]
```

### `initial = True`

This is the **first** migration for the `accounts` app. Future migrations (`0002_...`, `0003_...`) won't have this flag.

### `dependencies` — the order graph

```python
dependencies = [
    ('auth', '0012_alter_user_first_name_max_length'),
]
```

Django builds a **graph** of all migrations across all apps. This line says: "Before running this migration, make sure `auth.0012` has run."

Why? Because our `CustomUser` references `auth.Group` and `auth.Permission` (those `ManyToManyField`s at the bottom of the operations block). Those tables must exist first.

When you run `migrate`, Django uses this graph to compute a safe execution order.

### `operations` — the actual recipe

One operation in our file:

```python
migrations.CreateModel(
    name='CustomUser',
    fields=[
        # 14 fields listed here
    ],
    options={...},
    managers=[...],
)
```

`CreateModel` is the most common operation. Others include `AddField`, `RemoveField`, `AlterField`, `DeleteModel`, `RunSQL` (raw SQL escape hatch), `RunPython` (data migrations).

### The 14 fields — 3 ours + 11 inherited

| # | Field | Source |
|---|-------|--------|
| 1 | `id` | Auto-PK (`BigAutoField` because of `default_auto_field` in `apps.py`) |
| 2 | `password` | `AbstractUser` |
| 3 | `last_login` | `AbstractUser` |
| 4 | `is_superuser` | `AbstractUser` |
| 5 | `username` | `AbstractUser` |
| 6 | `first_name` | `AbstractUser` |
| 7 | `last_name` | `AbstractUser` |
| 8 | `is_staff` | `AbstractUser` |
| 9 | `is_active` | `AbstractUser` |
| 10 | `date_joined` | `AbstractUser` |
| 11 | **`email`** | **Ours** (overridden to `unique=True`) |
| 12 | **`phone`** | **Ours** (Indian mobile regex) |
| 13 | **`role`** | **Ours** (TextChoices enum) |
| 14 | `groups`, `user_permissions` | M2M from `AbstractUser` |

The cost of inheritance: we wrote 3 fields and got 11 for free, all production-tested.

### `managers` block

```python
managers=[
    ('objects', django.contrib.auth.models.UserManager()),
],
```

Attaches Django's `UserManager` to the model. This is what gives us `CustomUser.objects.create_user(...)` and `CustomUser.objects.create_superuser(...)` later. We never wrote those methods — `UserManager` provides them.

### Why this file goes to Git

The migration file IS the schema specification. Anyone who clones the repo can:

```bash
python manage.py migrate
```

And get an identical database to yours. Production servers do exactly this on every deploy. The recipe is the contract.

> **Don't edit migration files by hand** unless you really know what you're doing. They're Django's bookkeeping. To change the schema, change the model and run `makemigrations` again — Django will write a new file (`0002_...`).

---

## Half 4 — `migrate` in detail

```bash
python manage.py migrate
```

### What Django does

1. Reads the migration graph across **all** installed apps.
2. Checks the `django_migrations` table inside `db.sqlite3` to see which migrations have already run. (If `db.sqlite3` doesn't exist, creates it.)
3. Computes the set of **unapplied** migrations.
4. Sorts them by dependency.
5. Executes each one against the database.
6. Records each one in `django_migrations` so it's not run twice.

### Our 19-migration cascade

```
Applying contenttypes.0001_initial... OK
Applying contenttypes.0002_remove_content_type_name... OK
Applying auth.0001_initial... OK
...
Applying auth.0012_alter_user_first_name_max_length... OK
Applying accounts.0001_initial... OK     ← OURS
Applying admin.0001_initial... OK
Applying admin.0002_logentry_remove_auto_add... OK
Applying admin.0003_logentry_add_action_flag_choices... OK
Applying sessions.0001_initial... OK
```

19 = 2 contenttypes + 12 auth + **1 ours** + 3 admin + 1 sessions.

### The dependency order

Django respected the graph:
1. `contenttypes` first (plumbing for generic relations)
2. `auth` next — builds `auth_group`, `auth_permission` tables
3. **`accounts.0001_initial`** — creates `accounts_customuser` (depended on `auth.0012`)
4. `admin` — depends on the user model (which is now ours, not `auth_user`)
5. `sessions` — independent

If we'd run `migrate` before setting `AUTH_USER_MODEL`, Django would have applied `auth.0001_initial`'s `User` model FIRST, then admin would have wired itself to `auth_user`. Switching afterwards = catastrophe. That's why Step 7 had to come before Step 8.

### Where the table actually lives

```
backend/db.sqlite3  ← single file, contains all tables
```

SQLite stores the entire database in one file. PostgreSQL (production) uses a server with multiple data files — but the Django code is identical. The only difference is the connection string in `DATABASES['default']`.

### The "18 unapplied migrations" warning is finally gone

That red warning has nagged us since Step 4 (`runserver`). It was Django saying "I have built-in migrations queued up but no database to apply them to." Now the DB exists, all migrations are applied, and `runserver` will start clean.

---

## Half 5 — What's in the database now

Run this to see (don't worry about understanding every line — just confirmation):

```bash
python manage.py dbshell
```

Then at the SQLite prompt:

```sql
.tables
```

You'll see something like:

```
accounts_customuser              auth_user_groups
accounts_customuser_groups       auth_user_user_permissions
accounts_customuser_user_permissions   django_admin_log
auth_group                       django_content_type
auth_group_permissions           django_migrations
auth_permission                  django_session
```

**Key observation:** there's **`accounts_customuser`** but **no `auth_user`**. Django routed the user model to ours because of `AUTH_USER_MODEL`.

Exit dbshell with `.quit`.

### Naming convention — `<app_label>_<modelname_lowercase>`

| Model | Table name |
|-------|-----------|
| `accounts.CustomUser` | `accounts_customuser` |
| `auth.Group` | `auth_group` |
| `auth.Permission` | `auth_permission` |
| `admin.LogEntry` | `django_admin_log` (overridden — exception) |
| `sessions.Session` | `django_session` (overridden — exception) |

Most follow the pattern. A few Django builtins override the default table name via `Meta.db_table` because they predate this convention.

---

## Half 6 — Commit (the recipe, not the food)

```bash
git add backend/apps/accounts/migrations/0001_initial.py
git commit -m "feat(accounts): add initial migration for CustomUser table"
git push
```

### What we explicitly do NOT commit

- ❌ `backend/db.sqlite3` — gitignored. Each developer has their own.
- ❌ `__pycache__/` folders — gitignored. Regenerated automatically.

### Verifying with `git status`

```
Untracked files:
    backend/apps/accounts/migrations/0001_initial.py
```

Only the migration file appears. `db.sqlite3` is invisible to Git. This is exactly what we want.

### Why migrations are committed but DBs are not

| | Migrations | Database |
|--|-----------|----------|
| Size | Small text file | Can be huge |
| Contains | Schema only | Schema + actual data |
| Reproducible | Yes (just re-run) | No (data is unique) |
| Should team share? | Yes (everyone needs same schema) | No (everyone has own dev data) |

Production deploys run `migrate` automatically on every push — Render does this for us in Step 18.

---

## Gotchas

- **Forgetting to run `makemigrations` after changing a model** — your model says one thing, the DB says another, things break in confusing ways. Habit: every model edit → `makemigrations` → `migrate`.
- **Running `migrate` before `makemigrations`** — `migrate` only runs migration files that exist. If you didn't generate the file, your changes never reach the DB.
- **Editing a migration file by hand** — Django's internal bookkeeping gets confused. Always change the model and generate a new migration.
- **Deleting a migration file that's already been applied** — Django thinks it never ran, tries to apply it again, conflicts. Use `migrate accounts zero` to roll back before deleting.
- **Forgetting to commit migration files** — the worst version of this. Teammate pulls, runs `migrate`, no changes apply, schema diverges silently. Treat migration files like source code.
- **Committing `db.sqlite3`** — pollutes the repo, each developer's changes overwrite each other, eventually someone's local data gets pushed. The `.gitignore` rule from Step 5.5 prevents this.

---

## Where each future feature uses this

| Feature | When | What it needs |
|---------|------|--------------|
| Create superuser | Step 9 | The `accounts_customuser` table must exist ✅ |
| Login form | Step 12 | Same |
| Booking an appointment | Step 13 | `appointments.0001_initial` migration with FK to `accounts_customuser` |
| Adding any new field to any model | Forever | New migration file via `makemigrations` |
| Render deploy | Step 18 | Build script runs `migrate` automatically |

Every time you change a model from now on, you'll do the same dance: `makemigrations` → review the file → `migrate`. Eventually it'll feel automatic.

---

## Revise (3-line summary)

1. **`makemigrations` writes the recipe; `migrate` cooks the food.** The recipe is a `.py` file committed to Git; the food (`db.sqlite3`) is gitignored. Every team member re-cooks from the same recipes for an identical schema.
2. Our migration file has **14 columns** because `AbstractUser` gave us 11 for free on top of our 3 (`email`, `phone`, `role`). `dependencies` ensures Django's `auth` migrations run before ours so `Group` and `Permission` tables exist for the M2M relations.
3. After `migrate`, the user table is named **`accounts_customuser`** (not `auth_user`) because `AUTH_USER_MODEL = 'accounts.CustomUser'` routed Django to our model. Inspect tables with `python manage.py dbshell` then `.tables`.

---

**Next:** [Step 9 — Django admin + superuser](09-admin-superuser.md) — **stays on `feature/accounts-app` branch**. We register `CustomUser` in `admin.py`, create the first superuser with `createsuperuser`, log into `/admin/`, and see our role/phone fields in the admin UI. After Step 9, the accounts module is feature-complete and we open the PR to merge into `main`.
