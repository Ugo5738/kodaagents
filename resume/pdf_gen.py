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
def add_education(doc, story, edu_list):
    if edu_list:
        add_header_with_line(doc=doc, story=story, header_text="EDUCATION")

        column_width_large = doc.width * 0.75
        column_width_small = doc.width * 0.25

        for edu in edu_list:
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

    experiences = get_value(improved_resume_dict, "experiences", None)
    if experiences and any(experiences.values()):
        add_experiences(doc, story, experiences)
        story.append(Spacer(1, 8))

    education = get_value(improved_resume_dict, "education", None)
    if education and any(edu for edu in education if edu):
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
#     "contact": {
#         "name": "SARAH JOHNSON",
#         "job_title": "Registered Nurse Manager",
#         "address": "Seattle, Washington",
#         "phone": "+1-555-123-4567",
#         "email": "sjohnsonnurse@example.com",
#         "linkedIn": "https://www.linkedin.com/in/sarah-johnson-rn",
#     },
#     "summary": "Highly experienced and strategic Registered Nurse with over 10 years of clinical experience, including 5+ years in leadership roles focused on inpatient care. Proven track record in enhancing patient care, streamlining department operations, and leading healthcare teams towards excellence. Eager to contribute to AMCE's mission by bringing a culture of clinical excellence and patient-centered care to a diverse patient population.",
#     "experiences": {
#         "experience_1": {
#             "company_name": "Seattle General Hospital",
#             "job_role": "Registered Nurse",
#             "start_date": "June 2019",
#             "end_date": "Present",
#             "location": "Seattle, Washington",
#             "job_description": [
#                 "Oversee patient care delivery in a high-traffic emergency department, developing and executing strategies to reduce wait times and enhance service quality.",
#                 "Spearhead a comprehensive review and overhaul of patient triage protocol, resulting in a 30% leap in departmental efficiency and patient throughput.",
#                 "Pioneer patient education initiatives to tackle chronic disease management, yielding a significant improvement in patient compliance and outcomes.",
#             ],
#         },
#         "experience_2": {
#             "job_title": "Staff Nurse",
#             "start_date": "January 2017",
#             "end_date": "June 2019",
#             "job_description": "Managed and coordinated end-to-end patient care for various medical cases within a 30-bed inpatient unit, consistently scoring high on patient satisfaction metrics.",
#         },
#         "experience_3": {
#             "job_title": "Community Health Nurse",
#             "start_date": "July 2015",
#             "end_date": "December 2016",
#             "job_description": "Executed primary care services and health education for underserved communities, with an emphasis on preventative care and wellness.",
#         },
#     },
#     "education": [
#         {
#             "institution": "University of Washington",
#             "degree": "Master of Science in Nursing (MSN)",
#             "end_date": "June 2015",
#             "location": "Seattle, Washington",
#             "details": "Focused on Healthcare Leadership and Management",
#         }
#     ],
#     "skills": [
#         "Clinical Management",
#         "Team Leadership",
#         "Strategic Planning",
#         "Patient Education",
#         "Quality Assurance",
#         "Healthcare Regulation Compliance",
#         "Interdisciplinary Collaboration",
#         "Health Informatics",
#         "Patient Advocacy",
#         "Mentorship Programs",
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
#     "references": [
#         {
#             "referee_name": "Available upon request.",
#             "relationship": None,
#             "contact_information": None,
#         }
#     ],
# }

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
#     'certifications': [None], 
#     'references': [
#         {
#             'referee_name': None, 
#             'relationship': None, 
#             'contact_information': None
#         }
#     ]
# }

# generate_resume_pdf(improved_resume_dict, filename="resume.pdf")

# ================================================================
# ================================================================
# Constants
LEFT_MARGIN = 65
RIGHT_MARGIN = 40
TOP_MARGIN = 72
BOTTOM_MARGIN = 72
FONT_NAME = "Helvetica"
FONT_SIZE = 12


def wrap_text(text, width):
    """
    Wraps text to fit within a specified width.
    :param text: The text to be wrapped.
    :param width: The maximum width of a line.
    :return: A list of lines where each line fits within the specified width.
    """
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        # Check if adding the next word exceeds the line width
        if pdfmetrics.stringWidth(current_line + word, FONT_NAME, FONT_SIZE) <= width:
            current_line += word + " "
        else:
            # If the line is too long, start a new line
            lines.append(current_line)
            current_line = word + " "

    if current_line:  # Add the last line if it's not empty
        lines.append(current_line)

    return lines


def draw_line(canvas, text, x, y):
    canvas.drawString(x, y, text)


def format_paragraphs(canvas, text_blocks, width, height, y, is_paragraph=True):
    for block in text_blocks:
        if is_paragraph:
            # Treat as a paragraph with potential line wrapping
            wrapped_text = wrap_text(block, width - (LEFT_MARGIN + RIGHT_MARGIN))
        else:
            # Treat as single lines
            wrapped_text = block.split("\n")

        for line in wrapped_text:
            draw_line(canvas, line, LEFT_MARGIN, y)
            y -= 18  # Line spacing
            if y < BOTTOM_MARGIN:
                canvas.showPage()
                y = height - TOP_MARGIN
                canvas.setFont(FONT_NAME, FONT_SIZE)
        y -= 18  # Paragraph spacing
    return y


async def generate_formatted_pdf(response_text, filename, doc_type=None):
    start_time = time.time()

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    p.setFont(FONT_NAME, FONT_SIZE)
    y = height - TOP_MARGIN

    if doc_type == "CL":
        if isinstance(response_text, dict):
            # Body text formatting (for dict)
            body_text = response_text.get("body", "")
            paragraphs = body_text.split("\n\n")
            y = format_paragraphs(p, paragraphs, width, height, y, is_paragraph=True)

            # Concluding Greetings Formatting
            concluding_greetings = response_text.get("concluding_greetings", "")
            greeting_lines = concluding_greetings.split("\n\n")
            y = format_paragraphs(p, greeting_lines, width, height, y, is_paragraph=False)
        else:
            # Handle the case where response_text is a string
            paragraphs = response_text.split("\n\n")
            y = format_paragraphs(p, paragraphs, width, height, y, is_paragraph=True)
    else:
        # Handle the case where response_text is a string
        paragraphs = response_text.split("\n\n")
        y = format_paragraphs(p, paragraphs, width, height, y, is_paragraph=True)
    
    p.save()
    
    pdf_value = buffer.getvalue()
    buffer.seek(0)
    
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
#         pdf = generate_formatted_pdf(pdf_dict, "output.pdf", doc_type="CL")

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
#         pdf = generate_formatted_pdf(
#             pdf_dict, filename="Optimized Cover Letter", doc_type="CL"
#         )
