from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from .models import Appointment, EmailEvent


def send_appointment_email(appointment, reminder=False):
    patient = appointment.patient
    if not patient.email:
        return
    subject = f"Appointment {'Reminder - Tomorrow' if reminder else 'Confirmation'} - {appointment.reference_number}"
    intro = 'This is a reminder that you have an appointment tomorrow.' if reminder else 'Your appointment has been successfully scheduled.'
    formatted_date = appointment.appointment_date.strftime('%B %d, %Y').replace(' 0', ' ')
    formatted_time = appointment.appointment_time.strftime('%I:%M %p') if appointment.appointment_time else 'To be confirmed'
    body = (f"Hello {patient.full_name},\n\n{intro}\n\n"
            f"Reference Number: {appointment.reference_number}\n"
            f"Date: {formatted_date}\n"
            f"Time: {formatted_time}\n"
            f"Status: {appointment.get_status_display()}\n"
            f"Location: {settings.APPOINTMENT_LOCATION}\n\n"
            "Please arrive on time for your scheduled appointment.\n\nThank you.")
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [patient.email], fail_silently=False)
    now = timezone.now()
    field = 'reminder_sent_at' if reminder else 'confirmation_sent_at'
    Appointment.objects.filter(pk=appointment.pk).update(**{field: now})
    EmailEvent.objects.get_or_create(appointment=appointment, event_type='reminder' if reminder else 'confirmation')
