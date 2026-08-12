"""
Normalización segura de respuestas de casos de prueba.

Este módulo transforma variaciones conocidas del modelo en la
estructura interna validada. No crea ni completa información
funcional ausente.
"""

from __future__ import annotations

from typing import Final

from pydantic import ValidationError

from apps.test_cases.schemas.test_case_response import (
    RawNotTestableResult,
    RawRequirementResponse,
    RawRequirementReview,
    RawTestCase,
    RawTestStep,
    RequirementTestCases,
)


CLASSIFICATION_ALIASES: Final[dict[str, str]] = {
    "happy_path": "happy_path",
    "happy path": "happy_path",
    "happy-path": "happy_path",
    "happypath": "happy_path",
    "exception": "exception",
    "excepcion": "exception",
    "excepción": "exception",
}

REVIEW_LEVEL_ALIASES: Final[dict[str, str]] = {
    "adequate": "adequate",
    "high_concentration": "high_concentration",
    "high concentration": "high_concentration",
    "high-concentration": "high_concentration",
    "saturated": "saturated",
}


def normalize_requirement_response(
    raw_response: RawRequirementResponse,
) -> RequirementTestCases:
    """
    Normaliza y valida la respuesta funcional del modelo.

    Args:
        raw_response: Respuesta tolerante previamente validada.

    Returns:
        Respuesta interna normalizada y estricta.

    Raises:
        ValueError: Cuando falta información funcional obligatoria
            o existe una clasificación desconocida.
    """
    normalized_test_cases = [
        _normalize_test_case(test_case)
        for test_case in (
            raw_response.test_cases
            or []
        )
    ]

    normalized_not_testable = None

    if raw_response.not_testable is not None:
        normalized_not_testable = (
            _normalize_not_testable(
                raw_response.not_testable
            )
        )

    normalized_review = None

    if raw_response.requirement_review is not None:
        normalized_review = (
            _normalize_requirement_review(
                raw_response.requirement_review
            )
        )

    payload = {
        "test_cases": normalized_test_cases,
        "not_testable": normalized_not_testable,
        "requirement_review": normalized_review,
    }

    try:
        return RequirementTestCases.model_validate(
            payload
        )
    except ValidationError as exc:
        raise ValueError(
            "La respuesta del modelo no contiene "
            "información funcional suficiente."
        ) from exc


def _normalize_test_case(
    test_case: RawTestCase,
) -> dict[str, object]:
    """
    Normaliza un caso de prueba sin completar datos faltantes.

    Args:
        test_case: Caso recibido desde el modelo.

    Returns:
        Diccionario preparado para la validación estricta.

    Raises:
        ValueError: Cuando la clasificación no es reconocida.
    """
    classification = _normalize_classification(
        test_case.classification
    )

    preconditions = _normalize_text_list(
        test_case.preconditions
    )

    steps = [
        _normalize_test_step(step)
        for step in (
            test_case.steps
            or []
        )
    ]

    return {
        "classification": classification,
        "objective": _clean_text(
            test_case.objective
        ),
        "expected_result": _clean_text(
            test_case.expected_result
        ),
        "preconditions": preconditions,
        "steps": steps,
    }


def _normalize_test_step(
    step: RawTestStep,
) -> dict[str, str]:
    """
    Normaliza un paso sin generar contenido funcional.

    Args:
        step: Paso recibido desde el modelo.

    Returns:
        Paso con valores textuales normalizados.
    """
    return {
        "action": _clean_text(
            step.action
        ),
        "expected": _clean_text(
            step.expected
        ),
    }


def _normalize_not_testable(
    result: RawNotTestableResult,
) -> dict[str, str]:
    """
    Normaliza información de un requerimiento no testeable.

    Args:
        result: Información recibida desde el modelo.

    Returns:
        Diccionario preparado para validación estricta.
    """
    return {
        "objective": _clean_text(
            result.objective
        ),
        "reason": _clean_text(
            result.reason
        ),
        "missing_information": _clean_text(
            result.missing_information
        ),
        "required_definition": _clean_text(
            result.required_definition
        ),
    }


def _normalize_requirement_review(
    review: RawRequirementReview,
) -> dict[str, object]:
    """
    Normaliza la evaluación funcional del requerimiento.

    Args:
        review: Evaluación recibida desde el modelo.

    Returns:
        Evaluación preparada para validación estricta.

    Raises:
        ValueError: Cuando el nivel no es reconocido.
    """
    return {
        "level": _normalize_review_level(
            review.level
        ),
        "reason": _clean_text(
            review.reason
        ),
        "areas": _normalize_text_list(
            review.areas
        ),
        "functional_blocks": _normalize_text_list(
            review.functional_blocks
        ),
    }


def _normalize_classification(
    classification: str | None,
) -> str:
    """
    Convierte variantes conocidas a una clasificación interna.

    Args:
        classification: Clasificación recibida desde el modelo.

    Returns:
        Clasificación interna normalizada.

    Raises:
        ValueError: Cuando el valor está vacío o no es conocido.
    """
    clean_value = _clean_text(
        classification
    ).lower()

    normalized = CLASSIFICATION_ALIASES.get(
        clean_value
    )

    if normalized is None:
        raise ValueError(
            "La clasificación del caso de prueba "
            f"no es reconocida: {clean_value!r}."
        )

    return normalized


def _normalize_review_level(
    level: str | None,
) -> str:
    """
    Convierte variantes conocidas al nivel interno.

    Args:
        level: Nivel recibido desde el modelo.

    Returns:
        Nivel de evaluación normalizado.

    Raises:
        ValueError: Cuando el nivel está vacío o no es conocido.
    """
    clean_value = _clean_text(
        level
    ).lower()

    normalized = REVIEW_LEVEL_ALIASES.get(
        clean_value
    )

    if normalized is None:
        raise ValueError(
            "El nivel de evaluación del requerimiento "
            f"no es reconocido: {clean_value!r}."
        )

    return normalized


def _normalize_text_list(
    values: list[str] | str | None,
) -> list[str]:
    """
    Convierte un valor textual o lista en una lista limpia.

    Args:
        values: Valor recibido desde el modelo.

    Returns:
        Lista textual sin elementos vacíos.
    """
    if values is None:
        return []

    if isinstance(
        values,
        str,
    ):
        clean_value = _clean_text(
            values
        )

        return (
            [clean_value]
            if clean_value
            else []
        )

    return [
        clean_value
        for value in values
        if (
            clean_value := _clean_text(
                value
            )
        )
    ]


def _clean_text(
    value: str | None,
) -> str:
    """
    Limpia espacios exteriores de un valor textual.

    Args:
        value: Texto original.

    Returns:
        Texto limpio o cadena vacía.
    """
    return (
        value
        or ""
    ).strip()