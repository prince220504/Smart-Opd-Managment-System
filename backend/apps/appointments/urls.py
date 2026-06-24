from django.urls import path
from . import views

app_name = 'appointments' 

urlpatterns = [
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('book/<int:doctor_id>/', views.book_appointment, name='book'),
    path('mine/', views.my_appointments, name='my_appointments'),
    path('cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel'),
]