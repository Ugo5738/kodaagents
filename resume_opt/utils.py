import re
import json
import time
import asyncio
from uuid import uuid4
import mimetypes

import boto3
from koda.config.base_config import anthropic_client
from koda.config.logging_config import configure_logger
from resume.utils.util_funcs import generate_documents, upload_documents_to_s3
from django.conf import settings
from typing import Tuple, Optional
from typing import BinaryIO, Optional
from botocore.exceptions import BotoCoreError, ClientError

logger = configure_logger(__name__)


resume_example_structure = json.dumps(
    {
        "contact": {
            "name": "Sender Name",
            "job_title": "Job Title",
            "address": "Sender Address",
            "phone": "Sender Phone",
            "email": "Sender Email",
            "linkedIn": "LinkedIn Profile url (if available)",
        },
        "summary": "Resume Executive Summary",
        "experiences": {
            "experience_1": {
                "company_name": "Name of company worked for",
                "job_role": "Job Position",
                "start_date": "Start date of job",
                "end_date": "End date of job if available",
                "location": "Location of the company",
                "job_description": [
                    "First Description of Job Responsibilities and Achievements",
                    "Second Description of Job Responsibilities and Achievements",
                    "Third Description of Job Responsibilities and Achievements",
                    # Additional descriptions can be added here
                ],
            },
            "experience_2": {
                "job_title": "Job Position",
                "start_date": "Start date of job",
                "end_date": "End date of job if available",
                "job_description": "Description of Job Responsibilities and Achievements",
            },
            "experience_3": {
                "job_title": "Job Position",
                "start_date": "Start date of job",
                "end_date": "End date of job if available",
                "job_description": "Description of Job Responsibilities and Achievements",
            },
        },
        "education": [
            {
                "institution": "Educational Institution",
                "degree": "Degree Obtained",
                "end_date": "End Date",
                "location": "Location of institution",
                "details": "Details about the Course or Achievements if available",
            },
            # Additional education entries can be added here
        ],
        "skills": [
            "Skill 1",
            "Skill 2",
            # Additional skills can be listed here
        ],
        "certifications": [
            {
                "title": "Certification Title",
                "issuing_organization": "Issuing Organization",
                "date_obtained": "Date Obtained (if applicable)",
                "validity_period": "Validity Period (if applicable)",
            },
            # Additional certifications can be listed here
        ],
        # "projects": [
        #     {
        #         "project_title": "Project Title",
        #         "duration": "Project Duration",
        #         "description": "Project Description",
        #         "technologies_used": ["Technology 1", "Technology 2"],
        #     },
        #     # Additional projects can be listed here
        # ],
        "references": [
            {
                "referee_name": "Referee Name",
                "relationship": "Relationship to the Referee",
                "contact_information": "Referee Contact Information",
            },
            # Additional references can be added here
        ],
    },
    indent=2,
)


cover_letter_example_structure = json.dumps(
    {
        "name": "Full Name",
        "recipient": "Dear Hiring Manager,",
        "body": "Cover letter body text, separated into paragraphs by \\n\\n",
        "closing": "Choose an appropriate closing based on the tone and content of the letter"
    }
)


def extract_json(text):
    """
    Extract JSON content from text, handling potential nested structures.
    """
    stack = []
    start = -1
    for i, char in enumerate(text):
        if char == '{':
            if not stack:
                start = i
            stack.append(char)
        elif char == '}':
            if stack and stack[-1] == '{':
                stack.pop()
                if not stack:
                    return text[start:i+1]
            else:
                stack.append(char)
    return None

def repair_json(json_str):
    """
    Attempt to repair common JSON issues.
    """
    # Replace single quotes with double quotes
    json_str = json_str.replace("'", '"')

    # Remove trailing commas in objects and arrays
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*\]', ']', json_str)

    # Ensure property names are in double quotes
    json_str = re.sub(r'(\w+)(?=\s*:)', r'"\1"', json_str)

    return json_str

def parse_json_safely(json_str):
    """
    Attempt to parse JSON with multiple fallback methods.
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Initial JSON parsing failed: {e}")

        # Try repairing the JSON
        repaired_json = repair_json(json_str)
        try:
            return json.loads(repaired_json)
        except json.JSONDecodeError as e:
            logger.warning(f"Parsing repaired JSON failed: {e}")

            # As a last resort, try ast.literal_eval
            try:
                import ast
                return ast.literal_eval(repaired_json)
            except (SyntaxError, ValueError) as e:
                logger.error(f"All parsing attempts failed: {e}")
                logger.error(f"Problematic JSON content: {json_str}")
                raise ValueError("Unable to parse JSON content")

async def get_anth_chat_response(prompt, to_json=True):
    start_time = time.time()

    response = await anthropic_client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=4096,
        temperature=0.2,
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": "Here is the JSON requested:\n{"}
        ]
    )
    message = response.content[0].text
    edited_message = "{" + message[:message.rfind("}") + 1]
    print(edited_message)

    if to_json:
        # Extract JSON content
        json_content = extract_json(edited_message)
        if not json_content:
            raise ValueError("No JSON content found in the response")

        # Parse JSON safely
        try:
            output_json = parse_json_safely(json_content)

            total = time.time() - start_time
            logger.info(f"Chat Response Time: {total}")
            return output_json
        except ValueError as e:
            logger.error(str(e))
            raise

    total = time.time() - start_time
    logger.info(f"Chat Response Time: {total}")

    return edited_message


async def analyze_and_improve_document(doc_type="resume", content=None, job_description=None):
    start_time = time.time()

    prompt = f"""
    You are an expert resume writer and career coach with over 20 years of experience helping candidates secure interviews at top companies. Your task is to optimize the provided {doc_type} and create a compelling cover letter that will maximize the applicant's chances of getting an interview.

    DOCUMENT TYPE: {doc_type}
    CONTENT: {content}
    JOB DESCRIPTION: {job_description if job_description else 'Not provided'}

    Follow these steps to create the best possible resume and cover letter:

    1. Resume Optimization:
       a) Analyze the current resume for strengths and weaknesses.
       b) Rewrite and restructure the resume to highlight the applicant's most relevant skills and achievements.
       c) Use powerful action verbs and quantify achievements wherever possible.
       d) Ensure the resume is ATS-friendly by incorporating relevant keywords from the job description (if provided).
       e) Tailor the content to the specific job or industry, emphasizing the most relevant experiences and skills.
       f) Improve the overall readability and visual appeal of the resume.

    2. Cover Letter Creation:
       a) Write a compelling, personalized cover letter that complements the resume.
       b) Address the specific requirements mentioned in the job description (if provided).
       c) Highlight the applicant's unique value proposition and most relevant achievements.
       d) Demonstrate enthusiasm for the position and knowledge of the company.
       e) Keep the tone professional yet engaging, and limit the length to one page.

    3. Overall Improvements:
       a) Ensure consistency in formatting and language between the resume and cover letter.
       b) Proofread for any grammatical or spelling errors.
       c) Optimize the documents for both human readers and ATS systems.

    Return the results in the following JSON format:
    {{
        "analysis": {{
            "readability": string,
            "tone": string,
            "structure": string,
            "keywords": string,  // Only if job description provided
        }},
        "general_section_review": {{
            "section_name": "review"
        }},
        "job_tailored_section_review": {{
            "section_name": "review"
        }},
        "improved_resume_content": {{
            {resume_example_structure}
        }},
        "job_match_score": float,  // Only if job description provided
        "cover_letter": {{
            {cover_letter_example_structure}
        }}
        "improvement_summary": {{
            "key_changes": [string],
            "ats_optimization": string,
            "tailoring_to_job": string  // if job description provided
        }},
        "interview_potential_score": float  // On a scale of 0 to 100
    }}

    Focus on creating the most impactful and interview-worthy documents possible. Be creative and strategic in your improvements while maintaining honesty and professionalism.
    """

    result = {}
    try:
        result = await get_anth_chat_response(prompt)
        total = time.time() - start_time
        logger.info(f"Chat Response Time: {total}")
    except ValueError as e:
        logger.error(f"Failed to get valid response: {e}")

    return result


async def anth_customize_document(document_type, original_content, customization_request):
    """
    Customizes a resume or cover letter based on user input.

    :param document_type: String, either "resume" or "cover_letter"
    :param original_content: Dict or String, the original optimized document
    :param customization_request: String, the user's customization request
    :return: Dict or String, the customized document
    """
    prompt = f"""
    As an expert resume writer and career coach, your task is to customize the provided {document_type}
    based on the user's specific request. Apply the requested changes while maintaining the overall
    quality and effectiveness of the document.

    DOCUMENT TYPE: {document_type}
    ORIGINAL CONTENT: {json.dumps(original_content) if isinstance(original_content, dict) else original_content}
    CUSTOMIZATION REQUEST: {customization_request}

    Guidelines for customization:
    1. Carefully interpret the user's request and apply changes accordingly.
    2. Maintain the professional tone and structure of the document.
    3. Ensure any additions or changes align with best practices for {document_type}s.
    4. Preserve the document's ATS-friendly qualities if applicable.
    5. If the request might negatively impact the document's effectiveness, provide a brief explanation and suggestion.

    Return the customized document in the following format:

    {"{" if document_type == "resume" else ""}
    "customized_{document_type}": {{
        // If resume, use the same structure as the original optimized resume
        // If cover letter, return the full text as a string with \n for newlines
    }},
    "customization_notes": [
        // List of strings explaining the changes made and any relevant notes or suggestions
    ]
    {"}," if document_type == "resume" else ""}
    "effectiveness_impact": float  // Scale from -1 to 1, where -1 is very negative, 0 is neutral, and 1 is very positive
    """

    try:
        result = await get_anth_chat_response(prompt)

        # Parse the result
        customized_content = result.get(f"customized_{document_type}", {})
        customization_notes = result.get("customization_notes", [])
        effectiveness_impact = result.get("effectiveness_impact", 0)

        return {
            f"customized_document": customized_content,
            "customization_notes": customization_notes,
            "effectiveness_impact": effectiveness_impact
        }
    except Exception as e:
        logger.error(f"Failed to customize document: {e}")
        return None


async def get_anth_doc_urls(resume_content: Optional[str] = None, job_post_content: Optional[str] = None) -> Tuple[str, str, str, str]:
    start_time = time.time()

    is_optimized = bool(job_post_content)
    result = await analyze_and_improve_document(content=resume_content, job_description=job_post_content)

    resume_content = result["improved_resume_content"]
    cover_letter_content = result["cover_letter"]

    suffix = "optimized" if is_optimized else "improved"

    resume_pdf, resume_docx = await generate_documents("resume", resume_content, is_optimized)
    cl_pdf, cl_docx = await generate_documents("cover_letter", cover_letter_content, is_optimized)

    resume_pdf_url, resume_docx_url = await upload_documents_to_s3(resume_pdf, resume_docx, "resume", is_optimized)
    cl_pdf_url, cl_docx_url = await upload_documents_to_s3(cl_pdf, cl_docx, "cover_letter", is_optimized)

    duration = time.time() - start_time
    logger.info(f"ENTIRE PROCESS TOOK {duration:.2f} seconds")

    return resume_pdf_url, resume_docx_url, cl_pdf_url, cl_docx_url


def upload_directly_to_s3(file: BinaryIO, bucket_name: str, s3_key: str, content_type: Optional[str] = None) -> None:
    """
    Upload a file directly to S3.

    Args:
        file (BinaryIO): File-like object to upload.
        bucket_name (str): Name of the S3 bucket.
        s3_key (str): S3 object key (path) for the uploaded file.
        content_type (Optional[str]): MIME type of the file. If None, it will be guessed.

    Raises:
        ValueError: If the file object doesn't have a 'read' method.
        boto3.exceptions.S3UploadFailedError: If the upload to S3 fails.
    """
    if not hasattr(file, 'read'):
        raise ValueError("File object must have a read method")

    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            # region_name='your-region',  # Uncomment and set your region if necessary
        )

        # Determine the content type if not provided
        if content_type is None:
            content_type, _ = mimetypes.guess_type(s3_key)
            content_type = content_type or 'application/octet-stream'

        # Set the appropriate content disposition based on the file type
        content_disposition = 'inline' if content_type == 'application/pdf' else 'attachment'

        # Include ExtraArgs to set content type and content disposition
        s3.upload_fileobj(
            file,
            bucket_name,
            s3_key,
            ExtraArgs={
                "ContentType": content_type,
                "ContentDisposition": content_disposition,
            },
        )
    except (BotoCoreError, ClientError) as e:
        # Log the error and re-raise as a custom exception
        error_message = f"Failed to upload file to S3. Error: {str(e)}"
        logger.error(error_message)
        raise boto3.exceptions.S3UploadFailedError(error_message)


default_resume = """
Klein Udumaga - Digital Marketing and Growth Hacking Specialist
kleinuduh@gmail.com

LINKS
https://www.linkedin.com/in/klein-udumaga-donald-2a8238ba https://kleinuduh.medium.com/

PROFILE
Klein is a digital marketing and growth professional. As a marketing and growth whizz, he has worked at both agency and client-side and has gained experience across different verticals, including Fintech, Ecommerce, SaaS, Edutech, Health and more.

EXPERIENCE
Nov 2022 - Present
Marketing Lead - Parmz Digital Technologies Crafted a comprehensive marketing strategy for Parmz Digital Technologies. Led the design of inventive and captivating content across various social platforms. Formulated PPC advertising budget allocations. Conducted in-depth keyword analysis to optimize channel content for search visibility. Designed and implemented multi-platform promotional campaigns. Established a promotional calendar and coordinated content release schedules for each distribution channel.

May 2022 - Oct 2022
Marketing Specialist- Emsisoft Ltd. (Contract) Oversaw email marketing campaigns targeting over 300,000 users. Crafted and analyzed content for a ransomware report, recognized by CNN and cited across the industry. Steered and implemented PR initiatives. Facilitated communications and fostered relationships with government entities like Europol on the company's behalf. Supervised blog content and coordinated with freelance contributors.

Sept 2021 - Feb, 2022
Marketing Manager - WeLoveNoCode Accelerated revenue growth from $840,000 to $3M ARR in just five months, achieving 30% month-over-month expansion. Independently initiated, fine-tuned, and enhanced 5+ paid campaigns on Facebook and Instagram, resulting in a 4X Return on Ad Spend (ROAS). Boosted Domain Rating (DR) from 16 to 29, advanced SEO site health to 74%, and achieved a top 6 ranking for targeted keywords within three months. Aided in the design of custom landing pages, imagery, and content to cater to specific segments of our audience, leveraging automation wherever feasible.

Mar 2020 - Dec 2021
Marketing Manager - Sankofa Pan African Series Crafted and implemented a comprehensive marketing blueprint. Nurtured the YouTube channel's growth from scratch to over 48,000 subscribers within a year. Designed and rolled out YouTube ads that achieved a 3% Click-Through Rate (CTR). Produced video content that amassed over 2 million views. Supervised content creators to enhance the channel's offerings. Oversaw community engagement and formulated a revenue-generating strategy for the channel. Took hands-on roles in video creation, editing, publishing, and promotion. Engaged in content collaborations with prominent YouTube channels, such as 2nacheki.

Apr 2021 - Sept 2021
Ads Operations Manager - DelusionMFG (Contract) Boosted monthly revenue from $60,000 to over $100,000 in just six months. Increased Conversion Rate from 0.53% to 1.68%. Independently initiated, refined, and enhanced 20+ paid campaigns on Facebook and Instagram, achieving a remarkable 7X Return on Ad Spend (ROAS). Oversaw a substantial five-figure monthly advertising budget. Delivered weekly reports on channel performance to the marketing team and account management, while also forecasting monthly response volumes and budget allocations.

SKILLS Funnel Design and Optimization Lead Magnet Design Email Automation Analytics Tracking Content Creation Workflow Paid Media Buying (Facebook, Google) Search Engine Optimization Adobe Photoshop and Premier Pro HubSpot CRM Keyword Research Graphics Design No-code development(Bubble & Airtable)

EDUCATION & CERTIFICATION
YABA COLLEGE OF TECHNOLOGY | 2013 - 2018 HIGHER NATIONAL DIPLOMA, METALLURGICAL AND MATERIALS ENGINEERING

HUBSPOT ACADEMY
DIGITAL ADVERTISING CERTIFIED | FEB, 2021

HUBSPOT ACADEMY
CONTENT MARKETING CERFICATION | FEB, 2021

TOOLS I USE
Bubble Airtable Asana Miro Google Analytics Facebook Ads Manager Google Keyword Planner Notion Hootsuite Hubspot Ahref Tilda
"""


job_description = """
Job Title: Digital Marketing Specialist
Location: Acme Corporation, New York, NY

Department: Marketing

Reports To: John Smith, Marketing Manager

Employment Type: Full-Time

Job Summary:
Acme Corporation is seeking a creative and results-driven Digital Marketing Specialist to join our dynamic marketing team. The successful candidate will be responsible for developing, implementing, and managing marketing campaigns that promote our company and products. This role requires a deep understanding of digital marketing strategies, excellent communication skills, and the ability to analyze data to drive decisions.

Key Responsibilities:
Campaign Management: Plan and execute all digital marketing campaigns, including SEO/SEM, email, social media, and display advertising.
Content Creation: Develop engaging and high-quality content for various digital platforms.
Analytics: Monitor and analyze campaign performance metrics to optimize strategies and achieve marketing goals.
SEO and SEM: Optimize content and website structure for search engines to improve organic search rankings and increase traffic.
Social Media: Manage and grow the company's social media presence across platforms such as Facebook, Twitter, LinkedIn, and Instagram.
Email Marketing: Design and execute email marketing campaigns, including newsletters and promotional offers.
Collaboration: Work with internal teams to create landing pages and optimize user experience.
Market Research: Stay updated on industry trends, competitor activities, and emerging digital marketing technologies.
Qualifications:
Education: Bachelor’s degree in Marketing, Business, Communications, or a related field.
Experience: 2-4 years of experience in digital marketing or a related field.
Skills: Proficiency in digital marketing tools and platforms such as Google Analytics, Google AdWords, and social media management tools.
Attributes: Creative thinker, detail-oriented, and able to work independently as well as part of a team.
Certifications: Google Analytics and Google AdWords certifications preferred.
Benefits:
Competitive salary and comprehensive benefits package.
Opportunities for professional growth and advancement.
Collaborative and innovative work environment.
Application Process:
Interested candidates should submit their resume and cover letter to hr@acmecorp.com. Applications will be reviewed on a rolling basis until the position is filled.
"""

# result = asyncio.run(analyze_and_improve_document(content=default_resume, job_description=job_description))
# print(result)
# resume_pdf_url, resume_docx_url, cl_pdf_url, cl_docx_url = asyncio.run(get_anth_doc_urls(resume_content=default_resume, job_post_content=job_description))
# print(resume_pdf_url, resume_docx_url, cl_pdf_url, cl_docx_url)

test_result = {
    'analysis': {
        'readability': 'The original resume has good content but could be improved in terms of structure and formatting for better readability.',
        'tone': 'The tone is professional and achievement-oriented, which is appropriate for a marketing resume.',
        'structure': 'The structure needs improvement. Sections could be better organized and formatted for easier scanning.',
        'keywords': 'The resume includes relevant keywords for digital marketing, but could be further optimized to match the job description.'
    },
    'general_section_review': {
        'Profile': 'Good overview but could be more concise and impactful.',
        'Experience': 'Strong achievements but could benefit from better formatting and more consistent structure.',
        'Skills': 'Comprehensive list but could be categorized for better readability.',
        'Education': 'Adequate but could be moved to the end of the resume.',
        'Certifications': 'Relevant but could be formatted more professionally.'
    },
    'job_tailored_section_review': {
        'Experience': 'Aligns well with the job requirements, but could highlight more specific digital marketing campaign results.',
        'Skills': 'Matches many required skills, but could emphasize SEO/SEM and analytics more prominently.',
        'Certifications': 'Google certifications should be highlighted as they directly relate to the job requirements.'
    },
    'improved_resume_content': {
        'contact': {
            'name': 'Klein Udumaga',
            'job_title': 'Digital Marketing and Growth Specialist',
            'email': 'kleinuduh@gmail.com',
            'linkedIn': 'https://www.linkedin.com/in/klein-udumaga-donald-2a8238ba'
        },
        'summary': 'Results-driven Digital Marketing Specialist with a proven track record in developing and executing comprehensive marketing strategies across various industries. Expertise in growth hacking, content creation, and data-driven campaign optimization, consistently delivering significant ROI and revenue growth.',
        'experiences': {
            'experience_1': {
                'company_name': 'Parmz Digital Technologies',
                'job_role': 'Marketing Lead',
                'start_date': 'November 2022',
                'end_date': 'Present',
                'job_description': [
                    'Developed and implemented comprehensive marketing strategies, resulting in increased brand visibility and customer engagement.',
                    'Designed innovative content across multiple social platforms, enhancing brand presence and user interaction.',
                    'Optimized PPC advertising budgets and conducted in-depth keyword analysis, improving search visibility and ROI.',
                    'Orchestrated multi-platform promotional campaigns, significantly boosting product awareness and sales conversions.'
                ]
            },
            'experience_2': {
                'company_name': 'WeLoveNoCode',
                'job_role': 'Marketing Manager',
                'start_date': 'September 2021',
                'end_date': 'February 2022',
                'job_description': [
                    'Spearheaded marketing initiatives that accelerated revenue growth from $840,000 to $3M ARR in just five months, achieving 30% month-over-month expansion.',
                    'Independently managed and optimized 5+ paid campaigns on Facebook and Instagram, resulting in a 4X Return on Ad Spend (ROAS).',
                    'Improved Domain Rating (DR) from 16 to 29 and advanced SEO site health to 74%, achieving top 6 ranking for targeted keywords within three months.',
                    'Collaborated on design of custom landing pages and content, leveraging automation to enhance audience engagement and conversion rates.'
                ]
            },
            'experience_3': {
                'company_name': 'DelusionMFG',
                'job_role': 'Ads Operations Manager',
                'start_date': 'April 2021',
                'end_date': 'September 2021',
                'job_description': [
                    'Boosted monthly revenue from $60,000 to over $100,000 in six months through strategic ad campaign management.',
                    'Increased Conversion Rate from 0.53% to 1.68% through data-driven optimization techniques.',
                    'Managed and refined 20+ paid campaigns on Facebook and Instagram, achieving a 7X Return on Ad Spend (ROAS).',
                    'Oversaw a substantial five-figure monthly advertising budget, delivering weekly performance reports and forecasts to stakeholders.'
                ]
            }
        },
        'education': [
            {
                'institution': 'YABA COLLEGE OF TECHNOLOGY',
                'degree': 'Higher National Diploma, Metallurgical and Materials Engineering',
                'end_date': '2018',
                'location': 'Nigeria'
            }
        ],
        'skills': [
            'Digital Marketing Strategy',
            'SEO/SEM Optimization',
            'Social Media Marketing',
            'Content Creation and Management',
            'Data Analytics and Reporting',
            'PPC Advertising (Facebook, Google)',
            'Email Marketing Automation',
            'Conversion Rate Optimization',
            'Marketing Funnel Design',
            'Adobe Creative Suite',
            'HubSpot CRM',
            'No-code Development (Bubble & Airtable)'
        ],
        'certifications': [
            {
                'title': 'Google Analytics Certification',
                'issuing_organization': 'Google',
                'date_obtained': '2023'
            },
            {
                'title': 'Google Ads Certification',
                'issuing_organization': 'Google',
                'date_obtained': '2023'
            },
            {
                'title': 'Digital Advertising Certification',
                'issuing_organization': 'HubSpot Academy',
                'date_obtained': 'February 2021'
            },
            {
                'title': 'Content Marketing Certification',
                'issuing_organization': 'HubSpot Academy',
                'date_obtained': 'February 2021'
            }
        ]
    },
    'job_match_score': 85,
    'cover_letter': "Dear Hiring Manager,\n\nI am writing to express my strong interest in the Digital Marketing Specialist position at Acme Corporation. With over five years of experience in digital marketing and a proven track record of driving significant revenue growth and ROI, I am confident in my ability to contribute to your team's success.\n\nIn my current role as Marketing Lead at Parmz Digital Technologies, I have developed and implemented comprehensive marketing strategies that have significantly increased brand visibility and customer engagement. My experience aligns perfectly with your need for someone who can plan and execute digital marketing campaigns across various channels.\n\nSome key achievements that demonstrate my qualifications for this role include:\n\n• Accelerating revenue growth from $840,000 to $3M ARR in just five months at WeLoveNoCode, achieving a 30% month-over-month expansion.\n• Independently managing and optimizing paid campaigns on Facebook and Instagram, resulting in a 4X Return on Ad Spend (ROAS).\n• Improving SEO performance, including boosting Domain Rating from 16 to 29 and achieving top 6 ranking for targeted keywords within three months.\n• Increasing conversion rates from 0.53% to 1.68% through data-driven optimization techniques at DelusionMFG.\n\nI am particularly drawn to Acme Corporation's innovative approach to digital marketing and your commitment to staying at the forefront of industry trends. My expertise in SEO/SEM, content creation, and data analytics, combined with my Google Analytics and Ads certifications, position me to make immediate contributions to your team's goals.\n\nI am excited about the opportunity to bring my skills and passion for digital marketing to Acme Corporation. I look forward to the possibility of discussing how my experience and abilities can benefit your team.\n\nThank you for your consideration.\n\nSincerely,\nKlein Udumaga",
    'improvement_summary': {
        'key_changes': [
            'Restructured the resume for better readability and impact',
            'Crafted a concise and powerful professional summary',
            'Quantified achievements more consistently across experiences',
            'Reorganized and categorized skills for better alignment with job requirements',
            'Added relevant certifications and highlighted Google certifications'
        ],
        'ats_optimization': "Incorporated key terms from the job description such as 'SEO/SEM', 'email marketing', and 'Google Analytics' to improve ATS compatibility.",
        'tailoring_to_job': 'Emphasized experiences and skills most relevant to the Digital Marketing Specialist role, particularly highlighting campaign management, analytics, and SEO/SEM expertise.'
    },
    'interview_potential_score': 90
}


improved_resume_dict = {
    "customized_resume": {
        "name": "Klein Udumaga",
        "title": "Digital Marketing and Growth Specialist",
        "contact": {
            "email": "kleinuduh@gmail.com",
            "phone": "(555) 123-4567",
            "location": "New York, NY",
            "linkedin": "https://www.linkedin.com/in/klein-udumaga-donald-2a8238ba"
        },
        "summary": "Results-driven Digital Marketing Specialist with 5+ years of experience in developing and executing comprehensive marketing strategies across various industries. Proven track record of increasing revenue, optimizing campaigns, and driving engagement through innovative digital marketing techniques. Expertise in SEO/SEM, content creation, social media management, and data-driven decision making.",
        "experience": [
            {
                "company": "Emsisoft Ltd.",
                "position": "Marketing Specialist",
                "date": "May 2022 – October 2022",
                "location": "Remote",
                "responsibilities": [
                    "Managed email marketing campaigns targeting 300,000+ users, resulting in a 20% increase in open rates and a 15% boost in click-through rates",
                    "Crafted a high-impact ransomware report recognized by CNN, elevating brand authority and generating significant industry citations",
                    "Spearheaded PR initiatives and fostered relationships with government entities, enhancing the company's reputation in the cybersecurity sector"
                ]
            },
            {
                "company": "WeLoveNoCode",
                "position": "Marketing Manager",
                "date": "September 2021 – February 2022",
                "location": "Remote",
                "responsibilities": [
                    "Drove revenue growth from $840,000 to $3M ARR in 5 months, achieving 30% month-over-month expansion through strategic marketing initiatives",
                    "Optimized and managed 5+ paid campaigns on Facebook and Instagram, resulting in a 4X Return on Ad Spend (ROAS)",
                    "Improved Domain Rating from 16 to 29 and advanced SEO site health to 74%, achieving top 6 ranking for targeted keywords within three months"
                ]
            }
        ],
        "education": {
            "institution": "Yaba College of Technology",
            "degree": "Higher National Diploma, Metallurgical and Materials Engineering",
            "year": "2018",
            "location": "Yaba, Lagos"
        },
        "skills": [
            "Digital Marketing Strategy",
            "SEO/SEM",
            "Content Creation",
            "Social Media Management",
            "Email Marketing",
            "Analytics and Data Analysis",
            "PPC Advertising",
            "Marketing Automation",
            "Adobe Creative Suite",
            "HubSpot CRM"
        ],
        "certifications": [
            {
                "name": "Digital Advertising Certification - HubSpot Academy",
                "date": "February 2021"
            },
            {
                "name": "Content Marketing Certification - HubSpot Academy",
                "date": "February 2021"
            }
        ]
    },
    "customization_notes": [
        "Removed the Parmz Digital Technologies experience as requested.",
        "Maintained the chronological order of the remaining experiences.",
        "No other changes were made to preserve the overall structure and content of the resume."
    ],
    "effectiveness_impact": -0.2
}


# # resume
# document_type = "resume"
# original_content = test_result["improved_resume_content"]
# customization_request = "can you add the context that I managed a team of 4 people including video editors, content creators, etc in delusionMFG"

# # cover letter
# document_type = "cover letter"
# original_content = test_result["cover_letter"]
# customization_request = ""


doc_type = "resume"
is_optimized = True
customized_content = {'customized_document': {'name': 'Klein Udumaga', 'title': 'Digital Marketing Specialist', 'contact': {'email': 'kleinuduh@gmail.com', 'phone': '(555) 123-4567', 'location': 'New York, NY', 'linkedin': 'https://www.linkedin.com/in/klein-udumaga-donald-2a8238ba'}, 'summary': 'Results-driven Digital Marketing Specialist with 5+ years of experience in developing and executing comprehensive marketing strategies across various industries. Proven track record of increasing revenue, optimizing campaigns, and driving engagement through innovative digital marketing techniques. Expertise in SEO/SEM, content creation, social media management, and data-driven decision making.', 'experience': [{'company': 'Emsisoft Ltd.', 'position': 'Marketing Specialist', 'duration': 'May 2022 – October 2022', 'location': 'Remote', 'responsibilities': ['Managed email marketing campaigns for 300,000+ users, achieving a 20% increase in open rates and a 15% boost in click-through rates', 'Crafted a high-impact ransomware report recognized by CNN, generating significant industry buzz and increasing brand authority', "Spearheaded PR initiatives and fostered relationships with government entities, enhancing the company's reputation in the cybersecurity sector"]}, {'company': 'WeLoveNoCode', 'position': 'Marketing Manager', 'duration': 'September 2021 – February 2022', 'location': 'Remote', 'responsibilities': ['Drove revenue growth from $840,000 to $3M ARR in 5 months, achieving 30% month-over-month expansion through strategic marketing initiatives', 'Optimized paid campaigns on Facebook and Instagram, resulting in a 4X Return on Ad Spend (ROAS) and a 25% increase in qualified leads', 'Improved SEO performance, boosting Domain Rating from 16 to 29 and achieving top 6 ranking for targeted keywords within three months']}], 'education': {'institution': 'Yaba College of Technology', 'degree': 'Higher National Diploma, Metallurgical and Materials Engineering', 'year': '2018', 'location': 'Yaba, Nigeria'}, 'skills': ['Digital Marketing Strategy', 'SEO/SEM', 'Content Creation', 'Social Media Management', 'Email Marketing', 'Analytics & Reporting', 'PPC Advertising', 'Marketing Automation', 'Adobe Creative Suite', 'CRM Systems (HubSpot)'], 'certifications': [{'name': 'Digital Advertising Certification - HubSpot Academy', 'date': 'February 2021'}, {'name': 'Content Marketing Certification - HubSpot Academy', 'date': 'February 2021'}]}, 'customization_notes': ['Removed the experience entry for Parmz Digital Technologies as requested.', 'Maintained the chronological order of the remaining work experiences.', 'No other changes were made to preserve the overall structure and content of the resume.'], 'effectiveness_impact': -0.2, 'metadata': {'document_type': 'resume', 'customization_request': 'remove parmz digital technologies'}}
print("This is the customized content: ", customized_content)
pdf, docx = asyncio.run(generate_documents(doc_type, customized_content["customized_document"], is_optimized))
pdf_url, docx_url = asyncio.run(upload_documents_to_s3(pdf, docx, doc_type, is_optimized))
print(pdf_url, docx_url)
# customization_result = asyncio.run(anth_customize_document(document_type, original_content, customization_request))
# print(customization_result)


input_cost = 0.005514  # dollars
output_cost = 0.023595  # dollars
total = 0.029109  # every run

# "20 * 0.029109" = 0.58218  # from every user/opt_session
