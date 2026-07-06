from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import BookAppointmentForm
from .models import Appointment
from datetime import date
from django.db.models import Q

User = get_user_model()

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
@require_POST
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        Q(patient=request.user) | Q(doctor=request.user),
        id=appointment_id,
    )

    if appointment.status != Appointment.Status.CANCELLED: 
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()

    if request.user.role == "DOCTOR":
        return redirect('appointments:doctor_today')
    
    return redirect('appointments:my_appointments')