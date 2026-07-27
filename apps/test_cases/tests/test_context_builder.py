from django.test import SimpleTestCase

from apps.test_cases.services.context_builder import (
    build_context_pack,
)


class ContextBuilderTests(SimpleTestCase):
    def test_builds_global_context(self) -> None:
        text = """
        Sistema: ServiceNow
        Input: Solicitud RITM
        Output: Registro validado
        La información fue obtenida en la actividad 1.
        Formato de salida .csv
        """

        result = build_context_pack(text)

        self.assertIn(
            "ServiceNow",
            result,
        )

        self.assertIn(
            "Solicitud RITM",
            result,
        )

        self.assertIn(
            "Registro validado",
            result,
        )

        self.assertIn(
            "actividad 1",
            result,
        )

    def test_respects_character_limit(self) -> None:
        text = (
            "Sistema: Aplicación\n"
            + ("Texto extenso. " * 200)
        )

        result = build_context_pack(
            text,
            max_chars=150,
        )

        self.assertLessEqual(
            len(result),
            162,
        )