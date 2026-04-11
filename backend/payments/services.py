import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from booking.models import Booking, BookingPaymentStatus, BookingStatus

from .models import Payment, PaymentStatus, PaymentStatusHistory, PayoutStatus, TransporterPayout
from .utils import DarajaError, daraja_password, daraja_timestamp, format_kenyan_phone_number, parse_callback_payload, post_daraja_json


logger = logging.getLogger(__name__)


def _record_history(payment, status, notes="", payload=None):
    PaymentStatusHistory.objects.create(
        payment=payment,
        status=status,
        notes=notes,
        payload=payload,
    )


def _sync_payment_parties(payment):
    updates = []
    if payment.transporter_id != payment.booking.transporter_id:
        payment.transporter = payment.booking.transporter
        updates.append("transporter")
    if updates:
        payment.save(update_fields=[*updates, "updated_at"])


def _sync_payout_party(booking):
    if not hasattr(booking, "payment"):
        return None
    payout, _ = TransporterPayout.objects.get_or_create(
        booking=booking,
        defaults={
            "transporter": booking.transporter,
            "amount_kes": booking.quoted_price,
            "payment": booking.payment,
            "status": PayoutStatus.PENDING_RELEASE,
            "notes": "Payout pending delivery completion.",
        },
    )
    changed_fields = []
    if payout.payment_id != booking.payment.id:
        payout.payment = booking.payment
        changed_fields.append("payment")
    if payout.transporter_id != booking.transporter_id:
        payout.transporter = booking.transporter
        changed_fields.append("transporter")
    if payout.amount_kes != booking.quoted_price:
        payout.amount_kes = booking.quoted_price
        changed_fields.append("amount_kes")
    if changed_fields:
        payout.save(update_fields=[*changed_fields, "updated_at"])
    return payout


def initiate_booking_payment(booking, phone_number, user):
    if booking.farmer_id != user.id:
        raise DarajaError("You can only pay for your own booking.")
    if booking.status == BookingStatus.CANCELLED:
        raise DarajaError("This booking has been cancelled and can no longer be paid for.")
    if booking.quoted_price is None:
        raise DarajaError("This booking is not ready for payment yet.")
    if hasattr(booking, "payment") and booking.payment.status in {PaymentStatus.PAID_HELD, PaymentStatus.RELEASED}:
        raise DarajaError("This booking has already been paid for.")
    if hasattr(booking, "payment") and booking.payment.status in {PaymentStatus.PENDING, PaymentStatus.STK_PUSH_SENT}:
        raise DarajaError("A payment request is already in progress. Check your phone to complete it.")

    normalized_phone = format_kenyan_phone_number(phone_number)
    timestamp = daraja_timestamp()
    amount = int(Decimal(str(booking.quoted_price)).quantize(Decimal("1")))

    logger.info("Initiating STK push for booking %s", booking.id)
    daraja_response = post_daraja_json(
        "/mpesa/stkpush/v1/processrequest",
        {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": daraja_password(timestamp),
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": normalized_phone,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": normalized_phone,
            "CallBackURL": settings.MPESA_CALLBACK_URL,
            "AccountReference": f"Booking-{booking.id}",
            "TransactionDesc": f"Payment for booking {booking.id}",
        },
    )

    with transaction.atomic():
        payment, _ = Payment.objects.update_or_create(
            booking=booking,
            defaults={
                "farmer": booking.farmer,
                "transporter": booking.transporter,
                "amount_kes": booking.quoted_price,
                "phone_number": normalized_phone,
                "merchant_request_id": daraja_response.get("MerchantRequestID", ""),
                "checkout_request_id": daraja_response.get("CheckoutRequestID", ""),
                "result_desc": daraja_response.get("ResponseDescription", ""),
                "status": PaymentStatus.STK_PUSH_SENT,
            },
        )
        booking.payment_status = BookingPaymentStatus.PENDING
        if booking.status not in {BookingStatus.CONFIRMED, BookingStatus.ACCEPTED, BookingStatus.PICKED_UP, BookingStatus.IN_TRANSIT, BookingStatus.DELIVERED, BookingStatus.COMPLETED}:
            booking.status = BookingStatus.PENDING_PAYMENT
        booking.save(update_fields=["payment_status", "status", "updated_at"])
        _record_history(payment, PaymentStatus.STK_PUSH_SENT, "STK push sent to customer phone.", daraja_response)
    return payment, daraja_response


def confirm_successful_payment(payment, callback_data, raw_payload):
    if payment.status in {PaymentStatus.PAID_HELD, PaymentStatus.RELEASED}:
        return payment

    if Decimal(str(callback_data.get("amount") or "0")).quantize(Decimal("0.01")) != payment.amount_kes:
        raise DarajaError("We could not confirm this payment amount. Please contact support.")

    booking = payment.booking
    payment.mpesa_receipt_number = callback_data.get("mpesa_receipt_number", "")
    payment.transaction_date = callback_data.get("transaction_date")
    payment.result_code = callback_data.get("result_code")
    payment.result_desc = callback_data.get("result_desc", "")
    payment.phone_number = callback_data.get("phone_number") or payment.phone_number
    payment.raw_callback_payload = raw_payload
    payment.status = PaymentStatus.PAID_HELD
    payment.held_at = timezone.now()
    _sync_payment_parties(payment)
    payment.save()

    booking.payment_status = BookingPaymentStatus.PAID
    if booking.status == BookingStatus.PENDING_PAYMENT:
        booking.status = BookingStatus.CONFIRMED
    booking.save(update_fields=["payment_status", "status", "updated_at"])
    payout = _sync_payout_party(booking)
    if payout and payout.status == PayoutStatus.FAILED:
        payout.status = PayoutStatus.PENDING_RELEASE
        payout.notes = "Payout reset to pending release after payment success."
        payout.save(update_fields=["status", "notes", "updated_at"])
    _record_history(payment, PaymentStatus.PAID_HELD, "Payment confirmed and held in application escrow.", raw_payload)
    logger.info("Payment %s confirmed for booking %s", payment.id, booking.id)
    return payment


def fail_payment(payment, callback_data, raw_payload, status_value=PaymentStatus.FAILED):
    if payment.status in {PaymentStatus.PAID_HELD, PaymentStatus.RELEASED}:
        return payment
    payment.result_code = callback_data.get("result_code")
    payment.result_desc = callback_data.get("result_desc", "")
    payment.raw_callback_payload = raw_payload
    payment.status = status_value
    payment.save(update_fields=["result_code", "result_desc", "raw_callback_payload", "status", "updated_at"])
    booking = payment.booking
    booking.payment_status = BookingPaymentStatus.UNPAID
    if booking.status == BookingStatus.PENDING_PAYMENT:
        booking.save(update_fields=["payment_status", "updated_at"])
    else:
        booking.save(update_fields=["payment_status", "status", "updated_at"])
    _record_history(payment, status_value, payment.result_desc or "Payment failed.", raw_payload)
    logger.info("Payment %s failed for booking %s", payment.id, booking.id)
    return payment


def handle_mpesa_callback(payload):
    callback_data = parse_callback_payload(payload)
    payment = Payment.objects.filter(
        checkout_request_id=callback_data["checkout_request_id"]
    ).first() or Payment.objects.filter(
        merchant_request_id=callback_data["merchant_request_id"]
    ).first()
    if payment is None:
        logger.warning("Received callback for unknown payment: %s", callback_data)
        raise DarajaError("We could not match this payment to a booking. Please contact support if money was deducted.")

    logger.info("Received Daraja callback for payment %s", payment.id)
    payment.raw_callback_payload = payload
    payment.result_code = callback_data.get("result_code")
    payment.result_desc = callback_data.get("result_desc", "")
    payment.save(update_fields=["raw_callback_payload", "result_code", "result_desc", "updated_at"])

    if callback_data.get("result_code") == 0:
        return confirm_successful_payment(payment, callback_data, payload)
    status_value = PaymentStatus.CANCELLED if callback_data.get("result_code") == 1032 else PaymentStatus.FAILED
    return fail_payment(payment, callback_data, payload, status_value=status_value)


def release_payment_to_transporter(booking):
    if booking.status != BookingStatus.DELIVERED:
        raise DarajaError("This payment can only be completed after delivery is confirmed.")
    if not hasattr(booking, "payment"):
        raise DarajaError("This booking does not have a payment record yet.")
    payment = booking.payment
    if payment.status != PaymentStatus.PAID_HELD:
        raise DarajaError("This payment is not ready to be completed yet.")

    payout = _sync_payout_party(booking)
    with transaction.atomic():
        _sync_payment_parties(payment)
        payment.status = PaymentStatus.RELEASED
        payment.released_at = timezone.now()
        payment.save(update_fields=["transporter", "status", "released_at", "updated_at"])

        payout.status = PayoutStatus.RELEASED
        payout.released_at = timezone.now()
        payout.notes = "Application escrow released after delivery confirmation."
        payout.save(update_fields=["transporter", "status", "released_at", "notes", "updated_at"])

        _record_history(payment, PaymentStatus.RELEASED, "Held payment released to transporter in system records.")
    logger.info("Released payment %s for booking %s", payment.id, booking.id)
    return payout


def maybe_auto_release_on_delivery(booking):
    if booking.status != BookingStatus.DELIVERED or not hasattr(booking, "payment"):
        return None
    payment = booking.payment
    if payment.status != PaymentStatus.PAID_HELD:
        return None
    return release_payment_to_transporter(booking)
