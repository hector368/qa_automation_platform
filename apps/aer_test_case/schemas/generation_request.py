"""Validación de la solicitud de generación AER."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


class AerGenerationRequest(BaseModel):
    """Representa los requerimientos seleccionados por el usuario."""

    model_config = ConfigDict(
        extra="forbid",
    )

    selected_requirement_ids: list[str] = Field(
        min_length=1,
    )

    @field_validator(
        "selected_requirement_ids",
    )
    @classmethod
    def validate_requirement_ids(
        cls,
        values: list[str],
    ) -> list[str]:
        """Limpia y valida los IDs seleccionados."""
        cleaned_values: list[str] = []

        for value in values:
            clean_value = value.strip()

            if not clean_value:
                continue

            if clean_value not in cleaned_values:
                cleaned_values.append(
                    clean_value
                )

        if not cleaned_values:
            raise ValueError(
                "At least one requirement must be selected."
            )

        return cleaned_values


def parse_selected_requirement_ids(
    raw_value: str | None,
) -> list[str]:
    """Convierte una cadena CSV en una lista de IDs."""
    if raw_value is None:
        return []

    return [
        value.strip()
        for value in raw_value.split(",")
        if value.strip()
    ]