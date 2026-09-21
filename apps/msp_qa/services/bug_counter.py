"""Conteo de defectos y tipo predominante por etapa."""

from __future__ import annotations

import logging

from collections import Counter
from dataclasses import dataclass
from typing import Any, Final

from django.conf import settings
from django.core.cache import cache

from apps.msp_qa.services.azure_client import post_json, request_json
from apps.msp_qa.services.azure_iterations import (
    load_stage_iterations,
    resolve_stage_iteration,
)
from apps.msp_qa.services.test_case_counter import (
    BATCH_SIZE,
    belongs_to_stage,
    read_field,
)


logger = logging.getLogger(__name__)

WIQL_PATH_TEMPLATE: Final[str] = "{project}/_apis/wit/wiql"

BATCH_PATH: Final[str] = "_apis/wit/workitemsbatch"

FIELDS_PATH_TEMPLATE: Final[str] = (
    "{project}/_apis/wit/workitemtypes/{work_item_type}/fields"
)

BUGS_CACHE_KEY_TEMPLATE: Final[str] = "msp_qa:bugs:{project}"

FIELD_CACHE_KEY_TEMPLATE: Final[str] = "msp_qa:root_cause:{project}"

DEFAULT_TTL_SECONDS: Final[int] = 600

WORK_ITEM_TYPE: Final[str] = "Bug"

# El campo que alimenta la columna TIPO se creó a mano en la
# organización, así que su nombre interno no se puede dar por
# supuesto. Se resuelve preguntando a Azure DevOps qué campos tiene
# el work item Bug y buscando el que se llame así para el usuario.
# Se aceptan las dos grafías porque el nombre visible no siempre se
# captura igual.
ROOT_CAUSE_LABELS: Final[tuple[str, ...]] = (
    "rootcause",
    "rootcase",
)

CREATED_DATE_FIELD: Final[str] = "System.CreatedDate"

BASE_FIELDS: Final[tuple[str, ...]] = (
    "System.Id",
    "System.IterationPath",
    "System.State",
    CREATED_DATE_FIELD,
)

WIQL_QUERY: Final[str] = (
    "SELECT [System.Id] FROM WorkItems "
    f"WHERE [System.WorkItemType] = '{WORK_ITEM_TYPE}'"
)

# Longitud de un instante ISO hasta los segundos. Recortar ahí hace
# que las fechas se puedan ordenar como texto sin depender de cuántos
# decimales traiga cada una.
TIMESTAMP_LENGTH: Final[int] = 19


@dataclass(frozen=True, slots=True)
class BugRecord:
    """Los datos de un defecto que hacen falta para la matriz."""

    iteration_path: str
    state: str
    root_cause: str
    created_at: str


@dataclass(frozen=True, slots=True)
class BugCounts:
    """Conteos de defectos de una etapa."""

    valid_defects: int
    defect_type: str
    tied_types: tuple[str, ...]
    missing_root_cause: int


@dataclass(frozen=True, slots=True)
class StageBugResult:
    """Resultado del conteo de defectos, con su trazabilidad."""

    iteration_name: str
    counts: BugCounts | None
    root_cause_field: str

    @property
    def resolved(self) -> bool:
        """Indica si la etapa se pudo ubicar en Azure DevOps."""
        return self.counts is not None


def get_bugs_ttl() -> int:
    """Obtiene la vigencia de los defectos en caché, en segundos."""
    return int(
        getattr(
            settings,
            "MSP_QA_WORK_ITEMS_TTL_SECONDS",
            DEFAULT_TTL_SECONDS,
        ),
    )


def normalize_label(raw_label: Any) -> str:
    """Normaliza el nombre visible de un campo para compararlo."""
    return "".join(str(raw_label or "").split()).casefold()


def resolve_root_cause_field(project_name: str) -> str:
    """
    Averigua el nombre interno del campo que alimenta TIPO.

    Azure DevOps expone los campos del work item con su nombre
    visible y su nombre de referencia. Se busca por el visible, que
    es el que la gente conoce, y así el módulo no depende de cómo
    haya quedado escrito el interno.

    Returns:
        El nombre de referencia, o cadena vacía si no existe.
    """
    cache_key = FIELD_CACHE_KEY_TEMPLATE.format(project=project_name)
    cached_field = cache.get(cache_key)

    if cached_field is not None:
        return cached_field

    payload = request_json(
        path=FIELDS_PATH_TEMPLATE.format(
            project=project_name,
            work_item_type=WORK_ITEM_TYPE,
        ),
    )

    field_name = ""

    for field in payload.get("value") or []:
        if normalize_label(field.get("name")) in ROOT_CAUSE_LABELS:
            field_name = str(field.get("referenceName") or "").strip()
            break

    cache.set(
        cache_key,
        field_name,
        timeout=get_bugs_ttl(),
    )

    if field_name:
        logger.info(
            "Campo de causa raíz en %s: %s",
            project_name,
            field_name,
        )
    else:
        logger.warning(
            "El work item Bug de %s no tiene un campo de causa raíz.",
            project_name,
        )

    return field_name


def list_project_bug_ids(project_name: str) -> tuple[int, ...]:
    """Obtiene los identificadores de todos los defectos."""
    payload = post_json(
        path=WIQL_PATH_TEMPLATE.format(project=project_name),
        body={"query": WIQL_QUERY},
    )

    return tuple(
        int(work_item["id"])
        for work_item in payload.get("workItems") or []
        if work_item.get("id") is not None
    )


def build_record(
    *,
    work_item: dict[str, Any],
    root_cause_field: str,
) -> BugRecord:
    """Convierte un work item en el registro que se usa para contar."""
    fields = work_item.get("fields") or {}

    root_cause = (
        read_field(fields, root_cause_field)
        if root_cause_field
        else ""
    )

    return BugRecord(
        iteration_path=read_field(fields, "System.IterationPath"),
        state=read_field(fields, "System.State"),
        root_cause=root_cause,
        created_at=read_field(fields, CREATED_DATE_FIELD),
    )


def fetch_bug_records(
    *,
    identifiers: tuple[int, ...],
    root_cause_field: str,
) -> tuple[BugRecord, ...]:
    """Descarga los campos de los defectos en lotes."""
    requested_fields = list(BASE_FIELDS)

    if root_cause_field:
        requested_fields.append(root_cause_field)

    records: list[BugRecord] = []

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
                    root_cause_field=root_cause_field,
                ),
            )

    return tuple(records)


def load_project_bugs(
    project_name: str,
) -> tuple[tuple[BugRecord, ...], str]:
    """
    Obtiene los defectos de un proyecto, con caché.

    Returns:
        Los registros y el nombre del campo de causa raíz usado.
    """
    cache_key = BUGS_CACHE_KEY_TEMPLATE.format(project=project_name)
    cached_bugs = cache.get(cache_key)

    if cached_bugs is not None:
        return cached_bugs

    root_cause_field = resolve_root_cause_field(project_name)
    identifiers = list_project_bug_ids(project_name)

    records = fetch_bug_records(
        identifiers=identifiers,
        root_cause_field=root_cause_field,
    )

    result = (records, root_cause_field)

    cache.set(
        cache_key,
        result,
        timeout=get_bugs_ttl(),
    )

    logger.info(
        "Defectos leídos en %s: %s.",
        project_name,
        len(records),
    )

    return result


def sortable_timestamp(raw_value: str) -> str:
    """Recorta un instante ISO para poder ordenarlo como texto."""
    return raw_value[:TIMESTAMP_LENGTH]


def pick_defect_type(
    records: tuple[BugRecord, ...],
) -> tuple[str, tuple[str, ...]]:
    """
    Elige la causa raíz que más se repite entre los defectos.

    La moda se calcula sobre todos los defectos de la etapa, sin
    importar su estado. Cuando hay empate gana la del defecto creado
    más recientemente, y el empate se reporta para que quede claro
    que el valor escrito no fue unánime.

    Returns:
        La causa raíz ganadora y las que hayan empatado con ella.
    """
    causes = [
        record.root_cause
        for record in records
        if record.root_cause
    ]

    if not causes:
        return ("", ())

    occurrences = Counter(causes)
    top_count = max(occurrences.values())

    leaders = {
        cause
        for cause, count in occurrences.items()
        if count == top_count
    }

    if len(leaders) == 1:
        return (next(iter(leaders)), ())

    newest = max(
        (
            record
            for record in records
            if record.root_cause in leaders
        ),
        key=lambda record: sortable_timestamp(record.created_at),
    )

    return (newest.root_cause, tuple(sorted(leaders)))


def count_stage(
    *,
    records: tuple[BugRecord, ...],
    stage_path: str,
) -> BugCounts:
    """
    Cuenta los defectos de una etapa y decide su tipo.

    Todos los defectos de la etapa cuentan como válidos, en cualquier
    estado. La columna de no identificados se sigue llenando a mano,
    así que este módulo no la toca.
    """
    stage_records = tuple(
        record
        for record in records
        if belongs_to_stage(
            iteration_path=record.iteration_path,
            stage_path=stage_path,
        )
    )

    defect_type, tied_types = pick_defect_type(stage_records)

    return BugCounts(
        valid_defects=len(stage_records),
        defect_type=defect_type,
        tied_types=tied_types,
        missing_root_cause=sum(
            1
            for record in stage_records
            if not record.root_cause
        ),
    )


def count_stage_bugs(
    *,
    project_name: str,
    block_code: str,
) -> StageBugResult:
    """
    Cuenta los defectos de una etapa de un proyecto.

    Usa la misma correspondencia entre bloque e iteración que los
    casos de prueba, así que un proyecto sin la iteración de esa
    etapa deja las celdas intactas en lugar de escribir ceros.

    Args:
        project_name: Nombre del proyecto en Azure DevOps.
        block_code: Código del bloque, por ejemplo "S1" o "CR".

    Returns:
        Los conteos y la trazabilidad de cómo se obtuvieron.
    """
    stages = load_stage_iterations(project_name)

    stage = resolve_stage_iteration(
        block_code=block_code,
        stages=stages,
    )

    if stage is None:
        return StageBugResult(
            iteration_name="",
            counts=None,
            root_cause_field="",
        )

    records, root_cause_field = load_project_bugs(project_name)

    return StageBugResult(
        iteration_name=stage.name,
        counts=count_stage(
            records=records,
            stage_path=stage.path,
        ),
        root_cause_field=root_cause_field,
    )
