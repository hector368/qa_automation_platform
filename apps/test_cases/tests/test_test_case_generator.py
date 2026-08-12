import json
from io import BytesIO
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.test import override_settings
from openpyxl import load_workbook

from apps.test_cases.exceptions import (
    JsonGenerationError,
)
from apps.test_cases.services.claude_client import (
    ClaudeResult,
)
from apps.test_cases.services.requirement_splitter import (
    RequirementBlock,
)
from apps.test_cases.services.test_case_generator import (
    generate_test_cases,
)
from apps.test_cases.services.token_usage import (
    TokenUsage,
)


class TestCaseGeneratorTests(SimpleTestCase):
    """Pruebas del generador basado en JSON."""

    @override_settings(
        CLAUDE_INPUT_USD_PER_MTOK=0,
        CLAUDE_OUTPUT_USD_PER_MTOK=0,
    )
    @patch(
        "apps.test_cases.services."
        "test_case_generator.load_test_cases_prompt",
        return_value="Prompt de prueba",
    )
    @patch(
        "apps.test_cases.services."
        "test_case_generator.call_claude"
    )
    def test_generates_valid_xlsx(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        """Genera un XLSX desde una respuesta JSON válida."""
        call_claude_mock.return_value = ClaudeResult(
            text=self._build_valid_json(),
            usage=TokenUsage(
                input_tokens=100,
                output_tokens=50,
            ),
        )

        result = generate_test_cases(
            original_filename="CFC.003_PDD.pdf",
            project_id="CFC.003",
            context_text="Sistema: SAP",
            blocks=[
                RequirementBlock(
                    requirement_number=1,
                    scenario_name="Validar archivo",
                    input_text=(
                        "Descripción general: "
                        "Validar el archivo."
                    ),
                ),
            ],
            assigned_to="Usuario QA",
        )

        self.assertEqual(
            result["filename"],
            "CFC.003_PDD_TC.xlsx",
        )

        self.assertIn(
            "xlsx_bytes",
            result,
        )

        workbook = load_workbook(
            BytesIO(
                result["xlsx_bytes"]
            ),
            read_only=True,
        )

        worksheet = workbook[
            "Test Cases"
        ]

        self.assertEqual(
            worksheet["C2"].value,
            "CFC.003.001.001",
        )

        workbook.close()

        self.assertEqual(
            result["usage"]["input_tokens"],
            100,
        )

        self.assertEqual(
            call_claude_mock.call_count,
            1,
        )

    @override_settings(
        CLAUDE_INPUT_USD_PER_MTOK=0,
        CLAUDE_OUTPUT_USD_PER_MTOK=0,
    )
    @patch(
        "apps.test_cases.services."
        "test_case_generator.load_test_cases_prompt",
        return_value="Prompt de prueba",
    )
    @patch(
        "apps.test_cases.services."
        "test_case_generator.call_claude"
    )
    def test_includes_requirement_review_in_stats(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        """Incluye la evaluación funcional en estadísticas."""
        call_claude_mock.return_value = ClaudeResult(
            text=self._build_valid_json(
                review_level="saturated",
            ),
            usage=TokenUsage(),
        )

        result = generate_test_cases(
            original_filename="CFC.003_PDD.pdf",
            project_id="CFC.003",
            context_text="Sistema: SAP",
            blocks=[
                RequirementBlock(
                    requirement_number=8,
                    scenario_name="Realizar proceso",
                    input_text="Proceso con varios subprocesos.",
                ),
            ],
            assigned_to="Usuario QA",
        )

        details = result["stats"][
            "requirement_details"
        ]

        self.assertEqual(
            len(details),
            1,
        )

        self.assertEqual(
            details[0]["requirement"],
            8,
        )

        self.assertEqual(
            details[0]["scenario_name"],
            "Realizar proceso",
        )

        self.assertEqual(
            details[0][
                "requirement_review"
            ]["level"],
            "saturated",
        )

        self.assertEqual(
            details[0][
                "requirement_review"
            ]["functional_blocks"],
            [
                "Obtener información",
                "Procesar información",
            ],
        )

    @override_settings(
        CLAUDE_INPUT_USD_PER_MTOK=0,
        CLAUDE_OUTPUT_USD_PER_MTOK=0,
    )
    @patch(
        "apps.test_cases.services."
        "test_case_generator.load_test_cases_prompt",
        return_value="Prompt de prueba",
    )
    @patch(
        "apps.test_cases.services."
        "test_case_generator.call_claude"
    )
    def test_repairs_invalid_first_response(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        """Repara una primera respuesta JSON inválida."""
        call_claude_mock.side_effect = [
            ClaudeResult(
                text="respuesta inválida",
                usage=TokenUsage(
                    input_tokens=10,
                    output_tokens=5,
                ),
            ),
            ClaudeResult(
                text=self._build_valid_json(),
                usage=TokenUsage(
                    input_tokens=20,
                    output_tokens=10,
                ),
            ),
        ]

        result = generate_test_cases(
            original_filename="CFC.003_PDD.pdf",
            project_id="CFC.003",
            context_text="Sistema: SAP",
            blocks=[
                RequirementBlock(
                    requirement_number=1,
                    scenario_name="Validar archivo",
                    input_text="Validar archivo.",
                ),
            ],
            assigned_to="Usuario QA",
        )

        self.assertEqual(
            call_claude_mock.call_count,
            2,
        )

        repair_text = (
            call_claude_mock
            .call_args_list[1]
            .kwargs["user_text"]
        )

        self.assertIn(
            "Previous invalid output",
            repair_text,
        )

        self.assertIn(
            "respuesta inválida",
            repair_text,
        )

        self.assertIn(
            "requirement_review",
            repair_text,
        )

        self.assertEqual(
            result["usage"]["input_tokens"],
            30,
        )

    @override_settings(
        CLAUDE_INPUT_USD_PER_MTOK=0,
        CLAUDE_OUTPUT_USD_PER_MTOK=0,
    )
    @patch(
        "apps.test_cases.services."
        "test_case_generator.load_test_cases_prompt",
        return_value="Prompt de prueba",
    )
    @patch(
        "apps.test_cases.services."
        "test_case_generator.call_claude"
    )
    def test_repairs_response_without_requirement_review(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        """Repara una respuesta sin evaluación funcional."""
        invalid_payload = {
            "test_cases": [
                self._build_test_case(),
            ],
            "not_testable": None,
        }

        call_claude_mock.side_effect = [
            ClaudeResult(
                text=json.dumps(
                    invalid_payload,
                    ensure_ascii=False,
                ),
                usage=TokenUsage(),
            ),
            ClaudeResult(
                text=self._build_valid_json(),
                usage=TokenUsage(),
            ),
        ]

        generate_test_cases(
            original_filename="CFC.003.pdf",
            project_id="CFC.003",
            context_text="Contexto",
            blocks=[
                RequirementBlock(
                    requirement_number=1,
                    scenario_name="Validar",
                    input_text="Contenido",
                ),
            ],
            assigned_to="Usuario QA",
        )

        self.assertEqual(
            call_claude_mock.call_count,
            2,
        )

    @override_settings(
        CLAUDE_INPUT_USD_PER_MTOK=0,
        CLAUDE_OUTPUT_USD_PER_MTOK=0,
    )
    @patch(
        "apps.test_cases.services."
        "test_case_generator.load_test_cases_prompt",
        return_value="Prompt de prueba",
    )
    @patch(
        "apps.test_cases.services."
        "test_case_generator.call_claude"
    )
    def test_rejects_invalid_repaired_response(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        """Rechaza una reparación que continúa inválida."""
        call_claude_mock.side_effect = [
            ClaudeResult(
                text="respuesta inválida",
                usage=TokenUsage(),
            ),
            ClaudeResult(
                text="también inválida",
                usage=TokenUsage(),
            ),
        ]

        with self.assertRaises(
            JsonGenerationError,
        ):
            generate_test_cases(
                original_filename="CFC.003.pdf",
                project_id="CFC.003",
                context_text="Contexto",
                blocks=[
                    RequirementBlock(
                        requirement_number=1,
                        scenario_name="Validar",
                        input_text="Contenido",
                    ),
                ],
                assigned_to="Usuario QA",
            )

    @override_settings(
        CLAUDE_INPUT_USD_PER_MTOK=0,
        CLAUDE_OUTPUT_USD_PER_MTOK=0,
    )
    @patch(
        "apps.test_cases.services."
        "test_case_generator.load_test_cases_prompt",
        return_value="Prompt de prueba",
    )
    @patch(
        "apps.test_cases.services."
        "test_case_generator.call_claude"
    )
    def test_generates_not_testable_result(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        """Genera correctamente un requerimiento no testeable."""
        payload = {
            "test_cases": [],
            "not_testable": {
                "objective": (
                    "Que el bot valide el proceso cuando "
                    "exista información suficiente."
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

        call_claude_mock.return_value = ClaudeResult(
            text=json.dumps(
                payload,
                ensure_ascii=False,
            ),
            usage=TokenUsage(),
        )

        result = generate_test_cases(
            original_filename="ABC.001.pdf",
            project_id="ABC.001",
            context_text="Contexto",
            blocks=[
                RequirementBlock(
                    requirement_number=2,
                    scenario_name="Validar proceso",
                    input_text="Contenido incompleto.",
                ),
            ],
            assigned_to="Usuario QA",
        )

        self.assertEqual(
            result["stats"][
                "requirements_not_testable"
            ],
            1,
        )

        self.assertEqual(
            result["stats"][
                "test_cases_total"
            ],
            1,
        )

        detail = result["stats"][
            "requirement_details"
        ][0]

        self.assertEqual(
            detail["scenario_name"],
            "Validar proceso",
        )

        self.assertEqual(
            detail[
                "requirement_review"
            ]["level"],
            "adequate",
        )

    @classmethod
    def _build_valid_json(
        cls,
        *,
        review_level: str = "adequate",
    ) -> str:
        """Construye una respuesta JSON funcional válida."""
        payload = {
            "test_cases": [
                cls._build_test_case(),
            ],
            "not_testable": None,
            "requirement_review": (
                cls._build_requirement_review(
                    level=review_level,
                )
            ),
        }

        return json.dumps(
            payload,
            ensure_ascii=False,
        )

    @staticmethod
    def _build_test_case() -> dict[str, object]:
        """Construye un caso de prueba válido."""
        return {
            "classification": "happy_path",
            "objective": (
                "Que el bot valide el archivo."
            ),
            "expected_result": (
                "El archivo es validado correctamente."
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
                        "El archivo está disponible"
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

        return {
            "level": "adequate",
            "reason": (
                "El requerimiento representa un único "
                "comportamiento funcional."
            ),
            "areas": [],
            "functional_blocks": [],
        }