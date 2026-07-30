# Step 18 — `notifications` app + background tasks

The system tells each user what happened to them: a booking confirmed, a result uploaded, a test requested.
This step is **two things** — an in-app notification feed (the bell), and the emails / scheduled jobs behind it.
Parent-step file — grows one section per sub-step (18a, 18b, …).

**New concepts this step:** a generic notification record, email via SMTP, and background tasks (Celery + Redis)
for the 24-hour reminder and stale-appointment cleanup.

---

## 18a — the app + the `Notification` model

### What
A new Django app `notifications` with a single `Notification` model (one row = "system told user X something"),
plus admin registration and the first migration. No triggers, no bell, no email yet — this is just the data layer.

### Why
One feature = one app (project convention). Every future trigger (booking, result, prescription…) writes the
**same** kind of row: *who* to tell, *what* to say, *where* clicking goes. Model that shape once, reuse everywhere.

### How

**1. Create the app** (scaffolding — run from `backend/`):
```bash
python manage.py startapp notifications apps/notifications
```
Then fix `apps/notifications/apps.py`:
```python
name = 'apps.notifications'      # dotted path so Django finds it under apps/
```
Register it in `config/settings.py` `INSTALLED_APPS`:
```python
    'apps.notifications',
```

**2. The model** (`apps/notifications/models.py`):
```python
from django.db import models
from django.conf import settings


class Notification(models.Model):
    class Type(models.TextChoices):
        BOOKING = 'BOOKING', 'Booking'
        REMINDER = 'REMINDER', 'Reminder'
        TEST = 'TEST', 'Test'
        RESULT = 'RESULT', 'Result'
        PRESCRIPTION = 'PRESCRIPTION', 'Prescription'
        STATUS = 'STATUS', 'Status Update'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    message = models.CharField(max_length=255)
    notification_type = models.CharField(
        max_length=20, choices=Type.choices, default=Type.STATUS,
    )
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.recipient.username} - {self.message[:40]}'
```

**Why each field:**
- **`recipient` → `settings.AUTH_USER_MODEL`** — the Django way to FK the user model (never import `CustomUser`
  directly in a model; avoids circular imports). `CASCADE` — user gone, their notifications gone.
- **`related_name='notifications'`** — gives `user.notifications.all()`, the exact query the bell will run in 18c.
- **`notification_type` as `TextChoices`** — a fixed enum of *categories* (same pattern as `Appointment.Status`).
  The 8 events in the notification matrix collapse to 6 categories; the category drives the icon, not the logic.
- **`link` as a plain `CharField`, not an FK** — notifications point at different pages (appointment, lab result,
  prescription). One text-path column beats three nullable FKs. Store the resolved URL string.
- **`is_read`** — drives the unread badge count.
- **`ordering = ['-created_at']`** — newest first by default (`-` = descending), so no `.order_by()` in every view.

**3. Admin** (`apps/notifications/admin.py`):
```python
from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'message', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__username', 'message')
```
`recipient__username` = FK-span lookup (double underscore hops the FK) so admin search hits the username.

**4. Migration** (from `backend/`):
```bash
python manage.py makemigrations notifications
python manage.py migrate
```

### Gotchas
- `name = 'apps.notifications'` — `startapp` writes bare `notifications`; forgetting the `apps.` prefix breaks import.
- FK the user via `settings.AUTH_USER_MODEL`, never a direct model import.

### Revise
- `Notification` = generic "tell user X something" row: `recipient` + `message` + `notification_type` + `link` + `is_read`.
- `related_name='notifications'` → `user.notifications.all()` is the bell query.
- `link` is a stored URL string, not an FK — one column for many target page types.
- 18a is data-layer only; triggers (18b), bell + email (18c), background tasks (18d) come next.

---

## 18b — the `notify()` helper + 7 in-app triggers

### What
One shared function `notify(recipient, message, notification_type, link='')` in a new
`apps/notifications/services.py`, called from 7 places across three apps so real events start
writing real notification rows. In-app only — email is 18c.

### Why
Seven views want to write a `Notification`. Calling `Notification.objects.create(...)` in all seven
means that when 18c adds email, you edit seven places and silently miss one. A single write path =
one edit, all triggers.

**Why not Django signals?** A `post_save` on `Appointment` fires on *every* save — admin edits,
data imports, future scripts. You lose control of *which* status change means what, and "why did
this notification appear" becomes a hunt. Explicit calls in views stay readable.

**What `services.py` is:** a convention, not a framework file (Django never looks for it).
`models.py` = shape of data · `views.py` = handle one request · `services.py` = the verbs in between.

### How

**1. The helper** (`apps/notifications/services.py`):
```python
from .models import Notification


def notify(recipient, message, notification_type, link=''):
    """Create one in-app notification. Single write path for all triggers."""
    return Notification.objects.create(
        recipient=recipient,
        message=message,
        notification_type=notification_type,
        link=link,
    )
```
- Takes a **recipient object**, not an id — the caller already has it loaded, so assigning it to the
  FK costs zero extra queries. An id would force Django back to the DB.
- **No default for `notification_type`** even though the *model field* has `default=Type.STATUS`.
  The model default protects anonymous writers (admin, shell, imports); the helper is stricter
  because every trigger knows exactly what it is. A missing arg should crash, not silently save STATUS.

**2. `reverse()` — the Python twin of `{% url %}`**
`link` stores a URL *string* (18a decision), so callers resolve it in Python:
```python
from django.urls import reverse
reverse('appointments:my_appointments')          # → '/appointments/mine/'
reverse('lab:test_detail', args=[test.id])       # → '/lab/test/7/'
```
`args=[...]` fills the `<int:test_id>` in the URL pattern. Miss it → `NoReverseMatch` at request
time (`manage.py check` will NOT catch this).

**3. The 7 triggers**

| # | View | File | Recipient | Type |
|---|------|------|-----------|------|
| 1 | `book_appointment` | appointments | patient | BOOKING |
| 2 | `reception_book` (walk-in) | appointments | patient | BOOKING |
| 3 | `confirm_appointment` | appointments | patient | STATUS |
| 4 | `cancel_appointment` | appointments | the *other* party | STATUS |
| 5 | `request_test` | lab | every LAB user | TEST |
| 6 | `upload_result` | lab | patient **+** doctor | RESULT |
| 7 | `write_prescription` | prescriptions | patient | PRESCRIPTION |

Pattern for every one — **after `.save()`, inside the guard**:
```python
    if appointment.status == Appointment.Status.PENDING:
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save()
        notify(
            recipient=appointment.patient,
            message=f'Your appointment on {appointment.appointment_date} is confirmed.',
            notification_type=Notification.Type.STATUS,
            link=reverse('appointments:my_appointments'),
        )
```

**Trigger #4 — "the other party" in two lines.** Patient, doctor or reception can cancel, and nobody
should be told about their own click:
```python
        recipients = [appointment.patient, appointment.doctor]
        for user in recipients:
            if user != request.user:
                notify(...)
```
| Who cancelled | Gets notified |
|---|---|
| Patient | Doctor |
| Doctor | Patient |
| Reception | Both |

Two lines replace a three-branch `if/elif/else` on `request.user.role`.

**Trigger #5 — notify a role, not a person.** "The lab" is a group, so query it:
```python
        for tech in User.objects.filter(role='LAB'):
            notify(recipient=tech, ..., link=reverse('lab:queue'))
```
One row **per tech**, not one shared row — `is_read` lives on the row, so a shared notification
couldn't track "Ravi read it, Sneha didn't."

**Trigger #6 — two calls, no loop.** Patient and doctor need *different* pages
(`lab:my_tests` vs `lab:test_detail`), so two explicit `notify()` calls beat a loop with an `if` in it.
A stored link is not permission to view — `test_detail`'s IDOR guard still applies.

### Gotchas
- **Indentation is the feature.** `notify()` goes *inside* the `if status == ...` guard. That guard is
  the idempotency check — outside it, a double-clicked Confirm button or a refreshed POST writes a
  second row. Valid Python, no error, wrong behaviour (see the grep-list).
- **Notify after `.save()`, never before.** Before the save there's no PK and the write can still fail —
  you'd announce an event that never happened.
- Use `Notification.Type.BOOKING`, never the string `'BOOKING'`. Same value, but the enum survives a
  rename and your editor checks it.
- Keyword arguments at every call site. `notify(x, y, z, w)` is unreadable by call #5.
- `appointment.doctor.username` after `form.save()` is a **lazy FK lookup** = one extra query. Fine
  once on a form submit; N+1 only bites in loops (that's what `select_related` is for).
- `user != request.user` is safe even though `request.user` is a `SimpleLazyObject` — Django's
  `Model.__eq__` compares **primary keys** and the lazy wrapper proxies the comparison through.
- Typo caught this session: `appointment.patent.username` → `AttributeError` *after* the file was
  saved and the first notification written. Anything that can raise after a `.save()` leaves you
  half-done (the real cure is `transaction.atomic()`, later).

### Known duplicate (accepted)
`write_prescription` is create-or-update, so a doctor fixing a typo notifies the patient twice.
Left alone deliberately — a duplicate is noise, not a bug, and it's easier to judge once the bell
exists in 18c.

### Testing without a UI
The bell doesn't exist yet, so read the DB directly (from `backend/`, venv active):
```bash
python manage.py shell -c "from apps.notifications.models import Notification as N; [print(f'{n.recipient.username:<12} {n.notification_type:<12} {n.message[:50]}') for n in N.objects.select_related('recipient')[:10]]"
```
Verify URL names resolve before trusting them — `manage.py check` does not:
```python
reverse('lab:test_detail', args=[1])
```

### Revise
- `services.py` = one shared write path; 18c adds email there once, not in 7 views.
- `reverse('ns:name', args=[...])` = `{% url %}` in Python; resolves the string stored in `link`.
- `notify()` goes **after `.save()` and inside the state guard** — that guard is what stops duplicates.
- Same-link recipients → loop; different-link recipients → separate calls.
- Model instances compare by **primary key**, so `user != request.user` is the whole "other party" rule.

---

## 18c — the bell (in-app delivery)

### What
Notifications existed in the database since 18b but no user could see one. 18c builds the delivery
surface: a 🔔 in the nav with an unread count on **every** page, a list page, and a click that marks
the row read and forwards you to the page the notification is about.

Email is *not* here — it moved to 18d with the Celery work.

### Why
**Why a context processor.** The bell lives in `base.html`, which every page extends. But context is
built by views, and there are ~20 of them. Adding `unread_count` to 20 context dicts is 20 chances to
forget one, and the bell silently disappears on the page you forgot. A **context processor** is a
function Django runs on *every* template render, whose returned dict is merged into that render's
context. Write once, appears everywhere. `user` and `csrf_token` reach your templates by exactly this
mechanism.

**Why a count and not a dropdown.** A dropdown of recent notifications needs those rows fetched on
every single request, for a panel that's mostly never opened. `.count()` is one `SELECT COUNT(*)`
returning one integer. The bell links to a full page instead — the rows are fetched only when someone
actually wants them.

**Why marking-read and navigating are one view.** The only reason to click a notification is to go
look at the thing it announces. So there is no separate "mark as read" button: `open_notification`
flips the flag and redirects. One route, no UI clutter, and the flag can never drift out of sync with
what the user actually looked at.

### How

**1. The views** (`apps/notifications/views.py`):
```python
@login_required
def notification_list(request):
    notifications = request.user.notifications.all()
    return render(request, 'notifications/list.html', {'notifications': notifications})


@login_required
def open_notification(request, notification_id):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user,
    )
    notification.is_read = True
    notification.save()
    return redirect(notification.link or 'notifications:list')
```

`request.user.notifications.all()` is the `related_name` from 18a paying off — Django compiles it to
`WHERE recipient_id = <you> ORDER BY created_at DESC`, the ordering coming free from `Meta.ordering`.
The reverse accessor *is* the filter; no `filter(recipient=...)` needed.

`recipient=request.user` inside `get_object_or_404` is the same IDOR pattern as `doctor=me` (16b) and
`appointment__patient=me` (17c): **authorisation lives in the lookup, not in a separate `if`.** Someone
typing another user's notification id gets a 404.

`redirect()` accepts two kinds of string: a path (`/appointments/mine/`) goes straight into the
`Location` header, a URL *name* (`'notifications:list'`) is run through `reverse()` first. Since `link`
is `blank=True` it can be `''`, and `redirect('')` goes nowhere — the `or` supplies the fallback in one
operator instead of an `if`.

**2. The routes** (`apps/notifications/urls.py` + one `include` in `config/urls.py`):
```python
app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('open/<int:notification_id>/', views.open_notification, name='open'),
]
```
The converter name (`notification_id`) must match the view's parameter name exactly, or Django raises
`TypeError: got an unexpected keyword argument`.

**3. The context processor** (`apps/notifications/context_processors.py`):
```python
def unread_count(request):
    if not request.user.is_authenticated:
        return {}
    return {'unread_count': request.user.notifications.filter(is_read=False).count()}
```
Registered by dotted path in `settings.TEMPLATES[0]['OPTIONS']['context_processors']`.

**4. The bell** (`base.html`, outside the role `if/elif` chain, inside `if user.is_authenticated`):
```html
<a href="{% url 'notifications:list' %}">
    🔔{% if unread_count %} ({{ unread_count }}){% endif %}
</a>
```

**5. The list page** uses `get_notification_type_display` — Django auto-generates `get_FOO_display()`
for any field with `choices`, returning the human label (`'Prescription'`) for the stored value
(`'PRESCRIPTION'`). Called **without parentheses** in a template; the template language calls callables
for you.

### Gotchas
- **A context processor must never raise.** It runs on *every* render, including the login page, where
  `request.user` is `AnonymousUser` and has no `notifications` accessor. Without the
  `is_authenticated` guard, logging in becomes impossible. Returning `{}` is enough — a missing
  template variable is simply empty, so `{% if unread_count %}` is just false.
- `.count()` not `len(queryset)`. `.count()` asks the database for one integer; `len()` drags every
  unread row into Python objects to measure the list.
- `{% if unread_count %}` hides `(0)` — a bell showing zero reads as broken.
- **`link` is a frozen string, not a live lookup.** `reverse()` runs at write time and the result is
  stored. Fixing a wrong link in a view does *not* repair rows already in the database (an FK would
  re-resolve on read; that was the trade for one column serving many page types).
- Typos caught this session: `request.user.notification.all()` (singular — `AttributeError` at request
  time, `check` passes) and `<storng>` (browsers render unknown tags as plain inline elements, so
  unread rows just quietly stopped looking bold).

### Two bugs the bell exposed
Making notifications clickable turned two invisible bugs into visible ones — which is the whole point
of building the delivery surface before adding more triggers.

1. **Cancel sent both parties to `appointments:my_appointments`**, a page that reads
   `request.user.patient_appointments`. A doctor clicking their own cancellation notice landed on an
   empty table — no error, no crash, just a dead end. Fixed with a ternary inside the loop that
   already existed:
   ```python
   target = 'appointments:my_appointments' if user == appointment.patient else 'appointments:doctor_records'
   ```
   Same PK-comparison trick as the `user != request.user` guard one line above.
2. **`{% url 'prescription:write' %}`** (singular) in `doctor_today.html` — dating from 17c. It only
   fired the first time a row on today's page became COMPLETED, because `{% url %}` resolves at render
   time and that link lives inside the COMPLETED branch. `manage.py check` never sees it.

### The duplicate, decided
`write_prescription` re-notifies on edit (18b's parked question). **Left as-is.** An edited
prescription genuinely is news to the patient, and suppressing it would mean threading a `created`
flag through the create-or-update path. Zero code, defensible behaviour.

### Revise
- **Context processor** = a function whose dict is merged into *every* template render. The only way
  to put something in `base.html` without touching every view.
- Authorisation belongs in the lookup (`recipient=request.user`), not in a following `if`.
- `redirect()` takes a path *or* a URL name — `or 'ns:name'` is a one-operator fallback for an empty
  stored link.
- Ask the DB for the number (`.count()`), never for the rows you're going to throw away.
- A stored URL string never re-resolves. Fix the view, and old rows stay wrong.
