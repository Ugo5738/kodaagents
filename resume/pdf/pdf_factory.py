# from weasyprint import HTML
import time
from io import BytesIO

from django.core.files.base import ContentFile
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
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

# def generate_pdf_from_html(html_content, output_filename):
#     HTML(string=html_content).write_pdf(output_filename, stylesheets=["path/to/your/cssfile.css"])


logger = configure_logger(__name__)


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
    name_text = contact_dict.get("name", "")
    email_text = contact_dict.get("email", "")
    phone_text = contact_dict.get("phone", "")
    address_text = contact_dict.get("address", "")
    linkedIn_url = contact_dict.get("linkedIn", "")

    middle_contact_details = f"{email_text} | {phone_text} | {address_text}"

    # Append the name with a special style
    story.append(Paragraph(name_text, name_style))

    # Append the address
    story.append(Paragraph(middle_contact_details, contact_details_style))

    # Append the LinkedIn URL
    if "linkedIn" in contact_dict:
        # Use Paragraph to allow link styling
        linkedin = f'<link href="{linkedIn_url}" color="blue">{linkedIn_url}</link>'
        story.append(Paragraph(linkedin, linkedin_style))


# Function to add contact information
def add_summary(doc=None, story=None, summary_text=None):
    add_header_with_line(doc=doc, story=story, header_text="SUMMARY")

    # Append the name with a special style
    story.append(Paragraph(summary_text, summary_style))


# Function to add experiences
def add_experiences(doc, story, exp_dict):
    add_header_with_line(doc=doc, story=story, header_text="EXPERIENCES")

    for exp_value in exp_dict.values():
        company_name_text = exp_value.get("company_name", "")
        start_date_text = exp_value.get("start_date", "")
        end_date_text = exp_value.get("end_date", "")
        job_role_text = exp_value.get("job_role", "")
        location_text = exp_value.get("location", "")
        job_description_list = exp_value.get("job_description", "")

        company_name = Paragraph(company_name_text, company_name_style)
        duration = Paragraph(start_date_text + " – " + end_date_text, duration_style)
        job_role = Paragraph(job_role_text, job_role_style)
        location = Paragraph(location_text, location_style)

        # Add a company table
        company_table_data = [[company_name, duration], [job_role, location]]
        story.append(
            create_company_table(company_table_data, [doc.width * 0.5, doc.width * 0.5])
        )

        # Add job descriptions
        story.append(create_bullet_list(job_description_list, job_desc_style))
        story.append(Spacer(1, 5))


# Function to add education
def add_education(doc, story, edu_list):
    add_header_with_line(doc=doc, story=story, header_text="EDUCATION")

    column_width_large = doc.width * 0.75
    column_width_small = doc.width * 0.25

    for edu in edu_list:
        degree_text = edu.get("degree", "")
        institution_text = edu.get("institution", "")
        location_text = edu.get("location", "")
        end_date_text = edu.get("end_date", "")

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
    add_header_with_line(doc=doc, story=story, header_text="SKILLS")

    skills_string = ", ".join(skill_list)
    story.append(Paragraph(skills_string, summary_style))


# Function to add certifications
def add_certifications(doc=None, story=None, cert_list=None):
    add_header_with_line(doc=doc, story=story, header_text="CERTIFICATIONS")

    column_width_large = doc.width * 0.75
    column_width_small = doc.width * 0.25

    for cert in cert_list:
        title_text = cert.get("title", "")
        issuing_organization_text = cert.get("issuing_organization", "")
        date_obtained_text = cert.get("date_obtained", "")

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

    # Add sections to the document
    add_contact_info(story, improved_resume_dict.get("contact", ""))
    story.append(Spacer(1, 8))  # Add some space before the next section
    add_summary(
        doc=doc,
        story=story,
        summary_text=improved_resume_dict.get("summary", ""),
    )
    story.append(Spacer(1, 8))
    add_experiences(doc, story, improved_resume_dict.get("experiences", ""))
    story.append(Spacer(1, 8))
    add_education(doc, story, improved_resume_dict.get("education", ""))
    story.append(Spacer(1, 8))
    add_skills(doc, story, improved_resume_dict.get("skills", ""))
    story.append(Spacer(1, 8))
    add_certifications(doc, story, improved_resume_dict.get("certifications", ""))
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
