import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PaystackAPI:
    def __init__(self, test_mode=False):
        self.secret_key = settings.PAYSTACK_TEST_SECRET_KEY if test_mode else settings.PAYSTACK_SECRET_KEY
        self.BASE_URL = 'https://api.paystack.co'

    def _make_request(self, method, endpoint, data=None):
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        try:
            logger.info(f"Making {method} request to Paystack: URL={url}, Headers={headers}, Data={data}")
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API error: {e.response.status_code} {e.response.reason} - {e.response.text}")
        return None

    def initialize_transaction(self, email, amount, currency='NGN', callback_url=None):
        endpoint = '/transaction/initialize'
        converted_amount = self._convert_to_lowest_unit(amount, currency)
        data = {
            "email": email,
            "amount": converted_amount,
            "currency": currency,
            "webhook_url": settings.PAYSTACK_WEBHOOK_URL,
        }
        if callback_url:
            data['callback_url'] = callback_url
        return self._make_request('POST', endpoint, data)

    def _convert_to_lowest_unit(self, amount, currency):
        conversion_factors = {
            'NGN': 100,  # 1 Naira = 100 Kobo
            'USD': 100,  # 1 Dollar = 100 Cents
            'GHS': 100,  # 1 Cedi = 100 Pesewas
            # Add other currencies as needed
        }
        factor = conversion_factors.get(currency, 100)
        return int(amount * factor)

    def verify_transaction(self, reference):
        endpoint = f'/transaction/verify/{reference}'
        return self._make_request('GET', endpoint)
