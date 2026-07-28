"""Rutas del generador PEP."""

from django.urls import path

from apps.pep import views


app_name = "pep"


urlpatterns = [
    path(
        "",
        views.home,
        name="home",
    ),
    path(
        "analyze/",
        views.analyze_documents,
        name="analyze",
    ),
    path(
        "generate/",
        views.generate_pep,
        name="generate",
    ),
    path(
        "download/",
        views.download_pep,
        name="download",
    ),
]