from django.contrib import messages
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import CreateView
from django.views.generic.base import TemplateView
from django.contrib.auth.views import LoginView

from booking.models import Booking, BookingStatus
from transporters.models import DEFAULT_TRANSPORT_PRICING, TransportPricing, VehicleType

from .forms import AuthenticationForm, CustomUserCreationForm, TransportRateForm


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
        if self.request.user.is_staff:
            context.update(AdminDashboardView.build_dashboard_context(rate_form=TransportRateForm()))
        return context


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "accounts/admin_dashboard.html"
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff

    @classmethod
    def build_dashboard_context(cls, rate_form=None):
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

        return {
            "current_rates": current_rates,
            "booking_summary": booking_summary,
            "bookings_by_vehicle": bookings_by_vehicle,
            "rate_form": rate_form or TransportRateForm(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.build_dashboard_context())
        return context

    def post(self, request, *args, **kwargs):
        form = TransportRateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Transport rates updated.")
            return redirect("admin-dashboard")

        context = self.get_context_data(**kwargs)
        context.update(self.build_dashboard_context(rate_form=form))
        return self.render_to_response(context)


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'accounts/signup.html'


class CustomLoginView(LoginView):
    authentication_form = AuthenticationForm
    template_name = 'registration/login.html'
