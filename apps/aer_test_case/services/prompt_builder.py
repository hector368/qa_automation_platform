"""Construcción del prompt para cada requerimiento AER."""

from apps.aer_test_case.schemas.requirement_schema import (
    RequirementSegment,
)
from apps.aer_test_case.services.prompt_loader import (
    load_aer_prompt,
)


REQUIREMENT_ID_TOKEN = "{{REQUIREMENT_ID}}"
REQUIREMENT_TITLE_TOKEN = "{{REQUIREMENT_TITLE}}"
REQUIREMENT_CONTENT_TOKEN = "{{REQUIREMENT_CONTENT}}"

REFERENCED_REQUIREMENTS_TOKEN = (
    "{{REFERENCED_REQUIREMENTS}}"
)

NO_REFERENCED_REQUIREMENTS = (
    "No referenced requirement content was provided."
)


def build_requirement_prompt(
    requirement: RequirementSegment,
    referenced_requirements: str | None = None,
) -> str:
    """Construye el prompt final para un requerimiento."""
    prompt_template = load_aer_prompt()

    reference_context = (
        referenced_requirements.strip()
        if referenced_requirements
        else NO_REFERENCED_REQUIREMENTS
    )

    prompt = prompt_template.replace(
        REQUIREMENT_ID_TOKEN,
        requirement.requirement_id,
    )

    prompt = prompt.replace(
        REQUIREMENT_TITLE_TOKEN,
        requirement.title,
    )

    prompt = prompt.replace(
        REQUIREMENT_CONTENT_TOKEN,
        requirement.content,
    )

    prompt = prompt.replace(
        REFERENCED_REQUIREMENTS_TOKEN,
        reference_context,
    )

    _validate_built_prompt(prompt)

    return prompt


def _validate_built_prompt(
    prompt: str,
) -> None:
    """Comprueba que no queden tokens sin reemplazar."""
    unresolved_tokens = (
        REQUIREMENT_ID_TOKEN,
        REQUIREMENT_TITLE_TOKEN,
        REQUIREMENT_CONTENT_TOKEN,
        REFERENCED_REQUIREMENTS_TOKEN,
    )

    remaining_tokens = [
        token
        for token in unresolved_tokens
        if token in prompt
    ]

    if remaining_tokens:
        joined_tokens = ", ".join(
            remaining_tokens
        )

        raise ValueError(
            "Unresolved prompt tokens were detected: "
            f"{joined_tokens}."
        )