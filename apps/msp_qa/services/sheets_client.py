"""Cliente de Google Sheets para la matriz MSP_QA."""

from __future__ import annotations

import logging

from pathlib import Path
from typing import Any, Final

from django.conf import settings
from google.auth.exceptions import GoogleAuthError
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from apps.msp_qa.exceptions import (
    SheetAuthenticationError,
    SheetWriteError,
)


logger = logging.getLogger(__name__)

SHEETS_SCOPES: Final[list[str]] = [
    "https://www.googleapis.com/auth/spreadsheets",
]

DEFAULT_CREDENTIALS_FILE: Final[str] = "key.json"


def get_credentials_path() -> Path:
    """Obtiene la ruta del archivo de credenciales de Google."""
    configured_path = (
        getattr(settings, "GOOGLE_CREDENTIALS_FILE", "")
        or ""
    ).strip()

    if configured_path:
        return Path(configured_path)

    return Path(settings.BASE_DIR) / DEFAULT_CREDENTIALS_FILE


def build_sheets_service() -> Any:
    """
    Construye el cliente autenticado de Google Sheets.

    Returns:
        Servicio listo para consultar y escribir.

    Raises:
        SheetAuthenticationError: Cuando faltan o fallan las
            credenciales de la cuenta de servicio.
    """
    credentials_path = get_credentials_path()

    if not credentials_path.exists():
        raise SheetAuthenticationError(
            "No se encontró el archivo de credenciales en "
            f"{credentials_path}.",
        )

    try:
        credentials = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=SHEETS_SCOPES,
        )

        return build(
            "sheets",
            "v4",
            credentials=credentials,
            cache_discovery=False,
        )

    except (GoogleAuthError, ValueError) as error:
        logger.exception(
            "Falló la autenticación con Google Sheets.",
        )

        raise SheetAuthenticationError(
            f"Credenciales inválidas: {error}",
        ) from error


def get_sheet_id(
    *,
    service: Any,
    spreadsheet_id: str,
    sheet_name: str,
) -> int:
    """
    Obtiene el identificador interno de una hoja por su nombre.

    Raises:
        SheetWriteError: Cuando la hoja no existe o no es accesible.
    """
    try:
        spreadsheet = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
        ).execute()

    except HttpError as error:
        raise SheetWriteError(
            "No fue posible leer el archivo de Google Sheets. "
            "Verifica el identificador y que la cuenta de servicio "
            f"tenga acceso: {error}",
        ) from error

    for sheet in spreadsheet.get("sheets", []):
        properties = sheet.get("properties", {})

        if properties.get("title") == sheet_name:
            return int(properties.get("sheetId"))

    available_names = ", ".join(
        str(sheet.get("properties", {}).get("title"))
        for sheet in spreadsheet.get("sheets", [])
    )

    raise SheetWriteError(
        f"No existe la hoja '{sheet_name}'. "
        f"Hojas disponibles: {available_names}.",
    )


def read_values(
    *,
    service: Any,
    spreadsheet_id: str,
    range_name: str,
) -> list[list[str]]:
    """
    Lee un rango de celdas de la hoja.

    Raises:
        SheetWriteError: Cuando la lectura falla.
    """
    try:
        response = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
        ).execute()

    except HttpError as error:
        raise SheetWriteError(
            f"No fue posible leer el rango {range_name}: {error}",
        ) from error

    return response.get("values", [])


def insert_blank_rows(
    *,
    service: Any,
    spreadsheet_id: str,
    sheet_id: int,
    row_number: int,
    amount: int = 1,
) -> None:
    """
    Inserta filas vacías a partir de la posición indicada.

    Las filas existentes se desplazan hacia abajo tantas posiciones
    como filas se inserten. El formato se hereda de la fila siguiente,
    que es la primera fila de datos.

    Args:
        row_number: Posición donde inicia la inserción, en base uno.
        amount: Cantidad de filas a insertar.

    Raises:
        SheetWriteError: Cuando la inserción falla.
    """
    if amount <= 0:
        return

    request_body = {
        "requests": [
            {
                "insertDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": row_number - 1,
                        "endIndex": row_number - 1 + amount,
                    },
                    "inheritFromBefore": False,
                },
            },
        ],
    }

    try:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request_body,
        ).execute()

    except HttpError as error:
        raise SheetWriteError(
            f"No fue posible insertar {amount} fila(s) en la "
            f"posición {row_number}: {error}",
        ) from error

    logger.info(
        "Se insertaron %s fila(s) vacía(s) en la posición %s.",
        amount,
        row_number,
    )


def update_cells(
    *,
    service: Any,
    spreadsheet_id: str,
    updates: list[dict[str, Any]],
) -> int:
    """
    Escribe celdas individuales sin tocar el resto de la fila.

    Args:
        updates: Lista de rangos con su valor, en formato de la API.

    Returns:
        Cantidad de celdas actualizadas.

    Raises:
        SheetWriteError: Cuando la escritura falla.
    """
    if not updates:
        return 0

    request_body = {
        "valueInputOption": "USER_ENTERED",
        "data": updates,
    }

    try:
        response = service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request_body,
        ).execute()

    except HttpError as error:
        raise SheetWriteError(
            f"No fue posible escribir en la matriz: {error}",
        ) from error

    return int(response.get("totalUpdatedCells", 0))
