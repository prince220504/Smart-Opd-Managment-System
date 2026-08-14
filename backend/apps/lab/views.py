from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.http import Http404
from apps.appointments.models import Appointment
from .models import LabTest
from .forms import LabResultForm
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.notifications.services import notify
from apps.notifications.models import Notification
from django.db.models import Q, Count
from django.utils import timezone

User = get_user_model()

@login_required
@require_POST
def request_test(request, appointment_id):
    appointment = get_object_or_404(
        Appointment, id=appointment_id, doctor=request.user,
        status__in=[Appointment.Status.CONFIRMED, Appointment.Status.IN_PROGRESS],
    )
    test_name = request.POST.get('test_name', '').strip()
    if test_name:
        LabTest.objects.create(
            appointment=appointment,
            requested_by=request.user,
            test_name=test_name,
        )
        for tech in User.objects.filter(role='LAB'):
            notify(
                recipient=tech,
                message=f'New test requested: {test_name} for {appointment.patient.display_name}.',
                notification_type=Notification.Type.TEST,
                link=reverse('lab:dashboard'),
            )
    return redirect('prescriptions:write', appointment_id=appointment.id)

@login_required
def lab_dashboard(request):
    if request.user.role != 'LAB':
        raise Http404()
    tests = (
        LabTest.objects
        .filter(status=LabTest.Status.REQUESTED)
        .select_related('appointment__patient', 'requested_by')
    )
    stats = LabTest.objects.aggregate(
        new=Count('id', filter=Q(status=LabTest.Status.REQUESTED)),
        active=Count('id', filter=Q(status=LabTest.Status.IN_PROGRESS)),
        done_today=Count('id', filter=Q(result__result_date__date=timezone.localdate())),
    )

    return render(request, 'lab/lab_dashboard.html', {'tests': tests, 'stats': stats})

@login_required
def pending_results(request):
    if request.user.role != 'LAB':
        raise Http404()

    tests = (
        LabTest.objects
        .filter(status=LabTest.Status.IN_PROGRESS)
        .select_related('appointment__patient', 'requested_by')
    )
    return render(request, 'lab/pending_results.html', {'tests': tests})

@login_required
def all_requests(request):
    if request.user.role != 'LAB':
        raise Http404()

    tests = (
        LabTest.objects
        .select_related('appointment__patient', 'requested_by', 'result')
        .order_by('-requested_at')
    )

    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    if status:
        tests= tests.filter(status=status)
    if q:
        tests = tests.filter(
            Q(test_name__icontains=q) | Q(appointment__patient__full_name__icontains=q) | Q(appointment__patient__username__icontains=q)
        )

    return render(request, 'lab/all_requests.html', {
        'tests':tests,
        'statuses': LabTest.Status.choices,
        'status': status,
        'q':q,
    })

@login_required
@require_POST
def start_test(request, test_id):
    if request.user.role != 'LAB':
        raise Http404()
    test = get_object_or_404(LabTest, id=test_id, status=LabTest.Status.REQUESTED)
    test.status = LabTest.Status.IN_PROGRESS
    test.save()
    return redirect('lab:pending_results')

@login_required
def upload_result(request, test_id):
    if request.user.role != 'LAB':
        raise Http404()
    test = get_object_or_404(LabTest, id=test_id)
    existing = getattr(test, 'result', None)
    already_done = test.status == LabTest.Status.DONE

    if request.method == 'POST':
        form = LabResultForm(request.POST, request.FILES, instance=existing)
        if form.is_valid():
            result = form.save(commit=False)
            result.test = test
            result.uploaded_by = request.user
            result.save()
            test.status = LabTest.Status.DONE
            test.save()
            appointment = test.appointment
            notify(
                recipient=appointment.patient,
                message=f'Result uploaded for {test.test_name}.',
                notification_type=Notification.Type.RESULT,
                link=reverse('lab:my_tests'),
                email=not already_done,
            )
            notify(
                recipient=appointment.doctor,
                message=f'Result uploaded for {test.test_name} ({appointment.patient.display_name}).',
                notification_type=Notification.Type.RESULT,
                link=reverse('lab:test_detail', args=[test.id]),
            )
            return redirect('lab:pending_results')
    else:
        form = LabResultForm(instance=existing)

    return render(request, 'lab/upload_result.html', {'form':form, 'test':test})

@login_required
def my_tests(request):
    tests = (
        LabTest.objects
        .filter(appointment__patient=request.user)
        .select_related('appointment', 'result')
        .order_by('-requested_at')
    )
    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    if status:
        tests = tests.filter(status=status)
    if q: 
        tests = tests.filter(test_name__icontains=q)

    return render(request, 'lab/my_tests.html', {
        'tests':tests,
        'statuses': LabTest.Status.choices,
        'status': status,
        'q': q,
    })

@login_required
def test_detail(request, test_id):
    tests = LabTest.objects.select_related(
        'appointment__patient', 'appointment__doctor', 'requested_by', 'result__uploaded_by',
    )
    if request.user.role == 'PATIENT':
        test = get_object_or_404(tests, id=test_id, appointment__patient=request.user)
    elif request.user.role == 'DOCTOR':
        test = get_object_or_404(tests, id=test_id, appointment__doctor=request.user)
    elif request.user.role == 'LAB':
        test = get_object_or_404(tests, id=test_id)
    else:
        raise Http404()
    
    return render(request, 'lab/test_detail.html', {'test':test})
