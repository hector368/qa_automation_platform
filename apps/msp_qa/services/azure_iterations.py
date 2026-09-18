"""Resolución de las iteraciones de un proyecto de Azure DevOps."""

from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import Any, Final

from django.conf import settings
from django.core.cache import cache

from apps.msp_qa.services.azure_client import request_json


logger = logging.getLogger(__name__)

ITERATIONS_PATH_TEMPLATE: Final[str] = (
    "{project}/_apis/wit/classificationnodes/iterations"
)

CACHE_KEY_TEMPLATE: Final[str] = "msp_qa:iterations:{project}"

DEFAULT_TTL_SECONDS: Final[int] = 600

# Prefijo con el que se nombran las iteraciones de etapa.
STAGE_PREFIX: Final[str] = "General_"

# Código que el segmentador asigna a una descripción sin encabezados
# de sprint. En Azure DevOps ese caso sigue siendo el Sprint 1: el
# "único" solo existe en cómo está redactada la descripción.
SINGLE_BLOCK_CODE: Final[str] = "UNICO"
SINGLE_BLOCK_STAGE_CODE: Final[str] = "S1"

PATH_SEPARATOR: Final[str] = "\\"


@dataclass(frozen=True, slots=True)
class StageIteration:
    """Una iteración de etapa con su ruta lista para consultar."""

    name: str
    path: str


def build_work_item_path(
    *,
    project_name: str,
    stage_name: str,
) -> str:
    """
    Construye la ruta de iteración como la escriben los work items.

    El árbol de clasificación reporta rutas del tipo
    '\\MCC.016\\Iteration\\General_S1', con un segmento 'Iteration'
    intermedio que el campo System.IterationPath no usa. Por eso la
    ruta se arma con los nombres y no se copia del árbol: copiarla
    produciría consultas que devuelven cero sin marcar error.
    """
    return f"{project_name}{PATH_SEPARATOR}{stage_name}"


def extract_stage_iterations(
    *,
    project_name: str,
    payload: dict[str, Any],
) -> tuple[StageIteration, ...]:
    """Toma los hijos directos de la raíz del árbol de iteraciones."""
    children = payload.get("children") or []

    stages: list[StageIteration] = []

    for child in children:
        stage_name = str(child.get("name") or "").strip()

        if not stage_name:
            continue

        stages.append(
            StageIteration(
                name=stage_name,
                path=build_work_item_path(
                    project_name=project_name,
                    stage_name=stage_name,
                ),
            ),
        )

    return tuple(stages)


def get_iterations_ttl() -> int:
    """Obtiene la vigencia del árbol en caché, en segundos."""
    return int(
        getattr(
            settings,
            "MSP_QA_WORK_ITEMS_TTL_SECONDS",
            DEFAULT_TTL_SECONDS,
        ),
    )


def load_stage_iterations(
    project_name: str,
) -> tuple[StageIteration, ...]:
    """
    Obtiene las iteraciones de etapa de un proyecto.

    El árbol cambia poco, así que se guarda en caché para no releerlo
    una vez por cada bloque del mismo proyecto.

    Args:
        project_name: Nombre del proyecto en Azure DevOps.

    Returns:
        Iteraciones de primer nivel, en el orden que reporta Azure.
    """
    cache_key = CACHE_KEY_TEMPLATE.format(project=project_name)
    cached_stages = cache.get(cache_key)

    if cached_stages is not None:
        return cached_stages

    payload = request_json(
        path=ITERATIONS_PATH_TEMPLATE.format(project=project_name),
        query={"$depth": "1"},
    )

    stages = extract_stage_iterations(
        project_name=project_name,
        payload=payload,
    )

    cache.set(
        cache_key,
        stages,
        timeout=get_iterations_ttl(),
    )

    logger.info(
        "Iteraciones de %s: %s",
        project_name,
        ", ".join(stage.name for stage in stages) or "ninguna",
    )

    return stages


def is_single_block_code(block_code: str) -> bool:
    """Indica si el bloque abarca al proyecto completo."""
    return (block_code or "").strip().upper() == SINGLE_BLOCK_CODE


def normalize_stage_code(block_code: str) -> str:
    """Traduce el código del bloque al código de la etapa."""
    clean_code = (block_code or "").strip().upper()

    if clean_code == SINGLE_BLOCK_CODE:
        return SINGLE_BLOCK_STAGE_CODE

    return clean_code


def resolve_stage_iteration(
    *,
    block_code: str,
    stages: tuple[StageIteration, ...],
) -> StageIteration | None:
    """
    Busca la iteración que corresponde a un bloque de la descripción.

    Primero intenta el nombre esperado ('General_S1') y, si el
    proyecto usa otra convención, acepta cualquier iteración cuyo
    nombre termine con el código de la etapa.

    Returns:
        La iteración encontrada, o None cuando no hay coincidencia.
    """
    stage_code = normalize_stage_code(block_code)

    if not stage_code:
        return None

    expected_name = f"{STAGE_PREFIX}{stage_code}".casefold()

    for stage in stages:
        if stage.name.casefold() == expected_name:
            return stage

    expected_suffix = f"_{stage_code}".casefold()

    for stage in stages:
        if stage.name.casefold().endswith(expected_suffix):
            return stage

    logger.info(
        "El bloque %s no tiene iteración equivalente. "
        "Iteraciones disponibles: %s",
        block_code,
        ", ".join(stage.name for stage in stages) or "ninguna",
    )

    return None


def count_stage_iterations(
    stages: tuple[StageIteration, ...],
) -> int:
    """Cuenta las iteraciones que siguen el prefijo de etapa."""
    return sum(
        1
        for stage in stages
        if stage.name.casefold().startswith(STAGE_PREFIX.casefold())
    )
