from datetime import time
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


TIME_SLOTS = [time(hour, 0) for hour in range(8, 21)]
ACTIVE_STATUSES = ('pending', 'confirmed')


class Patient(models.Model):
    GENDER_CHOICES = [('female', 'Female'), ('male', 'Male'), ('other', 'Other'), ('prefer_not', 'Prefer not to say')]
    full_name = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    contact_number = models.CharField(max_length=40, blank=True)
    address = models.TextField()
    age = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(120)], null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SlotCapacity(models.Model):
    appointment_date = models.DateField()
    appointment_time = models.TimeField(choices=[(slot, slot.strftime('%I:%M %p')) for slot in TIME_SLOTS], null=True, blank=True)
    capacity = models.PositiveSmallIntegerField(default=10)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['appointment_date', 'appointment_time'], name='unique_date_time_capacity')]


class ScheduleDate(models.Model):
    appointment_date = models.DateField(unique=True)
    last_queue_number = models.PositiveIntegerField(default=0)
    is_open = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['appointment_date']


class Appointment(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('confirmed', 'Confirmed'), ('completed', 'Completed'), ('cancelled', 'Cancelled')]
    reference_number = models.CharField(max_length=24, unique=True, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField(choices=[(slot, slot.strftime('%I:%M %p')) for slot in TIME_SLOTS], null=True, blank=True)
    additional_names = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)
    confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['appointment_date', 'appointment_time', 'status'])]


class EmailEvent(models.Model):
    EVENT_TYPES = [('confirmation', 'Confirmation'), ('reminder', 'Reminder')]
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='email_events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    sent_at = models.DateTimeField(auto_now_add=True)
    delivery_status = models.CharField(max_length=30, default='sent')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['appointment', 'event_type'], name='unique_appointment_email_event')]
