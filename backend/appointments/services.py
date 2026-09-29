from django.db import IntegrityError, transaction
from .emailing import send_appointment_email
from .booking import booking_error
from .models import ACTIVE_STATUSES, Appointment, Patient, ScheduleDate, SlotCapacity


class SlotUnavailable(Exception):
    pass


def create_appointment(data):
    error = booking_error(data['appointment_date'])
    if error:
        raise SlotUnavailable(error)
    with transaction.atomic():
        schedule, _ = ScheduleDate.objects.get_or_create(appointment_date=data['appointment_date'])
        schedule = ScheduleDate.objects.select_for_update().get(pk=schedule.pk)
        if not schedule.is_open:
            raise SlotUnavailable(schedule.note or 'Appointments are closed for this date.')
        patient = Patient.objects.create(
            full_name=data['full_name'], email=data.get('email', ''), contact_number=data.get('contact_number', ''),
            address=data['address'], age=data.get('age'), gender=data.get('gender', ''),
        )
        queue_number = schedule.last_queue_number + 1
        prefix = f"APPT-{data['appointment_date']:%m%d}-"
        while Appointment.objects.filter(reference_number=f'{prefix}{queue_number:02d}').exists():
            queue_number += 1
        schedule.last_queue_number = queue_number
        schedule.save(update_fields=['last_queue_number'])
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
