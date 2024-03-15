from django.contrib import admin

from .models import Certification, Education, Experience, Reference, Resume, Skill


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 1


class EducationInline(admin.TabularInline):
    model = Education
    extra = 1


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 1


class CertificationInline(admin.TabularInline):
    model = Certification
    extra = 1


class ReferenceInline(admin.TabularInline):
    model = Reference
    extra = 1


class ResumeAdmin(admin.ModelAdmin):
    inlines = [
        ExperienceInline,
        EducationInline,
        SkillInline,
        CertificationInline,
        ReferenceInline,
    ]
    list_display = ("name", "email", "created_at")
    search_fields = ("name", "email")
    list_filter = ("created_at",)
    ordering = ("-created_at",)


admin.site.register(Resume, ResumeAdmin)
