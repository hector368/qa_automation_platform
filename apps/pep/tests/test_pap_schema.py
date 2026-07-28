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

    @staticmethod
    def _build_payload() -> dict[str, object]:
        return {
            "nombre_proyecto": "Proyecto de prueba",
            "id_proyecto": "CFC.003",
            "nombre_cliente": "Cliente de prueba",
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
    def test_rejects_technology_field(self) -> None:
        """El PAP ya no acepta información tecnológica."""
        payload = self._build_payload()
    
        payload["tecnologia"] = {
            "valor": "Power Automate",
            "tipo_deteccion": "explicita",
            "justificacion": None,
        }
    
        with self.assertRaises(
            ResponseParsingError,
        ):
            validate_pap_payload(
                payload
            )