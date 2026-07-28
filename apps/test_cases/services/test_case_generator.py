"""
Generación de casos de prueba por requerimiento.

Este módulo utiliza bloques ya segmentados. No extrae documentos ni
atiende solicitudes HTTP.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from collections.abc import Iterator, Sequence
from typing import Any, Final

from django.conf import settings

from apps.test_cases.exceptions import (
    CsvGenerationError,
    EmptyGenerationError,
    GenerationValidationError,
    SelectedRequirementsNotFoundError,
)
from apps.test_cases.services.ado_csv import (
    dump_ado_rows,
    enforce_structure_and_titles,
    ensure_csv_header,
    parse_ado_rows,
)
from apps.test_cases.services.claude_client import (
    ClaudeResult,
    call_claude,
)
from apps.test_cases.services.context_builder import (
    build_context_pack,
)
from apps.test_cases.services.csv_statistics import (
    compute_csv_stats,
)
from apps.test_cases.services.prompt_loader import (
    load_test_cases_prompt,
)
from apps.test_cases.services.requirement_splitter import (
    RequirementBlock,
)
from apps.test_cases.services.response_parser import (
    extract_csv_only,
)
from apps.test_cases.services.token_usage import (
    TokenUsage,
    calculate_token_cost,
)


logger = logging.getLogger(__name__)

NO_TC_START_DEFAULT: Final[int] = 1
MAX_REPAIR_OUTPUT_CHARS: Final[int] = 30_000

REPAIR_INSTRUCTIONS: Final[str] = """
The previous response was not a valid Azure DevOps CSV.

Correct the response using these rules:

- Return ONLY CSV rows.
- Do not include Markdown.
- Do not include explanations.
- Do not include the header.
- Every row must contain EXACTLY 15 columns.
- Every row must contain EXACTLY 14 commas.
- Leave State, Area Path and Assigned To empty when unknown.
- Preserve the functional meaning of the generated test cases.
"""


def generate_test_cases(
    *,
    original_filename: str,
    project_id: str,
    context_text: str,
    blocks: Sequence[RequirementBlock],
    assigned_to: str,
    selected_requirements: list[int] | None = None,
) -> dict[str, Any]:
    """
    Ejecuta la generación completa sin exponer eventos de progreso.

    Esta función conserva el contrato síncrono utilizado por el endpoint
    /generate/.
    """
    final_result: dict[str, Any] | None = None

    for event in iter_generate_test_cases(
        original_filename=original_filename,
        project_id=project_id,
        context_text=context_text,
        blocks=blocks,
        assigned_to=assigned_to,
        selected_requirements=selected_requirements,
    ):
        if event.get("type") == "completed":
            result = event.get("result")

            if isinstance(result, dict):
                final_result = result

    if final_result is None:
        raise EmptyGenerationError(
            "La generación terminó sin un evento final."
        )

    return final_result


def iter_generate_test_cases(
    *,
    original_filename: str,
    project_id: str,
    context_text: str,
    blocks: Sequence[RequirementBlock],
    assigned_to: str,
    selected_requirements: list[int] | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Genera casos y emite eventos de progreso.

    Yields:
        Eventos de inicio, progreso y finalización.
    """
    start_time = time.perf_counter()

    clean_project_id = (project_id or "").strip()
    clean_assigned_to = (assigned_to or "").strip()

    if not clean_project_id:
        raise GenerationValidationError(
            "El Project ID está vacío."
        )

    if not clean_assigned_to:
        raise GenerationValidationError(
            "Assigned To está vacío."
        )

    filtered_blocks, missing_selected = _filter_blocks(
        blocks=blocks,
        selected_requirements=selected_requirements,
    )

    if not filtered_blocks:
        raise SelectedRequirementsNotFoundError(
            "La selección no coincide con los bloques disponibles."
        )

    prompt_text = load_test_cases_prompt()
    global_context = build_context_pack(
        context_text
    )

    usage_total = TokenUsage()
    generated_rows: list[list[str]] = []
    total_requirements = len(filtered_blocks)

    selected_numbers = [
        int(block.requirement_number)
        for block in filtered_blocks
    ]

    yield {
        "type": "started",
        "ok": True,
        "project_id": clean_project_id,
        "total_requirements": total_requirements,
        "selected_requirements": selected_numbers,
        "missing_selected": missing_selected,
        "progress": 0,
    }

    for position, block in enumerate(
        filtered_blocks,
        start=1,
    ):
        requirement_number = int(
            block.requirement_number
        )

        scenario_name = (
            block.scenario_name
            or "InputText"
        ).strip()

        yield {
            "type": "requirement_started",
            "ok": True,
            "requirement_number": requirement_number,
            "scenario_name": scenario_name,
            "current": position,
            "total": total_requirements,
            "progress": round(
                ((position - 1) / total_requirements) * 100,
                2,
            ),
        }

        user_text = _build_user_text(
            project_id=clean_project_id,
            requirement_number=requirement_number,
            scenario_name=scenario_name,
            global_context=global_context,
            input_text=block.input_text,
        )

        model_rows, model_usage = (
            _generate_rows_with_repair(
                system_prompt=prompt_text,
                user_text=user_text,
            )
        )

        usage_total = usage_total + model_usage

        normalized_rows, _ = enforce_structure_and_titles(
            model_rows,
            project_id=clean_project_id,
            requirement_number=requirement_number,
            tc_start=NO_TC_START_DEFAULT,
            state="Design",
            area_path=clean_project_id,
            assigned_to=clean_assigned_to,
        )

        generated_rows.extend(
            normalized_rows
        )

        generated_cases = _count_test_case_rows(
            normalized_rows
        )

        yield {
            "type": "requirement_completed",
            "ok": True,
            "requirement_number": requirement_number,
            "scenario_name": scenario_name,
            "generated_test_cases": generated_cases,
            "current": position,
            "total": total_requirements,
            "progress": round(
                (position / total_requirements) * 100,
                2,
            ),
            "usage": usage_total.to_dict(),
        }

    if not generated_rows:
        raise EmptyGenerationError(
            "No se generaron filas después de normalizar."
        )

    csv_body = dump_ado_rows(
        generated_rows
    ).strip()

    if not csv_body:
        raise EmptyGenerationError(
            "El CSV final está vacío."
        )

    csv_output = ensure_csv_header(
        csv_body
    )

    stats = compute_csv_stats(
        csv_output
    )

    stats["project_id"] = clean_project_id
    stats["area_path"] = clean_project_id
    stats["assigned_to"] = clean_assigned_to

    cost = calculate_token_cost(
        usage=usage_total,
        input_rate_per_million=(
            settings.CLAUDE_INPUT_USD_PER_MTOK
        ),
        output_rate_per_million=(
            settings.CLAUDE_OUTPUT_USD_PER_MTOK
        ),
    )

    elapsed = (
        time.perf_counter()
        - start_time
    )

    result = {
        "filename": _build_download_filename(
            original_filename
        ),
        "csv_out": csv_output,
        "usage": usage_total.to_dict(),
        "cost": cost.to_dict(),
        "elapsed": round(elapsed, 2),
        "stats": stats,
        "selected_requirements": selected_numbers,
        "missing_selected": missing_selected,
    }

    yield {
        "type": "completed",
        "ok": True,
        "progress": 100,
        "result": result,
    }


def _generate_rows_with_repair(
    *,
    system_prompt: str,
    user_text: str,
) -> tuple[list[list[str]], TokenUsage]:
    """
    Genera filas y realiza una reparación funcional cuando sea necesario.

    La segunda llamada solamente ocurre cuando Claude sí respondió,
    pero la respuesta no cumple el formato CSV.
    """
    first_result = call_claude(
        system_prompt=system_prompt,
        user_text=user_text,
    )

    try:
        rows = _parse_strict_rows(
            first_result.text
        )

        return rows, first_result.usage

    except ValueError as first_error:
        logger.warning(
            "La primera respuesta no fue CSV válido: %s",
            first_error,
        )

    repair_user_text = _build_repair_user_text(
        original_user_text=user_text,
        invalid_output=first_result.text,
    )

    second_result = call_claude(
        system_prompt=system_prompt,
        user_text=repair_user_text,
    )

    combined_usage = (
        first_result.usage
        + second_result.usage
    )

    try:
        repaired_rows = _parse_strict_rows(
            second_result.text
        )
    except ValueError as exc:
        raise CsvGenerationError(
            "La respuesta reparada tampoco cumple "
            "las 15 columnas requeridas."
        ) from exc

    return repaired_rows, combined_usage


def _parse_strict_rows(
    raw_response: str,
) -> list[list[str]]:
    """
    Extrae y valida estrictamente las filas de una respuesta.

    Raises:
        ValueError: Cuando no existe CSV o las filas no tienen
            exactamente quince columnas.
    """
    csv_text = extract_csv_only(
        raw_response
    ).strip()

    if not csv_text:
        raise ValueError(
            "La respuesta no contiene CSV."
        )

    rows = parse_ado_rows(
        csv_text,
        strict=True,
    )

    if not rows:
        raise ValueError(
            "La respuesta solo contiene el encabezado o está vacía."
        )

    return rows


def _build_user_text(
    *,
    project_id: str,
    requirement_number: int,
    scenario_name: str,
    global_context: str,
    input_text: str,
) -> str:
    """Construye el contrato de entrada esperado por el prompt."""
    return (
        f"IdProyecto: {project_id}\n"
        f"RequirementNumber: {requirement_number}\n"
        f"ScenarioName: {scenario_name}\n"
        f"NoTCStart: {NO_TC_START_DEFAULT}\n"
        f"GlobalContext:\n{global_context}\n"
        f"InputText:\n{input_text}\n"
    )


def _build_repair_user_text(
    *,
    original_user_text: str,
    invalid_output: str,
) -> str:
    """Incluye en la reparación la salida inválida anterior."""
    safe_invalid_output = (
        invalid_output
        or ""
    )[:MAX_REPAIR_OUTPUT_CHARS]

    return (
        f"{original_user_text}\n"
        f"{REPAIR_INSTRUCTIONS.strip()}\n\n"
        "Previous invalid output:\n"
        "<invalid_output>\n"
        f"{safe_invalid_output}\n"
        "</invalid_output>\n"
    )


def _filter_blocks(
    *,
    blocks: Sequence[RequirementBlock],
    selected_requirements: list[int] | None,
) -> tuple[list[RequirementBlock], list[int]]:
    """Filtra bloques y reporta selecciones inexistentes."""
    available_blocks = list(blocks)

    if not selected_requirements:
        return available_blocks, []

    selected_set = {
        int(number)
        for number in selected_requirements
    }

    available_numbers = {
        int(block.requirement_number)
        for block in available_blocks
    }

    missing_selected = sorted(
        selected_set - available_numbers
    )

    filtered_blocks = [
        block
        for block in available_blocks
        if int(block.requirement_number) in selected_set
    ]

    return filtered_blocks, missing_selected

def _count_test_case_rows(
    rows: Sequence[Sequence[str]],
) -> int:
    """Cuenta únicamente las filas principales Test Case."""
    return sum(
        1
        for row in rows
        if len(row) > 1
        and str(row[1]).strip().casefold()
        == "test case"
    )

def _build_download_filename(
    original_filename: str,
) -> str:
    """Construye un nombre seguro para Content-Disposition."""
    original_stem = Path(
        original_filename or ""
    ).stem

    safe_stem = re.sub(
        r"[^\w.-]+",
        "_",
        original_stem,
    ).strip("._")

    if not safe_stem:
        safe_stem = "test_cases"

    return f"{safe_stem}_TC.csv"