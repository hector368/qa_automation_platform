"""Rutas HTTP del módulo MSP QA Matrix."""

from django.urls import path

from apps.msp_qa import views


app_name = "msp_qa"

urlpatterns = [
    path(
        "",
        views.home,
        name="home",
    ),
    path(
        "status/",
        views.connection_status,
        name="status",
    ),
    path(
        "projects/",
        views.projects,
        name="projects",
    ),
    path(
        "blocks/",
        views.blocks,
        name="blocks",
    ),
    path(
        "extract/",
        views.extract,
        name="extract",
    ),
    path(
        "write/",
        views.write_to_matrix,
        name="write",
    ),
    path(
        "catalog/",
        views.catalog,
        name="catalog",
    ),
    path(
        "preview/",
        views.preview,
        name="preview",
    ),
    path(
        "preview/edit/",
        views.edit_preview,
        name="edit_preview",
    ),
    path(
        "preview/check/",
        views.check_preview,
        name="check_preview",
    ),
    path(
        "batch-write/",
        views.batch_write,
        name="batch_write",
    ),
]
