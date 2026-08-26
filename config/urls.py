from django.contrib import admin
from django.urls import include
from django.urls import path


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
    ),
    path(
        "pep/",
        include("apps.pep.urls"),
    ),
    path(
        "aer-test-case/",
        include("apps.aer_test_case.urls"),
    ),
    path(
        "",
        include("apps.test_cases.urls"),
    ),
]