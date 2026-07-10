# Step 13e — Appointment Lifecycle + Doctor Time-Split Views

> **First step on a fresh branch after Step 13 merged.** Step 13 (PR #3) gave every role its booking tools, but the lifecycle dead-ended at CONFIRMED and the doctor could only see *today*. 13e closes the lifecycle (`COMPLETED`, `NO_SHOW`) and splits the doctor's calendar into history and upcoming. Branch `feature/appointments-lifecycle` → PR #4.

## What we did here

**13e-i — lifecycle completion:**
1. Added `COMPLETED` and `NO_SHOW` to `Appointment.Status` — two migrations.
2. `complete_appointment` + `no_show_appointment` views — both `CONFIRMED → terminal`, mirror of confirm.
3. Terminal-state-aware action buttons across all three appointment tables.

**13e-ii — doctor time-split:**
4. `doctor_history` (past + today) and `doctor_upcoming` (future) views via `__lte` / `__gt` lookups.
5. Two templates + doctor nav links.

---

## Half 1 — Adding enum values needs a migration

```python
class Status(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    COMPLETED = 'COMPLETED', 'Completed'
    NO_SHOW = 'NO_SHOW', 'No Show'
    CANCELLED = 'CANCELLED', 'Cancelled'
```

`choices` is part of the field definition Django tracks. Adding a value generates an `AlterField` migration (`0002`, then `0003` when NO_SHOW landed mid-session). **The SQLite column doesn't change** — still `varchar(20)` — but Django records the choices change so its migration state matches the model. Skip it and `makemigrations --check` complains "model changed".

> Why it matters: any edit to `choices=` needs a migration, even when the database column looks identical. It's state tracking, not schema surgery.

---

## Half 2 — The completed lifecycle

```
PENDING ──confirm──▶ CONFIRMED ──complete──▶ COMPLETED   (terminal)
   │                     ├───────no-show───▶ NO_SHOW     (terminal)
   └───────cancel────────┴─────────────────▶ CANCELLED   (terminal)
```

Three terminal states, each with a distinct meaning:

| State | Means |
|-------|-------|
| `COMPLETED` | Patient came, visit happened |
| `NO_SHOW` | Appointment was confirmed, patient never arrived |
| `CANCELLED` | Someone actively cancelled before the visit |

`NO_SHOW` exists so `COMPLETED` stays honest — without it, staff would either mark no-shows "completed" (a lie: says a visit happened) or "cancelled" (also a lie: nobody cancelled). Every status now answers "what actually happened" truthfully.

**Why no auto-transitions (yet):** the obvious next idea — "PENDING past its slot auto-cancels, CONFIRMED past its slot auto-completes" — needs a clock-driven background job, which is Celery Beat (Step 16). And the second half is wrong anyway: *confirmed ≠ visited*. Auto-completing a no-show fabricates a visit. The plan logged for Step 16: auto-expire stale PENDING only; humans mark CONFIRMED rows Complete or No-show manually — exactly the buttons 13e builds.

---

## Half 3 — The transition views (one skeleton, three transitions)

```python
@login_required
@require_POST
def complete_appointment(request, appointment_id):
    if request.user.role == 'RECEPTION':
        appointment = get_object_or_404(Appointment, id=appointment_id)
    else:
        appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)

    if appointment.status == Appointment.Status.CONFIRMED:
        appointment.status = Appointment.Status.COMPLETED
        appointment.save()

    return _redirect_after_action(request)
```

`no_show_appointment` is identical except the target status. Compare the family:

| View | From-state guard | Target |
|------|-----------------|--------|
| `confirm_appointment` | `== PENDING` | CONFIRMED |
| `complete_appointment` | `== CONFIRMED` | COMPLETED |
| `no_show_appointment` | `== CONFIRMED` | NO_SHOW |
| `cancel_appointment` | `!= CANCELLED`* | CANCELLED |

*Cancel's guard predates the new terminal states — the templates now hide Cancel on terminal rows, so the loose guard never fires on them in practice.

Same authorization split as 13d: reception any row, doctor own rows (`doctor=request.user`), patient blocked for free — their `doctor=me` lookup matches nothing → 404.

> Why it matters: a status machine = allowed transitions, each one a small guarded POST view. Adding a state costs one enum value + one view + one button. Nothing else moves.

---

## Half 4 — Terminal-state-aware buttons

One `if/elif/else` per action cell, driven by status:

| Row status | Buttons shown |
|-----------|---------------|
| PENDING | Accept + Cancel |
| CONFIRMED | Complete + No-show + Cancel |
| COMPLETED / NO_SHOW / CANCELLED | — (dash) |

Applied to `doctor_today.html`, `appointment_list.html`, and — **user-caught bug** — `my_appointments.html`, whose patient Cancel still tested `!= 'CANCELLED'` and so kept offering Cancel on completed/no-show rows. Fixed to `== 'PENDING' or == 'CONFIRMED'`.

Button visibility is UX; the view's from-state guard is the real gate. A forged POST to `/appointments/complete/<id>/` on a PENDING row hits `== CONFIRMED`, fails the guard, changes nothing.

**One deliberate divergence:** `doctor_upcoming.html` shows CONFIRMED rows with **Cancel only** — no Complete/No-show. The visit hasn't happened yet; marking a future appointment completed would be false. History is where those buttons live, because history (past + today) is where visits have actually occurred.

---

## Half 5 — `__lte` / `__gt` field lookups (the time split)

You've used `filter(appointment_date=today)` since 13c — that's the implicit `__exact` lookup. Lookups are suffixes after a double underscore that become SQL comparison operators:

```python
.filter(appointment_date__lte=today)   # WHERE appointment_date <= today   → history
.filter(appointment_date__gt=today)    # WHERE appointment_date >  today   → upcoming
```

| Lookup | SQL | Reads as |
|--------|-----|----------|
| `__lt` | `<` | before |
| `__lte` | `<=` | before or on |
| `__gt` | `>` | after |
| `__gte` | `>=` | on or after |

`<= today` and `> today` **partition** the calendar — every appointment lands in exactly one of history/upcoming, no overlap, no gap. Today's rows land in history (that's where the Complete/No-show marking happens) *and* stay on the dedicated today page.

Same double-underscore syntax as the FK traversal you met in admin (`patient__username`). Django disambiguates by what follows the underscores: a field name = traversal, a known operator = lookup.

The two views:

```python
@login_required
def doctor_history(request):
    today = date.today()
    appointments = (
        request.user.doctor_appointments
        .filter(appointment_date__lte=today)
        .select_related('patient')
    )
    return render(request, 'appointments/doctor_history.html', {'appointments': appointments})


@login_required
def doctor_upcoming(request):
    today = date.today()
    appointments = (
        request.user.doctor_appointments
        .filter(appointment_date__gt=today)
        .select_related('patient')
        .order_by('appointment_date', 'time_slot')
    )
    return render(request, 'appointments/doctor_upcoming.html', {'appointments': appointments})
```

Ordering detail: history keeps the model's `Meta.ordering` (newest first — most recent visit on top). Upcoming overrides with `order_by('appointment_date', 'time_slot')` — soonest first, because a doctor scanning the future wants tomorrow at the top, not next month.

> Why it matters: every date-range feature ahead — reports, Celery's "tomorrow's appointments" reminder (Step 16), DRF date filters (Step 14) — is these four suffixes.

---

## Gotchas (Days 18–19)

All silent at `manage.py check`; all found by file-scan before browser testing:

| Typo | Where | Failure |
|------|-------|---------|
| `'appointment:complete'` / `'appointment:no_show'` / 3× more singular namespaces | doctor_today.html, doctor_history.html | `NoReverseMatch` at render |
| `{% csrf token %}` (missing underscore) | appointment_list.html | 403 on that POST |
| `'appiontments'` / `'appintments'` context-dict keys | views.py | **Template loops a variable that doesn't exist → page permanently, silently empty.** New pattern for the grep list: check context keys, not just template code |
| `<form action="post" action="{% url ... %}">` | doctor_upcoming.html | Duplicate attribute — browser keeps the *first* `action`, so the form GETs a URL literally named `post` → 404. Should be `method="post"`. New pattern: eyeball form tags for method/action swap |
| Missing No-show button | doctor_history.html CONFIRMED branch | Feature silently absent — add-without-checking-the-spec |

Pre-commit grep list, updated: namespace singular/plural · `{% csrf_token %}` underscore · enum-vs-field casing · `' %}`→`%'}` scrambles · plural drops · add-without-delete · **context-dict keys** · **`method=`/`action=` in form tags**.

---

## Where this plugs in next

| Feature | Step | Uses |
|---------|------|------|
| Double-booking prevention | 14 | `UniqueConstraint(doctor, appointment_date, time_slot, condition=~Q(status='CANCELLED'))` + form ValidationError — logged Day 19 |
| Auto-expire stale PENDING | 16 | Celery Beat + `filter(status='PENDING', appointment_date__lt=today)` |
| 24-hour reminder | 16 | `filter(status='CONFIRMED', appointment_date=tomorrow)` — the `__exact` cousin of today's lookups |
| Visit statistics (completed vs no-show rates) | 15+ | The honest terminal states make the numbers meaningful |

---

## Revise (3-line summary)

1. **Lifecycle closed.** `PENDING → CONFIRMED → {COMPLETED | NO_SHOW}`, anything non-terminal can cancel. Two `AlterField` migrations (choices changes track state even when the column doesn't move). Each transition = one guarded POST view; three terminal states that tell the truth about what happened.
2. **Buttons follow state.** PENDING: Accept+Cancel · CONFIRMED: Complete+No-show+Cancel · terminal: dash. Upcoming hides Complete/No-show on future CONFIRMED rows — you can't complete a visit that hasn't happened. View guards are the real enforcement; buttons are UX.
3. **`__lte` / `__gt` partition the calendar.** History = `appointment_date__lte=today` (newest first), Upcoming = `__gt=today` (soonest first). Same double-underscore syntax as FK traversal; Django tells them apart by whether the suffix is a field or an operator.

---

**Next:** PR #4 merges this branch. Then Step 14 — DRF layer + the double-booking `UniqueConstraint`.
