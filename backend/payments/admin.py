from django.contrib import admin

from .models import Payment, PaymentStatusHistory, TransporterPayout


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "booking",
        "farmer",
        "transporter",
        "amount_kes",
        "phone_number",
        "status",
        "mpesa_receipt_number",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "booking__id",
        "farmer__phone_number",
        "transporter__phone_number",
        "phone_number",
        "merchant_request_id",
        "checkout_request_id",
        "mpesa_receipt_number",
    )
    readonly_fields = ("raw_callback_payload", "created_at", "updated_at", "held_at", "released_at")


@admin.register(TransporterPayout)
class TransporterPayoutAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "transporter", "amount_kes", "status", "released_at")
    list_filter = ("status", "released_at")
    search_fields = ("booking__id", "transporter__phone_number", "payment__mpesa_receipt_number")


@admin.register(PaymentStatusHistory)
class PaymentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("payment", "status", "notes", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("payment__booking__id", "payment__farmer__phone_number", "payment__checkout_request_id")
    readonly_fields = ("payload",)

