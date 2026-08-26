"""Segmentación de requerimientos identificados por ID."""

import re
from collections import Counter

from apps.aer_test_case.exceptions import (
    RequirementSegmentationError,
)
from apps.aer_test_case.schemas.requirement_schema import (
    RequirementSegment,
)

REQUIREMENT_ID_PATTERN = re.compile(
    r"^[ \t]*"
    r"(?P<requirement_id>"
    r"[A-Z][A-Z0-9]{1,9}"
    r"[ \t]*\.[ \t]*"
    r"[A-Z0-9]{3}"
    r"[ \t]*\.[ \t]*"
    r"\d{3,4}"
    r")"
    r"(?=[ \t\r\n]|$)",
    re.MULTILINE,
)

REQUIREMENT_SECTION_END_PATTERN = re.compile(
    r"^[ \t]*"
    r"\d{1,2}\."
    r"[ \t]+"
    r"(?:Exceptions|Excepciones)"
    r"[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)


def segment_requirements(
    document_text: str,
) -> list[RequirementSegment]:
    """Divide el documento usando IDs de requerimiento."""
    normalized_text = _normalize_document_text(document_text)

    matches = list(
        REQUIREMENT_ID_PATTERN.finditer(normalized_text)
    )

    if not matches:
        raise RequirementSegmentationError(
            "No requirement IDs were detected in the document."
        )

    segments = _build_segments(
        document_text=normalized_text,
        matches=matches,
    )

    _validate_unique_requirement_ids(segments)

    return segments


def _normalize_document_text(
    document_text: str,
) -> str:
    """Normaliza saltos de línea antes de segmentar."""
    if not isinstance(document_text, str):
        raise TypeError(
            "Document text must be a string."
        )

    normalized_text = (
        document_text
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .strip()
    )

    if not normalized_text:
        raise RequirementSegmentationError(
            "Document text is empty."
        )

    return normalized_text

def _find_requirement_section_end(
    document_text: str,
    search_start: int,
) -> int:
    """Obtiene el final de la sección funcional de requerimientos."""
    section_match = REQUIREMENT_SECTION_END_PATTERN.search(
        document_text,
        pos=search_start,
    )

    if section_match is None:
        return len(document_text)

    return section_match.start()

def _build_segments(
    document_text: str,
    matches: list[re.Match],
) -> list[RequirementSegment]:
    """Construye un bloque independiente por requerimiento."""
    segments: list[RequirementSegment] = []

    for index, current_match in enumerate(matches):
        start_position = current_match.start()

        if index + 1 < len(matches):
            end_position = matches[index + 1].start()
        else:
            end_position = _find_requirement_section_end(
                document_text=document_text,
                search_start=current_match.end(),
            )

        requirement_content = document_text[
            start_position:end_position
        ].strip()

        requirement_id = current_match.group(
            "requirement_id"
        )

        title = _extract_requirement_title(
            requirement_id=requirement_id,
            requirement_content=requirement_content,
        )

        segments.append(
            RequirementSegment(
                requirement_id=requirement_id,
                title=title,
                content=requirement_content,
            )
        )

    return segments


def _extract_requirement_title(
    requirement_id: str,
    requirement_content: str,
) -> str:
    """Obtiene el título visible del requerimiento."""
    lines = requirement_content.splitlines()

    if not lines:
        return ""

    first_line = lines[0].strip()

    title = first_line.removeprefix(
        requirement_id
    ).strip()

    if title:
        return _normalize_whitespace(title)

    for line in lines[1:]:
        candidate = line.strip()

        if candidate:
            return _normalize_whitespace(candidate)

    return ""


def _normalize_whitespace(
    value: str,
) -> str:
    """Reduce espacios consecutivos dentro de un texto."""
    return " ".join(value.split())


def _validate_unique_requirement_ids(
    segments: list[RequirementSegment],
) -> None:
    """Valida que un ID no haya sido segmentado dos veces."""
    requirement_ids = [
        segment.requirement_id
        for segment in segments
    ]

    duplicate_ids = [
        requirement_id
        for requirement_id, count
        in Counter(requirement_ids).items()
        if count > 1
    ]

    if duplicate_ids:
        duplicates = ", ".join(
            sorted(duplicate_ids)
        )

        raise RequirementSegmentationError(
            "Duplicate requirement IDs were detected: "
            f"{duplicates}."
        )