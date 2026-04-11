import json

from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions, response, status
from rest_framework.views import APIView

from booking.models import Booking
from booking.permissions import IsFarmer

from .models import Payment
from .serializers import (
    BookingPaymentStatusSerializer,
    MpesaCallbackSerializer,
    PaymentDetailSerializer,
    StkPushRequestSerializer,
)
from .utils import suggested_public_callback_url


class StkPushInitiateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsFarmer]

    def post(self, request):
        serializer = StkPushRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        callback_hint = suggested_public_callback_url()
        return response.Response(
            {
                "payment": PaymentDetailSerializer(payment).data,
                "daraja": serializer.daraja_response,
                "message": "STK push sent. Complete payment on your phone.",
                "callback_url_hint": callback_hint or None,
            },
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name="dispatch")
class MpesaCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else json.loads(request.body.decode("utf-8") or "{}")
        serializer = MpesaCallbackSerializer(data={"payload": payload})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        return response.Response(
            {"ResultCode": 0, "ResultDesc": "Accepted", "payment_id": payment.id},
            status=status.HTTP_200_OK,
        )


class PaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Payment.objects.select_related("booking", "farmer", "transporter", "payout")
        user = self.request.user
        if user.is_staff:
            return queryset
        return queryset.filter(Q(booking__farmer=user) | Q(booking__transporter=user))


class BookingPaymentStatusView(generics.RetrieveAPIView):
    serializer_class = BookingPaymentStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "booking_id"

    def get_queryset(self):
        queryset = Booking.objects.select_related("payment", "payment__payout")
        user = self.request.user
        if user.is_staff:
            return queryset
        return queryset.filter(Q(farmer=user) | Q(transporter=user))
