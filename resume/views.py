import uuid

from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from resume.models import OptimizedDocument, OriginalDocument
from resume.serializers import OptimizedDocumentSerializer, OriginalDocumentSerializer


class DocumentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        document_type = request.query_params.get('document_type', 'resume')

        # Get all original documents for the user and document type
        original_documents = OriginalDocument.objects.filter(
            user=request.user,
            document_type=document_type
        )

        # Get all optimized documents for the user and document type
        optimized_documents = OptimizedDocument.objects.filter(
            original_document__user=request.user,
            document_type=document_type,
            is_latest=True
        )

        grouped_documents = {}

        # Process original documents
        for document in original_documents:
            grouped_documents[document.category] = {
                'original': OriginalDocumentSerializer(document).data,
                'optimized': None
            }

        # Process optimized documents
        for optimized in optimized_documents:
            category = optimized.original_document.category
            if category not in grouped_documents:
                # If there's no original document, create an entry with only optimized document
                grouped_documents[category] = {
                    'original': None,
                    'optimized': OptimizedDocumentSerializer(optimized).data
                }
            else:
                # If there's an original document, add the optimized document to it
                grouped_documents[category]['optimized'] = OptimizedDocumentSerializer(optimized).data

        return Response(grouped_documents)


class DocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_obj = request.FILES.get('file')
        category = request.data.get('category', "General")
        document_type = request.data.get('document_type')

        if not all([file_obj, category, document_type]):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        file_key = f"temp/{uuid.uuid4()}_{file_obj.name}"
        file_name = default_storage.save(file_key, file_obj)
        file_url = default_storage.url(file_name)

        # Check if a document already exists for this user, category, and document_type
        existing_document = OriginalDocument.objects.filter(
            user=request.user,
            category=category,
            document_type=document_type
        ).first()

        if existing_document:
            # Update existing document
            existing_document.file_key = file_key
            existing_document.file_url = file_url
            existing_document.save()
            serializer = OriginalDocumentSerializer(existing_document)
        else:
            # Create new document
            new_document = OriginalDocument.objects.create(
                user=request.user,
                category=category,
                file_key=file_key,
                file_url=file_url,
                document_type=document_type
            )
            serializer = OriginalDocumentSerializer(new_document)

        return Response({
            'success': True,
            'message': 'Document uploaded successfully',
            'document': serializer.data
        }, status=status.HTTP_200_OK)


class DeleteOriginalDocumentView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        try:
            document = OriginalDocument.objects.get(id=id, user=request.user)
            document.delete()  # This will also delete associated OptimizedDocuments due to CASCADE
            return Response({"message": "Original document and its optimized versions deleted successfully"}, status=status.HTTP_200_OK)
        except OriginalDocument.DoesNotExist:
            return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)


class DeleteOptimizedDocumentView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        try:
            document = OptimizedDocument.objects.get(id=id, original_document__user=request.user)
            document.delete()
            return Response({"message": "Optimized document deleted successfully"}, status=status.HTTP_200_OK)
        except OptimizedDocument.DoesNotExist:
            return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.data['file']
        print("This is the file obj: ", file_obj)
        file_key = f"temp/{uuid.uuid4()}_{file_obj.name}"
        file_name = default_storage.save(file_key, file_obj)
        print("This is the file name: ", file_name)
        file_url = default_storage.url(file_name)
        print("This is the file url: ", file_url)

        category="General"
        document_type="resume"

        OriginalDocument.objects.update_or_create(
            user=request.user,
            category=category,
            defaults={
                'file_key': file_key,
                'file_url': file_url,
                'document_type': document_type,
            }
        )

        return Response({"success": True, "file_key": file_name}, status=status.HTTP_200_OK)


# SAMPLE GROUPED DOCUMENT
{
  'Digital Marketing': {
    'original': {
      'id': 1,
      'file_url': "https://kodastorage.s3.amazonaws.com/media/temp/4f9c2e00-2e8d-431e-891f-5de0febb521c_%20Klein%20Udumaga's%20CV%20-1%20.pdf",
      'document_type': 'resume',
      'uploaded_at': '2024-09-04T17:19:47.513444Z'
    },
    'optimized': {
      'id': 1,
      'pdf_url': 'https://kodastorage.s3.amazonaws.com/media/resume/optimized/41f3662a-2f84-4d96-aa7e-8a01d64f8df6.pdf',
      'docx_url': 'https://kodastorage.s3.amazonaws.com/media/resume/optimized/1714cfd0-9585-495b-8eb2-8ce1405e94c8.docx',
      'document_type': 'resume',
      'created_at': '2024-09-04T17:20:34.138902Z'
    }
  },
  'General': {
    'original': {
      'id': 2,
      'file_url': 'https://kodastorage.s3.amazonaws.com/media/temp/79d49147-5dc1-488d-ba93-cefb1bc7dbc3_CVAlain%20august.pdf',
      'document_type': 'resume',
      'uploaded_at': '2024-09-04T17:34:53.482218Z'
    },
    'optimized': {
      'id': 3,
      'pdf_url': 'https://kodastorage.s3.amazonaws.com/media/resume/improved/891921cf-131a-4660-a419-03622b974dab.pdf',
      'docx_url': 'https://kodastorage.s3.amazonaws.com/media/resume/improved/0511a02f-9fc5-47f3-a82b-b831a2118e78.docx',
      'document_type': 'resume',
      'created_at': '2024-09-04T17:35:44.021790Z'
    }
  }
}
