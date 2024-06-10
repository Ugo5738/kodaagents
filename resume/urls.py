from django.urls import path

from resume import views

urlpatterns = [
    path(
        "get-improved-resumes/<str:resume_id>/",
        views.ResumeDetailView.as_view(),
        name="improved_resume_detail",
    ),
    path(
        "get-optimized-resumes/<str:resume_id>/",
        views.OptimizedResumeContentDetailView.as_view(),
        name="optimized_resume_detail",
    ),
    path(
        "get-improved-cover-letters/<str:cover_letter_id>/",
        views.CoverLetterDetailView.as_view(),
        name="improved_cover_letter_detail",
    ),
    path(
        "get-optimized-cover-letters/<str:cover_letter_id>/",
        views.OptimizedCoverLetterContentDetailView.as_view(),
        name="optimized_cover_letter_detail",
    ),
    path(
        "get-improved-jobs/<str:job_id>/",
        views.JobPostDetailView.as_view(),
        name="improved_job_detail",
    ),
    # =====================> Resume URLs <=====================
    path(
        "improve-resume/<str:applicant_id>/",
        views.ResumeImprovementView.as_view(),
        name="improve_resume",
    ),  # ~ 173 secs
    path(
        "optimize-resume/<str:applicant_id>/<str:job_post_id>/",
        views.ResumeOptimizationView.as_view(),
        name="resume_optimization",
    ),  # ~ 91 secs
    path(
        "customize-improved-resume/<str:applicant_id>/",
        views.ResumeImprovementCustomizationView.as_view(),
        name="customize_improved_resume",
    ),  # ~ 92 secs
    path(
        "customize-optimize-resume/<str:applicant_id>/<str:job_post_id>/",
        views.ResumeOptimizationCustomizationView.as_view(),
        name="customize_resume_optimization",
    ),  # ~ 80 secs
    # =====================> Cover Letter URLs <=====================
    path(
        "create-cover-letter/<str:applicant_id>/",
        views.CoverLetterCreationView.as_view(),
        name="create_cover_letter",
    ),
    path(
        "improve-cover-letter/<str:applicant_id>/",
        views.CoverLetterImprovementView.as_view(),
        name="improve_cover_letter",
    ),  # ~ 58 secs
    path(
        "optimize-cover-letter/<str:applicant_id>/<str:job_post_id>/",
        views.CoverLetterOptimizationView.as_view(),
        name="optimize_cover_letter",
    ),  # ~ 41 secs
    path(
        "customize-improved-cover-letter/<str:applicant_id>/",
        views.CoverLetterImprovementCustomizationView.as_view(),
        name="customize_improved_cover_letter",
    ),  # ~ 53 secs
    path(
        "customize-optimize-cover-letter/<str:applicant_id>/<str:job_post_id>/",
        views.CoverLetterOptimizationCustomizationView.as_view(),
        name="customize_cover_letter_optimization",
    ),  # ~ 50 secs
    # =====================> Job Post URLs <=====================
    path(
        "optimize-job-post/<str:job_id>/",
        views.JobOptimizationView.as_view(),
        name="job_post_optimization",
    ),
    # # =====================> Testing <=====================
    # path("upload/", views.Boto3UploadView.as_view(), name="upload"),
    path("upload-resume/", views.FileUploadView.as_view(), name="file-upload"),
]
