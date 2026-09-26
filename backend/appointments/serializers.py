from django.utils import timezone
from rest_framework import serializers
from .models import Appointment, Patient, SlotCapacity, TIME_SLOTS


class AvailabilitySerializer(serializers.Serializer):
    date = serializers.DateField()
    slots = serializers.ListField()


class AppointmentSerializer(serializers.ModelSerializer):
    patient = serializers.SerializerMethodField()
    appointment_time = serializers.TimeField(format='%H:%M')
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'reference_number', 'patient', 'additional_names', 'appointment_date', 'appointment_time', 'status', 'status_label', 'created_at', 'confirmation_sent_at', 'reminder_sent_at']

    def get_patient(self, obj):
        return {
            'full_name': obj.patient.full_name,
            'email': obj.patient.email,
            'contact_number': obj.patient.contact_number,
            'address': obj.patient.address,
            'age': obj.patient.age,
            'gender': obj.patient.gender,
        }


class AppointmentCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160)
    email = serializers.EmailField()
    contact_number = serializers.CharField(max_length=40)
    address = serializers.CharField()
    age = serializers.IntegerField(min_value=1, max_value=120)
    gender = serializers.ChoiceField(choices=Patient.GENDER_CHOICES)
    appointment_date = serializers.DateField()
    additional_names = serializers.ListField(child=serializers.CharField(max_length=160), required=False, allow_empty=True)

    def validate_appointment_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError('Appointments must be scheduled for today or a future date.')
        if value.weekday() == 0:
            raise serializers.ValidationError('Appointments are unavailable on Mondays. Please select Tuesday through Sunday.')
        return value


class StatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['confirmed', 'completed', 'cancelled', 'pending'])
