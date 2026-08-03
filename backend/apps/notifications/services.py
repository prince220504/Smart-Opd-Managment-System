from .models import Notification
from .tasks import send_notification_email
import logging
from kombu.exceptions import OperationalError

logger = logging.getLogger(__name__)

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
    if email:
        try:
            send_notification_email.delay(notification.id)
        except OperationalError:
            logger.exception('Could not queue email for notification %s', notification.id)
    return notification
