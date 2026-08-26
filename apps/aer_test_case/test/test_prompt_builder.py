"""Pruebas locales del constructor del prompt AER."""

from apps.aer_test_case.schemas.requirement_schema import (
    RequirementSegment,
)
from apps.aer_test_case.services.prompt_builder import (
    build_requirement_prompt,
)
from apps.aer_test_case.services.prompt_loader import (
    load_aer_prompt,
)


def test_prompt_loading() -> None:
    """Valida que el archivo del prompt pueda cargarse."""
    prompt = load_aer_prompt()

    assert prompt
    assert "{{REQUIREMENT_ID}}" in prompt
    assert "{{REQUIREMENT_CONTENT}}" in prompt


def test_prompt_building() -> None:
    """Valida la construcción de un prompt individual."""
    requirement = RequirementSegment(
        requirement_id="MCC.015.050",
        title=(
            "Realizar orquestación "
            "multi-instancia de UNIGIS"
        ),
        content=(
            "MCC.015.050 Realizar orquestación "
            "multi-instancia de UNIGIS\n\n"
            "El BOT ejecuta múltiples instancias."
        ),
    )

    prompt = build_requirement_prompt(
        requirement
    )

    assert "MCC.015.050" in prompt

    assert (
        "Realizar orquestación "
        "multi-instancia de UNIGIS"
        in prompt
    )

    assert (
        "El BOT ejecuta múltiples instancias."
        in prompt
    )

    assert "{{REQUIREMENT_ID}}" not in prompt

    assert "{{REQUIREMENT_TITLE}}" not in prompt

    assert "{{REQUIREMENT_CONTENT}}" not in prompt

    assert "{{REFERENCED_REQUIREMENTS}}" not in prompt


def test_reference_context() -> None:
    """Valida la inclusión de requerimientos referenciados."""
    requirement = RequirementSegment(
        requirement_id="MCC.015.050",
        title="Orchestration",
        content=(
            "The process follows requirements "
            "34 to 49."
        ),
    )

    reference_context = (
        "MCC.015.034\n"
        "Referenced requirement content."
    )

    prompt = build_requirement_prompt(
        requirement=requirement,
        referenced_requirements=reference_context,
    )

    assert "MCC.015.034" in prompt

    assert (
        "Referenced requirement content."
        in prompt
    )


def test_default_reference_context() -> None:
    """Valida el contexto cuando no existen referencias."""
    requirement = RequirementSegment(
        requirement_id="ABC.001.001",
        title="Example",
        content="Example content.",
    )

    prompt = build_requirement_prompt(
        requirement
    )

    assert (
        "No referenced requirement content "
        "was provided."
        in prompt
    )


def run_tests() -> None:
    """Ejecuta las pruebas locales del prompt."""
    test_prompt_loading()
    test_prompt_building()
    test_reference_context()
    test_default_reference_context()

    print(
        "AER prompt builder tests: OK"
    )


if __name__ == "__main__":
    run_tests()