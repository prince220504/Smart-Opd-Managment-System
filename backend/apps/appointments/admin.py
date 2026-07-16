from django.contrib import admin
from .models import Appointment, DoctorAvailability

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'appointment_date', 'time_slot', 'status', 'created_at')
    list_filter = ('status', 'appointment_date', 'doctor')
    search_fields = ('patient__username', 'doctor__username', 'notes')
    autocomplete_fields = ('patient', 'doctor')
    date_hierarchy = 'appointment_date'

@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'recurrence', 'date', 'start_time', 'end_time')
    list_filter = ('recurrence',)