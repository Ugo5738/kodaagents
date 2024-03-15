import boto3
from django.template.loader import render_to_string
from weasyprint import HTML

from resume.models import GeneratedResumePDF, Resume


def generate_and_store_resume_pdf(resume_id):
    # Step 1: Retrieve resume data
    resume = Resume.objects.get(id=resume_id)
    resume_data = {  # Convert your resume data to a suitable dictionary format
        "name": resume.name,
        "experiences": resume.experiences.all(),
        "education": resume.education.all(),
        # Include other fields as necessary
    }

    # Step 2: Render HTML with dynamic data
    html_content = render_to_string("resume_template.html", {"resume": resume_data})

    # Step 3: Convert HTML to PDF
    pdf = HTML(string=html_content).write_pdf()

    # Step 4: Upload PDF to S3
    s3_client = boto3.client("s3")
    pdf_file_name = f"resumes/{resume.name}_{resume_id}.pdf"
    s3_client.put_object(Bucket="your-s3-bucket-name", Key=pdf_file_name, Body=pdf)
    pdf_url = f"https://{your-s3-bucket-name}.s3.amazonaws.com/{pdf_file_name}"

    # Step 5: Save PDF information to database
    generated_pdf = GeneratedResumePDF.objects.create(
        resume=resume,
        pdf_file=pdf_url,  # Assuming this field stores the URL to the PDF in S3
        version=resume.version,  # Increment version as needed
    )

    # Step 6: Return PDF URL to frontend
    return pdf_url
