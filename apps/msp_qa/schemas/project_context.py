"""Esquemas de validación del contexto extraído de un proyecto."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UnmappedLabel(BaseModel):
    """Etiqueta encontrada que no corresponde a un campo conocido."""

    model_config = ConfigDict(extra="forbid")

    label: str
    value: str


class ProjectBlockContext(BaseModel):
    """Datos extraídos de un bloque de la descripción del proyecto."""

    model_config = ConfigDict(extra="forbid")

    project_name: str | None = None
    client: str | None = None
    delivery_manager: list[str] = Field(default_factory=list)
    scrum_master: list[str] = Field(default_factory=list)
    business_analyst: list[str] = Field(default_factory=list)
    architect: list[str] = Field(default_factory=list)
    technical_lead: list[str] = Field(default_factory=list)
    developers: list[str] = Field(default_factory=list)
    tester: list[str] = Field(default_factory=list)
    code_reviewer: list[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    duration: str | None = None
    sprint_count: str | None = None
    service_type: str | None = None
    estimated_hours: str | None = None
    developer_roles: dict[str, list[str]] = Field(
        default_factory=dict,
    )
    unmapped_labels: list[UnmappedLabel] = Field(
        default_factory=list,
    )
    missing_fields: list[str] = Field(default_factory=list)


def validate_block_context(
    payload: dict[str, object],
) -> ProjectBlockContext:
    """
    Valida el diccionario extraído contra el esquema.

    Args:
        payload: Datos producidos por el parser de la descripción.

    Returns:
        Modelo validado del contexto del bloque.
    """
    return ProjectBlockContext.model_validate(payload)
