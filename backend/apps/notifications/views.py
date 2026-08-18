from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import Notification
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_GET
from django.utils.crypto import constant_time_compare
from .tasks import send_appointment_reminders, expire_stale_appointments

@login_required
@never_cache
def notification_list(request):
    notifications = request.user.notifications.all()
    return render(request, 'notifications/list.html', {'notifications':notifications})

@login_required
def open_notification(request, notification_id):
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user,
    )
    notification.is_read = True
    notification.save()
    return redirect(notification.link or 'notifications:list')

@require_GET
def run_daily_tasks(request):
    """Hit once a day by an external cron service. Replaces Celery Beat in production."""
    if not settings.CRON_KEY or not constant_time_compare(request.GET.get('key', ''), settings.CRON_KEY):
        raise Http404()
    return HttpResponse(
        f'reminders={send_appointment_reminders()} expired={expire_stale_appointments()}'
    )
