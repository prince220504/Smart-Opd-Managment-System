# 20f + 20g — real names, and a profile people can finish

Day 46. Two sub-steps in one session. Until today the app had no idea what
anyone was called. It printed the login name instead, so the doctor list read
"Dr. doc_opd" and the reception desk labelled a text box "Full name" over a
field that actually held a username.

---

## 20f — `full_name`

### The field

```python
full_name = models.CharField(max_length=100, blank=True)
```

`blank=True` is about **forms**, not the database. It says an empty string is
allowed. Seven accounts already existed with no name; without `blank=True`
Django's own admin would refuse to save any of them.

No `null=True`. A text column should have exactly one way to be empty — `''`.
Allow `NULL` as well and every check has to test for both, forever.

The migration ran without asking anything:

```
Migrations for 'accounts':
  0004_customuser_full_name.py
    + Add field full_name to customuser
```

No "you are trying to add a non-nullable field" prompt, because Django knows a
CharField's empty value is `''` and fills every existing row with it.

### Loose in the database, strict at the door

The model allows an empty name. The register form does not:

```python
class RegisterForm(forms.ModelForm):
    full_name = forms.CharField(max_length=100)
```

A hand-declared form field **overrides** the one Django would build from the
model. Model says optional, declared field says required. And because
`WalkInPatientForm` subclasses `RegisterForm`, one line makes it required in
both forms.

Same pattern as `age` on Day 45: nullable on the model so old rows survive,
required in the form so nothing new slips through.

### `display_name` — the badge

Fifty template spots needed "the name, or the username if there isn't one".
Writing that fifty times is fifty chances to write it differently.

Think of a hospital ID badge. It has a printed legal name and, for some staff,
just a scribbled nickname. Reception never decides which to read — they read
whatever is on the badge. The badge already made the choice.

```python
@property
def display_name(self):
    return self.full_name or self.username
```

Python's `or` returns the first truthy value. An empty `full_name` is `''`,
which is falsy, so it falls through to `username`.

This is why no backfill migration was needed. The seven nameless accounts keep
rendering exactly as before, and the moment someone types a name, every page
picks it up at once. The reception dashboard proved it in one table:
"Dr. Utsav Bhavsar" and "Dr. admin" side by side, same code path.

A `@property` is Python only. No column, no migration. `makemigrations` says
"No changes detected" and that is correct.

### Why a property and not a template filter

A template filter would only help templates. `display_name` also works in the
notification f-strings, the CSV export and `__str__` — the same rule in one
place for the whole app.

### Where `username` still wins

Not everything that shows a name should show the *display* name:

| Thing | Uses | Why |
|---|---|---|
| Notification messages, CSV rows, page headings | `display_name` | a person reads them |
| Login form, admin identity column, profile "Username" row | `username` | it identifies an account |
| Search boxes | **both** | a receptionist types "Ananya", not "ananya_iyer" |

The search filters became `Q | Q`:

```python
appointments.filter(Q(doctor__full_name__icontains=q) | Q(doctor__username__icontains=q))
```

Note the brackets. These were plain keyword arguments before; two `Q` objects
joined with `|` are a single positional argument.

### The one place a property cannot reach

The reception dashboard's per-doctor table is built with `values()`, which
returns plain **dicts**, not `CustomUser` objects. No object, no property. That
one had to ask SQL for both columns:

```python
.values('doctor__full_name', 'doctor__username')
```

and spell the fallback out in the template:

```
{{ row.doctor__full_name|default:row.doctor__username }}
```

Adding a column changes the `GROUP BY` to group on the pair. Harmless here —
one doctor is one pair, so the row count is unchanged.

### The typo `check` could not see

```python
Q(doctor__ful_name__icontains=q)
```

One missing `l`. `python manage.py check` passed. Field lookups are resolved
when the **query runs**, not at import — and this one sits inside `if q:`, so
the page loads fine and only raises `FieldError: Cannot resolve keyword
'ful_name'` the moment someone uses the search box. Silent until a user does
the one thing the line exists for.

---

## 20g — one page for editing and for completing

Self-registration asks for five things. Age, gender, blood group and address
are collected **after** first login instead — a stranger filling eight boxes
abandons the form.

Completing a profile and editing one are the same act on the same fields, so
they are one form, one view, one URL. Completing is just editing an empty one.

### A form that changes shape

```python
if self.instance.role == 'PATIENT':
    self.fields['age'].required = True
else:
    for name in ('age', 'blood_group', 'address'):
        del self.fields[name]

if self.instance.role != 'DOCTOR':
    del self.fields['department']
```

Picture the counter clerk with one master form that has every box on it.
Before handing it to a doctor they cut out the "blood group" and "address"
rows with scissors. The doctor gets a shorter sheet. If they scribble a blood
group in the margin, the clerk has no box to copy it into, so it goes nowhere.

That last part is the point. Hiding a box in the template is only paint —
anyone can still POST `blood_group=X` and Django will save it. `del
self.fields[name]` means `is_valid()` never looks at that key, so the column
cannot be touched. **Server-side removal, not CSS.**

`self.instance` is already the logged-in user when `__init__` runs, because
`ProfileForm(instance=request.user)` sets it before `super().__init__()`
returns.

### The template follows the Python

```
{% if form.age %}
```

When `__init__` deleted the field, `form.age` fails to resolve and Django
renders it as empty — falsy — so the block is skipped. One template serves all
four roles without a single `{% if user.role %}`. **The Python decides the
shape; the template just draws it.**

### The view needs no guard

```python
form = ProfileForm(request.POST, instance=request.user)
```

There is no id in the URL, so there is nothing to tamper with. `instance=request.user`
**is** the authorisation check.

### The gate

```python
if not user.age:
    return redirect('accounts:profile_edit')
return redirect('appointments:patient_dashboard')
```

Two lines in the patient branch of `login_view`, copying the doctor
availability gate directly above it.

`age` is the sentinel because it is the only field that is `NULL` until
someone fills it, and it is the one the form makes required — so "has an age"
and "finished the form" mean the same thing. **No `profile_completed` boolean.**
A flag can drift out of sync with the thing it describes; reading the data
itself cannot.

Three things fall out of that for free:

- doctor, reception and lab return earlier, so they never hit the gate
- walk-in patients already have an age from the counter form, so they skip it
- nothing new has to be written when a patient completes the form

`register_view` needed the same redirect. It logs the user in itself, so a
brand-new patient never passes through `login_view` and would have skipped the
gate on the very first visit — the one time it matters most.

**Deliberate limit:** the gate fires at login only. A patient who clicks away
is not chased. Middleware that redirects on every request is a lot of
machinery for a nag screen.

---

## What the tests found

Nine assertions driven through Django's test client against the real
database — status codes prove a page loads, not that it is right.

Two "failures" were the test's fault, not the code's: the patient used for the
search check had zero appointments, and the appointment used for the
consultation check was `CANCELLED`, so the page correctly returned 404. Both
passed on valid rows.

The best evidence was the reception dashboard rendering "Dr. Utsav Bhavsar"
and "Dr. admin" in the same table — the `or` fallback working on real data.

---

## The icon audit

Prince spotted that the **Dashboard** link had a different icon in each of the
four roles — house, calendar, grid, flask. Looking for more of the same class
of bug found the mirror image: one document glyph used for patient
*Prescriptions*, doctor *Appointment Records* and lab *Test Requests*.

The rule an icon set needs is one sentence: same meaning, same glyph;
different meaning, different glyph.

Checked and found genuinely clean: the status pill copied into 8 templates has
no colour drift, and the lab templates' "missing" statuses are a different
model (`LabTest`) entirely.

Also added: the sidebar now marks the page you are on. Done in `main.js` by
longest-matching-prefix rather than an `{% if %}` on all 17 links, so a new
nav item gets it for free.

### The scripted edit that ate 87 lines

The first attempt at the icon swap used this:

```python
re.compile(r'(<svg[^>]*>)(.*?)(</svg>\s*\n\s*Dashboard\s*\n\s*</a>)', re.S)
```

`.*?` is non-greedy, but the **start** of the match is not. The engine found
the first `<svg` in the file — the logo at line 29 — and expanded from there
until it hit the patient's Dashboard label at line 39, deleting everything in
between. 87 lines gone, and the file still compiled.

Reverted with `git checkout`, redone line-anchored: each icon is one complete
`<svg>…</svg>` on a single line, so nothing needs to span. Final diff, 5 lines.

Already on the grep-list as "scripted edit anchored on markup that repeats in
the same file". Third occurrence in this project.
