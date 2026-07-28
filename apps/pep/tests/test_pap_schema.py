from django.test import SimpleTestCase

from apps.pep.exceptions import ResponseParsingError
from apps.pep.schemas.pap_schema import (
    validate_pap_payload,
)


class PapSchemaTests(SimpleTestCase):
    def test_validates_complete_payload(self) -> None:
        result = validate_pap_payload(
            self._build_payload()
        )

        self.assertEqual(
            result.id_proyecto,
            "CFC.003",
        )

        self.assertEqual(
            result.tecnologia.valor,
            "Power Automate Desktop",
        )

        self.assertEqual(
            result.roles.desarrollador,
            ["Persona Desarrollo"],
        )

    def test_rejects_extra_fields(self) -> None:
        payload = self._build_payload()
        payload["campo_inventado"] = "valor"

        with self.assertRaises(
            ResponseParsingError,
        ):
            validate_pap_payload(
                payload
            )

    def test_rejects_inferred_technology_without_reason(
        self,
    ) -> None:
        payload = self._build_payload()

        payload["tecnologia"] = {
            "valor": "UiPath",
            "tipo_deteccion": "inferida",
            "justificacion": None,
        }

        with self.assertRaises(
            ResponseParsingError,
        ):
            validate_pap_payload(
                payload
            )

    def test_accepts_missing_technology(self) -> None:
        payload = self._build_payload()

        payload["tecnologia"] = {
            "valor": None,
            "tipo_deteccion": "no_encontrada",
            "justificacion": None,
        }

        result = validate_pap_payload(
            payload
        )

        self.assertIsNone(
            result.tecnologia.valor
        )

    @staticmethod
    def _build_payload() -> dict[str, object]:
        return {
            "nombre_proyecto": "Proyecto de prueba",
            "id_proyecto": "CFC.003",
            "nombre_cliente": "Cliente de prueba",
            "tecnologia": {
                "valor": "Power Automate Desktop",
                "tipo_deteccion": "explicita",
                "justificacion": None,
            },
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