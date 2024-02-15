from django.urls import path

from verification import views

urlpatterns = [
    # path(
    #     "birth-certificate/<str:document_id>/",
    #     views.VerifyAgeView.as_view(),
    #     name="age",
    # ),
    # path(
    #     "bank-statement/<str:document_id>/",
    #     views.VerifyBankStatementView.as_view(),
    #     name="income",
    # ),
    # path(
    #     "employee-letter/<str:document_id>/",
    #     views.VerifyEmployeeLetterView.as_view(),
    #     name="employee_letter",
    # ),
    # path("confirm-employment/", views.confirm_employment, name="confirm_employment"),
    # path("deny-employment/", views.deny_employment, name="deny_employment"),
    # path(
    #     "get_employment_status/<str:token>/",
    #     views.get_employment_verification_info,
    #     name="get_employment_status",
    # ),
    # path('scraper/', views.ScraperView.as_view(), name='scraper'),
    # path("apollo/", views.ApolloView.as_view(), name="apollo"),
    path(
        "verify-bank-statement/<str:document_id>/",
        views.BankStatementView.as_view(),
        name="bank_income",
    ),
]
