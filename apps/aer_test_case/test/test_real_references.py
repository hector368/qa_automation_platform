"""Prueba de referencias usando el FDD real."""

from pathlib import Path

from apps.aer_test_case.services.reference_resolver import (
    build_reference_context,
)
from apps.aer_test_case.services.reference_resolver import (
    resolve_referenced_requirements,
)
from apps.aer_test_case.services.requirement_segmenter import (
    segment_requirements,
)
from apps.test_cases.services.document_extractor import (
    extract_text_from_document,
)


TEST_DIRECTORY = Path(__file__).resolve().parent

TEST_FILE_PATH = (
    TEST_DIRECTORY
    / "files"
    / "mcc_015_fdd.pdf"
)

TARGET_REQUIREMENT_ID = "MCC.015.050"


def run_test() -> None:
    """Resuelve referencias reales del requerimiento 50."""
    file_bytes = TEST_FILE_PATH.read_bytes()

    document_text = extract_text_from_document(
        filename=TEST_FILE_PATH.name,
        file_bytes=file_bytes,
    )

    requirements = segment_requirements(
        document_text
    )

    current_requirement = next(
        requirement
        for requirement in requirements
        if (
            requirement.requirement_id
            == TARGET_REQUIREMENT_ID
        )
    )

    references = resolve_referenced_requirements(
        current_requirement=current_requirement,
        requirements=requirements,
    )

    reference_ids = [
        requirement.requirement_id
        for requirement in references
    ]

    print()
    print(
        f"Requerimiento actual: "
        f"{current_requirement.requirement_id}"
    )

    print(
        f"Referencias detectadas: "
        f"{len(reference_ids)}"
    )

    print()

    for requirement_id in reference_ids:
        print(
            requirement_id
        )

    assert len(reference_ids) == 16

    assert reference_ids[0] == "MCC.015.034"

    assert reference_ids[-1] == "MCC.015.049"

    context = build_reference_context(
        references
    )

    assert context
    assert "MCC.015.034" in context
    assert "MCC.015.049" in context

    print()
    print(
        f"Caracteres de contexto: {len(context)}"
    )

    print()
    print(
        "AER real reference test: OK"
    )


if __name__ == "__main__":
    run_test()