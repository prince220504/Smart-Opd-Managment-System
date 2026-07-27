from .models import Notification

def notify(recipient, message, notification_type, link=''):
    """Create one in-app notification. Single write path for all triggers."""
    return Notification.objects.create(
        recipient=recipient,
        message=message,
        notification_type=notification_type,
        link=link,
    )