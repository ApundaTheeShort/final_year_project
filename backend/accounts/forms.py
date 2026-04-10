from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm as DjangoAuthenticationForm
from django.contrib.auth.forms import UserCreationForm, UserChangeForm as BaseUserChangeForm
from django.core.exceptions import ValidationError

from transporters.models import DEFAULT_TRANSPORT_PRICING, TransportPricing, VehicleType

from .models import CustomUser


User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    ALLOWED_ROLES = ("farmer", "driver")

    class Meta:
        model = CustomUser
        fields = ('phone_number', 'email', 'first_name', 'last_name', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (value, label)
            for value, label in self.fields["role"].choices
            if value in self.ALLOWED_ROLES
        ]

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role not in self.ALLOWED_ROLES:
            raise ValidationError("Select a valid account type.")
        return role


class CustomUserChangeForm(BaseUserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('phone_number', 'email', 'first_name', 'last_name', 'role')


class AuthenticationForm(DjangoAuthenticationForm):
    username = forms.CharField(
        label='Phone number',
        max_length=150,
        widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username'}),
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff and not user.is_email_verified:
            raise ValidationError(
                "Verify your email address before signing in.",
                code="email_not_verified",
            )


class ProfileAccountForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ("first_name", "last_name", "phone_number", "email")

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"]
        existing = CustomUser.objects.filter(phone_number=phone_number).exclude(id=self.instance.id)
        if existing.exists():
            raise forms.ValidationError("This phone number is already in use.")
        return phone_number

    def clean_email(self):
        email = self.cleaned_data["email"]
        existing = CustomUser.objects.filter(email=email).exclude(id=self.instance.id)
        if existing.exists():
            raise forms.ValidationError("This email address is already in use.")
        return email


class ResendVerificationForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        email = self.cleaned_data["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise forms.ValidationError("No account was found with that email address.") from exc
        if user.is_staff:
            raise forms.ValidationError("This account cannot use email verification resend.")
        if user.is_email_verified:
            raise forms.ValidationError("This email address is already verified.")
        self.user = user
        return email


class TransportRateForm(forms.Form):
    motorbike = forms.DecimalField(label="Motorbike", min_value=0, decimal_places=2, max_digits=10)
    pickup = forms.DecimalField(label="Pickup", min_value=0, decimal_places=2, max_digits=10)
    van = forms.DecimalField(label="Van", min_value=0, decimal_places=2, max_digits=10)
    truck = forms.DecimalField(label="Truck", min_value=0, decimal_places=2, max_digits=10)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            current_rates = {
                item.vehicle_type: item.price_per_km
                for item in TransportPricing.objects.all()
            }
            for vehicle_type, _ in VehicleType.choices:
                self.fields[vehicle_type].initial = current_rates.get(vehicle_type, DEFAULT_TRANSPORT_PRICING[vehicle_type])

    def save(self):
        for vehicle_type, _ in VehicleType.choices:
            TransportPricing.objects.update_or_create(
                vehicle_type=vehicle_type,
                defaults={"price_per_km": self.cleaned_data[vehicle_type]},
            )
