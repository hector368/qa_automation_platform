from django.urls import path

from . import views


app_name = "pep"

urlpatterns = [
    path("", views.home, name="home"),
]