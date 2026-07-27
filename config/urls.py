from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("pep/", include("apps.pep.urls")),
    path("", include("apps.test_cases.urls")),
]