"""Resolución de referencias entre requerimientos AER."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Final

from apps.aer_test_case.schemas.requirement_schema import (
    RequirementSegment,
)


FULL_REQUIREMENT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b"
    r"(?P<requirement_id>"
    r"[A-Z][A-Z0-9]{1,9}\."
    r"\d{3}\."
    r"\d{3}"
    r")"
    r"\b"
)

REFERENCE_RANGE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:REQ|RQ)\s*"
    r"(?P<start>\d{1,3})"
    r"\s*(?:A|AL|-|–|—)\s*"
    r"(?:REQ|RQ)?\s*"
    r"(?P<end>\d{1,3})\b",
    re.IGNORECASE,
)

SINGLE_REFERENCE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:REQ|RQ)\s*"
    r"(?P<number>\d{1,3})\b",
    re.IGNORECASE,
)

MAX_REFERENCE_RANGE: Final[int] = 100


def resolve_referenced_requirements(
    *,
    current_requirement: RequirementSegment,
    requirements: Sequence[RequirementSegment],
) -> list[RequirementSegment]:
    """Obtiene los requerimientos referenciados explícitamente."""
    requirement_map = {
        requirement.requirement_id: requirement
        for requirement in requirements
    }

    project_prefix = _get_project_prefix(
        current_requirement.requirement_id
    )

    reference_ids = _extract_reference_ids(
        content=current_requirement.content,
        project_prefix=project_prefix,
    )

    resolved_requirements: list[RequirementSegment] = []

    for requirement_id in reference_ids:
        if (
            requirement_id
            == current_requirement.requirement_id
        ):
            continue

        referenced_requirement = requirement_map.get(
            requirement_id
        )

        if referenced_requirement is None:
            continue

        resolved_requirements.append(
            referenced_requirement
        )

    return resolved_requirements


def build_reference_context(
    referenced_requirements: Sequence[
        RequirementSegment
    ],
) -> str | None:
    """Construye el contexto textual para el prompt."""
    if not referenced_requirements:
        return None

    blocks = [
        _format_reference_block(requirement)
        for requirement in referenced_requirements
    ]

    return "\n\n".join(blocks)


def _extract_reference_ids(
    *,
    content: str,
    project_prefix: str,
) -> list[str]:
    """Extrae referencias completas, rangos y referencias simples."""
    discovered_ids: list[str] = []

    for match in FULL_REQUIREMENT_PATTERN.finditer(
        content
    ):
        discovered_ids.append(
            match.group("requirement_id")
        )

    for match in REFERENCE_RANGE_PATTERN.finditer(
        content
    ):
        start_number = int(
            match.group("start")
        )
        end_number = int(
            match.group("end")
        )

        range_ids = _build_range_ids(
            project_prefix=project_prefix,
            start_number=start_number,
            end_number=end_number,
        )

        discovered_ids.extend(
            range_ids
        )

    for match in SINGLE_REFERENCE_PATTERN.finditer(
        content
    ):
        requirement_number = int(
            match.group("number")
        )

        discovered_ids.append(
            _build_requirement_id(
                project_prefix=project_prefix,
                requirement_number=requirement_number,
            )
        )

    return _deduplicate_preserving_order(
        discovered_ids
    )


def _get_project_prefix(
    requirement_id: str,
) -> str:
    """Obtiene el prefijo común del ID del requerimiento."""
    parts = requirement_id.split(".")

    if len(parts) != 3:
        raise ValueError(
            "Requirement ID must contain three segments."
        )

    return ".".join(
        parts[:2]
    )


def _build_range_ids(
    *,
    project_prefix: str,
    start_number: int,
    end_number: int,
) -> list[str]:
    """Convierte un rango RQ en IDs completos."""
    lower_number = min(
        start_number,
        end_number,
    )
    upper_number = max(
        start_number,
        end_number,
    )

    range_size = (
        upper_number
        - lower_number
        + 1
    )

    if range_size > MAX_REFERENCE_RANGE:
        raise ValueError(
            "Requirement reference range is too large."
        )

    return [
        _build_requirement_id(
            project_prefix=project_prefix,
            requirement_number=requirement_number,
        )
        for requirement_number in range(
            lower_number,
            upper_number + 1,
        )
    ]


def _build_requirement_id(
    *,
    project_prefix: str,
    requirement_number: int,
) -> str:
    """Construye un ID completo desde su número."""
    if requirement_number < 0:
        raise ValueError(
            "Requirement number cannot be negative."
        )

    return (
        f"{project_prefix}."
        f"{requirement_number:03d}"
    )


def _deduplicate_preserving_order(
    values: Sequence[str],
) -> list[str]:
    """Elimina duplicados sin alterar el orden."""
    seen_values: set[str] = set()
    unique_values: list[str] = []

    for value in values:
        if value in seen_values:
            continue

        seen_values.add(
            value
        )
        unique_values.append(
            value
        )

    return unique_values


def _format_reference_block(
    requirement: RequirementSegment,
) -> str:
    """Formatea un bloque referenciado para Claude."""
    return (
        f"ID: {requirement.requirement_id}\n"
        f"Título: {requirement.title}\n"
        "Contenido:\n"
        f"{requirement.content}"
    )