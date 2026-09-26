from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet, availability, create_public_appointment, lookup_appointment, schedule_date

router = DefaultRouter()
router.register('admin/appointments', AppointmentViewSet, basename='admin-appointments')

urlpatterns = [
    path('availability/', availability),
    path('appointments/', create_public_appointment),
    path('appointments/lookup/<str:reference>/', lookup_appointment),
    path('admin/schedule/', schedule_date),
    path('', include(router.urls)),
]
