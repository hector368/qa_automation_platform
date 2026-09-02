"""Agrupación estructural de excepciones AER por lotes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final


MAX_EXCEPTIONS_PER_BATCH: Final[int] = 10

EXCEPTION_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]*"
    r"(?P<exception_id>[BS]\d{3,4})"
    r"(?=[ \t\r\n]|$)",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class AerExceptionBatch:
    """Representa un lote de excepciones para Claude."""

    exception_ids: tuple[str, ...]
    content: str


def build_exception_batches(
    exceptions_text: str,
) -> list[AerExceptionBatch]:
    """Divide Exceptions usando únicamente sus IDs estructurales."""
    if not isinstance(exceptions_text, str):
        raise TypeError(
            "Exceptions text must be a string."
        )

    clean_text = exceptions_text.strip()

    if not clean_text:
        raise ValueError(
            "Exceptions text cannot be empty."
        )

    matches = list(
        EXCEPTION_ID_PATTERN.finditer(
            clean_text
        )
    )

    if not matches:
        return [
            AerExceptionBatch(
                exception_ids=(),
                content=clean_text,
            )
        ]

    exception_blocks = _build_exception_blocks(
        exceptions_text=clean_text,
        matches=matches,
    )

    return _group_exception_blocks(
        exception_blocks
    )


def _build_exception_blocks(
    *,
    exceptions_text: str,
    matches: list[re.Match[str]],
) -> list[tuple[str, str]]:
    """Obtiene un bloque textual por ID de excepción."""
    blocks: list[tuple[str, str]] = []

    for index, match in enumerate(matches):
        start_position = match.start()

        if index + 1 < len(matches):
            end_position = matches[
                index + 1
            ].start()
        else:
            end_position = len(
                exceptions_text
            )

        exception_id = (
            match.group(
                "exception_id"
            )
            .strip()
            .upper()
        )

        content = exceptions_text[
            start_position:end_position
        ].strip()

        blocks.append(
            (
                exception_id,
                content,
            )
        )

    return blocks


def _group_exception_blocks(
    exception_blocks: list[tuple[str, str]],
) -> list[AerExceptionBatch]:
    """Agrupa bloques sin interpretar su contenido funcional."""
    batches: list[AerExceptionBatch] = []

    current_ids: list[str] = []
    current_contents: list[str] = []

    for exception_id, content in exception_blocks:
        current_ids.append(
            exception_id
        )

        current_contents.append(
            content
        )

        if (
            len(current_ids)
            < MAX_EXCEPTIONS_PER_BATCH
        ):
            continue

        batches.append(
            AerExceptionBatch(
                exception_ids=tuple(
                    current_ids
                ),
                content="\n\n".join(
                    current_contents
                ),
            )
        )

        current_ids = []
        current_contents = []

    if current_ids:
        batches.append(
            AerExceptionBatch(
                exception_ids=tuple(
                    current_ids
                ),
                content="\n\n".join(
                    current_contents
                ),
            )
        )

    return batches