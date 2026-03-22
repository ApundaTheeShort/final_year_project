from rest_framework import permissions, response, serializers
from rest_framework.views import APIView

from .serializers import MapPlaceSelectionSerializer, RoutePreviewSerializer
from .services import get_route_details, lookup_place, reverse_geocode, search_places


class PlaceSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            raise serializers.ValidationError({"q": "This query parameter is required."})

        limit = min(int(request.query_params.get("limit", 5)), 10)
        results = search_places(query, limit=limit)
        return response.Response({"results": MapPlaceSelectionSerializer(results, many=True).data})


class PlaceLookupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        osm_type = request.query_params.get("osm_type", "").strip()
        osm_id = request.query_params.get("osm_id", "").strip()
        if not osm_type or not osm_id:
            raise serializers.ValidationError({"detail": "osm_type and osm_id are required."})

        place = lookup_place(osm_type, osm_id)
        return response.Response(MapPlaceSelectionSerializer(place).data)


class ReverseGeocodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        latitude = request.query_params.get("latitude", "").strip()
        longitude = request.query_params.get("longitude", "").strip()
        if not latitude or not longitude:
            raise serializers.ValidationError({"detail": "latitude and longitude are required."})

        place = reverse_geocode(latitude, longitude)
        return response.Response(MapPlaceSelectionSerializer(place).data)


class RoutePreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = RoutePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pickup = serializer.validated_data["pickup_place"]
        dropoff = serializer.validated_data["dropoff_place"]
        route = get_route_details(
            pickup["latitude"],
            pickup["longitude"],
            dropoff["latitude"],
            dropoff["longitude"],
        )
        return response.Response(
            {
                "pickup_place": pickup,
                "dropoff_place": dropoff,
                "distance_km": route["distance_km"],
                "duration_minutes": route["duration_minutes"],
                "geometry": route["geometry"],
            }
        )
