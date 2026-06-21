# Step 12 — Auth Forms (Login, Register, Logout, Profile)

## What we did here

1. Wrote `backend/apps/accounts/forms.py` — `RegisterForm(forms.ModelForm)` with password + confirm fields, match validation via `clean_password_confirm()`, password hashing in `save()`, and a hard-coded `role = 'PATIENT'` (security).
2. Rewrote `backend/apps/accounts/views.py` — four real views: `login_view`, `register_view`, `logout_view` (POST-only), `profile_view` (`@login_required`).
3. Added `path('profile/', ...)` to `backend/apps/accounts/urls.py`.
4. Added three settings to `backend/config/settings.py` — `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`.
5. Locked `register.html` to PATIENT only — dropped the 4-role dropdown, replaced with a static label. Added a `{{ form.errors }}` render block above the form.
6. Added an error render block to `login.html` so bad-credentials text actually shows.
7. Created `frontend/templates/accounts/profile.html` — extends `base.html`, prints `{{ user.username }}`, `{{ user.role }}`, includes a POST logout form.
8. Added `path('', RedirectView.as_view(url='/accounts/login/'))` in `backend/config/urls.py` — kills the homepage 404 inherited from Step 10.
9. Four atomic commits on `feature/auth-views`. Tutorial + docs commit. PR #2 ready.

After this, the entire **accounts** module is feature-complete and mergeable as one PR.

---

## Half 1 — `authenticate()` vs `login()` — the split

Django splits "verify credentials" from "start a session" into two functions. Most beginners think login is one step. It is two.

```python
from django.contrib.auth import authenticate, login

user = authenticate(request, username='prince', password='secret')
if user is not None:
    login(request, user)
```

| Function | What it does | What it does NOT do |
|----------|--------------|---------------------|
| **`authenticate()`** | Looks up the user, calls `check_password()` on the hash, returns the `User` object on match or `None` on miss | Does NOT touch sessions or cookies |
| **`login(request, user)`** | Writes a row in `django_session`, sets the `sessionid` cookie, attaches `user` to `request.user` | Does NOT verify the password |

Why the split? Sometimes you want to log a user in **without** them typing a password — e.g., right after they register (we use this in `register_view`), or after OAuth / "magic link" flows. `login()` standalone handles that. `authenticate()` standalone is useful for re-verifying password before a sensitive action (delete account, change email).

> **Mnemonic:** `authenticate` answers *"is this person who they say they are?"*; `login` answers *"remember this browser as them from now on."*

---

## Half 2 — Password hashing (never store plain)

```python
user.set_password('secret')   # hashes + stores
user.check_password('secret') # verifies
user.password                 # 'pbkdf2_sha256$870000$<salt>$<hash>'
```

Django uses **PBKDF2-SHA256** by default — 870,000 iterations as of Django 5. The stored value is `algorithm$iterations$salt$hash`. Same password typed by two different users produces two different hashes (because salts differ).

### The cardinal rule

**Never write `user.password = plain_string`.** That bypasses hashing and stores the password as plain text. Always use `set_password()`. This is the single most common Django auth bug in junior code.

We use it in `RegisterForm.save()`:

```python
def save(self, commit=True):
    user = super().save(commit=False)
    user.set_password(self.cleaned_data['password'])  # hash here
    user.role = 'PATIENT'
    if commit:
        user.save()
    return user
```

Why it matters: if your database leaks (and they do), plain passwords mean every user's other accounts are also compromised (because people reuse passwords). Hashes mean the attacker has to brute-force each one — at 870K iterations per guess, that's economically infeasible for strong passwords.

---

## Half 3 — Sessions in 60 seconds

How does Django remember "this browser is Prince" between requests? HTTP is stateless — every request looks identical to the server unless something carries identity.

### The session dance

1. User submits login form. `authenticate()` returns the user. `login(request, user)` runs.
2. Django generates a random 32-char string (the **session key**), e.g. `abc123...xyz`.
3. Django inserts a row into the `django_session` table: `(session_key='abc123...', session_data=<encoded user_id>, expire_date=...)`.
4. Response sets a cookie: `Set-Cookie: sessionid=abc123...; HttpOnly`.
5. Browser stores the cookie. **Next** request to your site auto-sends `Cookie: sessionid=abc123...`.
6. On every incoming request, `SessionMiddleware` reads the cookie, looks up the row, decodes the user_id, and attaches `request.user`.

### Why `HttpOnly` matters

`HttpOnly` on the cookie means **JavaScript cannot read it** (`document.cookie` is blocked). If an attacker injects a malicious `<script>` (XSS), they still can't steal the session cookie and impersonate the user. This is browser-level defense Django wires up for free.

> **Mnemonic:** Cookie = ID card. Server = bouncer. Bouncer checks the card against the guest list (`django_session` table) on every entry.

---

## Half 4 — `forms.ModelForm` and the `clean_<fieldname>()` hook

```python
class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone']
```

### `ModelForm` vs `Form`

| Class | When | What you get for free |
|-------|------|----------------------|
| **`forms.ModelForm`** ✅ | The form is tied to one model (User, Appointment, etc.) | Auto-generates fields from `Meta.fields`, auto-validates `unique=True` and `EmailField`, `save()` method writes to DB |
| `forms.Form` | The form is pure data, not tied to a model (e.g., a search box) | Just validation. You write `.save()` yourself if you need to persist |

Registration creates a `CustomUser` row → `ModelForm` is the right fit.

### Why `password` is declared manually (not in `Meta.fields`)

`AbstractUser.password` is already a `CharField`. If we added `'password'` to `Meta.fields`, the form would render a normal `<input type="text">` — visible password. By declaring it ourselves with `widget=forms.PasswordInput`, we get masked dots and we control the flow (hash before save).

### The `clean_<fieldname>()` hook

Django auto-calls `clean_password_confirm()` during `is_valid()` because the method name matches `clean_` + field name. Whatever the method **returns** replaces `cleaned_data['password_confirm']`.

```python
def clean_password_confirm(self):
    password = self.cleaned_data.get('password')
    confirm = self.cleaned_data.get('password_confirm')
    if password and confirm and password != confirm:
        raise forms.ValidationError("Passwords don't match")
    return confirm
```

**The two parts:**

1. **The check** — `if password != confirm` raises `ValidationError`. Django catches it, adds it to `form.errors['password_confirm']`, `is_valid()` returns `False`.
2. **The `return confirm`** — Django's contract. The return value REPLACES `cleaned_data['password_confirm']`. Forget the return → Django writes `None` into `cleaned_data` silently. The form validates but the data is lost.

> **Mnemonic:** `clean_X` is a checkpoint. You either raise (reject) or return (accept the value forward).

---

## Half 5 — Decorators that gate views

### `@login_required` — bounce anonymous users

```python
from django.contrib.auth.decorators import login_required

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')
```

Behavior: if `request.user.is_authenticated` is False, Django redirects to `LOGIN_URL` (from settings) with `?next=/accounts/profile/` appended. After login, `LoginView` reads `?next=` and bounces the user back to the page they originally wanted. Clean UX with one decorator.

### `@require_POST` — block GET on destructive actions

```python
from django.views.decorators.http import require_POST

@require_POST
def logout_view(request):
    logout(request)
    return redirect('accounts:login')
```

Why POST-only for logout? Django 5+ enforces this because GET requests can be triggered by prefetchers, image tags, browser preview cards — any of which could accidentally log the user out. POST requires a real form submit, which requires CSRF token, which requires intent. Defense in depth.

That's why `profile.html` logout is a `<form method="post">` with `{% csrf_token %}`, not a plain `<a>` link.

---

## Half 6 — Locking register to PATIENT (defense in depth)

The hospital flow: only patients self-register. Doctor / Reception / Lab accounts are created by Receptionist through admin. The Step 11 register form mistakenly exposed all 4 roles in a `<select>` — a malicious user could POST `role=DOCTOR` and grant themselves prescription-writing privileges.

We fix this in **three layers**. Each one alone would be enough — together they form defense in depth.

| Layer | Where | What it does |
|-------|-------|--------------|
| **1. HTML** | `register.html` — dropped the `<select>` block, replaced with a static "Account type: Patient" label | User can't pick a role in the UI |
| **2. Form** | `RegisterForm.Meta.fields = ['username','email','phone']` — `role` is NOT in the list | Even if a malicious user POSTs `role=DOCTOR`, the form ignores it (not bound to that field) |
| **3. Save** | `user.role = 'PATIENT'` hard-coded in `RegisterForm.save()` | Even if layers 1 + 2 broke, the saved row is always PATIENT |

> **Rule:** Never trust the client. The HTML layer is decoration. The server is the law. If your security depends on the dropdown not having an option, you have no security.

---

## Half 7 — The four views, line by line

### `login_view` — verify + start session

```python
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('accounts:profile')
        else:
            return render(request, 'accounts/login.html', {'error': 'Invalid username or password'})
    return render(request, 'accounts/login.html')
```

- GET → render empty form.
- POST → authenticate. Success → login + redirect. Fail → re-render with `error` in context.

### `register_view` — create user + auto-login

```python
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('accounts:profile')
        return render(request, 'accounts/register.html', {'form': form})
    form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})
```

Auto-login after register saves the user one extra step. `form.save()` returns the freshly-hashed user; we pass it to `login()` and the session starts.

### `logout_view` — POST-only

Already shown — `logout(request)` clears the `django_session` row and deletes the cookie, then redirects to login.

### `profile_view` — gated by login

Already shown — `@login_required` ensures `request.user` is real before the template runs. `profile.html` reads `{{ user.username }}` via the `auth` context processor (auto-wired in `settings.py` → `TEMPLATES['OPTIONS']['context_processors']`).

---

## Half 8 — Auth settings

```python
# backend/config/settings.py
AUTH_USER_MODEL = 'accounts.CustomUser'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:profile'
LOGOUT_REDIRECT_URL = 'accounts:login'
```

| Setting | Who reads it | Effect |
|---------|--------------|--------|
| `LOGIN_URL` | `@login_required` | Where to send anonymous users who hit a gated view |
| `LOGIN_REDIRECT_URL` | `LoginView` default | Where to land after successful login if no `?next=` is set |
| `LOGOUT_REDIRECT_URL` | `LogoutView` default | Where to land after logout |

We use URL names (`'accounts:login'`) not hard-coded paths (`'/accounts/login/'`) — same reason as `{% url %}` in templates. Rename the URL pattern, the setting still works.

---

## Half 9 — `/` → login (`RedirectView`)

```python
# backend/config/urls.py
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('', RedirectView.as_view(url='/accounts/login/')),
]
```

`RedirectView` is a Django built-in CBV that returns a 302 (or 301 with `permanent=True`) pointing at the given URL. Cleaner than writing a one-line view function. Browser auto-follows the 302 → user lands on `/accounts/login/`.

This kills the 404 we inherited at Step 10 when we removed Django's default welcome page.

---

## Half 10 — Verify in browser

```bash
cd backend
python manage.py runserver
```

| Step | URL | Expected |
|------|-----|----------|
| 1 | `/` | 302 → `/accounts/login/` |
| 2 | `/accounts/register/` | Form with username, email, phone, "Account type: Patient", password, confirm |
| 3 | Submit valid register | Auto-login → `/accounts/profile/` showing username + role=PATIENT |
| 4 | Click Logout | POST fires → back to `/accounts/login/` |
| 5 | Login with wrong password | Red "Invalid username or password" above form |
| 6 | Login correct | Back to profile |
| 7 | `/admin/` → users list | `testpatient` row, `password` field shows `pbkdf2_sha256$...` (NOT plain), `role=PATIENT` |
| 8 | Register with mismatched passwords | Red `password_confirm: Passwords don't match` |
| 9 | `/accounts/profile/` while logged out | 302 → `/accounts/login/?next=/accounts/profile/` |
| 10 | Duplicate username or email | Form errors render (because `ModelForm` auto-validates `unique=True`) |

---

## Half 11 — Four commits, four logical changes

```bash
# Commit 1: the form
git add backend/apps/accounts/forms.py
git commit -m "feat(accounts): add RegisterForm with password hashing + match validation"

# Commit 2: the views + settings + profile template
git add backend/apps/accounts/views.py backend/apps/accounts/urls.py backend/config/settings.py frontend/templates/accounts/profile.html
git commit -m "feat(accounts): wire real login/logout/register/profile views + auth settings"

# Commit 3: the PATIENT lock + error rendering
git add frontend/templates/accounts/register.html frontend/templates/accounts/login.html
git commit -m "refactor(accounts): lock register form to PATIENT role + render form errors"

# Commit 4: the homepage redirect
git add backend/config/urls.py
git commit -m "feat(config): redirect / to accounts:login"

git push
```

Why split? Each commit answers one question. If "lock to PATIENT" turns out to break something, we can `git revert` just commit 3 without losing the views or the form logic.

---

## Gotchas

- **Forgetting `return confirm` in `clean_password_confirm`** — silent data loss. Form validates but `cleaned_data['password_confirm']` becomes `None`. Always `return` from a `clean_X` method.
- **Writing `user.password = plain_string`** — stores plain text. Always `user.set_password(plain)`.
- **Using a GET link for logout** — Django 5+ blocks it. Use a POST form with `{% csrf_token %}`.
- **Trusting the HTML role dropdown for security** — a curl request can POST any role. Server-side `Meta.fields` exclusion + hard-coded `user.role = 'PATIENT'` are the real defense.
- **Hard-coding `'/accounts/login/'` in settings** — rename the URL pattern and your settings break. Use the URL name `'accounts:login'`.
- **Forgetting `{% csrf_token %}` inside a POST form** — Django returns 403 Forbidden. Always add it.
- **Setting `LOGIN_REDIRECT_URL` twice (typo)** — second wins, breaks login flow. Day 11 hit this exact bug — fixed Day 12.

---

## Where each future feature plugs in

| Feature | When | How it uses today's code |
|---------|------|--------------------------|
| Role-based redirect (`/doctor/`, `/reception/`, ...) | Step 13 | Override `login_view` to branch on `user.role` |
| Receptionist creates Doctor/Lab accounts | Step 13 | Separate `StaffCreateForm` — no role lock, requires receptionist permission |
| Forgot password | Step 14 | Django built-in `PasswordResetView` — works because `email` is `unique=True` |
| DRF JWT login | Step 14 | `authenticate()` reused, but returns JWT pair instead of session cookie |
| Appointment booking gated by login | Step 13 | Reuse `@login_required` on patient views |

The auth foundation is reusable for every later feature.

---

## Revise (3-line summary)

1. **Authentication splits into two functions.** `authenticate(request, username, password)` verifies credentials and returns the user (or `None`); `login(request, user)` starts the session (writes the `django_session` row, sets the `sessionid` cookie). Use them together for password login, or `login()` alone for auto-login after registration / OAuth.
2. **`RegisterForm(forms.ModelForm)` does three things in `save()`:** hashes the password with `set_password()` (never plain text), forces `role = 'PATIENT'` (server-side defense layer 3), and writes the row. The `clean_password_confirm()` hook is auto-called during `is_valid()` and MUST `return` the value or Django writes `None` silently.
3. **Defense in depth on the register flow** — HTML removes the role dropdown, `Meta.fields` excludes `role`, `save()` hard-codes it. Each layer alone would be enough; together they make role escalation impossible. The pattern repeats throughout the project: never trust the client, always validate on the server.

---

**Next:** [Step 13 — `appointments` app (models with foreign keys, ORM queries)](13-appointments-app.md) — start a new branch `feature/appointments-app` after PR #2 merges. Build the Appointment model with `ForeignKey` to `CustomUser` (Doctor and Patient), learn the Django ORM for first time, write queries like `Appointment.objects.filter(doctor=user, status='PENDING')`.
