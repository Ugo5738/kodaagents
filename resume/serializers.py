from rest_framework import serializers

from resume.models import OptimizedDocument, OriginalDocument


class OriginalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OriginalDocument
        fields = ['id', 'file_url', 'document_type', 'uploaded_at']

class OptimizedDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizedDocument
        fields = ['id', 'pdf_url', 'docx_url', 'document_type', 'created_at']
