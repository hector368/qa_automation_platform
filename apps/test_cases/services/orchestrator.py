"""
Orquestación del generador de casos de prueba.

En esta fase coordina el análisis determinístico del documento sin realizar
llamadas al modelo de inteligencia artificial.
"""

from __future__ import annotations

import re
from typing import Any, Final

from apps.test_cases.exceptions import RequirementsNotFoundError
from apps.test_cases.services.document_extractor import (
    extract_text_from_document,
)
from apps.test_cases.services.file_validator import (
    validate_upload_metadata,
)
from apps.test_cases.services.requirement_segmenter import (
    segment_requirements_flexible,
)
from apps.test_cases.services.requirement_splitter import (
    RequirementBlock,
    extract_project_id,
)
from apps.test_cases.exceptions import (
    ProjectIdNotFoundError,
    RequirementsNotFoundError,
)
from apps.test_cases.schemas.request_schema import (
    GenerationRequest,
)
from apps.test_cases.services.test_case_generator import (
    generate_test_cases,
    iter_generate_test_cases,
)
from collections.abc import Iterator
from dataclasses import dataclass

MAX_PREVIEW_REQUIREMENTS: Final[int] = 400

@dataclass(frozen=True, slots=True)
class PreparedGeneration:
    """Documento procesado y listo para llamar a Claude."""

    filename: str
    project_id: str
    context_text: str
    blocks: tuple[RequirementBlock, ...]

def prepare_generation_document(
    *,
    filename: str,
    file_bytes: bytes,
    max_upload_mb: int,
) -> PreparedGeneration:
    """
    Valida, extrae y segmenta un documento.

    Esta función se ejecuta antes de abrir la respuesta de streaming,
    permitiendo devolver errores HTTP 400 o 422 normalmente.
    """
    validate_upload_metadata(
        filename=filename,
        file_size=len(file_bytes),
        max_upload_mb=max_upload_mb,
    )

    document_text = extract_text_from_document(
        filename=filename,
        file_bytes=file_bytes,
    )

    project_id = extract_project_id(
        document_text,
        filename=filename,
    )

    if not project_id:
        raise ProjectIdNotFoundError(
            "No se encontró ID en contenido ni nombre."
        )

    segmentation = segment_requirements_flexible(
        document_text,
        project_id=project_id,
    )

    blocks = tuple(
        segmentation.blocks
        or []
    )

    if not blocks:
        raise RequirementsNotFoundError(
            "El documento no produjo bloques para generación."
        )

    context_text = (
        getattr(
            segmentation,
            "context_text",
            "",
        )
        or document_text
    )

    return PreparedGeneration(
        filename=filename,
        project_id=project_id,
        context_text=context_text,
        blocks=blocks,
    )

def analyze_document(
    *,
    filename: str,
    file_bytes: bytes,
    max_upload_mb: int,
) -> dict[str, Any]:
    """
    Analiza un PDD/FDD sin utilizar Claude.

    Args:
        filename: Nombre original del documento.
        file_bytes: Contenido binario del archivo.
        max_upload_mb: Tamaño máximo permitido en megabytes.

    Returns:
        Payload serializable con el Project ID y los requerimientos.

    Raises:
        TestCasesError: Cuando el archivo o documento no es válido.
    """
    validate_upload_metadata(
        filename=filename,
        file_size=len(file_bytes),
        max_upload_mb=max_upload_mb,
    )

    document_text = extract_text_from_document(
        filename=filename,
        file_bytes=file_bytes,
    )

    project_id = extract_project_id(
        document_text,
        filename=filename,
    )

    segmentation = segment_requirements_flexible(
        document_text,
        project_id=project_id or "",
    )

    blocks = list(segmentation.blocks or [])

    if not blocks:
        raise RequirementsNotFoundError(
            "El segmentador terminó sin producir bloques. "
            f"Método final: {segmentation.method}."
        )

    requirements = [
        _build_requirement_payload(block)
        for block in blocks
    ]

    total_blocks = len(requirements)
    truncated = total_blocks > MAX_PREVIEW_REQUIREMENTS

    if truncated:
        requirements = requirements[
            :MAX_PREVIEW_REQUIREMENTS
        ]

    return {
        "ok": True,
        "project_id": project_id,
        "method": segmentation.method,
        "total_blocks": total_blocks,
        "requirements": requirements,
        "truncated": truncated,
    }

def generate_document(
    *,
    filename: str,
    file_bytes: bytes,
    max_upload_mb: int,
    generation_request: GenerationRequest,
) -> dict[str, Any]:
    """Prepara el documento y ejecuta la generación síncrona."""
    prepared = prepare_generation_document(
        filename=filename,
        file_bytes=file_bytes,
        max_upload_mb=max_upload_mb,
    )

    return generate_test_cases(
        original_filename=prepared.filename,
        project_id=prepared.project_id,
        context_text=prepared.context_text,
        blocks=prepared.blocks,
        assigned_to=generation_request.assigned_to,
        selected_requirements=(
            generation_request.selected_requirements
        ),
    )

def iter_generate_prepared_document(
    *,
    prepared: PreparedGeneration,
    generation_request: GenerationRequest,
) -> Iterator[dict[str, Any]]:
    """Emite los eventos de generación de un documento preparado."""
    yield from iter_generate_test_cases(
        original_filename=prepared.filename,
        project_id=prepared.project_id,
        context_text=prepared.context_text,
        blocks=prepared.blocks,
        assigned_to=generation_request.assigned_to,
        selected_requirements=(
            generation_request.selected_requirements
        ),
    )

def _build_requirement_payload(
    block: RequirementBlock,
) -> dict[str, int | str]:
    """
    Convierte un bloque en un requerimiento resumido para la interfaz.

    Args:
        block: Bloque detectado por el segmentador.

    Returns:
        Número y título limpio del requerimiento.
    """
    number = int(block.requirement_number)
    title = _clean_requirement_title(
        title=block.scenario_name,
        number=number,
    )

    return {
        "number": number,
        "title": title,
    }


def _clean_requirement_title(
    *,
    title: str,
    number: int,
) -> str:
    """
    Elimina numeración o prefijos repetidos del título.

    Args:
        title: Título detectado.
        number: Número normalizado del requerimiento.

    Returns:
        Título limpio.
    """
    clean_title = (title or "").strip()
    number_text = re.escape(str(number))

    patterns = (
        rf"^\s*#\s*{number_text}\s+",
        rf"^\s*{number_text}\s*[.)-]\s+",
        r"^\s*Nombre\s+de\s+la\s+acci[oó]n\s*:\s*",
    )

    for pattern in patterns:
        clean_title = re.sub(
            pattern,
            "",
            clean_title,
            count=1,
            flags=re.IGNORECASE,
        )

    clean_title = clean_title.strip()

    return clean_title or f"Requerimiento {number}"