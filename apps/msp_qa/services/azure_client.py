"""Cliente de consulta de la API REST de Azure DevOps."""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from typing import Any, Final

from django.conf import settings

from apps.msp_qa.exceptions import (
    AzureAuthenticationError,
    AzureConfigurationError,
    AzureRequestError,
    MspQaError,
    ProjectNotFoundError,
)


logger = logging.getLogger(__name__)

API_VERSION: Final[str] = "7.1"

DEFAULT_TIMEOUT_SECONDS: Final[int] = 30

HTTP_NON_AUTHORITATIVE: Final[int] = 203
HTTP_UNAUTHORIZED: Final[int] = 401
HTTP_FORBIDDEN: Final[int] = 403
HTTP_NOT_FOUND: Final[int] = 404


def get_organization_url() -> str:
    """Obtiene la URL de la organización, sin diagonal final."""
    organization_url = (
        getattr(settings, "AZURE_DEVOPS_ORG_URL", "")
        or ""
    ).strip()

    return organization_url.rstrip("/")


def get_personal_access_token() -> str:
    """Obtiene el token personal definido en el entorno."""
    return (
        getattr(settings, "AZURE_DEVOPS_PAT", "")
        or ""
    ).strip()


def get_request_timeout() -> int:
    """Obtiene el tiempo máximo de espera de cada consulta."""
    return int(
        getattr(
            settings,
            "AZURE_DEVOPS_TIMEOUT_SECONDS",
            DEFAULT_TIMEOUT_SECONDS,
        ),
    )


def build_authorization_header(
    personal_access_token: str,
) -> str:
    """
    Construye el encabezado de autenticación básica.

    Azure DevOps espera el token como contraseña y el usuario vacío.
    """
    raw_credentials = f":{personal_access_token}"

    encoded_credentials = base64.b64encode(
        raw_credentials.encode("utf-8"),
    ).decode("ascii")

    return f"Basic {encoded_credentials}"


def build_request_url(
    *,
    path: str,
    query: dict[str, str] | None = None,
) -> str:
    """
    Construye la URL completa de una consulta a Azure DevOps.

    Raises:
        AzureConfigurationError: Cuando falta la URL de organización.
    """
    organization_url = get_organization_url()

    if not organization_url:
        raise AzureConfigurationError(
            "La variable AZURE_DEVOPS_ORG_URL no está definida.",
        )

    parameters = dict(query or {})
    parameters.setdefault("api-version", API_VERSION)

    query_string = urllib.parse.urlencode(parameters)
    clean_path = path.lstrip("/")

    return f"{organization_url}/{clean_path}?{query_string}"


def request_json(
    *,
    path: str,
    query: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Ejecuta una consulta GET contra Azure DevOps.

    Args:
        path: Ruta relativa del recurso, por ejemplo "_apis/projects".
        query: Parámetros adicionales de la consulta.

    Returns:
        Cuerpo de la respuesta convertido a diccionario.

    Raises:
        AzureConfigurationError: Cuando falta el token o la URL.
        AzureAuthenticationError: Cuando el token es inválido.
        ProjectNotFoundError: Cuando el recurso no es visible.
        AzureRequestError: Cuando la consulta falla por otra causa.
    """
    personal_access_token = get_personal_access_token()

    if not personal_access_token:
        raise AzureConfigurationError(
            "La variable AZURE_DEVOPS_PAT no está definida.",
        )

    request_url = build_request_url(
        path=path,
        query=query,
    )

    request = urllib.request.Request(
        request_url,
        method="GET",
    )

    request.add_header(
        "Authorization",
        build_authorization_header(personal_access_token),
    )

    request.add_header(
        "Accept",
        "application/json",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=get_request_timeout(),
        ) as response:
            status_code = response.getcode()
            raw_body = response.read()

    except urllib.error.HTTPError as error:
        logger.warning(
            "Azure DevOps respondió con error HTTP %s en %s.",
            error.code,
            path,
        )

        raise translate_http_error(error) from error

    except urllib.error.URLError as error:
        logger.exception(
            "No fue posible conectar con Azure DevOps.",
        )

        raise AzureRequestError(
            f"No hubo respuesta de Azure DevOps: {error.reason}",
        ) from error

    except TimeoutError as error:
        logger.exception(
            "La consulta a Azure DevOps excedió el tiempo de espera.",
        )

        raise AzureRequestError(
            "La consulta a Azure DevOps excedió el tiempo de espera.",
        ) from error

    if status_code == HTTP_NON_AUTHORITATIVE:
        raise AzureAuthenticationError(
            "Azure DevOps devolvió una pantalla de inicio de sesión, "
            "lo que indica un token inválido o vencido.",
        )

    return decode_json_body(raw_body)


def translate_http_error(
    error: urllib.error.HTTPError,
) -> MspQaError:
    """Convierte un error HTTP en la excepción del módulo."""
    if error.code in (HTTP_UNAUTHORIZED, HTTP_FORBIDDEN):
        return AzureAuthenticationError(
            f"Azure DevOps respondió con el código {error.code}.",
        )

    if error.code == HTTP_NOT_FOUND:
        return ProjectNotFoundError(
            "Azure DevOps respondió 404. El recurso no existe o el "
            "token no tiene acceso a él.",
        )

    return AzureRequestError(
        f"Azure DevOps respondió con el código {error.code}.",
    )


def decode_json_body(raw_body: bytes) -> dict[str, Any]:
    """
    Convierte el cuerpo de la respuesta en un diccionario.

    Raises:
        AzureAuthenticationError: Cuando la respuesta no es JSON.
        AzureRequestError: Cuando el JSON no tiene la forma esperada.
    """
    try:
        decoded_body = raw_body.decode("utf-8")

    except UnicodeDecodeError as error:
        raise AzureRequestError(
            "La respuesta de Azure DevOps no está codificada en UTF-8.",
        ) from error

    try:
        payload = json.loads(decoded_body)

    except json.JSONDecodeError as error:
        raise AzureAuthenticationError(
            "Azure DevOps no devolvió JSON. Habitualmente significa "
            "que el token es inválido o ya venció.",
        ) from error

    if not isinstance(payload, dict):
        raise AzureRequestError(
            "Azure DevOps devolvió una estructura inesperada.",
        )

    return payload
