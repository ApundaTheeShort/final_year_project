import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone


EMAIL_VERIFICATION_CODE_TTL_MINUTES = 10


def generate_email_verification_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def set_email_verification_code(user):
    code = generate_email_verification_code()
    user.email_verification_code = code
    user.email_verification_sent_at = timezone.now()
    user.email_verification_expires_at = timezone.now() + timedelta(minutes=EMAIL_VERIFICATION_CODE_TTL_MINUTES)
    user.save(
        update_fields=[
            "email_verification_code",
            "email_verification_sent_at",
            "email_verification_expires_at",
        ]
    )
    return code


def clear_email_verification_code(user):
    user.email_verification_code = ""
    user.email_verification_expires_at = None
    user.save(update_fields=["email_verification_code", "email_verification_expires_at"])


def send_verification_email(request, user):
    current_site = get_current_site(request)
    code = set_email_verification_code(user)
    subject = render_to_string(
        "registration/email_verification_subject.txt",
        {"site_name": current_site.name},
    ).strip()
    message = render_to_string(
        "registration/email_verification_email.txt",
        {
            "user": user,
            "site_name": current_site.name,
            "domain": current_site.domain,
            "verification_code": code,
            "verification_expires_minutes": EMAIL_VERIFICATION_CODE_TTL_MINUTES,
        },
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def verify_email_code(user, code):
    if user.is_email_verified:
        return False, "This email address has already been verified."
    if not user.email_verification_code:
        return False, "Request a new verification code and try again."
    if not user.email_verification_expires_at or user.email_verification_expires_at < timezone.now():
        return False, "This verification code has expired. Request a new one and try again."
    if user.email_verification_code != code:
        return False, "That verification code is not correct. Check your email and try again."

    user.is_email_verified = True
    user.email_verified_at = timezone.now()
    user.email_verification_code = ""
    user.email_verification_expires_at = None
    user.save(
        update_fields=[
            "is_email_verified",
            "email_verified_at",
            "email_verification_code",
            "email_verification_expires_at",
        ]
    )
    return True, None
