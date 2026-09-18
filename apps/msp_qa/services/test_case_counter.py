"""Conteo de casos de prueba por etapa de un proyecto."""

from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import Any, Final

from django.conf import settings
from django.core.cache import cache

from apps.msp_qa.services.azure_client import post_json
from apps.msp_qa.services.azure_iterations import (
    StageIteration,
    count_stage_iterations,
    is_single_block_code,
    load_stage_iterations,
    resolve_stage_iteration,
)


logger = logging.getLogger(__name__)

WIQL_PATH_TEMPLATE: Final[str] = "{project}/_apis/wit/wiql"

BATCH_PATH: Final[str] = "_apis/wit/workitemsbatch"

CACHE_KEY_TEMPLATE: Final[str] = "msp_qa:test_cases:{project}"

DEFAULT_TTL_SECONDS: Final[int] = 600

# Azure DevOps no acepta más de 200 identificadores por lectura.
BATCH_SIZE: Final[int] = 200

WORK_ITEM_TYPE: Final[str] = "Test Case"

# Campo personalizado que clasifica el caso de prueba. El nombre va
# tal como fue creado en la organización: 'Typeoftest', no
# 'TypeOfTest'. La respuesta trae esa llave literal, así que
# "corregir" la ortografía deja el campo vacío.
TEST_TYPE_FIELD: Final[str] = "Custom.Typeoftest"

FUNCTIONAL_TEST_TYPE: Final[str] = "Functional"

CLOSED_STATE: Final[str] = "Closed"

OBSOLETE_REASON: Final[str] = "Obsolete"

PATH_SEPARATOR: Final[str] = "\\"

REQUESTED_FIELDS: Final[tuple[str, ...]] = (
    "System.Id",
    "System.IterationPath",
    "System.State",
    "System.Reason",
    TEST_TYPE_FIELD,
)

WIQL_QUERY: Final[str] = (
    "SELECT [System.Id] FROM WorkItems "
    f"WHERE [System.WorkItemType] = '{WORK_ITEM_TYPE}'"
)


@dataclass(frozen=True, slots=True)
class TestCaseRecord:
    """Los datos de un caso de prueba que hacen falta para contar."""

    iteration_path: str
    test_type: str
    state: str
    reason: str


@dataclass(frozen=True, slots=True)
class TestCaseCounts:
    """Conteos de una etapa, listos para la matriz."""

    functional: int
    uncovered_functional: int
    non_functional: int
    obsolete_functional: int
    untyped: int


@dataclass(frozen=True, slots=True)
class StageCountResult:
    """Resultado del conteo, con lo necesario para diagnosticarlo."""

    iteration_name: str
    iteration_path: str
    counts: TestCaseCounts | None
    available_stages: tuple[str, ...]
    extra_stages: int

    @property
    def resolved(self) -> bool:
        """Indica si la etapa se pudo ubicar en Azure DevOps."""
        return self.counts is not None


def get_test_cases_ttl() -> int:
    """Obtiene la vigencia de los casos de prueba en caché."""
    return int(
        getattr(
            settings,
            "MSP_QA_WORK_ITEMS_TTL_SECONDS",
            DEFAULT_TTL_SECONDS,
        ),
    )


def list_project_test_case_ids(project_name: str) -> tuple[int, ...]:
    """
    Obtiene los identificadores de todos los casos de prueba.

    La consulta se lanza a nivel de proyecto, así que no hace falta
    filtrar por equipo ni por iteración: el recorte por etapa se hace
    después, sobre los datos ya descargados.
    """
    payload = post_json(
        path=WIQL_PATH_TEMPLATE.format(project=project_name),
        body={"query": WIQL_QUERY},
    )

    work_items = payload.get("workItems") or []

    return tuple(
        int(work_item["id"])
        for work_item in work_items
        if work_item.get("id") is not None
    )


def read_field(fields: dict[str, Any], name: str) -> str:
    """Lee un campo del work item, tolerando que no venga."""
    return str(fields.get(name) or "").strip()


def build_record(work_item: dict[str, Any]) -> TestCaseRecord:
    """Convierte un work item en el registro que se usa para contar."""
    fields = work_item.get("fields") or {}

    return TestCaseRecord(
        iteration_path=read_field(fields, "System.IterationPath"),
        test_type=read_field(fields, TEST_TYPE_FIELD),
        state=read_field(fields, "System.State"),
        reason=read_field(fields, "System.Reason"),
    )


def fetch_test_case_records(
    identifiers: tuple[int, ...],
) -> tuple[TestCaseRecord, ...]:
    """
    Descarga los campos de los casos de prueba en lotes.

    Args:
        identifiers: Identificadores obtenidos de la consulta.

    Returns:
        Un registro por caso de prueba.
    """
    records: list[TestCaseRecord] = []

    for start in range(0, len(identifiers), BATCH_SIZE):
        chunk = identifiers[start:start + BATCH_SIZE]

        payload = post_json(
            path=BATCH_PATH,
            body={
                "ids": list(chunk),
                "fields": list(REQUESTED_FIELDS),
            },
        )

        for work_item in payload.get("value") or []:
            records.append(build_record(work_item))

    return tuple(records)


def load_project_test_cases(
    project_name: str,
) -> tuple[TestCaseRecord, ...]:
    """
    Obtiene los casos de prueba de un proyecto, con caché.

    Un proyecto puede tener varias etapas y todas se cuentan sobre el
    mismo recorrido, así que se descarga una vez por proyecto.
    """
    cache_key = CACHE_KEY_TEMPLATE.format(project=project_name)
    cached_records = cache.get(cache_key)

    if cached_records is not None:
        return cached_records

    identifiers = list_project_test_case_ids(project_name)
    records = fetch_test_case_records(identifiers)

    cache.set(
        cache_key,
        records,
        timeout=get_test_cases_ttl(),
    )

    logger.info(
        "Casos de prueba leídos en %s: %s.",
        project_name,
        len(records),
    )

    return records


def belongs_to_stage(
    *,
    iteration_path: str,
    stage_path: str,
) -> bool:
    """
    Indica si un caso de prueba pertenece a una etapa.

    Reproduce el operador UNDER de Azure DevOps: la propia ruta de la
    etapa cuenta, y también todo lo que cuelgue debajo de ella.
    """
    clean_item = iteration_path.strip().casefold()
    clean_stage = stage_path.strip().casefold()

    if not clean_item or not clean_stage:
        return False

    return (
        clean_item == clean_stage
        or clean_item.startswith(clean_stage + PATH_SEPARATOR)
    )


def count_stage(
    *,
    records: tuple[TestCaseRecord, ...],
    stage_path: str,
) -> TestCaseCounts:
    """
    Cuenta los casos de prueba de una etapa.

    Los funcionales se parten en dos: los cerrados cuentan como
    ejecutados y validados, y los demás como no cubiertos.

    Los no funcionales son el complemento: todo lo que no sea del
    tipo funcional, en cualquier estado. Ahí entran los mandatorios,
    los de seguridad y los extras que se desprenden de un To-Be,
    además de los que no tienen tipo capturado.
    """
    functional = 0
    uncovered = 0
    non_functional = 0
    obsolete = 0
    untyped = 0

    expected_type = FUNCTIONAL_TEST_TYPE.casefold()
    closed_state = CLOSED_STATE.casefold()
    obsolete_reason = OBSOLETE_REASON.casefold()

    for record in records:
        if not belongs_to_stage(
            iteration_path=record.iteration_path,
            stage_path=stage_path,
        ):
            continue

        if record.test_type.casefold() != expected_type:
            non_functional += 1

            if not record.test_type:
                untyped += 1

            continue

        if record.state.casefold() != closed_state:
            uncovered += 1
            continue

        functional += 1

        if record.reason.casefold() == obsolete_reason:
            obsolete += 1

    return TestCaseCounts(
        functional=functional,
        uncovered_functional=uncovered,
        non_functional=non_functional,
        obsolete_functional=obsolete,
        untyped=untyped,
    )


def build_unresolved_result(
    stages: tuple[StageIteration, ...],
) -> StageCountResult:
    """Arma el resultado de una etapa que no existe en Azure DevOps."""
    return StageCountResult(
        iteration_name="",
        iteration_path="",
        counts=None,
        available_stages=tuple(stage.name for stage in stages),
        extra_stages=0,
    )


def count_stage_test_cases(
    *,
    project_name: str,
    block_code: str,
) -> StageCountResult:
    """
    Cuenta los casos de prueba de una etapa de un proyecto.

    Cuando la etapa no tiene iteración equivalente en Azure DevOps el
    resultado llega sin conteos, para que las celdas queden intactas.
    Un cero falso en la matriz es peor que una celda vacía: aparenta
    ser un dato medido cuando en realidad no se midió nada.

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
        return build_unresolved_result(stages)

    records = load_project_test_cases(project_name)

    # Un bloque único cubre al proyecto completo con una sola fila,
    # así que si Azure DevOps tiene más de una etapa, esa fila se
    # queda con los casos de una sola. En los demás bloques tener
    # varias etapas es lo normal: cada una trae su propia fila.
    extra_stages = (
        max(count_stage_iterations(stages) - 1, 0)
        if is_single_block_code(block_code)
        else 0
    )

    return StageCountResult(
        iteration_name=stage.name,
        iteration_path=stage.path,
        counts=count_stage(
            records=records,
            stage_path=stage.path,
        ),
        available_stages=tuple(
            available.name
            for available in stages
        ),
        extra_stages=extra_stages,
    )
