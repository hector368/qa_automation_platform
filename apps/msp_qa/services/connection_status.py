"""Diagnóstico de la configuración de acceso a Azure DevOps."""

from __future__ import annotations

import urllib.parse

from typing import Any

from apps.msp_qa.services.azure_client import (
    get_organization_url,
    get_personal_access_token,
)


def extract_organization_name(organization_url: str) -> str:
    """Obtiene el nombre de la organización a partir de su URL."""
    if not organization_url:
        return ""

    parsed_url = urllib.parse.urlparse(organization_url)

    path_segments = [
        segment
        for segment in parsed_url.path.split("/")
        if segment
    ]

    if path_segments:
        return path_segments[-1]

    return parsed_url.netloc


def build_connection_status() -> dict[str, Any]:
    """
    Describe el estado de la configuración de Azure DevOps.

    El token nunca se expone: solo se informa si está presente.

    Returns:
        Diccionario con el estado y las variables faltantes.
    """
    organization_url = get_organization_url()
    personal_access_token = get_personal_access_token()

    missing_variables: list[str] = []

    if not organization_url:
        missing_variables.append("AZURE_DEVOPS_ORG_URL")

    if not personal_access_token:
        missing_variables.append("AZURE_DEVOPS_PAT")

    is_configured = not missing_variables

    if is_configured:
        message = (
            "Conexión configurada. El token se leyó desde las "
            "variables de entorno."
        )
    else:
        missing_text = ", ".join(missing_variables)

        message = (
            "Falta configurar en el archivo .env: "
            f"{missing_text}."
        )

    return {
        "configured": is_configured,
        "organization_url": organization_url,
        "organization_name": extract_organization_name(
            organization_url,
        ),
        "missing_variables": missing_variables,
        "message": message,
    }
