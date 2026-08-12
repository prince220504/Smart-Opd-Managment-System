from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        DOCTOR = 'DOCTOR', 'Doctor'
        RECEPTION = 'RECEPTION', 'Receptionist'
        LAB = 'LAB', 'Lab Technician'
        PATIENT = 'PATIENT','Patient'

    class Department(models.TextChoices):
        GENERAL = 'GENERAL', 'General Medicine'
        CARDIOLOGY = 'CARDIOLOGY', 'Cardiology'
        ORTHOPAEDICS = 'ORTHOPAEDICS', 'Orthopaedics'
        DERMATOLOGY = 'DERMATOLOGY', 'Dermatology'
        ENT = 'ENT', 'ENT'
        PAEDIATRICS = 'PAEDIATRICS', 'Paediatrics'

    class Gender(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER = 'OTHER', 'Other'

    class BloodGroup(models.TextChoices):
        A_POST = 'A+', 'A+'
        A_NEG = 'A-', 'A-'
        B_POS = 'B+', 'B+'
        B_NEG = 'B-', 'B-'
        AB_POS = 'AB+', 'AB+'
        AB_NEG = 'AB-', 'AB-'
        O_POS = 'O+', 'O+'
        O_NEG = 'O-', 'O-'

    phone_validator = RegexValidator(regex=r'^[6-9]\d{9}$', message='Enter a valid 10-digit Indian mobile number (must start with 6, 7, 8, or 9).',)

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10,validators=[phone_validator], blank=True,)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PATIENT,
    )

    department = models.CharField(
        max_length=20,
        choices=Department.choices,
        blank=True, 
    )

    age = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices,blank=True)
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices, blank=True)
    address = models.TextField(blank=True)

    @property
    def phone_with_code(self):
        return f"+91{self.phone}" if self.phone else ''

    def __str__(self):
        return f"{self.username}({self.get_role_display()})"