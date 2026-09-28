from datetime import timedelta
from django.utils import timezone


def next_appointment_date():
    return timezone.localdate() + timedelta(days=1)


def booking_error(appointment_date):
    today = timezone.localdate()
    if today.weekday() == 6:
        return 'Bookings are closed on Sundays. Please return on Monday to book for Tuesday.'
    if appointment_date != today + timedelta(days=1):
        return 'Appointments can only be booked for tomorrow.'
    return ''
