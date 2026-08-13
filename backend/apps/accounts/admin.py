from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username','full_name','email','role','phone','is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'full_name', 'email', 'phone')

    hospital_fields = ('full_name', 'role', 'department', 'phone', 'age', 'gender', 'blood_group', 'address')

    fieldsets = UserAdmin.fieldsets + (('Hospital info', {'fields': hospital_fields}),)

    add_fieldsets = UserAdmin.add_fieldsets + (('Hospital info', {'fields': hospital_fields}),)