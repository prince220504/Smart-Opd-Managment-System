# Step 19a–19b — Reception dashboard (ORM aggregation + Chart.js)

Every page so far asked the database for **rows**: give me this patient's appointments, give me today's list, give me one prescription. A dashboard asks a different kind of question — it doesn't want rows at all, it wants **numbers about rows**.

"How many appointments exist?" is not a list. It's one integer, and the database can produce it far better than Python can.

---

## 1. The warehouse analogy

You own a warehouse with 200,000 boxes. Someone asks: *how many boxes are red?*

**Way one — the Python way.** You drive to the warehouse, load all 200,000 boxes onto a truck, drive them to your office, unload them, and count the red ones on your carpet.

```python
appointments = Appointment.objects.all()      # 200,000 rows into RAM
total = len(appointments)                     # now count them
```

Every row travels over the network, gets turned into a Python object, and sits in memory — so you can throw away everything except one number.

**Way two — the SQL way.** You phone the warehouse manager and ask "how many are red?" He walks the aisles himself and says "forty-one thousand."

```python
Appointment.objects.filter(colour='red').count()    # SELECT COUNT(*) ...
```

One integer crosses the wire. The boxes never move.

That's the whole lesson of aggregation: **make the database do the arithmetic, and ship the answer, not the data.** A dashboard is the page where this matters most, because a dashboard is nothing *but* answers.

---

## 2. `aggregate()` vs `annotate()`

Both push math into SQL. They differ in **what shape comes back**.

### `aggregate()` — collapses everything to one dict

```python
Appointment.objects.aggregate(total=Count('id'))
# {'total': 25}
```

It flattens the entire QuerySet into a **single Python dict**. It is not lazy — the moment you call it, the query runs and you get real values back. There's no QuerySet left to chain onto.

Think: *one number for the whole table.*

### `annotate()` — attaches a value to each row/group

```python
Appointment.objects.values('doctor__username').annotate(total=Count('id'))
# <QuerySet [{'doctor__username': 'admin', 'total': 15},
#            {'doctor__username': 'doc_opd', 'total': 10}]>
```

It computes a value **per group** and hands back a **QuerySet**, still lazy, still chainable — you can `.order_by()` and `.filter()` it afterwards.

Think: *one number per doctor.*

| | `aggregate()` | `annotate()` |
|---|---|---|
| Returns | `dict` | `QuerySet` |
| Lazy? | No — runs immediately | Yes — runs when iterated |
| SQL | `SELECT COUNT(*) FROM ...` | `SELECT ..., COUNT(*) ... GROUP BY ...` |
| Use for | the big number at the top | the bar chart |

**Why it matters:** you cannot swap them. `aggregate()` can't produce a per-doctor breakdown (it collapses everything to one row), and `annotate()` can't give you a plain integer to drop into a stat card (it gives you a QuerySet you'd have to loop).

---

## 3. Conditional aggregation — `Count(filter=Q(...))`

The dashboard needs five status counts. The obvious way:

```python
pending   = Appointment.objects.filter(status='PENDING').count()     # query 1
confirmed = Appointment.objects.filter(status='CONFIRMED').count()   # query 2
completed = Appointment.objects.filter(status='COMPLETED').count()   # query 3
cancelled = Appointment.objects.filter(status='CANCELLED').count()   # query 4
no_show   = Appointment.objects.filter(status='NO_SHOW').count()     # query 5
```

Five round trips. The database walks the appointments table **five separate times**, each time counting one status and ignoring the other four.

`filter=` inside `Count` fixes that:

```python
stats = Appointment.objects.aggregate(
    total     = Count('id'),
    pending   = Count('id', filter=Q(status=Appointment.Status.PENDING)),
    confirmed = Count('id', filter=Q(status=Appointment.Status.CONFIRMED)),
    completed = Count('id', filter=Q(status=Appointment.Status.COMPLETED)),
    cancelled = Count('id', filter=Q(status=Appointment.Status.CANCELLED)),
    no_show   = Count('id', filter=Q(status=Appointment.Status.NO_SHOW)),
    today     = Count('id', filter=Q(appointment_date=today)),
)
```

The generated SQL is one statement with seven counters:

```sql
SELECT COUNT(id),
       COUNT(CASE WHEN status = 'PENDING'   THEN id END),
       COUNT(CASE WHEN status = 'CONFIRMED' THEN id END),
       ...
FROM appointments_appointment;
```

**What physically happens:** the database walks the table **once**. For each row it checks the conditions and bumps whichever counters match — the row is already in the CPU's hands, so testing seven conditions on it is nearly free. Reading the row off disk is the expensive part, and this way you pay for it once instead of five times.

Note `Count('id')` and not `Count('*')`. Counting a column means "count rows where this column isn't NULL", which is why `CASE WHEN ... THEN id END` works: rows that don't match produce `NULL` and don't get counted.

---

## 4. `values()` before `annotate()` = SQL `GROUP BY`

```python
per_doctor = (
    Appointment.objects
    .values('doctor__username')        # ← GROUP BY this column
    .annotate(total=Count('id'))       # ← count each group
    .order_by('-total')                # ← biggest first
)
```

Order matters and it reads like English:

- `.values('doctor__username')` — "bucket the rows by doctor username"
- `.annotate(total=Count('id'))` — "and tell me how many are in each bucket"

Put `.annotate()` **before** `.values()` and you get something else entirely (a per-row annotation), so keep the order.

### The `__` span

`doctor__username` is a **double-underscore span** — it follows the `doctor` ForeignKey into `CustomUser` and reads that user's `username`. It becomes a `JOIN` in the same query:

```sql
SELECT u.username, COUNT(a.id)
FROM appointments_appointment a
JOIN accounts_customuser u ON u.id = a.doctor_id
GROUP BY u.username;
```

**Why it matters:** without the span you'd get `doctor_id` numbers, then loop them and hit the user table once per doctor — the N+1 problem again, in aggregate clothing.

### `values()` gives dicts, not model objects

This is the part that surprises people. `.values()` turns each result into a **plain dict**, and the key is the exact string you spanned:

```python
{'doctor__username': 'admin', 'total': 15}
```

So the template is:

```django
{{ row.doctor__username }}      ✅
{{ row.doctor.username }}       ❌ renders empty, no error
```

Double underscore survives all the way into the HTML.

---

## 5. UTC bites again — `timezone.localdate()`

```python
today = timezone.localdate()          ✅
today = date.today()                  ❌
```

Same trap as Step 18e. `USE_TZ=True` means the database stores UTC, and IST is UTC+5:30. At **02:00 on the 5th in Mumbai**, UTC is still **20:30 on the 4th**. A server using `date.today()` would count the 4th's appointments and label them "Today".

`timezone.localdate()` converts *now* into the `TIME_ZONE` you configured (`Asia/Kolkata`) and hands back the date a person in that timezone would agree with.

---

## 6. Getting data from Python into JavaScript — `json_script`

The charts need `per_doctor` and `stats` **as JavaScript values**. The obvious attempt is a trap:

```django
<script>
  var data = {{ per_doctor }};      <!-- broken AND dangerous -->
</script>
```

Two independent failures.

### Failure 1 — it isn't JSON

Django renders Python's `repr()`:

```js
var data = [{'doctor__username': 'admin', 'total': 15}];
```

Single quotes. Valid Python, **invalid JSON**, and `Uncaught SyntaxError` in the browser. Python's `None`/`True` would come out as `None`/`True` too, not `null`/`true`.

### Failure 2 — it's an XSS hole

Usernames come from a registration form, which means **a user controls that text**. Register as:

```
</script><script>alert(document.cookie)</script>
```

Now your template writes that string inside a `<script>` block. The browser sees a closing tag, ends your script early, and runs theirs. Django's autoescape doesn't save you — it escapes for *HTML* context, and `&#x27;` inside a `<script>` block is not what JavaScript needs anyway, so it corrupts your data *and* leaves the hole.

### The fix

```django
{{ per_doctor|json_script:"per-doctor-data" }}
{{ stats|json_script:"stats-data" }}
```

renders:

```html
<script id="per-doctor-data" type="application/json">
[{"doctor__username": "admin", "total": 15}, {"doctor__username": "doc_opd", "total": 10}]
</script>
```

Two things make this safe:

1. **`type="application/json"`** — the browser sees a MIME type it does not execute. It parses the tag, stores the text, and runs nothing. A `<script>` block that can only ever be data.
2. **The filter escapes `<`, `>` and `&`** into JSON unicode escapes (a backslash-`u` sequence, e.g. `<` becomes `u003C`). `JSON.parse` turns them back into the right characters inside JavaScript, but the browser's **HTML** parser never sees a literal `<` in the block — so there is no way to type a closing tag that survives.

JavaScript then reads it **deliberately**, which is the point — data crosses the boundary through a channel that can only carry data:

```js
const perDoctor = JSON.parse(document.getElementById('per-doctor-data').textContent);
```

`.textContent`, not `.innerHTML` — you want the raw characters, not the browser's HTML interpretation of them.

### `json_script` needs a real list

```python
per_doctor = list(
    Appointment.objects.values('doctor__username').annotate(total=Count('id'))
)
```

The `list()` is not decoration. `json_script` serializes with `DjangoJSONEncoder`, and a **QuerySet is not JSON serializable** — without it you get:

```
TypeError: Object of type QuerySet is not JSON serializable
```

`aggregate()` needs no such treatment; it already handed back a plain dict of integers.

---

## 7. Chart.js in fifteen lines

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  const perDoctor = JSON.parse(document.getElementById('per-doctor-data').textContent);
  const stats     = JSON.parse(document.getElementById('stats-data').textContent);

  new Chart(document.getElementById('doctorChart'), {
    type: 'bar',
    data: {
      labels: perDoctor.map(row => row.doctor__username),
      datasets: [{
        label: 'Appointments',
        data: perDoctor.map(row => row.total),
        backgroundColor: '#4e79a7',
      }]
    },
    options: { scales: { y: { beginAtZero: true } } }
  });
</script>
```

The shape Chart.js wants is always the same: **`labels` is an array of strings, `data` is an array of numbers, and the two must line up index for index.** `.map()` is what turns a list of dicts into those two parallel arrays.

`new Chart(canvasElement, config)` — Chart.js draws onto a `<canvas>`, which is a fixed-size bitmap the browser gives you to paint on. That's why the canvas sits inside a sized `<div>`; a canvas with no width constraint expands to fill whatever it can.

A doughnut is the same call with `type: 'doughnut'` and one dataset of five numbers. Note that `Pending = 0` still shows up in the legend — Chart.js builds legends from `labels`, not from which values happen to be non-zero.

---

## 8. Gotchas

### `getElementByID` — one letter, both charts blank

```js
document.getElementByID('per-doctor-data')     ❌
document.getElementById('per-doctor-data')     ✅
```

JavaScript is case-sensitive, and this is the **second time** this exact typo has appeared in the project (Step 17b killed the "+ Add medicine" button the same way).

This version is nastier than 17b's. `document.getElementByID` isn't a function at all, so it throws `TypeError: document.getElementByID is not a function` — and **a thrown error aborts the entire `<script>` block**. The line was in the first statement, so `stats`, both `new Chart()` calls, everything below it never ran. **One typo, two blank charts, and neither one is the chart the typo mentions.**

The lesson: a blank canvas tells you nothing. **Open the browser console first** — it names the file, the line, and the exact word.

### Dict-key typos in templates render empty

```django
{{ stats.completd }}
```

`stats` is a plain dict. Django's dot-lookup tries the key, misses, and — per template design — **renders an empty string rather than raising**. `check` passes, the page loads, the card just says nothing. Same family as the context-dict key typo already on the grep-list, now one level deeper.

### `values()` key in the template

`{{ row.doctor.username }}` looks more natural than `{{ row.doctor__username }}` and is silently wrong for the same reason — missing key, empty output, no error.

---

## 9. What we deliberately skipped

| Skipped | Why | Add when |
|---|---|---|
| A separate `dashboard` app | Adds no models. It's a read over `Appointment`, which already lives in `appointments` | it grows its own tables |
| A CSS file / `static/css/` | Project has no stylesheet yet; Step 21 rebuilds the frontend anyway. Four rules in an inline `<style>` cover it | Step 21 |
| Chart.js as an npm dependency | CDN `<script>` tag is one line and needs no build step | there's a build pipeline to put it in |
| Date-range filters on the stats | Nobody asked. `aggregate` takes a `.filter()` in front of it whenever they do | reception wants "this month" |

---

## Revise (3 lines)

1. **`aggregate()` returns one dict, `annotate()` returns a QuerySet** — big number at the top vs one number per group; `values('x').annotate(...)` *is* SQL `GROUP BY`, and the template key keeps the double underscore (`row.doctor__username`).
2. **`Count('id', filter=Q(...))` counts five statuses in one table scan** instead of five — the row is already in hand, so extra conditions are nearly free while re-reading the table is not.
3. **`json_script` is the only safe way to hand Python data to JavaScript** — `type="application/json"` is never executed and `<`/`>`/`&` are escaped, so a username containing `</script>` can't break out; wrap QuerySets in `list()` first, and read with `getElementById` (capital `E`, lowercase `d` — a `TypeError` there kills every chart on the page).
