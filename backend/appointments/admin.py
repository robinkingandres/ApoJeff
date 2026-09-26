from django.contrib import admin
from .models import Appointment, EmailEvent, Patient, ScheduleDate, SlotCapacity

admin.site.register(Patient)
admin.site.register(SlotCapacity)
admin.site.register(ScheduleDate)
admin.site.register(EmailEvent)

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'patient', 'appointment_date', 'appointment_time', 'status', 'confirmation_sent_at', 'reminder_sent_at')
    list_filter = ('status', 'appointment_date', 'appointment_time')
    search_fields = ('reference_number', 'patient__full_name', 'patient__email')
