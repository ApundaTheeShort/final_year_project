from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin

# Create your models here.


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, email, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Must enter phone number")
        if not email:
            raise ValueError("Must enter email")
        if not extra_fields.get("role"):
            raise ValueError("Must enter role")

        email = self.normalize_email(email)
        user = self.model(
            phone_number=phone_number,
            email=email, **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_email_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('is_staff must be set to true')
        if extra_fields.get('is_active') is not True:
            raise ValueError('is_active must be set to true')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('is_superuser must be set to True')

        return self.create_user(phone_number, email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    USER_ROLES = (
        ("admin", "admin"),
        ("driver", "driver"),
        ("farmer", "farmer"),
    )

    phone_number = models.CharField(max_length=12, unique=True)
    role = models.CharField(max_length=20, choices=USER_ROLES)
    first_name = models.CharField(max_length=100, blank=False)
    last_name = models.CharField(max_length=100, blank=False)
    email = models.EmailField(unique=True, max_length=254, blank=False)
    is_email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return f"{self.phone_number} - {self.first_name} {self.last_name}"
