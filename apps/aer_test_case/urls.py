"""Rutas HTTP del AER Test Case Generator."""

from django.urls import path

from apps.aer_test_case import views


app_name = "aer_test_case"

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