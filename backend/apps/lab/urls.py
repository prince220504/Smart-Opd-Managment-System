from django.urls import path
from . import views

app_name = 'lab'

urlpatterns = [
    path('queue/', views.lab_queue, name='queue'),
    path('request-test/<int:appointment_id>/', views.request_test, name='request_test'),
]
