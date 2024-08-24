from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField

from helpers.models import TrackingModel

GENDER_CHOICES = (("M", "Male"), ("F", "Female"))


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users require an email field")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser, TrackingModel):
    email = models.EmailField(
        _("email address"), db_index=True, unique=True, blank=True, null=True
    )
    username = models.CharField(
        _("username"), max_length=30, blank=True, null=True, unique=False
    )
    phone = models.CharField(max_length=60, blank=True, null=True)
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, blank=True, null=True
    )
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to="profile_pics/", null=True, blank=True
    )

    email_verification_token = models.CharField(max_length=128, null=True, blank=True)
    email_verified = models.BooleanField(
        _("email verified"),
        default=False,
        help_text="Designates whether this users email is verified.",
    )

    # payment
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    tier = models.ForeignKey("UserTier", on_delete=models.SET_NULL, null=True, related_name='users')
    download_count = models.IntegerField(default=0)
    creation_count = models.IntegerField(default=0)
    customization_count = models.IntegerField(default=0)

    @property
    def total_usage_count(self):
        return self.creation_count + self.customization_count + self.download_count

    def has_reached_limit(self, action_type):
        if self.tier is None:
            return True
        if action_type == 'download':
            return self.download_count >= self.tier.download_limit
        elif action_type == 'creation':
            return self.creation_count >= self.tier.creation_limit
        elif action_type == 'customization':
            return self.customization_count >= self.tier.customization_limit
        return False

    def get_remaining_uses(self, action_type):
        if self.tier is None:
            return 0
        if action_type == 'download':
            return max(0, self.tier.download_limit - self.download_count)
        elif action_type == 'creation':
            return max(0, self.tier.creation_limit - self.creation_count)
        elif action_type == 'customization':
            return max(0, self.tier.customization_limit - self.customization_count)
        return 0

    def needs_payment(self):
        return (self.has_reached_limit('download') or
                self.has_reached_limit('creation') or
                self.has_reached_limit('customization'))

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        return "{}".format(self.email)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.last_login = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")


class UserTier(models.Model):
    FREE = 'free'
    ESSENTIAL = 'essential'
    PROFESSIONAL = 'professional'
    PREMIUM = 'premium'

    TIER_CHOICES = [
        (FREE, 'Free'),
        (ESSENTIAL, 'Essential'),
        (PROFESSIONAL, 'Professional'),
        (PREMIUM, 'Premium'),
    ]

    name = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    download_limit = models.IntegerField()
    creation_limit = models.IntegerField()
    customization_limit = models.IntegerField()

    def __str__(self):
        return self.name


class OrganizationProfile(TrackingModel):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="organization_profile"
    )
    name = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, null=True)

    # organization address
    city = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    address2 = models.CharField(max_length=255, null=True, blank=True)
    country = CountryField(multiple=False, null=True, blank=True)
    zip_code = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return "{}".format(self.name)

    class Meta:
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")


class GoogleToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()
    email = models.EmailField()
    scopes = models.TextField()  # Store the scopes as a comma-separated string

    @property
    def expired(self):
        from django.utils import timezone
        return self.expires_at <= timezone.now()

    def get_scopes(self):
        return self.scopes.split(',')
