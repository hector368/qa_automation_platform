from django.test import SimpleTestCase

from apps.pep.services.context_builder import (
    build_pep_context,
    build_pep_context_payload,
    build_pep_output_filename,
)
from apps.pep.tests.pep_factories import (
    build_pap_data,
    build_pdd_data,
)


class PepContextBuilderTests(SimpleTestCase):
    def test_builds_combined_context(self) -> None:
        context = build_pep_context(
            pap_data=build_pap_data(),
            pdd_data=build_pdd_data(),
        )

        self.assertEqual(
            context.project_id,
            "CFC.003",
        )

        self.assertEqual(
            context.output_filename,
            "CFC.003_PEP.docx",
        )

        self.assertEqual(
            context.pdd.tecnologia.valor,
            "Power Automate Desktop",
        )

        self.assertEqual(
            context.pdd.requerimientos,
            [
                "Consultar solicitudes",
                "Validar información",
            ],
        )

    def test_builds_serializable_payload(self) -> None:
        context = build_pep_context(
            pap_data=build_pap_data(),
            pdd_data=build_pdd_data(),
        )

        payload = build_pep_context_payload(
            context
        )

        self.assertTrue(
            payload["ok"]
        )

        self.assertEqual(
            payload["summary"][
                "functional_requirements"
            ],
            2,
        )

        self.assertEqual(
            payload["summary"][
                "technology_source"
            ],
            "pdd",
        )

    def test_warns_when_project_id_is_missing(self) -> None:
        context = build_pep_context(
            pap_data=build_pap_data(
                project_id=None
            ),
            pdd_data=build_pdd_data(),
        )

        self.assertEqual(
            context.output_filename,
            "PROYECTO_PEP.docx",
        )

        self.assertIn(
            "No se detectó el ID del proyecto en el PAP.",
            context.warnings,
        )

    def test_sanitizes_output_filename(self) -> None:
        result = build_pep_output_filename(
            'ABC:001 / "Proyecto"'
        )

        self.assertEqual(
            result,
            "ABC_001_Proyecto_PEP.docx",
        )