# Step 11 — Templates

## What we did here

1. Made a shared shell file `frontend/templates/base.html` — the header + nav + footer that every page reuses.
2. Made 3 small page files inside `frontend/templates/accounts/` — `login.html`, `register.html`, `logout.html`. Each one fills in only its own middle section.
3. Changed `backend/apps/accounts/views.py` — replaced the plain text `HttpResponse('...')` with `render(request, 'accounts/login.html')` so the browser now gets real HTML pages.
4. Checked all 3 URLs in the browser — login, register, logout pages all show up with the same header and footer.
5. Made 3 small commits on `feature/auth-views`.

Before Step 11, our views returned one line of plain text. After Step 11, they return full HTML pages with forms, links, and a shared layout. This is the first time the site **looks like a website**.

---

## Section 1 — What a template actually is

A **template** is just an HTML file with a few extra tags that Django understands.

Here is a tiny example.

A plain HTML file:

```html
<h1>Hello Prince</h1>
```

A Django template:

```html
<h1>Hello {{ name }}</h1>
```

The `{{ name }}` is a placeholder. When Django sends the page to the browser, it swaps `{{ name }}` with a real value (like `"Prince"`).

So the browser only ever sees normal HTML. The Django tags are just markers that tell Django **where to fill stuff in** before sending.

**Three kinds of tags you'll see today:**

| Tag | What it does | Example |
|-----|--------------|---------|
| `{{ something }}` | Print a value | `{{ user.username }}` |
| `{% something %}` | Do an action (if / for / load / extends) | `{% if user.is_authenticated %}` |
| `{# something #}` | A comment (browser never sees it) | `{# todo: add forgot password #}` |

That's it. Once you see those three shapes, you can read any Django template on the internet.

---

## Section 2 — Why we need `frontend/templates/` (and how Django finds it)

We told Django **where to look for templates** way back in Step 5. Open `backend/config/settings.py` and find this block:

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR.parent / 'frontend' / 'templates'],  # ← this line
        'APP_DIRS': True,
        ...
    },
]
```

`BASE_DIR` points at `backend/`. So `BASE_DIR.parent` is the project root, and `BASE_DIR.parent / 'frontend' / 'templates'` is our `frontend/templates/` folder.

Now when our code says `render(request, 'accounts/login.html')`, Django:

1. Looks inside `frontend/templates/`
2. Finds the folder `accounts/`
3. Finds the file `login.html`
4. Reads it, fills in the tags, sends the HTML to the browser

**Simple test in your head:** "If I move the templates folder somewhere else, will Django still find it?"
Answer: No, unless you also change the `DIRS` line. The setting is the only thing that tells Django where to look.

---

## Section 3 — The shared shell idea (`base.html`)

Every page on our site needs the same wrapper:

- `<!DOCTYPE html>` at the top
- A `<head>` with the title and CSS link
- A `<header>` with the nav links
- A `<footer>` at the bottom

Without templates, we'd copy-paste this wrapper into **every single page**. Then if we ever change one nav link, we'd have to change it in 30 places. That's the problem.

**The fix:** write the wrapper once in `base.html`. Other pages "extend" it and only fill in the middle.

Picture it like a printed form:

```
+---------------------------------+
|  HEADER (same on every page)   |
+---------------------------------+
|                                 |
|   ← child fills this hole      |
|                                 |
+---------------------------------+
|  FOOTER (same on every page)   |
+---------------------------------+
```

`base.html` is the form. `login.html`, `register.html`, etc. fill in the hole.

### How the "hole" works in code

In `base.html`:

```html
<main>
    {% block content %}{% endblock %}
</main>
```

`{% block content %}{% endblock %}` says: **"This is a hole named `content`. Child pages can fill it."**

In `login.html`:

```html
{% extends 'base.html' %}

{% block content %}
    <h1>Log in</h1>
    <form>...</form>
{% endblock %}
```

`{% extends 'base.html' %}` says: **"Start with the base.html shell."**
`{% block content %}...{% endblock %}` says: **"Put this stuff in the hole named `content`."**

When Django combines them, the browser gets:

```html
<!-- everything from base.html, with the hole filled in: -->
<main>
    <h1>Log in</h1>
    <form>...</form>
</main>
```

### Two important rules

1. **`{% extends '...' %}` must be the very first line** of the child template. Not even a blank line before it. Django checks this.
2. **A child can have more than one block.** Our pages have `title` and `content` blocks — each one fills a different hole.

---

## Section 4 — Our `base.html` line by line

Here is the whole file. We'll read it once top-to-bottom.

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{% block title %}Smart OPD{% endblock %}</title>
        <link rel="stylesheet" href="{% static 'css/main.css' %}">
    </head>
    <body>
        <header>
            <nav>
                <a href="{% url 'accounts:login' %}">Log in</a>
                <a href="{% url 'accounts:register' %}">Register</a>
            </nav>
        </header>
        <main>
            {% block content %}{% endblock %}
        </main>
        <footer>
            <p>Smart OPD Management System</p>
        </footer>
    </body>
</html>
```

| Line | What it does |
|------|--------------|
| `{% load static %}` | Tells Django: "I'm going to use the `{% static %}` tag below — please load it." Without this line, `{% static %}` errors out. |
| `<title>{% block title %}Smart OPD{% endblock %}</title>` | A hole called `title`. If a child page doesn't fill it, the title falls back to `"Smart OPD"`. |
| `<link ... href="{% static 'css/main.css' %}">` | Builds the URL `/static/css/main.css`. `{% static %}` adds the right prefix in front so we don't hardcode `/static/`. |
| `<a href="{% url 'accounts:login' %}">` | Looks up the URL named `login` inside the `accounts` app, gives back `/accounts/login/`. Same rule as Step 10 — never type the path by hand. |
| `{% block content %}{% endblock %}` | The main hole. Every child page fills this. |

### Why `{% static %}` instead of `/static/css/main.css`

Two reasons:

1. **In production**, the static URL might not be `/static/`. It might be a CDN like `https://cdn.smart-opd.com/`. `{% static %}` reads the current setting and builds the right URL.
2. **Easy to change.** If we move the static folder later, we change `STATIC_URL` once. Every page that uses `{% static %}` updates automatically.

Same idea as `{% url %}` from Step 10: the **name** stays stable, the **actual value** can change.

---

## Section 5 — The 3 child templates

All 3 follow the same pattern: extend the base, fill the `title` block, fill the `content` block.

### `login.html`

```html
{% extends 'base.html' %}

{% block title %}Log in - Smart OPD{% endblock %}

{% block content %}
<h1>Log in</h1>

<form method="post" action="{% url 'accounts:login' %}">
    {% csrf_token %}

    <label for="id_username">Username</label>
    <input type="text" name="username" id="id_username" required>

    <label for="id_password">Password</label>
    <input type="password" name="password" id="id_password" required>

    <button type="submit">Log in</button>
</form>

<p>No account? <a href="{% url 'accounts:register' %}">Register</a></p>
{% endblock %}
```

The `<form>` is the new piece — see Section 6 for `{% csrf_token %}`.

### `register.html`

Same pattern, just more fields. Six inputs: username, email, phone (with the Indian-mobile pattern from Step 7), role (a dropdown), password, password_confirm.

```html
<input type="tel" name="phone" id="id_phone" pattern="[6-9][0-9]{9}" placeholder="9876543210">
```

The `pattern="[6-9][0-9]{9}"` makes the **browser** reject anything that isn't a 10-digit number starting with 6/7/8/9. This is **only the first line of defense**. The real check is the `RegexValidator` on the model (Step 7). Why both?

- **Browser check** = nice user experience (instant red border, no round trip).
- **Server check** = real security. Anyone can edit HTML in DevTools and bypass the browser pattern. The server validator catches them.

This is called **defense in depth**: check twice, once for friendliness, once for safety.

### `logout.html`

The smallest one — just a confirmation message and two links.

```html
{% extends 'base.html' %}

{% block title %}Logged out - Smart OPD{% endblock %}

{% block content %}
<h1>Logged out</h1>
<p>You have been logged out successfully</p>
<p>
    <a href="{% url 'accounts:login' %}">Log in again</a>
    or
    <a href="{% url 'accounts:register' %}">Register</a>
</p>
{% endblock %}
```

No form, no inputs. Just text plus two `{% url %}` links.

---

## Section 6 — `{% csrf_token %}` in 60 seconds

Every `<form method="post">` in Django **must** have `{% csrf_token %}` inside it. Skip it → Django returns **403 Forbidden** instead of processing the form.

### Why does this exist?

CSRF = Cross-Site Request Forgery. The short version:

1. You log in to our site. Django gives your browser a cookie that says "this is Prince's session."
2. You go to a sketchy site in another tab.
3. That sketchy site has a hidden form that POSTs to **our** site (something like "transfer all money to attacker").
4. Your browser sends our session cookie along with that POST — because that's how cookies work.
5. Our server thinks Prince made that request and runs the action.

That's the attack. The user didn't click anything dangerous. Just **opening** the sketchy site was enough.

### How `{% csrf_token %}` blocks it

When the login page loads:

1. Django generates a secret random string (the "CSRF token").
2. `{% csrf_token %}` puts that string in a hidden input inside the form: `<input type="hidden" name="csrfmiddlewaretoken" value="abc123...">`.
3. Django also stores the same string in a cookie on your browser.
4. When you submit the form, Django checks: **does the hidden input match the cookie?**
5. If yes → request is real, process it.
6. If no (or hidden input is missing) → return 403.

The attacker on the sketchy site **cannot read** the hidden token (the browser blocks cross-site reads). So they can't include it in their fake form. The check fails. Attack blocked.

**Easy rule:** every POST form gets `{% csrf_token %}` right after the `<form>` tag. No exceptions.

### Quick check yourself

After running the server, open `/accounts/login/`, right-click → **View page source**. You should see:

```html
<input type="hidden" name="csrfmiddlewaretoken" value="...random string...">
```

That hidden input is `{% csrf_token %}` doing its job.

---

## Section 7 — Swapping `HttpResponse` for `render()`

The old view (Step 10):

```python
from django.http import HttpResponse

def login_view(request):
    return HttpResponse('Login page — coming in Step 12')
```

The new view (Step 11):

```python
from django.shortcuts import render

def login_view(request):
    return render(request, 'accounts/login.html')
```

What changed:

| Old | New |
|-----|-----|
| Import `HttpResponse` | Import `render` |
| Return plain text | Return a rendered template |
| 1 argument: a string | 2-3 arguments: `(request, template_path, context_dict)` |

### What `render()` is doing under the hood

```python
return render(request, 'accounts/login.html', {'page_title': 'Log in'})
```

is shorthand for:

```python
template = loader.get_template('accounts/login.html')
html = template.render({'page_title': 'Log in'}, request)
return HttpResponse(html)
```

Same three steps every time: **find the file → fill in the placeholders → wrap in `HttpResponse`**. `render()` just does them all in one line.

### The 3rd argument — the context dict

We didn't pass one today because our templates have no `{{ ... }}` placeholders yet. But it'll show up in Step 12. Example:

```python
def login_view(request):
    return render(request, 'accounts/login.html', {'next_url': '/dashboard/'})
```

In the template:

```html
<input type="hidden" name="next" value="{{ next_url }}">
```

The dict keys (`next_url`) become the names you use inside `{{ }}` in the template. That's the bridge from Python to HTML.

---

## Section 8 — Verifying in the browser

```bash
cd backend
python manage.py runserver
```

Open each URL. You should see:

| URL | What you see |
|-----|--------------|
| `/accounts/login/` | Nav at top, "Log in" heading, form with username + password + Log in button, "No account? Register" link, footer at bottom |
| `/accounts/register/` | Same nav and footer, "Create account" heading, 6 fields, role dropdown showing 4 options |
| `/accounts/logout/` | Same nav and footer, "Logged out" heading, two links |

### What to check carefully

1. **Header and footer look identical on all 3 pages** — proves `base.html` is being shared correctly.
2. **Click the "Log in" link in the nav from the register page** — should land on `/accounts/login/`. Proves `{% url 'accounts:login' %}` works.
3. **Right-click → View page source on the login form** — look for `<input type="hidden" name="csrfmiddlewaretoken" ...>`. Proves `{% csrf_token %}` works.
4. **Type a letter into the phone field on the register page and try to submit** — the browser should block it with a popup. Proves `pattern="[6-9][0-9]{9}"` works.

If any of those fail, the most likely cause is a typo. Read the file again — Django will print a clear error in the terminal if a tag is broken.

### Common error you'll see if a tag is wrong

```
TemplateSyntaxError at /accounts/login/
Invalid block tag on line 8: 'url'
```

Usually means missing `%}` or stray quote. Reload the file, fix it, refresh — no need to restart `runserver`.

---

## Section 9 — Three commits

We landed Step 11 in 3 atomic commits. Each one is one logical idea.

```bash
# Commit 1 — the shared shell
git add frontend/templates/base.html
git commit -m "feat(accounts): add base.html template with nav + content block"

# Commit 2 — the 3 child pages
git add frontend/templates/accounts/
git commit -m "feat(accounts): add login/register/logout templates"

# Commit 3 — point the views at the templates
git add backend/apps/accounts/views.py
git commit -m "refactor(accounts): swap placeholder HttpResponse for render() with templates"

git push
```

### Why split this way

- **Commit 1** — Pure infrastructure. The shell exists, but no page uses it yet.
- **Commit 2** — The 3 pages now exist. They reference `base.html` (commit 1), but `views.py` still returns text — no one actually sees the templates yet.
- **Commit 3** — Wire it up. `views.py` now points at the templates.

If you read the git history later, you can answer 3 different questions by reading 3 different commits:
- "When did we add a shared layout?" → commit 1
- "When did the auth pages first exist?" → commit 2
- "When did the views stop returning plain text?" → commit 3

That's the point of atomic commits: each one answers one question cleanly.

### Why `refactor` and not `feat` for commit 3

`refactor` means: **same behavior, different implementation**.

Before commit 3, the URL returns text. After commit 3, it returns HTML. The user-facing behavior changed (the user now sees a real page), so you could argue `feat` here. Both are defensible. The line is fuzzy. The rule of thumb: if you're swapping placeholder code for real code, `refactor` reads cleaner because the URL was already wired up.

---

## Gotchas

- **`{% extends '...' %}` must be the first line.** Even a blank line before it will throw a `TemplateSyntaxError`. Some IDEs auto-insert one. Watch for it.
- **`{% csrf_token %}` missing → 403 on POST.** Easy to forget. If you ever see a 403 on a form, this is the first thing to check.
- **Stray apostrophes from IDE autocomplete.** Day 9 had 5 of these in `register.html` (`for="'id_username"` with a leading `'`). Antigravity sometimes drops them. If a form breaks for no obvious reason, eyeball every attribute quote.
- **`{% load static %}` only loads for that one file.** It does **not** carry into child templates. If your child template uses `{% static %}`, that file needs its own `{% load static %}` at the top.
- **Forgetting the folder prefix in `render()`.** Write `render(request, 'accounts/login.html')`, **not** `'login.html'`. Django searches all of `frontend/templates/` and would not find a bare `login.html`.
- **Typo in template path.** `render(request, 'account/login.html')` (missing `s`) → `TemplateDoesNotExist`. The traceback page shows every folder Django searched — read it.
- **HTML5 `pattern=` is not security.** Anyone with DevTools can remove it. The real check is the model-level `RegexValidator` on the `phone` field (Step 7). HTML5 pattern = good UX, not protection.
- **`{% url 'login' %}` (no `accounts:` prefix) → `NoReverseMatch`.** Step 10 fixed this with `app_name = 'accounts'`. Always use the full `accounts:login` form.

---

## Where this plugs into future steps

| Feature | When | How today's work helps |
|---------|------|------------------------|
| Real login form processing | Step 12 | The `login.html` form is already wired — Step 12 just adds the Python that handles the POST |
| Logged-in nav menu (show "Logout" instead of "Log in" when user is signed in) | Step 12 | Add `{% if user.is_authenticated %}` inside `base.html`'s `<nav>` block |
| Dashboard pages | Step 13+ | Each one extends `base.html` and fills `content`. The shared layout is free now |
| Role-based menus | Step 13+ | `{% if user.role == 'DOCTOR' %}` inside the nav block — show doctor menu, hide patient menu |
| Email templates | Step 15 | Same template engine, different folder (`frontend/templates/email/`). The `{% extends %}` trick works there too |

Every page from here on rides on `base.html`. The shell only gets written once.

---

## Revise (3-line summary)

1. **One shell, many fillers.** `base.html` holds the header / nav / footer once. Every page starts with `{% extends 'base.html' %}` and fills the `{% block content %}` hole. Change the nav in one place, every page updates.
2. **Three template tags do the heavy lifting.** `{% url 'app:name' %}` builds links by URL name (never hardcode paths). `{% load static %}` + `{% static 'file' %}` builds asset URLs. `{% csrf_token %}` is required inside every POST form or Django returns 403.
3. **`render()` connects views to templates.** Old views returned `HttpResponse('text')`. New views return `render(request, 'accounts/login.html', context)`. The third argument is a dict — its keys become `{{ variable }}` placeholders in the template.

---

**Next:** [Step 12 — Auth forms (login, register, profile)](12-auth-forms.md) — **stays on `feature/auth-views` branch**. We'll add real Python logic behind the forms: hash the password, log the user in, save the new account to the DB, and redirect by role. The HTML stays the same — only the view code changes.
