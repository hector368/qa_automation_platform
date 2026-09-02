"""Carga del prompt utilizado por el AER Test Case Generator."""

from pathlib import Path


PROMPT_FILE_NAME = "aer_test_cases_prompt.txt"

EXCEPTIONS_PROMPT_FILE_NAME = (
    "aer_exceptions_prompt.txt"
)

def load_aer_prompt() -> str:
    """Carga el prompt base del generador AER."""
    prompt_path = _get_prompt_path()

    if not prompt_path.is_file():
        raise FileNotFoundError(
            f"AER prompt file was not found: {prompt_path}"
        )

    prompt_text = prompt_path.read_text(
        encoding="utf-8",
    ).strip()

    if not prompt_text:
        raise ValueError(
            "AER prompt file is empty."
        )

    return prompt_text

def load_aer_exceptions_prompt() -> str:
    """Carga el prompt base para excepciones AER."""
    prompt_path = _get_prompt_path(
        EXCEPTIONS_PROMPT_FILE_NAME
    )

    if not prompt_path.is_file():
        raise FileNotFoundError(
            "AER exceptions prompt file was not found: "
            f"{prompt_path}"
        )

    prompt_text = prompt_path.read_text(
        encoding="utf-8",
    ).strip()

    if not prompt_text:
        raise ValueError(
            "AER exceptions prompt file is empty."
        )

    return prompt_text

def _get_prompt_path(
    prompt_file_name: str = PROMPT_FILE_NAME,
) -> Path:
    """Obtiene la ubicación absoluta de un prompt AER."""
    current_file = Path(__file__).resolve()

    app_directory = current_file.parent.parent

    return (
        app_directory
        / "prompts"
        / prompt_file_name
    )