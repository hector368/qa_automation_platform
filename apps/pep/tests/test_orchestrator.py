from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.pep.services.orchestrator import (
    analyze_pep_documents,
    generate_pep_from_analysis,
)
from apps.pep.tests.pep_factories import (
    build_pap_data,
    build_pdd_data,
)


class PepOrchestratorTests(SimpleTestCase):
    @patch(
        "apps.pep.services.orchestrator."
        "analyze_pdd_document"
    )
    @patch(
        "apps.pep.services.orchestrator."
        "analyze_pap_document"
    )
    def test_analyzes_both_documents(
        self,
        pap_mock: Mock,
        pdd_mock: Mock,
    ) -> None:
        pap_result = Mock()
        pap_result.data = build_pap_data()
        pap_result.elapsed_seconds = 1.2

        pap_result.usage.to_dict.return_value = {
            "input_tokens": 100,
            "output_tokens": 25,
            "total_tokens": 125,
        }

        pap_result.cost.to_dict.return_value = {
            "input_usd": 0.01,
            "output_usd": 0.02,
            "total_usd": 0.03,
        }

        pdd_result = Mock()
        pdd_result.data = build_pdd_data()
        pdd_result.elapsed_seconds = 2.3

        pdd_result.usage.to_dict.return_value = {
            "input_tokens": 200,
            "output_tokens": 50,
            "total_tokens": 250,
        }

        pdd_result.cost.to_dict.return_value = {
            "input_usd": 0.02,
            "output_usd": 0.04,
            "total_usd": 0.06,
        }

        pap_mock.return_value = pap_result
        pdd_mock.return_value = pdd_result

        result = analyze_pep_documents(
            pap_filename="PAP.docx",
            pap_bytes=b"pap",
            pdd_filename="PDD.docx",
            pdd_bytes=b"pdd",
            max_upload_mb=10,
        )

        self.assertEqual(
            result["preview"]["project_id"],
            "CFC.003",
        )

        self.assertEqual(
            result["usage"]["total"][
                "input_tokens"
            ],
            300,
        )

        self.assertEqual(
            result["usage"]["total"][
                "output_tokens"
            ],
            75,
        )

        self.assertEqual(
            result["cost"]["total"][
                "total_usd_formatted"
            ],
            "$0.09",
        )
        
        self.assertEqual(
            result["elapsed"],
            3.5,
        )

    @patch(
        "apps.pep.services.orchestrator."
        "generate_pep_docx_bytes",
        return_value=b"generated-docx",
    )
    def test_generates_without_analyzing_again(
        self,
        generator_mock: Mock,
    ) -> None:
        analysis_payload = {
            "pap": build_pap_data().model_dump(
                mode="json",
            ),
            "pdd": build_pdd_data().model_dump(
                mode="json",
            ),
        }

        result = generate_pep_from_analysis(
            analysis_payload
        )

        self.assertEqual(
            result["filename"],
            "CFC.003_PEP.docx",
        )

        self.assertEqual(
            result["content"],
            b"generated-docx",
        )

        generator_mock.assert_called_once()