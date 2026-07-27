from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from docx import Document


class AnalyzeDocumentViewTests(TestCase):
    def test_analyzes_valid_docx(self) -> None:
        document_bytes = self._build_valid_docx()

        uploaded_file = SimpleUploadedFile(
            name="CFC.003_PDD.docx",
            content=document_bytes,
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
        )

        response = self.client.post(
            reverse("test_cases:analyze"),
            {
                "document": uploaded_file,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        payload = response.json()

        self.assertTrue(
            payload["ok"],
        )

        self.assertEqual(
            payload["project_id"],
            "CFC.003",
        )

        self.assertEqual(
            payload["total_blocks"],
            2,
        )

    def test_rejects_request_without_file(self) -> None:
        response = self.client.post(
            reverse("test_cases:analyze"),
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.json()["code"],
            "ERR_NO_FILE",
        )

    def test_rejects_unsupported_extension(self) -> None:
        uploaded_file = SimpleUploadedFile(
            name="document.txt",
            content=b"contenido",
            content_type="text/plain",
        )

        response = self.client.post(
            reverse("test_cases:analyze"),
            {
                "document": uploaded_file,
            },
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        self.assertEqual(
            response.json()["code"],
            "ERR_BAD_EXT",
        )

    def test_returns_422_when_requirements_are_missing(
        self,
    ) -> None:
        document = Document()
        document.add_paragraph(
            "Documento sin requerimientos funcionales."
        )

        output = BytesIO()
        document.save(output)

        uploaded_file = SimpleUploadedFile(
            name="document.docx",
            content=output.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
        )

        response = self.client.post(
            reverse("test_cases:analyze"),
            {
                "document": uploaded_file,
            },
        )

        self.assertEqual(
            response.status_code,
            422,
        )

        self.assertEqual(
            response.json()["code"],
            "ERR_NO_REQUIREMENTS",
        )

    @staticmethod
    def _build_valid_docx() -> bytes:
        document = Document()

        document.add_paragraph(
            "ID proyecto CFC.003"
        )

        document.add_paragraph(
            "2.4 Acciones detalladas del proceso TO-BE"
        )

        document.add_paragraph(
            "1. Nombre de la acción: Validar archivo"
        )

        document.add_paragraph(
            "Descripción general: Validar estructura."
        )

        document.add_paragraph(
            "2. Nombre de la acción: Procesar información"
        )

        document.add_paragraph(
            "Descripción general: Procesar registros."
        )

        document.add_paragraph(
            "2.5 Matriz de criterios de aceptación"
        )

        output = BytesIO()
        document.save(output)

        return output.getvalue()