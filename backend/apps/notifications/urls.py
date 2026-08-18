from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('open/<int:notification_id>/', views.open_notification, name='open'),
    path('cron/daily/', views.run_daily_tasks, name='cron_daily'),
]