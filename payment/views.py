import hashlib
import hmac

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from helpers.email_utils import (
    send_payment_confirmation_email,
    send_payment_notification_email,
    send_subscription_status_email,
)
from koda.config.logging_config import configure_logger
from payment.models import Payment, Subscription, WebhookLog
from payment.paystack_api import PaystackAPI
from payment.stripe_api import StripeAPI
import stripe
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime

logger = configure_logger(__name__)

class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        amount = data.get('amount')
        currency = data.get('currency', 'usd')
        provider = data.get('provider', 'stripe')
        payment_type = data.get('payment_type', 'one_time')  # 'one_time' or 'subscription'

        if not amount and payment_type == 'one_time':
            return JsonResponse({'error': 'Amount is required for one-time payments'}, status=status.HTTP_400_BAD_REQUEST)

        if payment_type not in ['one_time', 'subscription']:
            return JsonResponse({'error': 'Invalid payment type'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if payment_type == 'one_time':
                amount = float(amount)
        except ValueError:
            return JsonResponse({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        if provider == 'paystack':
            return self.initiate_paystack_payment(request, amount, currency, payment_type)
        elif provider == 'stripe':
            return self.initiate_stripe_payment(request, amount, currency, payment_type)
        else:
            return JsonResponse({'error': 'Invalid payment provider'}, status=400)

    def initiate_paystack_payment(self, request, amount, currency, payment_type):
        paystack = PaystackAPI()
        if payment_type == 'subscription':
            response = paystack.initialize_subscription(
                email=request.user.email,
                plan=settings.PAYSTACK_PLAN_CODE,
                callback_url=f"{settings.FRONTEND_BASE_URL}/subscription/verify/"
            )

            if response and 'data' in response:
                Subscription.objects.create(
                    user=request.user,
                    paystack_subscription_code=response['data']['subscription_code'],
                    provider='paystack'
                )
                return JsonResponse({'authorization_url': response['data']['authorization_url']})
            else:
                return JsonResponse({'error': 'Failed to initialize subscription'}, status=500)
        else:
            response = paystack.initialize_transaction(
                email=request.user.email,
                amount=amount,
                currency=currency,
                callback_url=f"{settings.FRONTEND_BASE_URL}/payment/verify/"
            )

            if response and 'data' in response:
                Payment.objects.create(
                    user=request.user,
                    amount=amount,
                    currency=currency,
                    reference=response['data']['reference'],
                    provider='paystack'
                )
                return JsonResponse({'authorization_url': response['data']['authorization_url']})
            else:
                return JsonResponse({'error': 'Failed to initialize transaction'}, status=500)

    def initiate_stripe_payment(self, request, amount, currency, payment_type):
        stripe_api = StripeAPI()

        if payment_type == 'subscription':
            return self.initiate_stripe_subscription(request)
        else:
            intent = stripe_api.create_payment_intent(amount, request.user.email, currency)

            if intent:
                Payment.objects.create(
                    user=request.user,
                    amount=amount,
                    currency=currency,
                    reference=intent.id,
                    stripe_payment_intent_id=intent.id,
                    provider='stripe'
                )
                return JsonResponse({
                    'client_secret': intent.client_secret,
                    'publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
                })
            else:
                return JsonResponse({'error': 'Failed to create payment intent'}, status=500)

    def initiate_stripe_subscription(self, request):
        try:
            # Ensure the user has a Stripe customer ID
            if not request.user.stripe_customer_id:
                customer = stripe.Customer.create(email=request.user.email)
                request.user.stripe_customer_id = customer.id
                request.user.save()

            # Create a Stripe Subscription
            subscription = stripe.Subscription.create(
                customer=request.user.stripe_customer_id,
                items=[{'price': settings.STRIPE_PRICE_ID}],
                payment_behavior='default_incomplete',
                expand=['latest_invoice.payment_intent'],
            )

            intent = subscription.latest_invoice.payment_intent
            if intent:
                Payment.objects.create(
                    user=request.user,
                    amount=intent.amount / 100.0,  # Convert cents to dollars
                    currency=intent.currency.upper(),
                    reference=intent.id,
                    stripe_payment_intent_id=intent.id,
                    status="pending",
                    provider='stripe'
                )
                return Response({
                    'client_secret': intent.client_secret,
                    'subscription_id': subscription.id,
                })
            else:
                return Response({'error': 'Failed to create subscription'}, status=400)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {str(e)}")
            return Response({'error': str(e)}, status=400)


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reference = request.GET.get('reference')
        subscription_id = request.GET.get('subscription_id')
        provider = request.GET.get('provider', 'stripe')

        if not reference and not subscription_id:
            return JsonResponse({"status": "failed", "message": "No reference or subscription ID provided"}, status=400)

        if provider == 'paystack':
            return self.verify_paystack_payment(reference)
        elif provider == 'stripe':
            return self.verify_stripe_payment(reference, subscription_id)
        else:
            return JsonResponse({"status": "failed", "message": "Invalid payment provider"}, status=400)

    def verify_paystack_payment(self, reference):
        paystack = PaystackAPI()
        verify_response = paystack.verify_transaction(reference)

        if verify_response and verify_response['data']['status'] == 'success':
            payment = Payment.objects.get(reference=reference)
            payment.status = 'success'
            payment.save()
            payment.user.is_paid = True
            payment.user.save()
            return JsonResponse({
                "status": "success",
                "message": "Payment verified successfully",
                "details": {
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                    "reference": payment.reference,
                }
            })
        else:
            return JsonResponse({"status": "failed", "message": "Failed to verify payment"}, status=400)

    def verify_stripe_payment(self, reference, subscription_id):
        stripe_api = StripeAPI()
        if subscription_id:
            try:
                subscription = stripe_api.retrieve_subscription(subscription_id)
                if subscription and subscription.status in ['active', 'trialing']:
                    return self._handle_successful_subscription(subscription)
                else:
                    return JsonResponse({"status": "failed", "message": "Subscription is not active"}, status=400)
            except stripe.error.InvalidRequestError:
                return JsonResponse({"status": "failed", "message": "Invalid subscription ID"}, status=400)
        elif reference:
            intent = stripe_api.verify_payment_intent(reference)
            if intent and intent.status == 'succeeded':
                return self._handle_successful_payment(intent)

    def _handle_successful_payment(self, intent):
        payment = Payment.objects.get(stripe_payment_intent_id=intent.id)
        payment.status = 'success'
        payment.save()
        payment.user.is_paid = True
        payment.user.save()

        return JsonResponse({
            "status": "success",
            "message": "Payment verified successfully",
            "details": {
                "amount": str(payment.amount),
                "currency": payment.currency,
                "reference": payment.stripe_payment_intent_id,
                "type": "one_time"
            }
        })

    def _handle_successful_subscription(self, subscription):
        user = User.objects.get(stripe_customer_id=subscription.customer)
        user.is_paid = True
        user.save()

        sub, created = Subscription.objects.update_or_create(
            user=user,
            stripe_subscription_id=subscription.id,
            defaults={
                'status': subscription.status,
                'current_period_start': datetime.fromtimestamp(subscription.current_period_start),
                'current_period_end': datetime.fromtimestamp(subscription.current_period_end),
                'provider': 'stripe'
            }
        )
        return JsonResponse({
            "status": "success",
            "message": "Subscription verified successfully",
            "details": {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
                "type": "subscription"
            }
        })


class PaymentDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, reference):
        try:
            payment = Payment.objects.get(reference=reference)

            # Ensure the logged-in user owns this payment
            if payment.user != request.user:
                return Response({
                    "status": "failed",
                    "message": "Unauthorized access to payment details"
                }, status=status.HTTP_403_FORBIDDEN)

            # If more details is needed from Paystack, you can fetch them here
            paystack = PaystackAPI()
            paystack_response = paystack.verify_transaction(reference)

            if paystack_response and paystack_response['data']['status'] == 'success':
                return JsonResponse({
                    "status": "success",
                    "amount": str(payment.amount),  # Convert to string for JSON serialization
                    "currency": payment.currency,
                    "reference": payment.reference,
                    # Add any other relevant details
                })
            else:
                return JsonResponse({
                    "status": "failed",
                    "message": "Payment verification failed"
                }, status=400)
        except Payment.DoesNotExist:
            logger.error(f"Payment with reference {reference} not found")
            return JsonResponse({
                "status": "failed",
                "message": "Payment not found"
            }, status=404)
        except Exception as e:
            logger.error(f"Error fetching payment details: {str(e)}")
            return JsonResponse({
                "status": "failed",
                "message": "An error occurred while fetching payment details"
            }, status=500)


class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    @csrf_exempt
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {str(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {str(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)


        # Create a WebhookLog entry
        webhook_log = WebhookLog.objects.create(
            payload=event,
            verified=True,
            provider='stripe'
        )

        event_handlers = {
            # add customer.created
            # add customer.deleted
            'payment_intent.succeeded': self.handle_payment_intent_succeeded,
            'customer.subscription.created': self.handle_subscription_created,
            'customer.subscription.updated': self.handle_subscription_updated,
            'customer.subscription.deleted': self.handle_subscription_deleted,
            'invoice.paid': self.handle_invoice_paid,
            'invoice.payment_failed': self.handle_invoice_payment_failed,
        }

        handler = event_handlers.get(event['type'])
        # print("This is the handler: ", handler)
        if handler:
            try:
                response = handler(event['data']['object'], webhook_log)
                webhook_log.processed = True
                webhook_log.save()
                return response or Response(status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error processing webhook: {str(e)}")
                webhook_log.processed = False
                webhook_log.save()
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            logger.warning(f"Unhandled event type: {event['type']}")
            return Response(status=status.HTTP_400_BAD_REQUEST)


    def handle_payment_intent_succeeded(self, payment_intent, webhook_log):
        try:
            with transaction.atomic():
                payment = Payment.objects.select_for_update().get(stripe_payment_intent_id=payment_intent['id'])

                if payment.status == 'success':
                    logger.info(f"Payment {payment_intent['id']} already processed")
                    return

                payment.status = 'success'

                # Safely get the charge ID
                latest_charge = payment_intent.get('latest_charge')
                if latest_charge:
                    payment.stripe_charge_id = latest_charge
                else:
                    logger.warning(f"No charge found for payment intent {payment_intent['id']}")

                payment.save()

                user = payment.user
                user.is_paid = True
                user.save()

            # Send payment notification email
            send_payment_confirmation_email(payment)
            send_payment_notification_email(payment)
            return Response(status=status.HTTP_200_OK)

        except Payment.DoesNotExist:
            logger.error(f"Payment with Stripe PaymentIntent ID {payment_intent['id']} not found")
        except Exception as e:
            logger.error(f"Error processing successful payment: {str(e)}")
            raise  # Re-raise the exception to be caught by the outer try-except block

    def handle_subscription_created(self, subscription, webhook_log):
        user = User.objects.filter(stripe_customer_id=subscription['customer']).first()
        if not user:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Convert Unix timestamps to datetime objects
        current_period_start = datetime.fromtimestamp(subscription['current_period_start'])
        current_period_end = datetime.fromtimestamp(subscription['current_period_end'])

        Subscription.objects.create(
            user=user,
            stripe_subscription_id=subscription['id'],
            status=subscription['status'],
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            provider='stripe'
        )

        user.is_paid = subscription['status'] == 'active'
        user.save()

        send_subscription_status_email(user.email, 'created')
        return Response(status=status.HTTP_200_OK)

    def handle_subscription_updated(self, subscription, webhook_log):
        sub = Subscription.objects.filter(stripe_subscription_id=subscription['id']).first()
        if not sub:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Convert Unix timestamps to datetime objects
        current_period_start = datetime.fromtimestamp(subscription['current_period_start'])
        current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
        cancel_at_period_end = datetime.fromtimestamp(subscription['cancel_at_period_end'])

        sub.status = subscription['status']
        sub.current_period_start = current_period_start
        sub.current_period_end = current_period_end
        sub.cancel_at_period_end = cancel_at_period_end
        if subscription['status'] == 'canceled':
            sub.canceled_at = subscription['canceled_at']
        sub.save()

        user = sub.user
        user.is_paid = sub.is_active()
        user.save()

        if subscription['status'] == 'past_due':
            send_subscription_status_email(user.email, 'payment_failed')
        elif subscription['status'] == 'canceled':
            send_subscription_status_email(user.email, 'cancelled')

        return Response(status=status.HTTP_200_OK)

    def handle_subscription_deleted(self, subscription, webhook_log):
        sub = Subscription.objects.filter(stripe_subscription_id=subscription['id']).first()
        if not sub:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        sub.status = 'canceled'
        sub.canceled_at = subscription['canceled_at']
        sub.save()

        user = sub.user
        user.is_paid = False
        user.save()

        send_subscription_status_email(user.email, 'cancelled')
        return Response(status=status.HTTP_200_OK)

    def handle_invoice_paid(self, invoice, webhook_log):
        subscription_id = invoice['subscription']
        sub = Subscription.objects.filter(stripe_subscription_id=subscription_id).first()
        if not sub:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        payment = Payment.objects.create(
            user=sub.user,
            amount=invoice['amount_paid'] / 100,  # Convert cents to dollars
            currency=invoice['currency'].upper(),
            reference=invoice['id'],
            status='success',
            provider='stripe',
            stripe_charge_id=invoice['charge'],
            subscription=sub
        )

        # Ensure user is marked as paid
        user = sub.user
        user.is_paid = True
        user.save()

        send_payment_confirmation_email(payment)
        return Response(status=status.HTTP_200_OK)

    def handle_invoice_payment_failed(self, invoice, webhook_log):
        subscription_id = invoice['subscription']
        sub = Subscription.objects.filter(stripe_subscription_id=subscription_id).first()
        if not sub:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        sub.status = 'past_due'
        sub.save()

        user = sub.user
        user.is_paid = False
        user.save()

        send_subscription_status_email(user.email, 'payment_failed')
        return Response(status=status.HTTP_200_OK)


@permission_classes([AllowAny])
class PaystackWebhookView(APIView):
    def post(self, request):
        payload = request.data
        signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE', '')

        # Verify the signature
        computed_signature = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
            request.body,
            digestmod=hashlib.sha512
        ).hexdigest()

        if signature == computed_signature:
            # Signature is valid, process the webhook
            webhook_log = WebhookLog.objects.create(payload=payload, verified=True)
            try:
                with transaction.atomic():
                    self.process_webhook(webhook_log)
                return Response(status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error processing webhook: {str(e)}")
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Invalid signature
            WebhookLog.objects.create(payload=payload, verified=False)
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def process_webhook(self, webhook_log):
        event = webhook_log.payload.get('event')
        data = webhook_log.payload.get('data', {})

        if not event or not data:
            logger.error("Invalid webhook payload")
            return

        handler_map = {
            'charge.success': self.handle_successful_charge,
            'subscription.create': self.handle_subscription_created,
            'subscription.disable': self.handle_subscription_cancelled,
            'invoice.payment_failed': self.handle_payment_failed
        }

        handler = handler_map.get(event)
        if handler:
            handler(data)
        else:
            logger.warning(f"Unhandled event type: {event}")

        webhook_log.processed = True
        webhook_log.save()

    def handle_successful_charge(self, data):
        reference = data.get('reference')

        if not reference:
            logger.error("Reference missing in charge.success event")
            return

        try:
            with transaction.atomic():
                payment = Payment.objects.select_for_update().get(reference=reference)
                if payment.status == 'success':
                    logger.info(f"Payment {reference} already processed")
                    return

                payment.status = 'success'
                payment.save()

                user = payment.user
                subscription, created = Subscription.objects.select_for_update().get_or_create(
                    user=user,
                    defaults={
                        'start_date': timezone.now(),
                        'end_date': timezone.now() + relativedelta(months=1),
                        'is_active': True,
                        'provider': 'paystack'
                    }
                )

                if not created:
                    subscription.end_date = max(subscription.end_date, timezone.now()) + relativedelta(months=1)
                    subscription.is_active = True

                subscription.last_payment = payment
                subscription.save()

                user.is_paid = True
                user.save()

            # Send payment notification email
            send_payment_confirmation_email(payment)
            send_payment_notification_email(payment)

        except Payment.DoesNotExist:
            logger.error(f"Payment with reference {reference} not found")
        except Exception as e:
            logger.error(f"Error processing successful charge: {str(e)}")

    def handle_subscription_created(self, data):
        customer_email = data.get('customer', {}).get('email')
        subscription_code = data.get('subscription_code')

        if not customer_email or not subscription_code:
            logger.error("Missing customer email or subscription code in subscription.create event")
            return

        try:
            with transaction.atomic():
                user = User.objects.get(email=customer_email)
                subscription, created = Subscription.objects.select_for_update().get_or_create(
                    user=user,
                    defaults={
                        'paystack_subscription_code': subscription_code,
                        'start_date': timezone.now(),
                        'end_date': timezone.now() + relativedelta(months=1),
                        'is_active': True,
                        'provider': 'paystack'
                    }
                )

                if not created:
                    subscription.paystack_subscription_code = subscription_code
                    subscription.save()

            send_subscription_status_email(user.email, 'created')
        except User.DoesNotExist:
            logger.error(f"User with email {customer_email} not found")

    def handle_subscription_cancelled(self, data):
        customer_email = data.get('customer', {}).get('email')
        try:
            subscription = Subscription.objects.get(paystack_subscription_code=data.get('subscription_code'))
            subscription.is_active = False
            subscription.end_date = timezone.now()
            subscription.save()

            subscription.user.is_paid = False
            subscription.user.save()

            send_subscription_status_email(customer_email, 'cancelled')
        except Subscription.DoesNotExist:
            logger.error(f"Subscription with code {data.get('subscription_code')} not found")

    def handle_payment_failed(self, data):
        customer_email = data.get('customer', {}).get('email')
        try:
            user = User.objects.get(email=customer_email)
            subscription = Subscription.objects.get(user=user)
            subscription.is_active = False
            subscription.save()

            user.is_paid = False
            user.save()

            send_subscription_status_email(customer_email, 'payment_failed')
        except User.DoesNotExist:
            logger.error(f"User with email {customer_email} not found")
        except Subscription.DoesNotExist:
            logger.error(f"Subscription for user {customer_email} not found")
