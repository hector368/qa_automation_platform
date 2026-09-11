"""Auditoría de las etiquetas usadas en las descripciones de Azure."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from django.core.management.base import BaseCommand

from apps.msp_qa.exceptions import MspQaError
from apps.msp_qa.services.block_splitter import (
    split_description_blocks,
)
from apps.msp_qa.services.description_parser import (
    IGNORED_LABELS,
    build_alias_index,
    extract_labels,
    normalize_label,
)
from apps.msp_qa.services.project_catalog import (
    get_project_description,
    list_projects,
)

SAMPLE_PROJECT_COUNT = 3


class Command(BaseCommand):
    """Recorre los proyectos y reporta las etiquetas encontradas."""

    help = (
        "Revisa la descripción de cada proyecto de Azure DevOps y "
        "reporta qué etiquetas usa, cuáles no reconoce el parser y "
        "qué tan seguido aparece cada campo de la matriz."
    )

    def add_arguments(self, parser: Any) -> None:
        """Declara las opciones del comando."""
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help=(
                "Revisa solo los primeros N proyectos. Cero los "
                "revisa todos."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Ejecuta la auditoría y escribe el reporte."""
        limit = int(options.get("limit") or 0)

        projects = list_projects()

        if limit > 0:
            projects = projects[:limit]

        self.stdout.write(
            f"Revisando {len(projects)} proyecto(s)...\n"
        )

        alias_index = build_alias_index()

        unmapped_counter: Counter[str] = Counter()
        unmapped_projects: dict[str, list[str]] = defaultdict(list)
        field_projects: dict[str, set[str]] = defaultdict(set)

        empty_projects: list[str] = []
        failed_projects: list[str] = []
        scanned_blocks = 0

        for project in projects:
            project_name = str(project["name"])

            try:
                description = get_project_description(project_name)

            except MspQaError as error:
                failed_projects.append(
                    f"{project_name}: {error.detail}"
                )
                continue

            if not description:
                empty_projects.append(project_name)
                continue

            try:
                blocks = split_description_blocks(description)

            except MspQaError as error:
                failed_projects.append(
                    f"{project_name}: {error.detail}"
                )
                continue

            for block in blocks:
                scanned_blocks += 1

                for raw_label in extract_labels(block.text):
                    normalized = normalize_label(raw_label)

                    if normalized in IGNORED_LABELS:
                        continue

                    field_name = alias_index.get(normalized)

                    if field_name is None:
                        unmapped_counter[raw_label] += 1

                        samples = unmapped_projects[raw_label]

                        if project_name not in samples:
                            samples.append(project_name)

                        continue

                    field_projects[field_name].add(project_name)

        self.report_summary(
            projects=projects,
            scanned_blocks=scanned_blocks,
            empty_projects=empty_projects,
            failed_projects=failed_projects,
        )

        self.report_unmapped(
            unmapped_counter=unmapped_counter,
            unmapped_projects=unmapped_projects,
        )

        self.report_coverage(
            field_projects=field_projects,
            total_projects=len(projects),
        )

    def report_summary(
        self,
        *,
        projects: list[dict[str, object]],
        scanned_blocks: int,
        empty_projects: list[str],
        failed_projects: list[str],
    ) -> None:
        """Escribe el resumen general de la revisión."""
        self.stdout.write("")
        self.stdout.write("RESUMEN")
        self.stdout.write(f"  Proyectos revisados : {len(projects)}")
        self.stdout.write(f"  Bloques leidos      : {scanned_blocks}")
        self.stdout.write(
            f"  Sin descripcion     : {len(empty_projects)}"
        )
        self.stdout.write(
            f"  Con error           : {len(failed_projects)}"
        )

        if empty_projects:
            self.stdout.write("")
            self.stdout.write("SIN DESCRIPCION")

            for project_name in empty_projects:
                self.stdout.write(f"  - {project_name}")

        if failed_projects:
            self.stdout.write("")
            self.stdout.write("CON ERROR")

            for detail in failed_projects:
                self.stdout.write(f"  - {detail}")

    def report_unmapped(
        self,
        *,
        unmapped_counter: Counter[str],
        unmapped_projects: dict[str, list[str]],
    ) -> None:
        """Escribe las etiquetas que el parser no reconoce."""
        self.stdout.write("")
        self.stdout.write("ETIQUETAS SIN MAPEAR")

        if not unmapped_counter:
            self.stdout.write(
                "  Ninguna. El catalogo cubre todas las "
                "descripciones revisadas."
            )
            return

        self.stdout.write(
            "  Agregalas a FIELD_ALIASES o a IGNORED_LABELS en "
            "description_parser.py\n"
        )

        for label, count in unmapped_counter.most_common():
            samples = unmapped_projects[label][:SAMPLE_PROJECT_COUNT]
            sample_text = ", ".join(samples)

            self.stdout.write(
                f"  {count:4}x  {label:32}  {sample_text}"
            )

    def report_coverage(
        self,
        *,
        field_projects: dict[str, set[str]],
        total_projects: int,
    ) -> None:
        """Escribe en cuántos proyectos aparece cada campo."""
        self.stdout.write("")
        self.stdout.write("COBERTURA POR CAMPO")

        if not total_projects:
            return

        ordered_fields = sorted(
            field_projects.items(),
            key=lambda item: len(item[1]),
            reverse=True,
        )

        for field_name, project_names in ordered_fields:
            found = len(project_names)
            percentage = round((found / total_projects) * 100)

            self.stdout.write(
                f"  {field_name:20} {found:4} de {total_projects}"
                f"  ({percentage}%)"
            )
