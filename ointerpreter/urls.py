from django.urls import include, path

from ointerpreter import views

urlpatterns = [
    path(
        "interpret/",
        views.CodeInterpreterView.as_view(),
        name="interpret",
    ),
]
