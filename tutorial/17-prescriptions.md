# Step 17 — `prescriptions` app

The doctor writes a prescription after a completed visit; the patient reads it back.
Parent-step file — grows one section per sub-step (17a, 17b, …).

**New concept this step: `JSONField`** — storing a *list of dicts* in one column instead of a child table.

---

## 17a — the app + the `Prescription` model

### What
A new Django app `prescriptions` with a single `Prescription` model (one row per completed appointment),
plus admin registration and the first migration.

### Why
One feature = one app (project convention). A prescription belongs to exactly one appointment,
so it hangs off `Appointment` as a **OneToOne** child — the same shape as `LabResult` → `LabTest` from Step 16.

### How

**1. Create the app** (scaffolding — run from `backend/`):
```bash
python manage.py startapp prescriptions apps/prescriptions
```
Then fix `apps/prescriptions/apps.py`:
```python
name = 'apps.prescriptions'      # dotted path so Django finds it under apps/
```

**2. Register** in `config/settings.py` → `INSTALLED_APPS`:
```python
    'apps.prescriptions',
```

**3. The model** — `apps/prescriptions/models.py`:
```python
from django.db import models
from apps.appointments.models import Appointment

class Prescription(models.Model):
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='prescription',
    )
    diagnosis = models.CharField(max_length=255)
    medicines = models.JSONField(default=list)
    advice = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prescription for {self.appointment.patient.username}"
```

**4. Admin** — `apps/prescriptions/admin.py`:
```python
from django.contrib import admin
from .models import Prescription

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'diagnosis', 'created_at')
    search_fields = ('appointment__patient__username', 'diagnosis')
```

**5. Migrate**:
```bash
python manage.py makemigrations prescriptions
python manage.py migrate
```
→ `prescriptions/0001_initial.py` created + applied.

### The three ideas worth keeping

- **`OneToOneField` + `CASCADE`** — one appointment → at most one prescription. Reverse access is
  `appointment.prescription`. CASCADE = delete the appointment, its prescription goes too (a script has
  no meaning without its visit). Same reasoning as `LabResult.test` in Step 16.

- **`JSONField(default=list)`** *(the new concept)* — one column holds a **Python list of dicts**:
  ```python
  [{"name": "Paracetamol", "dosage": "500mg", "frequency": "twice daily", "duration": "5 days"}, ...]
  ```
  Django serializes it to JSON on the way into the DB and hands you back a real list in Python.
  `default=list` is the **function** (no `()`) — each new row gets its own fresh `[]`. Never write
  `default=[]`: that shares one mutable list across every row (the classic mutable-default bug).
  - *Why JSON, not a `Medicine` table?* The medicine lines are only ever read as a group, together with
    their prescription — no one queries "every row of Paracetamol", so there is no join to justify a table.
    JSON is the lazy-correct call here. Promote to a table only if we ever need to query across medicines.

- **No COMPLETED-gate in the model** — "only writable on a COMPLETED appointment" is a *business rule*,
  enforced in the doctor write-view (17b), not the schema. The model stays dumb; the view guards.

### Gotchas
- `apps.py` → `name = 'apps.prescriptions'` (not bare `'prescriptions'`), or Django can't import the app.
- `default=list`, never `default=[]`.
- FK import path is `apps.appointments.models` — the migration should show `to='appointments.appointment'`.

### Revise (3-line recall)
- `Prescription` = OneToOne child of `Appointment` (CASCADE), reached as `appointment.prescription`.
- `medicines = JSONField(default=list)` stores the medicine lines as a list-of-dicts in one column — no child table.
- COMPLETED-only is a view rule (17b), not a model constraint.

---

## 17b — the doctor write page

### What
Doctor opens a COMPLETED appointment, fills diagnosis + advice + a dynamic list of medicine rows,
saves → one `Prescription`. Same page edits an existing one.

### Why
Prescriptions is its own app (like `lab`), so the write view/form/urls live in `apps/prescriptions/`.
The "only on COMPLETED" rule from 17a gets enforced here, in the view — not the model.

### How

**Form** — `apps/prescriptions/forms.py` (only the flat text fields):
```python
from django import forms
from .models import Prescription

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['diagnosis', 'advice']
```
`appointment` is set from the URL; `medicines` is built from repeated inputs, so neither is a form field.

**View** — `apps/prescriptions/views.py`:
```python
@login_required
def write_prescription(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        doctor=request.user,
        status=Appointment.Status.COMPLETED,
    )
    existing = getattr(appointment, 'prescription', None)

    if request.method == 'POST':
        form = PrescriptionForm(request.POST, instance=existing)
        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.appointment = appointment
            names = request.POST.getlist('med_name')
            dosages = request.POST.getlist('med_dosage')
            frequencies = request.POST.getlist('med_frequency')
            durations = request.POST.getlist('med_duration')
            medicines = []
            for name, dosage, frequency, duration in zip(names, dosages, frequencies, durations):
                if name:
                    medicines.append({'name': name, 'dosage': dosage,
                                      'frequency': frequency, 'duration': duration})
            prescription.medicines = medicines
            prescription.save()
            return redirect('appointments:doctor_records')
    else:
        form = PrescriptionForm(instance=existing)
    ...
```

**URLs** — `apps/prescriptions/urls.py` (`app_name = 'prescriptions'`, route `write/<int:appointment_id>/`
name `write`) + `config/urls.py`: `path('prescriptions/', include('apps.prescriptions.urls'))`.

**Button** — on `doctor_records.html`, a new `{% elif appt.status == 'COMPLETED' %}` branch links to
`prescriptions:write`; label flips on `{% if appt.prescription %}` (Write vs View/Edit).

**Template** — `frontend/templates/prescriptions/write.html` = the form + a `#medicines` box of `.med-row`s
(four `<input>`s each: name/dosage/frequency/duration) + a `+ Add medicine` button running the same
cloneNode JS as schedule breaks.

### The ideas worth keeping

- **The scoped lookup IS the gate.** `doctor=request.user, status=COMPLETED` in `get_object_or_404`:
  another doctor's appointment → 404, a not-yet-COMPLETED one → 404. This is *why* the model carries no
  COMPLETED constraint — the write path enforces it. Same "lookup = authorization" trick as `request_test`.

- **`instance=getattr(appointment, 'prescription', None)` = create-or-update.** The OneToOne trap from 16c:
  `appointment.prescription` raises `RelatedObjectDoesNotExist` when none exists, but that subclasses
  `AttributeError`, so `getattr(..., None)` returns `None` → the form creates; if one exists → it edits.
  No second-write `IntegrityError`.

- **`getlist` + `zip` + skip-empty** — four parallel lists (name/dosage/frequency/duration), zipped
  row-by-row, `if name:` drops blank rows → `medicines` JSON. Identical shape to the schedule-breaks
  `getlist` from 15c. The template's `cloneNode` "+ Add medicine" is the client half of the same pattern.

### Gotchas
- **`document.getElementById` — lowercase `d`.** Typed `getElementByID` → JS is case-sensitive →
  `TypeError: ... is not a function`; the clone is built but never appended, so "+ Add medicine" silently
  does nothing. (Caught on Prince's test — the row was cloned in memory but the append line threw.)
- `{% if appt.prescription %}` in a template safely reads empty when no prescription exists (Django swallows
  the reverse-OneToOne miss, same as lab notes in 16d).

### Revise (3-line recall)
- Write view lives in the prescriptions app; `get_object_or_404(..., doctor=me, status=COMPLETED)` = auth + COMPLETED-gate in one query.
- `instance=getattr(appointment, 'prescription', None)` makes one view both create and edit (OneToOne, no IntegrityError).
- Medicine rows: `getlist` four parallel lists + `zip` + `if name:` → JSON; `cloneNode` adds rows client-side.

---

## 17c — patient view page + doctor read-back + column split (Day 33)

**Goal:** the patient can finally *read* a prescription; the doctor's records page stops being a
one-column pile of unrelated buttons.

### What we built

**View** — `apps/prescriptions/views.py`, `view_prescription`. The IDOR guard is the lookup again — but
this time the scope spans the FK:
```python
prescription = get_object_or_404(
    Prescription,
    appointment__id=appointment_id,
    appointment__patient=request.user,
)
```
`appointment__patient` = a **field lookup that crosses the FK** ("the patient of the appointment this
prescription belongs to"). Someone else's `appointment_id` → filter matches nothing → 404. Fetch + auth in
one query, no separate `if` check.

**Route** — `view/<int:appointment_id>/` name `view`.

**Template** — `frontend/templates/prescriptions/view.html`: read-only. Loops `prescription.medicines`
(the **JSONField** — a plain list of dicts, no join) into a table; diagnosis + advice as text.

**Link** — on `my_appointments.html`, a `{% elif appt.status == 'COMPLETED' and appt.prescription %}`
branch links to `prescriptions:view`.

**Doctor read-back — nothing to build.** The 17b doctor_records button already links to `prescriptions:write`,
which loads the existing prescription into the form. Read = the same page. No separate doctor view page.

### Column split (Prince's UX call)

Both doctor pages had one **Action** cell holding lifecycle buttons + Request Test + the test list + the
prescription button — messy. Split by concern into three columns on `doctor_records.html` **and**
`doctor_today.html`:
- **Action** = lifecycle only (Accept / Complete / No-show / Cancel).
- **Tests** = Request form (CONFIRMED only) + the existing-tests list.
- **Prescription** = the Write / View-Edit button (COMPLETED only).

`doctor_today` gained a Prescription column it never had (a today appointment can be COMPLETED).

### The idea worth keeping — kill the reverse-OneToOne N+1

`{% if appt.prescription %}` reads a **reverse OneToOne** → one extra query per row. Django *can* join it,
so add it to `select_related`:
```python
.select_related('doctor', 'prescription')   # my_appointments
.select_related('patient', 'prescription')  # doctor_today
```
One JOIN instead of one-query-per-row. (Reverse OneToOne = select_related; reverse FK one→many = prefetch,
like `lab_tests`.)

### Design decisions
- **Request Test stays on CONFIRMED, not COMPLETED.** The doctor orders tests *live during the consult*
  (CONFIRMED), then marks COMPLETED. Moving it to COMPLETED would force finish-then-reopen. It's optional —
  available, never forced.

### Revise (3-line recall)
- Patient view: `get_object_or_404(Prescription, appointment__id=..., appointment__patient=request.user)` — cross-FK lookup = IDOR guard.
- Doctor read-back reuses the write page (loads existing); no separate view.
- Reverse OneToOne (`appt.prescription`) → `select_related` to kill the per-row N+1; reverse FK stays `prefetch_related`.

---

## 17d — prescription PDF (Day 34)

**Decision: no ReportLab.** Unlike lab 16d (which *cut* its PDF because the tech's raw upload
carried the real content), a prescription's content **is** generated here — but the HTML we already
render *is* the document. So skip the library, the view, the route, the hand-drawn layout.

**`window.print()`** — 1 line. The browser's own print dialog has "Save as PDF" as a destination,
so the patient gets a real PDF with **zero server code**.

**`@media print { … }`** — CSS that applies only when printing. The screen page has a nav bar, footer,
a Back link, the print button itself — none belong on a printed prescription. Mark them `.no-print`
(plus `header, footer`) and hide them in the print block.

```django
<style>
    @media print { header, footer, .no-print { display: none; } }
</style>
...
<button type="button" onclick="window.print()">Print / Save as PDF</button>
```

**What physically happens:** click → `window.print()` fires → browser re-renders applying `@media print`
(nav/footer/button gone) → patient picks "Save as PDF" → file in Downloads. No round-trip to Django.

### Default PDF filename = the page `<title>`

The browser suggests the save filename from `document.title`. Make it useful per-prescription:
```django
{% block title %}Prescription -{{ prescription.appointment.patient.username }}-{{ prescription.appointment.appointment_date|date:"Y-m-d" }}{% endblock %}
```
→ suggests `Prescription -rahul-2026-07-24.pdf`. `|date:"Y-m-d"` keeps it clean (no spaces/slashes).
Browser only *suggests* — user can still rename. That's a browser limit, not fixable.

### Also fixed the 17c advice gap
The patient view never rendered `advice` (model had it, form saved it, template skipped it). Added:
```django
{% if prescription.advice %}
    <h3>Advice</h3>
    <p>{{ prescription.advice }}</p>
{% endif %}
```

### Bugs (silent typos, all template)
- `{{ prescrition.advice }}` — missing the `p` in `prescription`. Undefined var → empty string, no error.
  The `{% if %}` above it was spelled right, so the heading showed but the text was blank.
- `prescription.appointment_date` in the title — dropped the `.appointment` hop (date lives on the
  appointment, not the prescription). Undefined → `|date` had nothing → empty filename segment.

### Revise (3-line recall)
- Generated content → `window.print()` + `@media print`, not ReportLab. One template, no server code.
- Default PDF filename comes from `<title>` — set it per-record; browser only suggests.
- Missing-hop / misspelled var in a template = silent empty render, no error. Sweep them.

**Step 17 closed.**
