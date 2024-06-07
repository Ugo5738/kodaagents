import json

import boto3
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from rest_framework import status

from resume.cl_opt import (
    customize_improved_cover_letter,
    customize_optimized_cover_letter,
    get_default_cover_letter,
    improve_cover_letter,
    optimize_cover_letter,
)
from resume.job_post import optimize_job_post
from resume.models import (
    CoverLetter,
    JobPost,
    OptimizedCoverLetterContent,
    OptimizedResumeContent,
    Resume,
)
from resume.resume_opt import (
    customize_improved_resume,
    customize_optimized_resume,
    improve_resume,
    optimize_resume,
)
from resume.serializers import (
    CoverLetterSerializer,
    JobPostSerializer,
    OptimizedCoverLetterContentSerializer,
    OptimizedResumeSerializer,
    ResumeSerializer,
)


class ResumeDetailView(View):
    def get(self, request, resume_id):
        resume = get_object_or_404(Resume, resume_id=resume_id)
        serializer = ResumeSerializer(resume)
        return JsonResponse(serializer.data, safe=False)


class OptimizedResumeContentDetailView(View):
    def get(self, request, resume_id):
        optimized_resume_content = get_object_or_404(
            OptimizedResumeContent, resume__resume_id=resume_id
        )
        serializer = OptimizedResumeSerializer(optimized_resume_content)
        return JsonResponse(serializer.data, safe=False)


class CoverLetterDetailView(View):
    def get(self, request, cover_letter_id):
        cover_letter = get_object_or_404(CoverLetter, cover_letter_id=cover_letter_id)
        serializer = CoverLetterSerializer(cover_letter)
        return JsonResponse(serializer.data, safe=False)


class OptimizedCoverLetterContentDetailView(View):
    def get(self, request, cover_letter_id):
        optimized_cover_letter_content = get_object_or_404(
            OptimizedCoverLetterContent, cover_letter__cover_letter_id=cover_letter_id
        )
        serializer = OptimizedCoverLetterContentSerializer(
            optimized_cover_letter_content
        )
        return JsonResponse(serializer.data, safe=False)


class JobPostDetailView(View):
    def get(self, request, job_post_id):
        job_post = get_object_or_404(JobPost, job_post_id=job_post_id)
        serializer = JobPostSerializer(job_post)
        return JsonResponse(serializer.data, safe=False)


# ============================> RESUME <============================
class ResumeImprovementView(View):
    """
    Improves a resume for a given applicant ID
    """

    async def get(self, request, applicant_id, format=None):
        try:
            # Get the optimized content
            pdf_url = improve_resume.delay(applicant_id)
            # pdf_url = improve_resume(applicant_id)
            data = {
                "success": "Resume Improvement Initiated",
                # "improved_content": pdf_url,
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class ResumeOptimizationView(View):
    """
    Improves a resume for a given applicant ID to the given job ID
    """

    serializer_class = None

    async def get(self, request, applicant_id, job_post_id, format=None):
        try:
            # Get the optimized content
            return_data = optimize_resume.delay(applicant_id, job_post_id)
            # return_data = optimize_resume(applicant_id, job_post_id)
            data = {
                "success": "Resume Optimization Initiated",
                # "optimized_content": return_data,
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class ResumeImprovementCustomizationView(View):
    """
    Customizes improved resume for a given applicant ID
    """

    serializer_class = None

    async def post(self, request, applicant_id, format=None):
        try:
            # Parse JSON data from the request body
            body_unicode = request.body.decode("utf-8")
            body_data = json.loads(body_unicode)

            # Extract custom_instruction from the parsed data
            custom_instruction = body_data.get("custom_instruction")

            # Call the utility function with applicant_id and custom_instruction
            return_data = customize_improved_resume.delay(
                applicant_id, custom_instruction
            )
            # return_data = customize_improved_resume(applicant_id, custom_instruction)
            data = {
                "success": "Resume Improvement Customization Initiated",
                # "optimized_content": return_data,
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class ResumeOptimizationCustomizationView(View):
    """
    Customizes tailored resume for a given applicant ID to the given job ID
    """

    serializer_class = None

    async def post(self, request, applicant_id, job_post_id, format=None):
        try:
            # Parse JSON data from the request body
            body_unicode = request.body.decode("utf-8")
            body_data = json.loads(body_unicode)

            # Extract custom_instruction from the parsed data
            custom_instruction = body_data.get("custom_instruction")

            # Call the utility function with applicant_id, job_post_id, and custom_instruction
            return_data = customize_optimized_resume.delay(
                applicant_id, job_post_id, custom_instruction
            )
            # return_data = customize_optimized_resume(
            #     applicant_id, job_post_id, custom_instruction
            # )
            data = {
                "success": "Resume Optimization Customization Initiated",
                # "optimized_content": return_data,
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# ============================> RESUME <============================


# ============================> COVER LETTER <============================
class CoverLetterCreationView(View):
    """
    This view handles cover letter creation. It does not interact with the database directly,
    hence does not use a serializer_class. Instead, it relies on custom utility functions.
    """

    serializer_class = None

    async def get(self, request, applicant_id, format=None):
        try:
            # Get the optimized content
            pdf_url = get_default_cover_letter.delay(applicant_id)
            # pdf_url = get_default_cover_letter(applicant_id)
            data = {
                "success": "Cover Letter Creation Initiated",
                # "improved_content": pdf_url,
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class CoverLetterImprovementView(View):
    """
    This view handles cover letter improvement. It does not interact with the database directly,
    hence does not use a serializer_class. Instead, it relies on custom utility functions.
    """

    serializer_class = None

    async def get(self, request, applicant_id, format=None):
        try:
            # Get the optimized content
            pdf_url = improve_cover_letter.delay(applicant_id)
            # pdf_url = improve_cover_letter(applicant_id)
            data = {
                "success": "Cover Letter Improvement Initiated",
                # "improved_content": pdf_url,
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class CoverLetterOptimizationView(View):
    """
    This view handles cover letter optimization. It does not interact with the database directly,
    hence does not use a serializer_class. Instead, it relies on custom utility functions.
    """

    serializer_class = None

    # def get(self, request, application_id, job_post_id, format=None):
    async def get(self, request, applicant_id, job_post_id, format=None):
        try:
            return_data = optimize_cover_letter.delay(applicant_id, job_post_id)
            # return_data = optimize_cover_letter(applicant_id, job_post_id)
            data = {
                "success": "Cover Letter Optimization Initiated",
                # "optimized_content": return_data,
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class CoverLetterImprovementCustomizationView(View):
    """
    This view handles resume optimization. It does not interact with the database directly,
    hence does not use a serializer_class. Instead, it relies on custom utility functions.
    """

    serializer_class = None

    async def post(self, request, applicant_id, format=None):
        try:
            # Parse JSON data from the request body
            body_unicode = request.body.decode("utf-8")
            body_data = json.loads(body_unicode)

            # Extract custom_instruction from the parsed data
            custom_instruction = body_data.get("custom_instruction")

            # Call the utility function with applicant_id and custom_instruction
            return_data = customize_improved_cover_letter.delay(
                applicant_id, custom_instruction
            )
            # return_data = customize_improved_cover_letter(
            #     applicant_id, custom_instruction
            # )
            data = {
                "success": "Cover Letter Improvement Customization Initiated",
                # "optimized_content": return_data,
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


class CoverLetterOptimizationCustomizationView(View):
    """
    This view handles cover letter optimization. It does not interact with the database directly,
    hence does not use a serializer_class. Instead, it relies on custom utility functions.
    """

    serializer_class = None

    async def post(self, request, applicant_id, job_post_id, format=None):
        try:
            # Parse JSON data from the request body
            body_unicode = request.body.decode("utf-8")
            body_data = json.loads(body_unicode)

            # Extract custom_instruction from the parsed data
            custom_instruction = body_data.get("custom_instruction")

            # Call the utility function with applicant_id, job_post_id, and custom_instruction
            return_data = customize_optimized_cover_letter.delay(
                applicant_id, job_post_id, custom_instruction
            )
            # return_data = customize_optimized_cover_letter(
            #     applicant_id, job_post_id, custom_instruction
            # )
            data = {
                "success": "Cover Letter Optimization Customization Initiated",
                # "optimized_content": return_data,
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# ============================> COVER LETTER <============================


# ============================> JOB POST <============================
class JobOptimizationView(View):
    """
    This view handles job post optimization. It does not interact with the database directly,
    hence does not use a serializer_class. Instead, it relies on custom utility functions.
    """

    serializer_class = None

    async def get(self, request, job_id, format=None):
        # feedback_only = request.query_params.get("feedback", "false").lower() == "true"
        try:
            optimized_job_post_content = optimize_job_post.delay(job_id)
            # optimized_job_post_content = optimize_job_post(job_id)
            # might need to use the mark down dangerous html before pushing to frontend
            return JsonResponse(
                {
                    "success": "Job Optimization Initiated",
                    # "optimized_content": optimized_job_post_content,
                }
            )
        except Exception as e:
            return JsonResponse(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================> JOB POST <============================


class Boto3UploadView(View):
    def get(self, request):
        # The path to your file within your project directory
        file_path = "resume123.pdf"  # Replace with your file's path

        # Create an S3 client
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        # Define the bucket name and the key for the file in S3
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        file_key = "resume123.pdf"  # The name you want the file to have in S3

        # Try to upload the file
        try:
            with open(file_path, "rb") as data:
                s3.upload_fileobj(
                    data,
                    bucket_name,
                    file_key,
                    # Removed the ExtraArgs with ACL since it's not supported with your bucket configuration
                )
            return JsonResponse({"message": "File uploaded successfully!"}, status=200)
        except Exception as e:
            print(f"============ Error Details Start ============")
            print(e)
            print(f"============ Error Details End ============")
            return JsonResponse({"message": "Upload failed."}, status=500)


# http://127.0.0.1:8000/api/optimizers/optimize-job-post/654194177b7c7c8236e8541f/
# http://127.0.0.1:8000/api/optimizers/optimize-job-post/654194177b7c7c8236e8541f/?feedback=true
# http://127.0.0.1:8000/api/optimizers/optimize-resume/63a6af57677ed8a015025a62/654194177b7c7c8236e8541f/
# applicant_id 63a6af57677ed8a015025a62
# job_post_id 654194177b7c7c8236e8541f
# job_post_id = 65aa68567bd03fff776fbfcf
