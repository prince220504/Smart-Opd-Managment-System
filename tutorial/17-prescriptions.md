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
