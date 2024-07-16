from dateutil.relativedelta import relativedelta
from django.db import models
from django.utils import timezone

from accounts.models import User


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

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='NGN')
    reference = models.CharField(max_length=200, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency}"


class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    paystack_subscription_code = models.CharField(max_length=100, blank=True, null=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    last_payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + relativedelta(months=1)
        super().save(*args, **kwargs)

    def renew(self, payment):
        self.end_date = self.end_date + relativedelta(months=1)
        self.last_payment = payment
        self.save()

    def is_valid(self):
        return self.is_active and self.end_date > timezone.now()


class WebhookLog(models.Model):
    payload = models.JSONField()
    verified = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Webhook {self.id} - Verified: {self.verified}, Processed: {self.processed}"
