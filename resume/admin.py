from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CustomizationAnalytics,
    CustomizationNote,
    DocumentCustomization,
    ImprovementSummary,
    JobDetails,
    KeyChange,
    OptimizationAnalytics,
    OptimizedDocument,
    OriginalDocument,
)


class KeyChangeInline(admin.TabularInline):
    model = KeyChange
    extra = 1

@admin.register(ImprovementSummary)
class ImprovementSummaryAdmin(admin.ModelAdmin):
    inlines = [KeyChangeInline]
    list_display = ('optimized_document', 'key_changes_count')

    def key_changes_count(self, obj):
        return obj.key_changes.count()
    key_changes_count.short_description = 'Number of Key Changes'

class CustomizationNoteInline(admin.TabularInline):
    model = CustomizationNote
    extra = 1

@admin.register(DocumentCustomization)
class DocumentCustomizationAdmin(admin.ModelAdmin):
    list_display = ('optimized_document', 'created_at', 'pdf_link', 'docx_link')
    list_filter = ('created_at', 'optimized_document__document_type')
    search_fields = ('instruction', 'content')
    inlines = [CustomizationNoteInline]

    def pdf_link(self, obj):
        return format_html("<a href='{url}' target='_blank'>PDF</a>", url=obj.pdf_url)
    pdf_link.short_description = 'PDF'

    def docx_link(self, obj):
        return format_html("<a href='{url}' target='_blank'>DOCX</a>", url=obj.docx_url)
    docx_link.short_description = 'DOCX'

@admin.register(OptimizedDocument)
class OptimizedDocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'created_at', 'is_latest', 'pdf_link', 'docx_link')
    list_filter = ('document_type', 'is_latest', 'created_at')
    search_fields = ('original_document__user__username', 'content')
    readonly_fields = ('created_at',)

    def user(self, obj):
        return obj.original_document.user
    user.short_description = 'User'

    def pdf_link(self, obj):
        return format_html("<a href='{url}' target='_blank'>PDF</a>", url=obj.pdf_url)
    pdf_link.short_description = 'PDF'

    def docx_link(self, obj):
        return format_html("<a href='{url}' target='_blank'>DOCX</a>", url=obj.docx_url)
    docx_link.short_description = 'DOCX'

@admin.register(OriginalDocument)
class OriginalDocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('user__username', 'content')
    readonly_fields = ('uploaded_at',)

@admin.register(JobDetails)
class JobDetailsAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'content')
    readonly_fields = ('created_at',)

@admin.register(OptimizationAnalytics)
class OptimizationAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('optimized_document', 'job_match_score', 'interview_potential_score')
    list_filter = ('job_match_score', 'interview_potential_score')
    search_fields = ('ats_optimization', 'tailoring_to_job')

@admin.register(CustomizationAnalytics)
class CustomizationAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('customization', 'effectiveness_impact')
    list_filter = ('effectiveness_impact',)

# Register any models that don't have custom admin classes
admin.site.register(KeyChange)
admin.site.register(CustomizationNote)
