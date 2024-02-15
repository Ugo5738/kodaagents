from verification.pdf.data_extractor import DataExtractor
from verification.pdf.date_utils import DateValidator
from verification.pdf.grid_definer import GridDefiner
from verification.pdf.openai_chat import swap_columns
from verification.pdf.pdf_extractor import PDFExtractor, TableHeaderFinder


class PDFDataManager:
    def __init__(self, pdf_url):
        self.extractor = PDFExtractor(pdf_url)
        self.header_columns, self.target_columns = self.extractor.get_headers()

    def categorize_pdf(self):
        max_retries = 5  # Maximum number of retries
        retries = 0  # Current retry count

        while retries < max_retries:
            try:
                pdf_type = self.extractor.get_pdf_category()
                return pdf_type
            except Exception as e:
                print(f"Error categorizing PDF: {e}. Retrying...")
                retries += 1  # Increment retry count

        # Optional: Return a default value or raise an exception if all retries fail
        raise Exception("Failed to categorize PDF after maximum retries.")

    def process_pdf(self):
        stride_step = len(self.header_columns) - 1

        all_pages_data = self.extractor.extract_text_blocks_with_bboxes()
        processed_data = []

        for page_data in all_pages_data:
            text_blocks = page_data["data"]
            header_bboxes = TableHeaderFinder.find_table_headers(
                text_blocks, self.target_columns
            )
            print(header_bboxes)
            start_index_for_searching = (
                max(header["index"] for header in header_bboxes.values()) + 1
            )
            stride, first_date_index, last_date_index = (
                GridDefiner.find_stride_and_first_last_date_indices(
                    text_blocks, start_index_for_searching, stride_step=stride_step
                )
            )

            if stride:
                grid = GridDefiner.define_grid(
                    text_blocks,
                    first_date_index,
                    stride,
                    last_date_index,
                    header_bboxes,
                    self.target_columns,
                )
                extracted_data = DataExtractor.extract_data_using_grid(
                    text_blocks, grid
                )
                processed_data.append(extracted_data)

        flat_data = [row for page_data in processed_data for row in page_data]
        return flat_data

    def filter_tables(self):
        # use this when vision says to
        tables = self.extractor.extract_tables()
        print("this is the headers: ", self.target_columns)

        filtered_tables = []
        combined_rows = []
        for table in tables:
            header_index = None

            # Ensure there are rows to search through
            if not table["data"]:
                continue  # Skip tables with empty data

            for i, row in enumerate(table["data"]):
                # Skip rows with None values for header search
                if any(cell is None for cell in row) or len(row) < len(
                    self.header_columns
                ):
                    continue

                # Check if row matches the expected header and store its index
                if sorted(row[: len(self.header_columns)]) == sorted(
                    self.header_columns
                ):
                    header_index = i
                    # print("header_index found: ", header_index)
                    break

            new_table = []
            # Proceed with filtering if header is found
            if header_index is not None:
                # new_table = [table["data"][header_index]]  # Include header row
                data_start_index = header_index + 1
            else:
                # If no header, start from the first row
                data_start_index = 0

            for row in table["data"][data_start_index:]:
                if len(row) == len(self.header_columns) and DateValidator.is_valid_date(
                    row[0]
                ):
                    new_table.append(row)
                elif header_index is not None:
                    # If a header was found but this row doesn't meet criteria, stop processing
                    break

            # Add the filtered table if it has valid data rows
            if new_table:
                filtered_tables.append({"page": table["page"], "data": new_table})
        # print(filtered_tables)
        return filtered_tables

    def process_pdf_tables(self):
        filtered_tables = self.filter_tables()
        combined_rows = []

        # Iterate through each filtered table
        for table in filtered_tables:
            # Find indices of target columns in the header
            target_indices = [
                self.header_columns.index(col)
                for col in self.target_columns
                if col in self.header_columns
            ]

            # Extract rows using these indices
            for row in table["data"][
                1:
            ]:  # Assuming first row of 'data' is always the header
                selected_row = [
                    row[index] if index < len(row) else None for index in target_indices
                ]
                combined_rows.append(selected_row)
        # print(combined_rows)
        arranged_columns = swap_columns(self.target_columns)
        return combined_rows, arranged_columns

    def process_pdf_with_vision(self):
        data = self.extractor.vision_pdf()
        print("This is the response from process_pdf_with_vision: ", data)

        # Flatten the data structure
        flattened_data = []
        for entry in data:
            for date, description, credit, debit in zip(
                entry["Date"], entry["Description"], entry["Credit"], entry["Debit"]
            ):
                flattened_data.append(
                    {
                        "Date": date,
                        "Description": description,
                        "Credit": credit,
                        "Debit": debit,
                    }
                )
        return flattened_data
