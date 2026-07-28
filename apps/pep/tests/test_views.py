from unittest.mock import Mock, patch

from django.core.cache import cache
from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.pep.services.result_store import (
    save_pep_analysis,
)
from apps.pep.tests.pep_factories import (
    build_pap_data,
    build_pdd_data,
)


@override_settings(
    PEP_ANALYSIS_TTL_SECONDS=60,
    PEP_RESULT_TTL_SECONDS=60,
)
class PepViewsTests(TestCase):
    def setUp(self) -> None:
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_home_is_available(self) -> None:
        response = self.client.get(
            reverse("pep:home")
        )
    
        self.assertEqual(
            response.status_code,
            200,
        )
    
        self.assertTemplateUsed(
            response,
            "pep/index.html",
        )
    
        self.assertContains(
            response,
            "PEP Generator",
        )
    
        self.assertContains(
            response,
            "pep/css/pep.css",
        )
    
        self.assertContains(
            response,
            "pep/js/pep_generator.js",
        )
    
        self.assertContains(
            response,
            "pep/img/b-logo.png",
        )
    
        self.assertContains(
            response,
            "pep/img/logo.png",
        )
    
        self.assertNotContains(
            response,
            "tcgen/",
        )

    @patch(
        "apps.pep.views."
        "analyze_pep_documents"
    )
    def test_analyzes_documents(
        self,
        analyze_mock: Mock,
    ) -> None:
        analyze_mock.return_value = (
            self._build_analysis_payload()
        )

        response = self.client.post(
            reverse("pep:analyze"),
            {
                "pap_document": (
                    SimpleUploadedFile(
                        "PAP.docx",
                        b"pap-document",
                    )
                ),
                "pdd_document": (
                    SimpleUploadedFile(
                        "PDD.docx",
                        b"pdd-document",
                    )
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        payload = response.json()

        self.assertTrue(
            payload["ok"]
        )

        self.assertEqual(
            payload["code"],
            "OK_PEP_ANALYZED",
        )

        self.assertIn(
            "analysis_id",
            payload,
        )

    def test_rejects_missing_pap(self) -> None:
        response = self.client.post(
            reverse("pep:analyze"),
            {
                "pdd_document": (
                    SimpleUploadedFile(
                        "PDD.docx",
                        b"pdd-document",
                    )
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.json()["code"],
            "ERR_PEP_INPUT",
        )

    @patch(
        "apps.pep.views."
        "generate_pep_from_analysis"
    )
    def test_generates_and_downloads_pep(
        self,
        generate_mock: Mock,
    ) -> None:
        session = self.client.session
        session["initialized"] = True
        session.save()

        analysis_id = "analysis-test"

        save_pep_analysis(
            analysis_id=analysis_id,
            session_key=session.session_key,
            payload=self._build_analysis_payload(),
            timeout_seconds=60,
        )

        generate_mock.return_value = {
            "filename": "CFC.003_PEP.docx",
            "content": b"generated-docx",
            "context": {
                "project_id": "CFC.003",
            },
        }

        response = self.client.post(
            reverse("pep:generate"),
            {
                "analysis_id": analysis_id,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        payload = response.json()

        self.assertTrue(
            payload["ok"]
        )

        self.assertIn(
            "download_url",
            payload,
        )

        download_response = self.client.get(
            payload["download_url"]
        )

        self.assertEqual(
            download_response.status_code,
            200,
        )

        self.assertEqual(
            download_response.content,
            b"generated-docx",
        )

        self.assertIn(
            "CFC.003_PEP.docx",
            download_response[
                "Content-Disposition"
            ],
        )

    def test_returns_404_without_result(self) -> None:
        response = self.client.get(
            reverse("pep:download")
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.assertEqual(
            response.json()["code"],
            "ERR_PEP_RESULT_NOT_FOUND",
        )

    @staticmethod
    def _build_analysis_payload() -> dict:
        return {
            "pap_filename": "PAP.docx",
            "pdd_filename": "PDD.docx",
            "pap": build_pap_data().model_dump(
                mode="json",
            ),
            "pdd": build_pdd_data().model_dump(
                mode="json",
            ),
            "preview": {
                "project_id": "CFC.003",
            },
            "usage": {
                "total": {
                    "input_tokens": 300,
                    "output_tokens": 75,
                    "total_tokens": 375,
                },
            },
            "cost": {
                "total": {
                    "total_usd": 0.09,
                    "total_usd_formatted": "$0.090000",
                },
            },
            "elapsed": 3.5,
        }