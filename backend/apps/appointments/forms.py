from django import forms
from django.contrib.auth import get_user_model
from .models import Appointment, DoctorAvailability

User = get_user_model()

def _validate_slot_free(cleaned_data):
    doctor = cleaned_data.get('doctor')
    appt_date = cleaned_data.get('appointment_date')
    slot = cleaned_data.get('time_slot')
    if doctor and appt_date and slot:
        clash = (
            Appointment.objects
            .filter(doctor=doctor, appointment_date=appt_date, time_slot=slot)
            .exclude(status=Appointment.Status.CANCELLED)
            .exists()
        )
        if clash:
            raise forms.ValidationError('This slot is already booked for this doctor.')

def _validate_doctor_available(cleaned_data):
    doctor = cleaned_data.get('doctor')
    appt_date = cleaned_data.get('appointment_date')
    slot = cleaned_data.get('time_slot')
    if not (doctor and appt_date and slot):
        return
    
    availability = doctor.availabilities.filter(
        recurrence=DoctorAvailability.Recurrence.DATE, date=appt_date
    ).first()
    if availability is None:
        availability = doctor.availabilities.exclude(
            recurrence=DoctorAvailability.Recurrence.DATE
        ).first()
    
    if availability is None:
        raise forms.ValidationError('This doctor has not set a schedule yet.')
    
    weekday = appt_date.weekday() # Mon=0 ... Sun=6
    rec = availability.recurrence
    if rec == DoctorAvailability.Recurrence.WEEKDAYS and weekday > 4:
        raise forms.ValidationError('Doctor is not available on weekends.')
    if rec == DoctorAvailability.Recurrence.MON_SAT and weekday > 5 :
        raise forms.ValidationError('Doctor is not available on Sundays.')
    
    if not (availability.start_time <= slot < availability.end_time):
        raise forms.ValidationError('Doctor is not available at this time.')
    
    slot_str = slot.strftime('%H:%M')
    for b in availability.breaks:
        if b['start'] <= slot_str < b['end']:
            raise forms.ValidationError('Doctor is on a break at this time.')

class BookAppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['doctor', 'appointment_date', 'time_slot', 'notes']
        widgets= {
            'appointment_date': forms.DateInput(attrs={'type':'date'}),
            'time_slot': forms.TimeInput(attrs={'type':'time'}),      
        }

    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = User.objects.filter(role='DOCTOR')

    def clean(self):
        cleaned_data = super().clean()
        _validate_slot_free(cleaned_data)
        _validate_doctor_available(cleaned_data)
        return cleaned_data
        
class ReceptionBookingForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'appointment_date', 'time_slot', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type':'date'}),
            'time_slot': forms.TimeInput(attrs={'type':'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = User.objects.filter(role='PATIENT')
        self.fields['doctor'].queryset = User.objects.filter(role='DOCTOR')
    
    def clean(self):
        cleaned_data = super().clean()
        _validate_slot_free(cleaned_data)
        _validate_doctor_available(cleaned_data)
        return cleaned_data

class DoctorScheduleForm(forms.ModelForm):
    class Meta:
        model = DoctorAvailability
        fields = ['recurrence', 'date', 'start_time', 'end_time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        recurrence = cleaned_data.get('recurrence')
        date = cleaned_data.get('date')
        if recurrence == 'DATE' and not date:
            raise forms.ValidationError('Pick the date for a specific-date schedule.')
        start = cleaned_data.get('start_time')
        end = cleaned_data.get('end_time')
        if start and end and start >= end:
            raise forms.ValidationError('End time must be after start time.')
        return cleaned_data
