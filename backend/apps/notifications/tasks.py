from celery import shared_task
from django.core.mail import send_mail
from .models import Notification

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_notification_email(self, notification_id):
    """Mail an existing Notification row. Retries on SMTP failure."""
    notification = Notification.objects.get(id=notification_id)
    if not notification.recipient.email:
        return 
    send_mail(
            subject=f'OPD - {Notification.Type(notification.notification_type).label}',
            message=notification.message,
            from_email=None,
            recipient_list=[notification.recipient.email],
            fail_silently=False,
        )
