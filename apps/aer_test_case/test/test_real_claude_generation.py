"""Prueba real del generador AER usando un FDD completo."""

from __future__ import annotations

import json
import os
from pathlib import Path

import django


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.local",
)

django.setup()


from django.conf import settings

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
from apps.test_cases.services.document_extractor import (
    extract_text_from_document,
)
from apps.test_cases.services.token_usage import (
    calculate_token_cost,
)


TEST_DIRECTORY = Path(__file__).resolve().parent

TEST_FILE_PATH = (
    TEST_DIRECTORY
    / "files"
    / "mcc_015_fdd.pdf"
)

TARGET_REQUIREMENT_ID = "MCC.015.050"


def load_real_requirement():
    """Extrae el requerimiento objetivo y sus referencias."""
    if not TEST_FILE_PATH.is_file():
        raise FileNotFoundError(
            f"Test document was not found: "
            f"{TEST_FILE_PATH}"
        )

    file_bytes = TEST_FILE_PATH.read_bytes()

    document_text = extract_text_from_document(
        filename=TEST_FILE_PATH.name,
        file_bytes=file_bytes,
    )

    requirements = segment_requirements(
        document_text
    )

    current_requirement = next(
        (
            requirement
            for requirement in requirements
            if (
                requirement.requirement_id
                == TARGET_REQUIREMENT_ID
            )
        ),
        None,
    )

    if current_requirement is None:
        raise AssertionError(
            f"Requirement "
            f"{TARGET_REQUIREMENT_ID} "
            f"was not detected."
        )

    referenced_requirements = (
        resolve_referenced_requirements(
            current_requirement=current_requirement,
            requirements=requirements,
        )
    )

    reference_context = build_reference_context(
        referenced_requirements
    )

    return (
        current_requirement,
        referenced_requirements,
        reference_context,
    )


def run_test() -> None:
    """Genera casos AER desde el requerimiento real."""
    (
        current_requirement,
        referenced_requirements,
        reference_context,
    ) = load_real_requirement()

    reference_ids = [
        requirement.requirement_id
        for requirement in referenced_requirements
    ]

    print()
    print(
        "Requerimiento procesado:"
    )
    print(
        current_requirement.requirement_id
    )
    print(
        current_requirement.title
    )

    print()
    print(
        f"Caracteres del requerimiento: "
        f"{len(current_requirement.content)}"
    )

    print(
        f"Referencias encontradas: "
        f"{len(reference_ids)}"
    )

    print(
        f"Caracteres de contexto: "
        f"{len(reference_context or '')}"
    )

    print()
    print(
        "Referencias:"
    )

    for requirement_id in reference_ids:
        print(
            requirement_id
        )

    assert len(reference_ids) == 16

    assert reference_ids[0] == "MCC.015.034"

    assert reference_ids[-1] == "MCC.015.049"

    assert "MCC.015.026" not in reference_ids

    print()
    print(
        "Enviando requerimiento real a Claude..."
    )
    print()

    generation = generate_requirement_test_cases(
        requirement=current_requirement,
        referenced_requirements=reference_context,
    )

    response = generation.response

    print(
        "Respuesta validada:"
    )

    print(
        json.dumps(
            response.model_dump(),
            ensure_ascii=False,
            indent=2,
        )
    )

    cost = calculate_token_cost(
        usage=generation.usage,
        input_rate_per_million=(
            settings.CLAUDE_INPUT_USD_PER_MTOK
        ),
        output_rate_per_million=(
            settings.CLAUDE_OUTPUT_USD_PER_MTOK
        ),
    )

    print()
    print(
        "Tokens:"
    )

    print(
        json.dumps(
            generation.usage.to_dict(),
            indent=2,
        )
    )

    print()
    print(
        "Costo estimado:"
    )

    print(
        cost.to_dict()[
            "total_usd_formatted"
        ]
    )

    assert (
        response.requirement_id
        == TARGET_REQUIREMENT_ID
    )

    assert (
        response.requirement_title
        == current_requirement.title
    )

    if response.is_testable:
        assert response.test_cases

    for test_case in response.test_cases:
        assert test_case.priority in (
            1,
            2,
        )

        if test_case.priority == 1:
            assert (
                test_case.exception_text
                is None
            )

        if test_case.priority == 2:
            assert (
                test_case.exception_text
                is not None
            )

    print()
    print(
        "AER real Claude generation test: OK"
    )


if __name__ == "__main__":
    run_test()