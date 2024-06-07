from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html

from resume.models import (
    CoverLetter,
    CoverLetterAnalysis,
    JobPost,
    JobPostAnalysis,
    OptimizedCoverLetterContent,
    OptimizedResumeContent,
    Resume,
    ResumeAnalysis,
)


# Inline admin for analyses and optimized content to show them on the same page as their parent models
class JobPostAnalysisInline(admin.TabularInline):
    model = JobPostAnalysis
    extra = 1


class OptimizedCoverLetterContentInline(admin.TabularInline):
    model = OptimizedCoverLetterContent
    extra = 1


class CoverLetterAnalysisInline(admin.TabularInline):
    model = CoverLetterAnalysis
    extra = 1


class OptimizedResumeContentInline(admin.TabularInline):
    model = OptimizedResumeContent
    extra = 1


class ResumeAnalysisInline(admin.TabularInline):
    model = ResumeAnalysis
    extra = 1


# Admin class for JobPost
@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ("job_post_id", "posted_at")
    search_fields = ("job_post_id",)
    inlines = [JobPostAnalysisInline]


# Admin class for CoverLetter
@admin.register(CoverLetter)
class CoverLetterAdmin(admin.ModelAdmin):
    list_display = ("cover_letter_id", "original_pdf_link", "general_improved_pdf_link")
    search_fields = ("cover_letter_id",)
    inlines = [CoverLetterAnalysisInline, OptimizedCoverLetterContentInline]

    def original_pdf_link(self, obj):
        if obj.original_pdf_s3_key:
            url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{obj.original_pdf_s3_key}"
            return format_html(
                "<a href='{url}' target='_blank'>View Original PDF</a>", url=url
            )
        return "No file"

    original_pdf_link.short_description = "Original PDF"

    def general_improved_pdf_link(self, obj):
        if obj.general_improved_pdf_s3_key:
            url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{obj.general_improved_pdf_s3_key}"
            return format_html(
                "<a href='{url}' target='_blank'>View Improved PDF</a>", url=url
            )
        return "No file"

    general_improved_pdf_link.short_description = "General Improved PDF"


# Admin class for Resume
@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("resume_id", "original_pdf_link", "general_improved_pdf_link")
    search_fields = ("resume_id",)
    inlines = [ResumeAnalysisInline, OptimizedResumeContentInline]

    def original_pdf_link(self, obj):
        if obj.original_pdf_s3_key:
            url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{obj.original_pdf_s3_key}"
            return format_html(
                "<a href='{url}' target='_blank'>View Original PDF</a>", url=url
            )
        return "No file"

    original_pdf_link.short_description = "Original PDF"

    def general_improved_pdf_link(self, obj):
        if obj.general_improved_pdf_s3_key:
            url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{obj.general_improved_pdf_s3_key}"
            return format_html(
                "<a href='{url}' target='_blank'>View Improved PDF</a>", url=url
            )
        return "No file"

    general_improved_pdf_link.short_description = "General Improved PDF"


@admin.register(OptimizedCoverLetterContent)
class OptimizedCoverLetterContentAdmin(admin.ModelAdmin):
    list_display = ("cover_letter", "is_tailored", "optimized_pdf_link", "optimized_at")
    search_fields = ("cover_letter__cover_letter_id",)

    def optimized_pdf_link(self, obj):
        if obj.optimized_pdf_s3_key:
            url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{obj.optimized_pdf_s3_key}"
            return format_html(
                "<a href='{url}' target='_blank'>View Optimized PDF</a>", url=url
            )
        return "No file"

    optimized_pdf_link.short_description = "Optimized PDF"


@admin.register(OptimizedResumeContent)
class OptimizedResumeContentAdmin(admin.ModelAdmin):
    list_display = ("resume", "is_tailored", "optimized_pdf_link", "optimized_at")
    search_fields = ("resume__resume_id",)

    def optimized_pdf_link(self, obj):
        if obj.optimized_pdf_s3_key:
            url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{obj.optimized_pdf_s3_key}"
            return format_html(
                "<a href='{url}' target='_blank'>View Optimized PDF</a>", url=url
            )
        return "No file"

    optimized_pdf_link.short_description = "Optimized PDF"


# Admin classes for analyses that are not directly tied to a parent model in the admin interface
@admin.register(JobPostAnalysis)
class JobPostAnalysisAdmin(admin.ModelAdmin):
    list_display = ("job_post", "readability_score", "sentiment_score", "analyzed_at")
    search_fields = ("job_post__job_post_id",)


@admin.register(CoverLetterAnalysis)
class CoverLetterAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "cover_letter",
        "readability_score",
        "sentiment_score",
        "analyzed_at",
    )
    search_fields = ("cover_letter__cover_letter_id",)


@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):
    list_display = ("resume", "readability_score", "sentiment_score", "analyzed_at")
    search_fields = ("resume__resume_id",)
