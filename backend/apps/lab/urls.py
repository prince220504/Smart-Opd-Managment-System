from django.urls import path
from . import views

app_name = 'lab'

urlpatterns = [
    path('queue/', views.lab_queue, name='queue'),
    path('request-test/<int:appointment_id>/', views.request_test, name='request_test'),
    path('start-test/<int:test_id>/', views.start_test, name='start_test'),
    path('upload-result/<int:test_id>/', views.upload_result, name='upload_result'),
    path('my-tests/', views.my_tests, name='my_tests'),
]
