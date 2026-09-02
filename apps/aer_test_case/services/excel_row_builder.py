"""Construcción de filas para el Excel AER."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from apps.aer_test_case.schemas.exception_response import (
    AerExceptionsPayload,
)
from apps.aer_test_case.schemas.test_case_response import (
    AerTestCaseResponse,
)


DEFAULT_TEST_STATUS = "Not Tested"


@dataclass(frozen=True, slots=True)
class AerExcelRow:
    """Representa una fila del archivo Excel AER."""

    scenario_id: int
    description: str
    fdd_reference: str
    expected_result: str
    exception_text: str | None
    input_value: str | None
    comments: str | None
    test_status: str
    date_when_tested: str | None
    priority: int
    tester: str | None
    associated_bug: str | None


def build_excel_rows(
    responses: Sequence[AerTestCaseResponse],
    exceptions_payload: AerExceptionsPayload | None = None,
) -> list[AerExcelRow]:
    """Convierte respuestas AER en filas para Excel."""
    rows: list[AerExcelRow] = []

    scenario_id = 1

    for response in responses:
        if not response.is_testable:
            continue

        for test_case in response.test_cases:
            rows.append(
                AerExcelRow(
                    scenario_id=scenario_id,
                    description=test_case.description,
                    fdd_reference=_build_fdd_reference(
                        response
                    ),
                    expected_result=(
                        test_case.expected_result
                    ),
                    exception_text=(
                        test_case.exception_text
                        or "N/A"
                    ),
                    input_value=(
                        test_case.input
                        or "N/A"
                    ),
                    comments=(
                        test_case.comments
                        or "N/A"
                    ),
                    test_status=DEFAULT_TEST_STATUS,
                    date_when_tested=None,
                    priority=test_case.priority,
                    tester=None,
                    associated_bug=None,
                )
            )

            scenario_id += 1

    if exceptions_payload is not None:
        for exception in exceptions_payload.exceptions:
            for test_case in exception.test_cases:
                rows.append(
                    AerExcelRow(
                        scenario_id=scenario_id,
                        description=test_case.description,
                        fdd_reference=(
                            _build_exception_reference(
                                exception.exception_id,
                                exception.exception_name,
                            )
                        ),
                        expected_result=(
                            test_case.expected_result
                        ),
                        exception_text=(
                            test_case.exception_text
                            or "N/A"
                        ),
                        input_value=(
                            test_case.input
                            or "N/A"
                        ),
                        comments=(
                            test_case.comments
                            or "N/A"
                        ),
                        test_status=DEFAULT_TEST_STATUS,
                        date_when_tested=None,
                        priority=test_case.priority,
                        tester=None,
                        associated_bug=None,
                    )
                )

                scenario_id += 1

    return rows


def _build_fdd_reference(
    response: AerTestCaseResponse,
) -> str:
    """Construye la referencia trazable del requerimiento."""
    return (
        "Referencia al requerimiento: "
        f"{response.requirement_id} - "
        f"{response.requirement_title}"
    )


def _build_exception_reference(
    exception_id: str,
    exception_name: str,
) -> str:
    """Construye la referencia trazable de una excepción."""
    return (
        "Referencia a excepción: "
        f"{exception_id} - "
        f"{exception_name}"
    )