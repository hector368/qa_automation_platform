"""
Análisis estructurado de documentos PAP.

Este servicio valida y extrae el documento, llama a Claude y convierte
su respuesta en información validada para generar el PEP.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from apps.pep.exceptions import ResponseParsingError
from apps.pep.schemas.pap_schema import (
    PapExtractionData,
    validate_pap_payload,
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
from apps.pep.services.prompt_loader import (
    load_pap_prompt,
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
class PapAnalysisResult:
    """Resultado normalizado del análisis PAP."""

    data: PapExtractionData
    usage: TokenUsage
    cost: TokenCost
    elapsed_seconds: float
    text_chars: int


def analyze_pap_document(
    *,
    filename: str,
    file_bytes: bytes,
    max_upload_mb: int | None = None,
) -> PapAnalysisResult:
    """
    Analiza un documento PAP utilizando Claude.

    Args:
        filename: Nombre original del documento.
        file_bytes: Contenido binario.
        max_upload_mb: Límite opcional de carga.

    Returns:
        Resultado estructurado y validado.

    Raises:
        PepError: Cuando falla la validación, extracción, configuración,
            llamada al modelo o validación de respuesta.
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

    prompt_text = load_pap_prompt()

    claude_result = call_claude(
        system_prompt=prompt_text,
        user_text=_build_pap_user_text(
            document_text
        ),
    )

    try:
        payload = parse_json_response(
            claude_result.text
        )
    except ValueError as exc:
        raise ResponseParsingError(
            "La respuesta PAP no contiene JSON válido."
        ) from exc

    pap_data = validate_pap_payload(
        payload
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

    return PapAnalysisResult(
        data=pap_data,
        usage=claude_result.usage,
        cost=cost,
        elapsed_seconds=round(
            elapsed_seconds,
            2,
        ),
        text_chars=len(document_text),
    )


def build_pap_preview_payload(
    result: PapAnalysisResult,
) -> dict[str, Any]:
    """
    Convierte el análisis PAP en un payload serializable.

    Args:
        result: Resultado validado del análisis.

    Returns:
        Diccionario para la interfaz o el orquestador.
    """
    return {
        "ok": True,
        "pap": result.data.model_dump(
            mode="json"
        ),
        "usage": result.usage.to_dict(),
        "cost": result.cost.to_dict(),
        "elapsed": result.elapsed_seconds,
        "text_chars": result.text_chars,
    }


def _build_pap_user_text(
    document_text: str,
) -> str:
    """Construye el mensaje de usuario enviado al modelo."""
    return (
        "Contenido del PAP:\n"
        f"{document_text.strip()}"
    )