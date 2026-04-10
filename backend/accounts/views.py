from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse, reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.views.generic import CreateView, View
from django.views.generic.base import TemplateView
from django.contrib.auth.views import LoginView

from booking.models import Booking, BookingStatus
from transporters.models import DEFAULT_TRANSPORT_PRICING, TransportPricing, VehicleType

from .forms import (
    AuthenticationForm,
    CustomUserCreationForm,
    ProfileAccountForm,
    ResendVerificationForm,
    TransportRateForm,
)
from .utils import send_verification_email


User = get_user_model()


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/home.html'

    def get_template_names(self):
        if self.request.user.is_staff:
            return ["accounts/admin_dashboard.html"]
        role_templates = {
            "farmer": "farmers/dashboard.html",
            "driver": "transporters/dashboard.html",
        }
        return [role_templates.get(self.request.user.role, self.template_name)]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile_form"] = ProfileAccountForm(instance=self.request.user)
        if self.request.user.is_staff:
            context.update(AdminDashboardView.build_dashboard_context(rate_form=TransportRateForm()))
        return context


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "accounts/admin_dashboard.html"
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff

    @classmethod
    def build_dashboard_context(cls, rate_form=None, profile_form=None):
        zero_amount = Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
        rates_by_type = {
            item.vehicle_type: item.price_per_km
            for item in TransportPricing.objects.all()
        }
        current_rates = [
            {
                "vehicle_type": vehicle_type,
                "label": VehicleType(vehicle_type).label,
                "price_per_km": rates_by_type.get(vehicle_type, DEFAULT_TRANSPORT_PRICING[vehicle_type]),
            }
            for vehicle_type, _ in VehicleType.choices
        ]

        booking_summary = Booking.objects.aggregate(
            total_bookings=Count("id"),
            active_bookings=Count("id", filter=Q(status__in=[
                BookingStatus.PENDING,
                BookingStatus.ACCEPTED,
                BookingStatus.PICKED_UP,
                BookingStatus.IN_TRANSIT,
            ])),
            delivered_bookings=Count("id", filter=Q(status=BookingStatus.DELIVERED)),
            total_revenue=Coalesce(Sum("quoted_price"), zero_amount),
            delivered_revenue=Coalesce(Sum("quoted_price", filter=Q(status=BookingStatus.DELIVERED)), zero_amount),
            active_revenue=Coalesce(Sum("quoted_price", filter=Q(status__in=[
                BookingStatus.ACCEPTED,
                BookingStatus.PICKED_UP,
                BookingStatus.IN_TRANSIT,
            ])), zero_amount),
        )
        bookings_by_vehicle = list(
            Booking.objects.values("vehicle_type_required")
            .annotate(
                bookings=Count("id"),
                revenue=Coalesce(Sum("quoted_price"), zero_amount),
            )
            .order_by("vehicle_type_required")
        )
        all_bookings = (
            Booking.objects.select_related("farmer", "transporter", "vehicle")
            .order_by("-created_at")
        )
        active_deliveries = all_bookings.filter(
            status__in=[
                BookingStatus.ACCEPTED,
                BookingStatus.PICKED_UP,
                BookingStatus.IN_TRANSIT,
            ]
        )

        return {
            "current_rates": current_rates,
            "booking_summary": booking_summary,
            "bookings_by_vehicle": bookings_by_vehicle,
            "rate_form": rate_form or TransportRateForm(),
            "all_bookings": all_bookings,
            "active_deliveries": active_deliveries,
            "booking_status_choices": BookingStatus.choices,
            "profile_form": profile_form or ProfileAccountForm(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.build_dashboard_context(profile_form=ProfileAccountForm(instance=self.request.user)))
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        if action == "update-booking-status":
            return self.handle_booking_status_update(request)
        if action == "delete-booking":
            return self.handle_booking_delete(request)

        form = TransportRateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Transport rates updated.")
            return redirect("admin-dashboard")

        context = self.get_context_data(**kwargs)
        context.update(
            self.build_dashboard_context(
                rate_form=form,
                profile_form=ProfileAccountForm(instance=request.user),
            )
        )
        return self.render_to_response(context)

    def handle_booking_status_update(self, request):
        booking = get_object_or_404(Booking, id=request.POST.get("booking_id"))
        new_status = request.POST.get("status", "")
        valid_statuses = {choice for choice, _ in BookingStatus.choices}
        if new_status not in valid_statuses:
            messages.error(request, "Select a valid booking status.")
            return redirect("admin-dashboard")

        booking.status = new_status
        if new_status == BookingStatus.DELIVERED and not booking.delivered_at:
            from django.utils import timezone
            booking.delivered_at = timezone.now()
        booking.save(update_fields=["status", "delivered_at", "updated_at"])
        messages.success(request, f"Booking #{booking.id} updated to {booking.get_status_display()}.")
        return redirect("admin-dashboard")

    def handle_booking_delete(self, request):
        booking = get_object_or_404(Booking, id=request.POST.get("booking_id"))
        booking_id = booking.id
        booking.delete()
        messages.success(request, f"Booking #{booking_id} deleted.")
        return redirect("admin-dashboard")


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        send_verification_email(self.request, self.object)
        messages.success(self.request, "Account created. Check your email to verify your address before signing in.")
        return response

    def get_success_url(self):
        return reverse("verification-sent")


class CustomLoginView(LoginView):
    authentication_form = AuthenticationForm
    template_name = 'registration/login.html'


class ProfileUpdateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        previous_email = user.email
        form = ProfileAccountForm(request.POST, instance=request.user)
        redirect_to = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse_lazy("home")
        if not url_has_allowed_host_and_scheme(
            redirect_to,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            redirect_to = reverse_lazy("home")
        if form.is_valid():
            updated_user = form.save()
            if previous_email != updated_user.email and not updated_user.is_staff:
                updated_user.is_email_verified = False
                updated_user.email_verified_at = None
                updated_user.save(update_fields=["is_email_verified", "email_verified_at"])
                send_verification_email(request, updated_user)
                messages.success(request, "Profile updated. Verify your new email address from the inbox link.")
                return redirect("verification-sent")
            messages.success(request, "Profile updated.")
        else:
            for errors in form.errors.values():
                if errors:
                    messages.error(request, errors[0])
                    break
        return redirect(redirect_to)


class VerificationSentView(TemplateView):
    template_name = "registration/verification_sent.html"


class VerifyEmailView(View):
    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user and default_token_generator.check_token(user, token):
            if not user.is_email_verified:
                user.is_email_verified = True
                user.email_verified_at = timezone.now()
                user.save(update_fields=["is_email_verified", "email_verified_at"])
            messages.success(request, "Email verified. You can now sign in.")
            return redirect("login")

        messages.error(request, "That verification link is invalid or has expired.")
        return redirect("resend-verification")


class ResendVerificationView(View):
    template_name = "registration/resend_verification.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"form": ResendVerificationForm()})

    def post(self, request, *args, **kwargs):
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            send_verification_email(request, form.user)
            messages.success(request, "A new verification email has been sent.")
            return redirect("verification-sent")
        return render(request, self.template_name, {"form": form})
