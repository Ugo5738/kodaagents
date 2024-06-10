import time
from uuid import uuid4

from asgiref.sync import async_to_sync, sync_to_async
from celery import shared_task
from django.conf import settings

from koda.config.logging_config import configure_logger
from resume.job_post import optimize_job
from resume.models import JobPost, OptimizedResumeContent, Resume
from resume.pdf_gen import generate_resume_pdf
from resume.utils.util_funcs import (
    Readability,
    customize_doc,
    improve_doc,
    optimize_doc,
    resume_sections_feedback,
    upload_directly_to_s3,
)

logger = configure_logger(__name__)


SYSTEM_ROLE = "system"
USER_ROLE = "user"


async def improve_resume_func(candidate_id):
    try:
        start_time = time.time()

        # Generate a unique S3 key for the PDF
        s3_key = f"media/resume/general_improved/{uuid4()}.pdf"

        # get from the database, because the default is going to be created using some of the applicant details
        resume_content = ""

        readability = Readability(resume_content)
        readability_feedback = await readability.get_readability_text(doc_type="resume")

        sections_feedback = await resume_sections_feedback(resume_content)
        feedbacks = [readability_feedback, sections_feedback]
        resume_feedback = "\n\n".join(feedbacks)

        improved_content = await improve_doc(
            doc_type="resume",
            doc_content=resume_content,
            doc_feedback=resume_feedback,
        )

        pdf = generate_resume_pdf(improved_content, filename="Improved Resume.pdf")
        # Upload the PDF directly to S3
        upload_directly_to_s3(pdf, settings.AWS_STORAGE_BUCKET_NAME, s3_key)

        resume_instance, resume_created = await sync_to_async(
            Resume.objects.update_or_create, thread_sensitive=True
        )(
            resume_id=candidate_id,
            defaults={
                "general_improved_content": improved_content,
                "general_improved_pdf_s3_key": s3_key,
            },
        )

        total = time.time() - start_time
        logger.info(f"Total time taken: {total}")

        pdf_url = (
            f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
        )
        return pdf_url

    except Exception as e:
        logger.error(e)
        raise


@shared_task
def improve_resume(applicant_id):
    start_time = time.time()

    sync_improvement = async_to_sync(improve_resume_func)
    url = sync_improvement(applicant_id)
    total = time.time() - start_time
    logger.info(f"Total time taken: {total}")
    return url


async def customize_improved_resume_func(candidate_id, custom_instruction):
    start_time = time.time()
    resume_update = sync_to_async(
        Resume.objects.update_or_create, thread_sensitive=True
    )

    resume_instance = await sync_to_async(Resume.objects.get)(resume_id=candidate_id)
    improved_content = resume_instance.general_improved_content
    customized_content = await customize_doc(
        doc_type="resume",
        doc_content=improved_content,
        custom_instruction=custom_instruction,
    )

    pdf = generate_resume_pdf(
        customized_content,
        filename="Customized Improved Resume.pdf",
    )

    # Generate a unique S3 key for the PDF
    s3_key = f"media/resume/general_improved/{uuid4()}.pdf"

    # Upload the PDF directly to S3
    upload_directly_to_s3(pdf, settings.AWS_STORAGE_BUCKET_NAME, s3_key)

    # Run the synchronous database update_or_create functions concurrently
    resume_instance, resume_created = await resume_update(
        resume_id=candidate_id,
        defaults={
            "general_improved_content": customized_content,
            "general_improved_pdf_s3_key": s3_key,
        },
    )

    total = time.time() - start_time
    logger.info(f"Total time taken: {total}")

    # Construct the URL to the PDF stored in S3
    pdf_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
    return pdf_url


@shared_task
def customize_improved_resume(applicant_id, custom_instruction):
    start_time = time.time()

    sync_optimize = async_to_sync(customize_improved_resume_func)
    url = sync_optimize(applicant_id, custom_instruction)

    total = time.time() - start_time
    logger.info(f"Total time taken: {total}")
    return url


async def resume_optimize_func(applicant_id, job_post_id):
    resume_instance = await sync_to_async(Resume.objects.get)(resume_id=applicant_id)
    try:
        job_post_instance = await sync_to_async(JobPost.objects.get)(
            job_post_id=job_post_id
        )

        if job_post_instance.optimized_content:
            logger.info(
                f"JobPost {job_post_id} already optimized. Skipping optimization."
            )
            optimized_content_for_job_post = job_post_instance.optimized_content

    except JobPost.DoesNotExist:
        logger.info(f"JobPost {job_post_id} not optimized. Starting optimization.")
        optimized_content_for_job_post = await optimize_job(job_post_id)

    optimized_content = await optimize_doc(
        doc_type="resume",
        doc_text=resume_instance.general_improved_content,
        job_description=optimized_content_for_job_post,
    )

    pdf = generate_resume_pdf(optimized_content, filename="Optimized Resume.pdf")

    # Generate a unique S3 key for the PDF
    s3_key = f"media/resume/optimized/{uuid4()}.pdf"

    # Upload the PDF directly to S3
    upload_directly_to_s3(pdf, settings.AWS_STORAGE_BUCKET_NAME, s3_key)

    optimized_content_instance, created = await sync_to_async(
        OptimizedResumeContent.objects.update_or_create, thread_sensitive=True
    )(
        resume=resume_instance,
        defaults={
            "optimized_content": optimized_content,
            "optimized_pdf_s3_key": s3_key,
            "is_tailored": True,
            "job_post": job_post_instance,
        },
    )

    # Construct the URL to the PDF stored in S3
    pdf_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
    return pdf_url


@shared_task
def optimize_resume(applicant_id, job_post_id):
    start_time = time.time()

    sync_optimize = async_to_sync(resume_optimize_func)
    url = sync_optimize(applicant_id, job_post_id)
    total = time.time() - start_time
    logger.info(f"Total time taken: {total}")
    return url


async def customize_resume_optimize_func(applicant_id, job_post_id, custom_instruction):
    resume_instance = await sync_to_async(Resume.objects.get)(resume_id=applicant_id)
    optimized_resume_instance = await sync_to_async(OptimizedResumeContent.objects.get)(
        resume=resume_instance
    )
    job_post_instance = await sync_to_async(JobPost.objects.get)(
        job_post_id=job_post_id
    )

    optimized_content = optimized_resume_instance.optimized_content
    customized_content = await customize_doc(
        doc_type="resume",
        doc_content=optimized_content,
        custom_instruction=custom_instruction,
    )

    pdf = generate_resume_pdf(
        customized_content, filename="Customized Optimized Resume.pdf"
    )

    # Generate a unique S3 key for the PDF
    s3_key = f"media/resume/optimized/{uuid4()}.pdf"

    # Upload the PDF directly to S3
    upload_directly_to_s3(pdf, settings.AWS_STORAGE_BUCKET_NAME, s3_key)

    optimized_content_instance, created = await sync_to_async(
        OptimizedResumeContent.objects.update_or_create, thread_sensitive=True
    )(
        resume=resume_instance,
        defaults={
            "optimized_content": customized_content,
            "optimized_pdf_s3_key": s3_key,
            "is_tailored": True,
            "job_post": job_post_instance,
        },
    )
    # Construct the URL to the PDF stored in S3
    pdf_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
    return pdf_url


@shared_task
def customize_optimized_resume(applicant_id, job_post_id, custom_instruction):
    start_time = time.time()

    sync_optimize = async_to_sync(customize_resume_optimize_func)
    url = sync_optimize(applicant_id, job_post_id, custom_instruction)

    total = time.time() - start_time
    logger.info(f"Total time taken: {total}")
    return url
