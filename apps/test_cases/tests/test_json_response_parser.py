from django.test import SimpleTestCase

from apps.test_cases.services.json_response_parser import (
    extract_json_object,
)


class JsonResponseParserTests(SimpleTestCase):
    """Pruebas para la extracción tolerante de JSON."""

    def test_extracts_clean_json(
        self,
    ) -> None:
        """Extrae una respuesta que contiene únicamente JSON."""
        text = """
        {
            "test_cases": []
        }
        """

        result = extract_json_object(
            text
        )

        self.assertEqual(
            result,
            {
                "test_cases": [],
            },
        )

    def test_extracts_json_from_code_fence(
        self,
    ) -> None:
        """Elimina fences Markdown antes de procesar el JSON."""
        text = """
        ```json
        {
            "test_cases": []
        }
        ```
        """

        result = extract_json_object(
            text
        )

        self.assertEqual(
            result["test_cases"],
            [],
        )

    def test_extracts_json_after_extra_text(
        self,
    ) -> None:
        """Tolera texto accidental antes del objeto JSON."""
        text = """
        Aquí está el resultado solicitado.

        {
            "test_cases": []
        }
        """

        result = extract_json_object(
            text
        )

        self.assertEqual(
            result["test_cases"],
            [],
        )

    def test_extracts_json_before_extra_text(
        self,
    ) -> None:
        """Tolera texto accidental después del objeto JSON."""
        text = """
        {
            "test_cases": []
        }

        Fin de la respuesta.
        """

        result = extract_json_object(
            text
        )

        self.assertEqual(
            result["test_cases"],
            [],
        )

    def test_skips_invalid_object_before_valid_json(
        self,
    ) -> None:
        """Continúa buscando cuando encuentra llaves no válidas."""
        text = """
        Ejemplo incorrecto: {valor}

        {
            "test_cases": []
        }
        """

        result = extract_json_object(
            text
        )

        self.assertEqual(
            result["test_cases"],
            [],
        )

    def test_removes_bom(
        self,
    ) -> None:
        """Tolera una marca BOM al inicio de la respuesta."""
        text = (
            "\ufeff"
            '{"test_cases": []}'
        )

        result = extract_json_object(
            text
        )

        self.assertEqual(
            result["test_cases"],
            [],
        )

    def test_rejects_empty_response(
        self,
    ) -> None:
        """Rechaza respuestas sin contenido."""
        with self.assertRaises(
            ValueError,
        ):
            extract_json_object(
                ""
            )

    def test_rejects_top_level_array(
        self,
    ) -> None:
        """Exige que la raíz de la respuesta sea un objeto."""
        text = """
        [
            {
                "test_cases": []
            }
        ]
        """

        with self.assertRaises(
            ValueError,
        ):
            extract_json_object(
                text
            )

    def test_rejects_invalid_json(
        self,
    ) -> None:
        """Rechaza respuestas sin ningún objeto JSON válido."""
        text = """
        Respuesta inválida:
        {
            'test_cases': []
        }
        """

        with self.assertRaises(
            ValueError,
        ):
            extract_json_object(
                text
            )