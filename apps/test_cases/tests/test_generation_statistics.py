from django.test import SimpleTestCase

from apps.test_cases.schemas.test_case_response import (
    RequirementTestCases,
)
from apps.test_cases.services.generation_statistics import (
    compute_generation_stats,
)


class GenerationStatisticsTests(SimpleTestCase):
    """Pruebas de estadísticas de generación."""

    def test_returns_zero_for_empty_results(
        self,
    ) -> None:
        """Devuelve métricas en cero sin resultados."""
        stats = compute_generation_stats(
            []
        )

        self.assertEqual(
            stats["requirements_total"],
            0,
        )

        self.assertEqual(
            stats["test_cases_total"],
            0,
        )

        self.assertEqual(
            stats["requirements_not_testable"],
            0,
        )

        self.assertEqual(
            stats["requirements"],
            [],
        )

        self.assertEqual(
            stats["requirement_details"],
            [],
        )

    def test_counts_requirements_and_test_cases(
        self,
    ) -> None:
        """Cuenta requerimientos y casos generados."""
        first = RequirementTestCases.model_validate(
            {
                "test_cases": [
                    self._build_test_case(),
                    self._build_test_case(),
                ],
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        second = RequirementTestCases.model_validate(
            {
                "test_cases": [
                    self._build_test_case(),
                ],
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        stats = compute_generation_stats(
            [
                (
                    1,
                    "Procesar archivo",
                    first,
                ),
                (
                    2,
                    "Validar información",
                    second,
                ),
            ]
        )

        self.assertEqual(
            stats["requirements_total"],
            2,
        )

        self.assertEqual(
            stats["test_cases_total"],
            3,
        )

        self.assertEqual(
            stats["requirements"],
            [1, 2],
        )

    def test_counts_not_testable_requirement(
        self,
    ) -> None:
        """Cuenta un no testeable como un TC de salida."""
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
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        stats = compute_generation_stats(
            [
                (
                    3,
                    "Validar proceso",
                    result,
                ),
            ]
        )

        self.assertEqual(
            stats["test_cases_total"],
            1,
        )

        self.assertEqual(
            stats["requirements_not_testable"],
            1,
        )

    def test_returns_requirement_detail(
        self,
    ) -> None:
        """Incluye el detalle individual del requerimiento."""
        result = RequirementTestCases.model_validate(
            {
                "test_cases": [
                    self._build_test_case(),
                ],
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        stats = compute_generation_stats(
            [
                (
                    5,
                    "Procesar información",
                    result,
                ),
            ]
        )

        details = stats[
            "requirement_details"
        ]

        self.assertEqual(
            details,
            [
                {
                    "requirement": 5,
                    "scenario_name": (
                        "Procesar información"
                    ),
                    "test_cases": 1,
                    "not_testable": False,
                    "requirement_review": {
                        "level": "adequate",
                        "reason": (
                            "El requerimiento representa "
                            "un único comportamiento funcional."
                        ),
                        "areas": [],
                        "functional_blocks": [],
                    },
                },
            ],
        )

    def test_returns_high_concentration_review(
        self,
    ) -> None:
        """Incluye una evaluación de alta concentración."""
        result = RequirementTestCases.model_validate(
            {
                "test_cases": [
                    self._build_test_case(),
                ],
                "requirement_review": (
                    self._build_requirement_review(
                        level="high_concentration",
                    )
                ),
            }
        )

        stats = compute_generation_stats(
            [
                (
                    6,
                    "Validar reglas",
                    result,
                ),
            ]
        )

        review = stats[
            "requirement_details"
        ][0]["requirement_review"]

        self.assertEqual(
            review["level"],
            "high_concentration",
        )

        self.assertEqual(
            review["areas"],
            [
                "Reglas de negocio",
            ],
        )

    def test_returns_saturated_review(
        self,
    ) -> None:
        """Incluye una evaluación funcional saturada."""
        result = RequirementTestCases.model_validate(
            {
                "test_cases": [
                    self._build_test_case(),
                ],
                "requirement_review": (
                    self._build_requirement_review(
                        level="saturated",
                    )
                ),
            }
        )

        stats = compute_generation_stats(
            [
                (
                    8,
                    "Realizar proceso",
                    result,
                ),
            ]
        )

        review = stats[
            "requirement_details"
        ][0]["requirement_review"]

        self.assertEqual(
            review["level"],
            "saturated",
        )

        self.assertEqual(
            review["functional_blocks"],
            [
                "Obtener información",
                "Procesar información",
            ],
        )

    def test_rejects_invalid_requirement_number(
        self,
    ) -> None:
        """Rechaza números de requerimiento inválidos."""
        result = RequirementTestCases.model_validate(
            {
                "test_cases": [
                    self._build_test_case(),
                ],
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        with self.assertRaises(
            ValueError,
        ):
            compute_generation_stats(
                [
                    (
                        0,
                        "Procesar información",
                        result,
                    ),
                ]
            )

    @staticmethod
    def _build_test_case() -> dict[str, object]:
        """Construye un caso válido para pruebas."""
        return {
            "classification": "happy_path",
            "objective": (
                "Que el bot procese la información."
            ),
            "expected_result": (
                "La información es procesada."
            ),
            "steps": [
                {
                    "action": (
                        "Validar que el bot procese "
                        "la información"
                    ),
                    "expected": (
                        "La información es procesada"
                    ),
                },
            ],
        }

    @staticmethod
    def _build_requirement_review(
        *,
        level: str = "adequate",
    ) -> dict[str, object]:
        """Construye una evaluación funcional válida."""
        if level == "high_concentration":
            return {
                "level": "high_concentration",
                "reason": (
                    "El requerimiento concentra varias "
                    "reglas relacionadas."
                ),
                "areas": [
                    "Reglas de negocio",
                ],
                "functional_blocks": [],
            }

        if level == "saturated":
            return {
                "level": "saturated",
                "reason": (
                    "El requerimiento agrupa varios "
                    "subprocesos independientes."
                ),
                "areas": [
                    "Subprocesos funcionales",
                ],
                "functional_blocks": [
                    "Obtener información",
                    "Procesar información",
                ],
            }

        return {
            "level": "adequate",
            "reason": (
                "El requerimiento representa un único "
                "comportamiento funcional."
            ),
            "areas": [],
            "functional_blocks": [],
        }