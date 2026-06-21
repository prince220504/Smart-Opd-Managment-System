# Step 10 — URLs and Views

## What we did here

1. Created a new feature branch `feature/auth-views` from `main`.
2. Created `backend/apps/accounts/urls.py` — the app-level URL map with 3 routes (`login/`, `logout/`, `register/`) and `app_name = 'accounts'` for namespacing.
3. Edited `backend/config/urls.py` — added `include` to imports and wired `path('accounts/', include('apps.accounts.urls'))` under the existing admin route.
4. Wrote `backend/apps/accounts/views.py` — three function-based placeholder views returning plain `HttpResponse` text. Real auth logic comes in Step 12.
5. Verified `runserver` resolves all 3 URLs (each returns 200 + the placeholder text) and `/accounts/foo/` returns 404 (proves routing is strict).
6. Pushed two Conventional Commits to `feature/auth-views`.

After this, Django can handle our own URLs — not just admin's. The full request lifecycle (URL → URLconf → view → response) is wired end-to-end for the first time.

---

## Half 1 — The request lifecycle

Every page load — yours, mine, every Django site on the internet — goes through these 6 steps:

```
Browser:  GET /accounts/login/ HTTP/1.1
   │
   ▼
1. Web server (runserver dev / gunicorn prod) hands the raw request to WSGI
2. WSGI builds an HttpRequest object and calls Django's get_response()
3. Django reads ROOT_URLCONF from settings → loads config.urls module
4. Walks urlpatterns top-to-bottom — first match wins
5. Match found → calls the view with (request, **path_kwargs)
6. View returns an HttpResponse → Django sends bytes back through WSGI
   │
   ▼
Browser:  HTTP/1.1 200 OK + body
```

**Why this matters:** until Step 10, our code only existed at the model/admin layer. Django auto-handled everything else. Step 10 is the first step where **our code runs in response to a browser request**. Every feature from here on (login, dashboard, appointment booking, lab upload) plugs into this lifecycle.

---

## Half 2 — Two-level URLconf — why split

Django supports putting all routes in `config/urls.py`, but **nobody does this** beyond a "hello world." Real projects split URLs across two levels:

| Level | File | Owns |
|-------|------|------|
| Root | `backend/config/urls.py` | Top-level prefixes (`admin/`, `accounts/`, `lab/`, `appointments/`). Delegates everything else. |
| App | `backend/apps/<app>/urls.py` | All routes within that app's URL space. |

```
backend/config/urls.py
│
├─ path('admin/',    admin.site.urls)
├─ path('accounts/', include('apps.accounts.urls'))   ← delegates
└─ path('appointments/', include('apps.appointments.urls'))  ← future

backend/apps/accounts/urls.py
│
├─ path('login/',    views.login_view,    name='login')
├─ path('logout/',   views.logout_view,   name='logout')
└─ path('register/', views.register_view, name='register')
```

**Three benefits:**
1. **Root file stays tiny.** One line per app. Easy to see the project's URL surface in 5 seconds.
2. **Each app owns its URLs.** Delete an app = delete one `include()` line in root. No grep-and-replace across files.
3. **Industry standard.** Every open-source Django project on GitHub uses this pattern.

> **Mnemonic:** *Root urls = building directory. App urls = office numbers on each floor.*

---

## Half 3 — `path()` — anatomy of a route

```python
path('register/<int:pk>/', views.detail, name='register-detail')
#     │                     │             │
#     │                     │             └─ name (for reverse lookup)
#     │                     └─ view callable (NO parens — Django calls it later)
#     └─ route pattern (with optional converters)
```

### Route converters

URL segments wrapped in `<type:name>` get captured + type-cast + passed to the view as a keyword argument.

| Converter | Matches | View receives |
|-----------|---------|---------------|
| `<int:pk>` | digits only | `pk=42` (`int`) |
| `<str:name>` | any non-slash text | `name="prince"` (`str`) |
| `<slug:s>` | `[a-z0-9-_]+` | `s="my-post"` (`str`) |
| `<uuid:u>` | UUID format | `u=UUID('...')` |
| `<path:p>` | text including slashes | `p="a/b/c"` (`str`) |

We used **zero converters** today — login/logout/register have no parameters. Step 13 (appointments) will use `<int:appointment_id>` heavily for routes like `/appointments/<int:appointment_id>/cancel/`.

### The view callable — no parens

```python
path('login/', views.login_view, name='login')      # CORRECT — pass the function
path('login/', views.login_view(), name='login')    # WRONG — calls function at import → crash
```

Django needs to **call the function later** when a matching request arrives. Pass the callable; don't invoke it.

### `name=` — the reverse-lookup handle

```python
path('login/', views.login_view, name='login')
```

The `name` lets the rest of the project refer to this URL without typing the literal path. More on this in Half 5.

---

## Half 4 — `include()` and `app_name`

```python
# config/urls.py
path('accounts/', include('apps.accounts.urls'))
```

Three things happen when Django hits this line:

1. Imports the module `apps.accounts.urls`
2. Strips the matched prefix (`accounts/`) from the URL
3. Hands the remainder to the included module's `urlpatterns`

So `/accounts/login/` → root matches `accounts/` → app urls receive `login/` → app matches `path('login/', ...)` → call view.

### Why `'apps.accounts.urls'` and not `'accounts.urls'`

Our `INSTALLED_APPS` registers the app as `'apps.accounts'` (dotted Python import path from project root). `include()` follows the same import path. The app's **label** (used by the ORM, admin, etc.) is the last segment (`accounts`), but Python imports need the full path.

### `app_name` — namespacing

Inside `apps/accounts/urls.py`:

```python
app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
]
```

The `app_name` declares a **namespace** for all the URL names in this file. The full name of the login route is now `'accounts:login'`.

**Why namespace?** Multiple apps can independently name a URL `'login'` (e.g., admin login, doctor portal login) without colliding. Without `app_name`, `reverse('login')` would be ambiguous. With it, `reverse('accounts:login')` is unambiguous.

> **Rule:** every app's `urls.py` declares `app_name`. Never skip it, even if you only have one app. It's free insurance against future collisions.

---

## Half 5 — `reverse()` and `{% url %}` — never hardcode URLs

**Bad:**

```python
return redirect('/accounts/login/')                 # Python
<a href="/accounts/login/">Log in</a>               <!-- Template -->
```

What's wrong? If we ever rename the route (e.g., `accounts/` → `auth/`), every hardcoded reference across the codebase breaks. Refactor becomes a grep-and-replace nightmare.

**Good:**

```python
from django.urls import reverse
return redirect(reverse('accounts:login'))          # Python (explicit)
return redirect('accounts:login')                   # Python (shortcut — redirect() auto-reverses)

<a href="{% url 'accounts:login' %}">Log in</a>     <!-- Template -->
```

Django takes the **name** and reconstructs the URL by walking the URLconf in reverse — hence `reverse()`. If the route pattern ever changes, every reference still resolves correctly because they're all looking up the same name.

> **Rule: never write a URL twice.** Once in `urls.py` (with `name=`), refer by name everywhere else. The path string is the source of truth, the name is its public handle.

This is one of the **most important** Django habits — internalize it now.

---

## Half 6 — FBV vs CBV — function-based vs class-based views

Two equivalent ways to write the same logic:

### Function-based view (FBV)

```python
def login_view(request):
    if request.method == 'POST':
        # validate credentials, log in
        return redirect('home')
    return render(request, 'accounts/login.html')
```

- Reads top-to-bottom
- All logic in one function — obvious data flow
- Verbose for common patterns (forms, lists, details)

### Class-based view (CBV)

```python
from django.contrib.auth.views import LoginView

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
```

- Subclass + override attributes/methods
- Tiny code when extending Django's built-ins
- Inheritance + mixin chain is opaque until you read the source

### When to pick which

| Situation | Pick |
|-----------|------|
| Learning Django for the first time | FBV — easier to debug |
| Need behavior identical to a built-in CBV (LoginView, LogoutView, ListView, DetailView) | CBV — subclass and override 2 attributes |
| Heavy custom form validation, business rules, weird response shapes | FBV — full control |
| CRUD with no exotic logic | CBV (`CreateView`, `UpdateView`, `DeleteView`) |

### Today's choice — placeholder FBVs

```python
from django.http import HttpResponse


def login_view(request):
    return HttpResponse('Login page — coming in Step 12')


def logout_view(request):
    return HttpResponse('Logout — coming in Step 12')


def register_view(request):
    return HttpResponse('Register page — coming in Step 12')
```

Why FBVs for placeholders:
- Smallest possible code that covers every concept (def, request param, return response)
- Zero template dependency (templates = Step 11)
- Easy to swap for real CBVs later

**Step 12 plan** — login/logout will become CBV subclasses of `LoginView` / `LogoutView` (free password hashing, session handling, "next" URL support). Register stays an FBV because Django's `UserCreationForm` doesn't know about our `role` / `phone` fields — we hand-roll the form.

---

## Half 7 — `HttpResponse` vs `render()`

```python
HttpResponse('Login page')                              # Today — raw bytes
render(request, 'accounts/login.html', {'form': f})     # Step 11 — HTML template
```

Both return an `HttpResponse`. `render()` is a shortcut:

```python
# render() is roughly equivalent to:
template = loader.get_template('accounts/login.html')
return HttpResponse(template.render({'form': f}, request))
```

Same plumbing — `render()` just hides the template-loading boilerplate.

### Why `request` even when unused

Django **always** calls views with `request` as the first positional argument. Your view's signature must accept it, even if the function body never touches it:

```python
def login_view(request):           # Required even though we don't use `request`
    return HttpResponse('...')
```

Skip the parameter → `TypeError: login_view() takes 0 positional arguments but 1 was given`.

---

## Half 8 — Verifying in the browser

```bash
cd backend
python manage.py runserver
```

Watch for:
```
System check identified no issues (0 silenced).
```

Then hit these URLs in a browser:

| URL | Expected | Status |
|-----|----------|--------|
| `/accounts/login/` | `Login page — coming in Step 12` | 200 |
| `/accounts/logout/` | `Logout — coming in Step 12` | 200 |
| `/accounts/register/` | `Register page — coming in Step 12` | 200 |
| `/accounts/foo/` | Django debug 404 page | 404 |
| `/` (homepage) | Django debug 404 page | 404 — see below |
| `/admin/` | Admin login | 200 |

### Why `/` returns 404 now (and not in Step 4)

Step 4 showed Django's "welcome rocket" page at `/`. That page only renders when `urlpatterns` has **zero non-admin routes** AND `DEBUG=True` — a "you haven't built anything yet" placeholder.

The moment we added a real route (`accounts/`), Django dropped the welcome page. `/` now follows the URLconf strictly: no pattern matches the empty path → 404.

**This is correct behavior**, not a bug. Many production sites don't have a homepage at `/`. They either redirect (`/` → `/login/` or `/` → `/dashboard/`) or have a real `home/` view. We'll wire `/` → `/accounts/login/` in Step 12 once the login page exists.

### Reading the terminal log

While clicking, runserver prints one line per request:

```
[15/Jun/2026 11:23:45] "GET /accounts/login/ HTTP/1.1" 200 35
                                                      │   │
                                                      │   └─ response size (bytes)
                                                      └─ HTTP status code
```

- `200` = OK
- `301`/`302` = redirect
- `404` = not found
- `500` = server crashed — check the traceback above the log line

When debugging "why doesn't my URL work?", this log is the first place to look.

---

## Half 9 — Two commits

```bash
git add backend/apps/accounts/urls.py backend/config/urls.py
git commit -m "feat(accounts): add urls.py with login/logout/register routes"

git add backend/apps/accounts/views.py
git commit -m "feat(accounts): add placeholder login/logout/register views"

git push -u origin feature/auth-views
```

The `-u` flag on first push sets the upstream — local branch starts tracking `origin/feature/auth-views`. Future pushes are just `git push`.

### Why split into two commits

Two distinct logical units:
- **Commit 1 — wiring.** The URL map declares "these three names exist at these three paths." Pure routing.
- **Commit 2 — views.** Three callables that respond when those routes are hit. Pure response logic.

If someone later wants to see "when did login become a real URL?" the answer is commit 1. "When did login start returning HTML?" — that'll be a future commit (Step 11 or 12). Atomic commits = atomic history.

---

## Gotchas

- **Forgetting `app_name`** — `reverse()` and `{% url %}` still work (without the `app:` prefix), but if two apps ever name a URL the same thing, you get `NoReverseMatch`. Always declare `app_name`.
- **Trailing slash mismatch** — Django's default is **slash-terminated URLs**. `/accounts/login` (no slash) → Django responds with a 301 redirect to `/accounts/login/`. Works but pollutes logs and adds a round trip. Always end patterns with `/`.
- **Calling the view in `path()`** — `views.login_view()` (with parens) calls the function at import time, server crashes on startup. Pass the callable, not the call.
- **Variable name typo `urlpattern` (singular)** — Django imports `urlpatterns` by literal name. Singular = empty patterns = every URL returns 404. Watch for it.
- **Forgetting `request` parameter** — `def login_view():` (no `request`) → `TypeError` on first request. Even unused, the parameter must exist.
- **Hardcoding URLs in code or templates** — every hardcoded path is technical debt waiting to break on the next refactor. Use `name=` + `reverse()` / `{% url %}` exclusively.
- **`include('accounts.urls')` instead of `'apps.accounts.urls'`** — `INSTALLED_APPS` registers the app under the full dotted path; Python imports need to match. Wrong path = `ModuleNotFoundError` at server start.

---

## Where each future feature plugs in

| Feature | When | How it uses today's wiring |
|---------|------|----------------------------|
| Login form (real) | Step 12 | Replace `login_view` placeholder with `LoginView.as_view(template_name='accounts/login.html')` |
| Register form (real) | Step 12 | Replace placeholder with FBV using a custom `RegisterForm(forms.ModelForm)` that knows `role` + `phone` |
| Role-based redirect after login | Step 12 | Override `LoginView.get_success_url()` — branch on `request.user.role` to send to `/doctor/`, `/lab/`, etc. |
| Appointments routes | Step 13 | New app + new `include('apps.appointments.urls')` line in root urlconf. Routes like `path('book/<int:doctor_id>/', ...)` |
| DRF API endpoints | Step 14 | `path('api/', include('apps.api.urls'))` — separate app, separate URL space |
| Homepage at `/` | Step 12 | `path('', RedirectView.as_view(url='accounts:login'))` once login template exists |

Every feature for the rest of the project rides on what we built today.

---

## Revise (3-line summary)

1. **Two-level URLconf is the standard.** Root `config/urls.py` only declares top-level prefixes and delegates each app via `include('apps.<name>.urls')`. Each app's own `urls.py` declares `app_name = '<name>'` for namespacing plus the `urlpatterns` list of `path()` entries — pattern, view callable (no parens), `name=` for reverse lookup.
2. **Never hardcode URLs.** Use `reverse('accounts:login')` in Python and `{% url 'accounts:login' %}` in templates. The path string lives in `urls.py` once; everything else refers by name so future renames don't break callers.
3. **FBV vs CBV is a style choice.** FBV (`def view(request): ... return HttpResponse(...)`) for tight custom logic; CBV (subclass + override) for tiny extensions of built-ins like `LoginView`. Both end with an `HttpResponse` — `render(request, template, context)` is the standard shortcut.

---

**Next:** [Step 11 — Templates pointing at `frontend/templates`](11-templates.md) — **stays on `feature/auth-views` branch**. We'll replace the placeholder `HttpResponse('...')` with `render(request, 'accounts/login.html', ...)` and confirm `TEMPLATES['DIRS']` (set back in Step 5) resolves Stitch-exported HTML correctly.
