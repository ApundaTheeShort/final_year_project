from django.urls import path

from .views import (
    BookingCreateView,
    BookingDecisionView,
    BookingDetailView,
    BookingPaymentStatusView,
    BookingStatusUpdateView,
    BookingTrackingView,
    BookingMarkDeliveredView,
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
    path("<int:booking_id>/mark-delivered/", BookingMarkDeliveredView.as_view(), name="booking-mark-delivered"),
    path("<int:booking_id>/tracking/", BookingTrackingView.as_view(), name="booking-tracking"),
    path("<int:booking_id>/payment-status/", BookingPaymentStatusView.as_view(), name="booking-payment-status"),
    path("<int:booking_id>/tracking-updates/", TrackingUpdateView.as_view(), name="booking-tracking-update"),
    path("driver/open/", DriverOpenBookingsView.as_view(), name="driver-open-bookings"),
    path("driver/assigned/", DriverAssignedBookingsView.as_view(), name="driver-assigned-bookings"),
    path("driver/decision/", BookingDecisionView.as_view(), name="booking-decision"),
]
