from django.urls import path

from .views import PlaceLookupView, PlaceSearchView, ReverseGeocodeView, RoutePreviewView


urlpatterns = [
    path("places/search/", PlaceSearchView.as_view(), name="map-place-search"),
    path("places/lookup/", PlaceLookupView.as_view(), name="map-place-lookup"),
    path("places/reverse/", ReverseGeocodeView.as_view(), name="map-place-reverse"),
    path("routes/preview/", RoutePreviewView.as_view(), name="map-route-preview"),
]
