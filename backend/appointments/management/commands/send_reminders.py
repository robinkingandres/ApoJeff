from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from appointments.emailing import send_appointment_email
from appointments.models import Appointment


class Command(BaseCommand):
    help = 'Send one-day-before reminders for active appointments.'

    def handle(self, *args, **options):
        tomorrow = timezone.localdate() + timedelta(days=1)
        appointments = Appointment.objects.select_related('patient').filter(
            appointment_date=tomorrow,
            status='confirmed',
            reminder_sent_at__isnull=True,
        )
        sent = 0
        for appointment in appointments:
            try:
                send_appointment_email(appointment, reminder=True)
                sent += 1
            except Exception as error:
                self.stderr.write(f'{appointment.reference_number}: {error}')
        self.stdout.write(self.style.SUCCESS(f'Sent {sent} reminder(s).'))
