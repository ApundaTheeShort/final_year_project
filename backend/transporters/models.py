from decimal import Decimal
from django.utils.text import slugify

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class VehicleType(models.TextChoices):
    MOTORBIKE = "motorbike", "Motorbike"
    VAN = "van", "Van"
    PICKUP = "pickup", "Pickup"
    TRUCK = "truck", "Truck"


DEFAULT_TRANSPORT_RULES = {
    VehicleType.MOTORBIKE: {
        "price_per_km": Decimal("100.00"),
        "min_weight_kg": Decimal("0.00"),
        "max_weight_kg": Decimal("200.00"),
    },
    VehicleType.VAN: {
        "price_per_km": Decimal("250.00"),
        "min_weight_kg": Decimal("200.00"),
        "max_weight_kg": Decimal("1000.00"),
    },
    VehicleType.PICKUP: {
        "price_per_km": Decimal("200.00"),
        "min_weight_kg": Decimal("1000.00"),
        "max_weight_kg": Decimal("3000.00"),
    },
    VehicleType.TRUCK: {
        "price_per_km": Decimal("350.00"),
        "min_weight_kg": Decimal("10000.00"),
        "max_weight_kg": Decimal("30000.00"),
    },
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
    vehicle_type = models.CharField(max_length=50)
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

    def get_vehicle_type_display(self):
        return format_vehicle_type_label(self.vehicle_type)


class TransportPricing(models.Model):
    vehicle_type = models.CharField(max_length=50, unique=True)
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2)
    min_weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    max_weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["vehicle_type"]
        verbose_name = "Transport pricing"
        verbose_name_plural = "Transport pricing"

    def __str__(self):
        return f"{self.get_vehicle_type_display()} - {self.price_per_km}/km"

    def clean(self):
        self.vehicle_type = normalize_vehicle_type_key(self.vehicle_type)
        if self.max_weight_kg <= self.min_weight_kg:
            raise ValidationError("Maximum weight must be greater than minimum weight.")
        overlapping = TransportPricing.objects.exclude(pk=self.pk).filter(
            min_weight_kg__lt=self.max_weight_kg,
            max_weight_kg__gt=self.min_weight_kg,
        )
        if overlapping.exists():
            raise ValidationError("Vehicle weight bands cannot overlap.")

    def get_vehicle_type_display(self):
        return format_vehicle_type_label(self.vehicle_type)


def get_transport_rule(vehicle_type):
    pricing = TransportPricing.objects.filter(vehicle_type=vehicle_type).first()
    if pricing:
        return {
            "vehicle_type": vehicle_type,
            "price_per_km": pricing.price_per_km,
            "min_weight_kg": pricing.min_weight_kg,
            "max_weight_kg": pricing.max_weight_kg,
        }
    defaults = DEFAULT_TRANSPORT_RULES[vehicle_type]
    return {
        "vehicle_type": vehicle_type,
        "price_per_km": defaults["price_per_km"],
        "min_weight_kg": defaults["min_weight_kg"],
        "max_weight_kg": defaults["max_weight_kg"],
    }


def get_price_per_km(vehicle_type):
    return get_transport_rule(vehicle_type)["price_per_km"]


def normalize_vehicle_type_key(value):
    normalized = slugify(str(value or "")).replace("-", "_")
    if not normalized:
        raise ValidationError("Enter a valid vehicle type name.")
    return normalized


def format_vehicle_type_label(vehicle_type):
    return str(vehicle_type or "").replace("_", " ").title()


def get_transport_rules():
    configured_rules = list(TransportPricing.objects.order_by("min_weight_kg", "vehicle_type"))
    if configured_rules:
        return configured_rules

    class DefaultRule:
        def __init__(self, vehicle_type, data):
            self.vehicle_type = vehicle_type
            self.price_per_km = data["price_per_km"]
            self.min_weight_kg = data["min_weight_kg"]
            self.max_weight_kg = data["max_weight_kg"]

        def get_vehicle_type_display(self):
            return format_vehicle_type_label(self.vehicle_type)

    return [DefaultRule(vehicle_type, data) for vehicle_type, data in DEFAULT_TRANSPORT_RULES.items()]


def resolve_vehicle_type_for_weight(weight_kg):
    weight = Decimal(str(weight_kg))
    for rule in get_transport_rules():
        min_weight = Decimal(str(rule.min_weight_kg))
        max_weight = Decimal(str(rule.max_weight_kg))
        if weight > min_weight and weight <= max_weight:
            return rule.vehicle_type
    raise ValidationError(
        "No vehicle class is configured for this load weight. Ask the system admin to update the booking weight ranges."
    )
