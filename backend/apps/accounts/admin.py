from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username','email','role','phone','is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone')

    fieldsets = UserAdmin.fieldsets + (('Hospital info', {'fields': ('role', 'phone')}),)

    add_fieldsets = UserAdmin.add_fieldsets + (('Hospital info', {'fields': ('role', 'phone')}),)