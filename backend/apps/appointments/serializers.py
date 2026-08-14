from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .forms import _validate_doctor_available, _validate_slot_free
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
        read_only_fields = ['id', 'patient', 'status', 'created_at']

    def validate_doctor(self, doctor):
        if doctor.role != 'DOCTOR':
            raise serializers.ValidationError('That user is not a doctor.')
        return doctor

    def validate(self, attrs):
        # the API must obey the same rules the booking form does, so it 
        # calls the same two helpers instead of copying them
        data = {
            field: attrs.get(field) or getattr(self.instance, field, None)
            for field in ('doctor', 'appointment_date', 'time_slot')
        }
        try:
            _validate_slot_free(data, self.instance)
            _validate_doctor_available(data)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return attrs
