from django.contrib import messages
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import CreateView, View
from django.views.generic.base import TemplateView
from django.contrib.auth.views import LoginView

from booking.models import Booking, BookingStatus
from transporters.models import DEFAULT_TRANSPORT_PRICING, TransportPricing, VehicleType

from .forms import AuthenticationForm, CustomUserCreationForm, ProfileAccountForm, TransportRateForm


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
    success_url = reverse_lazy('login')
    template_name = 'accounts/signup.html'


class CustomLoginView(LoginView):
    authentication_form = AuthenticationForm
    template_name = 'registration/login.html'


class ProfileUpdateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = ProfileAccountForm(request.POST, instance=request.user)
        redirect_to = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse_lazy("home")
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
        else:
            for errors in form.errors.values():
                if errors:
                    messages.error(request, errors[0])
                    break
        return redirect(redirect_to)
