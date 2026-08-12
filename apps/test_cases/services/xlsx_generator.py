"""
Generación de archivos XLSX para Azure DevOps.

Este módulo transforma filas ADO previamente construidas en un
libro de Excel. No contiene lógica funcional de casos de prueba.
"""

from __future__ import annotations

from io import BytesIO
from typing import Final, Sequence

from openpyxl import Workbook

from apps.test_cases.services.ado_rows_builder import (
    ADO_COLUMNS,
    ADO_NCOLS,
)


WORKSHEET_NAME: Final[str] = "Test Cases"


def generate_xlsx(
    rows: Sequence[Sequence[str]],
) -> bytes:
    """
    Genera un archivo XLSX desde filas ADO.

    Args:
        rows: Filas de quince columnas listas para exportación.

    Returns:
        Contenido binario del archivo XLSX.

    Raises:
        ValueError: Cuando alguna fila no tiene quince columnas.
    """
    _validate_rows(
        rows
    )

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = WORKSHEET_NAME

    worksheet.append(
        list(ADO_COLUMNS)
    )

    for row in rows:
        worksheet.append(
            list(row)
        )

    output = BytesIO()

    workbook.save(
        output
    )
    workbook.close()

    return output.getvalue()


def _validate_rows(
    rows: Sequence[Sequence[str]],
) -> None:
    """
    Valida la cantidad de columnas antes de generar Excel.

    Args:
        rows: Filas que serán exportadas.

    Raises:
        ValueError: Cuando alguna fila tiene longitud inválida.
    """
    for row_number, row in enumerate(
        rows,
        start=1,
    ):
        if len(row) != ADO_NCOLS:
            raise ValueError(
                "Fila XLSX inválida. "
                f"Fila: {row_number}. "
                f"Columnas esperadas: {ADO_NCOLS}. "
                f"Columnas recibidas: {len(row)}."
            )