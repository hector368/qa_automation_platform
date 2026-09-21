"""Resolución de nombres internos de campos de Azure DevOps."""

from __future__ import annotations

import logging
import unicodedata

from typing import Any, Final

from django.conf import settings
from django.core.cache import cache

from apps.msp_qa.services.azure_client import request_json


logger = logging.getLogger(__name__)

FIELDS_PATH_TEMPLATE: Final[str] = (
    "{project}/_apis/wit/workitemtypes/{work_item_type}/fields"
)

CACHE_KEY_TEMPLATE: Final[str] = (
    "msp_qa:field:{project}:{work_item_type}:{slug}"
)

DEFAULT_TTL_SECONDS: Final[int] = 600


def normalize_label(raw_label: Any) -> str:
    """
    Normaliza el nombre visible de un campo para compararlo.

    Quita acentos y espacios, de modo que 'Fecha final' y
    'FECHA  FINAL' se reconozcan igual.
    """
    decomposed = unicodedata.normalize(
        "NFKD",
        str(raw_label or ""),
    )

    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )

    return "".join(without_accents.split()).casefold()


def get_fields_ttl() -> int:
    """Obtiene la vigencia del catálogo de campos en caché."""
    return int(
        getattr(
            settings,
            "MSP_QA_WORK_ITEMS_TTL_SECONDS",
            DEFAULT_TTL_SECONDS,
        ),
    )


def find_reference_name(
    *,
    payload: dict[str, Any],
    labels: tuple[str, ...],
) -> str:
    """
    Busca el campo cuyo nombre visible coincida con los buscados.

    Los nombres se prueban en orden, así que el primero de la tupla
    tiene preferencia sobre los demás.
    """
    fields_by_label: dict[str, str] = {}

    for field in payload.get("value") or []:
        label = normalize_label(field.get("name"))
        reference = str(field.get("referenceName") or "").strip()

        if label and reference and label not in fields_by_label:
            fields_by_label[label] = reference

    for label in labels:
        reference = fields_by_label.get(label)

        if reference:
            return reference

    return ""


def resolve_field_reference(
    *,
    project_name: str,
    work_item_type: str,
    labels: tuple[str, ...],
) -> str:
    """
    Averigua el nombre interno de un campo por su nombre visible.

    Los campos personalizados se crean a mano en la organización, así
    que su nombre interno no se puede dar por supuesto: se pregunta a
    Azure DevOps qué campos tiene el work item y se busca por el
    nombre que la gente ve en pantalla.

    Args:
        project_name: Nombre del proyecto en Azure DevOps.
        work_item_type: Tipo de work item, por ejemplo "Bug".
        labels: Nombres visibles aceptados, ya normalizados y en
            orden de preferencia.

    Returns:
        El nombre de referencia, o cadena vacía si no existe.
    """
    cache_key = CACHE_KEY_TEMPLATE.format(
        project=project_name,
        work_item_type=work_item_type,
        slug=labels[0] if labels else "",
    )

    cached_reference = cache.get(cache_key)

    if cached_reference is not None:
        return cached_reference

    payload = request_json(
        path=FIELDS_PATH_TEMPLATE.format(
            project=project_name,
            work_item_type=work_item_type,
        ),
    )

    reference_name = find_reference_name(
        payload=payload,
        labels=labels,
    )

    cache.set(
        cache_key,
        reference_name,
        timeout=get_fields_ttl(),
    )

    if reference_name:
        logger.info(
            "Campo '%s' de %s en %s: %s",
            labels[0] if labels else "",
            work_item_type,
            project_name,
            reference_name,
        )
    else:
        logger.warning(
            "El work item %s de %s no tiene el campo '%s'.",
            work_item_type,
            project_name,
            labels[0] if labels else "",
        )

    return reference_name
