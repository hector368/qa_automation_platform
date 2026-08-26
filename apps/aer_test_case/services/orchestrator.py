"""Orquestación de generación del AER Test Case Generator."""

from __future__ import annotations

from collections.abc import Iterator
from collections.abc import Sequence
from dataclasses import dataclass

from apps.aer_test_case.schemas.requirement_schema import (
    RequirementSegment,
)
from apps.aer_test_case.schemas.test_case_response import (
    AerTestCaseResponse,
)
from apps.aer_test_case.services.reference_resolver import (
    build_reference_context,
)
from apps.aer_test_case.services.reference_resolver import (
    resolve_referenced_requirements,
)
from apps.aer_test_case.services.requirement_segmenter import (
    segment_requirements,
)
from apps.aer_test_case.services.test_case_generator import (
    generate_requirement_test_cases,
)
from apps.aer_test_case.services.xlsx_generator import (
    generate_aer_xlsx,
)
from apps.test_cases.services.document_extractor import (
    extract_text_from_document,
)
from apps.test_cases.services.file_validator import (
    validate_upload_metadata,
)
from apps.test_cases.services.token_usage import (
    TokenUsage,
)


@dataclass(frozen=True, slots=True)
class PreparedAerDocument:
    """Representa un documento AER preparado para generar TCs."""

    filename: str
    requirements: tuple[RequirementSegment, ...]


@dataclass(frozen=True, slots=True)
class AerDocumentGeneration:
    """Representa el resultado final de una generación AER."""

    responses: tuple[AerTestCaseResponse, ...]
    usage: TokenUsage
    total_test_cases: int
    xlsx_bytes: bytes


def prepare_document(
    *,
    filename: str,
    file_bytes: bytes,
    max_upload_mb: int | None = None,
) -> PreparedAerDocument:
    """Valida, extrae y segmenta un documento AER."""
    if max_upload_mb is not None:
        validate_upload_metadata(
            filename=filename,
            file_size=len(file_bytes),
            max_upload_mb=max_upload_mb,
        )

    document_text = extract_text_from_document(
        filename=filename,
        file_bytes=file_bytes,
    )

    requirements = segment_requirements(
        document_text
    )

    return PreparedAerDocument(
        filename=filename,
        requirements=tuple(requirements),
    )


def analyze_document(
    *,
    filename: str,
    file_bytes: bytes,
    max_upload_mb: int,
) -> dict[str, object]:
    """Analiza un documento sin realizar llamadas a Claude."""
    prepared_document = prepare_document(
        filename=filename,
        file_bytes=file_bytes,
        max_upload_mb=max_upload_mb,
    )

    requirements = [
        {
            "requirement_id": requirement.requirement_id,
            "title": requirement.title,
        }
        for requirement in prepared_document.requirements
    ]

    return {
        "ok": True,
        "filename": prepared_document.filename,
        "total_requirements": len(requirements),
        "requirements": requirements,
    }


def generate_document(
    *,
    prepared_document: PreparedAerDocument,
    selected_requirement_ids: list[str] | None = None,
) -> AerDocumentGeneration:
    """Genera casos para los requerimientos seleccionados."""
    selected_requirements = _select_requirements(
        requirements=prepared_document.requirements,
        selected_requirement_ids=selected_requirement_ids,
    )

    responses: list[AerTestCaseResponse] = []

    total_usage = TokenUsage()

    for requirement in selected_requirements:
        referenced_requirements = (
            resolve_referenced_requirements(
                current_requirement=requirement,
                requirements=prepared_document.requirements,
            )
        )

        reference_context = build_reference_context(
            referenced_requirements
        )

        generation = generate_requirement_test_cases(
            requirement=requirement,
            referenced_requirements=reference_context,
        )

        responses.append(
            generation.response
        )

        total_usage = (
            total_usage
            + generation.usage
        )

    return build_document_generation(
        responses=responses,
        usage=total_usage,
    )

def iter_generate_document(
    *,
    prepared_document: PreparedAerDocument,
    selected_requirement_ids: list[str] | None = None,
) -> Iterator[dict[str, object]]:
    """Genera casos AER y emite eventos de progreso."""
    selected_requirements = _select_requirements(
        requirements=prepared_document.requirements,
        selected_requirement_ids=selected_requirement_ids,
    )

    total_requirements = len(
        selected_requirements
    )

    selected_ids = [
        requirement.requirement_id
        for requirement in selected_requirements
    ]

    responses: list[AerTestCaseResponse] = []

    total_usage = TokenUsage()

    yield {
        "type": "started",
        "ok": True,
        "total_requirements": total_requirements,
        "selected_requirements": selected_ids,
        "progress": 0,
    }

    for position, requirement in enumerate(
        selected_requirements,
        start=1,
    ):
        start_progress = round(
            (
                (position - 1)
                / total_requirements
            )
            * 100,
            2,
        )

        yield {
            "type": "requirement_started",
            "ok": True,
            "requirement_id": (
                requirement.requirement_id
            ),
            "requirement_title": requirement.title,
            "current": position,
            "total": total_requirements,
            "progress": start_progress,
        }

        referenced_requirements = (
            resolve_referenced_requirements(
                current_requirement=requirement,
                requirements=prepared_document.requirements,
            )
        )

        reference_context = build_reference_context(
            referenced_requirements
        )

        generation = generate_requirement_test_cases(
            requirement=requirement,
            referenced_requirements=reference_context,
        )

        responses.append(
            generation.response
        )

        total_usage = (
            total_usage
            + generation.usage
        )

        generated_test_cases = len(
            generation.response.test_cases
        )

        end_progress = round(
            (
                position
                / total_requirements
            )
            * 100,
            2,
        )

        yield {
            "type": "requirement_completed",
            "ok": True,
            "requirement_id": (
                requirement.requirement_id
            ),
            "requirement_title": requirement.title,
            "generated_test_cases": generated_test_cases,
            "is_testable": (
                generation.response.is_testable
            ),
            "current": position,
            "total": total_requirements,
            "progress": end_progress,
            "usage": total_usage.to_dict(),
        }

    final_generation = build_document_generation(
        responses=responses,
        usage=total_usage,
    )

    yield {
        "type": "completed",
        "ok": True,
        "progress": 100,
        "generation": final_generation,
    }

def build_document_generation(
    *,
    responses: Sequence[AerTestCaseResponse],
    usage: TokenUsage,
) -> AerDocumentGeneration:
    """Construye el resultado final y genera el archivo Excel."""
    response_tuple = tuple(
        responses
    )

    total_test_cases = sum(
        len(response.test_cases)
        for response in response_tuple
    )

    xlsx_bytes = generate_aer_xlsx(
        response_tuple
    )

    return AerDocumentGeneration(
        responses=response_tuple,
        usage=usage,
        total_test_cases=total_test_cases,
        xlsx_bytes=xlsx_bytes,
    )


def _select_requirements(
    *,
    requirements: tuple[RequirementSegment, ...],
    selected_requirement_ids: list[str] | None,
) -> tuple[RequirementSegment, ...]:
    """Obtiene los requerimientos solicitados."""
    if selected_requirement_ids is None:
        return requirements

    selected_ids = set(
        selected_requirement_ids
    )

    available_ids = {
        requirement.requirement_id
        for requirement in requirements
    }

    missing_ids = (
        selected_ids
        - available_ids
    )

    if missing_ids:
        missing_text = ", ".join(
            sorted(missing_ids)
        )

        raise ValueError(
            "Selected requirement IDs were not found: "
            f"{missing_text}."
        )

    return tuple(
        requirement
        for requirement in requirements
        if (
            requirement.requirement_id
            in selected_ids
        )
    )