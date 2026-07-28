from django.test import SimpleTestCase

from apps.test_cases.schemas.request_schema import (
    GenerationRequest,
    parse_selected_requirements,
)


class GenerationRequestTests(SimpleTestCase):
    def test_parses_numbers_and_ranges(self) -> None:
        result = parse_selected_requirements(
            "1, 2, 5-7"
        )

        self.assertEqual(
            result,
            [1, 2, 5, 6, 7],
        )

    def test_reverses_range(self) -> None:
        result = parse_selected_requirements(
            "5-3"
        )

        self.assertEqual(
            result,
            [3, 4, 5],
        )

    def test_returns_none_for_empty_selection(
        self,
    ) -> None:
        self.assertIsNone(
            parse_selected_requirements("")
        )

    def test_rejects_invalid_selection(self) -> None:
        with self.assertRaises(ValueError):
            parse_selected_requirements(
                "1, dos, 3"
            )

    def test_rejects_excessive_range(self) -> None:
        with self.assertRaises(ValueError):
            parse_selected_requirements(
                "1-1000000"
            )

    def test_validates_generation_request(
        self,
    ) -> None:
        request_data = GenerationRequest(
            assigned_to="Usuario QA",
            selected_requirements=[3, 1, 3],
        )

        self.assertEqual(
            request_data.assigned_to,
            "Usuario QA",
        )

        self.assertEqual(
            request_data.selected_requirements,
            [1, 3],
        )