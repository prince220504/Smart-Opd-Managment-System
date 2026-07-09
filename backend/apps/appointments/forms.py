from django import forms
from django.contrib.auth import get_user_model
from .models import Appointment

User = get_user_model()

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
