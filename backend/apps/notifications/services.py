from django.core.mail import send_mail
from .models import Notification

def notify(recipient, message, notification_type, link='', email=False):
    """Create one in-app notification. Single write path for all triggers.
    
    email=True also sends plain-text mail (matrix: booking + result only).
    """
    notification = Notification.objects.create(
        recipient=recipient,
        message=message,
        notification_type=notification_type,
        link=link
    )
    if email and recipient.email:
        send_mail(
            subject=f'OPD - {Notification.Type(notification_type).label}',
            message=message,
            from_email=None,
            recipient_list=[recipient.email],
            fail_silently=True,  # mail failure must not kill the booking; retries land in 18e
        )
    return notification
