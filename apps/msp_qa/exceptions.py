"""Excepciones específicas del módulo MSP QA Matrix."""


class MspQaError(Exception):
    """Excepción base del módulo MSP QA Matrix."""

    code = "ERR_MSP_QA"
    public_message = "An error occurred in the MSP QA module."
    http_status = 500

    # Indica si el detalle técnico puede mostrarse al usuario. Se
    # activa cuando ese detalle es lo único que permite corregir el
    # problema, por ejemplo una columna mal mapeada.
    expose_detail = False

    def __init__(self, detail: str = "") -> None:
        """Conserva el detalle técnico junto al mensaje público."""
        super().__init__(detail or self.public_message)

        self.detail = detail or self.public_message


class AzureConfigurationError(MspQaError):
    """Indica que falta configurar la conexión a Azure DevOps."""

    code = "ERR_AZURE_CONFIG"
    public_message = (
        "The Azure DevOps connection is not configured."
    )
    http_status = 409
    expose_detail = True


class AzureAuthenticationError(MspQaError):
    """Indica que Azure DevOps rechazó el token configurado."""

    code = "ERR_AZURE_AUTH"
    public_message = (
        "Azure DevOps rejected the configured token. Check that it "
        "is still valid and has read permissions."
    )
    http_status = 401


class AzureRequestError(MspQaError):
    """Indica una falla al consultar la API de Azure DevOps."""

    code = "ERR_AZURE_REQUEST"
    public_message = "Azure DevOps could not be reached."
    http_status = 502


class ProjectNotFoundError(MspQaError):
    """Indica que el proyecto no existe o no es visible."""

    code = "ERR_PROJECT_NOT_FOUND"
    public_message = (
        "The project does not exist or is not visible with the "
        "current token."
    )
    http_status = 404


class DescriptionEmptyError(MspQaError):
    """Indica que el proyecto no tiene descripción capturada."""

    code = "ERR_DESCRIPTION_EMPTY"
    public_message = (
        "This project has no description in Azure DevOps, so there "
        "is nothing to extract."
    )
    http_status = 422


class BlockNotFoundError(MspQaError):
    """Indica que el bloque solicitado no existe en la descripción."""

    code = "ERR_BLOCK_NOT_FOUND"
    public_message = (
        "The selected block no longer exists in the project "
        "description."
    )
    http_status = 404
    expose_detail = True


class MatrixConfigError(MspQaError):
    """Indica que el mapeo de columnas es inválido o no existe."""

    code = "ERR_MATRIX_CONFIG"
    public_message = "The Config tab of the matrix is invalid."
    http_status = 500
    expose_detail = True


class SheetAuthenticationError(MspQaError):
    """Indica que no fue posible autenticarse con Google Sheets."""

    code = "ERR_SHEET_AUTH"
    public_message = "Could not authenticate with Google Sheets."
    http_status = 500
    expose_detail = True


class HeaderMismatchError(MspQaError):
    """Indica que los encabezados no coinciden con el mapeo."""

    code = "ERR_HEADER_MISMATCH"
    public_message = (
        "The matrix headers do not match the Config tab. "
        "Nothing was sent."
    )
    http_status = 409
    expose_detail = True


class SheetWriteError(MspQaError):
    """Indica una falla al escribir en la matriz."""

    code = "ERR_SHEET_WRITE"
    public_message = "Could not write to the MSP QA matrix."
    http_status = 502
    expose_detail = True


class PreviewExpiredError(MspQaError):
    """Indica que la vista previa ya no está en caché."""

    code = "ERR_PREVIEW_EXPIRED"
    public_message = (
        "The extracted data expired. Select the projects again."
    )
    http_status = 409
