"""Esquema de validación de la fila de la matriz MSP_QA."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from apps.msp_qa.statuses import normalize_status


class MspRow(BaseModel):
    """Representa una fila de la matriz MSP_QA.

    Cada atributo corresponde a una columna del archivo. El valor None
    indica que el dato no proviene de la descripción del proyecto y
    debe permanecer vacío.
    """

    model_config = ConfigDict(extra="forbid")

    month: str | None = None
    tester: str | None = None
    client: str | None = None
    msp_id: str | None = None
    service_type: str | None = None
    repository: str | None = None
    status: str | None = None
    release_date: str | None = None
    test_level: str | None = None
    exception_releases: str | None = None
    technologies: str | None = None
    developer: str | None = None
    estimated_hours: int | float | None = None
    used_hours: int | float | None = None
    functional_test_cases: int | None = None
    uncovered_functional_test_cases: int | None = None
    non_functional_test_cases: int | None = None
    valid_defects: int | None = None
    unidentified_defects: int | None = None

    @field_validator("status")
    @classmethod
    def check_status(cls, raw_value: str | None) -> str | None:
        """Acepta solo los estatus que la matriz tiene definidos."""
        return normalize_status(raw_value)


def validate_msp_row(payload: dict[str, object]) -> MspRow:
    """
    Valida la fila construida contra el esquema de la matriz.

    Args:
        payload: Fila producida por el constructor de filas.

    Returns:
        Modelo validado de la fila.
    """
    return MspRow.model_validate(payload)
