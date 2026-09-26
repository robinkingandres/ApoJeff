from datetime import date, time, timedelta
from django.core import mail
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from .emailing import send_appointment_email
from .models import Appointment, EmailEvent, ScheduleDate


class AppointmentCapacityTests(APITestCase):
    def test_date_accepts_multiple_bookings_without_time_capacity(self):
        appointment_date = self._future_open_date(2)
        payload = {
            'full_name': 'Test Patient', 'email': 'patient@example.com', 'contact_number': '09123456789',
            'address': 'Test address', 'age': 32, 'gender': 'prefer_not',
            'appointment_date': appointment_date.isoformat(),
        }
        for booking_number in range(11):
            response = self.client.post('/api/appointments/', payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, booking_number)
        self.assertEqual(Appointment.objects.filter(appointment_date=appointment_date).count(), 11)

    def test_availability_reports_full_slot(self):
        appointment_date = self._future_open_date(2)
        Appointment.objects.create(
            reference_number='APPT-TEST-1',
            patient_id=self._make_patient(),
            appointment_date=appointment_date,
            appointment_time=time(8),
        )
        response = self.client.get('/api/availability/', {'date': appointment_date.isoformat()})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_open'], True)

    def test_closed_date_rejects_public_booking(self):
        appointment_date = date.today() + timedelta(days=3)
        ScheduleDate.objects.create(appointment_date=appointment_date, is_open=False, note='Provider unavailable')
        payload = {
            'full_name': 'Closed Date Patient', 'email': 'patient@example.com', 'contact_number': '09123456789',
            'address': 'Test address', 'age': 32, 'gender': 'prefer_not',
            'appointment_date': appointment_date.isoformat(), 'appointment_time': '10:00',
        }
        response = self.client.post('/api/appointments/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_monday_rejects_public_booking(self):
        appointment_date = date.today() + timedelta(days=(7 - date.today().weekday()) % 7 or 7)
        payload = {
            'full_name': 'Monday Patient', 'email': 'patient@example.com', 'contact_number': '09123456789',
            'address': 'Test address', 'age': 32, 'gender': 'prefer_not',
            'appointment_date': appointment_date.isoformat(),
        }
        response = self.client.post('/api/appointments/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Mondays', str(response.data))

    def test_group_member_names_are_returned(self):
        appointment_date = date.today() + timedelta(days=4)
        payload = {
            'full_name': 'Group Leader', 'email': 'group@example.com', 'contact_number': '09123456789',
            'address': 'Test address', 'age': 32, 'gender': 'prefer_not',
            'appointment_date': appointment_date.isoformat(), 'additional_names': ['Member One', 'Member Two'],
        }
        response = self.client.post('/api/appointments/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['additional_names'], ['Member One', 'Member Two'])

    def _make_patient(self):
        from .models import Patient
        return Patient.objects.create(full_name='Test', email='test@example.com', contact_number='0', address='x', age=30, gender='other').pk

    def _future_open_date(self, days):
        appointment_date = date.today() + timedelta(days=days)
        while appointment_date.weekday() == 0:
            appointment_date += timedelta(days=1)
        return appointment_date


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AppointmentEmailTests(APITestCase):
    def test_confirmation_is_sent_to_the_registered_email(self):
        appointment = Appointment.objects.create(
            reference_number='APPT-TEST-EMAIL',
            patient_id=self._make_patient(),
            appointment_date=date.today() + timedelta(days=2),
        )

        send_appointment_email(appointment)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
        self.assertIn('successfully scheduled', mail.outbox[0].body)
        self.assertIn('To be confirmed', mail.outbox[0].body)
        appointment.refresh_from_db()
        self.assertIsNotNone(appointment.confirmation_sent_at)
        self.assertTrue(EmailEvent.objects.filter(appointment=appointment, event_type='confirmation').exists())

    def _make_patient(self):
        from .models import Patient
        return Patient.objects.create(
            full_name='Email Test', email='test@example.com', contact_number='0',
            address='x', age=30, gender='other',
        ).pk
