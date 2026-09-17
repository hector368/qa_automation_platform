"""Verificación de la pestaña Config contra la matriz real."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.msp_qa.exceptions import MspQaError
from apps.msp_qa.services.sheet_config import (
    build_header_index,
    get_config_sheet_name,
    load_matrix_config,
    normalize_header,
)
from apps.msp_qa.services.sheets_client import (
    build_sheets_service,
    read_values,
)


class Command(BaseCommand):
    """Confirma que el config coincide con la matriz."""

    help = (
        "Lee la pestaña Config, la contrasta contra la fila de "
        "encabezados de la matriz y reporta qué columna resolvió "
        "cada campo. Útil antes de escribir por primera vez."
    )

    def handle(self, *args: Any, **options: Any) -> None:
        """Ejecuta la verificación y escribe el reporte."""
        self.stdout.write(
            f"Leyendo la pestaña '{get_config_sheet_name()}'...\n"
        )

        try:
            config = load_matrix_config(force_refresh=True)

        except MspQaError as error:
            self.stdout.write("")
            self.stdout.write(self.style.ERROR("CONFIG INVALIDO"))
            self.stdout.write(f"  {error.public_message}")
            self.stdout.write(f"  {error.detail}")

            return

        self.report_settings(config)
        self.report_columns(config)
        self.report_unmapped_headers(config)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Config valido: la matriz se puede escribir."
            )
        )

    def report_settings(self, config: Any) -> None:
        """Escribe los ajustes generales que se leyeron."""
        self.stdout.write("")
        self.stdout.write("AJUSTES GENERALES")
        self.stdout.write(
            f"  Pestaña de la matriz : {config.sheet_name}"
        )
        self.stdout.write(
            f"  Fila de encabezados  : {config.header_row}"
        )
        self.stdout.write(
            f"  Primera fila de datos: {config.first_data_row}"
        )
        self.stdout.write(
            f"  Columna del ID       : {config.id_column} "
            f"('{config.id_header}')"
        )
        self.stdout.write(
            f"  Horas de QA          : {config.hours_ratio} "
            f"({round(config.hours_ratio * 100)}%)"
        )

    def report_columns(self, config: Any) -> None:
        """Escribe a qué columna resolvió cada campo."""
        self.stdout.write("")
        self.stdout.write(
            f"COLUMNAS RESUELTAS ({len(config.columns)})"
        )

        for mapping in config.columns:
            self.stdout.write(
                f"  {mapping.column:>3}  {mapping.field:34} "
                f"{mapping.header}"
            )

    def report_unmapped_headers(self, config: Any) -> None:
        """Escribe los encabezados de la matriz sin configurar."""
        service = build_sheets_service()

        header_rows = read_values(
            service=service,
            spreadsheet_id=config.spreadsheet_id,
            range_name=(
                f"'{config.sheet_name}'!"
                f"{config.header_row}:{config.header_row}"
            ),
        )

        header_index = build_header_index(
            header_rows[0] if header_rows else [],
        )

        mapped = {
            normalize_header(mapping.header)
            for mapping in config.columns
        }

        unmapped = [
            (column, header)
            for header, column in header_index.items()
            if header not in mapped
        ]

        self.stdout.write("")
        self.stdout.write("COLUMNAS DE LA MATRIZ SIN CONFIGURAR")

        if not unmapped:
            self.stdout.write("  Ninguna.")
            return

        self.stdout.write(
            "  Existen en la matriz pero el config no las menciona. "
            "No se escriben."
        )

        for column, header in sorted(unmapped):
            self.stdout.write(f"  {column:>3}  {header}")
