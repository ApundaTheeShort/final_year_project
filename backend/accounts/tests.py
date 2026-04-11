from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

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
        self.assertContains(response, "System Administration")
        self.assertContains(response, "KES 200.00")
        self.assertContains(response, "KES 2000")
        self.assertContains(response, "All Bookings")
        self.assertContains(response, "Active Deliveries")

    def test_non_staff_user_cannot_view_admin_dashboard(self):
        self.client.force_login(self.farmer)
        response = self.client.get("/accounts/admin-dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_update_transport_rates_from_dashboard(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            "/accounts/admin-dashboard/",
            {
                "action": "update-rates",
                "motorbike": "120.00",
                "pickup": "220.00",
                "van": "275.00",
                "truck": "360.00",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transport rates have been updated.")
        self.assertContains(response, "KES 220.00")
        self.assertEqual(
            str(TransportPricing.objects.get(vehicle_type="pickup").price_per_km),
            "220.00",
        )

    def test_staff_user_can_update_booking_status_from_dashboard(self):
        booking = Booking.objects.create(
            farmer=self.farmer,
            produce_name="Maize",
            produce_description="Dry",
            weight_kg="300.00",
            pickup_address="Farm Gate",
            pickup_latitude="-1.292100",
            pickup_longitude="36.821900",
            dropoff_address="Warehouse",
            dropoff_latitude="-1.300000",
            dropoff_longitude="36.800000",
            search_radius_km="20.00",
            estimated_distance_km="10.00",
            vehicle_type_required="pickup",
            quoted_price="2000.00",
            status="accepted",
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            "/accounts/admin-dashboard/",
            {
                "action": "update-booking-status",
                "booking_id": booking.id,
                "status": "delivered",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "delivered")
        self.assertIsNotNone(booking.delivered_at)
        self.assertContains(response, f"Booking #{booking.id} has been updated to Delivered.")

    def test_staff_user_can_delete_booking_from_dashboard(self):
        booking = Booking.objects.create(
            farmer=self.farmer,
            produce_name="Beans",
            produce_description="Bagged",
            weight_kg="120.00",
            pickup_address="Farm Gate",
            pickup_latitude="-1.292100",
            pickup_longitude="36.821900",
            dropoff_address="Depot",
            dropoff_latitude="-1.300000",
            dropoff_longitude="36.800000",
            search_radius_km="20.00",
            estimated_distance_km="10.00",
            vehicle_type_required="pickup",
            quoted_price="2000.00",
            status="confirmed",
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            "/accounts/admin-dashboard/",
            {
                "action": "delete-booking",
                "booking_id": booking.id,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.filter(id=booking.id).exists())
        self.assertContains(response, f"Booking #{booking.id} has been deleted.")


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
        self.assertTrue(admin.is_email_verified)

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
        self.assertContains(response, "System Administration")

    def test_logged_in_user_can_update_account_details_from_dashboard_form(self):
        user = User.objects.create_user(
            phone_number="0700000201",
            email="farmername@example.com",
            password="StrongPass123",
            first_name="Old",
            last_name="Name",
            role="farmer",
        )
        self.client.force_login(user)

        response = self.client.post(
            "/accounts/profile/",
            {
                "first_name": "New",
                "last_name": "Farmer",
                "phone_number": "0700000999",
                "email": "newfarmer@example.com",
                "next": "/",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "Farmer")
        self.assertEqual(user.phone_number, "0700000999")
        self.assertEqual(user.email, "newfarmer@example.com")
        self.assertContains(response, "Your profile has been updated.")

    def test_profile_update_rejects_duplicate_phone_or_email(self):
        user = User.objects.create_user(
            phone_number="0700000201",
            email="farmername@example.com",
            password="StrongPass123",
            first_name="Old",
            last_name="Name",
            role="farmer",
        )
        User.objects.create_user(
            phone_number="0700000202",
            email="taken@example.com",
            password="StrongPass123",
            first_name="Taken",
            last_name="User",
            role="farmer",
        )
        self.client.force_login(user)

        response = self.client.post(
            "/accounts/profile/",
            {
                "first_name": "Old",
                "last_name": "Name",
                "phone_number": "0700000202",
                "email": "taken@example.com",
                "next": "/",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.phone_number, "0700000201")
        self.assertEqual(user.email, "farmername@example.com")
        self.assertContains(response, "That phone number is already linked to another account.")

    def test_profile_update_requires_login(self):
        response = self.client.post("/accounts/profile/", {"first_name": "Nope", "last_name": "User"})
        self.assertEqual(response.status_code, 302)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailVerificationFlowTests(TestCase):
    def test_signup_sends_verification_email_and_redirects(self):
        response = self.client.post(
            "/accounts/signup/",
            {
                "phone_number": "0700000300",
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "role": "farmer",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verify your email")
        user = User.objects.get(phone_number="0700000300")
        self.assertFalse(user.is_email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/verify-email/", mail.outbox[0].body)

    def test_unverified_non_staff_user_cannot_sign_in(self):
        User.objects.create_user(
            phone_number="0700000301",
            email="pending@example.com",
            password="StrongPass123",
            first_name="Pending",
            last_name="User",
            role="farmer",
        )

        response = self.client.post(
            "/accounts/login/",
            {"username": "0700000301", "password": "StrongPass123"},
            follow=True,
        )

        self.assertContains(response, "Verify your email address before signing in.")

    def test_verification_link_marks_user_verified(self):
        user = User.objects.create_user(
            phone_number="0700000302",
            email="verifyme@example.com",
            password="StrongPass123",
            first_name="Verify",
            last_name="Me",
            role="farmer",
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.get(reverse("verify-email", kwargs={"uidb64": uid, "token": token}), follow=True)

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        self.assertIsNotNone(user.email_verified_at)
        self.assertContains(response, "Your email has been verified. You can now sign in.")

    def test_resend_verification_sends_new_email(self):
        User.objects.create_user(
            phone_number="0700000303",
            email="resend@example.com",
            password="StrongPass123",
            first_name="Resend",
            last_name="User",
            role="driver",
        )

        response = self.client.post(
            reverse("resend-verification"),
            {"email": "resend@example.com"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verify your email")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("resend@example.com", mail.outbox[0].to)

    def test_email_change_requires_reverification_and_sends_email(self):
        user = User.objects.create_user(
            phone_number="0700000304",
            email="verified@example.com",
            password="StrongPass123",
            first_name="Verified",
            last_name="User",
            role="farmer",
            is_email_verified=True,
        )
        self.client.force_login(user)

        response = self.client.post(
            "/accounts/profile/",
            {
                "first_name": "Verified",
                "last_name": "User",
                "phone_number": "0700000304",
                "email": "changed@example.com",
                "next": "/",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.email, "changed@example.com")
        self.assertFalse(user.is_email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("changed@example.com", mail.outbox[0].to)
        self.assertContains(response, "Verify your email")
