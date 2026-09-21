"""Catálogo de tecnologías de la matriz MSP_QA."""

from __future__ import annotations

from typing import Any, Final

from apps.msp_qa.choices import build_choice_index, normalize_choice


# Campo de la fila que corresponde a la columna TECNOLOGÍAS.
TECHNOLOGY_FIELD: Final[str] = "technologies"

# Mismas opciones y mismo orden que la lista desplegable de la
# columna TECNOLOGÍAS en la matriz. La escritura va tal cual está
# capturada ahí, incluyendo las minúsculas de 'rocketbot' y los
# paréntesis de Power Automate: cualquier variación quedaría marcada
# como inválida en la hoja de cálculo.
TECHNOLOGY_OPTIONS: Final[tuple[str, ...]] = (
    "UiPath",
    "BluePrism",
    "Automation anywhere",
    "rocketbot",
    "NA",
    "Process Mining",
    "Power Automate (Cloud)",
    "Power Apps",
    "Power Automate (Desktop)",
    "Azure AI Document Intelligence",
    "Power BI",
    "Chatbot IA",
    "IA Gemini",
    "AI Builder",
    "Service Now",
)

TECHNOLOGY_INDEX: Final[dict[str, str]] = build_choice_index(
    TECHNOLOGY_OPTIONS,
)


def normalize_technology(raw_value: Any) -> str | None:
    """
    Devuelve la tecnología canónica, o None cuando viene vacía.

    Raises:
        ValueError: Cuando el valor no está en el catálogo.
    """
    return normalize_choice(
        raw_value=raw_value,
        index=TECHNOLOGY_INDEX,
    )
