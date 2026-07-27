"""
Excepciones específicas del generador de casos de prueba.

Cada excepción contiene un código, un estado HTTP y un mensaje público
seguro. Los detalles internos deben utilizarse únicamente en logs.
"""

from __future__ import annotations


class TestCasesError(Exception):
    """Excepción base del generador de casos de prueba."""

    code = "ERR_TEST_CASES"
    http_status = 500
    public_message = (
        "Ocurrió un error durante el procesamiento "
        "de los casos de prueba."
    )

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.public_message
        super().__init__(self.detail)


class FileValidationError(TestCasesError):
    """Error general de validación de archivo."""

    code = "ERR_FILE_VALIDATION"
    http_status = 400
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
    http_status = 422
    public_message = "No fue posible leer el contenido del documento."


class EmptyDocumentTextError(DocumentExtractionError):
    """El documento no contiene texto extraíble."""

    code = "ERR_NO_TEXT"
    public_message = (
        "No se encontró texto extraíble. El documento podría estar "
        "escaneado o no contener una capa de texto."
    )


class RequirementsNotFoundError(TestCasesError):
    """No se encontraron requerimientos funcionales válidos."""

    code = "ERR_NO_REQUIREMENTS"
    http_status = 422
    public_message = (
        "No fue posible detectar requerimientos funcionales "
        "en el documento."
    )


class ClaudeConfigurationError(TestCasesError):
    """La integración con Claude no está configurada."""

    code = "ERR_CLAUDE_CONFIG"
    http_status = 500
    public_message = "La integración con Claude no está configurada."


class ClaudeRequestError(TestCasesError):
    """La solicitud a Claude no pudo completarse."""

    code = "ERR_CLAUDE_REQUEST"
    http_status = 502
    public_message = (
        "No fue posible completar la solicitud al modelo "
        "de inteligencia artificial."
    )


class ClaudeResponseError(TestCasesError):
    """Claude respondió sin texto utilizable."""

    code = "ERR_CLAUDE_RESPONSE"
    http_status = 502
    public_message = (
        "El modelo no devolvió una respuesta válida para continuar."
    )
    
class PromptConfigurationError(TestCasesError):
    """El prompt requerido no está disponible o está vacío."""

    code = "ERR_PROMPT_CONFIG"
    http_status = 500
    public_message = (
        "La configuración para generar los casos de prueba "
        "no está disponible."
    )