from django.apps import AppConfig


class TestCasesConfig(AppConfig):
    """Configuración del generador de casos de prueba."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.test_cases"
    verbose_name = "Test Case Generator"