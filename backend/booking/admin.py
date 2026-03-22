from django.contrib import admin

from .models import Booking, BookingStatusHistory, TrackingUpdate


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "farmer", "transporter", "produce_name", "weight_kg", "vehicle_type_required", "status")
    list_filter = ("status", "vehicle_type_required")
    search_fields = ("produce_name", "pickup_address", "dropoff_address", "farmer__phone_number")


@admin.register(BookingStatusHistory)
class BookingStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("booking", "status", "created_by", "created_at")
    list_filter = ("status",)


@admin.register(TrackingUpdate)
class TrackingUpdateAdmin(admin.ModelAdmin):
    list_display = ("booking", "transporter", "latitude", "longitude", "speed_kph", "created_at")
