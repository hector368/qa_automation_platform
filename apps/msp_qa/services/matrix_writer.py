"""Escritura de filas en la matriz MSP_QA."""

from __future__ import annotations

import logging

from collections import defaultdict
from typing import Any

from apps.msp_qa.exceptions import HeaderMismatchError
from apps.msp_qa.services.msp_row_builder import COLUMN_LABELS
from apps.msp_qa.services.sheet_config import (
    MatrixConfig,
    load_matrix_config,
)
from apps.msp_qa.services.sheets_client import (
    build_sheets_service,
    get_sheet_id,
    insert_blank_rows,
    read_values,
    update_cells,
)


logger = logging.getLogger(__name__)

ALPHABET_SIZE = 26

ACTION_INSERTED = "inserted"
ACTION_UPDATED = "updated"


def column_letter_to_index(column: str) -> int:
    """Convierte una letra de columna en su índice base cero."""
    index = 0

    for character in column.upper():
        index = (
            index * ALPHABET_SIZE
            + (ord(character) - ord("A") + 1)
        )

    return index - 1


def normalize_header(raw_header: str) -> str:
    """Normaliza un encabezado para compararlo sin ruido."""
    return " ".join(str(raw_header or "").split()).upper()


def build_range(
    *,
    config: MatrixConfig,
    column: str,
    row_number: int,
) -> str:
    """Construye el rango A1 de una celda de la matriz."""
    return f"'{config.sheet_name}'!{column}{row_number}"


def verify_headers(
    *,
    service: Any,
    config: MatrixConfig,
) -> None:
    """
    Verifica que los encabezados coincidan con el mapeo configurado.

    Evita escribir en la columna equivocada cuando alguien agrega o
    mueve columnas en la matriz sin actualizar el archivo de mapeo.

    Raises:
        HeaderMismatchError: Cuando algún encabezado no coincide.
    """
    header_range = (
        f"'{config.sheet_name}'!"
        f"{config.header_row}:{config.header_row}"
    )

    header_rows = read_values(
        service=service,
        spreadsheet_id=config.spreadsheet_id,
        range_name=header_range,
    )

    headers = header_rows[0] if header_rows else []

    mismatches: list[str] = []

    for mapping in config.columns:
        if not mapping.header:
            continue

        column_index = column_letter_to_index(mapping.column)

        found_header = (
            headers[column_index]
            if column_index < len(headers)
            else ""
        )

        if normalize_header(found_header) != normalize_header(
            mapping.header,
        ):
            mismatches.append(
                f"{mapping.column}: expected "
                f"'{mapping.header}', found '{found_header}'",
            )

    if mismatches:
        logger.warning(
            "El mapeo de columnas no coincide con la matriz: %s",
            "; ".join(mismatches),
        )

        raise HeaderMismatchError(
            "; ".join(mismatches),
        )


def find_row_numbers_by_id(
    *,
    service: Any,
    config: MatrixConfig,
) -> dict[str, list[int]]:
    """
    Mapea cada identificador de la matriz a las filas donde aparece.

    Returns:
        Diccionario de identificador en mayúsculas a números de fila.
    """
    id_range = (
        f"'{config.sheet_name}'!"
        f"{config.id_column}{config.first_data_row}:"
        f"{config.id_column}"
    )

    id_rows = read_values(
        service=service,
        spreadsheet_id=config.spreadsheet_id,
        range_name=id_range,
    )

    rows_by_id: dict[str, list[int]] = defaultdict(list)

    for offset, row in enumerate(id_rows):
        cell_value = row[0] if row else ""
        clean_value = str(cell_value).strip().upper()

        if clean_value:
            rows_by_id[clean_value].append(
                config.first_data_row + offset,
            )

    return dict(rows_by_id)


def build_cell_updates(
    *,
    config: MatrixConfig,
    row_number: int,
    row_data: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Construye las celdas a escribir de una fila.

    Solo se incluyen los campos con dato. Las columnas sin valor no se
    tocan, de modo que al sobrescribir una fila existente se conserva
    lo que ya estaba capturado a mano.

    Returns:
        Las actualizaciones y las etiquetas de columna escritas.
    """
    updates: list[dict[str, Any]] = []
    written_columns: list[str] = []

    for mapping in config.columns:
        value = row_data.get(mapping.field)

        if value is None or value == "":
            continue

        updates.append(
            {
                "range": build_range(
                    config=config,
                    column=mapping.column,
                    row_number=row_number,
                ),
                "values": [[value]],
            },
        )

        written_columns.append(
            COLUMN_LABELS.get(mapping.field, mapping.field),
        )

    return updates, written_columns


def write_rows_to_matrix(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Escribe varias filas en la matriz con criterio de actualización.

    Cuando el identificador ya existe en la matriz, se sobrescribe esa
    fila. Cuando no existe, se inserta una fila nueva al inicio del
    área de datos. Toda la escritura se resuelve en dos llamadas a
    Google Sheets, sin importar cuántas filas sean.

    Args:
        rows: Filas construidas a partir de los bloques seleccionados.

    Returns:
        Resumen de la escritura, fila por fila.
    """
    config = load_matrix_config()
    service = build_sheets_service()

    sheet_id = get_sheet_id(
        service=service,
        spreadsheet_id=config.spreadsheet_id,
        sheet_name=config.sheet_name,
    )

    verify_headers(service=service, config=config)

    rows_by_id = find_row_numbers_by_id(
        service=service,
        config=config,
    )

    rows_to_insert: list[dict[str, Any]] = []
    rows_to_update: list[tuple[int, dict[str, Any]]] = []
    duplicate_ids: list[dict[str, Any]] = []

    for row_data in rows:
        msp_id = str(row_data.get("msp_id") or "").strip().upper()
        matches = rows_by_id.get(msp_id) or []

        if matches:
            rows_to_update.append((matches[0], row_data))

            if len(matches) > 1:
                duplicate_ids.append(
                    {
                        "msp_id": row_data.get("msp_id"),
                        "rows": matches,
                    },
                )
        else:
            rows_to_insert.append(row_data)

    inserted_count = len(rows_to_insert)

    insert_blank_rows(
        service=service,
        spreadsheet_id=config.spreadsheet_id,
        sheet_id=sheet_id,
        row_number=config.first_data_row,
        amount=inserted_count,
    )

    updates: list[dict[str, Any]] = []
    written_rows: list[dict[str, Any]] = []

    for offset, row_data in enumerate(rows_to_insert):
        row_number = config.first_data_row + offset

        cell_updates, written_columns = build_cell_updates(
            config=config,
            row_number=row_number,
            row_data=row_data,
        )

        updates.extend(cell_updates)

        written_rows.append(
            {
                "msp_id": row_data.get("msp_id"),
                "row_number": row_number,
                "action": ACTION_INSERTED,
                "written_columns": written_columns,
            },
        )

    # Las filas existentes se recorrieron hacia abajo al insertar.
    for original_row, row_data in rows_to_update:
        row_number = original_row + inserted_count

        cell_updates, written_columns = build_cell_updates(
            config=config,
            row_number=row_number,
            row_data=row_data,
        )

        updates.extend(cell_updates)

        written_rows.append(
            {
                "msp_id": row_data.get("msp_id"),
                "row_number": row_number,
                "action": ACTION_UPDATED,
                "written_columns": written_columns,
            },
        )

    updated_cells = update_cells(
        service=service,
        spreadsheet_id=config.spreadsheet_id,
        updates=updates,
    )

    logger.info(
        "Matriz actualizada: %s fila(s) nueva(s), %s actualizada(s), "
        "%s celdas escritas.",
        inserted_count,
        len(rows_to_update),
        updated_cells,
    )

    return {
        "ok": True,
        "sheet_name": config.sheet_name,
        "inserted": inserted_count,
        "updated": len(rows_to_update),
        "updated_cells": updated_cells,
        "rows": written_rows,
        "duplicate_ids": duplicate_ids,
    }


def write_row_to_matrix(
    row_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Escribe una sola fila en la matriz.

    Delega en la escritura por lotes para no duplicar la lógica de
    actualización contra inserción.
    """
    return write_rows_to_matrix([row_data])
