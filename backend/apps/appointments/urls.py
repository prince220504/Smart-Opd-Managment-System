from django.urls import path
from . import views

app_name = 'appointments' 

urlpatterns = [
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('book/<int:doctor_id>/', views.book_appointment, name='book'),
    path('mine/', views.my_appointments, name='my_appointments'),
    path('doctor/today/', views.doctor_today, name='doctor_today'),
    path('cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel'),
    path('reception/book/', views.reception_book, name='reception_book'),
    path('confirm/<int:appointment_id>/', views.confirm_appointment, name='confirm'),
    path('all/', views.appointment_list, name='appointment_list'),
    path('complete/<int:appointment_id>/', views.complete_appointment, name='complete'),
    path('no-show/<int:appointment_id>/', views.no_show_appointment, name='no_show'),
    path('doctor/records/', views.doctor_records, name='doctor_records'),
    path('doctor/upcoming/', views.doctor_upcoming, name='doctor_upcoming'),
    path('doctor/schedule/', views.doctor_schedule, name='doctor_schedule')
]