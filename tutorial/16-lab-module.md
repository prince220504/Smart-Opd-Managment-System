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

---

# Step 16b — Doctor Request-Test + Lab Queue

## What we did here

1. `request_test` view — doctor requests a test on their own CONFIRMED appointment.
2. `lab_queue` view — the lab technician's pending list (REQUESTED + IN_PROGRESS, oldest first).
3. Routes, request-test buttons on doctor pages, LAB login redirect + nav.

## Half 1 — `status__in` (SQL `IN`)

The queue needs two statuses, not one:

```python
LabTest.objects.filter(status__in=['REQUESTED', 'IN_PROGRESS'])
# WHERE status IN ('REQUESTED', 'IN_PROGRESS')
```

`__in` is the `IN` lookup — same `__` family as `__lte`/`__gt`. Done tests fall off the queue for free.

Why `__in`, not `exclude(status='DONE')`: both give the same rows *today* (3 statuses, so "not DONE" = the two we want). But `__in` names exactly what belongs in the queue — add a 4th status later and `exclude(DONE)` silently lets it in. Explicit beats subtractive.

## Half 2 — Deep `select_related` (FK chain)

The queue prints the patient's name, but `LabTest` has no patient FK — the path is `LabTest → appointment → patient`. Two JOINs in one string:

```python
.select_related('appointment__patient', 'requested_by')
```

`appointment__patient` = follow `appointment`, then its `patient`. Same `__` traversal as admin `search_fields`. A 10-row queue: **1 query** with it, **21** without (1 tests + 10 appointments + 10 patients). Row count doesn't matter — select_related always collapses to one query.

## Half 3 — The views

```python
@login_required
@require_POST
def request_test(request, appointment_id):
    appointment = get_object_or_404(
        Appointment, id=appointment_id, doctor=request.user,
        status=Appointment.Status.CONFIRMED,
    )
    test_name = request.POST.get('test_name', '').strip()
    if test_name:
        LabTest.objects.create(appointment=appointment, requested_by=request.user, test_name=test_name)
    return redirect('appointments:doctor_today')


@login_required
def lab_queue(request):
    if request.user.role != 'LAB':
        raise Http404()
    tests = (
        LabTest.objects
        .filter(status__in=['REQUESTED', 'IN_PROGRESS'])
        .select_related('appointment__patient', 'requested_by')
    )
    return render(request, 'lab/lab_queue.html', {'tests': tests})
```

- `request_test` — the **scoped lookup IS the authorization**: `doctor=request.user, status=CONFIRMED` means a doctor can only request on their own confirmed appointments; anything else 404s. No separate role gate needed.
- One field (`test_name`) → read straight from POST, no ModelForm (ponytail — a form class for one CharField is overkill).
- `lab_queue` — LAB role gate (`raise Http404` hides it from everyone else), the two lookups above. Oldest-first is free from `Meta.ordering=['requested_at']`.

## Half 4 — Wiring

- `lab/urls.py` (NEW, `app_name='lab'`): `queue/` + `request-test/<int:appointment_id>/`; mounted `path('lab/', include('apps.lab.urls'))`.
- Request-test form on CONFIRMED rows (doctor_today + doctor_history) — inline `test_name` input + button (a testing stub; the real dedicated request-test page comes with the Step 21 frontend — the backend view doesn't care where the POST originates).
- `base.html`: LAB nav branch → Lab Queue. `login_view`: LAB → `lab:queue`.

## Gotchas (Day 28)

- `redirect('appointment:doctor_today')` — singular namespace again → `NoReverseMatch`. The reverse-string family; grep every `redirect()`/`{% url %}` for `appointment:` vs `appointments:`.

## Revise (16b)

1. **`status__in`** = SQL `IN` for multi-value filters; explicit beats `exclude` for future-proofing.
2. **`select_related('appointment__patient')`** collapses an FK chain's N+1 to one query regardless of row count.
3. **Scoped lookup as authorization** — `doctor=request.user, status=CONFIRMED` in `get_object_or_404` gates the action with no separate role check; `lab_queue` uses an explicit `raise Http404` LAB gate.

---

**Next (16c):** lab uploads the result file (`request.FILES`, `enctype="multipart/form-data"`) + status flow REQUESTED → IN_PROGRESS → DONE.

---

# Step 16c — Upload Result + Status Flow

## What we did here

1. `LabResultForm` (ModelForm over `LabResult`).
2. `start_test` view (REQUESTED → IN_PROGRESS) + `upload_result` view (creates/updates the result, flips test → DONE).
3. Upload page + queue action buttons.

## Half 1 — File upload needs three things

Every form until now: `<form method="post">` + `request.POST`. Files add a third piece.

**1. `enctype="multipart/form-data"` on the form tag.**

```html
<form method="post" enctype="multipart/form-data">
```

Default encoding sends `key=value&key=value` — a string. That can't carry binary. `multipart/form-data` splits the request into chunks, one per field, files as raw bytes. **Without it the file is silently dropped** — the form submits, the file field arrives empty, validation fails for a reason that looks unrelated. This is the #1 file-upload gotcha.

**2. `request.FILES` — a separate dict.** Text fields land in `request.POST`; uploaded files land in `request.FILES`. A ModelForm with a `FileField` needs **both**:

```python
form = LabResultForm(request.POST, request.FILES)
```

Pass only `request.POST` and the file never reaches the form.

**3. The ModelForm handles the rest.** Same auto-binding as always — Django pulls the file out of `request.FILES`, validates it, and `save()` writes bytes to `MEDIA_ROOT/upload_to/` while storing the path in the DB column (the 16a two-part storage model).

```python
class LabResultForm(forms.ModelForm):
    class Meta:
        model = LabResult
        fields = ['result_file', 'notes', 'is_normal']
```

`test` and `uploaded_by` stay out of the form — server-set in the view, same defense-in-depth as `appointment.patient`.

## Half 2 — Status transitions

```python
@login_required
@require_POST
def start_test(request, test_id):
    if request.user.role != 'LAB':
        raise Http404()
    test = get_object_or_404(LabTest, id=test_id, status=LabTest.Status.REQUESTED)
    test.status = LabTest.Status.IN_PROGRESS
    test.save()
    return redirect('lab:queue')
```

Same guarded-transition shape as the appointment lifecycle: `@require_POST`, role gate, from-state enforced **in the lookup** (`status=REQUESTED` → a non-requested test 404s instead of needing an `if`).

`upload_result` flips to DONE as a side effect of saving the result — no separate "mark done" endpoint. One action, one user intent.

## Half 3 — `instance=` handles create AND update (the OneToOne trap)

First upload attempt on a test that already had a result (created in admin during 16a) gave:

```
IntegrityError: UNIQUE constraint failed: lab_labresult.test_id
```

That's the OneToOne working exactly as designed — one result per test. But a 500 page is the wrong way to express it. Fix:

```python
existing = getattr(test, 'result', None)
...
form = LabResultForm(request.POST, request.FILES, instance=existing)   # POST
form = LabResultForm(instance=existing)                                # GET
```

**`instance=`** tells the ModelForm to *update that row* instead of inserting a new one. `None` → normal create. One argument covers both paths — no branching, no try/except, and re-uploading a corrected result now works.

**`getattr(test, 'result', None)`** — the reverse OneToOne accessor raises `RelatedObjectDoesNotExist` when empty, and Django deliberately makes that class subclass **`AttributeError`** so `getattr` with a default catches it. No try/except needed.

Bonus: GET now pre-fills notes/is_normal from the existing result.

## Gotchas (Day 29)

- **`IN_PORGRESS`** — transposed enum member; `AttributeError` when Start is clicked. The `ForeingKey`/`roel` family.
- **`{url ... %}`** — missing `%` in the *opening* tag, so the template rendered the tag as literal text into the `href`. Symptom: a 404 whose URL contains `%7Burl%20'lab:upload_result'...`. If a URL-encoded template tag shows up in a request path, a `{%` is malformed.
- **Stale browser page** — the 404 persisted after the fix until a hard refresh.

## Revise (16c)

1. **Three pieces or the file vanishes**: `enctype="multipart/form-data"` + `request.FILES` passed to the form + a `FileField` on the ModelForm.
2. **From-state in the lookup** (`status=REQUESTED` in `get_object_or_404`) enforces the transition without an `if`; saving the result flips the test to DONE as a side effect.
3. **`instance=existing`** makes one view do create-or-update, which is how a OneToOne should be edited; `getattr(obj, 'one_to_one', None)` works because `RelatedObjectDoesNotExist` subclasses `AttributeError`.

---

**Next (16d):** ReportLab branded PDF report + `FileResponse` download for patient and doctor. Closes Step 16 → PR #7.