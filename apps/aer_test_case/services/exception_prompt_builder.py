"""Construcción del prompt de excepciones AER."""

from apps.aer_test_case.services.prompt_loader import (
    load_aer_exceptions_prompt,
)


EXCEPTIONS_CONTENT_TOKEN = (
    "{{EXCEPTIONS_CONTENT}}"
)


def build_exceptions_prompt(
    exceptions_text: str,
) -> str:
    """Construye el prompt con la sección de excepciones."""
    if not isinstance(exceptions_text, str):
        raise TypeError(
            "Exceptions text must be a string."
        )

    clean_exceptions_text = (
        exceptions_text.strip()
    )

    if not clean_exceptions_text:
        raise ValueError(
            "Exceptions text cannot be empty."
        )

    prompt_template = (
        load_aer_exceptions_prompt()
    )

    prompt = prompt_template.replace(
        EXCEPTIONS_CONTENT_TOKEN,
        clean_exceptions_text,
    )

    _validate_built_prompt(
        prompt
    )

    return prompt


def _validate_built_prompt(
    prompt: str,
) -> None:
    """Comprueba que no queden tokens sin reemplazar."""
    if EXCEPTIONS_CONTENT_TOKEN in prompt:
        raise ValueError(
            "Unresolved exceptions prompt token "
            "was detected."
        )