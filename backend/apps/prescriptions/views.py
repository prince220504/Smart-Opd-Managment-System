from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from apps.appointments.models import Appointment
from .forms import PrescriptionForm
from .models import Prescription

@login_required
def write_prescription(request, appointment_id):
    appointment = get_object_or_404(
        Appointment, 
        id=appointment_id,
        doctor=request.user,
        status=Appointment.Status.COMPLETED,
    )
    existing = getattr(appointment, 'prescription', None)

    if request.method == 'POST':
        form = PrescriptionForm(request.POST, instance=existing)
        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.appointment = appointment
            names = request.POST.getlist('med_name')
            dosages = request.POST.getlist('med_dosage')
            frequencies = request.POST.getlist('med_frequency')
            durations = request.POST.getlist('med_duration')
            medicines = []
            for name, dosage, frequency, duration in zip(names, dosages, frequencies, durations):
                if name:
                    medicines.append({
                        'name': name,
                        'dosage': dosage,
                        'frequency': frequency,
                        'duration': duration,
                    })
            prescription.medicines = medicines
            prescription.save()
            return redirect('appointments:doctor_records')
    else:
        form = PrescriptionForm(instance=existing)

    return render(request, 'prescriptions/write.html', {
        'form': form,
        'appointment': appointment,
        'existing': existing,
    })
            
@login_required
def view_prescription(request, appointment_id):
    prescription = get_object_or_404(
        Prescription,
        appointment__id=appointment_id,
        appointment__patient=request.user,
    )
    return render(request, 'prescriptions/view.html', {'prescription':prescription,})
