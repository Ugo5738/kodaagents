from uuid import uuid4

from django.conf import settings
from django.db import models

from resume.utils.util_funcs import upload_directly_to_s3


class DocBase(models.Model):
    original_content = models.TextField(null=True, blank=True)
    general_improved_content = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True


class AnalysisBase(models.Model):
    readability_score = models.FloatField(null=True, blank=True)
    sentiment_score = models.FloatField(null=True, blank=True)
    tone_analysis = models.JSONField(null=True, blank=True)
    analyzed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class JobPost(models.Model):
    job_post_id = models.CharField(
        max_length=255, unique=True
    )  # ID from the Recruiting Platform
    original_content = models.TextField(null=True, blank=True)
    optimized_content = models.TextField(null=True, blank=True)
    posted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job_post_id


class JobPostAnalysis(AnalysisBase):
    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE)

    def __str__(self):
        return f"Analysis for Job Post ID {self.job_post.job_post_id}"


class CoverLetter(DocBase):
    cover_letter_id = models.CharField(max_length=255, unique=True)
    # original_pdf = models.FileField(
    #     upload_to="cover_letters/original/", null=True, blank=True
    # )
    # general_improved_pdf = models.FileField(
    #     upload_to="cover_letters/general_improved/", null=True, blank=True
    # )
    original_pdf_s3_key = models.CharField(max_length=1024, null=True, blank=True)
    general_improved_pdf_s3_key = models.CharField(
        max_length=1024, null=True, blank=True
    )

    def __str__(self):
        return f"Cover Letter ID {self.cover_letter_id}"

    def upload_to_s3(self, file, is_general_improved=False):
        s3_key = f"cover_letters/{'general_improved/' if is_general_improved else 'original/'}{uuid4()}.pdf"
        upload_directly_to_s3(file, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
        if is_general_improved:
            self.general_improved_pdf_s3_key = s3_key
        else:
            self.original_pdf_s3_key = s3_key


class CoverLetterAnalysis(AnalysisBase):
    cover_letter = models.ForeignKey(CoverLetter, on_delete=models.CASCADE)
    keyword_matches = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Analysis for Cover Letter ID {self.cover_letter.cover_letter_id}"


# class OptimizedCoverLetterContent(models.Model):
#     cover_letter = models.ForeignKey(CoverLetter, on_delete=models.CASCADE)
#     optimized_content = models.TextField()
#     optimized_pdf = models.FileField(
#         upload_to="cover_letters/optimized/", null=True, blank=True
#     )
#     is_tailored = models.BooleanField(default=False)
#     job_post = models.ForeignKey(
#         JobPost, on_delete=models.CASCADE, null=True, blank=True
#     )
#     analysis = models.ForeignKey(
#         CoverLetterAnalysis, on_delete=models.SET_NULL, null=True, blank=True
#     )
#     optimized_at = models.DateTimeField(auto_now_add=True)


#     def __str__(self):
#         tailored_str = "Tailored" if self.is_tailored else "General Improved"
#         return f"{tailored_str} Content for Cover Letter ID {self.cover_letter.cover_letter_id}"


class OptimizedCoverLetterContent(models.Model):
    cover_letter = models.ForeignKey(CoverLetter, on_delete=models.CASCADE)
    optimized_content = models.TextField()
    optimized_pdf_s3_key = models.CharField(max_length=1024, null=True, blank=True)
    is_tailored = models.BooleanField(default=False)
    job_post = models.ForeignKey(
        JobPost, on_delete=models.CASCADE, null=True, blank=True
    )
    analysis = models.ForeignKey(
        CoverLetterAnalysis, on_delete=models.SET_NULL, null=True, blank=True
    )
    optimized_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        tailored_str = "Tailored" if self.is_tailored else "General Improved"
        return f"{tailored_str} Content for Cover Letter ID {self.cover_letter.cover_letter_id}"

    def upload_optimized_pdf_to_s3(self, file):
        s3_key = f"cover_letters/optimized/{uuid4()}.pdf"
        upload_directly_to_s3(file, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
        self.optimized_pdf_s3_key = s3_key


class Resume(DocBase):
    resume_id = models.CharField(max_length=255, unique=True)
    # original_pdf = models.FileField(
    #     upload_to="resumes/original/", null=True, blank=True
    # )
    # general_improved_pdf = models.FileField(
    #     upload_to="resumes/general_improved/", null=True, blank=True
    # )
    original_pdf_s3_key = models.CharField(max_length=1024, null=True, blank=True)
    general_improved_pdf_s3_key = models.CharField(
        max_length=1024, null=True, blank=True
    )

    def __str__(self):
        return f"Resume ID {self.resume_id}"

    def upload_to_s3(self, file, is_general_improved=False):
        s3_key = f"resumes/{'general_improved/' if is_general_improved else 'original/'}{uuid4()}.pdf"
        upload_directly_to_s3(file, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
        if is_general_improved:
            self.general_improved_pdf_s3_key = s3_key
        else:
            self.original_pdf_s3_key = s3_key


class ResumeAnalysis(AnalysisBase):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE)
    keyword_matches = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Analysis for Resume ID {self.resume.resume_id}"


# class OptimizedResumeContent(models.Model):
#     resume = models.ForeignKey(Resume, on_delete=models.CASCADE)
#     optimized_content = models.TextField()
#     optimized_pdf = models.FileField(
#         upload_to="resumes/optimized/", null=True, blank=True
#     )
#     is_tailored = models.BooleanField(default=False)
#     analysis = models.ForeignKey(
#         ResumeAnalysis, on_delete=models.SET_NULL, null=True, blank=True
#     )
#     job_post = models.ForeignKey(
#         JobPost, on_delete=models.CASCADE, null=True, blank=True
#     )
#     optimized_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         tailored_str = "Tailored" if self.is_tailored else "General Improved"
#         return f"{tailored_str} Content for Cover Letter ID {self.resume.resume_id}"


class OptimizedResumeContent(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE)
    optimized_content = models.TextField()
    optimized_pdf_s3_key = models.CharField(max_length=1024, null=True, blank=True)
    is_tailored = models.BooleanField(default=False)
    analysis = models.ForeignKey(
        ResumeAnalysis, on_delete=models.SET_NULL, null=True, blank=True
    )
    job_post = models.ForeignKey(
        JobPost, on_delete=models.CASCADE, null=True, blank=True
    )
    optimized_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        tailored_str = "Tailored" if self.is_tailored else "General Improved"
        return f"{tailored_str} Content for Resume ID {self.resume.resume_id}"  # Fixed reference to cover letter

    def upload_optimized_pdf_to_s3(self, file):
        s3_key = f"resumes/optimized/{uuid4()}.pdf"
        upload_directly_to_s3(file, settings.AWS_STORAGE_BUCKET_NAME, s3_key)
        self.optimized_pdf_s3_key = s3_key
