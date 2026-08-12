from django.test import SimpleTestCase

from apps.test_cases.schemas.test_case_response import (
    RequirementTestCases,
)
from apps.test_cases.services.ado_rows_builder import (
    ADO_NCOLS,
    build_ado_rows,
)


class AdoRowsBuilderTests(SimpleTestCase):
    """Pruebas para la construcción de filas ADO."""

    def test_builds_happy_path_rows(
        self,
    ) -> None:
        """Construye metadata y pasos de Happy Path."""
        result = RequirementTestCases.model_validate(
            {
                "test_cases": [
                    {
                        "classification": "happy_path",
                        "objective": (
                            "Que el bot procese el archivo."
                        ),
                        "expected_result": (
                            "El archivo es procesado."
                        ),
                        "preconditions": [
                            "Archivo disponible",
                        ],
                        "steps": [
                            {
                                "action": (
                                    "Validar que el bot obtenga "
                                    "el archivo"
                                ),
                                "expected": (
                                    "El archivo está disponible"
                                ),
                            },
                            {
                                "action": (
                                    "Validar que el bot procese "
                                    "el archivo"
                                ),
                                "expected": (
                                    "El archivo es procesado"
                                ),
                            },
                        ],
                    },
                ],
            }
        )

        rows = build_ado_rows(
            result=result,
            project_id="CFC.003",
            requirement_number=1,
            scenario_name="Procesar archivo",
            assigned_to="Usuario QA",
        )

        self.assertEqual(
            len(rows),
            3,
        )

        self.assertTrue(
            all(
                len(row) == ADO_NCOLS
                for row in rows
            )
        )

        self.assertEqual(
            rows[0][2],
            "CFC.003.001.001",
        )

        self.assertEqual(
            rows[0][6],
            "Functional",
        )

        self.assertEqual(
            rows[0][7],
            "1",
        )

        self.assertEqual(
            rows[0][10],
            "(Happy Path) - Procesar archivo",
        )

        self.assertEqual(
            rows[1][3],
            "1",
        )

        self.assertEqual(
            rows[2][3],
            "2",
        )

    def test_builds_exception_metadata(
        self,
    ) -> None:
        """Asigna prioridad y escenario de excepción."""
        result = RequirementTestCases.model_validate(
            {
                "test_cases": [
                    {
                        "classification": "exception",
                        "objective": (
                            "Que el bot rechace el archivo."
                        ),
                        "expected_result": (
                            "El archivo es rechazado."
                        ),
                        "steps": [
                            {
                                "action": (
                                    "Validar que el bot revise "
                                    "el archivo"
                                ),
                                "expected": (
                                    "El archivo es rechazado"
                                ),
                            },
                        ],
                    },
                ],
            }
        )

        rows = build_ado_rows(
            result=result,
            project_id="CFC.003",
            requirement_number=2,
            scenario_name="Validar archivo",
            assigned_to="Usuario QA",
        )

        self.assertEqual(
            rows[0][7],
            "2",
        )

        self.assertEqual(
            rows[0][10],
            "(Excepción) - Validar archivo",
        )

    def test_numbers_multiple_test_cases(
        self,
    ) -> None:
        """Numera consecutivamente los casos del requerimiento."""
        test_case = {
            "classification": "happy_path",
            "objective": (
                "Que el bot procese información."
            ),
            "expected_result": (
                "La información es procesada."
            ),
            "steps": [
                {
                    "action": (
                        "Validar que el bot procese "
                        "información"
                    ),
                    "expected": (
                        "La información es procesada"
                    ),
                },
            ],
        }

        result = RequirementTestCases.model_validate(
            {
                "test_cases": [
                    test_case,
                    test_case,
                ],
            }
        )

        rows = build_ado_rows(
            result=result,
            project_id="ABC.001",
            requirement_number=5,
            scenario_name="Procesar información",
            assigned_to="Usuario QA",
        )

        metadata_rows = [
            row
            for row in rows
            if row[1] == "Test Case"
        ]

        self.assertEqual(
            metadata_rows[0][2],
            "ABC.001.005.001",
        )

        self.assertEqual(
            metadata_rows[1][2],
            "ABC.001.005.002",
        )

    def test_builds_not_testable_row(
        self,
    ) -> None:
        """Construye un requerimiento no testeable."""
        result = RequirementTestCases.model_validate(
            {
                "not_testable": {
                    "objective": (
                        "Que el bot procese el requerimiento "
                        "cuando exista información suficiente."
                    ),
                    "reason": (
                        "No existe comportamiento verificable."
                    ),
                    "missing_information": (
                        "Resultado esperado."
                    ),
                    "required_definition": (
                        "Definir el resultado esperado."
                    ),
                },
            }
        )

        rows = build_ado_rows(
            result=result,
            project_id="ABC.001",
            requirement_number=3,
            scenario_name="Validar información",
            assigned_to="Usuario QA",
        )

        self.assertEqual(
            len(rows),
            1,
        )

        self.assertEqual(
            rows[0][7],
            "2",
        )

        self.assertTrue(
            rows[0][8].startswith(
                "(No testeable):"
            )
        )

        self.assertEqual(
            rows[0][10],
            "(Excepción) - Validar información",
        )

    def test_sets_backend_managed_fields(
        self,
    ) -> None:
        """Completa campos controlados por Python."""
        result = RequirementTestCases.model_validate(
            {
                "test_cases": [
                    {
                        "classification": "happy_path",
                        "objective": (
                            "Que el bot procese datos."
                        ),
                        "expected_result": (
                            "Los datos son procesados."
                        ),
                        "steps": [
                            {
                                "action": (
                                    "Validar que el bot procese "
                                    "los datos"
                                ),
                                "expected": (
                                    "Los datos son procesados"
                                ),
                            },
                        ],
                    },
                ],
            }
        )

        rows = build_ado_rows(
            result=result,
            project_id="ABC.001",
            requirement_number=1,
            scenario_name="Procesar datos",
            assigned_to="Usuario QA",
        )

        self.assertEqual(
            rows[0][12],
            "Design",
        )

        self.assertEqual(
            rows[0][13],
            "ABC.001",
        )

        self.assertEqual(
            rows[0][14],
            "Usuario QA",
        )