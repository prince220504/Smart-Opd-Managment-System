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
