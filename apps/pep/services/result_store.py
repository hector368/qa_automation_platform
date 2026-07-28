"""
Almacenamiento temporal de análisis y documentos PEP.

Los elementos se asocian con la sesión que los produjo para impedir
que otra sesión pueda reutilizarlos o descargarlos.
"""

from __future__ import annotations

import hmac
from typing import Any, Final

from django.core.cache import cache


ANALYSIS_CACHE_PREFIX: Final[str] = "pep:analysis:"
RESULT_CACHE_PREFIX: Final[str] = "pep:result:"


def save_pep_analysis(
    *,
    analysis_id: str,
    session_key: str,
    payload: dict[str, Any],
    timeout_seconds: int,
) -> None:
    """Guarda temporalmente un análisis PAP/PDD validado."""
    cache.set(
        _build_analysis_key(analysis_id),
        {
            "session_key": session_key,
            "payload": payload,
        },
        timeout=timeout_seconds,
    )


def load_pep_analysis(
    *,
    analysis_id: str,
    session_key: str,
) -> dict[str, Any] | None:
    """Recupera un análisis perteneciente a la sesión."""
    stored_value = cache.get(
        _build_analysis_key(analysis_id)
    )

    if not isinstance(stored_value, dict):
        return None

    if not _belongs_to_session(
        stored_value=stored_value,
        session_key=session_key,
    ):
        return None

    payload = stored_value.get("payload")

    if not isinstance(payload, dict):
        return None

    return payload


def save_pep_result(
    *,
    result_id: str,
    session_key: str,
    filename: str,
    content: bytes,
    timeout_seconds: int,
) -> None:
    """Guarda temporalmente el DOCX generado."""
    cache.set(
        _build_result_key(result_id),
        {
            "session_key": session_key,
            "filename": filename,
            "content": content,
        },
        timeout=timeout_seconds,
    )


def load_pep_result(
    *,
    result_id: str,
    session_key: str,
) -> dict[str, Any] | None:
    """Recupera un DOCX perteneciente a la sesión."""
    stored_value = cache.get(
        _build_result_key(result_id)
    )

    if not isinstance(stored_value, dict):
        return None

    if not _belongs_to_session(
        stored_value=stored_value,
        session_key=session_key,
    ):
        return None

    filename = stored_value.get("filename")
    content = stored_value.get("content")

    if not isinstance(filename, str):
        return None

    if not isinstance(content, bytes):
        return None

    return {
        "filename": filename,
        "content": content,
    }


def _belongs_to_session(
    *,
    stored_value: dict[str, Any],
    session_key: str,
) -> bool:
    """Comprueba de forma segura la propiedad de una entrada."""
    stored_session_key = stored_value.get(
        "session_key"
    )

    if not isinstance(stored_session_key, str):
        return False

    if not stored_session_key or not session_key:
        return False

    return hmac.compare_digest(
        stored_session_key,
        session_key,
    )


def _build_analysis_key(
    analysis_id: str,
) -> str:
    """Construye la llave de un análisis."""
    return (
        f"{ANALYSIS_CACHE_PREFIX}"
        f"{analysis_id}"
    )


def _build_result_key(
    result_id: str,
) -> str:
    """Construye la llave de un documento."""
    return (
        f"{RESULT_CACHE_PREFIX}"
        f"{result_id}"
    )
    