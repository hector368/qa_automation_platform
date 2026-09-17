"""Lectura del mapeo de columnas desde la pestaña Config."""

from __future__ import annotations

import logging

from dataclasses import dataclass
from typing import Any, Final

from django.conf import settings
from django.core.cache import cache

from apps.msp_qa.exceptions import MatrixConfigError
from apps.msp_qa.schemas.msp_row import MspRow
from apps.msp_qa.services.sheets_client import (
    build_sheets_service,
    read_values,
)


logger = logging.getLogger(__name__)

ALPHABET_SIZE: Final[int] = 26

DEFAULT_CONFIG_SHEET: Final[str] = "Config"

CONFIG_CACHE_KEY: Final[str] = "msp_qa:matrix_config"

# Vigencia corta: el objetivo del config es que un cambio en la hoja
# se refleje casi de inmediato, pero sin releerla en cada fila.
DEFAULT_CONFIG_TTL_SECONDS: Final[int] = 60

SETTINGS_MARKER: Final[str] = "AJUSTES GENERALES"
COLUMNS_MARKER: Final[str] = "COLUMNAS"

# Encabezados de las tablas del config, que no son datos.
TABLE_HEADERS: Final[frozenset[str]] = frozenset(
    {
        "ajuste",
        "campo",
    },
)

# Nombres válidos para la columna A de la sección COLUMNAS. Salen del
# esquema de la fila, así que un nombre mal escrito se detiene con un
# mensaje en lugar de dejar esa columna sin escribir en silencio.
KNOWN_FIELDS: Final[frozenset[str]] = frozenset(MspRow.model_fields)

REQUIRED_SETTINGS: Final[tuple[str, ...]] = (
    "sheet_name",
    "header_row",
    "first_data_row",
    "id_header",
    "qa_hours_ratio",
)


@dataclass(frozen=True, slots=True)
class ColumnMapping:
    """Relaciona un campo con su encabezado y su columna resuelta."""

    field: str
    header: str
    column: str


@dataclass(frozen=True, slots=True)
class MatrixConfig:
    """Describe dónde y cómo se escribe en la matriz MSP_QA."""

    spreadsheet_id: str
    sheet_name: str
    header_row: int
    first_data_row: int
    id_header: str
    id_column: str
    hours_ratio: float
    columns: tuple[ColumnMapping, ...]

    def mapping_for(self, field: str) -> ColumnMapping | None:
        """Obtiene el mapeo de un campo, si está configurado."""
        for mapping in self.columns:
            if mapping.field == field:
                return mapping

        return None


def column_letter_to_index(column: str) -> int:
    """Convierte una letra de columna en su índice base cero."""
    index = 0

    for character in column.upper():
        index = (
            index * ALPHABET_SIZE
            + (ord(character) - ord("A") + 1)
        )

    return index - 1


def column_index_to_letter(index: int) -> str:
    """Convierte un índice base cero en letra de columna."""
    letters = ""
    position = index

    while position >= 0:
        letters = (
            chr(ord("A") + (position % ALPHABET_SIZE))
            + letters
        )
        position = position // ALPHABET_SIZE - 1

    return letters


def normalize_header(raw_header: Any) -> str:
    """Normaliza un encabezado para compararlo sin ruido."""
    return " ".join(str(raw_header or "").split()).upper()


def get_spreadsheet_id() -> str:
    """Obtiene el identificador del archivo de la matriz."""
    spreadsheet_id = (
        getattr(settings, "MSP_QA_SPREADSHEET_ID", "")
        or ""
    ).strip()

    if not spreadsheet_id:
        raise MatrixConfigError(
            "La variable MSP_QA_SPREADSHEET_ID no está definida "
            "en el archivo .env.",
        )

    return spreadsheet_id


def get_config_sheet_name() -> str:
    """Obtiene el nombre de la pestaña de configuración."""
    return (
        getattr(settings, "MSP_QA_CONFIG_SHEET", "")
        or DEFAULT_CONFIG_SHEET
    ).strip()


def get_config_ttl() -> int:
    """Obtiene la vigencia del config en caché, en segundos."""
    return int(
        getattr(
            settings,
            "MSP_QA_CONFIG_TTL_SECONDS",
            DEFAULT_CONFIG_TTL_SECONDS,
        ),
    )


def read_cell(row: list[Any], index: int) -> str:
    """Lee una celda de una fila, tolerando filas cortas."""
    if index >= len(row):
        return ""

    return str(row[index] or "").strip()


def parse_config_rows(
    rows: list[list[Any]],
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """
    Separa la pestaña en ajustes generales y mapeo de columnas.

    Los bloques se localizan por su rótulo, no por número de fila, de
    modo que insertar filas en la hoja no rompe la lectura.

    Returns:
        Los ajustes y los pares de campo y encabezado.
    """
    general_settings: dict[str, str] = {}
    column_pairs: list[tuple[str, str]] = []

    current_block = ""

    for row in rows:
        key = read_cell(row, 0)
        value = read_cell(row, 1)

        if not key:
            continue

        upper_key = key.upper()

        if upper_key == SETTINGS_MARKER:
            current_block = "settings"
            continue

        if upper_key == COLUMNS_MARKER:
            current_block = "columns"
            continue

        if key.lower() in TABLE_HEADERS:
            continue

        if current_block == "settings":
            general_settings[key] = value

        elif current_block == "columns":
            column_pairs.append((key, value))

    return general_settings, column_pairs


def parse_positive_int(
    general_settings: dict[str, str],
    key: str,
) -> int:
    """
    Obtiene un entero positivo de los ajustes generales.

    Raises:
        MatrixConfigError: Cuando el valor no es un entero positivo.
    """
    raw_value = general_settings.get(key, "")

    try:
        value = int(float(raw_value.replace(",", ".")))

    except (TypeError, ValueError) as error:
        raise MatrixConfigError(
            f"'{key}' debe ser un número entero. Se leyó "
            f"'{raw_value}'.",
        ) from error

    if value <= 0:
        raise MatrixConfigError(
            f"'{key}' debe ser mayor que cero.",
        )

    return value


def parse_ratio(general_settings: dict[str, str]) -> float:
    """
    Obtiene la proporción de horas de QA.

    Acepta punto o coma decimal, y también el formato de porcentaje.

    Raises:
        MatrixConfigError: Cuando el valor está fuera de rango.
    """
    raw_value = general_settings.get("qa_hours_ratio", "").strip()
    clean_value = raw_value.replace(",", ".")

    is_percentage = clean_value.endswith("%")

    if is_percentage:
        clean_value = clean_value[:-1].strip()

    try:
        value = float(clean_value)

    except (TypeError, ValueError) as error:
        raise MatrixConfigError(
            "'qa_hours_ratio' debe ser un número. Se leyó "
            f"'{raw_value}'.",
        ) from error

    if is_percentage:
        value = value / 100

    if not 0 < value <= 1:
        raise MatrixConfigError(
            "'qa_hours_ratio' debe estar entre 0 y 1. Se leyó "
            f"'{raw_value}'.",
        )

    return value


def build_header_index(
    headers: list[Any],
) -> dict[str, str]:
    """Relaciona cada encabezado de la matriz con su columna."""
    header_index: dict[str, str] = {}

    for position, raw_header in enumerate(headers):
        normalized = normalize_header(raw_header)

        if normalized and normalized not in header_index:
            header_index[normalized] = column_index_to_letter(
                position,
            )

    return header_index


def resolve_columns(
    *,
    column_pairs: list[tuple[str, str]],
    header_index: dict[str, str],
) -> tuple[ColumnMapping, ...]:
    """
    Convierte cada encabezado configurado en su columna real.

    Raises:
        MatrixConfigError: Cuando un nombre de campo no existe o
            cuando algún encabezado no está en la matriz. El proceso
            se detiene antes de escribir nada.
    """
    mappings: list[ColumnMapping] = []
    missing: list[str] = []
    unknown: list[str] = []

    for field, header in column_pairs:
        if not header:
            continue

        if field not in KNOWN_FIELDS:
            unknown.append(field)
            continue

        column = header_index.get(normalize_header(header))

        if column is None:
            missing.append(f"{field} -> '{header}'")
            continue

        mappings.append(
            ColumnMapping(
                field=field,
                header=header,
                column=column,
            ),
        )

    if unknown:
        raise MatrixConfigError(
            "These field names in column A of the Config tab do not "
            "exist: " + ", ".join(unknown) + ". Valid names are: "
            + ", ".join(sorted(KNOWN_FIELDS)),
        )

    if missing:
        raise MatrixConfigError(
            "These headers from the Config tab were not found in "
            "the matrix header row: " + "; ".join(missing),
        )

    if not mappings:
        raise MatrixConfigError(
            "La sección COLUMNAS no tiene ningún encabezado.",
        )

    return tuple(mappings)


def build_matrix_config(service: Any) -> MatrixConfig:
    """
    Lee la pestaña Config y resuelve las columnas de la matriz.

    Raises:
        MatrixConfigError: Cuando falta un ajuste o un encabezado.
    """
    spreadsheet_id = get_spreadsheet_id()
    config_sheet = get_config_sheet_name()

    config_rows = read_values(
        service=service,
        spreadsheet_id=spreadsheet_id,
        range_name=f"'{config_sheet}'!A:C",
    )

    if not config_rows:
        raise MatrixConfigError(
            f"La pestaña '{config_sheet}' está vacía o no existe.",
        )

    general_settings, column_pairs = parse_config_rows(config_rows)

    missing_settings = [
        key
        for key in REQUIRED_SETTINGS
        if not general_settings.get(key)
    ]

    if missing_settings:
        raise MatrixConfigError(
            "Faltan ajustes en la pestaña Config: "
            + ", ".join(missing_settings),
        )

    sheet_name = general_settings["sheet_name"]
    header_row = parse_positive_int(general_settings, "header_row")
    first_data_row = parse_positive_int(
        general_settings,
        "first_data_row",
    )

    if first_data_row <= header_row:
        raise MatrixConfigError(
            "'first_data_row' debe ser mayor que 'header_row'.",
        )

    header_rows = read_values(
        service=service,
        spreadsheet_id=spreadsheet_id,
        range_name=f"'{sheet_name}'!{header_row}:{header_row}",
    )

    if not header_rows:
        raise MatrixConfigError(
            f"La fila {header_row} de '{sheet_name}' está vacía.",
        )

    header_index = build_header_index(header_rows[0])

    id_header = general_settings["id_header"]
    id_column = header_index.get(normalize_header(id_header))

    if id_column is None:
        raise MatrixConfigError(
            f"The ID header '{id_header}' was not found in row "
            f"{header_row} of '{sheet_name}'.",
        )

    return MatrixConfig(
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        header_row=header_row,
        first_data_row=first_data_row,
        id_header=id_header,
        id_column=id_column,
        hours_ratio=parse_ratio(general_settings),
        columns=resolve_columns(
            column_pairs=column_pairs,
            header_index=header_index,
        ),
    )


def load_matrix_config(
    *,
    service: Any = None,
    force_refresh: bool = False,
) -> MatrixConfig:
    """
    Obtiene la configuración vigente de la matriz.

    Se guarda en caché por poco tiempo para no releer la hoja en cada
    fila de un lote, sin que los cambios tarden en reflejarse.

    Args:
        service: Cliente de Sheets ya construido, si lo hay.
        force_refresh: Ignora la caché y vuelve a leer la hoja.

    Returns:
        Configuración con las columnas ya resueltas.
    """
    if not force_refresh:
        cached_config = cache.get(CONFIG_CACHE_KEY)

        if cached_config is not None:
            return cached_config

    config = build_matrix_config(
        service or build_sheets_service(),
    )

    cache.set(
        CONFIG_CACHE_KEY,
        config,
        timeout=get_config_ttl(),
    )

    logger.info(
        "Config leído: %s columnas resueltas en '%s'.",
        len(config.columns),
        config.sheet_name,
    )

    return config
