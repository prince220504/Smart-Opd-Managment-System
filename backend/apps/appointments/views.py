from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import BookAppointmentForm, ReceptionBookingForm, DoctorScheduleForm
from .models import Appointment, DoctorAvailability
from datetime import date, timedelta
from django.db.models import Q, Count, Max
from django.http import Http404, HttpResponse
from django.urls import reverse
from apps.notifications.services import notify
from apps.notifications.models import Notification
from apps.lab.models import LabTest
from apps.prescriptions.models import Prescription
from django.utils import timezone
import csv

User = get_user_model()

def _redirect_after_action(request):
    if request.user.role == 'RECEPTION':
        return redirect('appointments:appointment_list')
    if request.user.role == 'DOCTOR':
        return redirect('appointments:doctor_dashboard')
    return redirect('appointments:my_appointments')

@login_required
def doctor_list(request):
    doctors = User.objects.filter(role='DOCTOR').order_by('username')
    department = request.GET.get('department', '')
    if department:
        doctors = doctors.filter(department=department)

    return render(request, 'appointments/patient/doctor_list.html', {
        'doctors': doctors,
        'department': department,
        'departments': User.Department.choices,
    })

@login_required
def book_appointment(request, doctor_id):
    doctor = get_object_or_404(User, id=doctor_id, role='DOCTOR')

    if request.method == 'POST':
        form = BookAppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = request.user
            appointment.save()
            notify(
                recipient=appointment.patient,
                message=f'Appointment booked with Dr. {doctor.display_name} on {appointment.appointment_date}.',
                notification_type=Notification.Type.BOOKING,
                link=reverse('appointments:my_appointments'),
                email=True,
            )
            return redirect('appointments:my_appointments')
    else:
        form = BookAppointmentForm(initial={'doctor': doctor})

    availability = doctor.availabilities.exclude(
        recurrence=DoctorAvailability.Recurrence.DATE
    ).first()

    return render(request, 'appointments/patient/book.html', {'form':form, 'doctor': doctor, 'availability': availability})

@login_required
def reschedule_appointment(request, appointment_id):
    # the scoped lookup is the permission check: your own appointment, and 
    # only one that has not finished yet
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user,
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
    )

    if request.method == 'POST':
        form = BookAppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            # a moved visit is no longer the one the doctor agreed to
            appointment.status = Appointment.Status.PENDING
            appointment.save()
            notify(
                recipient=appointment.doctor,
                message=f'{request.user.display_name} moved an appointment to {appointment.appointment_date} at {appointment.time_slot}.',
                notification_type=Notification.Type.STATUS,
                link=reverse('appointments:doctor_dashboard'), 
            )
            return redirect('appointments:my_appointments')
    else:
        form = BookAppointmentForm(instance=appointment)

    availability = appointment.doctor.availabilities.exclude(
        recurrence=DoctorAvailability.Recurrence.DATE
    ).first()

    return render(request, 'appointments/patient/reschedule.html',{
        'form': form,
        'appointment': appointment,
        'doctor': appointment.doctor,
        'availability': availability,
    })


@login_required
def patient_dashboard(request):
    """Landing page for a patient: three counts, the next visit, recent activity.

    Every number here is read straight off the real tables — nothing is stored.
    """
    if request.user.role != 'PATIENT':
        raise Http404()

    today = timezone.localdate()
    live = [Appointment.Status.PENDING, Appointment.Status.CONFIRMED, Appointment.Status.IN_PROGRESS]

    upcoming = (
        request.user.patient_appointments
        .filter(appointment_date__gte=today, status__in=live)
        .select_related('doctor')
        .order_by('appointment_date', 'time_slot')
    )

    return render(request, 'appointments/patient/patient_dashboard.html', {
        'upcoming_count': upcoming.count(),
        'pending_reports': LabTest.objects.filter(
            appointment__patient=request.user
        ).exclude(status=LabTest.Status.DONE).count(),
        'prescription_count': Prescription.objects.filter(
            appointment__patient=request.user
        ).count(),
        # .first() on an already-ordered queryset = the soonest visit
        'next_appointment': upcoming.first(),
        'recent': request.user.notifications.all()[:5],
    })

@login_required
def my_appointments(request):
    if request.user.role != 'PATIENT':
        raise Http404()
    appointments = (
        request.user.patient_appointments.select_related('doctor', 'prescription').all()
    )
    # filter ride in the querystring, so the page stays one plain GET
    status = request.GET.get('status', '')
    q = request.GET.get('q', '').strip()
    if status:
        appointments = appointments.filter(status=status)
    if q:
        appointments = appointments.filter(Q(doctor__full_name__icontains=q) | Q(doctor__username__icontains=q))

    return render(request, 'appointments/patient/my_appointments.html', {
        'appointments': appointments,
        'status': status,
        'q': q,
        'statuses': Appointment.Status.choices,
    })

@login_required 
def doctor_dashboard(request):
    if request.user.role != 'DOCTOR':
        raise Http404()
    today = timezone.localdate()
    appointments = (
        request.user.doctor_appointments
        .filter(appointment_date=today)
        .select_related('patient', 'prescription')
        .prefetch_related('lab_tests__result')
    )
    # one table scan for three counters, instead of three .count() round trips
    stats = appointments.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='COMPLETED')),
        pending=Count('id', filter=Q(status__in=['PENDING','CONFIRMED','IN_PROGRESS'])),
    )

    # last 7 days, one row per (day, status), gaps filled in python
    week_start = today - timedelta(days=6)
    done, rest = {}, {}
    for row in (
        request.user.doctor_appointments
        .filter(appointment_date__range=[week_start, today])
        .values('appointment_date', 'status')
        .annotate(total=Count('id'))
    ):
        bucket = done if row['status'] == 'COMPLETED' else rest
        key = row['appointment_date']
        bucket[key] = bucket.get(key, 0) + row['total']

    week = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        week.append({
            'label': day.strftime('%a'),
            'done': done.get(day, 0),
            'rest': rest.get(day, 0),
            'total': done.get(day, 0) + rest.get(day,0),
        })
    week_scale = max(1, max(d['total'] for d in week))
 
    return render(request,
        'appointments/doctor/doctor_dashboard.html', {
            'appointments': appointments,
            'today': today,
            'stats':stats,
            'week': week,
            'week_scale': week_scale,
            'week_total': sum(d['total'] for d in week),
            'week_done': sum(d['done'] for d in week),
        }              
    )    

@login_required 
def doctor_records(request):
    if request.user.role != 'DOCTOR':
        raise Http404()
    today = timezone.localdate()
    appointments = (
        request.user.doctor_appointments
        .filter(appointment_date__lte=today)
        .select_related('patient', 'prescription')
        .prefetch_related('lab_tests__result')
    )
    status = request.GET.get('status', '')
    appt_date = request.GET.get('date', '')
    q = request.GET.get('q', '').strip()
    if status:
        appointments = appointments.filter(status=status)
    if appt_date:
        appointments = appointments.filter(appointment_date=appt_date)
    if q:
        appointments = appointments.filter(Q(patient__full_name__icontains=q) | Q(patient__username__icontains=q))

    return render(request, 'appointments/doctor/doctor_records.html', {
        'appointments': appointments,
        'status': status,
        'date': appt_date,
        'q': q,
        'statuses': Appointment.Status.choices,
    })

@login_required
def doctor_upcoming(request):
    if request.user.role != 'DOCTOR':
        raise Http404()
    today = timezone.localdate()
    appointments = (
        request.user.doctor_appointments
        .filter(appointment_date__gt=today)
        .select_related('patient')
        .order_by('appointment_date', 'time_slot')
    )
    return render(request, 'appointments/doctor/doctor_upcoming.html', {
        'appointments': appointments,
    })

@login_required
def doctor_patients(request):
    if request.user.role != 'DOCTOR':
        raise Http404()

    patients = (
        User.objects
        .filter(
            patient_appointments__doctor=request.user,
            patient_appointments__status=Appointment.Status.COMPLETED,
        )
        .annotate(
            visits=Count('patient_appointments'),
            last_visit=Max('patient_appointments__appointment_date'),
        )
        .order_by('-last_visit')
    )
    return render(request, 'appointments/doctor/doctor_patients.html',{
        'patients': patients,
    })

@login_required
def doctor_schedule(request):
    if request.user.role != 'DOCTOR':
        raise Http404()
    
    current = request.user.availabilities.exclude(
        recurrence=DoctorAvailability.Recurrence.DATE 
    ).first()
    editing = current is None or request.GET.get('edit') == '1'

    if request.method == 'POST':
        editing = True
        form = DoctorScheduleForm(request.POST)
        if form.is_valid():
            availability = form.save(commit=False)
            availability.doctor = request.user
            break_starts = request.POST.getlist('break_start')
            break_ends = request.POST.getlist('break_end')
            breaks = []
            for bs, be in zip(break_starts, break_ends):
                if bs and be:
                    breaks.append({'start': bs, 'end': be})
            availability.breaks = breaks
            if availability.recurrence != DoctorAvailability.Recurrence.DATE:
                DoctorAvailability.objects.filter(doctor=request.user).exclude(
                    recurrence=DoctorAvailability.Recurrence.DATE
                ).delete()
            availability.save()
            return redirect('appointments:doctor_schedule')
    elif current:
        form = DoctorScheduleForm(initial={
            'recurrence': current.recurrence,
            'date': current.date,
            'start_time': current.start_time,
            'end_time': current.end_time,
        })
    else:
        form = DoctorScheduleForm()

    return render(request, 'appointments/doctor/doctor_schedule.html', {
        'form': form,
        'current': current,
        'editing': editing,
    })

@login_required
def reception_book(request):
    if request.user.role != 'RECEPTION':
        raise Http404()
    if request.method == 'POST':
        form = ReceptionBookingForm(request.POST)
        if form.is_valid():
            appointment = form.save()
            notify(
                recipient=appointment.patient,
                message=f'Appointment booked with Dr. {appointment.doctor.display_name} on {appointment.appointment_date}.',
                notification_type=Notification.Type.BOOKING,
                link=reverse('appointments:my_appointments'),
                email=True,
            )
            return redirect('appointments:appointment_list')
    else:
        form = ReceptionBookingForm()
    
    return render(request, 'appointments/reception/reception_book.html', {'form': form})

@login_required
@require_POST
def confirm_appointment(request, appointment_id):
    if request.user.role == 'RECEPTION':
        appointment = get_object_or_404(Appointment, id=appointment_id)
    else:
        appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)

    if appointment.status == Appointment.Status.PENDING:
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save()
        notify(
            recipient=appointment.patient,
            message=f'Your appointment on {appointment.appointment_date} is confirmed.',
            notification_type=Notification.Type.STATUS,
            link=reverse('appointments:my_appointments'),
        )
    
    return _redirect_after_action(request)

@login_required
@require_POST
def start_appointment(request, appointment_id):
    if request.user.role == 'RECEPTION':
        appointment = get_object_or_404(Appointment, id=appointment_id)
    else:
        appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)

    if appointment.status == Appointment.Status.CONFIRMED:
        appointment.status = Appointment.Status.IN_PROGRESS
        appointment.save()

    return _redirect_after_action(request)

@login_required
@require_POST
def complete_appointment(request, appointment_id):
    if request.user.role == 'RECEPTION':
        appointment = get_object_or_404(Appointment, id=appointment_id)
    else:
        appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)

    if appointment.status in (Appointment.Status.CONFIRMED, Appointment.Status.IN_PROGRESS):
        appointment.status = Appointment.Status.COMPLETED
        appointment.save()
    
    return _redirect_after_action(request)

@login_required
@require_POST
def no_show_appointment(request, appointment_id):
    if request.user.role == 'RECEPTION':
        appointment = get_object_or_404(Appointment, id=appointment_id)
    else:
        appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
    
    if appointment.status in (Appointment.Status.CONFIRMED, Appointment.Status.IN_PROGRESS):
        appointment.status = Appointment.Status.NO_SHOW
        appointment.save()

    return _redirect_after_action(request)

@login_required
@require_POST
def cancel_appointment(request, appointment_id):
    if request.user.role == 'RECEPTION':
        appointment = get_object_or_404(Appointment, id=appointment_id)
    else:
        appointment = get_object_or_404(Appointment, Q(patient=request.user) | Q(doctor=request.user), id=appointment_id,)
    
    if appointment.status != Appointment.Status.CANCELLED:
        appointment.status = Appointment.Status.CANCELLED
        appointment.cancel_reason = request.POST.get('cancel_reason', '')
        appointment.save()

        recipients = [appointment.patient, appointment.doctor]
        for user in recipients:
            if user != request.user:
                target = 'appointments:my_appointments' if user == appointment.patient else 'appointments:doctor_records'
                notify(
                    recipient=user,
                    message=f'Appointment on {appointment.appointment_date} was cancelled.',
                    notification_type=Notification.Type.STATUS,
                    link=reverse(target),
                )
    
    return _redirect_after_action(request)

def _filtered_appointments(request):
    appointments = (
        Appointment.objects
        .select_related('patient', 'doctor')
        .order_by('-appointment_date', '-time_slot')
    )

    status = request.GET.get('status')
    if status:
        appointments = appointments.filter(status=status)

    doctor_id = request.GET.get('doctor')
    if doctor_id:
        appointments = appointments.filter(doctor_id=doctor_id)

    appt_date = request.GET.get('date')
    if appt_date:
        appointments = appointments.filter(appointment_date=appt_date)

    return appointments

@login_required
def appointment_list(request):
    if request.user.role != 'RECEPTION':
        raise Http404()
    
    appointments = _filtered_appointments(request)
    doctors = User.objects.filter(role='DOCTOR').order_by('username')

    return render(request, 'appointments/reception/appointment_list.html', {
        'appointments':appointments,
        'doctors': doctors,
        'statuses': Appointment.Status.choices,
    })

@login_required
def reception_dashboard(request):
    if request.user.role != 'RECEPTION':
        raise Http404()

    today = timezone.localdate()

    stats = Appointment.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status=Appointment.Status.PENDING)),
        confirmed=Count('id', filter=Q(status=Appointment.Status.CONFIRMED)),
        completed=Count('id', filter=Q(status=Appointment.Status.COMPLETED)),
        cancelled=Count('id', filter=Q(status=Appointment.Status.CANCELLED)),
        no_show=Count('id', filter=Q(status=Appointment.Status.NO_SHOW)),
        today=Count('id', filter=Q(appointment_date=today)),
    )

    per_doctor = list(
        Appointment.objects
        .values('doctor__full_name', 'doctor__username')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    today_appointments = (
        Appointment.objects
        .filter(appointment_date=today)
        .select_related('patient', 'doctor')
        .order_by('time_slot')
    )

    return render(request, 'appointments/reception/dashboard.html', {
        'stats': stats,
        'per_doctor': per_doctor,
        'today': today,
        'today_appointments': today_appointments,
    })

@login_required
def medical_history(request, patient_id=None):
    if patient_id is None:
        if request.user.role != 'PATIENT':
            raise Http404()
        patient = request.user
    elif request.user.role in ('DOCTOR', 'RECEPTION'):
        patient = get_object_or_404(User, id=patient_id, role='PATIENT')
    else:
        raise Http404()

    appointments = (
        Appointment.objects
        .filter(patient=patient)
        .select_related('doctor', 'prescription')
        .prefetch_related('lab_tests__result')
    )

    return render(request, 'appointments/patient/medical_history.html', {
        'patient': patient,
        'appointments': appointments,
    })

def _csv_safe(value):
    text = str(value)
    if text.startswith(('=', '+', '-', '@')):
        return "'" + text
    return text

@login_required
def export_appointments_csv(request):
    if request.user.role != 'RECEPTION':
        raise Http404()

    appointments = _filtered_appointments(request)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="appointments-{timezone.localdate()}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(['Patient', 'Doctor', 'Date', 'Time', 'Status', 'Notes'])

    for appt in appointments:
        writer.writerow([
            _csv_safe(appt.patient.display_name),
            _csv_safe(appt.doctor.display_name),
            appt.appointment_date,
            appt.time_slot,
            appt.get_status_display(),
            _csv_safe(appt.notes),
        ])

    return response
