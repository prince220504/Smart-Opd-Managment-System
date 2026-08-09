from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import BookAppointmentForm, ReceptionBookingForm, DoctorScheduleForm
from .models import Appointment, DoctorAvailability
from datetime import date
from django.db.models import Q, Count
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
        return redirect('appointments:doctor_today')
    return redirect('appointments:my_appointments')

@login_required
def doctor_list(request):
    doctors = User.objects.filter(role='DOCTOR').order_by('username')
    return render(request, 'appointments/doctor_list.html', {'doctors': doctors})

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
                message=f'Appointment booked with Dr. {doctor.username} on {appointment.appointment_date}.',
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

    return render(request, 'appointments/book.html', {'form':form, 'doctor': doctor, 'availability': availability})

@login_required
def patient_dashboard(request):
    """Landing page for a patient: three counts, the next visit, recent activity.

    Every number here is read straight off the real tables — nothing is stored.
    """
    if request.user.role != 'PATIENT':
        raise Http404()

    today = timezone.localdate()
    live = [Appointment.Status.PENDING, Appointment.Status.CONFIRMED]

    upcoming = (
        request.user.patient_appointments
        .filter(appointment_date__gte=today, status__in=live)
        .select_related('doctor')
        .order_by('appointment_date', 'time_slot')
    )

    return render(request, 'appointments/patient_dashboard.html', {
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
    appointments = (
        request.user.patient_appointments.select_related('doctor', 'prescription').all()
    )
    return render(request, 'appointments/my_appointments.html', {'appointments': appointments})

@login_required 
def doctor_today(request):
    today = date.today()
    appointments = (
        request.user.doctor_appointments
        .filter(appointment_date=today)
        .select_related('patient', 'prescription')
        .prefetch_related('lab_tests__result')
    )
    return render(request,
        'appointments/doctor_today.html', {
            'appointments': appointments,
            'today': today,
        }              
    )    

@login_required 
def doctor_records(request):
    today = date.today()
    appointments = (
        request.user.doctor_appointments
        .filter(appointment_date__lte=today)
        .select_related('patient')
        .prefetch_related('lab_tests__result')
    )
    return render(request, 'appointments/doctor_records.html', {
        'appointments': appointments,
    })

@login_required
def doctor_upcoming(request):
    today = date.today()
    appointments = (
        request.user.doctor_appointments
        .filter(appointment_date__gt=today)
        .select_related('patient')
        .order_by('appointment_date', 'time_slot')
    )
    return render(request, 'appointments/doctor_upcoming.html', {
        'appointments': appointments,
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

    return render(request, 'appointments/doctor_schedule.html', {
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
                message=f'Appointment booked with Dr. {appointment.doctor.username} on {appointment.appointment_date}.',
                notification_type=Notification.Type.BOOKING,
                link=reverse('appointments:my_appointments'),
                email=True,
            )
            return redirect('appointments:appointment_list')
    else:
        form = ReceptionBookingForm()
    
    return render(request, 'appointments/reception_book.html', {'form': form})

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
def complete_appointment(request, appointment_id):
    if request.user.role == 'RECEPTION':
        appointment = get_object_or_404(Appointment, id=appointment_id)
    else:
        appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)

    if appointment.status == Appointment.Status.CONFIRMED:
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
    
    if appointment.status == Appointment.Status.CONFIRMED:
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

    return render(request, 'appointments/appointment_list.html', {
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
        .values('doctor__username')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    return render(request, 'appointments/dashboard.html', {
        'stats': stats,
        'per_doctor': per_doctor,
        'today': today,
    })

@login_required
def medical_history(request, patient_id=None):
    if patient_id is None:
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

    return render(request, 'appointments/medical_history.html', {
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
            _csv_safe(appt.patient.username),
            _csv_safe(appt.doctor.username),
            appt.appointment_date,
            appt.time_slot,
            appt.get_status_display(),
            _csv_safe(appt.notes),
        ])

    return response
