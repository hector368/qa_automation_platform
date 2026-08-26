"""Estructuras internas para requerimientos segmentados."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RequirementSegment:
    """Representa un requerimiento detectado en un PDD o FDD."""

    requirement_id: str
    title: str
    content: str