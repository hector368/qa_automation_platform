from django.core.cache import cache
from django.test import SimpleTestCase

from apps.pep.services.result_store import (
    load_pep_analysis,
    load_pep_result,
    save_pep_analysis,
    save_pep_result,
)


class PepResultStoreTests(SimpleTestCase):
    def setUp(self) -> None:
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_saves_and_loads_analysis(self) -> None:
        save_pep_analysis(
            analysis_id="analysis-1",
            session_key="session-1",
            payload={
                "pap": {
                    "id_proyecto": "CFC.003",
                },
            },
            timeout_seconds=60,
        )

        result = load_pep_analysis(
            analysis_id="analysis-1",
            session_key="session-1",
        )

        self.assertIsNotNone(
            result
        )

        assert result is not None

        self.assertEqual(
            result["pap"]["id_proyecto"],
            "CFC.003",
        )

    def test_rejects_analysis_from_other_session(
        self,
    ) -> None:
        save_pep_analysis(
            analysis_id="analysis-1",
            session_key="session-1",
            payload={"pap": {}},
            timeout_seconds=60,
        )

        result = load_pep_analysis(
            analysis_id="analysis-1",
            session_key="session-2",
        )

        self.assertIsNone(
            result
        )

    def test_saves_and_loads_document(self) -> None:
        save_pep_result(
            result_id="result-1",
            session_key="session-1",
            filename="CFC.003_PEP.docx",
            content=b"docx-content",
            timeout_seconds=60,
        )

        result = load_pep_result(
            result_id="result-1",
            session_key="session-1",
        )

        self.assertEqual(
            result,
            {
                "filename": "CFC.003_PEP.docx",
                "content": b"docx-content",
            },
        )

    def test_rejects_document_from_other_session(
        self,
    ) -> None:
        save_pep_result(
            result_id="result-1",
            session_key="session-1",
            filename="CFC.003_PEP.docx",
            content=b"docx-content",
            timeout_seconds=60,
        )

        result = load_pep_result(
            result_id="result-1",
            session_key="session-2",
        )

        self.assertIsNone(
            result
        )