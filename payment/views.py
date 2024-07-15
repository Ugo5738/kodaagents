import hashlib
import hmac
import json

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from koda.config.logging_config import configure_logger
from payment.models import Payment, WebhookLog
from payment.paystack_api import PaystackAPI

logger = configure_logger(__name__)


class InitiatePaymentView(LoginRequiredMixin, View):
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


class VerifyPaymentView(View):
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


class PaymentDetailsView(View):
    def get(self, request, reference):
        try:
            payment = Payment.objects.get(reference=reference)

            # If you need more details from Paystack, you can fetch them here
            paystack = PaystackAPI()
            paystack_response = paystack.verify_transaction(reference)

            if paystack_response and paystack_response['data']['status'] == 'success':
                return JsonResponse({
                    "status": "success",
                    "amount": str(payment.amount),  # Convert to string for JSON serialization
                    "currency": payment.currency,
                    "reference": payment.reference,
                    # Add any other relevant details you want to include
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


@method_decorator(csrf_exempt, name='dispatch')
class PaystackWebhookView(View):
    def post(self, request):
        payload = json.loads(request.body)
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
            self.process_webhook(webhook_log)
            return HttpResponse(status=200)
        else:
            # Invalid signature
            WebhookLog.objects.create(payload=payload, verified=False)
            return HttpResponse(status=400)

    def process_webhook(self, webhook_log):
        event = webhook_log.payload.get('event')
        data = webhook_log.payload.get('data', {})

        if event == 'charge.success':
            reference = data.get('reference')
            try:
                payment = Payment.objects.get(reference=reference)
                payment.status = 'success'
                payment.save()
                payment.user.is_paid = True
                payment.user.save()
                # Additional processing as needed (e.g., update order status, send email)
            except Payment.DoesNotExist:
                logger.error(f"Payment with reference {reference} not found")

        # Add more event types as needed

        webhook_log.processed = True
        webhook_log.save()
