"""Pruebas locales del orquestador AER."""

from pathlib import Path

from apps.aer_test_case.services.orchestrator import (
    prepare_document,
)


TEST_DIRECTORY = Path(__file__).resolve().parent

TEST_FILE_PATH = (
    TEST_DIRECTORY
    / "files"
    / "mcc_015_fdd.pdf"
)


def test_prepare_real_document() -> None:
    """Valida la preparación del FDD real."""
    prepared_document = prepare_document(
        filename=TEST_FILE_PATH.name,
        file_bytes=TEST_FILE_PATH.read_bytes(),
    )

    assert (
        len(prepared_document.requirements)
        == 50
    )

    assert (
        prepared_document
        .requirements[0]
        .requirement_id
        == "MCC.015.001"
    )

    assert (
        prepared_document
        .requirements[-1]
        .requirement_id
        == "MCC.015.050"
    )


def run_tests() -> None:
    """Ejecuta las pruebas locales del orquestador."""
    test_prepare_real_document()

    print(
        "AER orchestrator tests: OK"
    )


if __name__ == "__main__":
    run_tests()