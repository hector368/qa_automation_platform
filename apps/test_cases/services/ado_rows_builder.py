"""
Construcción de filas Azure DevOps desde casos de prueba validados.

Este módulo transforma el modelo funcional interno en filas de
quince columnas. No genera archivos de salida.
"""

from __future__ import annotations

from typing import Final

from apps.test_cases.schemas.test_case_response import (
    NotTestableResult,
    RequirementTestCases,
    TestCase,
)


ADO_COLUMNS: Final[tuple[str, ...]] = (
    "ID",
    "Work Item Type",
    "Title",
    "Test Step",
    "Step action",
    "Step Expected",
    "Type of test",
    "Priority",
    "Expected result",
    "Objetive",
    "Operating Scenario",
    "Preconditions",
    "State",
    "Area Path",
    "Assigned To",
)

ADO_NCOLS: Final[int] = len(
    ADO_COLUMNS
)

DEFAULT_STATE: Final[str] = "Design"
PRECONDITION_SEPARATOR: Final[str] = " • "


def build_ado_rows(
    *,
    result: RequirementTestCases,
    project_id: str,
    requirement_number: int,
    scenario_name: str,
    assigned_to: str,
    tc_start: int = 1,
) -> list[list[str]]:
    """
    Construye filas ADO desde un resultado funcional validado.

    Args:
        result: Casos de prueba validados.
        project_id: Identificador del proyecto.
        requirement_number: Número del requerimiento.
        scenario_name: Nombre del escenario.
        assigned_to: Usuario asignado en Azure DevOps.
        tc_start: Número inicial del caso de prueba.

    Returns:
        Filas de quince columnas listas para exportación.

    Raises:
        ValueError: Cuando los datos determinísticos son inválidos.
    """
    clean_project_id = (
        project_id
        or ""
    ).strip()

    clean_scenario_name = (
        scenario_name
        or ""
    ).strip()

    clean_assigned_to = (
        assigned_to
        or ""
    ).strip()

    if not clean_project_id:
        raise ValueError(
            "project_id no puede estar vacío."
        )

    if requirement_number <= 0:
        raise ValueError(
            "requirement_number debe ser mayor que cero."
        )

    if not clean_scenario_name:
        raise ValueError(
            "scenario_name no puede estar vacío."
        )

    if not clean_assigned_to:
        raise ValueError(
            "assigned_to no puede estar vacío."
        )

    if tc_start <= 0:
        raise ValueError(
            "tc_start debe ser mayor que cero."
        )

    if result.not_testable is not None:
        return [
            _build_not_testable_row(
                result=result.not_testable,
                project_id=clean_project_id,
                requirement_number=requirement_number,
                scenario_name=clean_scenario_name,
                assigned_to=clean_assigned_to,
                tc_number=tc_start,
            )
        ]

    rows: list[list[str]] = []

    for tc_number, test_case in enumerate(
        result.test_cases,
        start=tc_start,
    ):
        rows.extend(
            _build_test_case_rows(
                test_case=test_case,
                project_id=clean_project_id,
                requirement_number=requirement_number,
                scenario_name=clean_scenario_name,
                assigned_to=clean_assigned_to,
                tc_number=tc_number,
            )
        )

    return rows


def _build_test_case_rows(
    *,
    test_case: TestCase,
    project_id: str,
    requirement_number: int,
    scenario_name: str,
    assigned_to: str,
    tc_number: int,
) -> list[list[str]]:
    """Construye metadata y pasos de un caso de prueba."""
    metadata_row = _empty_row()

    metadata_row[1] = "Test Case"
    metadata_row[2] = _build_title(
        project_id=project_id,
        requirement_number=requirement_number,
        tc_number=tc_number,
    )

    metadata_row[6] = "Functional"
    metadata_row[7] = _get_priority(
        test_case.classification
    )
    metadata_row[8] = test_case.expected_result
    metadata_row[9] = test_case.objective
    metadata_row[10] = _build_operating_scenario(
        classification=test_case.classification,
        scenario_name=scenario_name,
    )
    metadata_row[11] = PRECONDITION_SEPARATOR.join(
        test_case.preconditions
    )
    metadata_row[12] = DEFAULT_STATE
    metadata_row[13] = project_id
    metadata_row[14] = assigned_to

    rows = [
        metadata_row,
    ]

    for step_number, step in enumerate(
        test_case.steps,
        start=1,
    ):
        step_row = _empty_row()

        step_row[3] = str(
            step_number
        )
        step_row[4] = step.action
        step_row[5] = step.expected

        rows.append(
            step_row
        )

    return rows


def _build_not_testable_row(
    *,
    result: NotTestableResult,
    project_id: str,
    requirement_number: int,
    scenario_name: str,
    assigned_to: str,
    tc_number: int,
) -> list[str]:
    """Construye la fila de un requerimiento no testeable."""
    row = _empty_row()

    row[1] = "Test Case"
    row[2] = _build_title(
        project_id=project_id,
        requirement_number=requirement_number,
        tc_number=tc_number,
    )
    row[6] = "Functional"
    row[7] = "2"
    row[8] = (
        f"(No testeable): {result.reason} | "
        f"Falta: {result.missing_information} | "
        "Para habilitar pruebas: "
        f"{result.required_definition}"
    )
    row[9] = result.objective
    row[10] = (
        f"(Excepción) - {scenario_name}"
    )
    row[11] = (
        f"(No testeable): {result.reason}"
    )
    row[12] = DEFAULT_STATE
    row[13] = project_id
    row[14] = assigned_to

    return row


def _build_title(
    *,
    project_id: str,
    requirement_number: int,
    tc_number: int,
) -> str:
    """Construye el título determinístico del caso."""
    return (
        f"{project_id}."
        f"{requirement_number:03d}."
        f"{tc_number:03d}"
    )


def _get_priority(
    classification: str,
) -> str:
    """Obtiene la prioridad a partir de la clasificación."""
    if classification == "happy_path":
        return "1"

    return "2"


def _build_operating_scenario(
    *,
    classification: str,
    scenario_name: str,
) -> str:
    """Construye el escenario operativo determinístico."""
    if classification == "happy_path":
        prefix = "Happy Path"
    else:
        prefix = "Excepción"

    return (
        f"({prefix}) - {scenario_name}"
    )


def _empty_row() -> list[str]:
    """Crea una fila ADO vacía."""
    return [
        ""
        for _ in range(
            ADO_NCOLS
        )
    ]