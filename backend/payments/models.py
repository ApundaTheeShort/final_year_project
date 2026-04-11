from django.conf import settings
from django.db import models


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    STK_PUSH_SENT = "stk_push_sent", "STK Push Sent"
    PAID_HELD = "paid_held", "Paid Held"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"
    RELEASED = "released", "Released"


class PayoutStatus(models.TextChoices):
    PENDING_RELEASE = "pending_release", "Pending Release"
    RELEASED = "released", "Released"
    FAILED = "failed", "Failed"


class Payment(models.Model):
    booking = models.OneToOneField("booking.Booking", on_delete=models.CASCADE, related_name="payment")
    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments_made",
    )
    transporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments_received",
    )
    amount_kes = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=20)
    merchant_request_id = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, db_index=True)
    mpesa_receipt_number = models.CharField(max_length=100, blank=True)
    transaction_date = models.DateTimeField(null=True, blank=True)
    result_code = models.IntegerField(null=True, blank=True)
    result_desc = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    raw_callback_payload = models.JSONField(null=True, blank=True)
    held_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.id} for booking {self.booking_id}"


class TransporterPayout(models.Model):
    booking = models.OneToOneField("booking.Booking", on_delete=models.CASCADE, related_name="payout")
    transporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payouts",
    )
    amount_kes = models.DecimalField(max_digits=10, decimal_places=2)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="payout")
    status = models.CharField(max_length=20, choices=PayoutStatus.choices, default=PayoutStatus.PENDING_RELEASE)
    released_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payout {self.id} for booking {self.booking_id}"


class PaymentStatusHistory(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=20, choices=PaymentStatus.choices)
    notes = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.payment_id} - {self.status}"

