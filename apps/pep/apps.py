from django.apps import AppConfig


class PepConfig(AppConfig):
    """Configuración del generador PEP."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.pep"
    verbose_name = "PEP Generator"