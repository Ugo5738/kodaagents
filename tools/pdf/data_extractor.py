class DataExtractor:
    """Extracts data using the defined grid."""

    @staticmethod
    def extract_data_using_grid(text_blocks, grid):
        extracted_data = []
        for row in grid:
            row_data = []
            for cell in row:
                cell_text = DataExtractor.find_text_in_bbox(text_blocks, cell["bbox"])
                row_data.append(cell_text)
            extracted_data.append(row_data)
        return extracted_data

    @staticmethod
    def find_text_in_bbox(text_blocks, bbox):
        cell_texts = []
        for block in text_blocks:
            if DataExtractor.block_overlaps_bbox(block["bbox"], bbox):
                cell_texts.append(block["text"])
        return " ".join(cell_texts).strip()

    @staticmethod
    def block_overlaps_bbox(block_bbox, cell_bbox):
        block_left, block_top, block_right, block_bottom = block_bbox
        cell_left, cell_top, cell_right, cell_bottom = cell_bbox

        is_left = block_right < cell_left
        is_right = block_left > cell_right
        is_above = block_bottom < cell_top
        is_below = block_top > cell_bottom

        return not (is_left or is_right or is_above or is_below)
