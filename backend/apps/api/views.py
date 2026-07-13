from rest_framework import viewsets, permissions
from apps.appointments.models import Appointment
from apps.appointments.serializers import AppointmentSerializer

class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'RECEPTION':
            return Appointment.objects.select_related('patient', 'doctor')
        if user.role == 'DOCTOR':
            return user.doctor_appointments.select_related('patient')
        return user.patient_appointments.select_related('doctor')
    
    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)