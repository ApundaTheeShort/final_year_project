from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


User = get_user_model()


class TransporterApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.driver = User.objects.create_user(
            phone_number="0700000001",
            email="driver@example.com",
            password="StrongPass123",
            first_name="Drive",
            last_name="One",
            role="driver",
        )

    def test_driver_can_create_profile_and_vehicle(self):
        self.client.force_authenticate(self.driver)
        response = self.client.post(
            "/api/transporters/me/",
            {
                "profile": {
                    "company_name": "Fast Wheels",
                    "current_latitude": "-1.292100",
                    "current_longitude": "36.821900",
                },
                "vehicles": [
                    {
                        "registration_number": "KDA123A",
                        "vehicle_type": "pickup",
                        "capacity_kg": "1500.00",
                        "is_available": True,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["profile"]["company_name"], "Fast Wheels")
        self.assertEqual(len(response.data["vehicles"]), 1)
        self.assertNotIn("price_per_km", response.data["vehicles"][0])

    def test_driver_can_update_existing_vehicle_setup(self):
        self.client.force_authenticate(self.driver)
        create_response = self.client.post(
            "/api/transporters/me/",
            {
                "profile": {
                    "company_name": "Fast Wheels",
                    "current_latitude": "-1.292100",
                    "current_longitude": "36.821900",
                },
                "vehicles": [
                    {
                        "registration_number": "KDA123A",
                        "vehicle_type": "pickup",
                        "capacity_kg": "1500.00",
                        "is_available": False,
                    }
                ],
            },
            format="json",
        )
        vehicle_id = create_response.data["vehicles"][0]["id"]

        update_response = self.client.post(
            "/api/transporters/me/",
            {
                "profile": {
                    "company_name": "Fast Wheels",
                    "current_latitude": "-1.292100",
                    "current_longitude": "36.821900",
                },
                "vehicles": [
                    {
                        "id": vehicle_id,
                        "registration_number": "KDA123A",
                        "vehicle_type": "pickup",
                        "capacity_kg": "1500.00",
                        "is_available": True,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(len(update_response.data["vehicles"]), 1)
        self.assertEqual(update_response.data["vehicles"][0]["id"], vehicle_id)
        self.assertTrue(update_response.data["vehicles"][0]["is_available"])
