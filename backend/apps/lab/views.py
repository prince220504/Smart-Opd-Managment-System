from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.http import Http404
from apps.appointments.models import Appointment
from .models import LabTest
from .forms import LabResultForm

@login_required
@require_POST
def request_test(request, appointment_id):
    appointment = get_object_or_404(
        Appointment, id=appointment_id, doctor=request.user,
        status=Appointment.Status.CONFIRMED,
    )
    test_name = request.POST.get('test_name', '').strip()
    if test_name:
        LabTest.objects.create(
            appointment=appointment,
            requested_by=request.user,
            test_name=test_name,
        )
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

@login_required
@require_POST
def start_test(request, test_id):
    if request.user.role != 'LAB':
        raise Http404()
    test = get_object_or_404(LabTest, id=test_id, status=LabTest.Status.REQUESTED)
    test.status = LabTest.Status.IN_PROGRESS
    test.save()
    return redirect('lab:queue')

@login_required
def upload_result(request, test_id):
    if request.user.role != 'LAB':
        raise Http404()
    test = get_object_or_404(LabTest, id=test_id)
    existing = getattr(test, 'result', None)

    if request.method == 'POST':
        form = LabResultForm(request.POST, request.FILES, instance=existing)
        if form.is_valid():
            result = form.save(commit=False)
            result.test = test
            result.uploaded_by = request.user
            result.save()
            test.status = LabTest.Status.DONE
            test.save()
            return redirect('lab:queue')
    else:
        form = LabResultForm(instance=existing)

    return render(request, 'lab/upload_result.html', {'form':form, 'test':test})

@login_required
def my_tests(request):
    tests = (
        LabTest.objects
        .filter(appointment__patient=request.user)
        .select_related('appointment', 'result')
    )
    return render(request, 'lab/my_tests.html', {'tests':tests})

@login_required
def test_detail(request, test_id):
    test = get_object_or_404(
        LabTest.objects.select_related('appointment__patient', 'result__uploaded_by'),
        id = test_id, appointment__doctor=request.user,
    )
    return render(request, 'lab/test_detail.html', {'test':test})
