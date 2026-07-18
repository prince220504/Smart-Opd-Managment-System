from django.contrib import admin
from .models import LabTest, LabResult

@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ('test_name', 'appointment', 'requested_by')
    list_filter = ('status',)
    search_fields = ('test_name', 'appointment__patient__username')

@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ('test', 'uploaded_by','is_normal', 'result_date')
    list_filter = ('is_normal',)