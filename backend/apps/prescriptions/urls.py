from django.urls import path
from . import views

app_name = 'prescriptions'

urlpatterns = [
    path('write/<int:appointment_id>/', views.write_prescription, name='write'),
    path('view/<int:appointment_id>/', views.view_prescription, name='view'),
]
