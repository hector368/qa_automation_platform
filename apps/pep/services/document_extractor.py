"""
Extracción de texto desde documentos PDF y DOCX.

El extractor conserva el orden de las páginas, párrafos y tablas para que
la segmentación de requerimientos pueda procesar el texto posteriormente.
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from pathlib import Path
from typing import Final
from zipfile import BadZipFile

import fitz
from docx import Document
from docx.document import Document as DocumentType
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from apps.pep.exceptions import (
    DocumentExtractionError,
    EmptyDocumentTextError,
    EmptyFileError,
    UnsupportedFileTypeError,
)


PDF_EXTENSION: Final[str] = ".pdf"
DOCX_EXTENSION: Final[str] = ".docx"

SUPPORTED_EXTENSIONS: Final[tuple[str, ...]] = (
    PDF_EXTENSION,
    DOCX_EXTENSION,
)

TABLE_CELL_SEPARATOR: Final[str] = " "


def extract_text_from_document(
    *,
    filename: str,
    file_bytes: bytes,
) -> str:
    """
    Extrae texto normalizado desde un documento PDF o DOCX.

    Args:
        filename: Nombre original del archivo.
        file_bytes: Contenido binario del documento.

    Returns:
        Texto extraído y normalizado.

    Raises:
        EmptyFileError: Cuando no existen bytes.
        UnsupportedFileTypeError: Cuando la extensión no es válida.
        DocumentExtractionError: Cuando el documento está corrupto.
        EmptyDocumentTextError: Cuando no existe texto extraíble.
    """
    if not file_bytes:
        raise EmptyFileError(
            "No se recibieron bytes para extraer."
        )

    extension = Path(filename or "").suffix.lower()

    if extension == PDF_EXTENSION:
        extracted_text = _extract_pdf_text(file_bytes)
    elif extension == DOCX_EXTENSION:
        extracted_text = _extract_docx_text(file_bytes)
    else:
        raise UnsupportedFileTypeError(
            f"Extensión no soportada: {extension or 'sin extensión'}."
        )

    cleaned_text = extracted_text.strip()

    if not cleaned_text:
        raise EmptyDocumentTextError(
            f"No se obtuvo texto desde el documento {filename!r}."
        )

    return cleaned_text


def _extract_pdf_text(file_bytes: bytes) -> str:
    """
    Extrae texto de un PDF página por página.

    Args:
        file_bytes: Contenido del PDF.

    Returns:
        Texto extraído.

    Raises:
        DocumentExtractionError: Cuando el PDF no puede abrirse.
    """
    page_texts: list[str] = []

    try:
        with fitz.open(
            stream=file_bytes,
            filetype="pdf",
        ) as document:
            for page in document:
                text = _clean_text(
                    page.get_text("text") or ""
                )

                if text:
                    page_texts.append(text)

    except (
        fitz.FileDataError,
        RuntimeError,
        ValueError,
    ) as exc:
        raise DocumentExtractionError(
            f"No fue posible abrir el PDF: {exc}"
        ) from exc

    return "\n\n".join(page_texts)


def _extract_docx_text(file_bytes: bytes) -> str:
    """
    Extrae párrafos y tablas de un DOCX en su orden original.

    Args:
        file_bytes: Contenido del DOCX.

    Returns:
        Texto extraído.

    Raises:
        DocumentExtractionError: Cuando el DOCX no puede abrirse.
    """
    try:
        document = Document(
            io.BytesIO(file_bytes)
        )
    except (
        PackageNotFoundError,
        BadZipFile,
        KeyError,
        ValueError,
    ) as exc:
        raise DocumentExtractionError(
            f"No fue posible abrir el DOCX: {exc}"
        ) from exc

    parts: list[str] = []

    for block in _iter_docx_blocks(document):
        if isinstance(block, Paragraph):
            paragraph_text = _clean_text(block.text)

            if paragraph_text:
                parts.append(paragraph_text)

            continue

        if isinstance(block, Table):
            _append_table_rows(
                table=block,
                parts=parts,
            )

    return "\n".join(parts)


def _iter_docx_blocks(
    document: DocumentType,
) -> Iterator[Paragraph | Table]:
    """
    Itera párrafos y tablas conservando su orden en el documento.

    Args:
        document: Documento DOCX abierto.

    Yields:
        Párrafos o tablas.
    """
    body = document.element.body

    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, document)
        elif isinstance(child, CT_Tbl):
            yield Table(child, document)


def _append_table_rows(
    *,
    table: Table,
    parts: list[str],
) -> None:
    """
    Agrega las filas de una tabla a la colección de texto.

    Args:
        table: Tabla DOCX.
        parts: Lista donde se almacenará el texto.
    """
    for row in table.rows:
        cells: list[str] = []

        for cell in row.cells:
            cell_text = _clean_text(cell.text)

            if not cell_text:
                continue

            one_line_text = " ".join(
                cell_text.splitlines()
            ).strip()

            if one_line_text:
                cells.append(one_line_text)

        if cells:
            parts.append(
                TABLE_CELL_SEPARATOR.join(cells)
            )


def _clean_text(text: str) -> str:
    """
    Normaliza artefactos frecuentes de PDF y DOCX.

    Args:
        text: Texto crudo.

    Returns:
        Texto normalizado.
    """
    if not text:
        return ""

    normalized = text.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    normalized = normalized.replace(
        "\u200b",
        "",
    ).replace(
        "\xa0",
        " ",
    )

    normalized = normalized.replace(
        "–",
        "-",
    ).replace(
        "—",
        "-",
    )

    lines = [
        line.strip()
        for line in normalized.splitlines()
        if line.strip()
    ]

    return "\n".join(lines)