from django.urls import path

from payment import views

urlpatterns = [
    path('initiate/', views.InitiatePaymentView.as_view(), name='initiate_payment'),
    path('verify/', views.VerifyPaymentView.as_view(), name='verify_payment'),
    path('details/<str:reference>/', views.PaymentDetailsView.as_view(), name='payment_details'),
    path('webhook/', views.PaystackWebhookView.as_view(), name='paystack_webhook'),
]
