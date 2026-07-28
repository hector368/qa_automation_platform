"""Vistas HTTP del generador PEP."""

from __future__ import annotations

import json
import logging
import secrets
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlencode

from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import (
    require_GET,
    require_POST,
)

from apps.pep.exceptions import (
    PepAnalysisNotFoundError,
    PepError,
    PepRequestError,
    PepResultNotFoundError,
)
from apps.pep.services.orchestrator import (
    analyze_pep_documents,
    generate_pep_from_analysis,
)
from apps.pep.services.result_store import (
    load_pep_analysis,
    load_pep_result,
    save_pep_analysis,
    save_pep_result,
)


LOGGER = logging.getLogger(__name__)

SESSION_ANALYSIS_ID_KEY: Final[str] = (
    "pep_analysis_id"
)

SESSION_RESULT_ID_KEY: Final[str] = (
    "pep_result_id"
)

DOCX_CONTENT_TYPE: Final[str] = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)


@require_GET
def home(
    request: HttpRequest,
) -> HttpResponse:
    """Muestra la interfaz principal del generador PEP."""
    return render(
        request,
        "pep/index.html",
        {
            "max_upload_mb": settings.MAX_UPLOAD_MB,
        },
    )


@require_POST
def analyze_documents(
    request: HttpRequest,
) -> JsonResponse:
    """Analiza los documentos PAP y PDD/FDD."""
    try:
        pap_upload = request.FILES.get(
            "pap_document"
        )

        pdd_upload = request.FILES.get(
            "pdd_document"
        )

        if pap_upload is None:
            raise PepRequestError(
                "No se recibió el documento PAP."
            )

        if pdd_upload is None:
            raise PepRequestError(
                "No se recibió el documento PDD/FDD."
            )

        pap_bytes = _read_upload(
            pap_upload
        )

        pdd_bytes = _read_upload(
            pdd_upload
        )

        analysis_payload = analyze_pep_documents(
            pap_filename=pap_upload.name,
            pap_bytes=pap_bytes,
            pdd_filename=pdd_upload.name,
            pdd_bytes=pdd_bytes,
            max_upload_mb=settings.MAX_UPLOAD_MB,
        )

        session_key = _ensure_session_key(
            request
        )

        analysis_id = secrets.token_urlsafe(
            24
        )

        save_pep_analysis(
            analysis_id=analysis_id,
            session_key=session_key,
            payload=analysis_payload,
            timeout_seconds=(
                settings.PEP_ANALYSIS_TTL_SECONDS
            ),
        )

        request.session[
            SESSION_ANALYSIS_ID_KEY
        ] = analysis_id

        response_payload = {
            "ok": True,
            "code": "OK_PEP_ANALYZED",
            "analysis_id": analysis_id,
            **analysis_payload,
        }

        return JsonResponse(
            response_payload
        )

    except PepError as exc:
        LOGGER.warning(
            "No fue posible analizar el PEP. "
            "code=%s detail=%s",
            exc.code,
            exc.detail,
        )

        return _json_error(
            exc
        )

    except Exception:
        LOGGER.exception(
            "Error inesperado durante el análisis PEP."
        )

        return _unexpected_error()


@require_POST
def generate_pep(
    request: HttpRequest,
) -> JsonResponse:
    """Genera un DOCX desde un análisis temporal."""
    try:
        request_payload = _read_request_payload(
            request
        )

        analysis_id = str(
            request_payload.get(
                "analysis_id",
                "",
            )
        ).strip()

        if not analysis_id:
            analysis_id = str(
                request.session.get(
                    SESSION_ANALYSIS_ID_KEY,
                    "",
                )
            ).strip()

        if not analysis_id:
            raise PepRequestError(
                "No se proporcionó analysis_id."
            )

        session_key = _ensure_session_key(
            request
        )

        analysis_payload = load_pep_analysis(
            analysis_id=analysis_id,
            session_key=session_key,
        )

        if analysis_payload is None:
            raise PepAnalysisNotFoundError()

        generation_result = (
            generate_pep_from_analysis(
                analysis_payload
            )
        )

        result_id = secrets.token_urlsafe(
            24
        )

        save_pep_result(
            result_id=result_id,
            session_key=session_key,
            filename=generation_result[
                "filename"
            ],
            content=generation_result[
                "content"
            ],
            timeout_seconds=(
                settings.PEP_RESULT_TTL_SECONDS
            ),
        )

        request.session[
            SESSION_RESULT_ID_KEY
        ] = result_id

        return JsonResponse(
            {
                "ok": True,
                "code": "OK_PEP_GENERATED",
                "result_id": result_id,
                "filename": generation_result[
                    "filename"
                ],
                "download_url": (
                    _build_download_url(
                        result_id
                    )
                ),
                "context": generation_result[
                    "context"
                ],
            }
        )

    except PepError as exc:
        LOGGER.warning(
            "No fue posible generar el PEP. "
            "code=%s detail=%s",
            exc.code,
            exc.detail,
        )

        return _json_error(
            exc
        )

    except Exception:
        LOGGER.exception(
            "Error inesperado durante la generación PEP."
        )

        return _unexpected_error()


@require_GET
def download_pep(
    request: HttpRequest,
) -> HttpResponse:
    """Descarga un DOCX generado por la misma sesión."""
    try:
        result_id = str(
            request.GET.get(
                "result_id",
                "",
            )
        ).strip()

        if not result_id:
            result_id = str(
                request.session.get(
                    SESSION_RESULT_ID_KEY,
                    "",
                )
            ).strip()

        if not result_id:
            raise PepResultNotFoundError()

        session_key = _ensure_session_key(
            request
        )

        stored_result = load_pep_result(
            result_id=result_id,
            session_key=session_key,
        )

        if stored_result is None:
            raise PepResultNotFoundError()

        filename = _sanitize_download_filename(
            stored_result["filename"]
        )

        response = HttpResponse(
            stored_result["content"],
            content_type=DOCX_CONTENT_TYPE,
        )

        response[
            "Content-Disposition"
        ] = (
            f'attachment; filename="{filename}"'
        )

        response[
            "Cache-Control"
        ] = "no-store"

        return response

    except PepError as exc:
        LOGGER.warning(
            "No fue posible descargar el PEP. "
            "code=%s detail=%s",
            exc.code,
            exc.detail,
        )

        return _json_error(
            exc
        )

    except Exception:
        LOGGER.exception(
            "Error inesperado al descargar el PEP."
        )

        return _unexpected_error()


def _read_upload(
    uploaded_file: Any,
) -> bytes:
    """Lee un archivo de carga de forma controlada."""
    try:
        file_bytes = uploaded_file.read()
    except OSError as exc:
        raise PepRequestError(
            "No fue posible leer el archivo cargado."
        ) from exc

    if not isinstance(file_bytes, bytes):
        raise PepRequestError(
            "El archivo cargado no produjo datos binarios."
        )

    return file_bytes


def _read_request_payload(
    request: HttpRequest,
) -> dict[str, Any]:
    """Lee datos POST tradicionales o JSON."""
    content_type = (
        request.content_type
        or ""
    ).lower()

    if "application/json" not in content_type:
        return request.POST.dict()

    try:
        payload = json.loads(
            request.body.decode("utf-8")
        )
    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as exc:
        raise PepRequestError(
            "El cuerpo JSON de la solicitud no es válido."
        ) from exc

    if not isinstance(payload, dict):
        raise PepRequestError(
            "El cuerpo JSON debe ser un objeto."
        )

    return payload


def _ensure_session_key(
    request: HttpRequest,
) -> str:
    """Garantiza que exista una sesión persistente."""
    session_key = (
        request.session.session_key
    )

    if session_key:
        return session_key

    request.session.create()

    session_key = (
        request.session.session_key
    )

    if not session_key:
        raise PepRequestError(
            "No fue posible inicializar la sesión."
        )

    return session_key


def _build_download_url(
    result_id: str,
) -> str:
    """Construye la ruta de descarga temporal."""
    query_string = urlencode(
        {
            "result_id": result_id,
        }
    )

    return (
        f"{reverse('pep:download')}"
        f"?{query_string}"
    )


def _sanitize_download_filename(
    filename: str,
) -> str:
    """Normaliza el nombre enviado en Content-Disposition."""
    safe_filename = Path(
        filename
    ).name

    safe_filename = (
        safe_filename
        .replace("\r", "")
        .replace("\n", "")
        .replace('"', "")
    )

    if not safe_filename.lower().endswith(
        ".docx"
    ):
        safe_filename = (
            f"{safe_filename}.docx"
        )

    return (
        safe_filename
        or "PROYECTO_PEP.docx"
    )


def _json_error(
    error: PepError,
) -> JsonResponse:
    """Convierte un error controlado en JSON público."""
    return JsonResponse(
        {
            "ok": False,
            "code": error.code,
            "message": error.public_message,
        },
        status=error.http_status,
    )


def _unexpected_error() -> JsonResponse:
    """Devuelve un error genérico sin filtrar detalles."""
    return JsonResponse(
        {
            "ok": False,
            "code": "ERR_PEP_INTERNAL",
            "message": (
                "Ocurrió un error inesperado "
                "durante el procesamiento del PEP."
            ),
        },
        status=500,
    )