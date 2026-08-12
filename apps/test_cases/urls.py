from django.urls import path

from . import views


app_name = "test_cases"

urlpatterns = [
    path(
        "",
        views.home,
        name="home",
    ),
    path(
        "analyze/",
        views.analyze_document,
        name="analyze",
    ),
    path(
        "generate/",
        views.generate_test_cases,
        name="generate",
    ),
    path(
        "generate/stream/",
        views.stream_generate_test_cases,
        name="generate_stream",
    ),
    path(
        "download/",
        views.download_xlsx,
        name="download",
    ),
]