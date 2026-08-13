from celery import shared_task
from django.core.mail import send_mail
from .models import Notification
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from apps.appointments.models import Appointment

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

@shared_task
def send_appointment_reminders():
    """Daily: remind patients about tomorrow's appointments."""
    from .services import notify

    tomorrow = timezone.localdate() + timedelta(days=1)
    appointments = Appointment.objects.filter(
        appointment_date=tomorrow,
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
        reminder_sent=False,
    ).select_related('patient', 'doctor')

    sent = 0
    for appt in appointments:
        notify(
            appt.patient,
            f'Reminder: appointment with Dr. {appt.doctor.display_name} tomorrow at {appt.time_slot}.',
            Notification.Type.REMINDER,
            link=reverse('appointments:my_appointments'),
            email=True,
        )
        appt.reminder_sent = True
        appt.save(update_fields=['reminder_sent'])
        sent += 1
    return sent

@shared_task
def expire_stale_appointments():
    """Daily: cancel PENDING appointments whose date has passed. Never touches CONFIRMED."""
    from .services import notify

    stale = Appointment.objects.filter(
        appointment_date__lt=timezone.localdate(),
        status=Appointment.Status.PENDING,
    ).select_related('patient', 'doctor')

    expired = 0
    for appt in stale:
        appt.status = Appointment.Status.CANCELLED
        appt.cancel_reason = 'Auto-cancelled: not confirmed before the appointment date.'
        appt.save(update_fields=['status', 'cancel_reason'])
        notify(
            appt.patient,
            f'Your appointment with Dr. {appt.doctor.display_name} on {appt.appointment_date} was auto-cancelled (never confirmed).',
            Notification.Type.STATUS,
            link=reverse('appointments:my_appointments'),
        )
        expired += 1
    return expired
