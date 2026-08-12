"""
Generación de casos de prueba por requerimiento.

Este módulo coordina Claude, validación funcional y construcción
del archivo XLSX. No extrae documentos ni atiende solicitudes HTTP.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, Final

from django.conf import settings
from pydantic import ValidationError

from apps.test_cases.exceptions import (
    EmptyGenerationError,
    GenerationValidationError,
    JsonGenerationError,
    SelectedRequirementsNotFoundError,
)
from apps.test_cases.schemas.test_case_response import (
    RawRequirementResponse,
    RequirementTestCases,
)
from apps.test_cases.services.ado_rows_builder import (
    build_ado_rows,
)
from apps.test_cases.services.claude_client import (
    call_claude,
)
from apps.test_cases.services.context_builder import (
    build_context_pack,
)
from apps.test_cases.services.generation_statistics import (
    compute_generation_stats,
)
from apps.test_cases.services.json_response_parser import (
    extract_json_object,
)
from apps.test_cases.services.prompt_loader import (
    load_test_cases_prompt,
)
from apps.test_cases.services.requirement_splitter import (
    RequirementBlock,
)
from apps.test_cases.services.test_case_normalizer import (
    normalize_requirement_response,
)
from apps.test_cases.services.token_usage import (
    TokenUsage,
    calculate_token_cost,
)
from apps.test_cases.services.xlsx_generator import (
    generate_xlsx,
)


logger = logging.getLogger(__name__)

MAX_REPAIR_OUTPUT_CHARS: Final[int] = 30_000

REPAIR_INSTRUCTIONS: Final[str] = """
La respuesta anterior no cumple el contrato JSON requerido.

Corrige únicamente la estructura necesaria.

Reglas:
- Devuelve únicamente un objeto JSON.
- No uses Markdown.
- No agregues explicaciones.
- Conserva el significado funcional original.
- No inventes información.
- Usa únicamente test_cases, not_testable y requirement_review
  como propiedades raíz.
- classification solo puede ser happy_path o exception.
- Cada paso debe contener action y expected.
- requirement_review es obligatorio.
- requirement_review debe contener level, reason, areas y
  functional_blocks.
- requirement_review.level solo puede ser adequate,
  high_concentration o saturated.
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
    """Ejecuta la generación completa sin eventos de progreso."""
    final_result: dict[str, Any] | None = None

    for event in iter_generate_test_cases(
        original_filename=original_filename,
        project_id=project_id,
        context_text=context_text,
        blocks=blocks,
        assigned_to=assigned_to,
        selected_requirements=selected_requirements,
    ):
        if event.get("type") != "completed":
            continue

        result = event.get(
            "result"
        )

        if isinstance(
            result,
            dict,
        ):
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
    """Genera casos y emite eventos de progreso."""
    start_time = time.perf_counter()

    clean_project_id = (
        project_id
        or ""
    ).strip()

    clean_assigned_to = (
        assigned_to
        or ""
    ).strip()

    if not clean_project_id:
        raise GenerationValidationError(
            "Project ID está vacío."
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

    generated_results: list[
        tuple[int, str, RequirementTestCases]
    ] = []

    total_requirements = len(
        filtered_blocks
    )

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
                (
                    (position - 1)
                    / total_requirements
                )
                * 100,
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

        model_result, model_usage = (
            _generate_result_with_repair(
                system_prompt=prompt_text,
                user_text=user_text,
            )
        )

        usage_total = (
            usage_total
            + model_usage
        )

        rows = build_ado_rows(
            result=model_result,
            project_id=clean_project_id,
            requirement_number=requirement_number,
            scenario_name=scenario_name,
            assigned_to=clean_assigned_to,
        )

        generated_rows.extend(
            rows
        )

        generated_results.append(
            (
                requirement_number,
                scenario_name,
                model_result,
            )
        )

        generated_cases = (
            _count_generated_test_cases(
                model_result
            )
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
                (
                    position
                    / total_requirements
                )
                * 100,
                2,
            ),
            "usage": usage_total.to_dict(),
        }

    if not generated_rows:
        raise EmptyGenerationError(
            "No se generaron casos de prueba."
        )

    xlsx_bytes = generate_xlsx(
        generated_rows
    )

    if not xlsx_bytes:
        raise EmptyGenerationError(
            "El archivo XLSX final está vacío."
        )

    stats = compute_generation_stats(
        generated_results
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
        "xlsx_bytes": xlsx_bytes,
        "usage": usage_total.to_dict(),
        "cost": cost.to_dict(),
        "elapsed": round(
            elapsed,
            2,
        ),
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


def _generate_result_with_repair(
    *,
    system_prompt: str,
    user_text: str,
) -> tuple[RequirementTestCases, TokenUsage]:
    """Genera y realiza un único intento de reparación."""
    first_result = call_claude(
        system_prompt=system_prompt,
        user_text=user_text,
    )

    try:
        parsed_result = _parse_model_result(
            first_result.text
        )

        return (
            parsed_result,
            first_result.usage,
        )

    except (
        ValueError,
        ValidationError,
    ) as first_error:
        logger.warning(
            "La primera respuesta JSON fue inválida: %s",
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
        repaired_result = _parse_model_result(
            second_result.text
        )
    except (
        ValueError,
        ValidationError,
    ) as exc:
        raise JsonGenerationError(
            "La respuesta reparada tampoco cumple "
            "el contrato JSON requerido."
        ) from exc

    return (
        repaired_result,
        combined_usage,
    )


def _parse_model_result(
    raw_response: str,
) -> RequirementTestCases:
    """Extrae, normaliza y valida una respuesta JSON."""
    payload = extract_json_object(
        raw_response
    )

    raw_result = (
        RawRequirementResponse.model_validate(
            payload
        )
    )

    return normalize_requirement_response(
        raw_result
    )


def _build_user_text(
    *,
    project_id: str,
    requirement_number: int,
    scenario_name: str,
    global_context: str,
    input_text: str,
) -> str:
    """Construye el contrato enviado al modelo."""
    return (
        f"IdProyecto: {project_id}\n"
        f"RequirementNumber: {requirement_number}\n"
        f"ScenarioName: {scenario_name}\n"
        "GlobalContext:\n"
        f"{global_context}\n"
        "InputText:\n"
        f"{input_text}\n"
    )


def _build_repair_user_text(
    *,
    original_user_text: str,
    invalid_output: str,
) -> str:
    """Construye la solicitud del único intento de reparación."""
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
    available_blocks = list(
        blocks
    )

    if not selected_requirements:
        return (
            available_blocks,
            [],
        )

    selected_set = {
        int(number)
        for number in selected_requirements
    }

    available_numbers = {
        int(block.requirement_number)
        for block in available_blocks
    }

    missing_selected = sorted(
        selected_set
        - available_numbers
    )

    filtered_blocks = [
        block
        for block in available_blocks
        if int(
            block.requirement_number
        ) in selected_set
    ]

    return (
        filtered_blocks,
        missing_selected,
    )


def _count_generated_test_cases(
    result: RequirementTestCases,
) -> int:
    """Cuenta los casos producidos para un requerimiento."""
    if result.not_testable is not None:
        return 1

    return len(
        result.test_cases
    )


def _build_download_filename(
    original_filename: str,
) -> str:
    """Construye el nombre seguro del archivo XLSX."""
    original_stem = Path(
        original_filename
        or ""
    ).stem

    safe_stem = re.sub(
        r"[^\w.-]+",
        "_",
        original_stem,
    ).strip("._")

    if not safe_stem:
        safe_stem = "test_cases"

    return (
        f"{safe_stem}_TC.xlsx"
    )