from datetime import datetime
from django.db import IntegrityError, transaction
from django.utils import timezone
from .emailing import send_appointment_email
from .models import ACTIVE_STATUSES, Appointment, Patient, ScheduleDate, SlotCapacity


class SlotUnavailable(Exception):
    pass


def create_appointment(data):
    with transaction.atomic():
        schedule = ScheduleDate.objects.filter(appointment_date=data['appointment_date']).first()
        if schedule and not schedule.is_open:
            raise SlotUnavailable(schedule.note or 'Appointments are closed for this date.')
        patient = Patient.objects.create(
            full_name=data['full_name'], email=data['email'], contact_number=data['contact_number'],
            address=data['address'], age=data['age'], gender=data['gender'],
        )
        appointment = Appointment.objects.create(
            reference_number='TEMP', patient=patient,
            appointment_date=data['appointment_date'],
            additional_names=data.get('additional_names', []),
        )
        appointment.reference_number = f'APPT-{timezone.localdate().year}-{appointment.pk:04d}'
        appointment.save(update_fields=['reference_number'])
    try:
        send_appointment_email(appointment)
    except Exception:
        pass
    return appointment
