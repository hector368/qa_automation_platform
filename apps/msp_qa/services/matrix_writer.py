"""Escritura de filas en la matriz MSP_QA."""

from __future__ import annotations

import logging

from collections import defaultdict
from typing import Any

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
from apps.msp_qa.statuses import STATUS_FIELD


logger = logging.getLogger(__name__)

ACTION_INSERTED = "inserted"
ACTION_UPDATED = "updated"


def build_range(
    *,
    config: MatrixConfig,
    column: str,
    row_number: int,
) -> str:
    """Construye el rango A1 de una celda de la matriz."""
    return f"'{config.sheet_name}'!{column}{row_number}"


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


def read_column_by_row(
    *,
    service: Any,
    config: MatrixConfig,
    column: str,
) -> dict[int, str]:
    """
    Lee una columna completa de la matriz, fila por fila.

    Returns:
        Diccionario de número de fila al texto capturado en ella.
    """
    column_range = (
        f"'{config.sheet_name}'!"
        f"{column}{config.first_data_row}:"
        f"{column}"
    )

    column_rows = read_values(
        service=service,
        spreadsheet_id=config.spreadsheet_id,
        range_name=column_range,
    )

    values_by_row: dict[int, str] = {}

    for offset, row in enumerate(column_rows):
        cell_value = str(row[0] if row else "").strip()

        if cell_value:
            values_by_row[config.first_data_row + offset] = cell_value

    return values_by_row


def inspect_matrix_rows(
    msp_ids: list[str],
) -> dict[str, Any]:
    """
    Revisa cuáles identificadores ya están capturados en la matriz.

    Se usa antes de escribir, para poder advertir qué proyectos se van
    a sobrescribir y en qué estatus están registrados hoy.

    Args:
        msp_ids: Identificadores que se pretende escribir.

    Returns:
        Los identificadores ya registrados con su fila y su estatus
        actual, y cuántas filas nuevas se insertarían.
    """
    service = build_sheets_service()
    config = load_matrix_config(service=service)

    rows_by_id = find_row_numbers_by_id(
        service=service,
        config=config,
    )

    status_mapping = config.mapping_for(STATUS_FIELD)
    status_by_row: dict[int, str] = {}

    if status_mapping is not None:
        status_by_row = read_column_by_row(
            service=service,
            config=config,
            column=status_mapping.column,
        )

    existing: list[dict[str, Any]] = []

    for msp_id in msp_ids:
        matches = rows_by_id.get(str(msp_id).strip().upper()) or []

        if not matches:
            continue

        row_number = matches[0]

        existing.append(
            {
                "msp_id": msp_id,
                "row_number": row_number,
                "current_status": status_by_row.get(row_number, ""),
                "duplicated_rows": matches[1:],
            },
        )

    logger.info(
        "Revisión previa a la escritura: %s de %s fila(s) ya "
        "existen en '%s'.",
        len(existing),
        len(msp_ids),
        config.sheet_name,
    )

    return {
        "sheet_name": config.sheet_name,
        "status_header": (
            status_mapping.header
            if status_mapping is not None
            else ""
        ),
        "existing": existing,
        "new_count": len(msp_ids) - len(existing),
    }


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
        Las actualizaciones y los encabezados escritos.
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

        written_columns.append(mapping.header)

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
    service = build_sheets_service()
    config = load_matrix_config(service=service)

    sheet_id = get_sheet_id(
        service=service,
        spreadsheet_id=config.spreadsheet_id,
        sheet_name=config.sheet_name,
    )

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
