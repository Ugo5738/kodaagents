import hashlib
import hmac
import json

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, JsonResponse
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

logger = configure_logger(__name__)

class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = json.loads(request.body)
        amount = data.get('amount')
        currency = data.get('currency', 'NGN')

        if not amount:
            return JsonResponse({'error': 'Amount is required'}, status=400)

        try:
            amount = float(amount)
        except ValueError:
            return JsonResponse({'error': 'Invalid amount'}, status=400)

        try:
            paystack = PaystackAPI()
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
                    reference=response['data']['reference']
                )
                return JsonResponse({'authorization_url': response['data']['authorization_url']})
            else:
                logger.error(f"Failed to initialize Paystack transaction: {response}")
                return JsonResponse({'error': 'Failed to initialize transaction'}, status=500)
        except Exception as e:
            logger.error(f"Error initializing Paystack transaction: {str(e)}")
            return JsonResponse({'error': 'An error occurred while processing your payment'}, status=500)


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reference = request.GET.get('reference')
        if not reference:
            return JsonResponse({
                "status": "failed",
                "message": "No reference provided",
            }, status=400)

        paystack = PaystackAPI()
        verify_response = paystack.verify_transaction(reference)

        if verify_response and verify_response['data']['status'] == 'success':
            try:
                payment = Payment.objects.get(reference=reference)
                payment.status = 'success'
                payment.save()
                request.user.is_paid = True
                request.user.save()

                # Return payment details along with verification success
                return JsonResponse({
                    "status": "success",
                    "message": "Payment verified successfully",
                    "details": {
                        "amount": str(payment.amount),
                        "currency": payment.currency,
                        "reference": payment.reference,
                        # Add any other relevant details
                    }
                })
            except Payment.DoesNotExist:
                logger.error(f"Payment with reference {reference} not found")
                return JsonResponse({
                    "status": "failed",
                    "message": "Payment record not found",
                }, status=404)
        else:
            logger.error(f"Failed to verify Paystack transaction: {verify_response}")
            return JsonResponse({
                "status": "failed",
                "message": "Failed to verify payment",
            }, status=400)


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
                        'is_active': True
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
                        'is_active': True
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
