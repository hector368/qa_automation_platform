"""Prueba real de integración AER con Claude."""

from __future__ import annotations

import json
import os

import django


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.local",
)

django.setup()


from django.conf import settings

from apps.aer_test_case.schemas.requirement_schema import (
    RequirementSegment,
)
from apps.aer_test_case.services.test_case_generator import (
    generate_requirement_test_cases,
)
from apps.test_cases.services.token_usage import (
    calculate_token_cost,
)


def build_sample_requirement() -> RequirementSegment:
    """Construye un requerimiento funcional de prueba."""
    return RequirementSegment(
        requirement_id="MCC.015.001",
        title="Download the MAE catalog",
        content=(
            "MCC.015.001 Download the MAE catalog\n\n"
            "The BOT accesses SharePoint and downloads "
            "the MAE Routes catalog from the Planning "
            "folder.\n\n"
            "Exception: If the catalog is not found in "
            "the specified location, the BOT suspends "
            "the execution and notifies the responsible "
            "user by email.\n\n"
            "Input: MAE Routes catalog.\n"
            "System: SharePoint."
        ),
    )


def run_test() -> None:
    """Ejecuta una generación real con Claude."""
    requirement = build_sample_requirement()

    print(
        "Procesando requerimiento:"
    )
    print(
        requirement.requirement_id
    )
    print()

    generation = generate_requirement_test_cases(
        requirement=requirement,
    )

    response_dict = (
        generation.response.model_dump()
    )

    print(
        "Respuesta validada:"
    )

    print(
        json.dumps(
            response_dict,
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
        generation.response.requirement_id
        == requirement.requirement_id
    )

    assert (
        generation.response.requirement_title
        == requirement.title
    )

    assert generation.response.test_cases

    for test_case in (
        generation.response.test_cases
    ):

        assert test_case.priority in (
            1,
            2,
        )

    print()
    print(
        "AER Claude integration test: OK"
    )


if __name__ == "__main__":
    run_test()