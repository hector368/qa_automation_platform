"""Validación de la solicitud de generación AER."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

class AerGenerationRequest(BaseModel):
    """Representa la selección de generación AER."""

    model_config = ConfigDict(
        extra="forbid",
    )

    selected_requirement_ids: list[str] = Field(
        default_factory=list,
    )

    include_exceptions: bool = False

    @field_validator(
        "selected_requirement_ids",
    )
    @classmethod
    def validate_requirement_ids(
        cls,
        values: list[str],
    ) -> list[str]:
        """Limpia los IDs seleccionados."""
        cleaned_values: list[str] = []

        for value in values:
            clean_value = value.strip()

            if not clean_value:
                continue

            if clean_value not in cleaned_values:
                cleaned_values.append(
                    clean_value
                )

        return cleaned_values

    @model_validator(
        mode="after",
    )
    def validate_generation_selection(
        self,
    ) -> "AerGenerationRequest":
        """Valida que exista al menos una fuente de generación."""
        if (
            not self.selected_requirement_ids
            and not self.include_exceptions
        ):
            raise ValueError(
                "At least one requirement or "
                "FDD Exceptions must be selected."
            )

        return self

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