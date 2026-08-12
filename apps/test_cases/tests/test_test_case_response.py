from django.test import SimpleTestCase
from pydantic import ValidationError

from apps.test_cases.schemas.test_case_response import (
    RawRequirementResponse,
    RequirementTestCases,
)


class TestCaseResponseTests(SimpleTestCase):
    """Pruebas de los modelos de respuesta de generación."""

    def test_raw_response_accepts_minor_variations(
        self,
    ) -> None:
        """Acepta variaciones que serán normalizadas después."""
        payload = {
            "test_cases": [
                {
                    "classification": "Happy Path",
                    "objective": (
                        "Que el bot procese el archivo."
                    ),
                    "expected_result": (
                        "El archivo se procesa correctamente."
                    ),
                    "preconditions": (
                        "El archivo está disponible"
                    ),
                    "steps": [
                        {
                            "action": (
                                "Validar que el bot obtenga "
                                "el archivo"
                            ),
                            "expected": (
                                "El archivo queda disponible"
                            ),
                        },
                    ],
                },
            ],
            "requirement_review": {
                "level": "Adequate",
                "reason": (
                    "El requerimiento representa "
                    "un único comportamiento."
                ),
                "areas": None,
                "functional_blocks": None,
            },
        }

        result = RawRequirementResponse.model_validate(
            payload
        )

        self.assertIsNotNone(
            result.test_cases
        )

        self.assertEqual(
            result.test_cases[0].classification,
            "Happy Path",
        )

        self.assertEqual(
            result.test_cases[0].preconditions,
            "El archivo está disponible",
        )

        self.assertIsNotNone(
            result.requirement_review
        )

        self.assertEqual(
            result.requirement_review.level,
            "Adequate",
        )

    def test_raw_response_ignores_extra_fields(
        self,
    ) -> None:
        """Ignora propiedades desconocidas en la respuesta RAW."""
        payload = {
            "test_cases": [],
            "unexpected_field": "valor",
        }

        result = RawRequirementResponse.model_validate(
            payload
        )

        self.assertEqual(
            result.test_cases,
            [],
        )

    def test_validated_response_accepts_test_cases(
        self,
    ) -> None:
        """Acepta un resultado interno correctamente normalizado."""
        payload = {
            "test_cases": [
                self._build_test_case(),
            ],
            "requirement_review": (
                self._build_requirement_review()
            ),
        }

        result = RequirementTestCases.model_validate(
            payload
        )

        self.assertEqual(
            len(result.test_cases),
            1,
        )

        self.assertEqual(
            result.test_cases[0].classification,
            "happy_path",
        )

        self.assertEqual(
            result.requirement_review.level,
            "adequate",
        )

    def test_validated_response_accepts_not_testable(
        self,
    ) -> None:
        """Acepta un requerimiento explícitamente no testeable."""
        payload = {
            "not_testable": {
                "objective": (
                    "Que el bot procese el requerimiento "
                    "cuando exista información suficiente."
                ),
                "reason": (
                    "No existe comportamiento verificable."
                ),
                "missing_information": (
                    "Resultado esperado del proceso."
                ),
                "required_definition": (
                    "Definir el comportamiento esperado."
                ),
            },
            "requirement_review": (
                self._build_requirement_review()
            ),
        }

        result = RequirementTestCases.model_validate(
            payload
        )

        self.assertEqual(
            result.test_cases,
            [],
        )

        self.assertIsNotNone(
            result.not_testable
        )

        self.assertEqual(
            result.requirement_review.level,
            "adequate",
        )

    def test_accepts_adequate_requirement_review(
        self,
    ) -> None:
        """Acepta una evaluación funcional adecuada."""
        payload = {
            "test_cases": [
                self._build_test_case(),
            ],
            "requirement_review": (
                self._build_requirement_review()
            ),
        }

        result = RequirementTestCases.model_validate(
            payload
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

    def test_accepts_high_concentration_review(
        self,
    ) -> None:
        """Acepta una evaluación con alta concentración."""
        payload = {
            "test_cases": [
                self._build_test_case(),
            ],
            "requirement_review": (
                self._build_requirement_review(
                    level="high_concentration",
                )
            ),
        }

        result = RequirementTestCases.model_validate(
            payload
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

    def test_accepts_saturated_review(
        self,
    ) -> None:
        """Acepta una evaluación funcional saturada."""
        payload = {
            "test_cases": [
                self._build_test_case(),
            ],
            "requirement_review": (
                self._build_requirement_review(
                    level="saturated",
                )
            ),
        }

        result = RequirementTestCases.model_validate(
            payload
        )

        self.assertEqual(
            result.requirement_review.level,
            "saturated",
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
        """Rechaza clasificaciones no soportadas."""
        payload = {
            "test_cases": [
                self._build_test_case(
                    classification="positive",
                ),
            ],
            "requirement_review": (
                self._build_requirement_review()
            ),
        }

        with self.assertRaises(
            ValidationError,
        ):
            RequirementTestCases.model_validate(
                payload
            )

    def test_rejects_empty_required_text(
        self,
    ) -> None:
        """Rechaza campos funcionales obligatorios vacíos."""
        payload = {
            "test_cases": [
                self._build_test_case(
                    objective="",
                ),
            ],
            "requirement_review": (
                self._build_requirement_review()
            ),
        }

        with self.assertRaises(
            ValidationError,
        ):
            RequirementTestCases.model_validate(
                payload
            )

    def test_rejects_test_cases_and_not_testable(
        self,
    ) -> None:
        """Impide devolver dos tipos de resultado simultáneamente."""
        payload = {
            "test_cases": [
                self._build_test_case(
                    classification="exception",
                ),
            ],
            "not_testable": {
                "objective": (
                    "Que el bot procese el requerimiento."
                ),
                "reason": (
                    "No existe criterio verificable."
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

        with self.assertRaises(
            ValidationError,
        ):
            RequirementTestCases.model_validate(
                payload
            )

    def test_rejects_empty_result(
        self,
    ) -> None:
        """Rechaza respuestas sin resultado funcional."""
        payload = {
            "requirement_review": (
                self._build_requirement_review()
            ),
        }

        with self.assertRaises(
            ValidationError,
        ):
            RequirementTestCases.model_validate(
                payload
            )

    def test_rejects_missing_requirement_review(
        self,
    ) -> None:
        """Rechaza resultados sin evaluación del requerimiento."""
        payload = {
            "test_cases": [
                self._build_test_case(),
            ],
        }

        with self.assertRaises(
            ValidationError,
        ):
            RequirementTestCases.model_validate(
                payload
            )

    def test_rejects_unknown_requirement_review_level(
        self,
    ) -> None:
        """Rechaza niveles de evaluación no soportados."""
        payload = {
            "test_cases": [
                self._build_test_case(),
            ],
            "requirement_review": {
                "level": "critical",
                "reason": (
                    "El requerimiento presenta "
                    "una clasificación desconocida."
                ),
                "areas": [],
                "functional_blocks": [],
            },
        }

        with self.assertRaises(
            ValidationError,
        ):
            RequirementTestCases.model_validate(
                payload
            )

    def test_rejects_high_concentration_without_areas(
        self,
    ) -> None:
        """Rechaza alta concentración sin áreas identificadas."""
        payload = {
            "test_cases": [
                self._build_test_case(),
            ],
            "requirement_review": {
                "level": "high_concentration",
                "reason": (
                    "El requerimiento concentra "
                    "varias reglas relacionadas."
                ),
                "areas": [],
                "functional_blocks": [],
            },
        }

        with self.assertRaises(
            ValidationError,
        ):
            RequirementTestCases.model_validate(
                payload
            )

    def test_rejects_saturated_review_without_areas(
        self,
    ) -> None:
        """Rechaza saturación sin áreas identificadas."""
        payload = {
            "test_cases": [
                self._build_test_case(),
            ],
            "requirement_review": {
                "level": "saturated",
                "reason": (
                    "El requerimiento agrupa "
                    "varios subprocesos."
                ),
                "areas": [],
                "functional_blocks": [
                    "Obtener información",
                ],
            },
        }

        with self.assertRaises(
            ValidationError,
        ):
            RequirementTestCases.model_validate(
                payload
            )

    def test_rejects_saturated_review_without_blocks(
        self,
    ) -> None:
        """Rechaza saturación sin bloques funcionales."""
        payload = {
            "test_cases": [
                self._build_test_case(),
            ],
            "requirement_review": {
                "level": "saturated",
                "reason": (
                    "El requerimiento agrupa "
                    "varios subprocesos."
                ),
                "areas": [
                    "Subprocesos funcionales",
                ],
                "functional_blocks": [],
            },
        }

        with self.assertRaises(
            ValidationError,
        ):
            RequirementTestCases.model_validate(
                payload
            )

    @staticmethod
    def _build_test_case(
        *,
        classification: str = "happy_path",
        objective: str = "Que el bot procese el archivo.",
    ) -> dict[str, object]:
        """Construye un caso de prueba para las pruebas."""
        return {
            "classification": classification,
            "objective": objective,
            "expected_result": (
                "El archivo se procesa correctamente."
            ),
            "preconditions": [
                "El archivo está disponible",
            ],
            "steps": [
                {
                    "action": (
                        "Validar que el bot obtenga "
                        "el archivo"
                    ),
                    "expected": (
                        "El archivo queda disponible"
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