"""Pruebas locales del resolvedor de referencias AER."""

from apps.aer_test_case.schemas.requirement_schema import (
    RequirementSegment,
)
from apps.aer_test_case.services.reference_resolver import (
    build_reference_context,
)
from apps.aer_test_case.services.reference_resolver import (
    resolve_referenced_requirements,
)


def build_requirements() -> list[RequirementSegment]:
    """Construye requerimientos sintéticos para las pruebas."""
    return [
        RequirementSegment(
            requirement_id=f"MCC.015.{number:03d}",
            title=f"Requirement {number}",
            content=(
                f"MCC.015.{number:03d} "
                f"Requirement {number}\n"
                f"Content for requirement {number}."
            ),
        )
        for number in range(
            1,
            51,
        )
    ]


def test_single_reference() -> None:
    """Valida una referencia simple."""
    requirements = build_requirements()

    current_requirement = RequirementSegment(
        requirement_id="MCC.015.018",
        title="Current requirement",
        content=(
            "The delivery date follows "
            "the rule defined in REQ13."
        ),
    )

    references = resolve_referenced_requirements(
        current_requirement=current_requirement,
        requirements=requirements,
    )

    assert [
        requirement.requirement_id
        for requirement in references
    ] == [
        "MCC.015.013",
    ]


def test_reference_range() -> None:
    """Valida un rango completo de requerimientos."""
    requirements = build_requirements()

    current_requirement = RequirementSegment(
        requirement_id="MCC.015.050",
        title="Orchestration",
        content=(
            "Procesa las Jornadas siguiendo "
            "el flujo de RQ 34 a RQ 49."
        ),
    )

    references = resolve_referenced_requirements(
        current_requirement=current_requirement,
        requirements=requirements,
    )

    reference_ids = [
        requirement.requirement_id
        for requirement in references
    ]

    assert len(reference_ids) == 16

    assert reference_ids[0] == "MCC.015.034"
    assert reference_ids[-1] == "MCC.015.049"


def test_duplicate_reference() -> None:
    """Valida que una referencia repetida no se duplique."""
    requirements = build_requirements()

    current_requirement = RequirementSegment(
        requirement_id="MCC.015.050",
        title="Orchestration",
        content=(
            "Utiliza RQ49 y conserva el "
            "comportamiento definido en RQ 49."
        ),
    )

    references = resolve_referenced_requirements(
        current_requirement=current_requirement,
        requirements=requirements,
    )

    assert len(references) == 1

    assert (
        references[0].requirement_id
        == "MCC.015.049"
    )


def test_reference_context() -> None:
    """Valida la construcción del contexto textual."""
    requirements = build_requirements()

    references = [
        requirements[33],
        requirements[34],
    ]

    context = build_reference_context(
        references
    )

    assert context is not None
    assert "MCC.015.034" in context
    assert "MCC.015.035" in context
    assert "Content for requirement 34." in context


def run_tests() -> None:
    """Ejecuta las pruebas locales de referencias."""
    test_single_reference()
    test_reference_range()
    test_duplicate_reference()
    test_reference_context()

    print(
        "AER reference resolver tests: OK"
    )


if __name__ == "__main__":
    run_tests()