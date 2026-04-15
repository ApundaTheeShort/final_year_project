from decimal import Decimal

from django.db import migrations, models


DEFAULT_RULES = {
    "motorbike": (Decimal("0.00"), Decimal("200.00")),
    "van": (Decimal("200.00"), Decimal("1000.00")),
    "pickup": (Decimal("1000.00"), Decimal("3000.00")),
    "truck": (Decimal("10000.00"), Decimal("30000.00")),
}


def seed_weight_bands(apps, schema_editor):
    TransportPricing = apps.get_model("transporters", "TransportPricing")
    for vehicle_type, (min_weight, max_weight) in DEFAULT_RULES.items():
        TransportPricing.objects.update_or_create(
            vehicle_type=vehicle_type,
            defaults={
                "min_weight_kg": min_weight,
                "max_weight_kg": max_weight,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("transporters", "0002_transportpricing_alter_vehicle_price_per_km"),
    ]

    operations = [
        migrations.AddField(
            model_name="transportpricing",
            name="max_weight_kg",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.AddField(
            model_name="transportpricing",
            name="min_weight_kg",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.RunPython(seed_weight_bands, migrations.RunPython.noop),
    ]
