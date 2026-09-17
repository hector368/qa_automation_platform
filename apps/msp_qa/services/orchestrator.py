"""Orquestación del llenado de la matriz MSP_QA."""

from __future__ import annotations

import json
import logging
import time

from typing import Any, Final

from apps.msp_qa.schemas.msp_row import validate_msp_row
from apps.msp_qa.schemas.project_context import (
    validate_block_context,
)
from apps.msp_qa.services.block_splitter import (
    find_block,
    split_description_blocks,
)
from apps.msp_qa.services.description_parser import parse_block
from apps.msp_qa.services.matrix_writer import (
    write_row_to_matrix,
)
from apps.msp_qa.services.msp_row_builder import (
    build_msp_row,
    list_empty_columns,
)
from apps.msp_qa.services.sheet_config import load_matrix_config
from apps.msp_qa.services.project_catalog import (
    get_project_description,
    list_projects,
)


logger = logging.getLogger(__name__)

# Bloques que no aportan sufijo al identificador de la matriz.
UNSUFFIXED_BLOCK_CODES: Final[tuple[str, ...]] = (
    "UNICO",
    "PREVIO",
)

def get_hours_ratio() -> float:
    """Obtiene la proporción de horas de QA desde la pestaña Config."""
    return load_matrix_config().hours_ratio


def build_column_labels() -> dict[str, str]:
    """
    Relaciona cada campo con el encabezado real de la matriz.

    Las etiquetas salen de la pestaña Config, así que la interfaz
    muestra exactamente los nombres que tiene el archivo.
    """
    return {
        mapping.field: mapping.header
        for mapping in load_matrix_config().columns
    }


def list_available_projects() -> dict[str, Any]:
    """
    Obtiene los proyectos visibles con el token configurado.

    Returns:
        Payload serializable con el catálogo de proyectos.
    """
    projects = list_projects()

    return {
        "ok": True,
        "total_projects": len(projects),
        "projects": projects,
    }


def list_project_blocks(project_name: str) -> dict[str, Any]:
    """
    Obtiene los bloques que contiene la descripción de un proyecto.

    Args:
        project_name: Nombre del proyecto en Azure DevOps.

    Returns:
        Payload serializable con los bloques detectados.
    """
    description = get_project_description(project_name)
    blocks = split_description_blocks(description)

    return {
        "ok": True,
        "project_name": project_name,
        "total_blocks": len(blocks),
        "blocks": [
            {
                "code": block.code,
                "label": block.label,
                "order": block.order,
                "header": block.header,
            }
            for block in blocks
        ],
    }


def build_msp_row_id(
    *,
    project_name: str,
    block_code: str,
) -> str:
    """
    Construye el identificador que la matriz MSP_QA usa por fila.

    La matriz combina el nombre del proyecto con el sufijo del bloque,
    por ejemplo "AMK.009_S1" o "AIN.002_CR".
    """
    if block_code in UNSUFFIXED_BLOCK_CODES:
        return project_name

    return f"{project_name}_{block_code}"


def build_diagnostics(
    *,
    row: dict[str, Any],
    parsed_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Arma la trazabilidad de la extracción.

    Sirve para explicar de dónde salió el cálculo de horas y para
    detectar etiquetas nuevas en la descripción de los proyectos.
    """
    return {
        "source_total_hours": parsed_context.get("estimated_hours"),
        "qa_hours_ratio": get_hours_ratio(),
        "empty_columns": list_empty_columns(row),
        "unmapped_labels": (
            parsed_context.get("unmapped_labels")
            or []
        ),
    }


def log_extraction_result(result: dict[str, Any]) -> None:
    """Registra el JSON estructurado resultante de la extracción."""
    serialized_result = json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )

    logger.info(
        "Fila extraída para la matriz MSP_QA:\n%s",
        serialized_result,
    )


def extract_block_context(
    *,
    project_name: str,
    block_code: str,
) -> dict[str, Any]:
    """
    Construye la fila de la matriz a partir de un bloque del proyecto.

    Args:
        project_name: Nombre del proyecto en Azure DevOps.
        block_code: Código del bloque, por ejemplo "S1" o "CR".

    Returns:
        Payload serializable con la fila y su trazabilidad.
    """
    started_at = time.perf_counter()

    description = get_project_description(project_name)
    blocks = split_description_blocks(description)
    selected_block = find_block(blocks, block_code)

    parsed_context = parse_block(selected_block.text)
    validated_context = validate_block_context(parsed_context)
    context_data = validated_context.model_dump(mode="json")

    row = build_msp_row(
        msp_id=build_msp_row_id(
            project_name=project_name,
            block_code=selected_block.code,
        ),
        context=context_data,
        hours_ratio=get_hours_ratio(),
    )

    validated_row = validate_msp_row(row)

    elapsed_seconds = round(
        time.perf_counter() - started_at,
        2,
    )

    result = {
        "ok": True,
        "project_name": project_name,
        "block": {
            "code": selected_block.code,
            "label": selected_block.label,
        },
        "msp_row": validated_row.model_dump(mode="json"),
        "column_labels": build_column_labels(),
        "diagnostics": build_diagnostics(
            row=row,
            parsed_context=context_data,
        ),
        "elapsed_seconds": elapsed_seconds,
    }

    log_extraction_result(result)

    return result


def write_extraction_to_matrix(
    *,
    project_name: str,
    block_code: str,
) -> dict[str, Any]:
    """
    Extrae el bloque y escribe la fila resultante en la matriz.

    La extraccion se repite en el servidor en lugar de confiar en lo
    que envia el navegador, de modo que en la matriz solo pueda
    escribirse lo que Azure DevOps reporta en ese momento.

    Args:
        project_name: Nombre del proyecto en Azure DevOps.
        block_code: Codigo del bloque, por ejemplo "S1" o "CR".

    Returns:
        Payload con la fila escrita y el resumen de la escritura.
    """
    extraction = extract_block_context(
        project_name=project_name,
        block_code=block_code,
    )

    write_result = write_row_to_matrix(extraction["msp_row"])

    return {
        "ok": True,
        "project_name": project_name,
        "block": extraction["block"],
        "msp_row": extraction["msp_row"],
        "write": write_result,
    }
