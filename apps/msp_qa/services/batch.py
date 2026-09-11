"""Procesos por lotes del módulo MSP QA Matrix."""

from __future__ import annotations

import logging
import secrets
import time

from collections.abc import Iterator
from typing import Any

from django.conf import settings
from django.core.cache import cache
from pydantic import ValidationError

from apps.msp_qa.exceptions import (
    MspQaError,
    PreviewExpiredError,
)
from apps.msp_qa.schemas.msp_row import validate_msp_row
from apps.msp_qa.schemas.project_context import (
    validate_block_context,
)
from apps.msp_qa.services.block_splitter import (
    find_block,
    split_description_blocks,
)
from apps.msp_qa.services.description_parser import parse_block
from apps.msp_qa.services.matrix_writer import write_rows_to_matrix
from apps.msp_qa.services.msp_row_builder import (
    COLUMN_LABELS,
    build_msp_row,
)
from apps.msp_qa.services.orchestrator import (
    build_msp_row_id,
    get_hours_ratio,
)
from apps.msp_qa.services.project_catalog import (
    get_project_description,
    list_projects,
)


logger = logging.getLogger(__name__)

# La lectura del catálogo domina el tiempo total, así que la barra de
# progreso reserva el tramo final para la escritura.
BUILD_PROGRESS_LIMIT = 90.0

CATALOG_CACHE_KEY = "msp_qa:catalog"

PREVIEW_CACHE_PREFIX = "msp_qa:preview:"

DEFAULT_CATALOG_TTL_SECONDS = 1800

DEFAULT_PREVIEW_TTL_SECONDS = 1800


def calculate_progress(
    *,
    current: int,
    total: int,
    limit: float = 100.0,
) -> float:
    """Calcula el porcentaje de avance de un recorrido."""
    if total <= 0:
        return limit

    return round((current / total) * limit, 2)


def get_catalog_ttl() -> int:
    """Obtiene la vigencia del catálogo en caché, en segundos."""
    return int(
        getattr(
            settings,
            "MSP_QA_CATALOG_TTL_SECONDS",
            DEFAULT_CATALOG_TTL_SECONDS,
        ),
    )


def iter_project_catalog(
    *,
    force_refresh: bool = False,
) -> Iterator[dict[str, Any]]:
    """
    Recorre los proyectos y arma el catálogo de bloques disponibles.

    Cada bloque corresponde a una fila de la matriz, así que el
    catálogo resultante es la lista de filas que se pueden escribir.

    Construirlo exige leer la descripción de cada proyecto, por lo que
    el resultado se guarda en caché. Una recarga posterior lo devuelve
    de inmediato, salvo que se pida reconstruirlo.

    Args:
        force_refresh: Ignora la caché y vuelve a leer Azure DevOps.

    Yields:
        Eventos de avance y, al final, el catálogo completo.
    """
    if not force_refresh:
        cached_catalog = cache.get(CATALOG_CACHE_KEY)

        if cached_catalog:
            logger.info("Catálogo servido desde la caché.")

            yield {
                "type": "completed",
                "ok": True,
                "progress": 100,
                "from_cache": True,
                "total_items": len(cached_catalog["items"]),
                "items": cached_catalog["items"],
                "skipped": cached_catalog["skipped"],
            }

            return

    projects = list_projects()
    total_projects = len(projects)

    yield {
        "type": "started",
        "ok": True,
        "total_projects": total_projects,
        "progress": 0,
    }

    items: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for position, project in enumerate(projects, start=1):
        project_name = str(project["name"])
        block_count = 0

        try:
            description = get_project_description(project_name)
            blocks = split_description_blocks(description)

            for block in blocks:
                items.append(
                    {
                        "msp_id": build_msp_row_id(
                            project_name=project_name,
                            block_code=block.code,
                        ),
                        "project_name": project_name,
                        "block_code": block.code,
                        "block_label": block.label,
                    },
                )

            block_count = len(blocks)

        except MspQaError as error:
            skipped.append(
                {
                    "project_name": project_name,
                    "reason": error.public_message,
                },
            )

        yield {
            "type": "project_completed",
            "ok": True,
            "project_name": project_name,
            "blocks": block_count,
            "current": position,
            "total": total_projects,
            "progress": calculate_progress(
                current=position,
                total=total_projects,
            ),
        }

    logger.info(
        "Catálogo construido: %s bloque(s) en %s proyecto(s), "
        "%s proyecto(s) omitido(s).",
        len(items),
        total_projects,
        len(skipped),
    )

    cache.set(
        CATALOG_CACHE_KEY,
        {
            "items": items,
            "skipped": skipped,
        },
        timeout=get_catalog_ttl(),
    )

    yield {
        "type": "completed",
        "ok": True,
        "progress": 100,
        "from_cache": False,
        "total_items": len(items),
        "items": items,
        "skipped": skipped,
    }


def build_row_for_item(
    *,
    project_name: str,
    block_code: str,
    description: str,
) -> dict[str, Any]:
    """
    Construye la fila de la matriz para un bloque de un proyecto.

    Args:
        project_name: Nombre del proyecto en Azure DevOps.
        block_code: Código del bloque, por ejemplo "S1".
        description: Descripción completa del proyecto.

    Returns:
        Fila validada, lista para escribirse en la matriz.
    """
    blocks = split_description_blocks(description)
    selected_block = find_block(blocks, block_code)

    parsed_context = parse_block(selected_block.text)
    validated_context = validate_block_context(parsed_context)

    row = build_msp_row(
        msp_id=build_msp_row_id(
            project_name=project_name,
            block_code=selected_block.code,
        ),
        context=validated_context.model_dump(mode="json"),
        hours_ratio=get_hours_ratio(),
    )

    return validate_msp_row(row).model_dump(mode="json")


def iter_build_rows(
    items: list[dict[str, str]],
) -> Iterator[dict[str, Any]]:
    """
    Construye la fila de cada bloque seleccionado.

    Un bloque que falle no detiene a los demás. El último evento
    entrega las filas construidas y la lista de fallas.

    Yields:
        Eventos de avance y, al final, un evento "rows_ready".
    """
    total_items = len(items)
    descriptions: dict[str, str] = {}

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for position, item in enumerate(items, start=1):
        project_name = str(item.get("project") or "").strip()
        block_code = str(item.get("block") or "").strip()

        item_ok = True
        reason = ""

        try:
            if project_name not in descriptions:
                descriptions[project_name] = (
                    get_project_description(project_name)
                )

            rows.append(
                build_row_for_item(
                    project_name=project_name,
                    block_code=block_code,
                    description=descriptions[project_name],
                ),
            )

        except MspQaError as error:
            item_ok = False
            reason = error.public_message

            failures.append(
                {
                    "project_name": project_name,
                    "block_code": block_code,
                    "reason": reason,
                },
            )

        yield {
            "type": "item_completed",
            "ok": item_ok,
            "project_name": project_name,
            "block_code": block_code,
            "reason": reason,
            "current": position,
            "total": total_items,
            "progress": calculate_progress(
                current=position,
                total=total_items,
                limit=BUILD_PROGRESS_LIMIT,
            ),
        }

    yield {
        "type": "rows_ready",
        "rows": rows,
        "failures": failures,
    }


def get_preview_ttl() -> int:
    """Obtiene la vigencia de una vista previa, en segundos."""
    return int(
        getattr(
            settings,
            "MSP_QA_PREVIEW_TTL_SECONDS",
            DEFAULT_PREVIEW_TTL_SECONDS,
        ),
    )


def collect_rows(
    items: list[dict[str, str]],
) -> Iterator[dict[str, Any]]:
    """
    Recorre la construcción de filas y guarda el resultado en caché.

    Yields:
        Eventos de avance y, al final, un evento "preview_ready".
    """
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for event in iter_build_rows(items):
        if event["type"] == "rows_ready":
            rows = event["rows"]
            failures = event["failures"]
            continue

        yield event

    preview_id = secrets.token_urlsafe(24)

    cache.set(
        f"{PREVIEW_CACHE_PREFIX}{preview_id}",
        {
            "items": items,
            "rows": rows,
            "edits": {},
        },
        timeout=get_preview_ttl(),
    )

    yield {
        "type": "preview_ready",
        "preview_id": preview_id,
        "rows": rows,
        "failures": failures,
    }


def iter_preview_rows(
    items: list[dict[str, str]],
) -> Iterator[dict[str, Any]]:
    """
    Extrae las filas seleccionadas sin escribir en la matriz.

    Yields:
        Eventos de avance y, al final, las filas listas para revisar.
    """
    started_at = time.perf_counter()

    yield {
        "type": "started",
        "ok": True,
        "total": len(items),
        "progress": 0,
    }

    for event in collect_rows(items):
        if event["type"] != "preview_ready":
            yield event
            continue

        yield {
            "type": "completed",
            "ok": True,
            "progress": 100,
            "preview_id": event["preview_id"],
            "column_labels": dict(COLUMN_LABELS),
            "rows": event["rows"],
            "failures": event["failures"],
            "elapsed_seconds": round(
                time.perf_counter() - started_at,
                2,
            ),
        }


def load_preview_rows(
    preview_id: str,
) -> list[dict[str, Any]] | None:
    """Recupera las filas de una vista previa vigente."""
    if not preview_id:
        return None

    cached = cache.get(f"{PREVIEW_CACHE_PREFIX}{preview_id}")

    if not cached:
        return None

    return cached.get("rows")


def iter_batch_write(
    items: list[dict[str, str]],
    *,
    preview_id: str = "",
) -> Iterator[dict[str, Any]]:
    """
    Escribe en la matriz las filas seleccionadas.

    Si existe una vista previa vigente se reutilizan sus filas, para
    no volver a consultar Azure DevOps. Si expiró, se reconstruyen.

    Args:
        items: Pares de proyecto y bloque a procesar.
        preview_id: Identificador de la vista previa, si la hubo.

    Yields:
        Eventos de avance y, al final, el resultado de la escritura.
    """
    started_at = time.perf_counter()

    yield {
        "type": "started",
        "ok": True,
        "total": len(items),
        "progress": 0,
    }

    rows = load_preview_rows(preview_id)
    failures: list[dict[str, str]] = []

    if rows is None:
        logger.info(
            "La vista previa expiró: las filas se reconstruyen.",
        )

        for event in collect_rows(items):
            if event["type"] != "preview_ready":
                yield event
                continue

            rows = event["rows"]
            failures = event["failures"]

    rows = rows or []

    if not rows:
        yield {
            "type": "completed",
            "ok": True,
            "progress": 100,
            "result": {
                "ok": True,
                "inserted": 0,
                "updated": 0,
                "updated_cells": 0,
                "rows": [],
                "duplicate_ids": [],
            },
            "failures": failures,
            "elapsed_seconds": round(
                time.perf_counter() - started_at,
                2,
            ),
        }

        return

    yield {
        "type": "writing",
        "ok": True,
        "total_rows": len(rows),
        "progress": BUILD_PROGRESS_LIMIT,
    }

    write_result = write_rows_to_matrix(rows)

    yield {
        "type": "completed",
        "ok": True,
        "progress": 100,
        "result": write_result,
        "failures": failures,
        "elapsed_seconds": round(
            time.perf_counter() - started_at,
            2,
        ),
    }


def update_preview_row(
    *,
    preview_id: str,
    msp_id: str,
    field: str,
    raw_value: str,
) -> dict[str, Any]:
    """
    Cambia el valor de un campo dentro de una vista previa.

    El valor pasa por el esquema de la fila, de modo que un campo
    numérico no puede quedarse con texto libre. Un valor vacío borra
    el dato y deja la celda intacta al escribir.

    Args:
        preview_id: Identificador de la vista previa.
        msp_id: Identificador de la fila a modificar.
        field: Campo de la matriz a cambiar.
        raw_value: Valor capturado por el usuario.

    Returns:
        La fila actualizada y los campos editados hasta ahora.

    Raises:
        PreviewExpiredError: Cuando la vista previa ya no existe.
        ValueError: Cuando el campo o el valor no son válidos.
    """
    cache_key = f"{PREVIEW_CACHE_PREFIX}{preview_id}"
    cached = cache.get(cache_key)

    if not cached:
        raise PreviewExpiredError(
            "La vista previa ya no está en caché.",
        )

    if field not in COLUMN_LABELS:
        raise ValueError(f"El campo '{field}' no existe.")

    target_row = None

    for row in cached["rows"]:
        if str(row.get("msp_id")) == msp_id:
            target_row = row
            break

    if target_row is None:
        raise ValueError(
            f"La fila '{msp_id}' no está en la vista previa.",
        )

    clean_value = (raw_value or "").strip()

    candidate = dict(target_row)
    candidate[field] = clean_value or None

    try:
        validated = validate_msp_row(candidate)

    except ValidationError as error:
        first_error = error.errors()[0]

        raise ValueError(
            f"'{COLUMN_LABELS[field]}' does not accept that value: "
            f"{first_error.get('msg')}",
        ) from error

    updated_row = validated.model_dump(mode="json")
    target_row.update(updated_row)

    edits = cached.setdefault("edits", {})
    row_edits = edits.setdefault(msp_id, [])

    if field not in row_edits:
        row_edits.append(field)

    cache.set(cache_key, cached, timeout=get_preview_ttl())

    logger.info(
        "Vista previa editada: fila %s, campo %s.",
        msp_id,
        field,
    )

    return {
        "row": updated_row,
        "edited_fields": row_edits,
    }
