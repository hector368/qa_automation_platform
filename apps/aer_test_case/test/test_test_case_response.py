"""Pruebas locales de los esquemas AER."""

from pydantic import ValidationError

from apps.aer_test_case.schemas.test_case_response import (
    AerTestCaseResponse,
)


def test_happy_path() -> None:
    """Valida un caso Happy Path con prioridad 1."""
    data = {
        "requirement_id": "MCC.015.050",
        "requirement_title": (
            "Realizar orquestación multi-instancia "
            "de UNIGIS"
        ),
        "is_testable": True,
        "not_testable_reason": None,
        "test_cases": [
            {
                "description": (
                    "Validate multi-instance "
                    "orchestration."
                ),
                "expected_result": (
                    "The orchestration finishes "
                    "successfully."
                ),
                "exception_text": None,
                "input": (
                    "CEDIS pending UNIGIS planning"
                ),
                "comments": None,
                "priority": 1,
            },
        ],
    }

    response = AerTestCaseResponse.model_validate(
        data
    )

    assert response.is_testable is True
    assert len(response.test_cases) == 1
    assert response.test_cases[0].priority == 1


def test_exception() -> None:
    """Valida un caso Exception con prioridad 2."""
    data = {
        "requirement_id": "MCC.015.050",
        "requirement_title": (
            "Realizar orquestación multi-instancia "
            "de UNIGIS"
        ),
        "is_testable": True,
        "not_testable_reason": None,
        "test_cases": [
            {
                "description": (
                    "Validate behavior when no "
                    "UNIGIS account is available."
                ),
                "expected_result": (
                    "The process waits until an "
                    "account becomes available."
                ),
                "exception_text": (
                    "No UNIGIS account is available."
                ),
                "input": (
                    "CEDIS pending UNIGIS planning"
                ),
                "comments": None,
                "priority": 2,
            },
        ],
    }

    response = AerTestCaseResponse.model_validate(
        data
    )

    assert response.test_cases[0].priority == 2
    assert (
        response.test_cases[0].exception_text
        is not None
    )


def test_invalid_priority() -> None:
    """Valida que solamente existan prioridades 1 y 2."""
    data = {
        "requirement_id": "MCC.015.001",
        "requirement_title": "Example",
        "is_testable": True,
        "not_testable_reason": None,
        "test_cases": [
            {
                "description": "Example",
                "fdd_reference": "MCC.015.001",
                "expected_result": "Expected result",
                "exception_text": None,
                "input": None,
                "comments": None,
                "priority": 3,
            },
        ],
    }

    try:
        AerTestCaseResponse.model_validate(
            data
        )
    except ValidationError:
        return

    raise AssertionError(
        "Priority 3 must be rejected."
    )


def test_exception_without_text() -> None:
    """Valida que una excepción incluya su condición."""
    data = {
        "requirement_id": "MCC.015.001",
        "requirement_title": "Example",
        "is_testable": True,
        "not_testable_reason": None,
        "test_cases": [
            {
                "description": "Exception example",
                "fdd_reference": "MCC.015.001",
                "expected_result": "Expected result",
                "exception_text": None,
                "input": None,
                "comments": None,
                "priority": 2,
            },
        ],
    }

    try:
        AerTestCaseResponse.model_validate(
            data
        )
    except ValidationError:
        return

    raise AssertionError(
        "Priority 2 without exception text "
        "must be rejected."
    )


def test_non_testable_requirement() -> None:
    """Valida un requerimiento no testeable."""
    data = {
        "requirement_id": "ABC.020.003",
        "requirement_title": "Pending definition",
        "is_testable": False,
        "not_testable_reason": (
            "No observable behavior is defined."
        ),
        "test_cases": [],
    }

    response = AerTestCaseResponse.model_validate(
        data
    )

    assert response.is_testable is False
    assert response.test_cases == []


def run_tests() -> None:
    """Ejecuta las pruebas locales del schema."""
    test_happy_path()
    test_exception()
    test_invalid_priority()
    test_exception_without_text()
    test_non_testable_requirement()

    print(
        "AER response schema tests: OK"
    )


if __name__ == "__main__":
    run_tests()
    