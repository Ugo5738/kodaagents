from django.shortcuts import redirect
from django.urls import reverse


class PaymentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if the user is an admin or superuser
            if request.user.is_staff or request.user.is_superuser:
                return self.get_response(request)

            # Check if the user has a tier and if they've exceeded any limits
            if request.user.tier and request.user.needs_payment():
                # List of URLs that should be accessible even if payment is needed
                allowed_paths = [
                    reverse('initiate_payment'),
                    reverse('user_payment_status'),
                    # Add any other paths that should be accessible
                ]

                if not any(request.path.startswith(path) for path in allowed_paths):
                    return redirect('initiate_payment')

        return self.get_response(request)
