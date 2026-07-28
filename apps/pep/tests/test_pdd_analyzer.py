import json
from io import BytesIO
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from docx import Document

from apps.pep.exceptions import ResponseParsingError
from apps.pep.services.claude_client import ClaudeResult
from apps.pep.services.pdd_analyzer import (
    analyze_pdd_document,
    build_pdd_preview_payload,
)
from apps.pep.services.token_usage import TokenUsage


@override_settings(
    CLAUDE_INPUT_USD_PER_MTOK=0,
    CLAUDE_OUTPUT_USD_PER_MTOK=0,
)
class PddAnalyzerTests(SimpleTestCase):
    @patch(
        "apps.pep.services.pdd_analyzer."
        "load_pdd_prompt",
        return_value="Prompt PDD",
    )
    @patch(
        "apps.pep.services.pdd_analyzer."
        "call_claude"
    )
    def test_analyzes_and_recalculates_inputs(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        payload = self._build_payload()

        # Claude entrega cantidades incorrectas intencionalmente.
        payload["calculo_insumos"]["plan_insumos"][
            "insumos_estres_120"
        ] = 999

        payload["calculo_insumos"]["plan_insumos"][
            "deployment"
        ]["uat_productivo"]["cantidad"] = 999

        call_claude_mock.return_value = ClaudeResult(
            text=json.dumps(payload),
            usage=TokenUsage(
                input_tokens=200,
                output_tokens=80,
            ),
        )

        result = analyze_pdd_document(
            filename="PDD.docx",
            file_bytes=self._build_docx(),
            max_upload_mb=10,
        )

        plan = result.data.calculo_insumos.plan_insumos

        self.assertIsNotNone(
            plan
        )

        assert plan is not None

        self.assertEqual(
            plan.insumos_estres_120,
            180,
        )

        self.assertEqual(
            plan.deployment.uat_productivo.cantidad,
            180,
        )

        self.assertEqual(
            result.usage.input_tokens,
            200,
        )

        preview = build_pdd_preview_payload(
            result
        )

        self.assertTrue(
            preview["ok"]
        )

        self.assertEqual(
            preview["pdd"]["requerimientos"],
            [
                "Consultar solicitudes",
                "Validar información",
            ],
        )

    @patch(
        "apps.pep.services.pdd_analyzer."
        "load_pdd_prompt",
        return_value="Prompt PDD",
    )
    @patch(
        "apps.pep.services.pdd_analyzer."
        "call_claude"
    )
    def test_rejects_invalid_json(
        self,
        call_claude_mock: Mock,
        _prompt_mock: Mock,
    ) -> None:
        call_claude_mock.return_value = ClaudeResult(
            text="respuesta sin JSON",
            usage=TokenUsage(),
        )

        with self.assertRaises(
            ResponseParsingError,
        ):
            analyze_pdd_document(
                filename="PDD.docx",
                file_bytes=self._build_docx(),
                max_upload_mb=10,
            )

    @staticmethod
    def _build_docx() -> bytes:
        document = Document()

        document.add_paragraph(
            "PDD del proyecto CFC.003"
        )

        output = BytesIO()
        document.save(output)

        return output.getvalue()

    @staticmethod
    def _build_payload() -> dict[str, object]:
        return {
            "estado_analisis": "completado",
            "tecnologia": {
                "valor": "Power Automate Desktop",
                "tipo_deteccion": "explicita",
                "justificacion": None,
            },
            "requerimientos": [
                "Consultar solicitudes",
                "Validar información",
            ],
            "contexto_proceso": {
                "descripcion_breve_proceso": (
                    "Procesar solicitudes."
                ),
                "calendario_frecuencia": "Diario",
                "cantidad_periodo_normal": {
                    "cantidad": 100,
                    "unidad_elemento": "solicitudes",
                },
                "cantidad_periodo_maximo": {
                    "cantidad": 150,
                    "unidad_elemento": "solicitudes",
                },
            },
            "calculo_insumos": {
                "estado_calculo": "ok",
                "datos_faltantes": [],
                "mensaje_validacion": None,
                "base_calculo_estres": "periodo_maximo",
                "plan_insumos": {
                    "nombre_proceso": (
                        "Procesar solicitudes."
                    ),
                    "frecuencia": "Diario",
                    "unidad_elemento": "solicitudes",
                    "insumos_base_periodo_normal": 100,
                    "insumos_estres_120": 180,
                    "development": {
                        "fase_1": {
                            "porcentaje": 50,
                            "cantidad": 50,
                        },
                        "fase_2": {
                            "porcentaje": 50,
                            "cantidad": 50,
                        },
                        "fase_3": {
                            "tipo": "estres",
                            "porcentaje": 120,
                            "cantidad": 180,
                        },
                    },
                    "deployment": {
                        "uat_productivo": {
                            "tipo": "estres",
                            "porcentaje": 120,
                            "cantidad": 180,
                        },
                    },
                    "trazabilidad_calculos": [],
                    "criterio_calculo": None,
                    "nota_deployment": None,
                },
            },
            "advertencias": [],
        }