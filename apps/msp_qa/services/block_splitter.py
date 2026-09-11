"""Segmentación de la descripción de un proyecto en bloques."""

from __future__ import annotations

import logging
import re

from dataclasses import dataclass
from typing import Final

from apps.msp_qa.exceptions import (
    BlockNotFoundError,
    DescriptionEmptyError,
)


logger = logging.getLogger(__name__)

SPRINT_HEADER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\s*sprint\s*#?\s*(\d+)\s*[:.\-]?\s*$",
    re.IGNORECASE,
)

CHANGE_REQUEST_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:change\s+request|cr)\s*#?\s*(\d*)\s*[:.\-]?\s*$",
    re.IGNORECASE,
)

SEPARATOR_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\s*[-_=*]{3,}\s*$",
)

SINGLE_BLOCK_CODE: Final[str] = "UNICO"
LEADING_BLOCK_CODE: Final[str] = "PREVIO"

FIRST_CHANGE_REQUEST_NUMBERS: Final[tuple[str, ...]] = ("", "1")


@dataclass(frozen=True, slots=True)
class DescriptionBlock:
    """Representa un bloque identificado dentro de la descripción."""

    code: str
    label: str
    order: int
    header: str
    text: str


def identify_header(line: str) -> tuple[str, str] | None:
    """
    Reconoce si una línea es el encabezado de un bloque.

    Args:
        line: Línea individual de la descripción.

    Returns:
        Par con el código y la etiqueta del bloque, o None si la
        línea no corresponde a un encabezado.
    """
    sprint_match = SPRINT_HEADER_PATTERN.match(line)

    if sprint_match is not None:
        sprint_number = sprint_match.group(1)

        return (
            f"S{sprint_number}",
            f"Sprint {sprint_number}",
        )

    change_request_match = CHANGE_REQUEST_PATTERN.match(line)

    if change_request_match is not None:
        request_number = change_request_match.group(1)

        if request_number in FIRST_CHANGE_REQUEST_NUMBERS:
            return ("CR", "Change Request")

        return (
            f"CR{request_number}",
            f"Change Request {request_number}",
        )

    return None


def clean_block_lines(lines: list[str]) -> str:
    """Une las líneas de un bloque descartando los separadores."""
    kept_lines = [
        line
        for line in lines
        if SEPARATOR_PATTERN.match(line) is None
    ]

    return "\n".join(kept_lines).strip()


def locate_headers(
    lines: list[str],
) -> list[tuple[int, str, str, str]]:
    """
    Localiza los encabezados presentes en la descripción.

    Returns:
        Lista de tuplas con índice, código, etiqueta y texto original.
    """
    located_headers: list[tuple[int, str, str, str]] = []

    for index, line in enumerate(lines):
        identified_header = identify_header(line)

        if identified_header is None:
            continue

        code, label = identified_header

        located_headers.append(
            (index, code, label, line.strip()),
        )

    return located_headers


def split_description_blocks(
    description: str,
) -> tuple[DescriptionBlock, ...]:
    """
    Divide la descripción de un proyecto en bloques.

    Cada bloque corresponde a un sprint o a un change request. En la
    matriz MSP_QA esos bloques aparecen como filas distintas, con el
    sufijo del identificador (_S1, _S2, _CR).

    Args:
        description: Texto completo del campo de descripción.

    Returns:
        Bloques encontrados, en el orden en que aparecen.

    Raises:
        DescriptionEmptyError: Cuando la descripción está vacía.
    """
    clean_description = (description or "").strip()

    if not clean_description:
        raise DescriptionEmptyError(
            "La descripción del proyecto está vacía en Azure DevOps.",
        )

    lines = clean_description.splitlines()
    located_headers = locate_headers(lines)

    if not located_headers:
        logger.info(
            "La descripción no tiene encabezados de sprint ni de "
            "change request. Se tratará como un bloque único.",
        )

        return (
            DescriptionBlock(
                code=SINGLE_BLOCK_CODE,
                label="Single sprint",
                order=1,
                header="",
                text=clean_description,
            ),
        )

    blocks: list[DescriptionBlock] = []

    leading_text = clean_block_lines(
        lines[:located_headers[0][0]],
    )

    if leading_text:
        blocks.append(
            DescriptionBlock(
                code=LEADING_BLOCK_CODE,
                label="No header",
                order=1,
                header="",
                text=leading_text,
            ),
        )

    total_headers = len(located_headers)

    for position, header_data in enumerate(located_headers):
        line_index, code, label, header_text = header_data

        is_last_header = position == total_headers - 1

        end_index = (
            len(lines)
            if is_last_header
            else located_headers[position + 1][0]
        )

        blocks.append(
            DescriptionBlock(
                code=code,
                label=label,
                order=len(blocks) + 1,
                header=header_text,
                text=clean_block_lines(
                    lines[line_index + 1:end_index],
                ),
            ),
        )

    return tuple(blocks)


def find_block(
    blocks: tuple[DescriptionBlock, ...],
    block_code: str,
) -> DescriptionBlock:
    """
    Busca un bloque por su código.

    Args:
        blocks: Bloques disponibles en la descripción.
        block_code: Código solicitado, por ejemplo "S1" o "CR".

    Returns:
        Bloque coincidente.

    Raises:
        BlockNotFoundError: Cuando el código no existe.
    """
    clean_code = (block_code or "").strip().upper()

    for block in blocks:
        if block.code.upper() == clean_code:
            return block

    available_codes = ", ".join(
        block.code
        for block in blocks
    )

    raise BlockNotFoundError(
        f"El bloque {clean_code} no existe. "
        f"Bloques disponibles: {available_codes}.",
    )
