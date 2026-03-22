from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import BookingStatus
from transporters.models import TransportPricing, TransporterProfile, Vehicle


User = get_user_model()


class BookingFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.farmer = User.objects.create_user(
            phone_number="0700000002",
            email="farmer@example.com",
            password="StrongPass123",
            first_name="Farm",
            last_name="Owner",
            role="farmer",
        )
        self.driver = User.objects.create_user(
            phone_number="0700000003",
            email="driver2@example.com",
            password="StrongPass123",
            first_name="Driver",
            last_name="Two",
            role="driver",
        )
        profile = TransporterProfile.objects.create(
            user=self.driver,
            company_name="Village Hauliers",
            current_latitude="-1.292100",
            current_longitude="36.821900",
        )
        self.vehicle = Vehicle.objects.create(
            transporter=profile,
            registration_number="KDB321B",
            vehicle_type="pickup",
            capacity_kg="2000.00",
            is_available=True,
        )
        self.far_driver = User.objects.create_user(
            phone_number="0700000004",
            email="driver3@example.com",
            password="StrongPass123",
            first_name="Driver",
            last_name="Far",
            role="driver",
        )
        far_profile = TransporterProfile.objects.create(
            user=self.far_driver,
            company_name="Regional Hauliers",
            current_latitude="-1.600000",
            current_longitude="36.900000",
        )
        self.far_vehicle = Vehicle.objects.create(
            transporter=far_profile,
            registration_number="KDC999Z",
            vehicle_type="pickup",
            capacity_kg="2500.00",
            is_available=True,
        )
        TransportPricing.objects.update_or_create(
            vehicle_type="pickup",
            defaults={"price_per_km": "200.00"},
        )

    @patch("booking.serializers.get_route_details")
    def test_farmer_booking_matches_driver_and_full_tracking_flow(self, mocked_route):
        mocked_route.return_value = {
            "distance_km": "12.40",
            "duration_minutes": "21.00",
            "geometry": {"type": "LineString", "coordinates": [[36.8219, -1.2921], [36.8, -1.3]]},
        }
        self.client.force_authenticate(self.farmer)
        create_response = self.client.post(
            "/api/bookings/",
            {
                "produce_name": "Tomatoes",
                "produce_description": "Fresh tomatoes",
                "weight_kg": "800.00",
                "pickup_place": {
                    "place_id": "11",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "11",
                    "name": "Farm Gate",
                    "address": "Farm Gate, Kiambu",
                    "latitude": "-1.292100",
                    "longitude": "36.821900",
                },
                "dropoff_place": {
                    "place_id": "22",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "22",
                    "name": "City Market",
                    "address": "City Market, Nairobi",
                    "latitude": "-1.300000",
                    "longitude": "36.800000",
                },
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data["vehicle_type_required"], "pickup")
        self.assertEqual(create_response.data["estimated_distance_km"], "12.40")
        self.assertEqual(create_response.data["search_radius_km"], "50.00")
        self.assertEqual(create_response.data["quoted_price"], "2480.00")
        self.assertEqual(len(create_response.data["matched_transporters"]), 2)
        self.assertEqual(create_response.data["matched_transporters"][0]["estimated_price"], "2480.00")
        booking_id = create_response.data["id"]

        self.client.force_authenticate(self.driver)
        decision_response = self.client.post(
            "/api/bookings/driver/decision/",
            {
                "booking_id": booking_id,
                "vehicle_id": self.vehicle.id,
                "action": "accept",
            },
            format="json",
        )
        self.assertEqual(decision_response.status_code, 200)
        self.assertEqual(decision_response.data["status"], BookingStatus.ACCEPTED)

        self.client.patch(
            "/api/transporters/me/location/",
            {"current_latitude": "-1.292100", "current_longitude": "36.821900"},
            format="json",
        )
        picked_response = self.client.post(
            f"/api/bookings/{booking_id}/status/",
            {"status": BookingStatus.PICKED_UP},
            format="json",
        )
        self.assertEqual(picked_response.status_code, 200)
        self.assertEqual(picked_response.data["status"], BookingStatus.PICKED_UP)

        tracking_response = self.client.post(
            f"/api/bookings/{booking_id}/tracking-updates/",
            {
                "latitude": "-1.295000",
                "longitude": "36.815000",
                "speed_kph": "45.00",
                "notes": "On the main road",
            },
            format="json",
        )
        self.assertEqual(tracking_response.status_code, 201)

        in_transit_response = self.client.get(f"/api/bookings/{booking_id}/tracking/")
        self.assertEqual(in_transit_response.status_code, 200)
        self.assertEqual(in_transit_response.data["status"], BookingStatus.IN_TRANSIT)

        self.client.patch(
            "/api/transporters/me/location/",
            {"current_latitude": "-1.300000", "current_longitude": "36.800000"},
            format="json",
        )
        delivered_response = self.client.post(
            f"/api/bookings/{booking_id}/status/",
            {"status": BookingStatus.DELIVERED},
            format="json",
        )
        self.assertEqual(delivered_response.status_code, 200)
        self.assertEqual(delivered_response.data["status"], BookingStatus.DELIVERED)

        self.client.force_authenticate(self.farmer)
        tracking_view = self.client.get(f"/api/bookings/{booking_id}/tracking/")
        self.assertEqual(tracking_view.status_code, 200)
        self.assertEqual(len(tracking_view.data["tracking_updates"]), 1)
        self.assertEqual(tracking_view.data["status"], BookingStatus.DELIVERED)

    @patch("booking.serializers.get_route_details")
    def test_driver_assigned_bookings_endpoint_returns_accepted_booking(self, mocked_route):
        mocked_route.return_value = {
            "distance_km": "12.40",
            "duration_minutes": "21.00",
            "geometry": {"type": "LineString", "coordinates": [[36.8219, -1.2921], [36.8, -1.3]]},
        }
        self.client.force_authenticate(self.farmer)
        create_response = self.client.post(
            "/api/bookings/",
            {
                "produce_name": "Maize",
                "produce_description": "Dry maize bags",
                "weight_kg": "700.00",
                "pickup_place": {
                    "place_id": "11",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "11",
                    "name": "Farm Gate",
                    "address": "Farm Gate, Kiambu",
                    "latitude": "-1.292100",
                    "longitude": "36.821900",
                },
                "dropoff_place": {
                    "place_id": "22",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "22",
                    "name": "Depot",
                    "address": "Depot, Nairobi",
                    "latitude": "-1.300000",
                    "longitude": "36.800000",
                },
            },
            format="json",
        )
        booking_id = create_response.data["id"]

        self.client.force_authenticate(self.driver)
        accept_response = self.client.post(
            "/api/bookings/driver/decision/",
            {
                "booking_id": booking_id,
                "vehicle_id": self.vehicle.id,
                "action": "accept",
            },
            format="json",
        )
        self.assertEqual(accept_response.status_code, 200)

        assigned_response = self.client.get("/api/bookings/driver/assigned/")
        self.assertEqual(assigned_response.status_code, 200)
        self.assertEqual(len(assigned_response.data), 1)
        self.assertEqual(assigned_response.data[0]["id"], booking_id)
        self.assertEqual(assigned_response.data[0]["status"], BookingStatus.ACCEPTED)

    @patch("booking.serializers.get_route_details")
    def test_farmer_can_delete_pending_booking_but_not_accepted_booking(self, mocked_route):
        mocked_route.return_value = {
            "distance_km": "12.40",
            "duration_minutes": "21.00",
            "geometry": {"type": "LineString", "coordinates": [[36.8219, -1.2921], [36.8, -1.3]]},
        }
        self.client.force_authenticate(self.farmer)
        create_response = self.client.post(
            "/api/bookings/",
            {
                "produce_name": "Beans",
                "produce_description": "Dry beans",
                "weight_kg": "300.00",
                "pickup_place": {
                    "place_id": "11",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "11",
                    "name": "Farm Gate",
                    "address": "Farm Gate, Kiambu",
                    "latitude": "-1.292100",
                    "longitude": "36.821900",
                },
                "dropoff_place": {
                    "place_id": "22",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "22",
                    "name": "Depot",
                    "address": "Depot, Nairobi",
                    "latitude": "-1.300000",
                    "longitude": "36.800000",
                },
            },
            format="json",
        )
        pending_booking_id = create_response.data["id"]

        delete_response = self.client.delete(f"/api/bookings/{pending_booking_id}/")
        self.assertEqual(delete_response.status_code, 204)

        accepted_response = self.client.post(
            "/api/bookings/",
            {
                "produce_name": "Maize",
                "produce_description": "Bagged maize",
                "weight_kg": "700.00",
                "pickup_place": {
                    "place_id": "11",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "11",
                    "name": "Farm Gate",
                    "address": "Farm Gate, Kiambu",
                    "latitude": "-1.292100",
                    "longitude": "36.821900",
                },
                "dropoff_place": {
                    "place_id": "22",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "22",
                    "name": "Depot",
                    "address": "Depot, Nairobi",
                    "latitude": "-1.300000",
                    "longitude": "36.800000",
                },
            },
            format="json",
        )
        accepted_booking_id = accepted_response.data["id"]

        self.client.force_authenticate(self.driver)
        self.client.post(
            "/api/bookings/driver/decision/",
            {
                "booking_id": accepted_booking_id,
                "vehicle_id": self.vehicle.id,
                "action": "accept",
            },
            format="json",
        )

        self.client.force_authenticate(self.farmer)
        blocked_delete_response = self.client.delete(f"/api/bookings/{accepted_booking_id}/")
        self.assertEqual(blocked_delete_response.status_code, 400)

    @patch("booking.serializers.get_route_details")
    def test_multiple_matching_drivers_can_see_same_open_booking(self, mocked_route):
        mocked_route.return_value = {
            "distance_km": "12.40",
            "duration_minutes": "21.00",
            "geometry": {"type": "LineString", "coordinates": [[36.8219, -1.2921], [36.8, -1.3]]},
        }
        self.client.force_authenticate(self.farmer)
        create_response = self.client.post(
            "/api/bookings/",
            {
                "produce_name": "Cabbages",
                "produce_description": "Fresh cabbages",
                "weight_kg": "900.00",
                "pickup_place": {
                    "place_id": "11",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "11",
                    "name": "Farm Gate",
                    "address": "Farm Gate, Kiambu",
                    "latitude": "-1.292100",
                    "longitude": "36.821900",
                },
                "dropoff_place": {
                    "place_id": "22",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "22",
                    "name": "Depot",
                    "address": "Depot, Nairobi",
                    "latitude": "-1.300000",
                    "longitude": "36.800000",
                },
            },
            format="json",
        )
        booking_id = create_response.data["id"]

        self.client.force_authenticate(self.driver)
        near_response = self.client.get("/api/bookings/driver/open/")
        self.assertEqual(near_response.status_code, 200)
        self.assertEqual(len(near_response.data), 1)
        self.assertEqual(near_response.data[0]["id"], booking_id)

        self.client.force_authenticate(self.far_driver)
        far_response = self.client.get("/api/bookings/driver/open/")
        self.assertEqual(far_response.status_code, 200)
        self.assertEqual(len(far_response.data), 1)
        self.assertEqual(far_response.data[0]["id"], booking_id)

    @patch("booking.serializers.get_route_details")
    def test_pickup_and_delivery_require_driver_to_be_within_50_metres_and_in_transit_is_automatic(self, mocked_route):
        mocked_route.return_value = {
            "distance_km": "12.40",
            "duration_minutes": "21.00",
            "geometry": {"type": "LineString", "coordinates": [[36.8219, -1.2921], [36.8, -1.3]]},
        }
        self.client.force_authenticate(self.farmer)
        create_response = self.client.post(
            "/api/bookings/",
            {
                "produce_name": "Onions",
                "produce_description": "Fresh onions",
                "weight_kg": "800.00",
                "pickup_place": {
                    "place_id": "11",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "11",
                    "name": "Farm Gate",
                    "address": "Farm Gate, Kiambu",
                    "latitude": "-1.292100",
                    "longitude": "36.821900",
                },
                "dropoff_place": {
                    "place_id": "22",
                    "source": "nominatim",
                    "osm_type": "W",
                    "osm_id": "22",
                    "name": "City Market",
                    "address": "City Market, Nairobi",
                    "latitude": "-1.300000",
                    "longitude": "36.800000",
                },
            },
            format="json",
        )
        booking_id = create_response.data["id"]

        self.client.force_authenticate(self.driver)
        accept_response = self.client.post(
            "/api/bookings/driver/decision/",
            {
                "booking_id": booking_id,
                "vehicle_id": self.vehicle.id,
                "action": "accept",
            },
            format="json",
        )
        self.assertEqual(accept_response.status_code, 200)

        self.client.patch(
            "/api/transporters/me/location/",
            {"current_latitude": "-1.400000", "current_longitude": "36.900000"},
            format="json",
        )
        far_pickup_response = self.client.post(
            f"/api/bookings/{booking_id}/status/",
            {"status": BookingStatus.PICKED_UP},
            format="json",
        )
        self.assertEqual(far_pickup_response.status_code, 400)

        self.client.patch(
            "/api/transporters/me/location/",
            {"current_latitude": "-1.292100", "current_longitude": "36.821900"},
            format="json",
        )
        pickup_response = self.client.post(
            f"/api/bookings/{booking_id}/status/",
            {"status": BookingStatus.PICKED_UP},
            format="json",
        )
        self.assertEqual(pickup_response.status_code, 200)
        self.assertEqual(pickup_response.data["status"], BookingStatus.PICKED_UP)

        tracking_response = self.client.post(
            f"/api/bookings/{booking_id}/tracking-updates/",
            {
                "latitude": "-1.295500",
                "longitude": "36.815000",
                "speed_kph": "40.00",
                "notes": "Departed farm gate",
            },
            format="json",
        )
        self.assertEqual(tracking_response.status_code, 201)

        tracking_view = self.client.get(f"/api/bookings/{booking_id}/tracking/")
        self.assertEqual(tracking_view.status_code, 200)
        self.assertEqual(tracking_view.data["status"], BookingStatus.IN_TRANSIT)

        blocked_delivery_response = self.client.post(
            f"/api/bookings/{booking_id}/status/",
            {"status": BookingStatus.DELIVERED},
            format="json",
        )
        self.assertEqual(blocked_delivery_response.status_code, 400)

        self.client.patch(
            "/api/transporters/me/location/",
            {"current_latitude": "-1.300000", "current_longitude": "36.800000"},
            format="json",
        )
        delivered_response = self.client.post(
            f"/api/bookings/{booking_id}/status/",
            {"status": BookingStatus.DELIVERED},
            format="json",
        )
        self.assertEqual(delivered_response.status_code, 200)
        self.assertEqual(delivered_response.data["status"], BookingStatus.DELIVERED)
