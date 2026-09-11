"""Carga del mapeo de columnas de la matriz MSP_QA."""

from __future__ import annotations

import json
import logging
import re

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from django.conf import settings

from apps.msp_qa.exceptions import MatrixConfigError


logger = logging.getLogger(__name__)

COLUMN_LETTER_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[A-Z]{1,3}$",
)

REQUIRED_KEYS: Final[tuple[str, ...]] = (
    "spreadsheet_id",
    "sheet_name",
    "header_row",
    "first_data_row",
    "id_column",
    "columns",
)


@dataclass(frozen=True, slots=True)
class ColumnMapping:
    """Relaciona un campo de la fila con una columna de la matriz."""

    field: str
    column: str
    header: str


@dataclass(frozen=True, slots=True)
class MatrixConfig:
    """Describe dónde y cómo se escribe en la matriz MSP_QA."""

    spreadsheet_id: str
    sheet_name: str
    header_row: int
    first_data_row: int
    id_column: str
    columns: tuple[ColumnMapping, ...]

    def mapping_for(self, field: str) -> ColumnMapping | None:
        """Obtiene el mapeo de un campo, si está configurado."""
        for mapping in self.columns:
            if mapping.field == field:
                return mapping

        return None


def get_config_path() -> Path:
    """Obtiene la ruta del archivo de mapeo de columnas."""
    configured_path = getattr(
        settings,
        "MSP_QA_COLUMNS_FILE",
        "",
    )

    if configured_path:
        return Path(configured_path)

    return (
        Path(__file__).resolve().parent.parent
        / "resources"
        / "msp_columns.json"
    )


def read_config_file(config_path: Path) -> dict[str, Any]:
    """
    Lee el archivo de mapeo y devuelve su contenido.

    Raises:
        MatrixConfigError: Cuando el archivo falta o no es JSON.
    """
    try:
        raw_content = config_path.read_text(encoding="utf-8")

    except FileNotFoundError as error:
        raise MatrixConfigError(
            f"No se encontró el archivo de mapeo: {config_path}",
        ) from error

    except OSError as error:
        raise MatrixConfigError(
            f"No fue posible leer el archivo de mapeo: {error}",
        ) from error

    try:
        payload = json.loads(raw_content)

    except json.JSONDecodeError as error:
        raise MatrixConfigError(
            f"El archivo de mapeo no es JSON válido: {error}",
        ) from error

    if not isinstance(payload, dict):
        raise MatrixConfigError(
            "El archivo de mapeo debe contener un objeto JSON.",
        )

    return payload


def validate_column_letter(field: str, column: str) -> str:
    """
    Valida que una letra de columna tenga formato correcto.

    Raises:
        MatrixConfigError: Cuando la letra no es válida.
    """
    clean_column = (column or "").strip().upper()

    if not COLUMN_LETTER_PATTERN.match(clean_column):
        raise MatrixConfigError(
            f"La columna '{column}' del campo '{field}' no es una "
            "letra de columna válida.",
        )

    return clean_column


def build_column_mappings(
    raw_columns: Any,
) -> tuple[ColumnMapping, ...]:
    """
    Construye los mapeos de columna a partir del archivo.

    Raises:
        MatrixConfigError: Cuando la estructura es inválida.
    """
    if not isinstance(raw_columns, dict) or not raw_columns:
        raise MatrixConfigError(
            "La sección 'columns' debe ser un objeto con al menos "
            "un campo.",
        )

    mappings: list[ColumnMapping] = []
    used_columns: dict[str, str] = {}

    for field, definition in raw_columns.items():
        if not isinstance(definition, dict):
            raise MatrixConfigError(
                f"La definición del campo '{field}' debe ser un "
                "objeto con 'column' y 'header'.",
            )

        column = validate_column_letter(
            field,
            definition.get("column", ""),
        )

        if column in used_columns:
            raise MatrixConfigError(
                f"La columna {column} está asignada a dos campos: "
                f"'{used_columns[column]}' y '{field}'.",
            )

        used_columns[column] = field

        mappings.append(
            ColumnMapping(
                field=field,
                column=column,
                header=str(
                    definition.get("header", ""),
                ).strip(),
            ),
        )

    return tuple(mappings)


def validate_positive_int(payload: dict[str, Any], key: str) -> int:
    """
    Obtiene un entero positivo del archivo de mapeo.

    Raises:
        MatrixConfigError: Cuando el valor no es un entero positivo.
    """
    raw_value = payload.get(key)

    try:
        value = int(raw_value)

    except (TypeError, ValueError) as error:
        raise MatrixConfigError(
            f"'{key}' debe ser un número entero.",
        ) from error

    if value <= 0:
        raise MatrixConfigError(
            f"'{key}' debe ser mayor que cero.",
        )

    return value


def load_matrix_config() -> MatrixConfig:
    """
    Carga y valida el mapeo de columnas de la matriz.

    Returns:
        Configuración lista para usarse al escribir.

    Raises:
        MatrixConfigError: Cuando la configuración es inválida.
    """
    config_path = get_config_path()
    payload = read_config_file(config_path)

    missing_keys = [
        key
        for key in REQUIRED_KEYS
        if key not in payload
    ]

    if missing_keys:
        raise MatrixConfigError(
            "Faltan claves en el archivo de mapeo: "
            f"{', '.join(missing_keys)}.",
        )

    spreadsheet_id = str(payload["spreadsheet_id"]).strip()
    sheet_name = str(payload["sheet_name"]).strip()

    if not spreadsheet_id:
        raise MatrixConfigError(
            "'spreadsheet_id' está vacío en el archivo de mapeo.",
        )

    if not sheet_name:
        raise MatrixConfigError(
            "'sheet_name' está vacío en el archivo de mapeo.",
        )

    header_row = validate_positive_int(payload, "header_row")
    first_data_row = validate_positive_int(payload, "first_data_row")

    if first_data_row <= header_row:
        raise MatrixConfigError(
            "'first_data_row' debe ser mayor que 'header_row'.",
        )

    logger.info(
        "Mapeo de columnas cargado desde %s.",
        config_path,
    )

    return MatrixConfig(
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        header_row=header_row,
        first_data_row=first_data_row,
        id_column=validate_column_letter(
            "id_column",
            payload["id_column"],
        ),
        columns=build_column_mappings(payload["columns"]),
    )
