from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.http import Http404
from apps.appointments.models import Appointment
from .models import LabTest

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
