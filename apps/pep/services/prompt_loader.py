"""
Carga de prompts pertenecientes al generador PEP.

Las rutas se resuelven desde la propia aplicación para evitar
dependencias con la raíz del proyecto Django.
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


def load_pap_prompt(
    prompt_path: Path | None = None,
) -> str:
    """
    Carga el prompt utilizado para analizar el PAP.

    Args:
        prompt_path: Ruta opcional para pruebas.

    Returns:
        Texto del prompt sin espacios externos ni BOM.

    Raises:
        PromptConfigurationError: Cuando el archivo no existe,
            no puede leerse o está vacío.
    """
    resolved_path = (
        prompt_path
        if prompt_path is not None
        else PAP_PROMPT_PATH
    )

    if not resolved_path.is_file():
        raise PromptConfigurationError(
            f"No se encontró el prompt PAP: {resolved_path}"
        )

    try:
        prompt_text = resolved_path.read_text(
            encoding="utf-8-sig",
        ).strip()
    except OSError as exc:
        raise PromptConfigurationError(
            f"No fue posible leer el prompt PAP: "
            f"{resolved_path}"
        ) from exc

    if not prompt_text:
        raise PromptConfigurationError(
            f"El prompt PAP está vacío: {resolved_path}"
        )

    return prompt_text