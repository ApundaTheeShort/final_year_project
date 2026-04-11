import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from booking.models import Booking, BookingPaymentStatus, BookingStatus
from payments.models import PaymentStatus, PayoutStatus
from transporters.models import TransportPricing


User = get_user_model()


@override_settings(
    MPESA_ENV="sandbox",
    MPESA_CONSUMER_KEY="key",
    MPESA_CONSUMER_SECRET="secret",
    MPESA_SHORTCODE="174379",
    MPESA_PASSKEY="passkey",
    MPESA_CALLBACK_URL="https://example.com/api/payments/mpesa/callback/",
)
class PaymentFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.farmer = User.objects.create_user(
            phone_number="0701000001",
            email="payfarmer@example.com",
            password="StrongPass123",
            first_name="Pay",
            last_name="Farmer",
            role="farmer",
            is_email_verified=True,
        )
        self.driver = User.objects.create_user(
            phone_number="0701000002",
            email="paydriver@example.com",
            password="StrongPass123",
            first_name="Pay",
            last_name="Driver",
            role="driver",
            is_email_verified=True,
        )
        TransportPricing.objects.update_or_create(vehicle_type="pickup", defaults={"price_per_km": "200.00"})
        self.booking = Booking.objects.create(
            farmer=self.farmer,
            produce_name="Tomatoes",
            produce_description="Fresh",
            weight_kg="800.00",
            pickup_address="Farm Gate",
            pickup_latitude="-1.292100",
            pickup_longitude="36.821900",
            dropoff_address="City Market",
            dropoff_latitude="-1.300000",
            dropoff_longitude="36.800000",
            search_radius_km="50.00",
            estimated_distance_km="12.40",
            estimated_duration_minutes="21.00",
            route_geometry={"type": "LineString", "coordinates": [[36.8219, -1.2921], [36.8, -1.3]]},
            vehicle_type_required="pickup",
            quoted_price="2480.00",
            status=BookingStatus.PENDING_PAYMENT,
            payment_status=BookingPaymentStatus.UNPAID,
        )

    @patch("payments.services.post_daraja_json")
    def test_farmer_can_initiate_stk_push_and_callback_holds_payment(self, mocked_stk):
        mocked_stk.return_value = {
            "MerchantRequestID": "merchant-1",
            "CheckoutRequestID": "checkout-1",
            "ResponseDescription": "Success. Request accepted for processing",
        }
        self.client.force_authenticate(self.farmer)
        response = self.client.post(
            "/api/payments/stk-push/",
            {"booking_id": self.booking.id, "phone_number": "0712345678"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, BookingStatus.PENDING_PAYMENT)
        self.assertEqual(self.booking.payment_status, BookingPaymentStatus.PENDING)
        payment = self.booking.payment
        self.assertEqual(payment.status, PaymentStatus.STK_PUSH_SENT)

        callback_payload = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "merchant-1",
                    "CheckoutRequestID": "checkout-1",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 2480},
                            {"Name": "MpesaReceiptNumber", "Value": "R123XYZ"},
                            {"Name": "TransactionDate", "Value": 20260411100533},
                            {"Name": "PhoneNumber", "Value": 254712345678},
                        ]
                    },
                }
            }
        }
        callback_response = self.client.post(
            "/api/payments/mpesa/callback/",
            data=json.dumps(callback_payload),
            content_type="application/json",
        )
        self.assertEqual(callback_response.status_code, 200)

        self.booking.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(self.booking.status, BookingStatus.CONFIRMED)
        self.assertEqual(self.booking.payment_status, BookingPaymentStatus.PAID)
        self.assertEqual(payment.status, PaymentStatus.PAID_HELD)
        self.assertEqual(payment.mpesa_receipt_number, "R123XYZ")
        self.assertEqual(payment.payout.status, PayoutStatus.PENDING_RELEASE)

    @patch("payments.services.post_daraja_json")
    def test_delivery_releases_held_payment(self, mocked_stk):
        mocked_stk.return_value = {
            "MerchantRequestID": "merchant-2",
            "CheckoutRequestID": "checkout-2",
            "ResponseDescription": "Success. Request accepted for processing",
        }
        self.client.force_authenticate(self.farmer)
        self.client.post(
            "/api/payments/stk-push/",
            {"booking_id": self.booking.id, "phone_number": "0712345678"},
            format="json",
        )
        self.client.post(
            "/api/payments/mpesa/callback/",
            data=json.dumps(
                {
                    "Body": {
                        "stkCallback": {
                            "MerchantRequestID": "merchant-2",
                            "CheckoutRequestID": "checkout-2",
                            "ResultCode": 0,
                            "ResultDesc": "Success",
                            "CallbackMetadata": {
                                "Item": [
                                    {"Name": "Amount", "Value": 2480},
                                    {"Name": "MpesaReceiptNumber", "Value": "R321XYZ"},
                                    {"Name": "TransactionDate", "Value": 20260411100533},
                                    {"Name": "PhoneNumber", "Value": 254712345678},
                                ]
                            },
                        }
                    }
                }
            ),
            content_type="application/json",
        )

        self.booking.transporter = self.driver
        self.booking.status = BookingStatus.DELIVERED
        self.booking.save()

        self.booking.refresh_from_db()
        payment = self.booking.payment
        payment.refresh_from_db()
        payout = self.booking.payout
        payout.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.RELEASED)
        self.assertEqual(payout.status, PayoutStatus.RELEASED)
        self.assertIsNotNone(payout.released_at)

