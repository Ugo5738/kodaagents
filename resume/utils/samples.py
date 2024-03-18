import json

default_resume = """
SARAH JOHNSON
Email: sjohnsonnurse@example.com | Phone: +1-555-123-4567 | Location: Seattle, Washington

SUMMARY
Registered Nurse with over 5 years of experience in providing high-quality patient care in hospital settings. Skilled in emergency care, patient education, and health advocacy. Demonstrated ability to work effectively in fast-paced environments. Committed to improving patient health outcomes through compassionate care and medical expertise. Fluent in English and Spanish, with strong communication skills and a focus on patient-centered care.

EXPERIENCE
Seattle General Hospital | Registered Nurse June 2019 - Present | Seattle, Washington

Provided critical care for patients in the emergency department, reducing patient wait times by 20%.
Led a team of nurses to implement a new patient triage system, increasing department efficiency by 30%.
Developed and conducted patient education programs on chronic disease management, improving patient compliance by 40%.
Harborview Medical Center | Staff Nurse January 2017 - June 2019 | Seattle, Washington

Managed care for patients with diverse medical conditions in a 30-bed unit.
Collaborated with interdisciplinary teams to develop patient care plans, enhancing patient satisfaction scores by 25%.
Initiated a peer mentoring program for new nurses, reducing turnover rate by 15%.
Rainier Valley Community Clinic | Community Health Nurse July 2015 - December 2016 | Seattle, Washington

Provided primary care and health education to underserved populations.
Coordinated community health fairs, resulting in a 50% increase in clinic visits and health screenings.
Implemented a vaccination outreach program, increasing vaccination rates in the community by 35%.
EDUCATION
University of Washington | Bachelor of Science in Nursing (BSN) | June 2015 | Seattle, Washington

TECHNICAL SKILLS

Nursing Software: Epic, Cerner, Meditech
Medical Equipment: IV pumps, EKG machines, Ventilators
Basic Life Support (BLS), Advanced Cardiac Life Support (ACLS)
Electronic Health Records (EHRs)
CERTIFICATIONS

Registered Nurse (RN) License, State of Washington
Certified Emergency Nurse (CEN)
Trauma Nursing Core Course (TNCC)
Pediatric Advanced Life Support (PALS)
PROFESSIONAL MEMBERSHIPS

American Nurses Association (ANA)
Emergency Nurses Association (ENA)
VOLUNTEERING

Volunteer Nurse, Seattle Free Clinic
Health Educator, Local High Schools
REFERENCES
Available upon request.

LinkedIn Profile: https://www.linkedin.com/in/sarah-johnson-rn
"""


resume_fb_example_structure = json.dumps(
    {
        "contact": "Feedback on contact section",
        "summary": "Feedback on summary section",
        "experiences": {
            "experience_1": "Feedback on first experience section",
            "experience_2": "Feedback on second experience section",
            "experience_3": "Feedback on third experience section",
            # Additional education entries can be added here
        },
        "education": [
            "Feedback on first education section",
            # Additional education entries can be added here
        ],
        "skills": "Feedback on skills section",
        "certifications": [
            "Feedback on certifications section",
            # Additional certifications can be listed here
        ],
        # "projects": [
        #     "Feedback on projects section",
        #     # Additional projects can be listed here
        # ],
        "references": [
            "Feedback on references section",
            # Additional references can be added here
        ],
    },
    indent=2,
)


resume_example_structure = json.dumps(
    {
        "contact": {
            "name": "Sender Name",
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
