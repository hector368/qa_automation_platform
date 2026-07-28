"""
Validación de los datos solicitados para generar casos de prueba.
"""

from __future__ import annotations

import re
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator


MAX_SELECTED_REQUIREMENTS: Final[int] = 400
MAX_ASSIGNED_TO_LENGTH: Final[int] = 150

_SELECTION_SEPARATOR_RE: Final[re.Pattern[str]] = re.compile(
    r"[,\s]+"
)

_SINGLE_NUMBER_RE: Final[re.Pattern[str]] = re.compile(
    r"^\d+$"
)

_NUMBER_RANGE_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<start>\d+)-(?P<end>\d+)$"
)


class GenerationRequest(BaseModel):
    """Datos validados para ejecutar una generación."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    assigned_to: str = Field(
        min_length=1,
        max_length=MAX_ASSIGNED_TO_LENGTH,
    )

    selected_requirements: list[int] | None = None

    @field_validator("selected_requirements")
    @classmethod
    def validate_selected_requirements(
        cls,
        value: list[int] | None,
    ) -> list[int] | None:
        """Valida, ordena y elimina duplicados."""
        if value is None:
            return None

        normalized = sorted(set(value))

        if not normalized:
            return None

        if any(number <= 0 for number in normalized):
            raise ValueError(
                "Los números de requerimiento deben ser positivos."
            )

        if len(normalized) > MAX_SELECTED_REQUIREMENTS:
            raise ValueError(
                "La selección supera el máximo permitido."
            )

        return normalized


def parse_selected_requirements(
    raw_value: str | None,
) -> list[int] | None:
    """
    Convierte valores como 1,2,5-8 en una lista ordenada.

    Args:
        raw_value: Selección enviada por el formulario.

    Returns:
        Lista ordenada o None cuando no existe selección.

    Raises:
        ValueError: Cuando el formato o tamaño no es válido.
    """
    clean_value = (raw_value or "").strip()

    if not clean_value:
        return None

    selected: set[int] = set()

    for part in _SELECTION_SEPARATOR_RE.split(clean_value):
        clean_part = part.strip()

        if not clean_part:
            continue

        range_match = _NUMBER_RANGE_RE.fullmatch(clean_part)

        if range_match:
            start = int(range_match.group("start"))
            end = int(range_match.group("end"))

            if start <= 0 or end <= 0:
                raise ValueError(
                    "Los requerimientos deben ser mayores que cero."
                )

            if start > end:
                start, end = end, start

            range_size = end - start + 1

            if range_size > MAX_SELECTED_REQUIREMENTS:
                raise ValueError(
                    "El rango de requerimientos es demasiado grande."
                )

            selected.update(
                range(start, end + 1)
            )

        elif _SINGLE_NUMBER_RE.fullmatch(clean_part):
            number = int(clean_part)

            if number <= 0:
                raise ValueError(
                    "Los requerimientos deben ser mayores que cero."
                )

            selected.add(number)

        else:
            raise ValueError(
                "La selección contiene un formato inválido."
            )

        if len(selected) > MAX_SELECTED_REQUIREMENTS:
            raise ValueError(
                "La selección supera el máximo permitido."
            )

    return sorted(selected) or None