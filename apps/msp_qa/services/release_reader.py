"""Lectura del estatus y la fecha de liberación de una etapa."""

from __future__ import annotations

import logging

from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
from typing import Any, Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.cache import cache

from apps.msp_qa.services.azure_client import post_json
from apps.msp_qa.services.azure_iterations import (
    StageIteration,
    load_stage_iterations,
    resolve_stage_iteration,
)
from apps.msp_qa.services.field_resolver import (
    resolve_field_reference,
)
from apps.msp_qa.services.test_case_counter import (
    BATCH_SIZE,
    read_field,
)


logger = logging.getLogger(__name__)

WIQL_PATH_TEMPLATE: Final[str] = "{project}/_apis/wit/wiql"

BATCH_PATH: Final[str] = "_apis/wit/workitemsbatch"

CACHE_KEY_TEMPLATE: Final[str] = "msp_qa:release:{project}:{stage}"

DEFAULT_TTL_SECONDS: Final[int] = 600

WORK_ITEM_TYPE: Final[str] = "Requirement"

# Título del work item que marca la liberación de la etapa.
RELEASE_TITLE: Final[str] = "Liberación Testing"

# Nombres visibles aceptados para la fecha de liberación, en orden de
# preferencia y ya normalizados (sin acentos ni espacios).
RELEASE_DATE_LABELS: Final[tuple[str, ...]] = (
    "fechafinal",
    "fechadefinalizacion",
    "finishdate",
)

STATE_FIELD: Final[str] = "System.State"
CHANGED_DATE_FIELD: Final[str] = "System.ChangedDate"

BASE_FIELDS: Final[tuple[str, ...]] = (
    "System.Id",
    "System.Title",
    STATE_FIELD,
    CHANGED_DATE_FIELD,
)

# La matriz captura la fecha como día/mes/año, sin hora.
DATE_OUTPUT_FORMAT: Final[str] = "%d/%m/%Y"

ISO_DATE_LENGTH: Final[int] = 10

TIME_SEPARATOR: Final[str] = "T"


@dataclass(frozen=True, slots=True)
class ReleaseRecord:
    """Los datos del work item de liberación de una etapa."""

    state: str
    release_date: str
    changed_at: str


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    """Lo que la etapa aporta a ESTATUS y FECHA LIBERACIÓN."""

    azure_state: str
    release_date: str
    matches: int
    date_field: str


@dataclass(frozen=True, slots=True)
class StageReleaseResult:
    """Resultado de la lectura, con su trazabilidad."""

    iteration_name: str
    info: ReleaseInfo | None

    @property
    def resolved(self) -> bool:
        """Indica si la etapa se pudo ubicar en Azure DevOps."""
        return self.info is not None


def get_release_ttl() -> int:
    """Obtiene la vigencia de la liberación en caché, en segundos."""
    return int(
        getattr(
            settings,
            "MSP_QA_WORK_ITEMS_TTL_SECONDS",
            DEFAULT_TTL_SECONDS,
        ),
    )


def get_local_timezone() -> tzinfo:
    """
    Obtiene la zona horaria con la que se interpreta la fecha.

    Azure DevOps entrega los instantes en UTC, pero la fecha que la
    gente ve en pantalla es la local. Sin convertir, una liberación de
    la tarde puede quedar registrada al día siguiente.
    """
    zone_name = (
        getattr(settings, "TIME_ZONE", "")
        or "UTC"
    )

    try:
        return ZoneInfo(zone_name)

    except (ZoneInfoNotFoundError, ValueError):
        logger.warning(
            "No se pudo usar la zona horaria '%s'; se toma UTC.",
            zone_name,
        )

        return timezone.utc


def parse_azure_timestamp(raw_value: Any) -> datetime | None:
    """Convierte un instante de Azure DevOps en datetime con zona."""
    clean_value = str(raw_value or "").strip()

    if not clean_value:
        return None

    try:
        parsed = datetime.fromisoformat(
            clean_value.replace("Z", "+00:00"),
        )

    except ValueError:
        try:
            parsed = datetime.strptime(
                clean_value[:ISO_DATE_LENGTH],
                "%Y-%m-%d",
            )

        except ValueError:
            logger.warning(
                "Fecha de Azure DevOps no reconocida: '%s'.",
                raw_value,
            )

            return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed


def format_release_date(raw_value: Any) -> str:
    """Devuelve la fecha en el formato que usa la matriz."""
    clean_value = str(raw_value or "").strip()
    parsed = parse_azure_timestamp(clean_value)

    if parsed is None:
        return ""

    # Un valor sin hora ya expresa el día correcto. Convertirlo de
    # zona lo movería al día anterior, porque se asume medianoche en
    # UTC. Solo los instantes con hora necesitan la conversión.
    if TIME_SEPARATOR not in clean_value:
        return parsed.strftime(DATE_OUTPUT_FORMAT)

    return parsed.astimezone(
        get_local_timezone(),
    ).strftime(DATE_OUTPUT_FORMAT)


def build_wiql_query(stage_path: str) -> str:
    """Arma la consulta del work item de liberación de una etapa."""
    escaped_path = stage_path.replace("'", "''")
    escaped_title = RELEASE_TITLE.replace("'", "''")

    return (
        "SELECT [System.Id] FROM WorkItems "
        f"WHERE [System.WorkItemType] = '{WORK_ITEM_TYPE}' "
        f"AND [System.Title] = '{escaped_title}' "
        f"AND [System.IterationPath] UNDER '{escaped_path}'"
    )


def list_stage_release_ids(
    *,
    project_name: str,
    stage_path: str,
) -> tuple[int, ...]:
    """Obtiene los identificadores de las liberaciones de la etapa."""
    payload = post_json(
        path=WIQL_PATH_TEMPLATE.format(project=project_name),
        body={"query": build_wiql_query(stage_path)},
    )

    return tuple(
        int(work_item["id"])
        for work_item in payload.get("workItems") or []
        if work_item.get("id") is not None
    )


def build_record(
    *,
    work_item: dict[str, Any],
    date_field: str,
) -> ReleaseRecord:
    """Convierte un work item en el registro de liberación."""
    fields = work_item.get("fields") or {}

    raw_date = (
        read_field(fields, date_field)
        if date_field
        else ""
    )

    return ReleaseRecord(
        state=read_field(fields, STATE_FIELD),
        release_date=format_release_date(raw_date),
        changed_at=read_field(fields, CHANGED_DATE_FIELD),
    )


def fetch_release_records(
    *,
    identifiers: tuple[int, ...],
    date_field: str,
) -> tuple[ReleaseRecord, ...]:
    """Descarga los campos de las liberaciones encontradas."""
    requested_fields = list(BASE_FIELDS)

    if date_field:
        requested_fields.append(date_field)

    records: list[ReleaseRecord] = []

    for start in range(0, len(identifiers), BATCH_SIZE):
        chunk = identifiers[start:start + BATCH_SIZE]

        payload = post_json(
            path=BATCH_PATH,
            body={
                "ids": list(chunk),
                "fields": requested_fields,
            },
        )

        for work_item in payload.get("value") or []:
            records.append(
                build_record(
                    work_item=work_item,
                    date_field=date_field,
                ),
            )

    return tuple(records)


def pick_release(
    records: tuple[ReleaseRecord, ...],
) -> ReleaseRecord | None:
    """
    Elige la liberación vigente de la etapa.

    Lo normal es que haya una sola. Si aparecen varias gana la
    modificada más recientemente, y la cantidad se reporta para que se
    note que hubo ambigüedad.
    """
    if not records:
        return None

    return max(
        records,
        key=lambda record: record.changed_at,
    )


def load_stage_release(
    *,
    project_name: str,
    stage: StageIteration,
) -> ReleaseInfo:
    """Obtiene la liberación de una etapa, con caché."""
    cache_key = CACHE_KEY_TEMPLATE.format(
        project=project_name,
        stage=stage.name,
    )

    cached_info = cache.get(cache_key)

    if cached_info is not None:
        return cached_info

    date_field = resolve_field_reference(
        project_name=project_name,
        work_item_type=WORK_ITEM_TYPE,
        labels=RELEASE_DATE_LABELS,
    )

    identifiers = list_stage_release_ids(
        project_name=project_name,
        stage_path=stage.path,
    )

    records = fetch_release_records(
        identifiers=identifiers,
        date_field=date_field,
    )

    selected = pick_release(records)

    info = ReleaseInfo(
        azure_state=selected.state if selected else "",
        release_date=selected.release_date if selected else "",
        matches=len(records),
        date_field=date_field,
    )

    cache.set(
        cache_key,
        info,
        timeout=get_release_ttl(),
    )

    logger.info(
        "Liberación de %s (%s): %s work item(s), estado '%s'.",
        project_name,
        stage.name,
        info.matches,
        info.azure_state or "sin dato",
    )

    return info


def read_stage_release(
    *,
    project_name: str,
    block_code: str,
) -> StageReleaseResult:
    """
    Lee el estatus y la fecha de liberación de una etapa.

    Usa la misma correspondencia entre bloque e iteración que los
    casos de prueba y los defectos, así que una etapa sin iteración
    deja las celdas intactas en lugar de inventar un estatus.

    Args:
        project_name: Nombre del proyecto en Azure DevOps.
        block_code: Código del bloque, por ejemplo "S1" o "CR".

    Returns:
        El estado crudo de Azure y la fecha ya formateada.
    """
    stages = load_stage_iterations(project_name)

    stage = resolve_stage_iteration(
        block_code=block_code,
        stages=stages,
    )

    if stage is None:
        return StageReleaseResult(iteration_name="", info=None)

    return StageReleaseResult(
        iteration_name=stage.name,
        info=load_stage_release(
            project_name=project_name,
            stage=stage,
        ),
    )
