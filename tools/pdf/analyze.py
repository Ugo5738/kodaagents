import time

from django.db import connections

from bankanalysis.configs.logging_config import configure_logger
from verification.pdf.df_analyzer import TransactionSummary
from verification.pdf.pdf_manager import PDFDataManager

logger = configure_logger(__name__)


def get_document_file_by_id(document_id):
    try:
        with connections["giddaa_db"].cursor() as cursor:
            # cursor.execute('SELECT "Document" FROM "public"."Documents" WHERE "Id" = %s', [document_id])
            # cursor.execute('SELECT * FROM "public"."Documents" WHERE "Id" = %s', [document_id])
            cursor.execute(
                'SELECT "Id", "Name", "Description", "Extension", "Document", "CloudinaryLink", "ExtraProperties" FROM "public"."Documents" WHERE "Id" = %s',
                [document_id],
            )

            row = cursor.fetchone()
            print("This is the row: ", row)
            if row:
                # Assuming columns are id, name, description, extension, document, extraProperties
                document_data = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "extension": row[3],
                    "document": row[4],
                    "cloudinary_link": row[5],
                    "extraProperties": row[6],
                }
                logger.info(f"-------------- DOCUMENT DATA: --------------")
                logger.info(f"{document_data}")
                return document_data
            else:
                return None
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None


def get_pdf_category(document_id):
    document_data = get_document_file_by_id(document_id)
    public_url = document_data["cloudinary_link"]

    # Initialize PDFDataManager with the given PDF path
    pdf_data_manager = PDFDataManager(pdf_url=public_url)
    pdf_type = pdf_data_manager.categorize_pdf()
    print("This is the pdf type: ", pdf_type)

    return pdf_type, pdf_data_manager


def process_pdf_with_retry(pdf_type, pdf_data_manager, max_retries=5):
    start_time = time.time()
    # Initialize the retry count
    retries = 0
    while retries < max_retries:
        try:
            # Process PDF based on its type
            if pdf_type == 1:
                extracted_data, target_columns = pdf_data_manager.process_pdf_tables()
                transaction_summary = TransactionSummary(
                    extracted_data, header_columns=target_columns
                )
            elif pdf_type == 2:
                extracted_data = pdf_data_manager.process_pdf()
                transaction_summary = TransactionSummary(extracted_data)
            elif pdf_type == 3:
                extracted_data = pdf_data_manager.process_pdf_with_vision()
                transaction_summary = TransactionSummary(extracted_data)
            else:
                # Handle unexpected PDF type
                print("Unknown PDF type.")
                return None

            # Initialize TransactionSummary with extracted data and target columns
            transaction_summary = TransactionSummary(extracted_data)
            monthly_summary = transaction_summary.generate_monthly_summary()
            gambling_activities = transaction_summary.check_gambling_activities()

            # Combine the results
            combined_result = {
                "monthly_summary": monthly_summary.to_dict(
                    "records"
                ),  # Convert DataFrame to list of dicts
                "gambling_activities": gambling_activities,
            }
            print(time.time() - start_time)

            # If the process succeeds, break out of the loop
            return combined_result
        except Exception as e:
            print(f"An error occurred: {e}. Retrying...")
            retries += 1
            time.sleep(1)  # Optional: wait a second before retrying

    # If the function reaches this point, it means all retries have failed
    print(f"Failed to process PDF after {max_retries} attempts.")
    return None


# pdf_path = "wema_statement.pdf"
# # pdf_path = "gt_statement.pdf"
# # pdf_path = "foreign_statement.pdf"
# # pdf_path = "gtb_statement.pdf"
# # pdf_path = "zen_statement.pdf"

# pdf_type, pdf_data_manager = get_pdf_category(pdf_path)

# result = process_pdf_with_retry(pdf_type, pdf_data_manager)
# print(result)
