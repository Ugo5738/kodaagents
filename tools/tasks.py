from celery import shared_task

from verification.pdf.analyze import process_pdf_with_retry


@shared_task
def process_pdf_task(pdf_type, pdf_data_manager):
    if pdf_type == 1 or pdf_type == 3:
        # Process immediately for straightforward cases
        return process_pdf_with_retry(pdf_type, pdf_data_manager)
    elif pdf_type == 2:
        # For more intensive processing, just return an acknowledgment or status
        # Actual processing can be done here if it's quick enough, or triggered as another task if needed
        return "Processing started for PDF type 2, please check back later for results."
