import json
from io import BytesIO
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from docx import Document

from apps.pep.exceptions import ResponseParsingError
from apps.pep.services.claude_client import ClaudeResult
from apps.pep.services.pap_analyzer import (
    analyze_pap_document,
    build_pap_preview_payload,
)
from apps.pep.services.token_usage import TokenUsage


@override_settings(
    CLAUDE_INPUT_USD_PER_MTOK=0,
    CLAUDE_OUTPUT_USD_PER_MTOK=0,
)
class PapAnalyzerTests(SimpleTestCase):
    @patch(
        "apps.pep.services.pap_analyzer."
        "load_pap_prompt",
        return_value="Prompt PAP",
    )
    @patch(
        "apps.pep.services.pap_analyzer."
        "call_claude"
    )
    def test_analyzes_pap_document(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        call_claude_mock.return_value = ClaudeResult(
            text=json.dumps(
                self._build_valid_payload()
            ),
            usage=TokenUsage(
                input_tokens=100,
                output_tokens=30,
            ),
        )

        result = analyze_pap_document(
            filename="PAP.docx",
            file_bytes=self._build_docx(),
            max_upload_mb=10,
        )

        self.assertEqual(
            result.data.id_proyecto,
            "CFC.003",
        )

        self.assertEqual(
            result.usage.input_tokens,
            100,
        )

        preview = build_pap_preview_payload(
            result
        )

        self.assertTrue(
            preview["ok"]
        )

        self.assertEqual(
            preview["pap"]["nombre_cliente"],
            "Cliente de prueba",
        )

    @patch(
        "apps.pep.services.pap_analyzer."
        "load_pap_prompt",
        return_value="Prompt PAP",
    )
    @patch(
        "apps.pep.services.pap_analyzer."
        "call_claude"
    )
    def test_rejects_invalid_json_response(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        call_claude_mock.return_value = ClaudeResult(
            text="respuesta sin json",
            usage=TokenUsage(),
        )

        with self.assertRaises(
            ResponseParsingError,
        ):
            analyze_pap_document(
                filename="PAP.docx",
                file_bytes=self._build_docx(),
                max_upload_mb=10,
            )

    @staticmethod
    def _build_docx() -> bytes:
        document = Document()

        document.add_paragraph(
            "PAP del proyecto CFC.003"
        )

        output = BytesIO()
        document.save(output)

        return output.getvalue()

    @staticmethod
    def _build_valid_payload() -> dict[str, object]:
        return {
            "nombre_proyecto": "Proyecto de prueba",
            "id_proyecto": "CFC.003",
            "nombre_cliente": "Cliente de prueba",
            "roles": {
                "desarrollador": [
                    "Persona Desarrollo"
                ],
                "tester": [
                    "Persona Testing"
                ],
                "scrum_master": None,
                "delivery_manager": None,
                "business_analyst": None,
                "arquitecto": None,
                "code_reviewer": None,
            },
            "requisitos_software": {
                "texto_introductorio": None,
                "items": [
                    "Power Automate Desktop"
                ],
            },
            "requisitos_hardware": {
                "texto_introductorio": None,
                "items": [],
            },
            "advertencias": [],
        }