from django.core.cache import cache
from django.test import SimpleTestCase

from apps.test_cases.services.result_store import (
    load_generation_result,
    save_generation_result,
)


class ResultStoreTests(SimpleTestCase):
    def setUp(self) -> None:
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_saves_and_loads_result_for_owner(
        self,
    ) -> None:
        payload = {
            "filename": "resultado.xlsx",
            "xlsx_bytes": b"contenido-xlsx",
        }

        save_generation_result(
            result_id="result-1",
            session_key="session-1",
            payload=payload,
            timeout_seconds=60,
        )

        result = load_generation_result(
            result_id="result-1",
            session_key="session-1",
        )

        self.assertEqual(
            result,
            payload,
        )

    def test_rejects_different_session(
        self,
    ) -> None:
        save_generation_result(
            result_id="result-1",
            session_key="session-1",
            payload={
                "xlsx_bytes": b"contenido-xlsx"
            },
            timeout_seconds=60,
        )

        result = load_generation_result(
            result_id="result-1",
            session_key="session-2",
        )

        self.assertIsNone(
            result
        )