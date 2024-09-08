from django.urls import path

from resume import views

urlpatterns = [
    path('upload-document/', views.DocumentUploadView.as_view(), name='document-upload'),
    path('get-documents/', views.DocumentsView.as_view(), name='resumes'),
    path("upload-resume/", views.FileUploadView.as_view(), name="file-upload"),
    path('delete-original/<int:id>/', views.DeleteOriginalDocumentView.as_view(), name='delete-original'),
    path('delete-optimized/<int:id>/', views.DeleteOptimizedDocumentView.as_view(), name='delete-optimized'),

]
