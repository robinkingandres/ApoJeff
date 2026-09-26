from django.db import IntegrityError, transaction
from .emailing import send_appointment_email
from .models import ACTIVE_STATUSES, Appointment, Patient, ScheduleDate, SlotCapacity


class SlotUnavailable(Exception):
    pass


def create_appointment(data):
    with transaction.atomic():
        schedule, _ = ScheduleDate.objects.get_or_create(appointment_date=data['appointment_date'])
        schedule = ScheduleDate.objects.select_for_update().get(pk=schedule.pk)
        if not schedule.is_open:
            raise SlotUnavailable(schedule.note or 'Appointments are closed for this date.')
        patient = Patient.objects.create(
            full_name=data['full_name'], email=data['email'], contact_number=data['contact_number'],
            address=data['address'], age=data['age'], gender=data['gender'],
        )
        queue_number = Appointment.objects.filter(appointment_date=data['appointment_date']).count() + 1
        appointment = Appointment.objects.create(
            reference_number=f"APPT-{data['appointment_date']:%m%d}-{queue_number:02d}", patient=patient,
            appointment_date=data['appointment_date'],
            additional_names=data.get('additional_names', []),
        )
    try:
        send_appointment_email(appointment)
    except Exception:
        pass
    return appointment
