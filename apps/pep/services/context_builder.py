"""
Construcción del contexto combinado del generador PEP.

Este módulo une la información administrativa del PAP con el análisis
funcional y de insumos obtenido desde el PDD/FDD.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from apps.pep.schemas.pap_schema import PapExtractionData
from apps.pep.schemas.pdd_schema import PddAnalysisData


@dataclass(frozen=True, slots=True)
class PepContext:
    """Contexto completo requerido para generar el PEP."""

    project_id: str | None
    output_filename: str
    pap: PapExtractionData
    pdd: PddAnalysisData
    warnings: tuple[str, ...]


def build_pep_context(
    *,
    pap_data: PapExtractionData,
    pdd_data: PddAnalysisData,
) -> PepContext:
    """
    Construye el contexto final del PEP.

    El ID principal se toma únicamente del PAP. No se inventa un ID
    cuando ese dato no fue extraído.

    Args:
        pap_data: Información validada del PAP.
        pdd_data: Información validada y recalculada del PDD/FDD.

    Returns:
        Contexto listo para previsualización o generación DOCX.
    """
    project_id = _clean_optional_text(
        pap_data.id_proyecto
    )

    warnings = _build_context_warnings(
        pap_data=pap_data,
        pdd_data=pdd_data,
    )

    return PepContext(
        project_id=project_id,
        output_filename=build_pep_output_filename(
            project_id
        ),
        pap=pap_data,
        pdd=pdd_data,
        warnings=tuple(warnings),
    )


def build_pep_context_payload(
    context: PepContext,
) -> dict[str, Any]:
    """
    Convierte el contexto en un payload serializable.

    Args:
        context: Contexto combinado del PEP.

    Returns:
        Diccionario listo para una respuesta JSON.
    """
    requirements = context.pdd.requerimientos

    return {
        "ok": True,
        "project_id": context.project_id,
        "output_filename": context.output_filename,
        "pap": context.pap.model_dump(
            mode="json",
        ),
        "pdd": context.pdd.model_dump(
            mode="json",
        ),
        "warnings": list(context.warnings),
        "summary": {
            "functional_requirements": len(
                requirements
            ),
            "insumo_calculation_status": (
                context.pdd.calculo_insumos.estado_calculo
            ),
            "technology_source": "pdd",
        },
    }


def build_pep_output_filename(
    project_id: str | None,
) -> str:
    """
    Construye un nombre seguro para el documento final.

    Args:
        project_id: ID extraído desde el PAP.

    Returns:
        Nombre DOCX seguro.
    """
    safe_project_id = _sanitize_filename_part(
        project_id or "PROYECTO"
    )

    return f"{safe_project_id}_PEP.docx"


def _build_context_warnings(
    *,
    pap_data: PapExtractionData,
    pdd_data: PddAnalysisData,
) -> list[str]:
    """Consolida advertencias del PAP y PDD/FDD."""
    warnings = [
        *pap_data.advertencias,
        *pdd_data.advertencias,
    ]

    if not _clean_optional_text(
        pap_data.id_proyecto
    ):
        warnings.append(
            "No se detectó el ID del proyecto en el PAP."
        )

    if not pdd_data.requerimientos:
        warnings.append(
            "No se detectaron requerimientos funcionales "
            "principales para insertar en el PEP."
        )

    calculation = pdd_data.calculo_insumos

    if (
        calculation.estado_calculo
        == "error_validacion"
        and calculation.mensaje_validacion
    ):
        warnings.append(
            calculation.mensaje_validacion
        )

    return _remove_duplicate_warnings(
        warnings
    )


def _remove_duplicate_warnings(
    warnings: list[str],
) -> list[str]:
    """Elimina advertencias repetidas conservando el orden."""
    unique_warnings: list[str] = []
    seen: set[str] = set()

    for warning in warnings:
        clean_warning = " ".join(
            (warning or "").split()
        )

        if not clean_warning:
            continue

        comparison_value = clean_warning.casefold()

        if comparison_value in seen:
            continue

        seen.add(comparison_value)
        unique_warnings.append(
            clean_warning
        )

    return unique_warnings


def _clean_optional_text(
    value: str | None,
) -> str | None:
    """Normaliza un valor de texto opcional."""
    if value is None:
        return None

    clean_value = " ".join(
        value.split()
    )

    return clean_value or None


def _sanitize_filename_part(
    value: str,
) -> str:
    """Limpia un valor para utilizarlo en un nombre de archivo."""
    clean_value = value.strip()

    clean_value = re.sub(
        r'[<>:"/\\|?*]+',
        "_",
        clean_value,
    )

    clean_value = re.sub(
        r"\s+",
        "_",
        clean_value,
    )

    clean_value = re.sub(
        r"_+",
        "_",
        clean_value,
    )

    clean_value = clean_value.strip(
        "._"
    )

    return clean_value or "PROYECTO"