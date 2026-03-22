from django.urls import path

from .views import DriverLocationUpdateView, DriverVehicleSetupView


urlpatterns = [
    path("me/", DriverVehicleSetupView.as_view(), name="driver-vehicle-setup"),
    path("me/location/", DriverLocationUpdateView.as_view(), name="driver-location-update"),
]
