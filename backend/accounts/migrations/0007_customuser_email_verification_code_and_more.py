from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_customuser_email_verification_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="email_verification_code",
            field=models.CharField(blank=True, max_length=6),
        ),
        migrations.AddField(
            model_name="customuser",
            name="email_verification_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
