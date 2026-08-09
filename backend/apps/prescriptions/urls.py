from django.urls import path
from . import views

app_name = 'prescriptions'

urlpatterns = [
    path('mine/', views.my_prescriptions, name='my_prescriptions'),
    path('write/<int:appointment_id>/', views.write_prescription, name='write'),
    path('view/<int:appointment_id>/', views.view_prescription, name='view'),
]
