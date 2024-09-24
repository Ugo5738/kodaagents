from django.urls import path

from payment import views

urlpatterns = [
    path("initiate/", views.InitiatePaymentView.as_view(), name="initiate_payment"),
    path("verify/", views.VerifyPaymentView.as_view(), name="verify_payment"),
    path("details/<str:reference>/", views.PaymentDetailsView.as_view(), name="payment_details"),
    path(
        "subscription-details/",
        views.SubscriptionDetailsView.as_view(),
        name="subscription_details",
    ),
    path("billing-history/", views.BillingHistoryView.as_view(), name="billing_history"),
    path(
        "cancel-subscription/", views.CancelSubscriptionView.as_view(), name="cancel_subscription"
    ),
    path("stripe-webhook/", views.StripeWebhookView.as_view(), name="stripe_webhook"),
    path("paystack-webhook/", views.PaystackWebhookView.as_view(), name="paystack_webhook"),
]
