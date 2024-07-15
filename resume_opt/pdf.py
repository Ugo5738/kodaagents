import time
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from django.core.files.base import ContentFile
import logging
import re

logger = logging.getLogger(__name__)

# Constants
MARGINS = {
    'left': 1 * inch,
    'right': 1 * inch,
    'top': 1 * inch,
    'bottom': 1 * inch
}
FONT_NAME = "Helvetica"
FONT_SIZE = 12
LINE_HEIGHT = 14
BULLET_INDENT = 0.25 * inch

def wrap_text(text, width):
    words = text.split()
    lines = []
    current_line = []
    current_width = 0

    for word in words:
        word_width = pdfmetrics.stringWidth(word, FONT_NAME, FONT_SIZE)
        if current_width + word_width <= width:
            current_line.append(word)
            current_width += word_width + pdfmetrics.stringWidth(' ', FONT_NAME, FONT_SIZE)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
            current_width = word_width + pdfmetrics.stringWidth(' ', FONT_NAME, FONT_SIZE)

    if current_line:
        lines.append(' '.join(current_line))

    return lines

def draw_text(canvas, text, x, y):
    canvas.drawString(x, y, text)

def format_paragraphs(canvas, paragraphs, width, height, y):
    for paragraph in paragraphs:
        if re.match(r'^\s*[•\-*]\s', paragraph):  # Detect bullet points
            lines = paragraph.split('\n')
            for line in lines:
                y = format_bullet_point(canvas, line.strip(), width, height, y)
        else:
            lines = wrap_text(paragraph, width)
            for line in lines:
                draw_text(canvas, line, MARGINS['left'], y)
                y -= LINE_HEIGHT
                if y < MARGINS['bottom']:
                    canvas.showPage()
                    y = height - MARGINS['top']
                    canvas.setFont(FONT_NAME, FONT_SIZE)
        y -= LINE_HEIGHT  # Extra space between paragraphs
    return y

def format_bullet_point(canvas, text, width, height, y):
    bullet = text[0]
    content = text[1:].strip()
    lines = wrap_text(content, width - BULLET_INDENT)
    for i, line in enumerate(lines):
        if i == 0:
            draw_text(canvas, bullet, MARGINS['left'], y)
            draw_text(canvas, line, MARGINS['left'] + BULLET_INDENT, y)
        else:
            draw_text(canvas, line, MARGINS['left'] + BULLET_INDENT, y)
        y -= LINE_HEIGHT
        if y < MARGINS['bottom']:
            canvas.showPage()
            y = height - MARGINS['top']
            canvas.setFont(FONT_NAME, FONT_SIZE)
    return y

async def generate_cv_pdf(content, filename, doc_type=None):
    start_time = time.time()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    p.setFont(FONT_NAME, FONT_SIZE)
    y = height - MARGINS['top']

    # Calculate available width for text
    available_width = width - MARGINS['left'] - MARGINS['right']

    if doc_type == "CL":
        if isinstance(content, dict):
            # Recipient
            recipient = content.get('recipient', 'Dear Hiring Manager,')
            draw_text(p, recipient, MARGINS['left'], y)
            y -= LINE_HEIGHT * 2

            # Body
            body_content = content.get('body', '')
            paragraphs = re.split(r'\n{2,}', body_content)  # Split on two or more newlines
            y = format_paragraphs(p, paragraphs, available_width, height, y)

            # Closing
            closing = content.get('closing', '')
            if closing:
                y -= LINE_HEIGHT * 2  # Add extra space before closing
                draw_text(p, closing, MARGINS['left'], y)
                y -= LINE_HEIGHT * 2  # Add space between closing and name

            # Name
            name = content.get('name', '')
            if name:
                draw_text(p, name, MARGINS['left'], y)
        else:
            # Handle the case where content is a string
            paragraphs = re.split(r'\n{2,}', content)  # Split on two or more newlines
            y = format_paragraphs(p, paragraphs, available_width, height, y)
    else:
        # Handle other document types if needed
        paragraphs = re.split(r'\n{2,}', content)  # Split on two or more newlines
        y = format_paragraphs(p, paragraphs, available_width, height, y)

    p.save()

    pdf_value = buffer.getvalue()
    buffer.close()

    total = time.time() - start_time
    logger.info(f"PDF CREATION TIME: {total}")
    return ContentFile(pdf_value, name=filename)
