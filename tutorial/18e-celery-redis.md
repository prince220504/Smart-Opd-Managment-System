# Step 18e — Celery + Redis (background tasks)

Everything before this ran **inside the request**. A patient clicks "Book", and Django does every single thing — save the row, build the message, talk to Gmail — before the browser gets a page back.

This step is where the app learns to say *"I'll do that later"*.

---

## 1. The restaurant analogy

Picture a small restaurant with **one waiter** and no kitchen staff.

A customer orders pasta. The waiter takes the order, walks into the kitchen, boils the water, cooks the pasta, plates it, and brings it out. Only *then* can he take the next customer's order.

Ten customers walk in. Nine of them stand at the door watching the waiter stir a pot.

That is your booking view on Day 38:

```
patient clicks Book
   → Django saves the appointment          (fast, 5 milliseconds)
   → Django phones Gmail and waits         (SLOW, 5 seconds)
   → browser finally gets a page
```

The patient waited five seconds for a booking that was already saved in five milliseconds. They waited on the *email*.

Now hire a **cook**, and put an **order rail** between the waiter and the kitchen — that metal strip where order tickets get clipped.

- Waiter takes the order, **clips the ticket to the rail**, walks straight back out. Two seconds.
- Cook pulls tickets off the rail, one at a time, and cooks.
- If the cook burns the pasta, he cooks it again. The customer never knew.

| Restaurant | Your app |
|---|---|
| Waiter | Django view (`runserver`) |
| Order rail | **Redis** (the broker) |
| Cook | **Celery worker** |
| Ticket | a task message (JSON) |
| Clipping the ticket | `.delay()` |

Three separate people. Three separate processes on your machine. That is the whole idea.

---

## 2. What each piece actually is

### Redis — the order rail

**Redis** is a database that lives in RAM instead of on disk. That makes it extremely fast and a little forgetful (RAM empties when the power goes out).

It stores simple things: strings, numbers, and **lists**. Celery only cares about the lists, and uses them as queues:

```
RPUSH  →  put a ticket on the right end of the rail
BLPOP  →  take a ticket off the left end (and WAIT if the rail is empty)
```

That `B` in `BLPOP` means *blocking*. The worker asks Redis "give me a ticket", and if there are none, Redis just **doesn't answer** until one shows up. The worker sleeps instead of asking a thousand times a second. That's why an idle worker uses almost no CPU.

Redis is not a Python library you `pip install` and forget. It's a **separate program**, running on its own, listening on port **6379**. That's why we needed Docker.

### Celery — the cook (and the recipe book)

**Celery** is a Python library with two jobs:

1. In your Django process, it **writes tickets**: turns `send_email.delay(42)` into JSON and pushes it to Redis.
2. In the worker process, it **reads tickets**: pulls JSON off Redis, finds the matching Python function, and runs it.

Both sides are the same library, run in different modes.

### Celery Beat — the alarm clock

The worker cooks whatever tickets arrive. It has no idea what time it is.

**Beat** is a third process whose only job is to watch the clock and **write a ticket at the right time**. "Every day at 8am, clip a ticket saying `send_appointment_reminders`."

Beat never runs your code. It only puts tickets on the rail. The worker still does all the cooking.

```
Django view  ──┐
               ├──► Redis (rail) ──► Worker (cook) ──► your Python code
Beat clock   ──┘
```

---

## 3. Why Redis had to run in Docker

Redis was built for Linux. There is no official Windows version.

**Docker** solves this by running a tiny Linux system inside your Windows machine — a **container**. Think of it as a sealed lunchbox with Linux and Redis already inside; you never install either one on Windows.

```powershell
docker run -d -p 6379:6379 --name opd-redis redis
```

| Part | Meaning |
|---|---|
| `run` | build a container from an image and start it |
| `-d` | detached — run in the background, give my terminal back |
| `-p 6379:6379` | **port mapping**: `windowsPort:containerPort` |
| `--name opd-redis` | give it a name so I can restart it by name later |
| `redis` | the image to use (downloaded from Docker Hub the first time) |

**`-p` is the important one.** Without it, Redis runs happily inside its sealed box and nothing outside can talk to it. The flag drills a hole: anything hitting `localhost:6379` on Windows gets forwarded inside to Redis.

Check it's alive:

```powershell
docker exec -it opd-redis redis-cli ping
# → PONG
```

**Tomorrow you don't `run` again** — that would try to create a second container with the same name and fail. The container still exists, just stopped:

```powershell
docker start opd-redis
```

---

## 4. Wiring Celery into Django

### `backend/config/celery.py` (new file)

```python
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
```

Line by line:

**`os.environ.setdefault('DJANGO_SETTINGS_MODULE', ...)`**
The worker is its own process. It never runs `manage.py`, so nobody has told it where `settings.py` lives — it wouldn't know your database, your email password, anything. This line does what `manage.py` normally does. `setdefault` (not `=`) means "only if it isn't already set", so on Render a real environment variable wins.

**`app = Celery('config')`**
Creates the Celery application object. `'config'` is just a name stamped on messages.

**`config_from_object('django.conf:settings', namespace='CELERY')`**
"Read your settings out of Django's settings file, but only the ones starting with `CELERY_`." So `CELERY_BROKER_URL` in `settings.py` becomes Celery's internal `broker_url`. The namespace keeps Celery's ~100 option names from cluttering your Django settings.

**`app.autodiscover_tasks()`**
Walks every app in `INSTALLED_APPS` and imports `<app>/tasks.py` if it exists. This is why the file **must** be named `tasks.py` — that exact name is the convention it looks for.

### `backend/config/__init__.py` (was empty)

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

**Why this matters more than it looks.** `__init__.py` runs the instant Python imports the `config` package — and Django imports it at startup, always. So this guarantees the Celery app object exists *before* any of your app code loads.

Skip it and `@shared_task` has no Celery app to attach to. Your tasks silently never register. The worker starts, prints a clean banner, lists **zero tasks**, and nothing ever runs. No error anywhere.

### `settings.py`

```python
from celery.schedules import crontab   # at the top with the other imports

# ...at the bottom:
CELERY_BROKER_URL = config('CELERY_BROKER_URL')
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
```

**`config('CELERY_BROKER_URL')` with no default** = required (the Day 38 rule). Missing key → app refuses to boot. The URL lives in `.env` because prod Redis is a different host with a password:

```
CELERY_BROKER_URL=redis://localhost:6379/0
```

That trailing `/0` is a **database number**. One Redis server ships 16 numbered databases (0–15). Celery uses 0. Later you could put a cache on `/1` without the queues colliding.

**`CELERY_TASK_SERIALIZER = 'json'`** — tickets have to become text to travel through Redis. Old Celery defaulted to **pickle**, a Python format that *executes code* when unpacked. Anyone who could write to your Redis could run any command on your server. Modern Celery already defaults to json; setting it explicitly means a future upgrade can't quietly change it back.

**`CELERY_TIMEZONE = TIME_ZONE`** — reuses `'Asia/Kolkata'`. Critical for Beat: "8am" is meaningless until you say *whose* 8am.

---

## 5. Writing a task

`backend/apps/notifications/tasks.py`:

```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_notification_email(self, notification_id):
    """Mail an existing Notification row. Retries on SMTP failure."""
    notification = Notification.objects.get(id=notification_id)
    if not notification.recipient.email:
        return
    send_mail(
        subject=f'OPD - {Notification.Type(notification.notification_type).label}',
        message=notification.message,
        from_email=None,
        recipient_list=[notification.recipient.email],
        fail_silently=False,
    )
```

### `@shared_task`, not `@app.task`

`@app.task` needs you to import the Celery app into every tasks file, which makes your app code depend on `config`. `@shared_task` attaches to whichever Celery app is active — which exists because of that `__init__.py` line. Reusable-app convention.

### Pass the ID, never the object

**This is the single most important Celery rule.**

Your arguments get turned into JSON and pushed through Redis. A Django model instance is not JSON — it can't make the trip.

But there's a deeper reason. Even if you *could* ship the object, you'd be shipping a **photograph** of the row taken at the moment you called `.delay()`. The worker might open that photo ten seconds later, or ten minutes later after a retry. Meanwhile the real row changed.

```python
send_notification_email.delay(notification.id)   # ✅ pass the ID
send_notification_email.delay(notification)      # ❌ a stale photograph
```

The task refetches inside itself, so it always works with what's true **now**.

### The retry machine

| Argument | What it does |
|---|---|
| `bind=True` | makes `self` the first parameter — gives the task a handle on its own run |
| `autoretry_for=(Exception,)` | if the body raises, put the ticket **back on the rail** instead of failing |
| `retry_backoff=True` | wait 1s, then 2s, then 4s between attempts |
| `max_retries=3` | give up after 3 — no infinite loop hammering a dead server |
| `fail_silently=False` | `send_mail` **must** raise, because the exception is what triggers the retry |

**Why backoff exists:** without it, three retries fire in the same second and hit the same dead Gmail three times. Waiting longer each time gives the other side a chance to come back.

**Note the reversal from Day 38.** Back then `fail_silently=True` was correct, because a mail crash would have 500'd a booking that was already saved. Now that the send happens in a *different process*, crashing is not just safe — it's the mechanism. Same line, opposite value, because the surrounding architecture changed.

---

## 6. Calling it: `.delay()`

In `services.py`:

```python
if email:
    try:
        send_notification_email.delay(notification.id)
    except OperationalError:
        logger.exception('Could not queue email for notification %s', notification.id)
```

**`.delay(x)` does NOT run the function.** It:

1. turns `("send_notification_email", [42])` into JSON,
2. `RPUSH`es it onto a Redis list,
3. returns in about a millisecond.

Your view moves on immediately. Somewhere else, a worker wakes up and does the slow part.

### The new dependency, and the guard

Moving email out of the request bought something and cost something:

| | Day 38 (blocking) | Day 39 (queued) |
|---|---|---|
| Gmail down | email silently lost forever | queued, retried, delivered |
| **Redis down** | booking works fine | **booking crashes** |

That second row is a bad trade — the appointment matters, the email is a courtesy. Hence the `try/except`.

**`except OperationalError`, not bare `except`.** This catches exactly one thing: "can't reach the broker". A typo in your own code still crashes loudly, the way it should. A bare `except:` would hide real bugs forever.

**And this is not Day 38 all over again.** `fail_silently=True` swallowed *every* mail failure permanently. This swallows only the narrow window where Redis is unreachable, and the in-app notification still gets created either way — the patient sees it in the bell. Once a ticket reaches the rail, the retry machinery guarantees it gets cooked.

**`logger.exception`** logs the message *and* the full traceback. Only valid inside an `except` block. `logger.error` would give you the message with no stack trace.

---

## 7. Scheduled tasks — and the double-run problem

Beat runs on a timer. **It will fire twice at some point** — you restart it, a deploy overlaps, the clock adjusts. If "send tomorrow's reminders" has no memory of what it already sent, everyone gets mailed twice.

A task that's safe to run twice is called **idempotent**. Ours had to become one.

We added one field to `Appointment`:

```python
reminder_sent = models.BooleanField(default=False)
```

`default=False` is what lets it migrate cleanly — every existing row gets `False`, so old appointments become eligible rather than being skipped. No prompt for a one-off default.

> Could we have reused the `Notification` rows as the record instead? No — `Notification` has no ForeignKey to `Appointment`, only that plain `link` string from 18a. Matching on a URL string is fragile, and a patient with two appointments tomorrow is ambiguous. One boolean is cheaper and exact.

```python
@shared_task
def send_appointment_reminders():
    """Daily: remind patients about tomorrow's appointments."""
    from .services import notify

    tomorrow = timezone.localdate() + timedelta(days=1)
    appointments = Appointment.objects.filter(
        appointment_date=tomorrow,
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
        reminder_sent=False,
    ).select_related('patient', 'doctor')

    sent = 0
    for appt in appointments:
        notify(..., Notification.Type.REMINDER, email=True)
        appt.reminder_sent = True
        appt.save(update_fields=['reminder_sent'])
        sent += 1
    return sent
```

Four details worth stopping on:

**`from .services import notify` is INSIDE the function.**
This is a **circular import**. `services.py` imports `tasks.py` (for the email task). If `tasks.py` also imports `services.py` at the top, Python starts loading `tasks`, hits the import, starts loading `services`, which imports `tasks` — already half-loaded, `send_notification_email` not defined yet → `ImportError`.

Deferring the import to *call* time breaks the loop: by the time the task actually runs, both modules are fully loaded. Function-level imports are normally a smell; here they're the standard fix.

**`timezone.localdate()`, not `date.today()`.**
`USE_TZ=True` means the database stores UTC. At 02:00 in India, UTC is still *yesterday*. `date.today()` on a UTC server would compute the wrong "tomorrow" and mail the wrong patients. `localdate()` converts through `TIME_ZONE` first.

**`sent += 1`, not `return appointments.count()`.**
A QuerySet is **lazy** — it re-runs its query whenever you ask it something new. By the end of the loop every matched row has `reminder_sent=True`, so a fresh `.count()` matches **nothing** and returns `0` after successfully sending 50 emails. A plain counter records what actually happened.

**`update_fields=['reminder_sent']`** writes one column instead of all fifteen — so this save can't accidentally clobber a `status` another task just changed.

### The expiry task

```python
@shared_task
def expire_stale_appointments():
    """Daily: cancel PENDING appointments whose date has passed. Never touches CONFIRMED."""
    stale = Appointment.objects.filter(
        appointment_date__lt=timezone.localdate(),
        status=Appointment.Status.PENDING,
    )
    ...
```

`status=PENDING` **only**, and that's a rule, not an oversight (decided Day 35): **never auto-complete a CONFIRMED appointment.** Confirmed means reception vouched for it. A confirmed visit that nobody marked complete is a data-entry problem, not a cancellation.

When testing this, we deliberately created a **CONFIRMED row in the same date range** as a control. Anyone can write a query that cancels things; the requirement is that it cancels PENDING and *nothing else*. Without a control row, a filter bug that cancels everything passes silently.

---

## 8. The Beat schedule

```python
CELERY_BEAT_SCHEDULE = {
    'send-appointment-reminders': {
        'task': 'apps.notifications.tasks.send_appointment_reminders',
        'schedule': crontab(hour=8, minute=0),
    },
    'expire-stale-appointments': {
        'task': 'apps.notifications.tasks.expire_stale_appointments',
        'schedule': crontab(hour=0, minute=30),
    },
}
```

**The `'task'` value is a STRING, not the function.** Beat never imports your code. It writes a ticket with a *name* on it, and the worker looks that name up in its own registry.

That string must exactly match what the worker printed under `[tasks]` in its banner. Get it wrong and:

- Beat starts fine
- Beat logs `Scheduler: Sending due task` — it thinks it succeeded
- the **worker**, in a different terminal, logs `Received unregistered task` and throws the ticket away

Nothing validates that string until a message crosses the broker. Not `check`, not Beat, not your editor.

**`crontab(hour=8, minute=0)`** = 08:00 daily, in `CELERY_TIMEZONE`. Every field you *don't* specify means "every". Omit `minute` and you get 08:00, 08:01, 08:02… sixty times.

Expiry at 00:30 runs before reminders at 08:00, so a stale PENDING is cancelled before the day's reminder pass could mail about it.

**The dict key** (`'send-appointment-reminders'`) is just a human label for logs and Beat's state file. Misspelling it is harmless — but it shows up in every log line, so fix it anyway.

---

## 9. Running the whole thing

Four terminals, all with the venv active:

```powershell
# 1 — Redis (once per boot)
docker start opd-redis

# 2 — Django
python manage.py runserver

# 3 — the cook
celery -A config worker -l info --pool=solo

# 4 — the alarm clock
celery -A config beat -l info
```

### `--pool=solo` is mandatory on Windows

Celery's default `prefork` pool calls `os.fork()` to spawn child processes. **Windows has no `fork()`.**

Without the flag the worker starts, prints a perfect banner, accepts a task, and then hangs or dies deep inside a library you've never heard of — a genuinely confusing failure, because startup looks flawless.

`solo` runs tasks in the main thread, one at a time. Fine for development. On Render (Linux) you drop the flag and get real concurrency.

### The worker does NOT auto-reload

`runserver` watches your files and restarts itself. **The worker does not.** It imports `tasks.py` once at startup and holds it in memory forever.

Edit a task, and the worker keeps running the **old code**, silently, with no warning at all. You will debug a bug you already fixed.

> **Every time you touch `tasks.py` or `settings.py`: Ctrl+C the worker (and Beat) and start them again.**

---

## 10. Reading the logs

A successful chain looks like this:

```
[18:09:12] Task ...send_appointment_reminders[50972c06] received
[18:09:12] Task ...send_appointment_reminders[50972c06] succeeded in 0.058s: 1
[18:09:12] Task ...send_notification_email[ae007bd5] received
[18:09:18] Task ...send_notification_email[ae007bd5] succeeded in 5.15s: None
```

Three things to notice:

1. **The `: 1` at the end is your `return` value.** It shows in the log even though we have no results backend — the worker prints it, then discards it.
2. **A task queued another task.** `send_appointment_reminders` called `notify(email=True)`, which called `.delay()`, which clipped a *second* ticket to the rail.
3. **Look at the timings.** The reminder task finished in 58 milliseconds. The email took 5.15 seconds. They're separate.

That second point is the payoff at scale: 200 reminders means the reminder task returns in under a second having queued 200 **independent, individually-retryable** emails — instead of blocking for 15 minutes and losing everything if it dies at number 150.

### Suspiciously fast is a bug signal

Early on, our email task reported:

```
succeeded in 0.009726s: None
```

Nine milliseconds. A real SMTP handshake with Gmail takes **1–5 seconds**. That number meant no network happened at all — the task had returned early.

The cause was a one-line typo (section 11). The lesson: **on a task that talks to the outside world, the duration in the log is a correctness check.** Too fast means it didn't do the thing.

---

## 11. Gotchas (all of these actually happened)

### `return` merged with the next statement

```python
    if not notification.recipient.email:
        return send_mail(          # ← WRONG
            ...
        )
```

The `return` and `send_mail(` collapsed onto one line while tidying whitespace. The logic **inverted**: mail is now sent only to people who have *no* email address. Everyone else gets nothing.

Valid Python. `check` clean. Worker logs `succeeded`. Zero emails.

```python
        return          # ← bare, alone on its line
    send_mail(
```

### Misspelled model attribute + correct `update_fields`

```python
appt.reminder_send = True                      # ← missing 't'
appt.save(update_fields=['reminder_sent'])     # ← writes the real field, still False
```

Python does **not** complain when you assign an attribute that isn't a model field — it just sticks it on the instance in memory. Then `save()` writes the *actual* field, which nobody touched.

Result: the email sends, the flag never persists, and the next run mails the same people again. **Forever.** Exactly the bug the field was added to prevent, reintroduced by one missing letter. No exception, no log, task returns a happy count.

### Singular/plural namespace — three times in one day

```python
reverse('appointment:my_appointments')                  # ❌ app_name is 'appointments'
'task': 'apps.notification.tasks.send_...'              # ❌ app is 'notifications'
```

`NoReverseMatch` for the first, `Received unregistered task` for the second. Both invisible to `check`, both only fail at runtime, and the second one fails **in a different process** than the one that made the mistake.

### Test settings left commented in place

```python
'schedule': crontab(hour=0, minute=30),
# 'schedule': crontab(minute='*'),        # ← delete this
```

After testing, revert *and delete* the commented line. A dict with two `'schedule'` keys, one live and one commented, is exactly how an every-minute test schedule ships to production six months later.

### `Received unregistered task` ≠ missing import

The error message suggests you forgot to import something. Almost always it's a **name mismatch** between publisher and worker. The worker's `[tasks]` banner is the authoritative list — diff your string against it.

---

## 12. Testing without waiting for the clock

You cannot wait until 8am to find out if the reminder works. Two techniques:

**Call the task by hand** in `manage.py shell`:

```python
from apps.notifications.tasks import send_appointment_reminders
send_appointment_reminders.delay()
```

This tests **your code**, but not Beat.

**Then temporarily speed up the schedule** to test Beat itself:

```python
'schedule': crontab(minute='*'),   # every minute
```

Restart Beat, watch for one fire, then **put it back and restart Beat again**.

That second test is not optional — it's the only thing that validates the task-name strings, and it's exactly what caught our `apps.notification` typo. Everything else had passed.

**Always verify a DB write with `refresh_from_db()`:**

```python
a1.refresh_from_db()
a1.reminder_sent      # → True
```

Your in-memory `a1` still remembers `False` and will happily lie to you. `refresh_from_db()` re-reads the actual row.

---

## 13. What we deliberately skipped

| Skipped | Why | Add when |
|---|---|---|
| `CELERY_RESULT_BACKEND` | stores each task's return value in Redis. Emails and status flips are fire-and-forget | a web request needs a task's result |
| `django-celery-beat` | DB-backed schedules editable from the admin. New dependency + migrations | someone wants to change the times without a deploy |
| `transaction.atomic()` around notify | not yet needed at this size | a half-written notification actually bites |

---

## Revise (3 lines)

1. **Redis is a rail, Celery is a cook, Beat is an alarm clock** — three separate processes; `.delay()` clips a ticket and returns in a millisecond instead of waiting five seconds for Gmail.
2. **Pass IDs, never objects** (JSON can't carry a model, and a passed object is a stale photograph), and make scheduled tasks **idempotent** (`reminder_sent`) because Beat will fire twice one day.
3. **The worker never reloads and never validates task-name strings** — restart it after every edit, and test Beat with a temporary `crontab(minute='*')` because `check` cannot see a name typo that only fails in another process.
