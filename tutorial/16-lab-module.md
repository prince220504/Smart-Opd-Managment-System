# Step 16 — Lab Module

> **Branch `feature/lab-module` → PR #7.** The lab technician's world: doctors request tests on confirmed appointments, the lab works a queue, uploads result files, and the system generates branded PDF reports. Chunked: **16a** models + media · **16b** doctor request + lab queue · **16c** upload + status flow · **16d** ReportLab PDF. This file grows per sub-step.

# Step 16a — Models + Media Serving

## What we did here

1. Scaffolded the `lab` app (same `apps.py` dotted-path dance as every app).
2. `LabTest` + `LabResult` models — the first `OneToOneField` and first `FileField` in the project. Migration `0001`.
3. Admin for both + media serving in dev.

---

## Half 1 — `OneToOneField` (one result per test, enforced by schema)

```python
test = models.OneToOneField(LabTest, on_delete=models.CASCADE, related_name='result')
```

**`OneToOneField`** = a ForeignKey with a UNIQUE constraint: exactly one `LabResult` may point at a given `LabTest`. A second result for the same test → `IntegrityError` from the DB, and the admin form blocks it before that.

The reverse accessor is a **single object, not a queryset**: `labtest.result` (no `.all()`). If no result exists yet, accessing it raises `RelatedObjectDoesNotExist` — check with `hasattr(test, 'result')` or `try/except`.

Why here: a test has one outcome. Two results for one test is a data bug the schema itself should make impossible — same philosophy as the double-booking constraint (14a): put invariants in the database, not in view code.

## Half 2 — `FileField` + how uploads actually work

```python
result_file = models.FileField(upload_to='lab_results/')
```

Two-part storage — this is the key mental model:
- **DB column** stores only the path string: `lab_results/report_x.pdf`.
- **File bytes** land on disk under `MEDIA_ROOT` (`backend/media/` — wired back in Step 5, gitignored).

`upload_to='lab_results/'` = subfolder inside MEDIA_ROOT. Name collisions are handled automatically (Django appends a random suffix).

No Pillow needed — that's only for `ImageField` (which validates the upload *is* an image). `FileField` takes anything (PDF or image both fine for lab results). Pillow enters at 16e if we do profile photos.

## Half 3 — Serving media in development

Uploaded files aren't web-reachable by default — `runserver` doesn't serve `MEDIA_ROOT`. Dev-only wiring in `config/urls.py`:

```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**`static()` returns patterns only when `DEBUG=True`** — in production it returns an empty list and the real web server (Whitenoise/nginx, Step 20) serves files. Safe to leave in permanently; it self-disables.

---

## Half 4 — The two models

```python
class LabTest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'REQUESTED', 'Requested'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        DONE = 'DONE', 'Done'

    appointment = models.ForeignKey(Appointment, on_delete=models.PROTECT, related_name='lab_tests')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='requested_tests')
    test_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['requested_at']
```

- **`Appointment` imported directly** (`from apps.appointments.models import Appointment`) — cross-app import is fine here because it's one-directional (lab → appointments, never back). `AUTH_USER_MODEL` stays the lazy string as always.
- **`PROTECT` everywhere except test→result.** Medical audit: can't delete an appointment or user with lab history attached. Only `LabResult` cascades with its test (a result is meaningless alone).
- **`ordering = ['requested_at']`** — oldest first. That IS the lab queue order for 16b, free.
- Lifecycle: `REQUESTED → IN_PROGRESS → DONE` (16c drives it, same guarded-transition pattern as appointments).

`LabResult`: the OneToOne + `uploaded_by` (PROTECT) + `result_file` + `notes` + `is_normal` (BooleanField, the normal/abnormal flag for the PDF) + `result_date` (auto_now_add).

---

## Gotchas (Day 27)

- **`class status` lowercase** — the enum-vs-field casing pattern at the *definition* side this time. Nested enum must be `Status`; lowercase collides with the `status` field and `NameError`s at class-body evaluation (this one at least crashes loudly at `check`).
- **`ForeingKey`** — transposed. `AttributeError: module 'django.db.models' has no attribute 'ForeingKey'`. The Day-14 `DataField/ChatField` family.

---

## Revise (16a)

1. **`OneToOneField`** = FK + UNIQUE — one result per test, schema-enforced; reverse accessor is a single object (`test.result`).
2. **`FileField`** stores a path in the DB, bytes under `MEDIA_ROOT/upload_to/`. Pillow only needed for `ImageField`.
3. **`static(MEDIA_URL, document_root=MEDIA_ROOT)`** serves uploads in dev only (self-disables when `DEBUG=False`); production serving comes with deploy (Step 20).

---

**Next (16b):** doctor requests a test from a CONFIRMED appointment (button on doctor pages) + the lab technician's pending queue (oldest first) + LAB role login redirect + nav.