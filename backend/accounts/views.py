import csv

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, View
from django.views.generic.base import TemplateView
from django.contrib.auth.views import LoginView

from booking.models import Booking, BookingStatus
from payments.models import PayoutStatus, TransporterPayout
from transporters.models import TransportPricing, get_transport_rules

from .forms import (
    AuthenticationForm,
    CustomUserCreationForm,
    NewTransportRuleForm,
    ProfileAccountForm,
    ResendVerificationForm,
    TransportRuleForm,
    VerifyEmailCodeForm,
)
from .utils import send_verification_email, verify_email_code


User = get_user_model()


def build_farmer_report_context(user):
    zero_amount = Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
    bookings = Booking.objects.filter(farmer=user).select_related("transporter", "vehicle").order_by("-created_at")
    summary = bookings.aggregate(
        total_bookings=Count("id"),
        pending_payment=Count("id", filter=Q(status=BookingStatus.PENDING_PAYMENT)),
        active_deliveries=Count("id", filter=Q(status__in=[
            BookingStatus.CONFIRMED,
            BookingStatus.ACCEPTED,
            BookingStatus.PICKED_UP,
            BookingStatus.IN_TRANSIT,
        ])),
        delivered_bookings=Count("id", filter=Q(status__in=[BookingStatus.DELIVERED, BookingStatus.COMPLETED])),
        total_spend=Coalesce(Sum("quoted_price"), zero_amount),
        paid_bookings=Count("id", filter=Q(payment_status="paid")),
    )
    return {
        "farmer_report_summary": summary,
        "farmer_recent_report_bookings": bookings[:8],
    }


def build_transporter_report_context(user):
    zero_amount = Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
    jobs = Booking.objects.filter(transporter=user).select_related("farmer", "vehicle").order_by("-created_at")
    payouts = TransporterPayout.objects.filter(transporter=user)
    summary = jobs.aggregate(
        total_jobs=Count("id"),
        active_jobs=Count("id", filter=Q(status__in=[
            BookingStatus.ACCEPTED,
            BookingStatus.PICKED_UP,
            BookingStatus.IN_TRANSIT,
        ])),
        delivered_jobs=Count("id", filter=Q(status__in=[BookingStatus.DELIVERED, BookingStatus.COMPLETED])),
        total_job_value=Coalesce(Sum("quoted_price"), zero_amount),
    )
    summary.update(
        payouts.aggregate(
            pending_release=Coalesce(Sum("amount_kes", filter=Q(status=PayoutStatus.PENDING_RELEASE)), zero_amount),
            released_earnings=Coalesce(Sum("amount_kes", filter=Q(status=PayoutStatus.RELEASED)), zero_amount),
        )
    )
    return {
        "transporter_report_summary": summary,
        "transporter_recent_jobs": jobs[:8],
    }


def build_csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response


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
            context.update(AdminDashboardView.build_dashboard_context())
        if self.request.user.role == "farmer":
            context.update(build_farmer_report_context(self.request.user))
        if self.request.user.role == "driver":
            context.update(build_transporter_report_context(self.request.user))
            context["vehicle_type_options"] = [
                {"value": rule.vehicle_type, "label": rule.get_vehicle_type_display()}
                for rule in get_transport_rules()
            ]
        return context


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "accounts/admin_dashboard.html"
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff

    @classmethod
    def build_rule_form(cls, rule, bound_forms=None):
        if bound_forms and rule.vehicle_type in bound_forms:
            return bound_forms[rule.vehicle_type]
        if getattr(rule, "pk", None):
            return TransportRuleForm(instance=rule, prefix=rule.vehicle_type)
        return TransportRuleForm(
            prefix=rule.vehicle_type,
            initial={
                "vehicle_type": rule.vehicle_type,
                "price_per_km": rule.price_per_km,
                "min_weight_kg": rule.min_weight_kg,
                "max_weight_kg": rule.max_weight_kg,
            },
        )

    @classmethod
    def build_dashboard_context(cls, profile_form=None, new_rule_form=None, rule_forms=None):
        zero_amount = Value(0, output_field=DecimalField(max_digits=10, decimal_places=2))
        current_rates = [
            {
                "rule": rule,
                "label": rule.get_vehicle_type_display(),
                "price_per_km": rule.price_per_km,
                "min_weight_kg": rule.min_weight_kg,
                "max_weight_kg": rule.max_weight_kg,
                "form": cls.build_rule_form(rule, rule_forms),
            }
            for rule in get_transport_rules()
        ]

        booking_summary = Booking.objects.aggregate(
            total_bookings=Count("id"),
            active_bookings=Count("id", filter=Q(status__in=[
                BookingStatus.PENDING_PAYMENT,
                BookingStatus.CONFIRMED,
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
        for item in bookings_by_vehicle:
            item["vehicle_type_label"] = item["vehicle_type_required"].replace("_", " ").title()
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
            "new_rule_form": new_rule_form or NewTransportRuleForm(),
            "all_bookings": all_bookings,
            "active_deliveries": active_deliveries,
            "recent_delivered_bookings": all_bookings.filter(
                status__in=[BookingStatus.DELIVERED, BookingStatus.COMPLETED]
            )[:8],
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
        if action == "update-transport-rule":
            return self.handle_transport_rule_update(request, **kwargs)
        if action == "create-transport-rule":
            return self.handle_transport_rule_create(request, **kwargs)
        return redirect("admin-dashboard")

    def handle_transport_rule_update(self, request, **kwargs):
        rule = get_object_or_404(TransportPricing, id=request.POST.get("rule_id"))
        form = TransportRuleForm(request.POST, instance=rule, prefix=rule.vehicle_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"{rule.get_vehicle_type_display()} settings have been updated.")
            return redirect("admin-dashboard")

        rule_forms = {
            item.vehicle_type: (
                form if item.id == rule.id else TransportRuleForm(instance=item, prefix=item.vehicle_type)
            )
            for item in TransportPricing.objects.order_by("min_weight_kg", "vehicle_type")
        }
        context = self.get_context_data(**kwargs)
        context.update(
            self.build_dashboard_context(
                profile_form=ProfileAccountForm(instance=request.user),
                new_rule_form=NewTransportRuleForm(),
                rule_forms=rule_forms,
            )
        )
        return self.render_to_response(context)

    def handle_transport_rule_create(self, request, **kwargs):
        form = NewTransportRuleForm(request.POST)
        if form.is_valid():
            rule = form.save()
            messages.success(request, f"{rule.get_vehicle_type_display()} has been added to the system.")
            return redirect("admin-dashboard")

        context = self.get_context_data(**kwargs)
        context.update(
            self.build_dashboard_context(
                profile_form=ProfileAccountForm(instance=request.user),
                new_rule_form=form,
            )
        )
        return self.render_to_response(context)

    def handle_booking_status_update(self, request):
        booking = get_object_or_404(Booking, id=request.POST.get("booking_id"))
        new_status = request.POST.get("status", "")
        valid_statuses = {choice for choice, _ in BookingStatus.choices}
        if new_status not in valid_statuses:
            messages.error(request, "Choose a valid booking status.")
            return redirect("admin-dashboard")

        booking.status = new_status
        if new_status == BookingStatus.DELIVERED and not booking.delivered_at:
            from django.utils import timezone
            booking.delivered_at = timezone.now()
        booking.save(update_fields=["status", "delivered_at", "updated_at"])
        messages.success(request, f"Booking #{booking.id} has been updated to {booking.get_status_display()}.")
        return redirect("admin-dashboard")

    def handle_booking_delete(self, request):
        booking = get_object_or_404(Booking, id=request.POST.get("booking_id"))
        booking_id = booking.id
        booking.delete()
        messages.success(request, f"Booking #{booking_id} has been deleted.")
        return redirect("admin-dashboard")


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        send_verification_email(self.request, self.object)
        self.request.session["pending_verification_email"] = self.object.email
        messages.success(self.request, "Your account has been created. Enter the code sent to your email before signing in.")
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
                request.session["pending_verification_email"] = updated_user.email
                messages.success(request, "Your profile has been updated. Enter the code sent to your new email address to verify it.")
                return redirect("verification-sent")
            messages.success(request, "Your profile has been updated.")
        else:
            for errors in form.errors.values():
                if errors:
                    messages.error(request, errors[0])
                    break
        return redirect(redirect_to)


class VerificationSentView(TemplateView):
    template_name = "registration/verification_sent.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pending_verification_email"] = self.request.session.get("pending_verification_email", "")
        return context


class VerifyEmailCodeView(View):
    template_name = "registration/verify_email_code.html"

    def get_initial(self, request):
        return {"email": request.session.get("pending_verification_email", request.GET.get("email", ""))}

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"form": VerifyEmailCodeForm(initial=self.get_initial(request))})

    def post(self, request, *args, **kwargs):
        form = VerifyEmailCodeForm(request.POST)
        if form.is_valid():
            user = form.user
            verified, error_message = verify_email_code(user, form.cleaned_data["code"])
            if verified:
                request.session.pop("pending_verification_email", None)
                messages.success(request, "Your email has been verified. You can now sign in.")
                return redirect("login")
            form.add_error("code", error_message)
        return render(request, self.template_name, {"form": form})


class VerifyEmailView(View):
    def get(self, request, *args, **kwargs):
        messages.info(request, "Email verification now uses a code. Enter the code sent to your email to finish setting up your account.")
        return redirect("verify-email")


class ResendVerificationView(View):
    template_name = "registration/resend_verification.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"form": ResendVerificationForm()})

    def post(self, request, *args, **kwargs):
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            send_verification_email(request, form.user)
            request.session["pending_verification_email"] = form.user.email
            messages.success(request, "A new verification code has been sent to your email.")
            return redirect("verification-sent")
        return render(request, self.template_name, {"form": form})


class FarmerBookingsReportExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "farmer":
            return redirect("home")
        bookings = (
            Booking.objects.filter(farmer=request.user)
            .select_related("transporter", "vehicle")
            .order_by("-created_at")
        )
        return build_csv_response(
            "farmer-bookings-report.csv",
            [
                "Booking ID",
                "Produce",
                "Weight (kg)",
                "Vehicle Type",
                "Status",
                "Payment Status",
                "Quoted Price (KES)",
                "Pickup",
                "Dropoff",
                "Transporter",
                "Created At",
            ],
            [
                [
                    booking.id,
                    booking.produce_name,
                    booking.weight_kg,
                    booking.get_vehicle_type_required_display(),
                    booking.get_status_display(),
                    booking.get_payment_status_display(),
                    booking.quoted_price or "0.00",
                    booking.pickup_address,
                    booking.dropoff_address,
                    f"{booking.transporter.first_name} {booking.transporter.last_name}".strip() if booking.transporter else "",
                    timezone.localtime(booking.created_at).strftime("%Y-%m-%d %H:%M"),
                ]
                for booking in bookings
            ],
        )


class TransporterJobsReportExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "driver":
            return redirect("home")
        jobs = (
            Booking.objects.filter(transporter=request.user)
            .select_related("farmer", "vehicle")
            .order_by("-created_at")
        )
        return build_csv_response(
            "transporter-jobs-report.csv",
            [
                "Booking ID",
                "Farmer",
                "Produce",
                "Vehicle",
                "Status",
                "Quoted Price (KES)",
                "Pickup",
                "Dropoff",
                "Accepted At",
                "Delivered At",
            ],
            [
                [
                    booking.id,
                    f"{booking.farmer.first_name} {booking.farmer.last_name}".strip(),
                    booking.produce_name,
                    booking.vehicle.get_vehicle_type_display() if booking.vehicle else booking.get_vehicle_type_required_display(),
                    booking.get_status_display(),
                    booking.quoted_price or "0.00",
                    booking.pickup_address,
                    booking.dropoff_address,
                    timezone.localtime(booking.accepted_at).strftime("%Y-%m-%d %H:%M") if booking.accepted_at else "",
                    timezone.localtime(booking.delivered_at).strftime("%Y-%m-%d %H:%M") if booking.delivered_at else "",
                ]
                for booking in jobs
            ],
        )


class AdminBookingsReportExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        bookings = Booking.objects.select_related("farmer", "transporter", "vehicle").order_by("-created_at")
        return build_csv_response(
            "admin-bookings-report.csv",
            [
                "Booking ID",
                "Farmer",
                "Transporter",
                "Produce",
                "Vehicle Type",
                "Status",
                "Payment Status",
                "Quoted Price (KES)",
                "Pickup",
                "Dropoff",
                "Created At",
            ],
            [
                [
                    booking.id,
                    f"{booking.farmer.first_name} {booking.farmer.last_name}".strip(),
                    f"{booking.transporter.first_name} {booking.transporter.last_name}".strip() if booking.transporter else "",
                    booking.produce_name,
                    booking.get_vehicle_type_required_display(),
                    booking.get_status_display(),
                    booking.get_payment_status_display(),
                    booking.quoted_price or "0.00",
                    booking.pickup_address,
                    booking.dropoff_address,
                    timezone.localtime(booking.created_at).strftime("%Y-%m-%d %H:%M"),
                ]
                for booking in bookings
            ],
        )


class AdminRatesReportExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        rates = get_transport_rules()
        return build_csv_response(
            "admin-rates-report.csv",
            ["Vehicle Type", "Rate Per Km (KES)", "Min Weight (kg)", "Max Weight (kg)"],
            [
                [rule.get_vehicle_type_display(), rule.price_per_km, rule.min_weight_kg, rule.max_weight_kg]
                for rule in rates
            ],
        )
