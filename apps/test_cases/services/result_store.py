"""
Almacenamiento temporal de resultados de generación.

El resultado generado se guarda en el caché y se asocia con la sesión que inició
la generación.
"""

from __future__ import annotations

import hmac
from typing import Any, Final

from django.core.cache import cache


CACHE_KEY_PREFIX: Final[str] = (
    "test_cases:generation_result:"
)


def save_generation_result(
    *,
    result_id: str,
    session_key: str,
    payload: dict[str, Any],
    timeout_seconds: int,
) -> None:
    """
    Guarda temporalmente un resultado.

    Args:
        result_id: Identificador aleatorio del resultado.
        session_key: Sesión propietaria.
        payload: Resultado completo de la generación.
        timeout_seconds: Tiempo de vida en segundos.

    Raises:
        ValueError: Cuando algún parámetro obligatorio es inválido.
    """
    clean_result_id = (result_id or "").strip()
    clean_session_key = (session_key or "").strip()

    if not clean_result_id:
        raise ValueError(
            "result_id no puede estar vacío."
        )

    if not clean_session_key:
        raise ValueError(
            "session_key no puede estar vacío."
        )

    if timeout_seconds <= 0:
        raise ValueError(
            "timeout_seconds debe ser mayor que cero."
        )

    cache.set(
        _build_cache_key(clean_result_id),
        {
            "session_key": clean_session_key,
            "payload": payload,
        },
        timeout=timeout_seconds,
    )


def load_generation_result(
    *,
    result_id: str,
    session_key: str,
) -> dict[str, Any] | None:
    """
    Recupera un resultado perteneciente a la misma sesión.

    Args:
        result_id: Identificador del resultado.
        session_key: Sesión solicitante.

    Returns:
        Payload almacenado o None cuando no existe, expiró o pertenece
        a otra sesión.
    """
    clean_result_id = (result_id or "").strip()
    clean_session_key = (session_key or "").strip()

    if not clean_result_id or not clean_session_key:
        return None

    stored_value = cache.get(
        _build_cache_key(clean_result_id)
    )

    if not isinstance(stored_value, dict):
        return None

    stored_session_key = str(
        stored_value.get("session_key")
        or ""
    )

    if not hmac.compare_digest(
        stored_session_key,
        clean_session_key,
    ):
        return None

    payload = stored_value.get("payload")

    if not isinstance(payload, dict):
        return None

    return payload


def _build_cache_key(result_id: str) -> str:
    """Construye la llave interna del caché."""
    return f"{CACHE_KEY_PREFIX}{result_id}"