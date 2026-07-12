from rest_framework import serializers
from .models import Appointment

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            'id',
            'patient',
            'doctor',
            'appointment_date',
            'time_slot',
            'status',
            'notes',
            'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']