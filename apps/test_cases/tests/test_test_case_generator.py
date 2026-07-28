import csv
import io
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.test import override_settings

from apps.test_cases.exceptions import (
    CsvGenerationError,
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

from apps.test_cases.services.test_case_generator import (
    generate_test_cases,
    iter_generate_test_cases,
)

class TestCaseGeneratorTests(SimpleTestCase):
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
    def test_generates_valid_csv(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        call_claude_mock.return_value = (
            ClaudeResult(
                text=self._build_valid_csv_row(),
                usage=TokenUsage(
                    input_tokens=100,
                    output_tokens=50,
                ),
            )
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
                )
            ],
            assigned_to="Usuario QA",
        )

        self.assertIn(
            "ID,Work Item Type",
            result["csv_out"],
        )

        self.assertIn(
            "CFC.003.001.001",
            result["csv_out"],
        )

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
    def test_repairs_invalid_first_response(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        call_claude_mock.side_effect = [
            ClaudeResult(
                text="a,b,c",
                usage=TokenUsage(
                    input_tokens=10,
                    output_tokens=5,
                ),
            ),
            ClaudeResult(
                text=self._build_valid_csv_row(),
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
                )
            ],
            assigned_to="Usuario QA",
        )

        self.assertEqual(
            call_claude_mock.call_count,
            2,
        )

        second_call = (
            call_claude_mock.call_args_list[1]
        )

        repair_text = (
            second_call.kwargs["user_text"]
        )

        self.assertIn(
            "Previous invalid output",
            repair_text,
        )

        self.assertIn(
            "a,b,c",
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
    def test_rejects_invalid_repaired_response(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        call_claude_mock.side_effect = [
            ClaudeResult(
                text="a,b,c",
                usage=TokenUsage(),
            ),
            ClaudeResult(
                text="d,e,f",
                usage=TokenUsage(),
            ),
        ]

        with self.assertRaises(
            CsvGenerationError,
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
                    )
                ],
                assigned_to="Usuario QA",
            )

    @staticmethod
    def _build_valid_csv_row() -> str:
        row = [""] * 15
        row[1] = "Test Case"
        row[2] = "TEMP.001.001"
        row[4] = "Validar que el bot ingrese"
        row[5] = "El sistema muestra el inicio"
        row[6] = "Functional"
        row[7] = "1"
        row[8] = "Acceso correcto"
        row[9] = "Que el bot valide el acceso"
        row[10] = "Positivo"
        row[11] = "Contar con credenciales"

        output = io.StringIO()

        writer = csv.writer(
            output,
            lineterminator="",
        )

        writer.writerow(row)

        return output.getvalue()
    
    from apps.test_cases.services.test_case_generator import (
    generate_test_cases,
    iter_generate_test_cases,
)