from verification.pdf.date_utils import DateValidator


class GridDefiner:
    """Defines grid for data extraction."""

    @staticmethod
    def find_stride_and_first_last_date_indices(
        data, start_index_for_searching, stride_step=None
    ):
        first_date_index = None
        for i in range(start_index_for_searching, len(data)):
            if DateValidator.is_valid_date(data[i]["text"]):
                first_date_index = i
                break

        if first_date_index is None:
            return None, None, None

        # the stride should be used from the openai vision response
        stride = None
        for i in range(first_date_index + 1, len(data)):
            if DateValidator.is_valid_date(data[i]["text"]):
                stride = i - first_date_index
                break

        if stride is None:
            return None, first_date_index, None

        last_date_index = first_date_index
        for i in range(first_date_index, len(data), stride):
            if DateValidator.is_valid_date(data[i]["text"]):
                last_date_index = i
            else:
                break

        return (
            stride_step,
            first_date_index,
            last_date_index,
        )  # use stride step instead of stride

    @staticmethod
    def define_grid(
        text_blocks, first_date_index, stride, last_date_index, headers, header_columns
    ):
        """
        Define the grid based on date entries and their stride in the text blocks, adjusting column widths and positions based on specific rules.

        Parameters:
        - text_blocks: List of dictionaries with text block details.
        - first_date_index: Index of the first date entry in the text blocks.
        - stride: The stride between consecutive date entries.
        - last_date_index: Index of the last date entry in the text blocks.
        - headers: Dictionary with details of header columns including their bbox.

        Returns:
        - A list of lists representing the grid with adjusted row and column boundaries.
        """
        grid = []
        sorted_headers = sorted(headers.items(), key=lambda x: x[1]["index"])
        credit_info = headers.get(header_columns[2])
        debit_info = headers.get(header_columns[3])
        transaction_info = headers.get(header_columns[1])

        second_row_date_index = first_date_index
        second_row_transaction_index = transaction_info["index"]

        # Determine the order of Credit and Debit columns
        if credit_info and debit_info:
            if credit_info["index"] < debit_info["index"]:
                # Credit comes first, set width based on Credit and adjust Debit accordingly
                column_width = (
                    credit_info["bbox"][2] - credit_info["bbox"][0] + 4
                )  # Adding allowance
                credit_bbox = (
                    credit_info["bbox"][0] - 2,
                    credit_info["bbox"][1],
                    credit_info["bbox"][0] - 2 + column_width,
                    credit_info["bbox"][3],
                )
                debit_bbox = (
                    debit_info["bbox"][0] - 2,
                    debit_info["bbox"][1],
                    debit_info["bbox"][0] - 2 + column_width,
                    debit_info["bbox"][3],
                )
            else:
                # Debit comes first, set width based on Debit and adjust Credit accordingly
                column_width = (
                    debit_info["bbox"][2] - debit_info["bbox"][0] + 4
                )  # Adding allowance
                debit_bbox = (
                    debit_info["bbox"][0] - 2,
                    debit_info["bbox"][1],
                    debit_info["bbox"][0] - 2 + column_width,
                    debit_info["bbox"][3],
                )
                credit_bbox = (
                    credit_info["bbox"][0] - 2,
                    credit_info["bbox"][1],
                    credit_info["bbox"][0] - 2 + column_width,
                    credit_info["bbox"][3],
                )

        # Iterate over the date entries using the first index, stride, and last index
        for i in range(first_date_index, last_date_index + 1, stride):
            text_block = text_blocks[i]
            row_top = text_block["bbox"][1]
            row_bottom = text_block["bbox"][3]

            grid_row = []
            for header_name, header_info in sorted_headers:
                column_left = header_info["bbox"][0]
                column_right = header_info["bbox"][2]  # Default right boundary

                if header_name == header_columns[0]:
                    # Use second row for Date column right boundary adjustment
                    next_row_block_start_index = text_blocks[second_row_date_index]
                    column_left = next_row_block_start_index["bbox"][0]
                    column_right = (
                        text_blocks[second_row_date_index + 1]["bbox"][0] - 0.0000000001
                    )  # Left boundary of next column
                elif header_name == header_columns[1]:
                    # Use second row for Transaction Details column, adjusting right boundary as needed
                    next_row_trans_start_block = text_blocks[
                        second_row_transaction_index
                    ]
                    column_left = next_row_trans_start_block["bbox"][0]
                    column_right = (
                        text_blocks[second_row_transaction_index + 1]["bbox"][2] - 2
                    )
                elif header_name == header_columns[2]:
                    column_left, column_right = credit_bbox[0], credit_bbox[2]

                elif header_name == header_columns[3]:
                    column_left, column_right = debit_bbox[0], debit_bbox[2]

                cell_bbox = (column_left, row_top, column_right, row_bottom)
                grid_row.append({"name": header_name, "bbox": cell_bbox})

            grid.append(grid_row)

        return grid
