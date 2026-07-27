from django.urls import path

from . import views


app_name = "test_cases"

urlpatterns = [
    path("", views.home, name="home"),
]