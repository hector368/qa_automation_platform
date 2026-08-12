from django.test import SimpleTestCase

from apps.test_cases.schemas.test_case_response import (
    RawRequirementResponse,
)
from apps.test_cases.services.test_case_normalizer import (
    normalize_requirement_response,
)


class TestCaseNormalizerTests(SimpleTestCase):
    """Pruebas para la normalización de respuestas."""

    def test_normalizes_happy_path(
        self,
    ) -> None:
        """Normaliza una variante textual de Happy Path."""
        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    self._build_test_case(
                        classification="Happy Path",
                    ),
                ],
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        result = normalize_requirement_response(
            raw_response
        )

        self.assertEqual(
            result.test_cases[0].classification,
            "happy_path",
        )

    def test_normalizes_exception(
        self,
    ) -> None:
        """Normaliza la clasificación Excepción."""
        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    self._build_test_case(
                        classification="Excepción",
                    ),
                ],
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        result = normalize_requirement_response(
            raw_response
        )

        self.assertEqual(
            result.test_cases[0].classification,
            "exception",
        )

    def test_converts_string_precondition_to_list(
        self,
    ) -> None:
        """Convierte una precondición textual a lista."""
        test_case = self._build_test_case()

        test_case["preconditions"] = (
            "El archivo está disponible"
        )

        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    test_case,
                ],
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        result = normalize_requirement_response(
            raw_response
        )

        self.assertEqual(
            result.test_cases[0].preconditions,
            [
                "El archivo está disponible",
            ],
        )

    def test_converts_null_preconditions_to_empty_list(
        self,
    ) -> None:
        """Convierte precondiciones nulas a una lista vacía."""
        test_case = self._build_test_case()

        test_case["preconditions"] = None

        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    test_case,
                ],
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        result = normalize_requirement_response(
            raw_response
        )

        self.assertEqual(
            result.test_cases[0].preconditions,
            [],
        )

    def test_removes_empty_preconditions(
        self,
    ) -> None:
        """Elimina precondiciones vacías sin inventar contenido."""
        test_case = self._build_test_case()

        test_case["preconditions"] = [
            " Archivo disponible ",
            "",
            " Usuario autenticado ",
        ]

        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    test_case,
                ],
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        result = normalize_requirement_response(
            raw_response
        )

        self.assertEqual(
            result.test_cases[0].preconditions,
            [
                "Archivo disponible",
                "Usuario autenticado",
            ],
        )

    def test_normalizes_not_testable(
        self,
    ) -> None:
        """Normaliza un resultado no testeable válido."""
        raw_response = RawRequirementResponse.model_validate(
            {
                "not_testable": {
                    "objective": (
                        " Que el bot procese el requerimiento "
                        "cuando exista información suficiente. "
                    ),
                    "reason": (
                        " No existe comportamiento verificable. "
                    ),
                    "missing_information": (
                        " Resultado esperado. "
                    ),
                    "required_definition": (
                        " Definir el resultado esperado. "
                    ),
                },
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        result = normalize_requirement_response(
            raw_response
        )

        self.assertIsNotNone(
            result.not_testable
        )

        self.assertEqual(
            result.not_testable.reason,
            "No existe comportamiento verificable.",
        )

    def test_normalizes_adequate_review(
        self,
    ) -> None:
        """Normaliza una evaluación adequate."""
        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    self._build_test_case(),
                ],
                "requirement_review": {
                    "level": " Adequate ",
                    "reason": (
                        " Requerimiento funcional coherente. "
                    ),
                    "areas": None,
                    "functional_blocks": None,
                },
            }
        )

        result = normalize_requirement_response(
            raw_response
        )

        self.assertEqual(
            result.requirement_review.level,
            "adequate",
        )

        self.assertEqual(
            result.requirement_review.areas,
            [],
        )

        self.assertEqual(
            result.requirement_review.functional_blocks,
            [],
        )

    def test_normalizes_high_concentration_review(
        self,
    ) -> None:
        """Normaliza una evaluación de alta concentración."""
        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    self._build_test_case(),
                ],
                "requirement_review": {
                    "level": "High Concentration",
                    "reason": (
                        " Concentra varias reglas relacionadas. "
                    ),
                    "areas": (
                        " Reglas de negocio "
                    ),
                    "functional_blocks": None,
                },
            }
        )

        result = normalize_requirement_response(
            raw_response
        )

        self.assertEqual(
            result.requirement_review.level,
            "high_concentration",
        )

        self.assertEqual(
            result.requirement_review.areas,
            [
                "Reglas de negocio",
            ],
        )

        self.assertEqual(
            result.requirement_review.functional_blocks,
            [],
        )

    def test_normalizes_saturated_review(
        self,
    ) -> None:
        """Normaliza una evaluación saturated."""
        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    self._build_test_case(),
                ],
                "requirement_review": {
                    "level": "Saturated",
                    "reason": (
                        " Agrupa subprocesos independientes. "
                    ),
                    "areas": [
                        " Subprocesos funcionales ",
                        "",
                    ],
                    "functional_blocks": [
                        " Obtener información ",
                        "",
                        " Procesar información ",
                    ],
                },
            }
        )

        result = normalize_requirement_response(
            raw_response
        )

        self.assertEqual(
            result.requirement_review.level,
            "saturated",
        )

        self.assertEqual(
            result.requirement_review.areas,
            [
                "Subprocesos funcionales",
            ],
        )

        self.assertEqual(
            result.requirement_review.functional_blocks,
            [
                "Obtener información",
                "Procesar información",
            ],
        )

    def test_rejects_unknown_classification(
        self,
    ) -> None:
        """No deduce clasificaciones desconocidas."""
        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    self._build_test_case(
                        classification="positive",
                    ),
                ],
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        with self.assertRaises(
            ValueError,
        ):
            normalize_requirement_response(
                raw_response
            )

    def test_rejects_unknown_review_level(
        self,
    ) -> None:
        """No deduce niveles de evaluación desconocidos."""
        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    self._build_test_case(),
                ],
                "requirement_review": {
                    "level": "critical",
                    "reason": (
                        "Clasificación desconocida."
                    ),
                    "areas": [],
                    "functional_blocks": [],
                },
            }
        )

        with self.assertRaises(
            ValueError,
        ):
            normalize_requirement_response(
                raw_response
            )

    def test_rejects_missing_objective(
        self,
    ) -> None:
        """No crea un objetivo cuando Claude lo omite."""
        test_case = self._build_test_case()

        test_case["objective"] = None

        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    test_case,
                ],
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        with self.assertRaises(
            ValueError,
        ):
            normalize_requirement_response(
                raw_response
            )

    def test_rejects_step_without_action(
        self,
    ) -> None:
        """No crea una acción faltante en un paso."""
        test_case = self._build_test_case()

        test_case["steps"] = [
            {
                "action": "",
                "expected": (
                    "Los datos son procesados"
                ),
            },
        ]

        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    test_case,
                ],
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        with self.assertRaises(
            ValueError,
        ):
            normalize_requirement_response(
                raw_response
            )

    def test_rejects_missing_requirement_review(
        self,
    ) -> None:
        """No completa una evaluación funcional ausente."""
        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    self._build_test_case(),
                ],
            }
        )

        with self.assertRaises(
            ValueError,
        ):
            normalize_requirement_response(
                raw_response
            )

    def test_rejects_saturated_without_blocks(
        self,
    ) -> None:
        """No acepta saturación sin bloques funcionales."""
        raw_response = RawRequirementResponse.model_validate(
            {
                "test_cases": [
                    self._build_test_case(),
                ],
                "requirement_review": {
                    "level": "saturated",
                    "reason": (
                        "Agrupa varios subprocesos."
                    ),
                    "areas": [
                        "Subprocesos funcionales",
                    ],
                    "functional_blocks": [],
                },
            }
        )

        with self.assertRaises(
            ValueError,
        ):
            normalize_requirement_response(
                raw_response
            )

    def test_rejects_empty_response(
        self,
    ) -> None:
        """Rechaza respuestas sin resultado funcional."""
        raw_response = RawRequirementResponse.model_validate(
            {
                "requirement_review": (
                    self._build_requirement_review()
                ),
            }
        )

        with self.assertRaises(
            ValueError,
        ):
            normalize_requirement_response(
                raw_response
            )

    @staticmethod
    def _build_test_case(
        *,
        classification: str = "happy_path",
    ) -> dict[str, object]:
        """Construye un caso RAW válido para pruebas."""
        return {
            "classification": classification,
            "objective": (
                "Que el bot procese el archivo."
            ),
            "expected_result": (
                "El archivo es procesado."
            ),
            "preconditions": [],
            "steps": [
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
        }

    @staticmethod
    def _build_requirement_review() -> dict[str, object]:
        """Construye una evaluación RAW válida para pruebas."""
        return {
            "level": "adequate",
            "reason": (
                "El requerimiento representa un único "
                "comportamiento funcional."
            ),
            "areas": [],
            "functional_blocks": [],
        }