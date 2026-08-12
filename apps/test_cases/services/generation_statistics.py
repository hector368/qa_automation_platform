"""
Cálculo de estadísticas de generación de casos de prueba.

Este módulo obtiene métricas y evaluaciones funcionales directamente
desde los resultados validados de cada requerimiento.
"""

from __future__ import annotations

from collections.abc import Sequence

from apps.test_cases.schemas.test_case_response import (
    RequirementTestCases,
)


def compute_generation_stats(
    results: Sequence[
        tuple[int, str, RequirementTestCases]
    ],
) -> dict[str, object]:
    """
    Calcula estadísticas desde resultados funcionales.

    Args:
        results: Resultados asociados a número y escenario
            del requerimiento.

    Returns:
        Estadísticas y evaluaciones para la interfaz.

    Raises:
        ValueError: Cuando un número de requerimiento es inválido.
    """
    requirements: list[int] = []
    requirement_details: list[
        dict[str, object]
    ] = []

    test_cases_total = 0
    not_testable_total = 0

    for (
        requirement_number,
        scenario_name,
        result,
    ) in results:
        if requirement_number <= 0:
            raise ValueError(
                "requirement_number debe ser mayor que cero."
            )

        is_not_testable = (
            result.not_testable is not None
        )

        if is_not_testable:
            test_case_count = 1
            not_testable_total += 1
        else:
            test_case_count = len(
                result.test_cases
            )

        test_cases_total += test_case_count

        requirements.append(
            requirement_number
        )

        requirement_details.append(
            {
                "requirement": requirement_number,
                "scenario_name": scenario_name,
                "test_cases": test_case_count,
                "not_testable": is_not_testable,
                "requirement_review": (
                    result.requirement_review.model_dump()
                ),
            }
        )

    return {
        "requirements_total": len(results),
        "test_cases_total": test_cases_total,
        "requirements_not_testable": (
            not_testable_total
        ),
        "requirements": requirements,
        "requirement_details": requirement_details,
    }