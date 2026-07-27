"""
Carga del prompt del generador de casos de prueba.

El prompt se encuentra dentro de la aplicación para que test_cases pueda
integrarse en otro proyecto Django sin depender de rutas globales.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from apps.test_cases.exceptions import PromptConfigurationError


APP_DIRECTORY: Final[Path] = (
    Path(__file__).resolve().parent.parent
)

DEFAULT_PROMPT_PATH: Final[Path] = (
    APP_DIRECTORY
    / "prompts"
    / "test_cases_prompt.txt"
)


def load_test_cases_prompt(
    prompt_path: Path | None = None,
) -> str:
    """
    Carga y valida el prompt de generación.

    Args:
        prompt_path: Ruta opcional usada principalmente en pruebas.

    Returns:
        Texto del prompt.

    Raises:
        PromptConfigurationError: Cuando el archivo no existe,
            no es un archivo regular o está vacío.
    """
    resolved_path = (
        prompt_path
        if prompt_path is not None
        else DEFAULT_PROMPT_PATH
    )

    if not resolved_path.is_file():
        raise PromptConfigurationError(
            f"No se encontró el prompt: {resolved_path}"
        )

    try:
        prompt_text = resolved_path.read_text(
            encoding="utf-8",
        ).strip()
    except OSError as exc:
        raise PromptConfigurationError(
            f"No fue posible leer el prompt: {resolved_path}"
        ) from exc

    if not prompt_text:
        raise PromptConfigurationError(
            f"El prompt está vacío: {resolved_path}"
        )

    return prompt_text