from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import BookAppointmentForm, ReceptionBookingForm
from .models import Appointment
from datetime import date
from django.db.models import Q
from django.http import Http404

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
            return redirect('appointments:my_appointments')
    else:
        form = BookAppointmentForm(initial={'doctor': doctor})

    return render(request, 'appointments/book.html', {'form':form, 'doctor': doctor})

@login_required
def my_appointments(request):
    appointments = (
        request.user.patient_appointments.select_related('doctor').all()
    )
    return render(request, 'appointments/my_appointments.html', {'appointments': appointments})

@login_required 
def doctor_today(request):
    today = date.today()
    appointments = (
        request.user.doctor_appointments
        .filter(appointment_date=today)
        .select_related('patient')
    )
    return render(request,
        'appointments/doctor_today.html', {
            'appointments': appointments,
            'today': today,
        }              
    )    

@login_required 
def doctor_history(request):
    today = date.today()
    appointments = (
        request.user.doctor_appointments
        .filter(appointment_date__lte=today)
        .select_related('patient')
    )
    return render(request, 'appointments/doctor_history.html', {
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
def reception_book(request):
    if request.user.role != 'RECEPTION':
        raise Http404()
    if request.method == 'POST':
        form = ReceptionBookingForm(request.POST)
        if form.is_valid():
            form.save()
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
    
    return _redirect_after_action(request)

@login_required
def appointment_list(request):
    if request.user.role != 'RECEPTION':
        raise Http404()
    
    appointments = (
        Appointment.objects
        .select_related('patient', 'doctor')
        .order_by('-appointment_date','-time_slot')
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
    
    doctors = User.objects.filter(role='DOCTOR').order_by('username')

    return render(request, 'appointments/appointment_list.html', {
        'appointments':appointments,
        'doctors': doctors,
        'statuses': Appointment.Status.choices,
    })