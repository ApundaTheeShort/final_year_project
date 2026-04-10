from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def build_email_verification_link(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("verify-email", kwargs={"uidb64": uid, "token": token})
    return request.build_absolute_uri(path)


def send_verification_email(request, user):
    current_site = get_current_site(request)
    verification_url = build_email_verification_link(request, user)
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
            "verification_url": verification_url,
        },
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    user.email_verification_sent_at = timezone.now()
    user.save(update_fields=["email_verification_sent_at"])
