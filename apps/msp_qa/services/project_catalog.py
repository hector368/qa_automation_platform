"""Consulta del catálogo de proyectos de Azure DevOps."""

from __future__ import annotations

import logging
import urllib.parse

from typing import Final

from apps.msp_qa.exceptions import ProjectNotFoundError
from apps.msp_qa.services.azure_client import request_json


logger = logging.getLogger(__name__)

MAX_PROJECTS: Final[int] = 1000


def list_projects() -> list[dict[str, object]]:
    """
    Obtiene los proyectos visibles con el token configurado.

    Un token solo alcanza los proyectos a los que tiene acceso la
    cuenta que lo generó, por lo que esta lista puede ser menor que
    el total de proyectos de la organización.

    Returns:
        Lista de proyectos ordenada por nombre.
    """
    payload = request_json(
        path="_apis/projects",
        query={
            "$top": str(MAX_PROJECTS),
            "stateFilter": "all",
        },
    )

    raw_projects = payload.get("value") or []

    projects = [
        {
            "name": str(project.get("name") or "").strip(),
            "state": str(project.get("state") or "").strip(),
            "has_description": bool(
                str(project.get("description") or "").strip(),
            ),
        }
        for project in raw_projects
        if isinstance(project, dict)
    ]

    named_projects = [
        project
        for project in projects
        if project["name"]
    ]

    logger.info(
        "Se obtuvieron %s proyectos visibles en Azure DevOps.",
        len(named_projects),
    )

    return sorted(
        named_projects,
        key=lambda project: str(project["name"]),
    )


def get_project_description(project_name: str) -> str:
    """
    Obtiene el campo de descripción de un proyecto.

    Args:
        project_name: Nombre del proyecto en Azure DevOps.

    Returns:
        Texto de la descripción, o cadena vacía si no tiene.

    Raises:
        ProjectNotFoundError: Cuando no se recibe el nombre.
    """
    clean_name = (project_name or "").strip()

    if not clean_name:
        raise ProjectNotFoundError(
            "No se recibió el nombre del proyecto.",
        )

    encoded_name = urllib.parse.quote(clean_name, safe="")

    payload = request_json(
        path=f"_apis/projects/{encoded_name}",
    )

    return str(payload.get("description") or "").strip()
