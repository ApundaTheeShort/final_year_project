from decimal import Decimal, ROUND_HALF_UP
from math import asin, cos, radians, sin, sqrt

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from transporters.models import VEHICLE_WEIGHT_RULES, Vehicle, VehicleType


def haversine_distance(lat1, lon1, lat2, lon2):
    radius_km = 6371
    delta_lat = radians(float(lat2) - float(lat1))
    delta_lon = radians(float(lon2) - float(lon1))
    lat1 = radians(float(lat1))
    lat2 = radians(float(lat2))

    arc = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return Decimal(str(2 * radius_km * asin(sqrt(arc)))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def determine_vehicle_type(weight_kg):
    weight = Decimal(str(weight_kg))
    for vehicle_type, max_weight in VEHICLE_WEIGHT_RULES:
        if weight <= max_weight:
            return vehicle_type
    return VehicleType.TRUCK


class BookingStatus(models.TextChoices):
    PENDING_PAYMENT = "pending_payment", "Pending Payment"
    CONFIRMED = "confirmed", "Confirmed"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    PICKED_UP = "picked_up", "Picked Up"
    IN_TRANSIT = "in_transit", "In Transit"
    DELIVERED = "delivered", "Delivered"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class BookingPaymentStatus(models.TextChoices):
    UNPAID = "unpaid", "Unpaid"
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"


class Booking(models.Model):
    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    transporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_bookings",
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings",
    )
    produce_name = models.CharField(max_length=255)
    produce_description = models.TextField(blank=True)
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    pickup_place_id = models.CharField(max_length=100, blank=True)
    pickup_place_source = models.CharField(max_length=50, blank=True)
    pickup_address = models.CharField(max_length=255)
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_place_id = models.CharField(max_length=100, blank=True)
    dropoff_place_source = models.CharField(max_length=50, blank=True)
    dropoff_address = models.CharField(max_length=255)
    dropoff_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    search_radius_km = models.DecimalField(max_digits=6, decimal_places=2)
    estimated_distance_km = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    estimated_duration_minutes = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    route_geometry = models.JSONField(null=True, blank=True)
    vehicle_type_required = models.CharField(max_length=20, choices=VehicleType.choices)
    quoted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.PENDING_PAYMENT)
    payment_status = models.CharField(
        max_length=20,
        choices=BookingPaymentStatus.choices,
        default=BookingPaymentStatus.UNPAID,
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        if self.farmer.role != "farmer":
            raise ValidationError("Only farmers can create bookings.")
        if self.transporter and self.transporter.role != "driver":
            raise ValidationError("Assigned transporter must have the driver role.")
        if self.vehicle and not self.vehicle.can_carry(self.weight_kg):
            raise ValidationError("Selected vehicle cannot carry this booking's weight.")
        if self.status in {BookingStatus.CONFIRMED, BookingStatus.ACCEPTED, BookingStatus.PICKED_UP, BookingStatus.IN_TRANSIT, BookingStatus.DELIVERED, BookingStatus.COMPLETED} and self.payment_status != BookingPaymentStatus.PAID:
            raise ValidationError("Confirmed or active bookings must have a successful payment record.")

    def save(self, *args, **kwargs):
        if self.weight_kg and not self.vehicle_type_required:
            self.vehicle_type_required = determine_vehicle_type(self.weight_kg)
        if (
            self.pickup_latitude is not None
            and self.pickup_longitude is not None
            and self.dropoff_latitude is not None
            and self.dropoff_longitude is not None
            and not self.estimated_distance_km
        ):
            self.estimated_distance_km = haversine_distance(
                self.pickup_latitude,
                self.pickup_longitude,
                self.dropoff_latitude,
                self.dropoff_longitude,
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.id} - {self.produce_name}"


class BookingStatusHistory(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=20, choices=BookingStatus.choices)
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_status_updates",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class TrackingUpdate(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="tracking_updates")
    transporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tracking_updates",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    speed_kph = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
