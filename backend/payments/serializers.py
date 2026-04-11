from rest_framework import serializers

from booking.models import Booking, BookingPaymentStatus, BookingStatus

from .models import Payment, PaymentStatus, PaymentStatusHistory, TransporterPayout
from .services import DarajaError, handle_mpesa_callback, initiate_booking_payment, release_payment_to_transporter
from .utils import format_kenyan_phone_number


class PaymentStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentStatusHistory
        fields = ("id", "status", "notes", "created_at")


class TransporterPayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransporterPayout
        fields = ("id", "amount_kes", "status", "released_at", "notes")


class PaymentDetailSerializer(serializers.ModelSerializer):
    payout = TransporterPayoutSerializer(read_only=True)
    status_history = PaymentStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "booking",
            "farmer",
            "transporter",
            "amount_kes",
            "phone_number",
            "merchant_request_id",
            "checkout_request_id",
            "mpesa_receipt_number",
            "transaction_date",
            "result_code",
            "result_desc",
            "status",
            "held_at",
            "released_at",
            "created_at",
            "updated_at",
            "payout",
            "status_history",
        )


class StkPushRequestSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        try:
            return format_kenyan_phone_number(value)
        except DarajaError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs):
        request = self.context["request"]
        try:
            booking = Booking.objects.get(id=attrs["booking_id"], farmer=request.user)
        except Booking.DoesNotExist as exc:
            raise serializers.ValidationError({"booking_id": "We could not find that booking."}) from exc
        if booking.status == BookingStatus.CANCELLED:
            raise serializers.ValidationError("This booking has been cancelled and can no longer be paid for.")
        if booking.payment_status == BookingPaymentStatus.PAID:
            raise serializers.ValidationError("This booking has already been paid for.")
        attrs["booking"] = booking
        return attrs

    def create(self, validated_data):
        try:
            payment, daraja_response = initiate_booking_payment(
                validated_data["booking"],
                validated_data["phone_number"],
                self.context["request"].user,
            )
        except DarajaError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        self._daraja_response = daraja_response
        return payment

    @property
    def daraja_response(self):
        return getattr(self, "_daraja_response", {})


class MpesaCallbackSerializer(serializers.Serializer):
    payload = serializers.JSONField()

    def create(self, validated_data):
        try:
            return handle_mpesa_callback(validated_data["payload"])
        except DarajaError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class BookingPaymentStatusSerializer(serializers.ModelSerializer):
    payment = PaymentDetailSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = ("id", "status", "payment_status", "quoted_price", "payment")


class ReleasePaymentSerializer(serializers.Serializer):
    def save(self, **kwargs):
        booking = self.context["booking"]
        try:
            return release_payment_to_transporter(booking)
        except DarajaError as exc:
            raise serializers.ValidationError(str(exc)) from exc
