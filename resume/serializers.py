from rest_framework import serializers

from resume.utils.util_funcs import get_full_url

from .models import (
    CoverLetter,
    CoverLetterAnalysis,
    JobPost,
    JobPostAnalysis,
    OptimizedCoverLetterContent,
    OptimizedResumeContent,
    Resume,
    ResumeAnalysis,
)


class JobPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPost
        fields = "__all__"


# CoverLetter
class CoverLetterSerializer(serializers.ModelSerializer):
    original_pdf_url = serializers.SerializerMethodField()
    general_improved_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = CoverLetter
        fields = (
            "original_pdf_url",
            "general_improved_pdf_url",
        )

    def get_original_pdf_url(self, obj):
        return (
            get_full_url(obj.original_pdf_s3_key) if obj.original_pdf_s3_key else None
        )

    def get_general_improved_pdf_url(self, obj):
        return (
            get_full_url(obj.general_improved_pdf_s3_key)
            if obj.general_improved_pdf_s3_key
            else None
        )


class CoverLetterAnalysisSerializer(serializers.ModelSerializer):
    cover_letter = CoverLetterSerializer(read_only=True)

    class Meta:
        model = CoverLetterAnalysis
        fields = "__all__"


class OptimizedCoverLetterContentSerializer(serializers.ModelSerializer):
    optimized_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = OptimizedCoverLetterContent
        fields = ("optimized_pdf_url",)

    def get_optimized_pdf_url(self, obj):
        return (
            get_full_url(obj.optimized_pdf_s3_key) if obj.optimized_pdf_s3_key else None
        )


# Resume
class ResumeSerializer(serializers.ModelSerializer):
    original_pdf_url = serializers.SerializerMethodField()
    general_improved_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = (
            "original_pdf_url",
            "general_improved_pdf_url",
        )

    def get_original_pdf_url(self, obj):
        return (
            get_full_url(obj.original_pdf_s3_key) if obj.original_pdf_s3_key else None
        )

    def get_general_improved_pdf_url(self, obj):
        return (
            get_full_url(obj.general_improved_pdf_s3_key)
            if obj.general_improved_pdf_s3_key
            else None
        )


class ResumeAnalysisSerializer(serializers.ModelSerializer):
    resume = ResumeSerializer(read_only=True)

    class Meta:
        model = ResumeAnalysis
        fields = "__all__"


class OptimizedResumeSerializer(serializers.ModelSerializer):
    optimized_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = OptimizedResumeContent
        fields = ("optimized_pdf_url",)

    def get_optimized_pdf_url(self, obj):
        return (
            get_full_url(obj.optimized_pdf_s3_key) if obj.optimized_pdf_s3_key else None
        )
