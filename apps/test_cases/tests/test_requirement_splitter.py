from django.test import SimpleTestCase

from apps.test_cases.services.requirement_splitter import (
    extract_project_id,
    slice_to_be_section,
    split_by_requirement,
)


class RequirementSplitterTests(SimpleTestCase):
    def test_extracts_project_id_from_label(self) -> None:
        text = """
        Código PDD_BA_05
        ID proyecto CFC.003
        Fecha de emisión: 24 de julio
        """

        project_id = extract_project_id(
            text,
            filename="documento.pdf",
        )

        self.assertEqual(
            project_id,
            "CFC.003",
        )

    def test_extracts_project_id_from_filename(self) -> None:
        project_id = extract_project_id(
            "Documento funcional sin etiqueta explícita.",
            filename="CFC.003_PDD.pdf",
        )

        self.assertEqual(
            project_id,
            "CFC.003",
        )

    def test_slices_tobe_section(self) -> None:
        text = """
        2.3 Mapa del proceso

        2.4 Acciones detalladas del proceso TO-BE

        1. Nombre de la acción: Validar archivo
        Descripción general: El bot valida el archivo.

        2. Nombre de la acción: Procesar información
        Descripción general: El bot procesa la información.

        2.5 Matriz de criterios de aceptación
        """

        section = slice_to_be_section(text)

        self.assertIn(
            "Validar archivo",
            section,
        )

        self.assertNotIn(
            "Matriz de criterios",
            section,
        )

    def test_splits_classic_beecker_requirements(self) -> None:
        text = """
        1. Nombre de la acción: Validar archivo
        Descripción general: Validación inicial.

        2. Nombre de la acción: Procesar información
        Descripción general: Procesamiento de registros.
        """

        blocks = split_by_requirement(text)

        self.assertEqual(
            len(blocks),
            2,
        )

        self.assertEqual(
            blocks[0].requirement_number,
            1,
        )

        self.assertEqual(
            blocks[0].scenario_name,
            "Validar archivo",
        )