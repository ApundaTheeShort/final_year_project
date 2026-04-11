from django.urls import path

from .views import BookingPaymentStatusView, MpesaCallbackView, PaymentDetailView, StkPushInitiateView


urlpatterns = [
    path("stk-push/", StkPushInitiateView.as_view(), name="payment-stk-push"),
    path("mpesa/callback/", MpesaCallbackView.as_view(), name="payment-mpesa-callback"),
    path("<int:pk>/", PaymentDetailView.as_view(), name="payment-detail"),
    path("bookings/<int:booking_id>/status/", BookingPaymentStatusView.as_view(), name="booking-payment-status"),
]

