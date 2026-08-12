"""
Cliente de Claude exclusivo del generador PEP.

Este módulo encapsula la comunicación con Anthropic y no contiene
reglas de análisis PAP/PDD ni generación DOCX.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import anthropic
from anthropic import Anthropic
from django.conf import settings

from apps.pep.exceptions import (
    ClaudeConfigurationError,
    ClaudeRequestError,
    ClaudeResponseError,
)
from apps.pep.services.token_usage import TokenUsage


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClaudeResult:
    """Resultado normalizado de una llamada a Claude."""

    text: str
    usage: TokenUsage


def get_client() -> Anthropic:
    """
    Construye el cliente de Anthropic.

    Returns:
        Cliente configurado.

    Raises:
        ClaudeConfigurationError: Cuando falta la API key.
    """
    api_key = str(
        getattr(
            settings,
            "ANTHROPIC_API_KEY",
            "",
        )
        or ""
    ).strip()

    if not api_key:
        raise ClaudeConfigurationError(
            "ANTHROPIC_API_KEY no está configurada."
        )

    timeout_seconds = float(
        getattr(
            settings,
            "CLAUDE_TIMEOUT_SECONDS",
            120,
        )
    )

    return Anthropic(
        api_key=api_key,
        timeout=timeout_seconds,
        max_retries=0,
    )


def call_claude(
    *,
    system_prompt: str,
    user_text: str,
    model: str | None = None,
    max_tokens: int | None = None,
) -> ClaudeResult:
    """
    Realiza una llamada a Claude sin reintentos automáticos.

    Args:
        system_prompt: Instrucciones del sistema.
        user_text: Contenido funcional enviado al modelo.
        model: Modelo opcional. Usa settings cuando no se proporciona.
        max_tokens: Límite opcional de salida.

    Returns:
        Texto y métricas de uso.

    Raises:
        ClaudeConfigurationError: Cuando falta configuración.
        ClaudeRequestError: Cuando Anthropic rechaza la solicitud.
        ClaudeResponseError: Cuando no existe texto de salida.
    """
    clean_system_prompt = (
        system_prompt or ""
    ).strip()

    clean_user_text = (
        user_text or ""
    ).strip()

    resolved_model = (
        model
        or getattr(
            settings,
            "CLAUDE_MODEL",
            "",
        )
        or ""
    ).strip()

    resolved_max_tokens = int(
        max_tokens
        or getattr(
            settings,
            "MAX_TOKENS",
            0,
        )
    )

    _validate_request_configuration(
        system_prompt=clean_system_prompt,
        user_text=clean_user_text,
        model=resolved_model,
        max_tokens=resolved_max_tokens,
    )

    logger.info(
        "Enviando solicitud a Claude: "
        "model=%s system_chars=%s user_chars=%s",
        resolved_model,
        len(clean_system_prompt),
        len(clean_user_text),
    )

    client = get_client()

    try:
        response = client.messages.create(
            model=resolved_model,
            max_tokens=resolved_max_tokens,
            temperature=0,
            system=clean_system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": clean_user_text,
                }
            ],
        )
    except anthropic.APIError as exc:
        status_code = getattr(
            exc,
            "status_code",
            None,
        )

        logger.exception(
            "Falló la solicitud a Claude. status=%s",
            status_code,
        )

        raise ClaudeRequestError(
            "Anthropic API error. "
            f"status={status_code}, "
            f"type={type(exc).__name__}."
        ) from exc

    response_text = _join_text_blocks(
        response.content
    )

    if not response_text:
        raise ClaudeResponseError(
            "Claude respondió sin bloques de texto."
        )

    usage = TokenUsage.from_anthropic(
        response.usage
    )

    logger.info(
        "Respuesta de Claude recibida: "
        "input_tokens=%s output_tokens=%s",
        usage.input_tokens,
        usage.output_tokens,
    )

    return ClaudeResult(
        text=response_text,
        usage=usage,
    )


def _validate_request_configuration(
    *,
    system_prompt: str,
    user_text: str,
    model: str,
    max_tokens: int,
) -> None:
    """
    Valida los parámetros antes de consumir la API.

    Raises:
        ClaudeConfigurationError: Cuando algún valor no es válido.
    """
    if not system_prompt:
        raise ClaudeConfigurationError(
            "El system prompt está vacío."
        )

    if not user_text:
        raise ClaudeConfigurationError(
            "El contenido del usuario está vacío."
        )

    if not model:
        raise ClaudeConfigurationError(
            "CLAUDE_MODEL no está configurado."
        )

    if max_tokens <= 0:
        raise ClaudeConfigurationError(
            "MAX_TOKENS debe ser mayor que cero."
        )


def _join_text_blocks(
    content: Any,
) -> str:
    """
    Une los bloques textuales devueltos por Anthropic.

    Args:
        content: Colección de bloques de respuesta.

    Returns:
        Texto consolidado.
    """
    parts: list[str] = []

    for block in content or []:
        text = getattr(
            block,
            "text",
            None,
        )

        if isinstance(text, str) and text.strip():
            parts.append(text.strip())

    return "\n".join(parts).strip()