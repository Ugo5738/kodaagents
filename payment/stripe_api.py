import stripe
from django.conf import settings

from koda.config.logging_config import configure_logger

logger = configure_logger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeAPI:
    def __init__(self, test_mode=False):
        self.api_key = settings.STRIPE_TEST_SECRET_KEY if test_mode else settings.STRIPE_SECRET_KEY
        stripe.api_key = self.api_key

    def create_payment_intent(self, amount, customer_email, currency):
        try:
            intent = stripe.PaymentIntent.create(
                amount=self._convert_to_lowest_unit(amount, currency),  # Stripe expects amounts in cents
                currency=currency,
                receipt_email=customer_email,
            )
            return intent
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {str(e)}")
            return None

    def _convert_to_lowest_unit(self, amount, currency):
        conversion_factors = {
            'usd': 100,  # 1 Dollar = 100 Cents
            'eur': 100,  # 1 Euro = 100 Cents
            'gbp': 100,  # 1 Pound = 100 Pence
            # Add other currencies as needed
        }
        factor = conversion_factors.get(currency.lower(), 100)
        return int(amount * factor)

    def verify_payment_intent(self, payment_intent_id):
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return intent
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {str(e)}")
            return None

    def retrieve_subscription(self, subscription_id):
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {str(e)}")
            return None

    def get_billing_history(self, customer_id):
        try:
            invoices = stripe.Invoice.list(customer=customer_id, limit=10)
            return [
                {
                    'date': invoice.created,
                    'amount': invoice.total / 100,  # Convert cents to dollars
                    'status': invoice.status,
                    'invoice_pdf': invoice.invoice_pdf,
                }
                for invoice in invoices.data
            ]
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {str(e)}")
            return []

    def cancel_subscription(self, subscription_id):
        try:
            canceled_subscription = stripe.Subscription.delete(subscription_id)
            return canceled_subscription
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {str(e)}")
            return None
