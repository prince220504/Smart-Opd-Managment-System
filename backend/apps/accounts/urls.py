from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'), 
    path('logout/', views.logout_view, name='logout'), 
    path('register/', views.register_view, name='register'), 
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('patients/', views.patient_registry, name='patient_registry'),
    path('patients/register/', views.register_patient, name='register_patient'),
]     