from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        DOCTOR = 'DOCTOR', 'Doctor'
        RECEPTION = 'RECEPTION', 'Receptionist'
        LAB = 'LAB', 'Lab Technician'
        PATIENT = 'PATIENT','Patient'

    phone_validator = RegexValidator(regex=r'^[6-9]\d{9}$', message='Enter a valid 10-digit Indian mobile number (must start with 6, 7, 8, or 9).',)

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10,validators=[phone_validator], blank=True,)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PATIENT,
    )

    @property
    def phone_with_code(self):
        return f"+91{self.phone}" if self.phone else ''

    def __str__(self):
        return f"{self.username}({self.get_role_display()})"