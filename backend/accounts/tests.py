from django.contrib.auth import get_user_model
from django.test import TestCase

from booking.models import Booking
from transporters.models import TransportPricing


User = get_user_model()


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone_number="0700000100",
            email="admin@example.com",
            password="StrongPass123",
            first_name="Admin",
            last_name="User",
            role="farmer",
            is_staff=True,
        )
        self.farmer = User.objects.create_user(
            phone_number="0700000101",
            email="farmer2@example.com",
            password="StrongPass123",
            first_name="Farm",
            last_name="Owner",
            role="farmer",
        )

    def test_staff_user_can_view_admin_dashboard(self):
        TransportPricing.objects.update_or_create(vehicle_type="pickup", defaults={"price_per_km": "200.00"})
        Booking.objects.create(
            farmer=self.farmer,
            produce_name="Tomatoes",
            produce_description="Fresh",
            weight_kg="500.00",
            pickup_address="Farm Gate",
            pickup_latitude="-1.292100",
            pickup_longitude="36.821900",
            dropoff_address="Market",
            dropoff_latitude="-1.300000",
            dropoff_longitude="36.800000",
            search_radius_km="20.00",
            estimated_distance_km="10.00",
            vehicle_type_required="pickup",
            quoted_price="2000.00",
            status="delivered",
        )

        self.client.force_login(self.admin)
        response = self.client.get("/accounts/admin-dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System admin dashboard")
        self.assertContains(response, "KES 200.00")
        self.assertContains(response, "KES 2000")

    def test_non_staff_user_cannot_view_admin_dashboard(self):
        self.client.force_login(self.farmer)
        response = self.client.get("/accounts/admin-dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_update_transport_rates_from_dashboard(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            "/accounts/admin-dashboard/",
            {
                "motorbike": "120.00",
                "pickup": "220.00",
                "van": "275.00",
                "truck": "360.00",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transport rates updated.")
        self.assertContains(response, "KES 220.00")
        self.assertEqual(
            str(TransportPricing.objects.get(vehicle_type="pickup").price_per_km),
            "220.00",
        )


class CustomUserAuthTests(TestCase):
    def test_create_superuser_sets_admin_permissions_and_role(self):
        admin = User.objects.create_superuser(
            phone_number="0700000199",
            email="root@example.com",
            password="StrongPass123",
            first_name="Root",
            last_name="Admin",
        )

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)
        self.assertEqual(admin.role, "admin")

    def test_staff_admin_can_login_and_reach_dashboard(self):
        admin = User.objects.create_superuser(
            phone_number="0700000200",
            email="adminlogin@example.com",
            password="StrongPass123",
            first_name="Login",
            last_name="Admin",
        )

        login_ok = self.client.login(username="0700000200", password="StrongPass123")
        self.assertTrue(login_ok)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System admin dashboard")
