"""Construcción de la fila que alimenta la matriz MSP_QA."""

from __future__ import annotations

import logging
import re

from typing import Any, Final


logger = logging.getLogger(__name__)

NUMBER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(\d+(?:[.,]\d+)?)",
)

THOUSANDS_FRACTION_LENGTH: Final[int] = 3

PEOPLE_JOIN_SEPARATOR: Final[str] = " / "

CONSTANT_REPOSITORY: Final[str] = "Azure DevOps"

# Columnas de la matriz MSP_QA en el orden en que aparecen en el
# archivo de Google Sheets. El valor es la etiqueta de la columna.
COLUMN_LABELS: Final[dict[str, str]] = {
    "month": "MES",
    "tester": "TESTER",
    "client": "CLIENTE",
    "msp_id": "ID",
    "service_type": "TIPO DE SERVICIO",
    "repository": "REPOSITORIO",
    "status": "ESTATUS",
    "release_date": "FECHA LIBERACIÓN",
    "test_level": "NIVEL DE PRUEBA",
    "exception_releases": "LIBERACIONES POR EXCEPCIÓN",
    "technologies": "TECNOLOGÍAS",
    "developer": "DESARROLLADOR",
    "estimated_hours": "HORAS ESTIMADAS",
    "used_hours": "HORAS USADAS",
    "functional_test_cases": "CASOS DE PRUEBA FUNCIONALES",
    "uncovered_functional_test_cases": (
        "CASOS DE PRUEBA FUNCIONALES NO CUBIERTOS"
    ),
    "non_functional_test_cases": "CASOS DE PRUEBA NO FUNCIONALES",
    "valid_defects": "DEFECTOS VÁLIDOS",
    "unidentified_defects": "DEFECTOS NO IDENTIFICADOS",
}


def clean_text(raw_value: Any) -> str | None:
    """Devuelve el texto limpio, o None cuando viene vacío."""
    if raw_value is None:
        return None

    clean_value = str(raw_value).strip()

    return clean_value or None


def join_people(values: Any) -> str | None:
    """Une una lista de personas en el formato de la matriz."""
    if not values:
        return None

    if isinstance(values, str):
        return clean_text(values)

    joined_value = PEOPLE_JOIN_SEPARATOR.join(
        str(value).strip()
        for value in values
        if str(value).strip()
    )

    return joined_value or None


def extract_first_number(raw_value: Any) -> float | None:
    """
    Obtiene el primer número presente en un texto.

    Reconoce valores como "660", "354 Hrs" o "1,040", y distingue la
    coma decimal de la coma de millares por la cantidad de dígitos.
    """
    if raw_value is None:
        return None

    number_match = NUMBER_PATTERN.search(str(raw_value))

    if number_match is None:
        return None

    number_text = number_match.group(1)

    if "," in number_text:
        integer_part, _, fraction_part = number_text.partition(",")

        if len(fraction_part) == THOUSANDS_FRACTION_LENGTH:
            number_text = f"{integer_part}{fraction_part}"
        else:
            number_text = f"{integer_part}.{fraction_part}"

    try:
        return float(number_text)

    except ValueError:
        logger.warning(
            "No fue posible convertir '%s' en número.",
            raw_value,
        )

        return None


def normalize_number(value: float) -> float | int:
    """Redondea a dos decimales y devuelve entero cuando aplica."""
    rounded_value = round(value, 2)

    if rounded_value == int(rounded_value):
        return int(rounded_value)

    return rounded_value


def calculate_qa_hours(
    *,
    total_hours_text: Any,
    hours_ratio: float,
) -> float | int | None:
    """
    Calcula las horas estimadas de QA.

    La descripción del proyecto registra las horas totales de todos los
    roles. La matriz MSP_QA registra únicamente la porción de QA, que
    corresponde a un porcentaje configurable de ese total.
    """
    total_hours = extract_first_number(total_hours_text)

    if total_hours is None:
        return None

    return normalize_number(total_hours * hours_ratio)


def build_msp_row(
    *,
    msp_id: str,
    context: dict[str, Any],
    hours_ratio: float,
) -> dict[str, Any]:
    """
    Construye la fila de la matriz a partir del contexto extraído.

    Las columnas cuyo dato no proviene de la descripción del proyecto
    se devuelven vacías, para que el proceso de escritura respete lo
    que ya esté capturado en la matriz.

    Args:
        msp_id: Identificador de la fila, por ejemplo "AMK.009_S1".
        context: Datos extraídos del bloque de la descripción.
        hours_ratio: Proporción de horas de QA sobre el total.

    Returns:
        Diccionario con una entrada por columna de la matriz.
    """
    return {
        "month": None,
        "tester": join_people(context.get("tester")),
        "client": clean_text(context.get("client")),
        "msp_id": clean_text(msp_id),
        "service_type": clean_text(context.get("service_type")),
        "repository": CONSTANT_REPOSITORY,
        "status": None,
        "release_date": None,
        "test_level": None,
        "exception_releases": None,
        "technologies": None,
        "developer": join_people(context.get("developers")),
        "estimated_hours": calculate_qa_hours(
            total_hours_text=context.get("estimated_hours"),
            hours_ratio=hours_ratio,
        ),
        "used_hours": None,
        "functional_test_cases": None,
        "uncovered_functional_test_cases": None,
        "non_functional_test_cases": None,
        "valid_defects": None,
        "unidentified_defects": None,
    }


def list_empty_columns(row: dict[str, Any]) -> list[str]:
    """Enumera las etiquetas de las columnas que quedaron vacías."""
    return [
        COLUMN_LABELS[column_key]
        for column_key, value in row.items()
        if value is None and column_key in COLUMN_LABELS
    ]
