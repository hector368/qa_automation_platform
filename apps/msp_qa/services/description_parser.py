"""Conversión de un bloque de descripción en datos estructurados."""

from __future__ import annotations

import logging
import re
import unicodedata

from typing import Any, Final


logger = logging.getLogger(__name__)

LABEL_LINE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\s*([^:]{2,60}?)\s*:\s*(.*)$",
)

PEOPLE_SEPARATOR_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\s*(?:/|,|&|\by\b)\s*",
    re.IGNORECASE,
)

WHITESPACE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\s+")

DEVELOPER_FIELD: Final[str] = "developers"

# Cada campo canónico agrupa las variantes de etiqueta observadas en
# las descripciones reales de Azure DevOps. Al aparecer una variante
# nueva, basta con agregarla aquí.
FIELD_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "project_name": (
        "nombre del proyecto",
        "project name",
        "nome do projeto",
    ),
    "client": (
        "empresa",
        "cliente",
        "company",
        "customer",
    ),
    "delivery_manager": (
        "delivery manager",
    ),
    "scrum_master": (
        "scrum master",
    ),
    "business_analyst": (
        "business analyst",
        "analista de negocio",
    ),
    "architect": (
        "arquitecto",
        "arquiteto",
        "architect",
        "solution architect",
    ),
    "technical_lead": (
        "lider tecnico",
        "technical lead",
        "tech lead",
    ),
    "developers": (
        "desarrollador",
        "desarrolladores",
        "developer",
        "developers",
        "desenvolvedor",
        "desenvolvedores",
        "dev",
        "devs",
        "dev rpa",
        "dev power bi",
        "ml engineer",
        "machine learning engineer",
        "data engineer",
        "data enginer",
        "date enginer",
    ),
    "tester": (
        "tester",
        "testers",
        "qa",
    ),
    "code_reviewer": (
        "code reviewer",
        "code reviewers",
    ),
    "start_date": (
        "fecha de inicio",
        "fecha de inicio de proyecto",
        "fecha de inicio estimada",
        "start date",
        "estimated start date",
        "data de inicio",
    ),
    "end_date": (
        "fecha estimada de fin",
        "fecha estimada de fin de proyecto",
        "fecha de fin",
        "fecha fin",
        "end date",
        "estimated end date",
        "data de fim",
    ),
    "duration": (
        "duracion",
        "duracion estimada",
        "duration",
        "estimated duration",
        "duracao",
    ),
    "sprint_count": (
        "numero de sprints",
        "number of sprints",
        "sprints",
    ),
    "service_type": (
        "tipo de servicio",
        "service type",
        "tipo de servico",
    ),
    "estimated_hours": (
        "horas",
        "horas totales",
        "horas totais",
        "horas_s1",
        "horas_s2",
        "horas_s3",
        "hours",
        "total hours",
    ),
}

# Etiquetas conocidas que no alimentan ninguna columna de la matriz.
# Se reconocen a proposito para no reportarlas como variantes nuevas.
IGNORED_LABELS: Final[frozenset[str]] = frozenset(
    {
        "revisor qc",
    },
)

PEOPLE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "delivery_manager",
        "scrum_master",
        "business_analyst",
        "architect",
        "technical_lead",
        "developers",
        "tester",
        "code_reviewer",
    },
)


def normalize_label(raw_label: str) -> str:
    """Normaliza un texto a minúsculas, sin acentos ni espacios extra."""
    decomposed_text = unicodedata.normalize("NFKD", raw_label)

    text_without_accents = "".join(
        character
        for character in decomposed_text
        if not unicodedata.combining(character)
    )

    collapsed_text = WHITESPACE_PATTERN.sub(
        " ",
        text_without_accents,
    )

    return collapsed_text.strip().lower()


def build_alias_index() -> dict[str, str]:
    """Construye el índice de alias normalizados a campo canónico."""
    alias_index: dict[str, str] = {}

    for field_name, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            alias_index[normalize_label(alias)] = field_name

    return alias_index


def split_people(raw_value: str) -> list[str]:
    """Separa una lista de personas escrita en lenguaje natural."""
    if not raw_value:
        return []

    candidates = PEOPLE_SEPARATOR_PATTERN.split(raw_value)

    return [
        candidate.strip()
        for candidate in candidates
        if candidate.strip()
    ]


def deduplicate_preserving_order(values: list[str]) -> list[str]:
    """Elimina duplicados conservando el orden de aparición."""
    seen_values: set[str] = set()
    unique_values: list[str] = []

    for value in values:
        normalized_value = normalize_label(value)

        if normalized_value in seen_values:
            continue

        seen_values.add(normalized_value)
        unique_values.append(value)

    return unique_values


def build_parsed_payload(
    *,
    parsed_fields: dict[str, Any],
    developer_roles: dict[str, list[str]],
    unmapped_labels: list[dict[str, str]],
) -> dict[str, Any]:
    """Completa los campos ausentes y agrega el diagnóstico."""
    payload: dict[str, Any] = {}

    for field_name in FIELD_ALIASES:
        if field_name in PEOPLE_FIELDS:
            payload[field_name] = deduplicate_preserving_order(
                parsed_fields.get(field_name) or [],
            )
            continue

        payload[field_name] = parsed_fields.get(field_name)

    missing_fields = [
        field_name
        for field_name, value in payload.items()
        if not value
    ]

    payload["developer_roles"] = developer_roles
    payload["unmapped_labels"] = unmapped_labels
    payload["missing_fields"] = missing_fields

    return payload


def parse_block(block_text: str) -> dict[str, Any]:
    """
    Convierte el texto de un bloque en datos estructurados.

    Las etiquetas que no se reconocen no se descartan: se devuelven en
    "unmapped_labels" para poder detectar variaciones nuevas en la
    forma de capturar la descripción del proyecto.

    Args:
        block_text: Contenido de un bloque de la descripción.

    Returns:
        Diccionario con los campos reconocidos y el diagnóstico.
    """
    alias_index = build_alias_index()

    parsed_fields: dict[str, Any] = {}
    developer_roles: dict[str, list[str]] = {}
    unmapped_labels: list[dict[str, str]] = []

    for line in block_text.splitlines():
        line_match = LABEL_LINE_PATTERN.match(line)

        if line_match is None:
            continue

        raw_label = line_match.group(1).strip()
        raw_value = line_match.group(2).strip()

        if not raw_value:
            continue

        normalized_label = normalize_label(raw_label)

        if normalized_label in IGNORED_LABELS:
            continue

        field_name = alias_index.get(normalized_label)

        if field_name is None:
            unmapped_labels.append(
                {
                    "label": raw_label,
                    "value": raw_value,
                },
            )
            continue

        if field_name in PEOPLE_FIELDS:
            people = split_people(raw_value)

            accumulated_people = parsed_fields.get(field_name) or []
            parsed_fields[field_name] = accumulated_people + people

            if field_name == DEVELOPER_FIELD:
                developer_roles[raw_label] = people

            continue

        parsed_fields.setdefault(field_name, raw_value)

    if unmapped_labels:
        logger.info(
            "Se encontraron %s etiquetas sin mapear en el bloque.",
            len(unmapped_labels),
        )

    return build_parsed_payload(
        parsed_fields=parsed_fields,
        developer_roles=developer_roles,
        unmapped_labels=unmapped_labels,
    )


def extract_labels(block_text: str) -> list[str]:
    """
    Obtiene las etiquetas presentes en un bloque, sin interpretarlas.

    Sirve para auditar qué variantes de etiqueta existen realmente en
    las descripciones de los proyectos.

    Args:
        block_text: Contenido de un bloque de la descripción.

    Returns:
        Etiquetas encontradas, en el orden en que aparecen.
    """
    labels: list[str] = []

    for line in block_text.splitlines():
        line_match = LABEL_LINE_PATTERN.match(line)

        if line_match is None:
            continue

        raw_label = line_match.group(1).strip()
        raw_value = line_match.group(2).strip()

        if raw_label and raw_value:
            labels.append(raw_label)

    return labels
