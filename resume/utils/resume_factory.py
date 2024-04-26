import time

from django.conf import settings

from koda.config.logging_config import configure_logger
from resume.models import Resume
from resume.utils.util_funcs import get_feedback_and_improve

logger = configure_logger(__name__)


def improve_resume(candidate_id):
    try:
        start_time = time.time()

        # get from the database, because the default is going to be created using some of the applicant details
        # resume_content = await get_doc_content(candidate_id, doc_type="R")
        resume_content = default_resume

        improved_content = async_to_sync(get_feedback_and_improve)(resume_content)

        pdf = generate_resume_pdf(improved_content, filename="Improved Resume.pdf")

        # Generate a unique S3 key for the PDF
        s3_key = f"media/resume/general_improved/{uuid4()}.pdf"

        # Upload the PDF directly to S3
        upload_directly_to_s3(pdf, settings.AWS_STORAGE_BUCKET_NAME, s3_key)

        resume_instance, resume_created = Resume.objects.update_or_create(
            resume_id=candidate_id,
            defaults={
                "general_improved_content": improved_content,
                "general_improved_pdf_s3_key": s3_key,
            },
        )
    except Exception as e:
        logger.error(e)

    total = time.time() - start_time
    logger.info(f"Total time taken: {total}")

    # Construct the URL to the PDF stored in S3
    pdf_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
    return pdf_url
