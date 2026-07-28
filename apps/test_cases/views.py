"""Vistas HTTP del generador de casos de prueba."""

from __future__ import annotations

import json
import logging
import secrets
from pathlib import Path
from typing import Final
from urllib.parse import urlencode

from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
    StreamingHttpResponse,
)
from django.urls import reverse
from django.views.decorators.http import (
    require_GET,
    require_POST,
)
from pydantic import ValidationError
from django.shortcuts import render
from apps.test_cases.exceptions import TestCasesError
from apps.test_cases.schemas.request_schema import (
    GenerationRequest,
    parse_selected_requirements,
)
from apps.test_cases.services.orchestrator import (
    analyze_document as analyze_document_service,
)
from apps.test_cases.services.orchestrator import (
    generate_document as generate_document_service,
)
from apps.test_cases.services.orchestrator import (
    iter_generate_prepared_document,
    prepare_generation_document,
)
from apps.test_cases.services.result_store import (
    load_generation_result,
    save_generation_result,
)


logger = logging.getLogger(__name__)


SESSION_RESULT_ID_KEY: Final[str] = (
    "test_cases_generation_result_id"
)

SESSION_INITIALIZED_KEY: Final[str] = (
    "test_cases_stream_initialized"
)

CONTENT_TYPE_CSV: Final[str] = (
    "text/csv; charset=utf-8"
)

NDJSON_CONTENT_TYPE: Final[str] = (
    "application/x-ndjson; charset=utf-8"
)


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    """Muestra la interfaz del generador de casos de prueba."""
    return render(
        request,
        "test_cases/index.html",
        {
            "max_upload_mb": settings.MAX_UPLOAD_MB,
        },
    )


@require_POST
def analyze_document(
    request: HttpRequest,
) -> JsonResponse:
    """
    Analiza un documento sin realizar llamadas a Claude.

    El endpoint valida el archivo, extrae el texto, identifica el
    proyecto y devuelve los requerimientos detectados.
    """
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
            "Error inesperado durante el análisis."
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
    """
    Genera casos de prueba mediante una respuesta JSON convencional.

    El resultado completo se guarda temporalmente en caché. La sesión
    solamente conserva el identificador del resultado.
    """
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
            "Solicitud de generación inválida: %s",
            exc,
        )

        return _json_error(
            code="ERR_GENERATION_INPUT",
            message=(
                "Revisa Assigned To y la selección "
                "de requerimientos."
            ),
            status=400,
        )

    filename = (
        uploaded_file.name
        or ""
    ).strip()

    try:
        payload = generate_document_service(
            filename=filename,
            file_bytes=uploaded_file.read(),
            max_upload_mb=settings.MAX_UPLOAD_MB,
            generation_request=generation_request,
        )

        session_key = _ensure_session_key(
            request
        )

        result_id = secrets.token_urlsafe(
            32
        )

        save_generation_result(
            result_id=result_id,
            session_key=session_key,
            payload=payload,
            timeout_seconds=(
                settings.TEST_CASES_RESULT_TTL_SECONDS
            ),
        )

        request.session[
            SESSION_RESULT_ID_KEY
        ] = result_id

        request.session.modified = True

        download_url = _build_download_url(
            result_id
        )

        return JsonResponse(
            {
                "ok": True,
                "code": "OK_GENERATED",
                "message": (
                    "Casos de prueba generados correctamente."
                ),
                "result_id": result_id,
                "download_url": download_url,
                "filename": payload["filename"],
                "usage": payload["usage"],
                "cost": payload["cost"],
                "elapsed": payload["elapsed"],
                "stats": payload["stats"],
                "selected_requirements": (
                    payload["selected_requirements"]
                ),
                "missing_selected": (
                    payload["missing_selected"]
                ),
            },
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    except TestCasesError as exc:
        logger.warning(
            "No fue posible generar los casos. "
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
            "Error inesperado durante la generación."
        )

        return _json_error(
            code="ERR_GENERATION",
            message=(
                "Ocurrió un error interno durante "
                "la generación de casos de prueba."
            ),
            status=500,
        )


@require_POST
def stream_generate_test_cases(
    request: HttpRequest,
) -> HttpResponse:
    """
    Genera casos y transmite el progreso mediante NDJSON.

    Los errores de archivo, formulario y segmentación se devuelven antes
    de abrir el stream. Los errores que ocurran durante las llamadas a
    Claude se transmiten como eventos NDJSON.
    """
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
            "Solicitud de streaming inválida: %s",
            exc,
        )

        return _json_error(
            code="ERR_GENERATION_INPUT",
            message=(
                "Revisa Assigned To y la selección "
                "de requerimientos."
            ),
            status=400,
        )

    filename = (
        uploaded_file.name
        or ""
    ).strip()

    try:
        prepared = prepare_generation_document(
            filename=filename,
            file_bytes=uploaded_file.read(),
            max_upload_mb=settings.MAX_UPLOAD_MB,
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
            "Error inesperado preparando el documento."
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
            "No fue posible inicializar la sesión del stream."
        )

        return _json_error(
            code="ERR_STREAM_SESSION",
            message=(
                "No fue posible iniciar la sesión "
                "de generación."
            ),
            status=500,
        )

    download_url = _build_download_url(
        result_id
    )

    def event_stream():
        try:
            events = iter_generate_prepared_document(
                prepared=prepared,
                generation_request=generation_request,
            )

            for event in events:
                if event.get("type") != "completed":
                    yield _encode_ndjson(
                        event
                    )
                    continue

                result = event.get(
                    "result"
                )

                if not isinstance(result, dict):
                    raise RuntimeError(
                        "El evento final no contiene "
                        "un resultado válido."
                    )

                save_generation_result(
                    result_id=result_id,
                    session_key=session_key,
                    payload=result,
                    timeout_seconds=(
                        settings
                        .TEST_CASES_RESULT_TTL_SECONDS
                    ),
                )

                final_event = {
                    "type": "completed",
                    "ok": True,
                    "progress": 100,
                    "result_id": result_id,
                    "download_url": download_url,
                    "filename": result["filename"],
                    "usage": result["usage"],
                    "cost": result["cost"],
                    "elapsed": result["elapsed"],
                    "stats": result["stats"],
                    "selected_requirements": (
                        result[
                            "selected_requirements"
                        ]
                    ),
                    "missing_selected": (
                        result[
                            "missing_selected"
                        ]
                    ),
                }

                yield _encode_ndjson(
                    final_event
                )

        except GeneratorExit:
            logger.info(
                "El cliente cerró la conexión "
                "de streaming."
            )

            return

        except TestCasesError as exc:
            logger.warning(
                "La generación en streaming falló. "
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
                "Error inesperado durante "
                "la generación en streaming."
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
def download_csv(
    request: HttpRequest,
) -> HttpResponse:
    """
    Descarga un CSV temporal perteneciente a la sesión actual.

    El resultado puede obtenerse por query string o mediante el último
    identificador guardado en la sesión.
    """
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
                "El resultado no existe, expiró o no "
                "pertenece a esta sesión."
            ),
            status=404,
            content_type="text/plain; charset=utf-8",
        )

    filename = _sanitize_download_filename(
        str(
            payload.get("filename")
            or "test_cases_TC.csv"
        )
    )

    csv_output = str(
        payload.get("csv_out")
        or ""
    )

    if not csv_output.strip():
        return HttpResponse(
            "El CSV generado está vacío.",
            status=422,
            content_type="text/plain; charset=utf-8",
        )

    response = HttpResponse(
        csv_output.encode(
            "utf-8-sig"
        ),
        content_type=CONTENT_TYPE_CSV,
    )

    response[
        "Content-Disposition"
    ] = f'attachment; filename="{filename}"'

    response[
        "X-Content-Type-Options"
    ] = "nosniff"

    response[
        "Cache-Control"
    ] = "no-store"

    return response


def _build_generation_request(
    request: HttpRequest,
) -> GenerationRequest:
    """
    Construye y valida la solicitud de generación.

    Returns:
        Solicitud validada mediante Pydantic.

    Raises:
        ValueError: Cuando la selección tiene un formato inválido.
        ValidationError: Cuando Pydantic rechaza los datos.
    """
    selected_requirements = (
        parse_selected_requirements(
            request.POST.get(
                "selected_requirements"
            )
        )
    )

    return GenerationRequest(
        assigned_to=request.POST.get(
            "assigned_to",
            "",
        ),
        selected_requirements=(
            selected_requirements
        ),
    )


def _ensure_session_key(
    request: HttpRequest,
) -> str:
    """
    Garantiza que exista una sesión persistida.

    La sesión se guarda antes de iniciar el streaming porque después de
    enviar los encabezados HTTP ya no es seguro modificarla.
    """
    request.session[
        SESSION_INITIALIZED_KEY
    ] = True

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
    """Construye la URL relativa para descargar un resultado."""
    query_string = urlencode(
        {
            "result_id": result_id,
        }
    )

    return (
        f"{reverse('test_cases:download')}"
        f"?{query_string}"
    )


def _sanitize_download_filename(
    filename: str,
) -> str:
    """
    Evita rutas y caracteres inseguros en Content-Disposition.

    Returns:
        Nombre de archivo seguro terminado en .csv.
    """
    clean_filename = Path(
        filename
    ).name

    clean_filename = clean_filename.replace(
        '"',
        "",
    ).replace(
        "\r",
        "",
    ).replace(
        "\n",
        "",
    ).strip()

    if not clean_filename:
        return "test_cases_TC.csv"

    if not clean_filename.lower().endswith(
        ".csv"
    ):
        clean_filename = (
            f"{clean_filename}.csv"
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