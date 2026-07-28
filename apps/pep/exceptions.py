"""
Excepciones específicas del generador PEP.

Los mensajes internos se utilizan en logs. Los mensajes públicos son
seguros para mostrarse en la interfaz.
"""

from __future__ import annotations


class PepError(Exception):
    """Excepción base del generador PEP."""

    code = "ERR_PEP"
    http_status = 500
    public_message = (
        "Ocurrió un error durante la generación del PEP."
    )

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.public_message
        super().__init__(self.detail)


class FileValidationError(PepError):
    """Error general de validación de archivo."""

    code = "ERR_FILE_VALIDATION"
    http_status = 400
    public_message = "El archivo proporcionado no es válido."


class UnsupportedFileTypeError(FileValidationError):
    """El formato del documento no está permitido."""

    code = "ERR_BAD_EXT"
    public_message = "El formato permitido es PDF o DOCX."


class EmptyFileError(FileValidationError):
    """El archivo recibido está vacío."""

    code = "ERR_EMPTY_FILE"
    public_message = "El archivo está vacío."


class FileTooLargeError(FileValidationError):
    """El archivo supera el límite configurado."""

    code = "ERR_TOO_LARGE"
    public_message = "El archivo supera el tamaño máximo permitido."


class DocumentExtractionError(PepError):
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


class ClaudeConfigurationError(PepError):
    """La integración con Claude no está configurada."""

    code = "ERR_CLAUDE_CONFIG"
    http_status = 500
    public_message = "La integración con Claude no está configurada."


class ClaudeRequestError(PepError):
    """La solicitud a Claude no pudo completarse."""

    code = "ERR_CLAUDE_REQUEST"
    http_status = 502
    public_message = (
        "No fue posible completar la solicitud al modelo de "
        "inteligencia artificial."
    )


class ClaudeResponseError(PepError):
    """Claude respondió sin texto utilizable."""

    code = "ERR_CLAUDE_RESPONSE"
    http_status = 502
    public_message = (
        "El modelo no devolvió una respuesta válida para continuar."
    )


class PromptConfigurationError(PepError):
    """No fue posible cargar un prompt de PEP."""

    code = "ERR_PROMPT_CONFIG"
    http_status = 500
    public_message = (
        "La configuración necesaria para analizar los documentos "
        "no está disponible."
    )


class ResponseParsingError(PepError):
    """La respuesta del modelo no coincide con el esquema esperado."""

    code = "ERR_RESPONSE_PARSING"
    http_status = 502
    public_message = (
        "El modelo no devolvió una respuesta estructurada válida."
    )


class PepGenerationError(PepError):
    """No fue posible construir el documento PEP."""

    code = "ERR_PEP_GENERATION"
    http_status = 500
    public_message = "No fue posible generar el documento PEP."

class PepTemplateError(PepGenerationError):
    """La plantilla integrada del PEP no es utilizable."""

    code = "ERR_PEP_TEMPLATE"
    http_status = 500
    public_message = (
        "La plantilla necesaria para generar el PEP "
        "no está disponible o no es válida."
    )