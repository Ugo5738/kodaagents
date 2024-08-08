from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils import timezone

from accounts.models import User, UserTier


class Payment(models.Model):
    CURRENCY_CHOICES = [
        ('NGN', 'Nigerian Naira'),
        ('USD', 'US Dollar'),
        ('GBP', 'British Pound'),
        ('EUR', 'Euro'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    PROVIDER_CHOICES = [
        ('paystack', 'Paystack'),
        ('stripe', 'Stripe'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    reference = models.CharField(max_length=200, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    subscription = models.ForeignKey("Subscription", on_delete=models.SET_NULL, null=True, blank=True)
    tier = models.ForeignKey(UserTier, on_delete=models.SET_NULL, null=True)

    # New fields for Stripe
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True, null=True)
    stripe_charge_id = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency} ({self.provider})"


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('trialing', 'Trialing'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
        ('incomplete', 'Incomplete'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    paystack_subscription_code = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    current_period_start = models.DateTimeField(null=True)
    current_period_end = models.DateTimeField(null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    provider = models.CharField(max_length=10, choices=Payment.PROVIDER_CHOICES)
    tier = models.ForeignKey(UserTier, on_delete=models.SET_NULL, null=True)

    def is_active(self):
        return self.status in ['trialing', 'active']

    def __str__(self):
        return f"{self.user.email}'s Subscription ({self.provider})"


class WebhookLog(models.Model):
    PROVIDER_CHOICES = [
        ('paystack', 'Paystack'),
        ('stripe', 'Stripe'),
    ]

    payload = models.JSONField()
    verified = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES)

    def __str__(self):
        return f"Webhook {self.id} - Provider: {self.provider}, Verified: {self.verified}, Processed: {self.processed}"
