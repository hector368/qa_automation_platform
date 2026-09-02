"""Extracción de la sección de excepciones del FDD."""

from __future__ import annotations

import re
from typing import Final


EXCEPTIONS_SECTION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]*"
    r"5\."
    r"[ \t]+"
    r"(?:Exceptions|Excepciones)"
    r"[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)

TOP_LEVEL_SECTION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]*"
    r"(?P<section_number>\d{1,2})\."
    r"[ \t]+"
    r".+$",
    re.MULTILINE,
)


def extract_exceptions_section(
    document_text: str,
) -> str | None:
    """Extrae completa la sección 5 de excepciones."""
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
        return None

    section_matches = list(
        EXCEPTIONS_SECTION_PATTERN.finditer(
            normalized_text
        )
    )

    if not section_matches:
        return None

    section_match = section_matches[-1]

    section_start = section_match.start()

    section_end = _find_section_end(
        document_text=normalized_text,
        search_start=section_match.end(),
    )

    exceptions_text = normalized_text[
        section_start:section_end
    ].strip()

    return exceptions_text or None


def _find_section_end(
    *,
    document_text: str,
    search_start: int,
) -> int:
    """Busca la siguiente sección principal después de Exceptions."""
    for match in TOP_LEVEL_SECTION_PATTERN.finditer(
        document_text,
        pos=search_start,
    ):
        section_number = int(
            match.group("section_number")
        )

        if section_number > 5:
            return match.start()

    return len(document_text)