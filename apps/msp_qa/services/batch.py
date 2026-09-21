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
from apps.msp_qa.services.matrix_writer import (
    inspect_matrix_rows,
    write_rows_to_matrix,
)
from apps.msp_qa.services.msp_row_builder import build_msp_row
from apps.msp_qa.services.orchestrator import (
    build_column_labels,
    build_msp_row_id,
    get_hours_ratio,
)
from apps.msp_qa.services.bug_counter import (
    StageBugResult,
    count_stage_bugs,
)
from apps.msp_qa.services.project_catalog import (
    get_project_description,
    list_projects,
)
from apps.msp_qa.services.release_reader import (
    StageReleaseResult,
    read_stage_release,
)
from apps.msp_qa.services.test_case_counter import (
    StageCountResult,
    count_stage_test_cases,
)
from apps.msp_qa.statuses import STATUS_FIELD, STATUS_OPTIONS
from apps.msp_qa.technologies import (
    TECHNOLOGY_FIELD,
    TECHNOLOGY_OPTIONS,
)


logger = logging.getLogger(__name__)

# La lectura del catálogo domina el tiempo total, así que la barra de
# progreso reserva el tramo final para la escritura.
BUILD_PROGRESS_LIMIT = 90.0

CATALOG_CACHE_KEY = "msp_qa:catalog"

PREVIEW_CACHE_PREFIX = "msp_qa:preview:"

DEFAULT_CATALOG_TTL_SECONDS = 1800

DEFAULT_PREVIEW_TTL_SECONDS = 1800


def build_choice_fields() -> dict[str, list[str]]:
    """
    Reúne las columnas que se capturan con una lista cerrada.

    La interfaz dibuja un combobox por cada entrada, así que agregar
    una columna de catálogo no exige tocar el navegador.
    """
    return {
        STATUS_FIELD: list(STATUS_OPTIONS),
        TECHNOLOGY_FIELD: list(TECHNOLOGY_OPTIONS),
    }


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


def count_stage_safely(
    *,
    project_name: str,
    block_code: str,
) -> tuple[StageCountResult | None, str]:
    """
    Cuenta los casos de prueba sin dejar que una falla tumbe la fila.

    Los casos de prueba son un dato adicional: si el token no alcanza
    para leer work items, la fila igual sirve con lo que trae la
    descripción. La razón viaja aparte para poder reportarla.

    Returns:
        El resultado del conteo, y el motivo cuando no se pudo.
    """
    try:
        return (
            count_stage_test_cases(
                project_name=project_name,
                block_code=block_code,
            ),
            "",
        )

    except MspQaError as error:
        logger.warning(
            "No fue posible contar casos de prueba de %s (%s): %s",
            project_name,
            block_code,
            error.detail,
        )

        return (None, error.public_message)


def count_bugs_safely(
    *,
    project_name: str,
    block_code: str,
) -> tuple[StageBugResult | None, str]:
    """
    Cuenta los defectos sin dejar que una falla tumbe la fila.

    Returns:
        El resultado del conteo, y el motivo cuando no se pudo.
    """
    try:
        return (
            count_stage_bugs(
                project_name=project_name,
                block_code=block_code,
            ),
            "",
        )

    except MspQaError as error:
        logger.warning(
            "No fue posible contar defectos de %s (%s): %s",
            project_name,
            block_code,
            error.detail,
        )

        return (None, error.public_message)


def read_release_safely(
    *,
    project_name: str,
    block_code: str,
) -> tuple[StageReleaseResult | None, str]:
    """
    Lee la liberación sin dejar que una falla tumbe la fila.

    Returns:
        El resultado de la lectura, y el motivo cuando no se pudo.
    """
    try:
        return (
            read_stage_release(
                project_name=project_name,
                block_code=block_code,
            ),
            "",
        )

    except MspQaError as error:
        logger.warning(
            "No fue posible leer la liberación de %s (%s): %s",
            project_name,
            block_code,
            error.detail,
        )

        return (None, error.public_message)


def build_stage_note(
    *,
    msp_id: str,
    stage: StageCountResult | None,
    reason: str,
) -> dict[str, str] | None:
    """Arma el aviso cuando el conteo por etapa no es confiable."""
    if reason:
        return {
            "msp_id": msp_id,
            "reason": reason,
        }

    if stage is None:
        return None

    if not stage.resolved:
        available = ", ".join(stage.available_stages) or "ninguna"

        return {
            "msp_id": msp_id,
            "reason": (
                "No matching iteration in Azure DevOps. "
                f"Available: {available}."
            ),
        }

    if stage.extra_stages > 0:
        return {
            "msp_id": msp_id,
            "reason": (
                f"Counted only {stage.iteration_name}, but the "
                f"project has {stage.extra_stages} more stage(s) "
                "with no row of their own."
            ),
        }

    return None


def build_defect_note(
    *,
    msp_id: str,
    bugs: StageBugResult | None,
    reason: str,
) -> dict[str, str] | None:
    """Arma el aviso cuando el tipo de defecto no es concluyente."""
    if reason:
        return {
            "msp_id": msp_id,
            "reason": reason,
        }

    if bugs is None or bugs.counts is None:
        return None

    if not bugs.root_cause_field:
        return {
            "msp_id": msp_id,
            "reason": (
                "The Bug work item has no root cause field, so TIPO "
                "was left untouched."
            ),
        }

    if bugs.counts.tied_types:
        tied = ", ".join(bugs.counts.tied_types)

        return {
            "msp_id": msp_id,
            "reason": (
                f"TIPO was a tie between {tied}; the most recent "
                "defect decided it."
            ),
        }

    if bugs.counts.missing_root_cause > 0:
        return {
            "msp_id": msp_id,
            "reason": (
                f"{bugs.counts.missing_root_cause} defect(s) have no "
                "root cause and did not count toward TIPO."
            ),
        }

    return None


def build_release_note(
    *,
    msp_id: str,
    release: StageReleaseResult | None,
    reason: str,
) -> dict[str, str] | None:
    """Arma el aviso cuando la liberación no aporta datos."""
    if reason:
        return {
            "msp_id": msp_id,
            "reason": reason,
        }

    if release is None or release.info is None:
        return None

    info = release.info

    if info.matches == 0:
        return {
            "msp_id": msp_id,
            "reason": (
                "No 'Liberación Testing' requirement in this "
                "iteration, so ESTATUS and FECHA LIBERACIÓN were "
                "left untouched."
            ),
        }

    if info.matches > 1:
        return {
            "msp_id": msp_id,
            "reason": (
                f"Found {info.matches} 'Liberación Testing' "
                "requirements; used the most recently changed."
            ),
        }

    if not info.date_field:
        return {
            "msp_id": msp_id,
            "reason": (
                "The Requirement work item has no release date "
                "field, so FECHA LIBERACIÓN was left untouched."
            ),
        }

    return None


def build_row_for_item(
    *,
    project_name: str,
    block_code: str,
    description: str,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """
    Construye la fila de la matriz para un bloque de un proyecto.

    Args:
        project_name: Nombre del proyecto en Azure DevOps.
        block_code: Código del bloque, por ejemplo "S1".
        description: Descripción completa del proyecto.

    Returns:
        La fila validada y los avisos sobre sus conteos.
    """
    blocks = split_description_blocks(description)
    selected_block = find_block(blocks, block_code)

    parsed_context = parse_block(selected_block.text)
    validated_context = validate_block_context(parsed_context)

    msp_id = build_msp_row_id(
        project_name=project_name,
        block_code=selected_block.code,
    )

    stage, stage_reason = count_stage_safely(
        project_name=project_name,
        block_code=selected_block.code,
    )

    bugs, bug_reason = count_bugs_safely(
        project_name=project_name,
        block_code=selected_block.code,
    )

    release, release_reason = read_release_safely(
        project_name=project_name,
        block_code=selected_block.code,
    )

    counts = stage.counts if stage is not None else None
    defects = bugs.counts if bugs is not None else None
    release_info = release.info if release is not None else None

    row = build_msp_row(
        msp_id=msp_id,
        context=validated_context.model_dump(mode="json"),
        hours_ratio=get_hours_ratio(),
        azure_state=(
            release_info.azure_state
            if release_info is not None
            else None
        ),
        release_date=(
            release_info.release_date
            if release_info is not None
            else None
        ),
        functional_test_cases=(
            counts.functional
            if counts is not None
            else None
        ),
        uncovered_functional_test_cases=(
            counts.uncovered_functional
            if counts is not None
            else None
        ),
        non_functional_test_cases=(
            counts.non_functional
            if counts is not None
            else None
        ),
        valid_defects=(
            defects.valid_defects
            if defects is not None
            else None
        ),
        defect_type=(
            defects.defect_type
            if defects is not None
            else None
        ),
    )

    validated_row = validate_msp_row(row).model_dump(mode="json")

    notes = [
        note
        for note in (
            build_stage_note(
                msp_id=msp_id,
                stage=stage,
                reason=stage_reason,
            ),
            build_defect_note(
                msp_id=msp_id,
                bugs=bugs,
                reason=bug_reason,
            ),
            build_release_note(
                msp_id=msp_id,
                release=release,
                reason=release_reason,
            ),
        )
        if note is not None
    ]

    return (validated_row, notes)


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
    stage_notes: list[dict[str, str]] = []

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

            row, item_notes = build_row_for_item(
                project_name=project_name,
                block_code=block_code,
                description=descriptions[project_name],
            )

            rows.append(row)
            stage_notes.extend(item_notes)

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
        "stage_notes": stage_notes,
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
    stage_notes: list[dict[str, str]] = []

    for event in iter_build_rows(items):
        if event["type"] == "rows_ready":
            rows = event["rows"]
            failures = event["failures"]
            stage_notes = event["stage_notes"]
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
        "stage_notes": stage_notes,
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
            "column_labels": build_column_labels(),
            "choice_fields": build_choice_fields(),
            "rows": event["rows"],
            "failures": event["failures"],
            "stage_notes": event["stage_notes"],
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


def check_preview_conflicts(preview_id: str) -> dict[str, Any]:
    """
    Revisa qué filas de la vista previa ya existen en la matriz.

    Se consulta antes de confirmar la escritura, para advertir qué
    proyectos se van a sobrescribir y en qué estatus están hoy.

    Args:
        preview_id: Identificador de la vista previa.

    Returns:
        Las filas ya registradas con su estatus actual.

    Raises:
        PreviewExpiredError: Cuando la vista previa ya no existe.
    """
    rows = load_preview_rows(preview_id)

    if rows is None:
        raise PreviewExpiredError(
            "La vista previa ya no está en caché.",
        )

    msp_ids = [
        str(row.get("msp_id") or "").strip()
        for row in rows
        if row.get("msp_id")
    ]

    return inspect_matrix_rows(msp_ids)


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

    column_labels = build_column_labels()

    if field not in column_labels:
        raise ValueError(
            f"The field '{field}' is not in the Config tab.",
        )

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
            f"'{column_labels[field]}' does not accept that "
            f"value: "
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
