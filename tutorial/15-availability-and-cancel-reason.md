# Step 15 — Doctor Availability + Cancel Reason

> **New branch `feature/availability-and-cancel-reason` → PR #6.** Two appointment-domain features: an optional **cancel reason**, and a **doctor availability** layer that validates bookings against the doctor's working hours (no slot-picking — the patient UX stays the same). Lab module is a separate later branch.
>
> Chunked: **15a** cancel reason · **15b** availability model · **15c** schedule setup + first-login gate · **15d** booking validation. This file grows per sub-step.

## The design decision (why validation, not slots)

The catalogue assumed a `TimeSlot` model with doctors creating bookable slots. We chose a lighter path:

- **Availability is a validation layer, not slots.** The doctor sets general working hours (e.g. 9–6, lunch 1–2). The patient still books with a plain date + time input — *unchanged*. On submit, the booking form checks the chosen time against the doctor's availability and rejects it with "Doctor not available" if it's outside hours / in a break / on an off day.
- **Why:** zero rework of the patient booking flow, no slot-management UI, and it's realistic. Slot-picking is heavier and the frontend gets rebuilt in Step 20 anyway.

**Deferred to Step 20 (frontend):** coloring the patient's date picker green/red for available/unavailable days. The native `<input type=date>` can't style individual dates — that needs a custom JS calendar. The availability *rule* built here is what makes that possible later; it gets painted in the frontend step.

---

# Step 15a — Cancel Reason

## What we did here

1. Added an optional `cancel_reason` field to `Appointment` (migration 0005).
2. `cancel_appointment` captures the reason from the POST.
3. Staff cancel forms (doctor + reception) gained an optional reason input; the reason is shown to **all** roles on cancelled rows.

## Half 1 — The field

```python
# models.py — on Appointment, after notes
cancel_reason = models.TextField(blank=True)
```

`blank=True` = optional (the "optional but recommended" ask). No `null=True` — empty string is the no-reason value, same convention as `notes`. Adding a field = a migration (`0006`... here `0005_appointment_cancel_reason`).

## Half 2 — Capturing it

```python
# cancel_appointment view
if appointment.status != Appointment.Status.CANCELLED:
    appointment.status = Appointment.Status.CANCELLED
    appointment.cancel_reason = request.POST.get('cancel_reason', '')
    appointment.save()
```

`request.POST.get('cancel_reason', '')` — reads the input if the form sent one, empty string otherwise. Patient cancel forms don't include the input → no reason, no error. It's set only inside the cancel branch, so re-cancelling never wipes an existing reason.

## Half 3 — The templates

**Reason input** — added to each *staff* cancel form (doctor_today, doctor_history, doctor_upcoming, appointment_list), before the button:

```django
<input type="text" name="cancel_reason" placeholder="Reason (optional)" style="width:130px">
```

Patient's `my_appointments` cancel stays button-only — a patient cancelling their own appointment doesn't justify it.

**Showing the reason** — inside the Status cell, for cancelled rows, in every list (reception, doctor, patient):

```django
<td>{{ appt.get_status_display }}{% if appt.status == 'CANCELLED' and appt.cancel_reason %}<br><small>{{ appt.cancel_reason }}</small>{% endif %}</td>
```

**Gotcha caught:** the reason block was first placed *between* two `<td>`s — loose content inside a `<tr>`, outside any cell. `manage.py check` doesn't validate HTML structure, so it passed; the browser renders it in the wrong place. Fix: keep the `{% if %}` **inside** the status `<td>`, before `</td>`.

## Commits

Two — backend then frontend:

```
feat(appointments): add optional cancel_reason field + capture on cancel   # models + migration + view
feat(appointments): reason input on staff cancel forms + show reason to all roles   # templates
```

---

## Revise (15a)

1. **`cancel_reason = TextField(blank=True)`** — optional field, migration, empty-string default like `notes`.
2. **View reads `request.POST.get('cancel_reason', '')`** inside the cancel branch — agnostic to which forms send it; patient forms simply don't.
3. **Inline in the Status cell** — reason shown to all roles on cancelled rows; keep the `{% if %}` inside the `<td>` (loose HTML between cells renders wrong, and `check` won't catch it).

---

**Next (15b):** `DoctorAvailability` model — `recurrence` (EVERYDAY / WEEKDAYS / MON_SAT / DATE) + `date` (for the DATE case) + `start_time` + `end_time` + `breaks` (JSONField, one or many). Then 15c setup + gate, 15d booking validation.

---

# Step 15b — The `DoctorAvailability` Model

## What we did here

1. New `DoctorAvailability` model — recurrence presets, working hours, breaks as JSON. Migration 0006.
2. Registered in admin, created a test row.

## Half 1 — `JSONField` (the one new concept)

```python
breaks = models.JSONField(default=list, blank=True)
# holds: [{"start": "13:00", "end": "14:00"}, {"start": "16:00", "end": "16:30"}]
```

**`JSONField`** stores a Python list/dict as JSON text in a single DB column. One or *many* breaks fit in one field — no separate `Break` model, no FK, no formset.

**`default=list`** — the *callable* `list`, never `[]`. A literal `[]` would be one shared list across every instance (Python's mutable-default bug); the callable makes a fresh list per row. Django refuses `[]` outright.

Trade-off to know: JSON contents are invisible to SQL — you can't easily `filter(breaks__contains=...)` across engines. Fine here: breaks are only ever read per-doctor and checked in Python. If breaks ever need their own queries, that's when a `Break` model earns its place.

## Half 2 — The model

```python
class DoctorAvailability(models.Model):
    class Recurrence(models.TextChoices):
        EVERYDAY = 'EVERYDAY', 'Every day'
        WEEKDAYS = 'WEEKDAYS', 'Weekdays (Mon-Fri)'
        MON_SAT = 'MON_SAT', 'Mon to Sat'
        DATE = 'DATE', 'Specific date'

    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='availabilities')
    recurrence = models.CharField(max_length=20, choices=Recurrence.choices,
                                  default=Recurrence.EVERYDAY)
    date = models.DateField(null=True, blank=True)     # only for DATE
    start_time = models.TimeField()
    end_time = models.TimeField()
    breaks = models.JSONField(default=list, blank=True)
```

- `CASCADE` (not PROTECT like appointments): availability is meaningless without its doctor; no history worth preserving.
- `date` nullable — filled only when `recurrence == DATE` (a one-day override).
- Recurrence weekday rule (used in 15d): `EVERYDAY` all days · `WEEKDAYS` Mon–Fri (`weekday()` 0–4) · `MON_SAT` 0–5 · `DATE` exact date match.

## Gotchas (Day 25 — the typo hunt)

- **`DoctorAvailablility`** (extra "li") in the class name — spread into admin imports AND the migration filename before being caught. Model-name typos propagate everywhere; fix = rollback migration → delete file → rename → remake. Migration names derive from the model name — a misspelled migration filename is the tell.
- **`related_name='availabilites'`** (missing "i") — silent until 15c's `user.availabilities` → `AttributeError`. Same rollback dance.
- **Admin JSON needs double quotes** — `[{'start': '12:00'}]` fails "Enter a valid JSON"; JSON is not Python — `[{"start": "12:00"}]`.
- Admin's TimeField widget shows odd shortcuts (Now/Midnight/Noon) — that's stock admin, you can type any time; the doctor-facing form uses the native `type="time"` picker.

---

# Step 15c — Schedule Setup + First-Login Gate

## What we did here

1. `DoctorScheduleForm` + `doctor_schedule` view + template with **unlimited breaks** (tiny vanilla JS).
2. First-login gate: doctor without a recurring schedule → forced to setup.
3. Nav link "My Schedule".

## Half 1 — One recurring rule per doctor

A doctor has ONE recurring schedule (EVERYDAY/WEEKDAYS/MON_SAT) plus any number of DATE overrides. Saving a recurring rule first deletes the old recurring one:

```python
if availability.recurrence != DoctorAvailability.Recurrence.DATE:
    DoctorAvailability.objects.filter(doctor=request.user).exclude(
        recurrence=DoctorAvailability.Recurrence.DATE
    ).delete()
availability.save()
```

Without this, EVERYDAY 9–6 and WEEKDAYS 10–4 would both exist — two conflicting truths. Delete-then-create keeps exactly one.

## Half 2 — Unlimited breaks: `getlist()` + 8 lines of JS

Breaks aren't form fields at all. The template has one break row whose inputs share names:

```html
<div id="breaks">
    <p class="break-row">
        <input type="time" name="break_start"> to <input type="time" name="break_end">
    </p>
</div>
<button type="button" onclick="addBreak()">+ Add break</button>

<script>
function addBreak() {
    const row = document.querySelector('.break-row');
    const copy = row.cloneNode(true);
    copy.querySelectorAll('input').forEach(i => i.value = '');
    document.getElementById('breaks').appendChild(copy);
}
</script>
```

Every added row repeats the same input names. The view collects them all:

```python
break_starts = request.POST.getlist('break_start')
break_ends = request.POST.getlist('break_end')
breaks = []
for bs, be in zip(break_starts, break_ends):
    if bs and be:
        breaks.append({'start': bs, 'end': be})
availability.breaks = breaks
```

**`getlist()`** — when multiple inputs share one name, `request.POST.get()` returns only the last; `getlist()` returns all, in order. `zip` pairs starts with ends; empty rows skip. HTML time inputs already submit `HH:MM` strings — straight into the JSON, no conversion.

This is the pattern for "repeat a row N times" without formsets: shared names + getlist + a cloneNode button.

## Half 3 — The gate

```python
# accounts/views.py — login_view DOCTOR branch
if user.role == 'DOCTOR':
    if not user.availabilities.exclude(recurrence='DATE').exists():
        return redirect('appointments:doctor_schedule')
    return redirect('appointments:doctor_today')
```

No recurring rule → setup page. DATE-only overrides don't count as "has a schedule." One `exists()` query — the reverse accessor `availabilities` named in 15b pays off again.

## Gotchas (Day 25, part 2)

- **Leftover form fields** — the earlier one-break design left `break_start`/`break_end` as form fields; with getlist they'd render a duplicate pair. Deleted. Add-without-delete strikes again — reread the whole class after a design change.
- **`form.erros` / `forms.erros`** in the template error block — renders nothing, silently. The plural-drop family.
- **`recureence`** in the gate's `.exclude()` — `FieldError` at first doctor login. Field-name strings in queries are unchecked until runtime.
- **Return-outside-if (NEW pattern)** — the gate's `return redirect('doctor_today')` was indented at the wrong level: outside the DOCTOR check. Effect: *every* role got doctor_today and the RECEPTION/profile lines below became dead code. `check` can't see it — the code is valid Python. Watch indentation around multi-branch returns.
- `doctor/schedule` missing trailing slash — works via `{% url %}` (generates the same slash-less path) but inconsistent; fixed per the `token/refresh` lesson.

---

## Revise (15b + 15c)

1. **`DoctorAvailability`** = recurrence preset + hours + `breaks` JSONField (`default=list` — callable, never `[]`). One recurring rule per doctor + DATE overrides; delete-then-create keeps the recurring rule unique.
2. **Unlimited repeat-rows without formsets**: inputs share a name, tiny cloneNode JS adds rows, `request.POST.getlist()` collects them all, zip + skip-empties → JSON.
3. **Gate at login**: `user.availabilities.exclude(recurrence='DATE').exists()` — no schedule, no dashboard. Indentation of returns in multi-branch code is a silent killer — `check` passes, wrong role lands wrong.

---

**Next (15d):** booking validation — both booking forms' `clean()` check the doctor's availability for the chosen date (DATE override wins, else recurring rule): weekday allowed + time inside [start, end] + not inside any break → else "Doctor not available". Plus cheap add: show the doctor's hours as text on the booking page. Then PR #6.