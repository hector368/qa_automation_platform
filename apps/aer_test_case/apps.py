"""Configuración de la aplicación AER Test Case."""

from django.apps import AppConfig


class AerTestCaseConfig(AppConfig):
    """Configura la aplicación AER Test Case Generator."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.aer_test_case"
    verbose_name = "AER Test Case Generator"