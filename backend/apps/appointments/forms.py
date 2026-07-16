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
