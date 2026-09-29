from django.db import migrations, models


def seed_queue_numbers(apps, schema_editor):
    Appointment = apps.get_model('appointments', 'Appointment')
    ScheduleDate = apps.get_model('appointments', 'ScheduleDate')
    database = schema_editor.connection.alias
    counters = {}
    for appointment_date, reference in Appointment.objects.using(database).values_list('appointment_date', 'reference_number').iterator():
        prefix = f'APPT-{appointment_date:%m%d}-'
        suffix = reference.removeprefix(prefix)
        if reference.startswith(prefix) and suffix.isdigit():
            counters[appointment_date] = max(counters.get(appointment_date, 0), int(suffix))
    for appointment_date, number in counters.items():
        ScheduleDate.objects.using(database).update_or_create(
            appointment_date=appointment_date, defaults={'last_queue_number': number},
        )


class Migration(migrations.Migration):
    dependencies = [('appointments', '0005_optional_patient_contact_fields')]

    operations = [
        migrations.AddField(
            model_name='scheduledate', name='last_queue_number',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(seed_queue_numbers, migrations.RunPython.noop),
    ]
