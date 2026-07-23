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
