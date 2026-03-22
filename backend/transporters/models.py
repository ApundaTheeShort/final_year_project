from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class VehicleType(models.TextChoices):
    MOTORBIKE = "motorbike", "Motorbike"
    PICKUP = "pickup", "Pickup"
    VAN = "van", "Van"
    TRUCK = "truck", "Truck"


VEHICLE_WEIGHT_RULES = (
    (VehicleType.MOTORBIKE, Decimal("50")),
    (VehicleType.PICKUP, Decimal("1000")),
    (VehicleType.VAN, Decimal("3000")),
    (VehicleType.TRUCK, Decimal("100000")),
)

DEFAULT_TRANSPORT_PRICING = {
    VehicleType.MOTORBIKE: Decimal("100.00"),
    VehicleType.PICKUP: Decimal("200.00"),
    VehicleType.VAN: Decimal("250.00"),
    VehicleType.TRUCK: Decimal("350.00"),
}


class TransporterProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transporter_profile",
    )
    company_name = models.CharField(max_length=255, blank=True)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.user.role != "driver":
            raise ValidationError("Only users with the driver role can have transporter profiles.")

    def __str__(self):
        return self.company_name or f"Transporter {self.user_id}"


class Vehicle(models.Model):
    transporter = models.ForeignKey(
        TransporterProfile,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    registration_number = models.CharField(max_length=50, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices)
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["registration_number"]

    def clean(self):
        if self.transporter.user.role != "driver":
            raise ValidationError("Vehicles must belong to a driver account.")

    def __str__(self):
        return f"{self.registration_number} ({self.vehicle_type})"

    def can_carry(self, weight_kg):
        return self.capacity_kg >= Decimal(str(weight_kg))


class TransportPricing(models.Model):
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices, unique=True)
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["vehicle_type"]
        verbose_name = "Transport pricing"
        verbose_name_plural = "Transport pricing"

    def __str__(self):
        return f"{self.get_vehicle_type_display()} - {self.price_per_km}/km"


def get_price_per_km(vehicle_type):
    pricing = TransportPricing.objects.filter(vehicle_type=vehicle_type).first()
    if pricing:
        return pricing.price_per_km
    return DEFAULT_TRANSPORT_PRICING[vehicle_type]
