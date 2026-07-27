from django.test import SimpleTestCase

from apps.test_cases.services.requirement_segmenter import (
    segment_requirements_flexible,
)


class RequirementSegmenterTests(SimpleTestCase):
    def test_segments_classic_beecker_format(self) -> None:
        text = """
        ID proyecto CFC.003

        2.4 Acciones detalladas del proceso TO-BE

        1. Nombre de la acción: Validar archivo
        Descripción general: Validar la estructura del archivo.

        2. Nombre de la acción: Procesar información
        Descripción general: Procesar los registros válidos.

        2.5 Matriz de criterios de aceptación
        """

        result = segment_requirements_flexible(
            text,
            project_id="CFC.003",
        )

        self.assertEqual(
            result.method,
            "tobe",
        )

        self.assertEqual(
            len(result.blocks),
            2,
        )

    def test_segments_new_beecker_format(self) -> None:
        text = """
        ID proyecto ABC.001

        2.4 Acciones detalladas del proceso TO-BE

        1. Obtener mapa de cargas
        Descripción general: Obtener la información inicial del proceso.

        2. Validar registros
        Descripción general: Validar los registros obtenidos.

        3. Generar archivo
        Descripción general: Generar el archivo de salida.

        2.5 Matriz de criterios de aceptación
        """

        result = segment_requirements_flexible(
            text,
            project_id="ABC.001",
        )

        self.assertEqual(
            result.method,
            "tobe_numbered",
        )

        self.assertEqual(
            len(result.blocks),
            3,
        )

        self.assertEqual(
            result.blocks[0].scenario_name,
            "Obtener mapa de cargas",
        )

    def test_segments_fdd_requirement_ids(self) -> None:
        text = """
        Project ID: ABC.001

        ABC.001.001 Consultar información
        El sistema consulta la información del proceso.

        ABC.001.002 Validar información
        El sistema valida los registros recibidos.

        ABC.001.003 Generar resultado
        El sistema genera el archivo final.
        """

        result = segment_requirements_flexible(
            text,
            project_id="ABC.001",
        )

        self.assertEqual(
            result.method,
            "req_id",
        )

        self.assertEqual(
            len(result.blocks),
            3,
        )

        self.assertEqual(
            result.blocks[0].requirement_number,
            1,
        )

    def test_returns_none_when_no_structure_exists(self) -> None:
        result = segment_requirements_flexible(
            "Documento sin requerimientos funcionales.",
        )

        self.assertEqual(
            result.method,
            "none",
        )

        self.assertEqual(
            result.blocks,
            [],
        )