from django.contrib import admin

from .models import TransportPricing, TransporterProfile, Vehicle


@admin.register(TransporterProfile)
class TransporterProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "current_latitude", "current_longitude", "last_location_update")
    search_fields = ("user__phone_number", "user__email", "company_name")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("registration_number", "vehicle_type", "capacity_kg", "is_available", "transporter")
    list_filter = ("vehicle_type", "is_available")
    search_fields = ("registration_number", "transporter__user__phone_number", "transporter__company_name")


@admin.register(TransportPricing)
class TransportPricingAdmin(admin.ModelAdmin):
    list_display = ("vehicle_type", "price_per_km", "updated_at")
    list_filter = ("vehicle_type",)
