"""
Carga y validación de la plantilla DOCX del generador PEP.

La plantilla se resuelve desde la propia aplicación para mantenerla
independiente de la estructura raíz del proyecto Django.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from apps.pep.exceptions import PepTemplateError


APP_DIRECTORY: Final[Path] = (
    Path(__file__).resolve().parent.parent
)

PEP_TEMPLATE_PATH: Final[Path] = (
    APP_DIRECTORY
    / "resources"
    / "pep_templates"
    / "pep_template.docx"
)


@dataclass(frozen=True, slots=True)
class PepTemplateInfo:
    """Información de la plantilla PEP validada."""

    path: Path
    filename: str
    size_bytes: int


def get_pep_template_path() -> Path:
    """Devuelve la ruta de la plantilla integrada."""
    return PEP_TEMPLATE_PATH


def validate_pep_template(
    template_path: Path | None = None,
) -> PepTemplateInfo:
    """
    Valida que la plantilla exista y sea un DOCX no vacío.

    Args:
        template_path: Ruta alternativa utilizada principalmente
            en pruebas.

    Returns:
        Información de la plantilla validada.

    Raises:
        PepTemplateError: Cuando la plantilla no es utilizable.
    """
    resolved_path = (
        template_path
        if template_path is not None
        else get_pep_template_path()
    )

    if not resolved_path.exists():
        raise PepTemplateError(
            f"No se encontró la plantilla PEP: "
            f"{resolved_path}"
        )

    if not resolved_path.is_file():
        raise PepTemplateError(
            f"La ruta de plantilla no es un archivo: "
            f"{resolved_path}"
        )

    if resolved_path.suffix.lower() != ".docx":
        raise PepTemplateError(
            "La plantilla PEP debe tener extensión .docx."
        )

    try:
        size_bytes = resolved_path.stat().st_size
    except OSError as exc:
        raise PepTemplateError(
            f"No fue posible consultar la plantilla: "
            f"{resolved_path}"
        ) from exc

    if size_bytes <= 0:
        raise PepTemplateError(
            f"La plantilla PEP está vacía: "
            f"{resolved_path}"
        )

    return PepTemplateInfo(
        path=resolved_path,
        filename=resolved_path.name,
        size_bytes=size_bytes,
    )


def read_pep_template_bytes(
    template_path: Path | None = None,
) -> bytes:
    """
    Lee la plantilla integrada como contenido binario.

    Args:
        template_path: Ruta alternativa utilizada en pruebas.

    Returns:
        Contenido binario de la plantilla.

    Raises:
        PepTemplateError: Cuando no puede leerse.
    """
    template_info = validate_pep_template(
        template_path
    )

    try:
        template_bytes = template_info.path.read_bytes()
    except OSError as exc:
        raise PepTemplateError(
            f"No fue posible leer la plantilla PEP: "
            f"{template_info.path}"
        ) from exc

    if not template_bytes:
        raise PepTemplateError(
            "La plantilla PEP no contiene datos."
        )

    return template_bytes