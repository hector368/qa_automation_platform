"""Vistas HTTP del AER Test Case Generator."""

from __future__ import annotations

import json
import logging
import secrets
from pathlib import Path
from typing import Final
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from pydantic import ValidationError

from apps.aer_test_case.services.orchestrator import (
    iter_generate_document,
)
from apps.aer_test_case.exceptions import (
    AerTestCaseError,
)
from apps.aer_test_case.schemas.generation_request import (
    AerGenerationRequest,
)
from apps.aer_test_case.schemas.generation_request import (
    parse_selected_requirement_ids,
)
from apps.aer_test_case.services.orchestrator import (
    analyze_document as analyze_document_service,
)
from apps.aer_test_case.services.orchestrator import (
    generate_document,
)
from apps.aer_test_case.services.orchestrator import (
    prepare_document,
)
from apps.test_cases.exceptions import (
    TestCasesError,
)
from apps.test_cases.services.result_store import (
    load_generation_result,
)
from apps.test_cases.services.result_store import (
    save_generation_result,
)
from apps.test_cases.services.token_usage import (
    calculate_token_cost,
)


logger = logging.getLogger(__name__)

SESSION_RESULT_ID_KEY: Final[str] = (
    "aer_test_case_generation_result_id"
)

CONTENT_TYPE_XLSX: Final[str] = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet"
)

NDJSON_CONTENT_TYPE: Final[str] = (
    "application/x-ndjson; charset=utf-8"
)

@require_GET
def home(
    request: HttpRequest,
) -> HttpResponse:
    """Muestra la interfaz principal del generador AER."""
    return render(
        request,
        "aer_test_case/index.html",
        {
            "max_upload_mb": settings.MAX_UPLOAD_MB,
        },
    )


@require_POST
def analyze_document(
    request: HttpRequest,
) -> JsonResponse:
    """Analiza un PDD/FDD sin realizar llamadas a Claude."""
    uploaded_file = request.FILES.get(
        "document"
    )

    if uploaded_file is None:
        return _json_error(
            code="ERR_NO_FILE",
            message=(
                "Debes seleccionar un documento PDF o DOCX."
            ),
            status=400,
        )

    filename = (
        uploaded_file.name
        or ""
    ).strip()

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

    except AerTestCaseError as exc:
        logger.warning(
            "No fue posible analizar el documento AER: %s",
            exc,
        )

        return _json_error(
            code="ERR_REQUIREMENTS",
            message=(
                "No fue posible detectar requerimientos "
                "válidos en el documento."
            ),
            status=422,
        )

    except TestCasesError as exc:
        logger.warning(
            "No fue posible analizar el documento AER. "
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
            "Error inesperado durante el análisis AER."
        )

        return _json_error(
            code="ERR_ANALYZE",
            message=(
                "Ocurrió un error interno durante "
                "el análisis del documento."
            ),
            status=500,
        )


@require_POST
def generate_test_cases(
    request: HttpRequest,
) -> JsonResponse:
    """Genera los casos AER de los requerimientos seleccionados."""
    uploaded_file = request.FILES.get(
        "document"
    )

    if uploaded_file is None:
        return _json_error(
            code="ERR_NO_FILE",
            message=(
                "Debes seleccionar un documento PDF o DOCX."
            ),
            status=400,
        )

    try:
        generation_request = _build_generation_request(
            request
        )
    except (ValueError, ValidationError) as exc:
        logger.warning(
            "Solicitud AER inválida: %s",
            exc,
        )

        return _json_error(
            code="ERR_GENERATION_INPUT",
            message=(
                "Debes seleccionar al menos "
                "un requerimiento válido."
            ),
            status=400,
        )

    filename = (
        uploaded_file.name
        or ""
    ).strip()

    try:
        prepared_document = prepare_document(
            filename=filename,
            file_bytes=uploaded_file.read(),
            max_upload_mb=settings.MAX_UPLOAD_MB,
        )

        generation = generate_document(
            prepared_document=prepared_document,
            selected_requirement_ids=(
                generation_request
                .selected_requirement_ids
            ),
        )

        session_key = _ensure_session_key(
            request
        )

        result_id = secrets.token_urlsafe(
            32
        )

        output_filename = _build_output_filename(
            filename
        )

        payload = {
            "filename": output_filename,
            "xlsx_bytes": generation.xlsx_bytes,
        }

        save_generation_result(
            result_id=result_id,
            session_key=session_key,
            payload=payload,
            timeout_seconds=(
                settings
                .TEST_CASES_RESULT_TTL_SECONDS
            ),
        )

        request.session[
            SESSION_RESULT_ID_KEY
        ] = result_id

        request.session.modified = True

        cost = calculate_token_cost(
            usage=generation.usage,
            input_rate_per_million=(
                settings
                .CLAUDE_INPUT_USD_PER_MTOK
            ),
            output_rate_per_million=(
                settings
                .CLAUDE_OUTPUT_USD_PER_MTOK
            ),
        )

        return JsonResponse(
            {
                "ok": True,
                "code": "OK_AER_GENERATED",
                "message": (
                    "Casos AER generados correctamente."
                ),
                "result_id": result_id,
                "filename": output_filename,
                "download_url": (
                    _build_download_url(
                        result_id
                    )
                ),
                "selected_requirements": (
                    generation_request
                    .selected_requirement_ids
                ),
                "total_test_cases": (
                    generation.total_test_cases
                ),
                "usage": (
                    generation.usage.to_dict()
                ),
                "cost": cost.to_dict(),
            },
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    except AerTestCaseError as exc:
        logger.warning(
            "No fue posible generar AER: %s",
            exc,
        )

        return _json_error(
            code="ERR_AER_GENERATION",
            message=(
                "No fue posible generar los casos "
                "de prueba AER."
            ),
            status=422,
        )

    except TestCasesError as exc:
        logger.warning(
            "Claude o el documento produjeron "
            "un error. code=%s detail=%s",
            exc.code,
            exc.detail,
        )

        return _json_error(
            code=exc.code,
            message=exc.public_message,
            status=exc.http_status,
        )

    except ValueError as exc:
        logger.warning(
            "Solicitud AER inconsistente: %s",
            exc,
        )

        return _json_error(
            code="ERR_GENERATION_INPUT",
            message=str(exc),
            status=400,
        )

    except Exception:
        logger.exception(
            "Error inesperado durante la generación AER."
        )

        return _json_error(
            code="ERR_AER_GENERATION",
            message=(
                "Ocurrió un error interno durante "
                "la generación AER."
            ),
            status=500,
        )

@require_POST
def stream_generate_test_cases(
    request: HttpRequest,
) -> HttpResponse:
    """Genera casos AER transmitiendo progreso mediante NDJSON."""
    uploaded_file = request.FILES.get(
        "document"
    )

    if uploaded_file is None:
        return _json_error(
            code="ERR_NO_FILE",
            message=(
                "Debes seleccionar un documento PDF o DOCX."
            ),
            status=400,
        )

    try:
        generation_request = _build_generation_request(
            request
        )
    except (ValueError, ValidationError) as exc:
        logger.warning(
            "Solicitud AER streaming inválida: %s",
            exc,
        )

        return _json_error(
            code="ERR_GENERATION_INPUT",
            message=(
                "Debes seleccionar al menos "
                "un requerimiento válido."
            ),
            status=400,
        )

    filename = (
        uploaded_file.name
        or ""
    ).strip()

    try:
        prepared_document = prepare_document(
            filename=filename,
            file_bytes=uploaded_file.read(),
            max_upload_mb=settings.MAX_UPLOAD_MB,
        )
    except AerTestCaseError as exc:
        logger.warning(
            "No fue posible preparar AER: %s",
            exc,
        )

        return _json_error(
            code="ERR_REQUIREMENTS",
            message=(
                "No fue posible preparar los "
                "requerimientos del documento."
            ),
            status=422,
        )

    except TestCasesError as exc:
        logger.warning(
            "No fue posible preparar el documento. "
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
            "Error preparando documento AER."
        )

        return _json_error(
            code="ERR_PREPARE_GENERATION",
            message=(
                "Ocurrió un error interno al preparar "
                "el documento."
            ),
            status=500,
        )

    try:
        session_key = _ensure_session_key(
            request
        )

        result_id = secrets.token_urlsafe(
            32
        )

        request.session[
            SESSION_RESULT_ID_KEY
        ] = result_id

        request.session.save()

    except Exception:
        logger.exception(
            "No fue posible inicializar "
            "la sesión AER."
        )

        return _json_error(
            code="ERR_STREAM_SESSION",
            message=(
                "No fue posible iniciar la sesión "
                "de generación."
            ),
            status=500,
        )

    output_filename = _build_output_filename(
        filename
    )

    download_url = _build_download_url(
        result_id
    )

    def event_stream():
        try:
            events = iter_generate_document(
                prepared_document=prepared_document,
                selected_requirement_ids=(
                    generation_request
                    .selected_requirement_ids
                ),
            )

            for event in events:
                if event.get("type") != "completed":
                    yield _encode_ndjson(
                        event
                    )
                    continue

                generation = event.get(
                    "generation"
                )

                if generation is None:
                    raise RuntimeError(
                        "El evento final no contiene "
                        "una generación válida."
                    )

                save_generation_result(
                    result_id=result_id,
                    session_key=session_key,
                    payload={
                        "filename": output_filename,
                        "xlsx_bytes": (
                            generation.xlsx_bytes
                        ),
                    },
                    timeout_seconds=(
                        settings
                        .TEST_CASES_RESULT_TTL_SECONDS
                    ),
                )

                cost = calculate_token_cost(
                    usage=generation.usage,
                    input_rate_per_million=(
                        settings
                        .CLAUDE_INPUT_USD_PER_MTOK
                    ),
                    output_rate_per_million=(
                        settings
                        .CLAUDE_OUTPUT_USD_PER_MTOK
                    ),
                )

                final_event = {
                    "type": "completed",
                    "ok": True,
                    "progress": 100,
                    "result_id": result_id,
                    "download_url": download_url,
                    "filename": output_filename,
                    "selected_requirements": (
                        generation_request
                        .selected_requirement_ids
                    ),
                    "total_test_cases": (
                        generation.total_test_cases
                    ),
                    "usage": (
                        generation.usage.to_dict()
                    ),
                    "cost": cost.to_dict(),
                }

                yield _encode_ndjson(
                    final_event
                )

        except GeneratorExit:
            logger.info(
                "El cliente cerró el stream AER."
            )

            return

        except AerTestCaseError as exc:
            logger.warning(
                "Generación AER streaming falló: %s",
                exc,
            )

            yield _encode_ndjson(
                {
                    "type": "error",
                    "ok": False,
                    "code": "ERR_AER_GENERATION",
                    "message": (
                        "No fue posible generar los "
                        "casos de prueba AER."
                    ),
                }
            )

        except TestCasesError as exc:
            logger.warning(
                "Servicio compartido falló. "
                "code=%s detail=%s",
                exc.code,
                exc.detail,
            )

            yield _encode_ndjson(
                {
                    "type": "error",
                    "ok": False,
                    "code": exc.code,
                    "message": exc.public_message,
                }
            )

        except Exception:
            logger.exception(
                "Error inesperado en stream AER."
            )

            yield _encode_ndjson(
                {
                    "type": "error",
                    "ok": False,
                    "code": "ERR_STREAM_GENERATION",
                    "message": (
                        "Ocurrió un error interno durante "
                        "la generación."
                    ),
                }
            )

    response = StreamingHttpResponse(
        streaming_content=event_stream(),
        content_type=NDJSON_CONTENT_TYPE,
    )

    response["Cache-Control"] = (
        "no-cache, no-store, must-revalidate"
    )

    response["X-Accel-Buffering"] = "no"
    response["X-Content-Type-Options"] = "nosniff"

    return response

@require_GET
def download_xlsx(
    request: HttpRequest,
) -> HttpResponse:
    """Descarga el Excel AER perteneciente a la sesión."""
    result_id = (
        request.GET.get(
            "result_id"
        )
        or request.session.get(
            SESSION_RESULT_ID_KEY
        )
        or ""
    ).strip()

    session_key = (
        request.session.session_key
        or ""
    )

    payload = load_generation_result(
        result_id=result_id,
        session_key=session_key,
    )

    if payload is None:
        return HttpResponse(
            (
                "El resultado no existe, expiró o "
                "no pertenece a esta sesión."
            ),
            status=404,
            content_type="text/plain; charset=utf-8",
        )

    filename = _sanitize_download_filename(
        str(
            payload.get("filename")
            or "AER_Test_Cases.xlsx"
        )
    )

    xlsx_bytes = payload.get(
        "xlsx_bytes"
    )

    if (
        not isinstance(
            xlsx_bytes,
            (bytes, bytearray),
        )
        or not xlsx_bytes
    ):
        return HttpResponse(
            "El archivo Excel generado está vacío.",
            status=422,
            content_type="text/plain; charset=utf-8",
        )

    response = HttpResponse(
        bytes(
            xlsx_bytes
        ),
        content_type=CONTENT_TYPE_XLSX,
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; filename="{filename}"'
    )

    response[
        "X-Content-Type-Options"
    ] = "nosniff"

    response[
        "Cache-Control"
    ] = "no-store"

    return response


def _build_generation_request(
    request: HttpRequest,
) -> AerGenerationRequest:
    """Construye y valida la solicitud de generación AER."""
    selected_requirement_ids = (
        parse_selected_requirement_ids(
            request.POST.get(
                "selected_requirements"
            )
        )
    )

    return AerGenerationRequest(
        selected_requirement_ids=(
            selected_requirement_ids
        ),
    )


def _ensure_session_key(
    request: HttpRequest,
) -> str:
    """Garantiza que la petición tenga una sesión persistida."""
    if request.session.session_key is None:
        request.session.save()

    session_key = (
        request.session.session_key
        or ""
    )

    if not session_key:
        raise RuntimeError(
            "No fue posible crear una sesión."
        )

    return session_key


def _build_download_url(
    result_id: str,
) -> str:
    """Construye la URL para descargar el Excel generado."""
    query_string = urlencode(
        {
            "result_id": result_id,
        }
    )

    return (
        f"{reverse('aer_test_case:download')}"
        f"?{query_string}"
    )


def _build_output_filename(
    source_filename: str,
) -> str:
    """Construye el nombre del Excel generado."""
    source_stem = Path(
        source_filename
    ).stem.strip()

    if not source_stem:
        source_stem = "AER"

    return (
        f"{source_stem}_AER_Test_Cases.xlsx"
    )


def _sanitize_download_filename(
    filename: str,
) -> str:
    """Construye un nombre seguro para descarga."""
    clean_filename = Path(
        filename
    ).name

    clean_filename = (
        clean_filename
        .replace('"', "")
        .replace("\r", "")
        .replace("\n", "")
        .strip()
    )

    if not clean_filename:
        return "AER_Test_Cases.xlsx"

    if not clean_filename.lower().endswith(
        ".xlsx"
    ):
        clean_filename = (
            Path(clean_filename)
            .with_suffix(".xlsx")
            .name
        )

    return clean_filename

def _encode_ndjson(
    event: dict[str, object],
) -> str:
    """Serializa un evento como una línea NDJSON."""
    return (
        json.dumps(
            event,
            ensure_ascii=False,
            separators=(
                ",",
                ":",
            ),
        )
        + "\n"
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