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
