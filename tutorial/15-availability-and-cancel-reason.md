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