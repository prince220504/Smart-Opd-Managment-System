from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import Notification

@login_required
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
    