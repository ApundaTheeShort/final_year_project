from django.urls import path

from .views import (
    BookingCreateView,
    BookingDecisionView,
    BookingDetailView,
    BookingStatusUpdateView,
    BookingTrackingView,
    DriverOpenBookingsView,
    DriverAssignedBookingsView,
    NearbyTransportersView,
    TrackingUpdateView,
)


urlpatterns = [
    path("", BookingCreateView.as_view(), name="booking-list-create"),
    path("<int:pk>/", BookingDetailView.as_view(), name="booking-detail"),
    path("<int:booking_id>/nearby-transporters/", NearbyTransportersView.as_view(), name="booking-nearby-transporters"),
    path("<int:booking_id>/status/", BookingStatusUpdateView.as_view(), name="booking-status-update"),
    path("<int:booking_id>/tracking/", BookingTrackingView.as_view(), name="booking-tracking"),
    path("<int:booking_id>/tracking-updates/", TrackingUpdateView.as_view(), name="booking-tracking-update"),
    path("driver/open/", DriverOpenBookingsView.as_view(), name="driver-open-bookings"),
    path("driver/assigned/", DriverAssignedBookingsView.as_view(), name="driver-assigned-bookings"),
    path("driver/decision/", BookingDecisionView.as_view(), name="booking-decision"),
]
