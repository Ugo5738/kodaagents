from django.core.files.storage import default_storage
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from accounts.models import User

DOC_TYPE_CHOICES = [('resume', 'Resume'), ('cover_letter', 'Cover Letter')]

class OriginalDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='original_documents')
    category = models.CharField(max_length=100, default='General')
    file_key = models.CharField(max_length=255)
    file_url = models.URLField()
    document_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField()  # Stored as plain text or JSON

    def __str__(self):
        return f"{self.user.username}'s {self.document_type} - {self.uploaded_at}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'category'], name='unique_user_category')
        ]


class JobDetails(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_details')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Job Details - {self.created_at}"


class OptimizedDocument(models.Model):
    original_document = models.ForeignKey(OriginalDocument, on_delete=models.CASCADE, related_name='optimized_versions')
    job_details = models.ForeignKey(JobDetails, on_delete=models.SET_NULL, null=True, blank=True)
    document_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    pdf_url = models.URLField()
    docx_url = models.URLField()
    content = models.TextField()  # Stored as plain text or JSON
    created_at = models.DateTimeField(auto_now_add=True)
    is_latest = models.BooleanField(default=True)

    def __str__(self):
        return f"Optimized {self.document_type} for {self.original_document.user.username} - {self.created_at}"


class DocumentCustomization(models.Model):
    optimized_document = models.ForeignKey(OptimizedDocument, on_delete=models.CASCADE, related_name='customizations')
    instruction = models.TextField()
    pdf_url = models.URLField()
    docx_url = models.URLField()
    content = models.TextField()  # Stored as plain text or JSON
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Customization for {self.optimized_document}"


class OptimizationAnalytics(models.Model):
    optimized_document = models.OneToOneField(OptimizedDocument, on_delete=models.CASCADE, related_name='analytics')
    job_match_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)], null=True, blank=True)
    interview_potential_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    ats_optimization = models.TextField()
    tailoring_to_job = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Analytics for {self.optimized_document}"


class ImprovementSummary(models.Model):
    optimized_document = models.OneToOneField(OptimizedDocument, on_delete=models.CASCADE, related_name='improvement_summary')

    def __str__(self):
        return f"Improvement Summary for {self.optimized_document}"


class KeyChange(models.Model):
    improvement_summary = models.ForeignKey(ImprovementSummary, on_delete=models.CASCADE, related_name='key_changes')
    description = models.TextField()

    def __str__(self):
        return f"Key Change for {self.improvement_summary}"


class CustomizationAnalytics(models.Model):
    customization = models.OneToOneField(DocumentCustomization, on_delete=models.CASCADE, related_name='analytics')
    effectiveness_impact = models.FloatField(validators=[MinValueValidator(-1), MaxValueValidator(1)])

    def __str__(self):
        return f"Customization Analytics for {self.customization}"


class CustomizationNote(models.Model):
    customization = models.ForeignKey(DocumentCustomization, on_delete=models.CASCADE, related_name='notes')
    content = models.TextField()

    def __str__(self):
        return f"Note for {self.customization}"
