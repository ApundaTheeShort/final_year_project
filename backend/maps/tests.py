from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


User = get_user_model()


class MapsApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone_number="0700000099",
            email="maps@example.com",
            password="StrongPass123",
            first_name="Map",
            last_name="User",
            role="farmer",
        )
        self.client.force_authenticate(self.user)

    @patch("maps.views.search_places")
    def test_place_search_returns_results(self, mocked_search):
        mocked_search.return_value = [
            {
                "place_id": "123",
                "source": "nominatim",
                "osm_type": "W",
                "osm_id": "456",
                "name": "City Market",
                "address": "City Market, Nairobi",
                "latitude": "-1.286389",
                "longitude": "36.817223",
            }
        ]
        response = self.client.get("/api/maps/places/search/?q=City%20Market")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

    @patch("maps.views.reverse_geocode")
    def test_reverse_geocode_returns_selected_map_point(self, mocked_reverse):
        mocked_reverse.return_value = {
            "place_id": "999",
            "source": "nominatim",
            "osm_type": "N",
            "osm_id": "12345",
            "name": "Pinned Farm",
            "address": "Pinned Farm, Kiambu",
            "latitude": "-1.250000",
            "longitude": "36.700000",
        }
        response = self.client.get("/api/maps/places/reverse/?latitude=-1.25&longitude=36.7")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Pinned Farm")

    @patch("maps.views.get_route_details")
    def test_route_preview_uses_selected_places(self, mocked_route):
        mocked_route.return_value = {
            "distance_km": "12.40",
            "duration_minutes": "21.00",
            "geometry": {"type": "LineString", "coordinates": [[36.8, -1.29], [36.81, -1.30]]},
        }
        response = self.client.post(
            "/api/maps/routes/preview/",
            {
                "pickup_place": {
                    "place_id": "1",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "11",
                    "name": "Farm Gate",
                    "address": "Farm Gate, Kiambu",
                    "latitude": "-1.292100",
                    "longitude": "36.821900",
                },
                "dropoff_place": {
                    "place_id": "2",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "22",
                    "name": "Market",
                    "address": "Market, Nairobi",
                    "latitude": "-1.300000",
                    "longitude": "36.800000",
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["distance_km"], "12.40")
