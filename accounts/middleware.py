# accounts/middleware.py

from django.shortcuts import redirect
from django.urls import reverse


class PaymentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_paid:
            if request.user.usage_count >= 1 and not request.path.startswith(reverse('initiate_payment')):
                return redirect('initiate_payment')
        return self.get_response(request)
