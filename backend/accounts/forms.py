from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm as DjangoAuthenticationForm
from django.contrib.auth.forms import UserCreationForm, UserChangeForm as BaseUserChangeForm
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from transporters.models import TransportPricing, format_vehicle_type_label, normalize_vehicle_type_key

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
            raise ValidationError("Choose whether you are signing up as a farmer or transporter.")
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
            raise forms.ValidationError("That phone number is already linked to another account.")
        return phone_number

    def clean_email(self):
        email = self.cleaned_data["email"]
        existing = CustomUser.objects.filter(email=email).exclude(id=self.instance.id)
        if existing.exists():
            raise forms.ValidationError("That email address is already linked to another account.")
        return email


class ResendVerificationForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        email = self.cleaned_data["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise forms.ValidationError("We could not find an account with that email address.") from exc
        if user.is_staff:
            raise forms.ValidationError("This account does not use this email verification page.")
        if user.is_email_verified:
            raise forms.ValidationError("This email address has already been verified.")
        self.user = user
        return email


class VerifyEmailCodeForm(forms.Form):
    email = forms.EmailField()
    code = forms.CharField(max_length=6, min_length=6)

    def clean_email(self):
        email = self.cleaned_data["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise forms.ValidationError("We could not find an account with that email address.") from exc
        if user.is_staff:
            raise forms.ValidationError("This account does not use this email verification page.")
        self.user = user
        return email

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit():
            raise forms.ValidationError("Enter the 6-digit code we sent to your email.")
        return code


class TransportRuleForm(forms.ModelForm):
    class Meta:
        model = TransportPricing
        fields = ("vehicle_type", "price_per_km", "min_weight_kg", "max_weight_kg")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle_type"].help_text = "Use a short name such as motorbike, van, pickup, or truck."

    def clean_vehicle_type(self):
        vehicle_type = normalize_vehicle_type_key(self.cleaned_data["vehicle_type"])
        existing = TransportPricing.objects.filter(vehicle_type=vehicle_type)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("That vehicle type already exists.")
        return vehicle_type

    def clean(self):
        cleaned_data = super().clean()
        min_weight = cleaned_data.get("min_weight_kg")
        max_weight = cleaned_data.get("max_weight_kg")
        if min_weight is None or max_weight is None:
            return cleaned_data
        if max_weight <= min_weight:
            self.add_error("max_weight_kg", "Maximum weight must be greater than minimum weight.")
            return cleaned_data

        vehicle_type = cleaned_data.get("vehicle_type")
        overlaps = TransportPricing.objects.exclude(pk=self.instance.pk).filter(
            min_weight_kg__lt=max_weight,
            max_weight_kg__gt=min_weight,
        )
        if overlaps.exists():
            self.add_error("min_weight_kg", "This weight band overlaps another vehicle type.")
        if vehicle_type:
            self.instance.vehicle_type = vehicle_type
        return cleaned_data


class NewTransportRuleForm(TransportRuleForm):
    pass
