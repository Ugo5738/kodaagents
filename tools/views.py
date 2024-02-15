import json
import os

import requests
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from verification.models import EmploymentVerification
from verification.pdf.analyze import get_pdf_category
from verification.tasks import process_pdf_task

# from verification.verifications import (
#     bank_statement,
#     birth_certificate,
#     create_bucket,
#     employee_letter,
#     get_website_rep_details,
#     scrape_website,
# )


# class VerifyAgeView(APIView):
#     def get(self, request, document_id):
#         result = birth_certificate(document_id)
#         return Response({"result": result})


# class VerifyBankStatementView(APIView):
#     def get(self, request, document_id):
#         analyzed_result = bank_statement(document_id)
#         return Response({"result": analyzed_result})


# class VerifyEmployeeLetterView(APIView):
#     def get(self, request, document_id):
#         employee_letter_result = employee_letter(document_id)
#         return Response({"result": employee_letter_result})


# def confirm_employment(request):
#     token = request.GET.get("token")
#     CALLBACK_URL = os.environ.get("CALLBACK_URL", "")
#     try:
#         verification = EmploymentVerification.objects.get(token=token)
#         verification.is_verified = True
#         verification.verified_at = timezone.now()  # Manually set when verified
#         verification.save()

#         response_data = {"status": "confirmed", "token": token}
#         requests.post(CALLBACK_URL, data=response_data)

#         return HttpResponse("Employment confirmed.")
#     except EmploymentVerification.DoesNotExist:
#         return HttpResponse("Invalid token.")


# def deny_employment(request):
#     token = request.GET.get("token")
#     CALLBACK_URL = os.environ.get("CALLBACK_URL", "")
#     try:
#         verification = EmploymentVerification.objects.get(token=token)
#         verification.is_verified = False
#         verification.save()

#         response_data = {"status": "denied", "token": token}
#         requests.post(CALLBACK_URL, data=response_data)

#         return HttpResponse("Employment denied.")
#     except EmploymentVerification.DoesNotExist:
#         return HttpResponse("Invalid token.")


# def get_employment_verification_info(request, token):
#     try:
#         employment_verification = EmploymentVerification.objects.get(token=token)
#         data = {
#             "token": employment_verification.token,
#             "status": employment_verification.status,
#             "is_verified": employment_verification.is_verified,
#             "verified_at": (
#                 employment_verification.verified_at.strftime("%Y-%m-%d %H:%M:%S")
#                 if employment_verification.verified_at
#                 else None
#             ),
#         }
#         return JsonResponse(data)
#     except EmploymentVerification.DoesNotExist:
#         return JsonResponse({"error": "Token not found"}, status=404)


# # class ScraperView(APIView):
# #     def get(self, request, *args, **kwargs):

# #         # scraper()
# #         url="https://www.enricodeiana.design/"
# #         scrape_website(url)

# #         return JsonResponse({"done": "done"})


# class ApolloView(APIView):
#     def get(self, request, *args, **kwargs):
#         url = "https://www.zenithbank.com/"
#         url = "https://www.enricodeiana.design/"
#         data = get_website_rep_details(url)
#         return JsonResponse({"data": data})


class BankStatementView(View):
    def get(self, request, document_id):
        pdf_type, pdf_data_manager = get_pdf_category(document_id)
        if pdf_type == 1 or pdf_type == 3:
            # For straightforward processing, call the task synchronously (or just process it directly)
            result = process_pdf_task.apply(
                args=[pdf_type, pdf_data_manager]
            ).get()  # sync call
            return JsonResponse({"status": "completed", "result": result})
        elif pdf_type == 2:
            # async call
            task = process_pdf_task.delay(pdf_type, pdf_data_manager)
            return JsonResponse(
                {
                    "status": "Analysis this PDF would take about 60 secs so please check back",
                    "task_id": task.id,
                }
            )
