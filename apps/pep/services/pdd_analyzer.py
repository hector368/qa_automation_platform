"""
Análisis estructurado de documentos PDD/FDD.

El servicio extrae requerimientos, tecnología y volumetría mediante
Claude. Los cálculos de insumos se recalculan posteriormente con Python.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from apps.pep.exceptions import ResponseParsingError
from apps.pep.schemas.pdd_schema import (
    PddAnalysisData,
    validate_pdd_payload,
)
from apps.pep.services.claude_client import (
    call_claude,
)
from apps.pep.services.document_extractor import (
    extract_text_from_document,
)
from apps.pep.services.file_validator import (
    validate_upload_metadata,
)
from apps.pep.services.input_calculator import (
    recalculate_insumo_plan,
)
from apps.pep.services.prompt_loader import (
    load_pdd_prompt,
)
from apps.pep.services.response_parser import (
    parse_json_response,
)
from apps.pep.services.token_usage import (
    TokenCost,
    TokenUsage,
    calculate_token_cost,
)


@dataclass(frozen=True, slots=True)
class PddAnalysisResult:
    """Resultado normalizado del análisis PDD/FDD."""

    data: PddAnalysisData
    usage: TokenUsage
    cost: TokenCost
    elapsed_seconds: float
    text_chars: int


def analyze_pdd_document(
    *,
    filename: str,
    file_bytes: bytes,
    max_upload_mb: int | None = None,
) -> PddAnalysisResult:
    """
    Analiza integralmente un documento PDD/FDD.

    El cálculo recibido desde Claude no se considera fuente definitiva.
    Después de validar el JSON, el plan de insumos se recalcula mediante
    reglas determinísticas en Python.

    Args:
        filename: Nombre original del documento.
        file_bytes: Contenido binario.
        max_upload_mb: Límite opcional de carga.

    Returns:
        Resultado estructurado, validado y recalculado.

    Raises:
        PepError: Cuando falla la validación, extracción, llamada,
            parsing o validación de esquema.
    """
    started_at = time.perf_counter()

    resolved_max_upload_mb = (
        max_upload_mb
        if max_upload_mb is not None
        else settings.MAX_UPLOAD_MB
    )

    validate_upload_metadata(
        filename=filename,
        file_size=len(file_bytes),
        max_upload_mb=resolved_max_upload_mb,
    )

    document_text = extract_text_from_document(
        filename=filename,
        file_bytes=file_bytes,
    )

    prompt_text = load_pdd_prompt()

    claude_result = call_claude(
        system_prompt=prompt_text,
        user_text=_build_pdd_user_text(
            document_text
        ),
    )

    try:
        payload = parse_json_response(
            claude_result.text
        )
    except ValueError as exc:
        raise ResponseParsingError(
            "La respuesta PDD/FDD no contiene JSON válido."
        ) from exc

    pdd_data = validate_pdd_payload(
        payload
    )

    recalculated_data = recalculate_insumo_plan(
        pdd_data
    )

    cost = calculate_token_cost(
        usage=claude_result.usage,
        input_rate_per_million=(
            settings.CLAUDE_INPUT_USD_PER_MTOK
        ),
        output_rate_per_million=(
            settings.CLAUDE_OUTPUT_USD_PER_MTOK
        ),
    )

    elapsed_seconds = (
        time.perf_counter()
        - started_at
    )

    return PddAnalysisResult(
        data=recalculated_data,
        usage=claude_result.usage,
        cost=cost,
        elapsed_seconds=round(
            elapsed_seconds,
            2,
        ),
        text_chars=len(document_text),
    )


def build_pdd_preview_payload(
    result: PddAnalysisResult,
) -> dict[str, Any]:
    """
    Convierte el análisis PDD/FDD en un payload serializable.

    Args:
        result: Resultado validado del análisis.

    Returns:
        Diccionario listo para la interfaz.
    """
    return {
        "ok": True,
        "pdd": result.data.model_dump(
            mode="json",
        ),
        "usage": result.usage.to_dict(),
        "cost": result.cost.to_dict(),
        "elapsed": result.elapsed_seconds,
        "text_chars": result.text_chars,
    }


def _build_pdd_user_text(
    document_text: str,
) -> str:
    """Construye el mensaje documental enviado al modelo."""
    return (
        "Contenido del PDD/FDD:\n"
        f"{document_text.strip()}"
    )