"""
Extracción de respuestas JSON generadas por el modelo.

Este módulo localiza y decodifica un objeto JSON dentro de la
respuesta textual del modelo. No modifica información funcional.
"""

from __future__ import annotations

import json
from typing import Any


def extract_json_object(
    text: str,
) -> dict[str, Any]:
    """
    Extrae un objeto JSON desde la respuesta del modelo.

    Tolera una respuesta JSON limpia, bloques Markdown y texto
    accidental antes o después del objeto.

    Args:
        text: Respuesta textual recibida desde el modelo.

    Returns:
        Objeto JSON decodificado como diccionario.

    Raises:
        ValueError: Cuando la respuesta está vacía, contiene un
            JSON de tipo incorrecto o no contiene un objeto JSON
            válido.
    """
    cleaned = _remove_code_fences(
        text
    )
    cleaned = (
        cleaned
        or ""
    ).lstrip("\ufeff").strip()

    if not cleaned:
        raise ValueError(
            "La respuesta del modelo está vacía."
        )

    try:
        parsed = json.loads(
            cleaned
        )
    except json.JSONDecodeError:
        return _find_embedded_json_object(
            cleaned
        )

    if not isinstance(
        parsed,
        dict,
    ):
        raise ValueError(
            "La respuesta debe contener un objeto JSON."
        )

    return parsed


def _find_embedded_json_object(
    text: str,
) -> dict[str, Any]:
    """
    Busca el primer objeto JSON válido dentro de un texto.

    Args:
        text: Texto que puede contener contenido adicional.

    Returns:
        Primer objeto JSON válido encontrado.

    Raises:
        ValueError: Cuando no se encuentra un objeto JSON válido.
    """
    decoder = json.JSONDecoder()

    for index, character in enumerate(
        text
    ):
        if character != "{":
            continue

        try:
            parsed, _ = decoder.raw_decode(
                text[index:]
            )
        except json.JSONDecodeError:
            continue

        if isinstance(
            parsed,
            dict,
        ):
            return parsed

    raise ValueError(
        "No fue posible encontrar un objeto JSON válido "
        "en la respuesta del modelo."
    )


def _remove_code_fences(
    text: str,
) -> str:
    """
    Elimina líneas de apertura y cierre de bloques Markdown.

    Args:
        text: Texto potencialmente envuelto en fences.

    Returns:
        Texto sin marcadores Markdown.
    """
    lines: list[str] = []

    for line in (
        text
        or ""
    ).splitlines():
        stripped = line.strip()

        if stripped.startswith(
            "```"
        ):
            continue

        lines.append(
            line
        )

    return "\n".join(
        lines
    ).strip()