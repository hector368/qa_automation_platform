"""
Validación de metadatos para documentos del generador de casos.

Este módulo valida únicamente el nombre, extensión y tamaño del archivo.
La integridad interna del PDF o DOCX se valida durante la extracción.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from apps.pep.exceptions import (
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)


SUPPORTED_EXTENSIONS: Final[tuple[str, ...]] = (
    ".pdf",
    ".docx",
)

BYTES_PER_MB: Final[int] = 1024 * 1024


def validate_upload_metadata(
    *,
    filename: str,
    file_size: int,
    max_upload_mb: int,
) -> None:
    """
    Valida los metadatos básicos de un archivo subido.

    Args:
        filename: Nombre original del archivo.
        file_size: Tamaño del archivo en bytes.
        max_upload_mb: Límite permitido en megabytes.

    Raises:
        UnsupportedFileTypeError: Cuando la extensión no está permitida.
        EmptyFileError: Cuando el archivo no contiene bytes.
        FileTooLargeError: Cuando supera el límite configurado.
        ValueError: Cuando el límite configurado no es válido.
    """
    clean_filename = (filename or "").strip()

    if not clean_filename:
        raise UnsupportedFileTypeError(
            "El nombre del archivo está vacío."
        )

    extension = Path(clean_filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Extensión no permitida: {extension or 'sin extensión'}."
        )

    if file_size <= 0:
        raise EmptyFileError(
            "El tamaño del archivo es cero."
        )

    if max_upload_mb <= 0:
        raise ValueError(
            "MAX_UPLOAD_MB debe ser mayor que cero."
        )

    maximum_bytes = max_upload_mb * BYTES_PER_MB

    if file_size > maximum_bytes:
        raise FileTooLargeError(
            "El archivo tiene "
            f"{file_size} bytes y el máximo es {maximum_bytes}."
        )