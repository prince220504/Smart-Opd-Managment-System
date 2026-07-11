from django import forms
from django.contrib.auth import get_user_model
from .models import Appointment

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
