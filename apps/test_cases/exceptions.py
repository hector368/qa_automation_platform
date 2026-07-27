"""
Excepciones específicas del generador de casos de prueba.

Cada excepción contiene un código y un mensaje público seguro. El detalle
interno puede registrarse en logs, pero no debe enviarse directamente a la
interfaz.
"""

from __future__ import annotations


class TestCasesError(Exception):
    """Excepción base del generador de casos de prueba."""

    code = "ERR_TEST_CASES"
    public_message = (
        "Ocurrió un error durante el procesamiento de los casos de prueba."
    )

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.public_message
        super().__init__(self.detail)


class FileValidationError(TestCasesError):
    """Error general de validación de archivo."""

    code = "ERR_FILE_VALIDATION"
    public_message = "El archivo proporcionado no es válido."


class UnsupportedFileTypeError(FileValidationError):
    """La extensión del documento no está permitida."""

    code = "ERR_BAD_EXT"
    public_message = "El formato permitido es PDF o DOCX."


class EmptyFileError(FileValidationError):
    """El archivo no contiene información binaria."""

    code = "ERR_EMPTY_FILE"
    public_message = "El archivo está vacío."


class FileTooLargeError(FileValidationError):
    """El archivo supera el tamaño configurado."""

    code = "ERR_TOO_LARGE"
    public_message = "El archivo supera el tamaño máximo permitido."


class DocumentExtractionError(TestCasesError):
    """No fue posible abrir o procesar el documento."""

    code = "ERR_DOCUMENT_EXTRACTION"
    public_message = "No fue posible leer el contenido del documento."


class EmptyDocumentTextError(DocumentExtractionError):
    """El documento no contiene texto extraíble."""

    code = "ERR_NO_TEXT"
    public_message = (
        "No se encontró texto extraíble. El documento podría estar "
        "escaneado o no contener una capa de texto."
    )


class ClaudeConfigurationError(TestCasesError):
    """La integración con Claude no está configurada."""

    code = "ERR_CLAUDE_CONFIG"
    public_message = "La integración con Claude no está configurada."


class ClaudeRequestError(TestCasesError):
    """La solicitud a Claude no pudo completarse."""

    code = "ERR_CLAUDE_REQUEST"
    public_message = (
        "No fue posible completar la solicitud al modelo de inteligencia "
        "artificial."
    )


class ClaudeResponseError(TestCasesError):
    """Claude respondió sin texto utilizable."""

    code = "ERR_CLAUDE_RESPONSE"
    public_message = (
        "El modelo no devolvió una respuesta válida para continuar."
    )