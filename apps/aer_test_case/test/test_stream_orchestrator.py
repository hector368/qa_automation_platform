"""Pruebas locales del progreso del orquestador AER."""

from __future__ import annotations

from unittest.mock import patch

from apps.aer_test_case.schemas.requirement_schema import (
    RequirementSegment,
)
from apps.aer_test_case.schemas.test_case_response import (
    AerTestCaseResponse,
)
from apps.aer_test_case.services.orchestrator import (
    PreparedAerDocument,
)
from apps.aer_test_case.services.orchestrator import (
    iter_generate_document,
)
from apps.aer_test_case.services.test_case_generator import (
    AerRequirementGeneration,
)
from apps.test_cases.services.token_usage import (
    TokenUsage,
)


def build_response(
    requirement_id: str,
    requirement_title: str,
) -> AerTestCaseResponse:
    """Construye una respuesta AER válida."""
    return AerTestCaseResponse.model_validate(
        {
            "requirement_id": requirement_id,
            "requirement_title": requirement_title,
            "is_testable": True,
            "not_testable_reason": None,
            "test_cases": [
                {
                    "description": (
                        "Precondiciones:\n"
                        "No especificadas.\n\n"
                        "Tipo de flujo:\n"
                        "Happy Path\n\n"
                        "Descripción:\n"
                        "Validar el comportamiento.\n\n"
                        "Pasos:\n"
                        "1. Iniciar el proceso."
                    ),
                    "expected_result": (
                        "El proceso finaliza."
                    ),
                    "exception_text": None,
                    "input": None,
                    "comments": None,
                    "priority": 1,
                },
            ],
        }
    )


def fake_generation(
    *,
    requirement: RequirementSegment,
    referenced_requirements: str | None = None,
) -> AerRequirementGeneration:
    """Simula la generación sin llamar a Claude."""
    del referenced_requirements

    return AerRequirementGeneration(
        response=build_response(
            requirement.requirement_id,
            requirement.title,
        ),
        usage=TokenUsage(
            input_tokens=100,
            output_tokens=50,
        ),
    )


def run_test() -> None:
    """Comprueba los eventos de progreso."""
    prepared_document = PreparedAerDocument(
        filename="sample.pdf",
        requirements=(
            RequirementSegment(
                requirement_id="MCC.015.001",
                title="First requirement",
                content=(
                    "MCC.015.001 First requirement"
                ),
            ),
            RequirementSegment(
                requirement_id="MCC.015.002",
                title="Second requirement",
                content=(
                    "MCC.015.002 Second requirement"
                ),
            ),
        ),
    )

    with patch(
        "apps.aer_test_case.services.orchestrator."
        "generate_requirement_test_cases",
        side_effect=fake_generation,
    ):
        events = list(
            iter_generate_document(
                prepared_document=prepared_document,
                selected_requirement_ids=[
                    "MCC.015.001",
                    "MCC.015.002",
                ],
            )
        )

    assert len(events) == 6

    assert events[0]["type"] == "started"

    assert (
        events[0]["total_requirements"]
        == 2
    )

    assert (
        events[1]["type"]
        == "requirement_started"
    )

    assert (
        events[2]["type"]
        == "requirement_completed"
    )

    assert (
        events[3]["type"]
        == "requirement_started"
    )

    assert (
        events[4]["type"]
        == "requirement_completed"
    )

    assert events[5]["type"] == "completed"

    assert events[5]["progress"] == 100

    generation = events[5][
        "generation"
    ]

    assert generation.total_test_cases == 2

    assert (
        generation.usage.input_tokens
        == 200
    )

    assert (
        generation.usage.output_tokens
        == 100
    )

    assert generation.xlsx_bytes

    print(
        "AER stream orchestrator test: OK"
    )


if __name__ == "__main__":
    run_test()