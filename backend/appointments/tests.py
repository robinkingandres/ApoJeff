from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from unittest.mock import patch
from django.utils import timezone
from django.core import mail
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from .emailing import send_appointment_email
from .models import Appointment, EmailEvent, ScheduleDate


class AppointmentCapacityTests(APITestCase):
    def test_date_accepts_multiple_bookings_without_time_capacity(self):
        appointment_date = timezone.localdate()
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
        appointment_date = timezone.localdate()
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
        appointment_date = timezone.localdate()
        ScheduleDate.objects.create(appointment_date=appointment_date, is_open=False, note='Provider unavailable')
        payload = {
            'full_name': 'Closed Date Patient', 'email': 'patient@example.com', 'contact_number': '09123456789',
            'address': 'Test address', 'age': 32, 'gender': 'prefer_not',
            'appointment_date': appointment_date.isoformat(), 'appointment_time': '10:00',
        }
        response = self.client.post('/api/appointments/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    @patch('django.utils.timezone.now', return_value=datetime(2026, 9, 27, 17, tzinfo=dt_timezone.utc))
    def test_default_booking_uses_manila_date_and_allows_monday(self, mock_now):
        response = self.client.post('/api/appointments/', {
            'full_name': 'Monday Patient', 'address': 'Test address',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['appointment_date'], '2026-09-28')
        self.assertEqual(Appointment.objects.get().appointment_date, date(2026, 9, 28))
        availability = self.client.get('/api/availability/')
        self.assertTrue(availability.data['is_open'])
        self.assertEqual(availability.data['booked_count'], 1)
        queue = self.client.get('/api/queue/')
        self.assertEqual(str(queue.data['date']), '2026-09-28')
        self.assertEqual(queue.data['queue'][0]['reference_number'], response.data['reference_number'])

    def test_other_dates_reject_public_booking(self):
        for offset in (-1, 1):
            with self.subTest(offset=offset):
                selected = (timezone.localdate() + timedelta(days=offset)).isoformat()
                response = self.client.post('/api/appointments/', {
                    'full_name': 'Other Date Patient', 'address': 'Test address',
                    'appointment_date': selected,
                }, format='json')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('only be booked for today', str(response.data))
                self.assertFalse(self.client.get('/api/availability/', {'date': selected}).data['is_open'])
        self.assertFalse(Appointment.objects.exists())

    @patch('django.utils.timezone.now', return_value=datetime(2026, 9, 28, 4, tzinfo=dt_timezone.utc))
    def test_staff_can_close_monday(self, mock_now):
        ScheduleDate.objects.create(appointment_date=timezone.localdate(), is_open=False)
        response = self.client.post('/api/appointments/', {
            'full_name': 'Closed Monday Patient', 'address': 'Test address',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(self.client.get('/api/availability/').data['is_open'])
        self.assertFalse(Appointment.objects.exists())

    def test_reference_numbers_use_a_daily_queue(self):
        appointment_date = timezone.localdate()
        payload = {
            'full_name': 'Queue Patient', 'email': 'patient@example.com', 'contact_number': '09123456789',
            'address': 'Test address', 'age': 32, 'gender': 'prefer_not',
            'appointment_date': appointment_date.isoformat(),
        }
        first = self.client.post('/api/appointments/', payload, format='json')
        second = self.client.post('/api/appointments/', {**payload, 'email': 'second@example.com'}, format='json')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        prefix = appointment_date.strftime('APPT-%m%d-')
        self.assertEqual(first.data['reference_number'], f'{prefix}01')
        self.assertEqual(second.data['reference_number'], f'{prefix}02')

    def test_group_member_names_are_returned(self):
        appointment_date = timezone.localdate()
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


class TodayScheduleTests(APITestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.client.force_authenticate(get_user_model().objects.create_user(username='staff', is_staff=True))

    @patch('django.utils.timezone.now', return_value=datetime(2026, 9, 27, 17, tzinfo=dt_timezone.utc))
    def test_patient_records_only_include_manila_today(self, mock_now):
        from .models import Patient
        patient = Patient.objects.create(full_name='Today Patient', address='Test address')
        for offset in (-1, 0, 1):
            Appointment.objects.create(
                patient=patient, reference_number=f'TEST-{offset}',
                appointment_date=timezone.localdate() + timedelta(days=offset),
            )
        for params in ({}, {'search': 'Today Patient'}):
            response = self.client.get('/api/admin/appointments/', params)
            self.assertEqual(response.status_code, 200)
            self.assertEqual([item['reference_number'] for item in response.data], ['TEST-0'])
            self.assertEqual(response.data[0]['appointment_date'], '2026-09-28')
        response = self.client.get('/api/admin/appointments/', {'date': '2026-09-29'})
        self.assertEqual(response.data, [])

    @patch('django.utils.timezone.now', return_value=datetime(2026, 9, 27, 17, tzinfo=dt_timezone.utc))
    def test_schedule_defaults_to_manila_today_and_controls_bookings(self, mock_now):
        response = self.client.get('/api/admin/schedule/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data['date']), '2026-09-28')
        for is_open in (False, True):
            response = self.client.patch('/api/admin/schedule/', {'is_open': is_open}, format='json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(ScheduleDate.objects.get().is_open, is_open)
            self.assertEqual(self.client.get('/api/availability/').data['is_open'], is_open)

    def test_cannot_control_other_dates(self):
        for offset in (-1, 1):
            selected = (timezone.localdate() + timedelta(days=offset)).isoformat()
            response = self.client.patch('/api/admin/schedule/', {'date': selected, 'is_open': False}, format='json')
            self.assertEqual(response.status_code, 400)
            response = self.client.patch(f'/api/admin/schedule/?date={selected}', {'is_open': False}, format='json')
            self.assertEqual(response.status_code, 400)
        self.assertFalse(ScheduleDate.objects.exists())

    def test_schedule_requires_staff(self):
        self.client.force_authenticate(None)
        response = self.client.patch('/api/admin/schedule/', {'is_open': False}, format='json')
        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(ScheduleDate.objects.exists())


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
