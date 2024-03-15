from django.db import models

from accounts.models import User


class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resumes")
    role = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    linkedIn = models.URLField(blank=True, null=True)
    summary = models.TextField()
    version = models.IntegerField(default=1)

    def __str__(self):
        return f"Resume for {self.name}"


class UserUploadedResumePDF(models.Model):
    resume = models.ForeignKey(
        Resume, on_delete=models.CASCADE, related_name="uploaded_pdfs"
    )
    pdf_file = models.FileField(upload_to="user_uploaded_resumes/")
    uploaded_at = models.DateTimeField(auto_now_add=True)


class GeneratedResumePDF(models.Model):
    resume = models.ForeignKey(
        Resume, on_delete=models.CASCADE, related_name="generated_pdfs"
    )
    pdf_file = models.FileField(upload_to="generated_resumes/")
    created_at = models.DateTimeField(auto_now_add=True)


class Experience(models.Model):
    resume = models.ForeignKey(
        Resume, related_name="experiences", on_delete=models.CASCADE
    )
    company_name = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    start_date = models.CharField(max_length=20)
    end_date = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    job_description = models.TextField()

    def __str__(self):
        return f"{self.job_title} at {self.company_name}"


class Education(models.Model):
    resume = models.ForeignKey(
        Resume, related_name="education", on_delete=models.CASCADE
    )
    institution = models.CharField(max_length=255)
    degree = models.CharField(max_length=255)
    end_date = models.CharField(max_length=20)
    location = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.degree} from {self.institution}"


class Skill(models.Model):
    resume = models.ForeignKey(Resume, related_name="skills", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Certification(models.Model):
    resume = models.ForeignKey(
        Resume, related_name="certifications", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    issuing_organization = models.CharField(max_length=255)
    date_obtained = models.CharField(max_length=20)
    validity_period = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.title


class Reference(models.Model):
    resume = models.ForeignKey(
        Resume, related_name="references", on_delete=models.CASCADE
    )
    referee_name = models.CharField(max_length=255, blank=True, null=True)
    relationship = models.CharField(max_length=255, blank=True, null=True)
    contact_information = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Reference: {self.referee_name or 'Unavailable'}"
