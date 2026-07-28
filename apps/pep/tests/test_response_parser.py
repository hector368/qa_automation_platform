from django.test import SimpleTestCase

from apps.pep.services.response_parser import (
    parse_json_response,
)


class ResponseParserTests(SimpleTestCase):
    def test_parses_plain_json(self) -> None:
        result = parse_json_response(
            '{"project_id": "CFC.003"}'
        )

        self.assertEqual(
            result["project_id"],
            "CFC.003",
        )

    def test_parses_json_inside_markdown(self) -> None:
        result = parse_json_response(
            '```json\n{"project_id": "CFC.003"}\n```'
        )

        self.assertEqual(
            result["project_id"],
            "CFC.003",
        )

    def test_extracts_json_after_extra_text(self) -> None:
        result = parse_json_response(
            'Resultado:\n{"project_id": "CFC.003"}'
        )

        self.assertEqual(
            result["project_id"],
            "CFC.003",
        )

    def test_preserves_braces_inside_strings(self) -> None:
        result = parse_json_response(
            (
                'Texto previo {"description": '
                '"Usa el formato {valor}"} texto posterior'
            )
        )

        self.assertEqual(
            result["description"],
            "Usa el formato {valor}",
        )

    def test_rejects_empty_response(self) -> None:
        with self.assertRaises(
            ValueError,
        ):
            parse_json_response("")

    def test_rejects_json_array_root(self) -> None:
        with self.assertRaises(
            ValueError,
        ):
            parse_json_response(
                '["uno", "dos"]'
            )