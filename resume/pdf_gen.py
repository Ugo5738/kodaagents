import re
import time
from io import BytesIO

from django.core.files.base import ContentFile
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from koda.config.logging_config import configure_logger
from resume.samples import improved_resume_dict

logger = configure_logger(__name__)


def get_value(dictionary, key, default_value):
    if isinstance(dictionary, dict):
        return dictionary.get(key, default_value)
    return default_value


class HRFlowable(Flowable):
    """
    Horizontal line flowable --- draws a line in a flowable
    """

    def __init__(self, width, thickness=1):
        Flowable.__init__(self)
        self.width = width
        self.thickness = thickness

    def __repr__(self):
        return f"HRFlowable(width={self.width}, thickness={self.thickness})"

    def draw(self):
        """
        Draw the line
        """
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)


# Base style for common properties
base_paragraph_style = ParagraphStyle(
    "BaseParagraph",
    fontName="Helvetica",
    fontSize=11,
    leading=13,
    spaceBefore=6,
    spaceAfter=6,
)

# Styles that extend the base style
name_style = ParagraphStyle(
    "Name",
    parent=base_paragraph_style,
    fontSize=25,
    leading=18,
    spaceAfter=16,
    alignment=TA_LEFT,
    fontName="Helvetica-Bold",
)

job_title_style = ParagraphStyle(
    "JobTitle",
    parent=base_paragraph_style,
    fontSize=14,
    leading=16,
    spaceAfter=6,
    alignment=TA_LEFT,
    fontName="Helvetica-Oblique",
)

contact_details_style = ParagraphStyle(
    "ContactDetails",
    parent=base_paragraph_style,
    spaceAfter=6,
)

linkedin_style = ParagraphStyle(
    "LinkedIn",
    parent=base_paragraph_style,
    textColor=colors.blue,
    underline=True,
)

header_style = ParagraphStyle(
    "Header",
    parent=base_paragraph_style,
    fontSize=14,
    spaceAfter=5,
    fontName="Helvetica-Bold",
)

summary_style = ParagraphStyle(
    "Summary",
    parent=base_paragraph_style,
    spaceBefore=2,
    alignment=TA_JUSTIFY,
)

company_name_style = ParagraphStyle(
    "CompanyName",
    fontName="Helvetica-Bold",
    parent=base_paragraph_style,
)

duration_style = ParagraphStyle(
    "Duration",
    fontName="Helvetica-Bold",
    parent=base_paragraph_style,
    alignment=TA_RIGHT,
)

job_role_style = ParagraphStyle(
    "JobRole",
    parent=base_paragraph_style,
    fontSize=9,
    spaceAfter=0,
)

location_style = ParagraphStyle(
    "Location",
    parent=base_paragraph_style,
    fontSize=9,
    alignment=TA_RIGHT,
)

job_desc_style = ParagraphStyle(
    "JobDesc",
    parent=base_paragraph_style,
    bulletFontName="Helvetica-Bold",
    leftIndent=12,
    bulletIndent=18,
    spaceBefore=3,
    spaceAfter=3,
)

education_style_r = ParagraphStyle(
    "EducationR",
    parent=base_paragraph_style,
    alignment=TA_RIGHT,
)

education_style_l = ParagraphStyle(
    "EducationL",
    parent=base_paragraph_style,
    alignment=TA_LEFT,
)

doc_style_r = ParagraphStyle(
    "DocR",
    parent=base_paragraph_style,
    alignment=TA_RIGHT,
)

doc_style_l = ParagraphStyle(
    "DocL",
    parent=base_paragraph_style,
    alignment=TA_LEFT,
)


# Function to create and style a header with an HRFlowable and Spacer
def add_header_with_line(doc=None, story=None, header_text=None, style=header_style):
    story.append(Paragraph(header_text, style))
    story.append(HRFlowable(width=doc.width))
    story.append(Spacer(1, 6))


# Function to create a table for company details and job description
def create_company_table(data, col_widths):
    return Table(
        data,
        colWidths=col_widths,
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )


# Function to create a styled Paragraph with an optional hyperlink
def create_styled_paragraph(text, style, hyperlink=None):
    if hyperlink:
        text = f'<link href="{hyperlink}" color="blue">{text}</link>'
    return Paragraph(text, style)


# Function to create a list of bullet points
def create_bullet_list(items, bullet_style):
    return ListFlowable(
        [ListItem(Paragraph(item, bullet_style)) for item in items],
        bulletType="bullet",
        start="•",
        leftIndent=bullet_style.leftIndent,
    )


# Function to add contact information
def add_contact_info(story, contact_dict):
    name_text = get_value(contact_dict, "name", "")
    job_title_text = get_value(contact_dict, "job_title", "")
    email_text = get_value(contact_dict, "email", "")
    phone_text = get_value(contact_dict, "phone", "")
    address_text = get_value(contact_dict, "address", "")
    linkedIn_url = get_value(contact_dict, "linkedIn", "")

    middle_contact_details = " | ".join(
        [text for text in [email_text, phone_text, address_text] if text]
    )

    if name_text:
        story.append(Paragraph(name_text, name_style))

    if job_title_text:
        story.append(Paragraph(job_title_text, job_title_style))

    if middle_contact_details:
        story.append(Paragraph(middle_contact_details, contact_details_style))

    if linkedIn_url:
        linkedin = f'<link href="{linkedIn_url}" color="blue">{linkedIn_url}</link>'
        story.append(Paragraph(linkedin, linkedin_style))


# Function to add contact information
def add_summary(doc=None, story=None, summary_text=None):
    if summary_text:
        add_header_with_line(doc=doc, story=story, header_text="SUMMARY")
        story.append(Paragraph(summary_text, summary_style))


# Function to add experiences
def add_experiences(doc, story, exp_dict):
    if exp_dict:
        add_header_with_line(doc=doc, story=story, header_text="EXPERIENCES")

        for exp_key, exp_value in exp_dict.items():
            if exp_value:
                company_name_text = get_value(exp_value, "company_name", "")
                start_date_text = get_value(exp_value, "start_date", "")
                end_date_text = get_value(exp_value, "end_date", "")
                job_role_text = get_value(exp_value, "job_role", "")
                location_text = get_value(exp_value, "location", "")
                job_description_list = get_value(exp_value, "job_description", "")

                # Ensure no NoneType values are passed to Paragraph
                company_name_text = company_name_text or ""
                start_date_text = start_date_text or ""
                end_date_text = end_date_text or ""
                job_role_text = job_role_text or ""
                location_text = location_text or ""
                job_description_list = job_description_list or []

                company_name = Paragraph(company_name_text, company_name_style)
                duration = Paragraph(
                    start_date_text + " – " + end_date_text, duration_style
                )
                job_role = Paragraph(job_role_text, job_role_style)
                location = Paragraph(location_text, location_style)

                # Add a company table
                company_table_data = [[company_name, duration], [job_role, location]]
                story.append(
                    create_company_table(
                        company_table_data, [doc.width * 0.5, doc.width * 0.5]
                    )
                )

                # Add job descriptions
                story.append(create_bullet_list(job_description_list, job_desc_style))
                story.append(Spacer(1, 5))
            else:
                print("There is no experience here")


# Function to add education
def add_education(doc, story, edu_data):
    if edu_data:
        add_header_with_line(doc=doc, story=story, header_text="EDUCATION")

        column_width_large = doc.width * 0.75
        column_width_small = doc.width * 0.25

        # Convert to list if it's a dictionary
        if isinstance(edu_data, dict):
            edu_data = [edu_data]

        for edu in edu_data:
            degree_text = get_value(edu, "degree", "")
            institution_text = get_value(edu, "institution", "")
            location_text = get_value(edu, "location", "")
            end_date_text = get_value(edu, "end_date", "")

            degree_text = degree_text or ""
            institution_text = institution_text or ""
            location_text = location_text or ""
            end_date_text = end_date_text or ""

            if degree_text or institution_text or location_text or end_date_text:
                degree = Paragraph(degree_text, education_style_l)
                institution = Paragraph(institution_text, education_style_l)
                location = Paragraph(location_text, education_style_r)
                end_date = Paragraph(end_date_text, education_style_r)

                # Add a education table
                education_table_data = [[institution, end_date], [degree, location]]
                story.append(
                    create_company_table(
                        education_table_data, [column_width_large, column_width_small]
                    )
                )


# Function to add skills
def add_skills(doc=None, story=None, skill_list=None):
    if skill_list:
        add_header_with_line(doc=doc, story=story, header_text="SKILLS")

        skills_string = ", ".join(skill_list)
        skills_string = skills_string or ""
        story.append(Paragraph(skills_string, summary_style))


# Function to add certifications
def add_certifications(doc=None, story=None, cert_list=None):
    if cert_list:
        add_header_with_line(doc=doc, story=story, header_text="CERTIFICATIONS")

        column_width_large = doc.width * 0.75
        column_width_small = doc.width * 0.25

        for cert in cert_list:
            if cert is not None:
                title_text = get_value(cert, "title", "")
                issuing_organization_text = get_value(cert, "issuing_organization", "")
                date_obtained_text = get_value(cert, "date_obtained", "")

                title_text = title_text or ""
                issuing_organization_text = issuing_organization_text or ""
                date_obtained_text = date_obtained_text or ""

                if title_text or issuing_organization_text or date_obtained_text:
                    certification_title = Paragraph(
                        f"{title_text} - {issuing_organization_text}", doc_style_l
                    )
                    date = Paragraph(f"{date_obtained_text}", doc_style_r)

                    # Add a education table
                    certification_table_data = [[certification_title, date]]
                    story.append(
                        create_company_table(
                            certification_table_data, [column_width_large, column_width_small]
                        )
                    )


# # Function to add projects
# def add_projects(proj_list):
#     for proj in proj_list:
#         story.append(Paragraph(proj["project_title"], header_style))
#         story.append(Paragraph(proj["description"], job_desc_style))


def generate_resume_pdf(improved_resume_dict, filename):
    start_time = time.time()

    # Define the buffer for the PDF
    pdf_buffer = BytesIO()

    # Create a PDF document
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=36)
    story = []

    # Add sections to the document if they are not empty
    contact_info = get_value(improved_resume_dict, "contact", None)
    if contact_info and any(contact_info.values()):
        add_contact_info(story, contact_info)
        story.append(Spacer(1, 8))  # Add some space before the next section

    summary_text = get_value(improved_resume_dict, "summary", "")
    if summary_text:
        add_summary(doc=doc, story=story, summary_text=summary_text)
        story.append(Spacer(1, 8))

    experiences = get_value(improved_resume_dict, "experiences", None) or get_value(improved_resume_dict, "experience", None)
    if experiences and any(experiences.values()):
        add_experiences(doc, story, experiences)
        story.append(Spacer(1, 8))

    education = get_value(improved_resume_dict, "education", None)
    if education:
        add_education(doc, story, education)
        story.append(Spacer(1, 8))

    skills = get_value(improved_resume_dict, "skills", None)
    if skills and any(skills):
        add_skills(doc, story, skills)
        story.append(Spacer(1, 8))

    certifications = get_value(improved_resume_dict, "certifications", None)
    if certifications and any(cert for cert in certifications if cert):
        add_certifications(doc, story, certifications)
        story.append(Spacer(1, 8))

    # Optionally add projects if required
    # story.append(Spacer(1, 8))
    # add_projects(story, improved_resume_dict["projects"])

    # Build the PDF
    doc.build(story)

    # Get the PDF data
    pdf_value = pdf_buffer.getvalue()
    pdf_buffer.close()

    total = time.time() - start_time
    logger.info(f"PDF CREATION TIME: {total}")
    return ContentFile(pdf_value, name=filename)


# improved_resume_dict = {
#     'contact': {
#         'name': 'Chris Ukachu',
#         'job_title': 'Website Designer',
#         'address': 'Apapa, Lagos',
#         'phone': '+2347017132725',
#         'email': 'chrisukachu@gmail.com',
#         'linkedIn': None
#     },
#     'summary': 'Results-driven website designer with over 4 years of experience in creating user-centric and visually appealing digital experiences. Passionate about leveraging data to drive decision-making and optimize business processes, seeking to transition into a data analyst role. Eager to apply strong analytical skills, proficiency in data visualization tools, and a keen eye for detail to extract meaningful insights and contribute to data-driven strategies. Committed to continuous learning and staying abreast of industry trends to deliver impactful results.',
#     'experiences': {
#         'experience_1': {
#             'company_name': 'Kaycee Shortlets',
#             'job_role': 'Wordpress Web Developer',
#             'start_date': '2022',
#             'end_date': '2024',
#             'location': 'Surulere, Lagos',
#             'job_description': [
#                 'Customized themes to align with brand guidelines, resulting in a cohesive and visually appealing online presence.',
#                 'Integrated and configured third-party plugins to enhance website features.',
#                 'Created visually appealing, responsive website designs that improved user engagement by 25%.',
#                 'Configured and managed payment gateways, optimizing the checkout process and reducing cart abandonment by 15%.',
#                 'Optimized website performance, including improving loading speeds and SEO, resulting in a 40% increase in organic traffic.',
#                 'Implemented and customized e-commerce solutions using WooCommerce or other WordPress-compatible platforms.',
#                 'Developed and customized Shopify stores using HTML, CSS, JavaScript, and Liquid, leading to a 30% increase in user engagement.'
#             ]
#         },
#         'experience_2': {
#             'company_name': 'Brandyme.fr',
#             'job_role': 'Freelance Wordpress and Shopify Developer',
#             'start_date': '2020',
#             'end_date': 'Present',
#             'location': 'Paris, France',
#             'job_description': [
#                 'Coordinate with clients, designers, and other developers to deliver projects on time and within budget.',
#                 'Manage and structure website content effectively using the WordPress, Shopify CMS.',
#                 'Optimize website performance, including improving loading speeds and SEO.',
#                 'Perform regular updates, backups, and security checks.',
#                 'Diagnose and fix website issues, including bugs, errors, and downtime.',
#                 'Provide technical support and guidance to clients or users.', "Utilize Liquid, Shopify's templating language, to create and manipulate themes and functionalities within the Shopify platform.",
#                 'Integrate third-party apps to extend Shopify’s functionality and develop custom apps to meet specific business needs.',
#                 'Work with clients to understand their business needs and implement effective e-commerce strategies to enhance sales and customer engagement.',
#                 'Design intuitive and visually appealing user interfaces and user experiences that enhance customer satisfaction and drive conversions.',
#                 'Configured and managed payment gateways, optimizing the checkout process and reducing cart abandonment by 15%.',
#                 'Designed and developed email templates and managed automated email campaigns, contributing to a 20% increase in repeat purchases.'
#             ]
#         },
#         'experience_3': None
#     },
#     'education': [
#         {
#             'institution': 'ESM University',
#             'degree': 'Bachelor of Science in Computer Science',
#             'end_date': 'July 2024',
#             'location': 'Benin Republic',
#             'details': None
#         }
#     ],
#     'skills': [
#         'JavaScript',
#         'HTML/CSS',
#         'WooCommerce',
#         'Email Marketing',
#         'Graphics Design',
#         'Python',
#         'SQL',
#         'Shopify',
#         'WordPress'
#     ],
#     "certifications": [
#         {
#             "title": "Certified Emergency Nurse (CEN)",
#             "issuing_organization": "Institute of Michigan",
#             "date_obtained": "August 2016",
#             "validity_period": None,
#         },
#         {
#             "title": "Trauma Nursing Core Course (TNCC)",
#             "issuing_organization": "Institute of Michigan",
#             "date_obtained": "March 2018",
#             "validity_period": "4 years",
#         },
#         {
#             "title": "Pediatric Advanced Life Support (PALS)",
#             "issuing_organization": "Institute of Michigan",
#             "date_obtained": "May 2017",
#             "validity_period": "2 years",
#         },
#         {
#             "title": "Registered Nurse (RN) License, State of Washington",
#             "issuing_organization": "Institute of Michigan",
#             "date_obtained": "June 2015",
#             "validity_period": None,
#         },
#     ],
#     'references': [
#         {
#             "referee_name": "Available upon request.",
#             "relationship": None,
#             "contact_information": None,
#         }
#     ]
# }


# generate_resume_pdf(improved_resume_dict["customized_resume"], filename="resume.pdf")

# ================================================================
# ================================================================
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
LIST_INDENT = 0.5 * inch

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

def format_content(canvas, content, width, height, y):
    paragraphs = re.split(r'\n{2,}', content)  # Split on two or more newlines
    for paragraph in paragraphs:
        lines = paragraph.split('\n')  # Split on single newlines to preserve manual line breaks
        for line in lines:
            list_match = re.match(r'^(\s*)([•\-*]|\d+\.|\w\.)\s+(.+)$', line.strip())
            if list_match:
                indent, marker, item_content = list_match.groups()
                y = format_list_item(canvas, indent, marker, item_content, width, height, y)
            else:
                y = format_paragraph(canvas, line, width, height, y)
        y -= LINE_HEIGHT  # Extra space between paragraphs
    return y

def format_paragraph(canvas, text, width, height, y):
    lines = wrap_text(text, width - MARGINS['left'] - MARGINS['right'])
    for line in lines:
        draw_text(canvas, line, MARGINS['left'], y)
        y -= LINE_HEIGHT
        if y < MARGINS['bottom']:
            canvas.showPage()
            y = height - MARGINS['top']
            canvas.setFont(FONT_NAME, FONT_SIZE)
    return y

def format_list_item(canvas, indent, marker, content, width, height, y):
    indent_width = len(indent) * pdfmetrics.stringWidth(' ', FONT_NAME, FONT_SIZE)
    marker_width = pdfmetrics.stringWidth(marker + ' ', FONT_NAME, FONT_SIZE)
    total_indent = MARGINS['left'] + indent_width
    content_indent = total_indent + marker_width

    # Draw the marker
    draw_text(canvas, marker, total_indent, y)

    # Wrap and draw the content
    content_width = width - content_indent - MARGINS['right']
    lines = wrap_text(content, content_width)
    for i, line in enumerate(lines):
        draw_text(canvas, line, content_indent, y)
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

    if doc_type == "CL":
        if isinstance(content, dict):
            # Recipient
            recipient = content.get('recipient', 'Dear Hiring Manager,')
            draw_text(p, recipient, MARGINS['left'], y)
            y -= LINE_HEIGHT * 2

            # Body
            body_content = content.get('body', '')
            y = format_content(p, body_content, width, height, y)

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
            y = format_content(p, content, width, height, y)
    else:
        # Handle other document types if needed
        y = format_content(p, content, width, height, y)

    p.save()

    pdf_value = buffer.getvalue()
    buffer.close()

    total = time.time() - start_time
    logger.info(f"PDF CREATION TIME: {total}")
    return ContentFile(pdf_value, name=filename)


# async def run_main():
#     from asgiref.sync import sync_to_async

#     from resume.models import CoverLetter, JobPost
#     from resume.samples import improved_cover_letter_dict, optimized_cover_letter_dict
#     from resume.utils import optimize_doc

#     cover_letter_update = sync_to_async(
#         CoverLetter.objects.update_or_create, thread_sensitive=True
#     )

#     # pdf_dict = improved_pdf_dict
#     pdf_dict = optimized_cover_letter_dict

#     if pdf_dict == improved_cover_letter_dict:
#         improved_content = "content"
#         pdf = generate_cv_pdf(pdf_dict, "output.pdf", doc_type="CL")

#         candidate_id = "111"

#         # Run the synchronous database update_or_create functions concurrently
#         cover_letter_instance, cover_letter_created = await cover_letter_update(
#             cover_letter_id=candidate_id,
#             defaults={
#                 "general_improved_content": improved_content,
#                 "general_improved_pdf": pdf,
#             },
#         )
#     elif pdf_dict == optimized_cover_letter_dict:
#         pdf = generate_cv_pdf(
#             pdf_dict, filename="Optimized Cover Letter", doc_type="CL"
#         )
