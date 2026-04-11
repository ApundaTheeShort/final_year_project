from django.db.models.signals import post_save
from django.dispatch import receiver

from booking.models import Booking, BookingStatus

from .services import maybe_auto_release_on_delivery


@receiver(post_save, sender=Booking)
def auto_release_payment_on_delivery(sender, instance, **kwargs):
    if instance.status == BookingStatus.DELIVERED:
        maybe_auto_release_on_delivery(instance)

