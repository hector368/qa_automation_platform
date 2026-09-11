"""Vistas HTTP del módulo MSP QA Matrix."""

from __future__ import annotations

import json
import logging

from collections.abc import Iterator
from typing import Any, Final

from django.http import (
    HttpRequest,
    HttpResponse,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from apps.msp_qa.exceptions import MspQaError
from apps.msp_qa.services.batch import (
    iter_batch_write,
    iter_preview_rows,
    iter_project_catalog,
    update_preview_row,
)
from apps.msp_qa.services.connection_status import (
    build_connection_status,
)
from apps.msp_qa.services.orchestrator import (
    extract_block_context,
    list_available_projects,
    list_project_blocks,
    write_extraction_to_matrix,
)


logger = logging.getLogger(__name__)

NDJSON_CONTENT_TYPE: Final[str] = (
    "application/x-ndjson; charset=utf-8"
)

MAX_BATCH_ITEMS: Final[int] = 300


def build_json_response(
    payload: dict[str, object],
    status: int = 200,
) -> JsonResponse:
    """Construye una respuesta JSON conservando los acentos."""
    return JsonResponse(
        payload,
        status=status,
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


def build_json_error(
    *,
    code: str,
    message: str,
    status: int,
) -> JsonResponse:
    """Construye una respuesta JSON de error."""
    return build_json_response(
        {
            "ok": False,
            "code": code,
            "message": message,
        },
        status=status,
    )


def handle_module_error(error: MspQaError) -> JsonResponse:
    """Convierte una excepción del módulo en una respuesta JSON."""
    logger.warning(
        "Falla controlada en MSP_QA. code=%s detail=%s",
        error.code,
        error.detail,
    )

    message = error.public_message

    if error.expose_detail and error.detail:
        message = f"{message} {error.detail}"

    return build_json_error(
        code=error.code,
        message=message,
        status=error.http_status,
    )


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    """Muestra la interfaz de extracción de la matriz MSP_QA."""
    return render(
        request,
        "msp_qa/index.html",
        {
            "connection_status": build_connection_status(),
        },
    )


@require_GET
def connection_status(request: HttpRequest) -> JsonResponse:
    """Devuelve el estado de la configuración de Azure DevOps."""
    return build_json_response(build_connection_status())


@require_GET
def projects(request: HttpRequest) -> JsonResponse:
    """Devuelve los proyectos visibles con el token configurado."""
    try:
        payload = list_available_projects()

    except MspQaError as error:
        return handle_module_error(error)

    except Exception:
        logger.exception(
            "Error inesperado al consultar el catálogo de proyectos.",
        )

        return build_json_error(
            code="ERR_PROJECT_CATALOG",
            message=(
                "An internal error occurred while loading projects."
            ),
            status=500,
        )

    return build_json_response(payload)


@require_GET
def blocks(request: HttpRequest) -> JsonResponse:
    """Devuelve los bloques detectados en un proyecto."""
    project_name = (
        request.GET.get("project")
        or ""
    ).strip()

    if not project_name:
        return build_json_error(
            code="ERR_MISSING_PROJECT",
            message="Select a project first.",
            status=400,
        )

    try:
        payload = list_project_blocks(project_name)

    except MspQaError as error:
        return handle_module_error(error)

    except Exception:
        logger.exception(
            "Error inesperado al segmentar la descripción de %s.",
            project_name,
        )

        return build_json_error(
            code="ERR_BLOCK_SEGMENTATION",
            message=(
                "An internal error occurred while reading the "
                "project description."
            ),
            status=500,
        )

    return build_json_response(payload)


@require_GET
def extract(request: HttpRequest) -> JsonResponse:
    """Devuelve el JSON estructurado del bloque seleccionado."""
    project_name = (
        request.GET.get("project")
        or ""
    ).strip()

    block_code = (
        request.GET.get("block")
        or ""
    ).strip()

    if not project_name or not block_code:
        return build_json_error(
            code="ERR_MISSING_SELECTION",
            message=(
                "Select both a project and a block."
            ),
            status=400,
        )

    try:
        payload = extract_block_context(
            project_name=project_name,
            block_code=block_code,
        )

    except MspQaError as error:
        return handle_module_error(error)

    except Exception:
        logger.exception(
            "Error inesperado al extraer el bloque %s de %s.",
            block_code,
            project_name,
        )

        return build_json_error(
            code="ERR_BLOCK_EXTRACTION",
            message=(
                "An internal error occurred while extracting the "
                "block."
            ),
            status=500,
        )

    return build_json_response(payload)


@require_POST
def write_to_matrix(request: HttpRequest) -> JsonResponse:
    """Escribe en la matriz la fila del bloque seleccionado."""
    project_name = (
        request.POST.get("project")
        or ""
    ).strip()

    block_code = (
        request.POST.get("block")
        or ""
    ).strip()

    if not project_name or not block_code:
        return build_json_error(
            code="ERR_MISSING_SELECTION",
            message=(
                "Debes seleccionar el proyecto y el bloque."
            ),
            status=400,
        )

    try:
        payload = write_extraction_to_matrix(
            project_name=project_name,
            block_code=block_code,
        )

    except MspQaError as error:
        return handle_module_error(error)

    except Exception:
        logger.exception(
            "Error inesperado al escribir el bloque %s de %s.",
            block_code,
            project_name,
        )

        return build_json_error(
            code="ERR_MATRIX_WRITE",
            message=(
                "An internal error occurred while writing to the "
                "matrix."
            ),
            status=500,
        )

    return build_json_response(payload)


def encode_ndjson(event: dict[str, object]) -> str:
    """Serializa un evento como una línea NDJSON."""
    return (
        json.dumps(
            event,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n"
    )


def build_stream_response(
    events: Iterator[dict[str, Any]],
    *,
    error_code: str,
    error_message: str,
) -> StreamingHttpResponse:
    """
    Envuelve un generador de eventos en una respuesta NDJSON.

    Los errores que ocurren una vez abierto el flujo no pueden usar un
    código HTTP, así que viajan como un evento más.
    """
    def event_stream() -> Iterator[str]:
        try:
            for event in events:
                yield encode_ndjson(event)

        except GeneratorExit:
            logger.info("El cliente cerró la conexión del flujo.")
            return

        except MspQaError as error:
            logger.warning(
                "Falla controlada durante el flujo. code=%s detail=%s",
                error.code,
                error.detail,
            )

            message = error.public_message

            if error.expose_detail and error.detail:
                message = f"{message} {error.detail}"

            yield encode_ndjson(
                {
                    "type": "error",
                    "ok": False,
                    "code": error.code,
                    "message": message,
                },
            )

        except Exception:
            logger.exception("Error inesperado durante el flujo.")

            yield encode_ndjson(
                {
                    "type": "error",
                    "ok": False,
                    "code": error_code,
                    "message": error_message,
                },
            )

    response = StreamingHttpResponse(
        streaming_content=event_stream(),
        content_type=NDJSON_CONTENT_TYPE,
    )

    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["X-Accel-Buffering"] = "no"
    response["X-Content-Type-Options"] = "nosniff"

    return response


@require_GET
def catalog(request: HttpRequest) -> HttpResponse:
    """Transmite el catálogo de bloques disponibles."""
    force_refresh = request.GET.get("refresh") == "1"

    return build_stream_response(
        iter_project_catalog(force_refresh=force_refresh),
        error_code="ERR_CATALOG",
        error_message=(
            "An internal error occurred while building the catalog."
        ),
    )


def parse_batch_items(raw_items: str) -> list[dict[str, str]]:
    """
    Valida la selección recibida del navegador.

    Raises:
        ValueError: Cuando la selección no tiene el formato esperado.
    """
    try:
        payload = json.loads(raw_items or "[]")

    except json.JSONDecodeError as error:
        raise ValueError("La selección no es JSON válido.") from error

    if not isinstance(payload, list) or not payload:
        raise ValueError("La selección está vacía.")

    if len(payload) > MAX_BATCH_ITEMS:
        raise ValueError(
            f"La selección excede el máximo de {MAX_BATCH_ITEMS}.",
        )

    items: list[dict[str, str]] = []

    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError("La selección tiene entradas inválidas.")

        project_name = str(entry.get("project") or "").strip()
        block_code = str(entry.get("block") or "").strip()

        if not project_name or not block_code:
            raise ValueError(
                "Cada entrada requiere proyecto y bloque.",
            )

        items.append(
            {
                "project": project_name,
                "block": block_code,
            },
        )

    return items


@require_POST
def batch_write(request: HttpRequest) -> HttpResponse:
    """Transmite el avance de la escritura por lotes."""
    try:
        items = parse_batch_items(request.POST.get("items", ""))

    except ValueError as error:
        logger.warning("Selección inválida: %s", error)

        return build_json_error(
            code="ERR_INVALID_SELECTION",
            message="Select at least one row to write.",
            status=400,
        )

    preview_id = (request.POST.get("preview_id") or "").strip()

    return build_stream_response(
        iter_batch_write(items, preview_id=preview_id),
        error_code="ERR_BATCH_WRITE",
        error_message=(
            "An internal error occurred while writing the batch."
        ),
    )


@require_POST
def preview(request: HttpRequest) -> HttpResponse:
    """Transmite las filas extraídas, sin escribir en la matriz."""
    try:
        items = parse_batch_items(request.POST.get("items", ""))

    except ValueError as error:
        logger.warning("Selección inválida: %s", error)

        return build_json_error(
            code="ERR_INVALID_SELECTION",
            message="Select at least one row to preview.",
            status=400,
        )

    return build_stream_response(
        iter_preview_rows(items),
        error_code="ERR_PREVIEW",
        error_message=(
            "An internal error occurred while building the preview."
        ),
    )


@require_POST
def edit_preview(request: HttpRequest) -> JsonResponse:
    """Modifica un campo de la vista previa antes de escribir."""
    preview_id = (request.POST.get("preview_id") or "").strip()
    msp_id = (request.POST.get("msp_id") or "").strip()
    field = (request.POST.get("field") or "").strip()
    raw_value = request.POST.get("value", "")

    if not preview_id or not msp_id or not field:
        return build_json_error(
            code="ERR_INVALID_EDIT",
            message="The edit request is incomplete.",
            status=400,
        )

    try:
        payload = update_preview_row(
            preview_id=preview_id,
            msp_id=msp_id,
            field=field,
            raw_value=raw_value,
        )

    except MspQaError as error:
        return handle_module_error(error)

    except ValueError as error:
        return build_json_error(
            code="ERR_INVALID_VALUE",
            message=str(error),
            status=400,
        )

    except Exception:
        logger.exception(
            "Error inesperado al editar la vista previa.",
        )

        return build_json_error(
            code="ERR_EDIT_PREVIEW",
            message=(
                "An internal error occurred while saving the edit."
            ),
            status=500,
        )

    payload["ok"] = True

    return build_json_response(payload)
