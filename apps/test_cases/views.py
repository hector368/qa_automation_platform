"""Vistas HTTP del generador de casos de prueba."""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.test_cases.exceptions import TestCasesError
from apps.test_cases.services.orchestrator import (
    analyze_document as analyze_document_service,
)


logger = logging.getLogger(__name__)


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    """Comprueba que la aplicación esté disponible."""
    return HttpResponse("Test Case Generator ready")


@require_POST
def analyze_document(
    request: HttpRequest,
) -> JsonResponse:
    """
    Analiza un documento sin llamar a Claude.

    Args:
        request: Petición multipart con el campo document.

    Returns:
        Project ID y requerimientos detectados.
    """
    uploaded_file = request.FILES.get("document")

    if uploaded_file is None:
        return _json_error(
            code="ERR_NO_FILE",
            message="Debes seleccionar un documento PDF o DOCX.",
            status=400,
        )

    filename = (uploaded_file.name or "").strip()

    try:
        payload = analyze_document_service(
            filename=filename,
            file_bytes=uploaded_file.read(),
            max_upload_mb=settings.MAX_UPLOAD_MB,
        )

        return JsonResponse(
            payload,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    except TestCasesError as exc:
        logger.warning(
            "No fue posible analizar el documento. "
            "code=%s detail=%s",
            exc.code,
            exc.detail,
        )

        return _json_error(
            code=exc.code,
            message=exc.public_message,
            status=exc.http_status,
        )

    except Exception:
        logger.exception(
            "Ocurrió un error inesperado durante el análisis."
        )

        return _json_error(
            code="ERR_ANALYZE",
            message=(
                "Ocurrió un error interno durante el análisis "
                "del documento."
            ),
            status=500,
        )


def _json_error(
    *,
    code: str,
    message: str,
    status: int,
) -> JsonResponse:
    """Construye una respuesta JSON de error segura."""
    return JsonResponse(
        {
            "ok": False,
            "code": code,
            "message": message,
        },
        status=status,
        json_dumps_params={
            "ensure_ascii": False,
        },
    )