"""Cliente de consulta de la API REST de Azure DevOps."""

from __future__ import annotations

import base64
import json
import logging
import time
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

DEFAULT_TIMEOUT_SECONDS: Final[int] = 60

# Intentos totales por consulta, incluido el primero.
DEFAULT_MAX_ATTEMPTS: Final[int] = 3

# Espera antes del reintento. Se duplica en cada vuelta.
RETRY_BACKOFF_SECONDS: Final[float] = 1.5

MAX_RETRY_DELAY_SECONDS: Final[float] = 30.0

HTTP_NON_AUTHORITATIVE: Final[int] = 203
HTTP_UNAUTHORIZED: Final[int] = 401
HTTP_FORBIDDEN: Final[int] = 403
HTTP_NOT_FOUND: Final[int] = 404
HTTP_TOO_MANY_REQUESTS: Final[int] = 429

# Códigos que indican una falla del servicio, no de la consulta. Se
# reintentan porque volver a preguntar suele bastar.
RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset(
    {
        HTTP_TOO_MANY_REQUESTS,
        500,
        502,
        503,
        504,
    },
)


class RetryLater(Exception):
    """Señala una falla pasajera que conviene reintentar."""

    def __init__(
        self,
        *,
        cause: MspQaError,
        retry_after: float = 0.0,
    ) -> None:
        """Conserva la excepción final y la espera sugerida."""
        super().__init__(str(cause))

        self.cause = cause
        self.retry_after = retry_after


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


def get_max_attempts() -> int:
    """Obtiene cuántos intentos se hacen por consulta."""
    attempts = int(
        getattr(
            settings,
            "AZURE_DEVOPS_MAX_ATTEMPTS",
            DEFAULT_MAX_ATTEMPTS,
        ),
    )

    return max(attempts, 1)


def read_retry_after(
    error: urllib.error.HTTPError,
) -> float:
    """
    Lee la espera que pide Azure DevOps al limitar el consumo.

    Cuando el servicio está saturado responde con el encabezado
    Retry-After. Respetarlo evita insistir antes de tiempo y empeorar
    la saturación.
    """
    raw_value = error.headers.get("Retry-After", "")

    try:
        return max(float(raw_value), 0.0)

    except (TypeError, ValueError):
        return 0.0


def calculate_retry_delay(
    *,
    attempt: int,
    retry_after: float,
) -> float:
    """Calcula cuánto esperar antes del siguiente intento."""
    backoff = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))

    return min(
        max(backoff, retry_after),
        MAX_RETRY_DELAY_SECONDS,
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


def send_request(
    *,
    path: str,
    query: dict[str, str] | None = None,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Ejecuta una consulta contra Azure DevOps.

    Args:
        path: Ruta relativa del recurso, por ejemplo "_apis/projects".
        query: Parámetros adicionales de la consulta.
        method: Verbo HTTP a usar.
        body: Cuerpo JSON de la petición, cuando el verbo lo admite.

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

    encoded_body = (
        json.dumps(body).encode("utf-8")
        if body is not None
        else None
    )

    authorization = build_authorization_header(personal_access_token)
    max_attempts = get_max_attempts()
    timeout = get_request_timeout()

    for attempt in range(1, max_attempts + 1):
        # La petición se arma en cada vuelta porque urllib consume el
        # cuerpo al enviarlo y no se puede reutilizar el objeto.
        request = build_request(
            request_url=request_url,
            method=method,
            encoded_body=encoded_body,
            authorization=authorization,
        )

        try:
            status_code, raw_body = attempt_request(
                request=request,
                timeout=timeout,
            )

        except RetryLater as error:
            if attempt >= max_attempts:
                logger.warning(
                    "Azure DevOps no respondió en %s intento(s) a "
                    "%s: %s",
                    max_attempts,
                    path,
                    error.cause.detail,
                )

                raise error.cause from error

            delay = calculate_retry_delay(
                attempt=attempt,
                retry_after=error.retry_after,
            )

            logger.info(
                "Reintento %s de %s en %.1f s para %s: %s",
                attempt + 1,
                max_attempts,
                delay,
                path,
                error.cause.detail,
            )

            time.sleep(delay)

            continue

        if status_code == HTTP_NON_AUTHORITATIVE:
            raise AzureAuthenticationError(
                "Azure DevOps devolvió una pantalla de inicio de "
                "sesión, lo que indica un token inválido o vencido.",
            )

        return decode_json_body(raw_body)

    raise AzureRequestError(
        f"No fue posible completar la consulta a {path}.",
    )


def build_request(
    *,
    request_url: str,
    method: str,
    encoded_body: bytes | None,
    authorization: str,
) -> urllib.request.Request:
    """Arma la petición HTTP con sus encabezados."""
    request = urllib.request.Request(
        request_url,
        data=encoded_body,
        method=method,
    )

    request.add_header("Authorization", authorization)
    request.add_header("Accept", "application/json")

    if encoded_body is not None:
        request.add_header("Content-Type", "application/json")

    return request


def attempt_request(
    *,
    request: urllib.request.Request,
    timeout: int,
) -> tuple[int, bytes]:
    """
    Ejecuta un intento de la consulta.

    Todas las consultas del módulo son de lectura, así que reintentar
    no tiene efectos secundarios aunque viajen como POST.

    Returns:
        El código de respuesta y el cuerpo sin procesar.

    Raises:
        RetryLater: Cuando la falla es pasajera.
        MspQaError: Cuando la falla es definitiva.
    """
    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            return (response.getcode(), response.read())

    except urllib.error.HTTPError as error:
        if error.code in RETRYABLE_STATUS_CODES:
            raise RetryLater(
                cause=translate_http_error(error),
                retry_after=read_retry_after(error),
            ) from error

        logger.warning(
            "Azure DevOps respondió con error HTTP %s.",
            error.code,
        )

        raise translate_http_error(error) from error

    except urllib.error.URLError as error:
        raise RetryLater(
            cause=AzureRequestError(
                f"No hubo respuesta de Azure DevOps: {error.reason}",
            ),
        ) from error

    except TimeoutError as error:
        raise RetryLater(
            cause=AzureRequestError(
                "La consulta a Azure DevOps excedió el tiempo de "
                "espera.",
            ),
        ) from error


def request_json(
    *,
    path: str,
    query: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Ejecuta una consulta GET contra Azure DevOps."""
    return send_request(
        path=path,
        query=query,
        method="GET",
    )


def post_json(
    *,
    path: str,
    body: dict[str, Any],
    query: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Ejecuta una consulta POST contra Azure DevOps.

    Las consultas de work items (WIQL) y la lectura por lotes exigen
    POST, porque el filtro y la lista de identificadores viajan en el
    cuerpo y no caben en la URL.
    """
    return send_request(
        path=path,
        query=query,
        method="POST",
        body=body,
    )


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
