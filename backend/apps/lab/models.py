from django.conf import settings
from django.db import models
from apps.appointments.models import Appointment

class LabTest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = 'REQUESTED', 'Requested'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        DONE = 'DONE', 'Done'

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.PROTECT,
        related_name='lab_tests',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='requested_tests',
    )
    test_name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
    )
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['requested_at']

    def __str__(self):
        return f"{self.test_name} for {self.appointment.patient.username} ({self.status})"

class LabResult(models.Model):
    test = models.OneToOneField(
        LabTest,
        on_delete=models.CASCADE,
        related_name='result',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='uploaded_results',
    )
    result_file = models.FileField(upload_to='lab_results/')
    notes = models.TextField(blank=True)
    is_normal = models.BooleanField(default=True)
    result_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for {self.test.test_name}"
