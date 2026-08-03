"""
Orquestación principal del generador PEP.

El análisis PAP/PDD consume Claude una sola vez. La generación DOCX
reutiliza exclusivamente los datos validados almacenados en caché.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from apps.pep.exceptions import (
    PepGenerationError,
    ResponseParsingError,
)
from apps.pep.schemas.pap_schema import (
    validate_pap_payload,
)
from apps.pep.schemas.pdd_schema import (
    validate_pdd_payload,
)
from apps.pep.services.context_builder import (
    build_pep_context,
    build_pep_context_payload,
)
from apps.pep.services.docx_generator import (
    generate_pep_docx_bytes,
)
from apps.pep.services.pap_analyzer import (
    analyze_pap_document,
)
from apps.pep.services.pdd_analyzer import (
    analyze_pdd_document,
)


def analyze_pep_documents(
    *,
    pap_filename: str,
    pap_bytes: bytes,
    pdd_filename: str,
    pdd_bytes: bytes,
    max_upload_mb: int | None = None,
) -> dict[str, Any]:
    """
    Analiza el PAP y el PDD/FDD.

    Returns:
        Payload serializable y reutilizable para generar el DOCX.
    """
    pap_result = analyze_pap_document(
        filename=pap_filename,
        file_bytes=pap_bytes,
        max_upload_mb=max_upload_mb,
    )

    pdd_result = analyze_pdd_document(
        filename=pdd_filename,
        file_bytes=pdd_bytes,
        max_upload_mb=max_upload_mb,
    )

    context = build_pep_context(
        pap_data=pap_result.data,
        pdd_data=pdd_result.data,
    )

    pap_usage = pap_result.usage.to_dict()
    pdd_usage = pdd_result.usage.to_dict()

    pap_cost = pap_result.cost.to_dict()
    pdd_cost = pdd_result.cost.to_dict()

    return {
        "pap_filename": pap_filename,
        "pdd_filename": pdd_filename,
        "pap": pap_result.data.model_dump(
            mode="json",
        ),
        "pdd": pdd_result.data.model_dump(
            mode="json",
        ),
        "preview": build_pep_context_payload(
            context
        ),
        "usage": {
            "pap": pap_usage,
            "pdd": pdd_usage,
            "total": _combine_usage(
                pap_usage,
                pdd_usage,
            ),
        },
        "cost": {
            "pap": pap_cost,
            "pdd": pdd_cost,
            "total": _combine_cost(
                pap_cost,
                pdd_cost,
            ),
        },
        "elapsed": round(
            pap_result.elapsed_seconds
            + pdd_result.elapsed_seconds,
            2,
        ),
    }


def generate_pep_from_analysis(
    analysis_payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Genera el DOCX desde un análisis previamente validado.

    Esta función no llama a Claude.
    """
    pap_payload = analysis_payload.get("pap")
    pdd_payload = analysis_payload.get("pdd")

    if not isinstance(pap_payload, dict):
        raise ResponseParsingError(
            "El análisis temporal no contiene datos PAP válidos."
        )

    if not isinstance(pdd_payload, dict):
        raise ResponseParsingError(
            "El análisis temporal no contiene datos PDD válidos."
        )

    pap_data = validate_pap_payload(
        pap_payload
    )

    pdd_data = validate_pdd_payload(
        pdd_payload
    )

    context = build_pep_context(
        pap_data=pap_data,
        pdd_data=pdd_data,
    )

    document_bytes = generate_pep_docx_bytes(
        context
    )

    if not document_bytes:
        raise PepGenerationError(
            "El generador DOCX devolvió un archivo vacío."
        )

    return {
        "filename": context.output_filename,
        "content": document_bytes,
        "context": build_pep_context_payload(
            context
        ),
    }


def _combine_usage(
    first: dict[str, Any],
    second: dict[str, Any],
) -> dict[str, int]:
    """Suma tokens PAP y PDD."""
    input_tokens = (
        _safe_int(
            first.get("input_tokens")
        )
        + _safe_int(
            second.get("input_tokens")
        )
    )

    output_tokens = (
        _safe_int(
            first.get("output_tokens")
        )
        + _safe_int(
            second.get("output_tokens")
        )
    )

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": (
            input_tokens
            + output_tokens
        ),
    }


def _combine_cost(
    first: dict[str, Any],
    second: dict[str, Any],
) -> dict[str, Any]:
    """Suma costos PAP y PDD."""
    input_usd = (
        _safe_decimal(
            first.get("input_usd")
        )
        + _safe_decimal(
            second.get("input_usd")
        )
    )

    output_usd = (
        _safe_decimal(
            first.get("output_usd")
        )
        + _safe_decimal(
            second.get("output_usd")
        )
    )

    total_usd = (
        _safe_decimal(
            first.get("total_usd")
        )
        + _safe_decimal(
            second.get("total_usd")
        )
    )

    return {
        "currency": "USD",
        "input_usd": float(input_usd),
        "output_usd": float(output_usd),
        "total_usd": float(total_usd),
        "total_usd_formatted": (
            f"${total_usd:.2f}"
        ),
    }


def _safe_int(
    value: Any,
) -> int:
    """Convierte un valor desconocido en entero seguro."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_decimal(
    value: Any,
) -> Decimal:
    """Convierte un valor desconocido en Decimal seguro."""
    try:
        return Decimal(
            str(value or 0)
        )
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):
        return Decimal("0")