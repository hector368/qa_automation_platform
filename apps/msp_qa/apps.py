"""Configuración de la aplicación MSP QA Matrix."""

from django.apps import AppConfig


class MspQaConfig(AppConfig):
    """Configura el llenado automático de la matriz MSP_QA."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.msp_qa"
    verbose_name = "MSP QA Matrix"
