"""Prueba real de generación múltiple del orquestador AER."""

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

from apps.aer_test_case.services.orchestrator import (
    generate_document,
)
from apps.aer_test_case.services.orchestrator import (
    prepare_document,
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

OUTPUT_FILE_PATH = (
    TEST_DIRECTORY
    / "real_orchestrator_result.json"
)

SELECTED_REQUIREMENT_IDS = [
    "MCC.015.001",
    "MCC.015.018",
]


def run_test() -> None:
    """Genera dos requerimientos reales en una ejecución."""
    if not TEST_FILE_PATH.is_file():
        raise FileNotFoundError(
            f"Test document was not found: "
            f"{TEST_FILE_PATH}"
        )

    print()
    print(
        "Preparando documento..."
    )

    prepared_document = prepare_document(
        filename=TEST_FILE_PATH.name,
        file_bytes=TEST_FILE_PATH.read_bytes(),
    )

    print(
        f"Requerimientos detectados: "
        f"{len(prepared_document.requirements)}"
    )

    assert (
        len(prepared_document.requirements)
        == 50
    )

    print()
    print(
        "Requerimientos seleccionados:"
    )

    for requirement_id in SELECTED_REQUIREMENT_IDS:
        print(
            requirement_id
        )

    print()
    print(
        "Iniciando generación con Claude..."
    )
    print()

    generation = generate_document(
        prepared_document=prepared_document,
        selected_requirement_ids=(
            SELECTED_REQUIREMENT_IDS
        ),
    )

    assert len(generation.responses) == 2

    generated_ids = [
        response.requirement_id
        for response in generation.responses
    ]

    assert generated_ids == (
        SELECTED_REQUIREMENT_IDS
    )

    total_test_cases = sum(
        len(response.test_cases)
        for response in generation.responses
    )

    print()
    print(
        "Resultados:"
    )
    print()

    for response in generation.responses:
        print(
            f"{response.requirement_id} | "
            f"{response.requirement_title}"
        )

        print(
            f"Testeable: {response.is_testable}"
        )

        print(
            f"Casos generados: "
            f"{len(response.test_cases)}"
        )

        happy_path_count = sum(
            1
            for test_case in response.test_cases
            if test_case.priority == 1
        )

        exception_count = sum(
            1
            for test_case in response.test_cases
            if test_case.priority == 2
        )

        print(
            f"Happy Path: {happy_path_count}"
        )

        print(
            f"Excepciones: {exception_count}"
        )

        print()

    assert generation.usage.input_tokens > 0
    assert generation.usage.output_tokens > 0

    cost = calculate_token_cost(
        usage=generation.usage,
        input_rate_per_million=(
            settings.CLAUDE_INPUT_USD_PER_MTOK
        ),
        output_rate_per_million=(
            settings.CLAUDE_OUTPUT_USD_PER_MTOK
        ),
    )

    print(
        f"Total de casos: "
        f"{total_test_cases}"
    )

    print()
    print(
        "Tokens acumulados:"
    )

    print(
        json.dumps(
            generation.usage.to_dict(),
            indent=2,
        )
    )

    print()
    print(
        "Costo acumulado:"
    )

    print(
        cost.to_dict()[
            "total_usd_formatted"
        ]
    )

    output_data = {
        "requirements": [
            response.model_dump()
            for response in generation.responses
        ],
        "usage": generation.usage.to_dict(),
        "cost": cost.to_dict(),
        "total_test_cases": total_test_cases,
    }

    OUTPUT_FILE_PATH.write_text(
        json.dumps(
            output_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "Resultado completo guardado en:"
    )

    print(
        OUTPUT_FILE_PATH
    )

    print()
    print(
        "AER real orchestrator generation test: OK"
    )


if __name__ == "__main__":
    run_test()