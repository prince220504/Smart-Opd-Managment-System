from django.conf import settings
from django.db import models
from django.db.models import Q

class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        COMPLETED = 'COMPLETED', 'Completed'
        NO_SHOW = 'NO_SHOW', 'No show'
        CANCELLED = 'CANCELLED', 'Cancelled'

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='patient_appointments',
    )

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name = 'doctor_appointments', 
    )
    
    appointment_date = models.DateField()
    time_slot = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    notes = models.TextField(blank=True)
    cancel_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-appointment_date', '-time_slot']
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'appointment_date', 'time_slot'],
                condition=~Q(status='CANCELLED'),
                name='unique_doctor_slot',
                violation_error_message='This slot is already booked for this doctor.',
            )
        ]
    
    def __str__(self):
        return f"{self.patient.username} -> {self.doctor.username} on {self.appointment_date} {self.time_slot}"
    
class DoctorAvailability(models.Model):
    class Recurrence(models.TextChoices):
        EVERYDAY = 'EVERYDAY', 'Every day'
        WEEKDAYS = 'WEEKDAYS', 'Weekdays (Mon-Fri)'
        MON_SAT = 'MON_SAT', 'Mon to Sat'
        DATE = 'DATE', 'Specific date'

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='availabilities',
    )
    recurrence = models.CharField(
        max_length=20,
        choices=Recurrence.choices,
        default=Recurrence.EVERYDAY,
    )
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    breaks = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.doctor.username} - {self.recurrence} ({self.start_time}-{self.end_time})"