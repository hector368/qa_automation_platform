"""Pruebas locales del segmentador de requerimientos."""

from apps.aer_test_case.exceptions import (
    RequirementSegmentationError,
)
from apps.aer_test_case.services.requirement_segmenter import (
    segment_requirements,
)


def test_valid_requirements() -> None:
    """Valida la segmentación de IDs esperados."""
    document_text = """
General project information.

MCC.015.001 Download the MAE catalog

The BOT downloads the MAE Routes catalog.

MCC.015.002 Consult the MAE catalog

The BOT validates the required columns.

MCC.015.050 Realizar orquestación multi-instancia de UNIGIS

El BOT ejecuta la orquestación.
"""

    requirements = segment_requirements(
        document_text
    )

    assert len(requirements) == 3

    assert (
        requirements[0].requirement_id
        == "MCC.015.001"
    )

    assert (
        requirements[1].requirement_id
        == "MCC.015.002"
    )

    assert (
        requirements[2].requirement_id
        == "MCC.015.050"
    )


def test_different_project_id() -> None:
    """Valida que el detector no dependa de MCC."""
    document_text = """
ABC.020.001 First requirement

Requirement content.

ABC.020.002 Second requirement

Requirement content.
"""

    requirements = segment_requirements(
        document_text
    )

    requirement_ids = [
        requirement.requirement_id
        for requirement in requirements
    ]

    assert requirement_ids == [
        "ABC.020.001",
        "ABC.020.002",
    ]


def test_internal_reference() -> None:
    """Valida que REQ13 no cree un segmento nuevo."""
    document_text = """
MCC.015.018 Monitor MIP Progress

The delivery date follows the rule defined in REQ13.

MCC.015.019 Solve Delivery Problems

The BOT handles delivery problems.
"""

    requirements = segment_requirements(
        document_text
    )

    assert len(requirements) == 2


def test_empty_document() -> None:
    """Valida el error esperado para texto vacío."""
    try:
        segment_requirements("")
    except RequirementSegmentationError:
        return

    raise AssertionError(
        "An empty document must raise "
        "RequirementSegmentationError."
    )


def test_document_without_ids() -> None:
    """Valida el error cuando no existen IDs."""
    try:
        segment_requirements(
            "Document without requirement IDs."
        )
    except RequirementSegmentationError:
        return

    raise AssertionError(
        "A document without IDs must raise "
        "RequirementSegmentationError."
    )

def test_last_requirement_section_end() -> None:
    """Valida que el último RQ no absorba secciones posteriores."""
    document_text = """
4.20 Final process section

MCC.015.049 Notify results

The BOT sends the final notification.

MCC.015.050 Execute orchestration

The BOT orchestrates available instances.
The process follows RQ 34 to RQ 49.

5. Exceptions

Business Exceptions

If an incident occurs, follow REQ 26.
"""

    requirements = segment_requirements(
        document_text
    )

    assert len(requirements) == 2

    last_requirement = requirements[-1]

    assert (
        last_requirement.requirement_id
        == "MCC.015.050"
    )

    assert (
        "RQ 34 to RQ 49"
        in last_requirement.content
    )

    assert (
        "5. Exceptions"
        not in last_requirement.content
    )

    assert (
        "REQ 26"
        not in last_requirement.content
    )

def run_tests() -> None:
    """Ejecuta las pruebas locales del segmentador."""
    test_valid_requirements()
    test_different_project_id()
    test_internal_reference()
    test_empty_document()
    test_document_without_ids()
    test_last_requirement_section_end()

    print(
        "Requirement segmenter tests: OK"
    )


if __name__ == "__main__":
    run_tests()