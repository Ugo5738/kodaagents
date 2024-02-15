import base64
import json
from io import BytesIO

import fitz  # PyMuPDF
import requests
from fuzzywuzzy import process
from pdf2image import convert_from_bytes, convert_from_path

from verification.pdf.openai_chat import (
    categorize_pdf,
    get_chat_response,
    get_vision_data,
    get_vision_response,
    refine_data,
)


def pdf_url_to_images(pdf_url):
    response = requests.get(pdf_url)
    if response.status_code == 200:
        images = convert_from_bytes(response.content)
        return images  # This is a list of PIL.Image objects
    else:
        raise Exception("Failed to download PDF")


class PDFExtractor:
    """Handles PDF extraction."""

    def __init__(self, pdf_url):
        self.pdf_url = pdf_url
        self.pdf_data = self.download_pdf()

    def download_pdf(self):
        """Downloads PDF from the URL and returns a bytes object."""
        response = requests.get(self.pdf_url)
        response.raise_for_status()  # Raises an HTTPError if the response was an error
        return response.content

    def extract_text_blocks_with_bboxes(self):
        doc = fitz.open(stream=self.pdf_data, filetype="pdf")
        all_pages_data = []

        for page_num, page in enumerate(doc):
            page_data = []
            page_index = 0

            text_dict = page.get_text("dict")
            blocks = text_dict["blocks"]

            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            span_data = {
                                "index": page_index,
                                "text": span["text"],
                                "bbox": span["bbox"],
                            }
                            page_data.append(span_data)
                            page_index += 1

            all_pages_data.append({"page": page_num, "data": page_data})

        doc.close()
        return all_pages_data

    def extract_tables(self):
        doc = fitz.open(stream=self.pdf_data, filetype="pdf")
        all_tables_data = []

        for page_num, page in enumerate(doc):
            # Find tables on the page
            tables = page.find_tables()

            # Iterate through found tables and extract their data
            for table in tables:
                # Extract table data
                table_data = table.extract()  # Use the extract method to get table data
                all_tables_data.append(
                    {
                        "page": page_num,
                        "bbox": table.bbox,  # Directly access the bbox attribute of the table
                        "data": table_data,
                    }
                )

        doc.close()
        return all_tables_data

    def encode_image_to_base64(self, image):
        """Encode PIL image to base64 without saving to disk."""
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="JPEG")
        return base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")

    def get_headers(self):
        """Get headers from the first page of the PDF by sending it to an API."""

        desired_columns = {"columns": ["Date", "Description", "Credit", "Debit"]}

        # Convert PDF to list of images
        # images = convert_from_path(self.pdf_path, first_page=0, last_page=1)
        images = pdf_url_to_images(self.pdf_url)
        images = True

        if images:
            # first_image = images[0]
            # encoded_image = self.encode_image_to_base64(first_image)
            # image_data_url = f"data:image/jpeg;base64,{encoded_image}"
            image_data_url = self.pdf_url
            vision_columns = get_vision_response(image_data_url, desired_columns)

            instruction = f"""Given two lists of column names for a transactions table, return a list of which columns in the second list correspond to the columns in \
            the first list. Provide the matched column names from the second list in the same order as they appear in the first list.
            """

            message = f"""
            LIST 1: 
            {desired_columns["columns"]}
            
            list 2 which represent actual column names:
            {vision_columns}

            In your returned list, there has to be:
            - a column for date of transaction
            - a column for description of transaction
            - a column for transaction credit
            - a column for transaction debit
            """

            chat_response = get_chat_response(
                instruction,
                message,
                example_structure=desired_columns,
                message_type="for_vision",
            )

            target_columns = chat_response["columns"]
            return vision_columns, target_columns
        else:
            return []

    def vision_pdf(self):
        vision_data_sample_columns = {
            # name of column that has the dates
            "Date": [
                "02-Jan-2023",
                "15-Jan-2023",
                "22-Feb-2023",
                # more dates here
            ],
            # name of column that has the description of transaction
            "Description": [
                "Description of transaction 1",
                "Description of transaction 2",
                "Description of transaction 3",
                # more description here
            ],
            # name of columns that has shows the credits
            "Credit": [
                "Amount of credit transaction",
                "Amount of credit transaction",
                "Amount of credit transaction",
                # more credit here
            ],
            # name of columns that has shows the debits
            "Debit": [
                "Amount of debit transaction",
                "Amount of debit transaction",
                "Amount of debit transaction",
                # more debit here
            ],
        }

        # # Convert PDF to list of images
        # images = convert_from_path(self.pdf_path)
        images = pdf_url_to_images(self.pdf_url)

        data = []
        if images:
            vision_data = None
            for image in images:
                success = False
                while not success:
                    try:
                        encoded_image = self.encode_image_to_base64(image)
                        image_data_url = f"data:image/jpeg;base64,{encoded_image}"

                        vision_data = get_vision_data(
                            image_data_url, vision_data_sample_columns
                        )
                        success = True  # If get_vision_data succeeds, set success to True to exit the loop

                        refined_data = refine_data(
                            vision_data, vision_data_sample_columns
                        )
                        data.append(refined_data)
                    except Exception as e:
                        print(f"Error processing image: {e}. Retrying...")
        return data

    def get_pdf_category(self):
        # Convert PDF to list of images
        # images = convert_from_path(self.pdf_path, first_page=0, last_page=1)
        images = pdf_url_to_images(self.pdf_url)

        if images:
            first_image = images[0]
            encoded_image = self.encode_image_to_base64(first_image)
            image_data_url = f"data:image/jpeg;base64,{encoded_image}"

            sample_columns = {"type": 1}
            pdf_type = categorize_pdf(image_data_url, sample_columns)

        return pdf_type


# PDF processing
class TableHeaderFinder:
    """Finds table headers using fuzzy matching."""

    @staticmethod
    def find_table_headers(text_blocks, target_headers):
        header_bboxes = {}
        for block in text_blocks:
            for target in target_headers:
                if (
                    process.fuzz.partial_ratio(target.lower(), block["text"].lower())
                    > 80
                ):
                    header_bboxes[target] = {
                        "bbox": block["bbox"],
                        "index": block["index"],
                    }
                    break
        return header_bboxes


[
    {
        "Date": ["03-Oct-2022", "12-Oct-2022", "12-Oct-2022"],
        "Description": ["Opening Balance", "Deposit interest", "Closing Balance"],
        "Credit": ["", "0.64", ""],
        "Debit": ["", "", ""],
        "Balance": ["748.30", "748.94", "748.94"],
    },
    {
        "Date": ["01-Dec-2022", "12-Dec-2022"],
        "Description": ["Opening Balance", "Deposit interest"],
        "Credit": ["", "0.01"],
        "Debit": ["", ""],
    },
    {
        "Date": ["4 Jul", "4 Jul", "5 Jul"],
        "Description": [
            "Online Transfer to Deposit Account-3393",
            "Online Banking transfer - 3286",
            "Deposit interest",
        ],
        "Withdrawals": [825.0, 799.91, ""],
        "Deposits": ["", "", 1.48],
        "Balance": [4, 500.0, 2, 875.09, 2, 876.57],
    },
    {
        "Date": ["Not Visible"],
        "Description": ["Fee Electronic transaction 1 @ $5.00"],
        "Withdrawals": ["5.00"],
        "Deposits": ["Not Visible"],
        "Balance": ["1,946.57"],
    },
    {
        "Date": ["27-Oct", "27-Oct", "1-Nov"],
        "Description": [
            "Online Transfer to Deposit Account-2370",
            "Online Banking transfer - 4352",
            "Deposit interest",
        ],
        "Credit": [None, None, "0.59"],
        "Debit": ["240.00", "500.00", None],
    },
    {
        "Date": ["26-Jul", "1-Aug", "2-Aug"],
        "Description": [
            "Online Transfer to Deposit Account-8107",
            "Deposit interest",
            "Online Transfer to Deposit Account-4696",
        ],
        "Withdrawals": [400.0, "", 800.0],
        "Deposits": ["", 1.21, ""],
    },
    {
        "Date": ["01-Sep-2022", "12-Sep-2022"],
        "Description": ["Opening Balance", "Deposit interest"],
        "Credit": ["", "0.52"],
        "Debit": ["", ""],
    },
]
