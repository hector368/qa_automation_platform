"""Prueba local de extracción y segmentación de un FDD real."""

from pathlib import Path

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


def load_test_document() -> tuple[str, bytes]:
    """Carga el documento utilizado para la prueba local."""
    if not TEST_FILE_PATH.is_file():
        raise FileNotFoundError(
            f"Test document was not found: "
            f"{TEST_FILE_PATH}"
        )

    return (
        TEST_FILE_PATH.name,
        TEST_FILE_PATH.read_bytes(),
    )


def test_real_document() -> None:
    """Extrae y segmenta los requerimientos del FDD real."""
    filename, file_bytes = load_test_document()

    document_text = extract_text_from_document(
        filename=filename,
        file_bytes=file_bytes,
    )

    requirements = segment_requirements(
        document_text
    )

    if not requirements:
        raise AssertionError(
            "No requirements were detected."
        )

    print()
    print(
        f"Documento: {filename}"
    )
    print(
        f"Caracteres extraídos: {len(document_text)}"
    )
    print(
        f"Requerimientos detectados: "
        f"{len(requirements)}"
    )
    print()

    for requirement in requirements:
        print(
            f"{requirement.requirement_id} | "
            f"{requirement.title}"
        )

    target_requirement = next(
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

    if target_requirement is None:
        raise AssertionError(
            f"Requirement "
            f"{TARGET_REQUIREMENT_ID} "
            f"was not detected."
        )

    print()
    print(
        "Requerimiento objetivo encontrado:"
    )
    print(
        target_requirement.requirement_id
    )
    print(
        target_requirement.title
    )
    print()

    assert target_requirement.content
    assert (
        target_requirement.content.startswith(
            TARGET_REQUIREMENT_ID
        )
    )

    print(
        "AER real document test: OK"
    )


if __name__ == "__main__":
    test_real_document()