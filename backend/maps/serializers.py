from rest_framework import serializers


class MapPlaceSelectionSerializer(serializers.Serializer):
    place_id = serializers.CharField(required=False, allow_blank=True)
    source = serializers.CharField(default="nominatim")
    osm_type = serializers.CharField(required=False, allow_blank=True)
    osm_id = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField()
    address = serializers.CharField()
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)


class RoutePreviewSerializer(serializers.Serializer):
    pickup_place = MapPlaceSelectionSerializer()
    dropoff_place = MapPlaceSelectionSerializer()
