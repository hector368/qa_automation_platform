"""Utilidades comunes a las columnas de lista cerrada."""

from __future__ import annotations

from typing import Any


def build_choice_index(
    options: tuple[str, ...],
) -> dict[str, str]:
    """
    Relaciona cada opción con su escritura canónica.

    El índice conserva el orden en que se declararon las opciones,
    porque ese es el orden en que la interfaz las ofrece y el que
    aparece en los mensajes de error.
    """
    return {
        option.casefold(): option
        for option in options
    }


def normalize_choice(
    *,
    raw_value: Any,
    index: dict[str, str],
) -> str | None:
    """
    Devuelve la opción canónica, o None cuando viene vacía.

    Un valor vacío significa que la columna no se toca, para respetar
    lo que ya esté capturado en la matriz.

    Args:
        raw_value: Valor recibido de la interfaz o de Azure DevOps.
        index: Índice construido con build_choice_index.

    Returns:
        La opción con la escritura exacta que usa la matriz.

    Raises:
        ValueError: Cuando el valor no está en la lista.
    """
    clean_value = str(raw_value or "").strip()

    if not clean_value:
        return None

    canonical_value = index.get(clean_value.casefold())

    if canonical_value is None:
        raise ValueError(
            "must be one of: " + ", ".join(index.values()),
        )

    return canonical_value
