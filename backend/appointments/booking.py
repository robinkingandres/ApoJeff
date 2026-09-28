from datetime import time, timedelta
from django.utils import timezone


def next_appointment_date():
    return timezone.localdate() + timedelta(days=1)


def booking_error(appointment_date):
    now = timezone.localtime()
    today = now.date()
    if today.weekday() == 6:
        return 'Bookings are closed on Sundays. Please return on Monday to book for Tuesday.'
    if not time(6) <= now.time() < time(18):
        return 'Booking hours are 6:00 AM to 6:00 PM, Monday through Saturday (Manila time).'
    if appointment_date != today + timedelta(days=1):
        return 'Appointments can only be booked for tomorrow.'
    return ''
