"""
Carga de prompts pertenecientes al generador PEP.

Los archivos se resuelven desde la propia aplicación para mantener
independencia respecto a la raíz del proyecto Django.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from apps.pep.exceptions import PromptConfigurationError


APP_DIRECTORY: Final[Path] = (
    Path(__file__).resolve().parent.parent
)

PAP_PROMPT_PATH: Final[Path] = (
    APP_DIRECTORY
    / "prompts"
    / "pap_prompt.txt"
)

PDD_PROMPT_PATH: Final[Path] = (
    APP_DIRECTORY
    / "prompts"
    / "pdd_prompt.txt"
)


def load_pap_prompt(
    prompt_path: Path | None = None,
) -> str:
    """Carga el prompt utilizado para analizar el PAP."""
    return _load_prompt(
        prompt_path=prompt_path,
        default_path=PAP_PROMPT_PATH,
        prompt_name="PAP",
    )


def load_pdd_prompt(
    prompt_path: Path | None = None,
) -> str:
    """Carga el prompt utilizado para analizar el PDD/FDD."""
    return _load_prompt(
        prompt_path=prompt_path,
        default_path=PDD_PROMPT_PATH,
        prompt_name="PDD/FDD",
    )


def _load_prompt(
    *,
    prompt_path: Path | None,
    default_path: Path,
    prompt_name: str,
) -> str:
    """
    Carga y valida un prompt de la aplicación.

    Args:
        prompt_path: Ruta opcional utilizada en pruebas.
        default_path: Ruta predeterminada de la aplicación.
        prompt_name: Nombre utilizado en mensajes internos.

    Returns:
        Contenido del prompt sin BOM ni espacios externos.

    Raises:
        PromptConfigurationError: Cuando el archivo no está disponible.
    """
    resolved_path = (
        prompt_path
        if prompt_path is not None
        else default_path
    )

    if not resolved_path.is_file():
        raise PromptConfigurationError(
            f"No se encontró el prompt {prompt_name}: "
            f"{resolved_path}"
        )

    try:
        prompt_text = resolved_path.read_text(
            encoding="utf-8-sig",
        ).strip()
    except OSError as exc:
        raise PromptConfigurationError(
            f"No fue posible leer el prompt {prompt_name}: "
            f"{resolved_path}"
        ) from exc

    if not prompt_text:
        raise PromptConfigurationError(
            f"El prompt {prompt_name} está vacío: "
            f"{resolved_path}"
        )

    return prompt_text