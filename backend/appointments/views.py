from datetime import timedelta
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from .emailing import send_appointment_email
from .booking import booking_error, next_appointment_date
from .models import ACTIVE_STATUSES, Appointment, ScheduleDate, SlotCapacity, TIME_SLOTS
from .serializers import AppointmentCreateSerializer, AppointmentSerializer, StatusUpdateSerializer
from .services import SlotUnavailable, create_appointment


def slot_payload(appointment_date):
    schedule = ScheduleDate.objects.filter(appointment_date=appointment_date).first()
    if schedule and not schedule.is_open:
        return [{'time': slot.strftime('%H:%M'), 'label': slot.strftime('%I:%M %p').lstrip('0'), 'booked': 0, 'capacity': 10, 'available': 0, 'is_full': True} for slot in TIME_SLOTS]
    appointments = Appointment.objects.filter(appointment_date=appointment_date, status__in=ACTIVE_STATUSES)
    counts = {(item['appointment_time'].hour): item['count'] for item in appointments.values('appointment_time').annotate(count=Count('id'))}
    return [{'time': slot.strftime('%H:%M'), 'label': slot.strftime('%I:%M %p').lstrip('0'), 'booked': counts.get(slot.hour, 0), 'capacity': 10, 'available': max(10 - counts.get(slot.hour, 0), 0), 'is_full': counts.get(slot.hour, 0) >= 10} for slot in TIME_SLOTS]


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def availability(request):
    date_text = request.query_params.get('date')
    try:
        selected = timezone.datetime.strptime(date_text, '%Y-%m-%d').date() if date_text else next_appointment_date()
    except ValueError:
        return Response({'detail': 'Use YYYY-MM-DD for date.'}, status=400)
    error = booking_error(selected)
    if error:
        return Response({'date': selected, 'is_open': False, 'note': error, 'booked_count': 0})
    schedule = ScheduleDate.objects.filter(appointment_date=selected).first()
    booked_count = Appointment.objects.filter(appointment_date=selected, status__in=ACTIVE_STATUSES).count()
    return Response({'date': selected, 'is_open': not schedule or schedule.is_open, 'note': schedule.note if schedule else '', 'booked_count': booked_count})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def create_public_appointment(request):
    serializer = AppointmentCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        appointment = create_appointment(serializer.validated_data)
    except SlotUnavailable as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
    return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH'])
@permission_classes([permissions.IsAdminUser])
def schedule_date(request):
    today = next_appointment_date()
    date_text = request.query_params.get('date') or request.data.get('date')
    try:
        selected = timezone.datetime.strptime(date_text, '%Y-%m-%d').date() if date_text else today
    except (TypeError, ValueError):
        return Response({'detail': 'A date in YYYY-MM-DD format is required.'}, status=400)
    if selected != today:
        return Response({'detail': 'Only tomorrow can be opened or closed.'}, status=400)
    if request.method == 'PATCH' and not isinstance(request.data.get('is_open'), bool):
        return Response({'detail': 'is_open must be a boolean.'}, status=400)
    schedule, _ = ScheduleDate.objects.get_or_create(appointment_date=selected)
    if request.method == 'PATCH':
        schedule.is_open = request.data['is_open']
        schedule.save(update_fields=['is_open', 'updated_at'])
    return Response({'date': schedule.appointment_date, 'is_open': schedule.is_open, 'note': schedule.note, 'updated_at': schedule.updated_at})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def lookup_appointment(request, reference):
    try:
        appointment = Appointment.objects.select_related('patient').get(reference_number=reference)
    except Appointment.DoesNotExist:
        return Response({'detail': 'Appointment not found.'}, status=404)
    return Response(AppointmentSerializer(appointment).data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_daily_queue(request):
    date_text = request.query_params.get('date')
    try:
        selected = timezone.datetime.strptime(date_text, '%Y-%m-%d').date() if date_text else timezone.localdate()
    except (TypeError, ValueError):
        return Response({'detail': 'A date in YYYY-MM-DD format is required.'}, status=400)
    appointments = Appointment.objects.filter(
        appointment_date=selected, status__in=ACTIVE_STATUSES
    ).select_related('patient').order_by('created_at', 'id')
    return Response({
        'date': selected,
        'queue': [
            {'queue_position': position, 'booker_name': appointment.patient.full_name,
             'reference_number': appointment.reference_number,
             'additional_names': appointment.additional_names or []}
            for position, appointment in enumerate(appointments, start=1)
        ],
    })


class AppointmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Appointment.objects.select_related('patient').all().order_by('appointment_date', 'appointment_time')

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            queryset = queryset.filter(appointment_date=timezone.localdate()).order_by('created_at', 'id')
        query = self.request.query_params.get('search')
        appointment_status = self.request.query_params.get('status')
        appointment_date = self.request.query_params.get('date')
        if query:
            queryset = queryset.filter(Q(reference_number__icontains=query) | Q(patient__full_name__icontains=query) | Q(patient__email__icontains=query))
        if appointment_status:
            queryset = queryset.filter(status=appointment_status)
        if appointment_date:
            queryset = queryset.filter(appointment_date=appointment_date)
        return queryset

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        appointment = self.get_object()
        serializer = StatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment.status = serializer.validated_data['status']
        appointment.save(update_fields=['status'])
        return Response(self.get_serializer(appointment).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        today = timezone.localdate()
        return Response({
            'today': self.get_queryset().filter(appointment_date=today).count(),
            'upcoming': self.get_queryset().filter(appointment_date__gt=today, status__in=ACTIVE_STATUSES).count(),
            'completed': self.get_queryset().filter(status='completed').count(),
            'cancelled': self.get_queryset().filter(status='cancelled').count(),
        })
