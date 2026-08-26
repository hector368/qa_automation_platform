"""Prueba local del endpoint de análisis AER."""

from __future__ import annotations

import os
from pathlib import Path

import django


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.local",
)

django.setup()


from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)
from django.test import Client
from django.urls import reverse


TEST_DIRECTORY = Path(__file__).resolve().parent

TEST_FILE_PATH = (
    TEST_DIRECTORY
    / "files"
    / "mcc_015_fdd.pdf"
)


def test_real_document() -> None:
    """Valida el análisis HTTP del FDD real."""
    if not TEST_FILE_PATH.is_file():
        raise FileNotFoundError(
            f"Test document was not found: "
            f"{TEST_FILE_PATH}"
        )

    uploaded_file = SimpleUploadedFile(
        name=TEST_FILE_PATH.name,
        content=TEST_FILE_PATH.read_bytes(),
        content_type="application/pdf",
    )

    client = Client(
        HTTP_HOST="localhost",
    )

    response = client.post(
        reverse(
            "aer_test_case:analyze"
        ),
        {
            "document": uploaded_file,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["ok"] is True

    assert (
        payload["filename"]
        == "mcc_015_fdd.pdf"
    )

    assert (
        payload["total_requirements"]
        == 50
    )

    requirements = payload[
        "requirements"
    ]

    assert len(requirements) == 50

    assert requirements[0] == {
        "requirement_id": "MCC.015.001",
        "title": "Download the MAE catalog",
    }

    assert requirements[-1] == {
        "requirement_id": "MCC.015.050",
        "title": (
            "Realizar orquestación "
            "multi-instancia de UNIGIS"
        ),
    }

    print()
    print(
        f"HTTP status: {response.status_code}"
    )

    print(
        f"Requerimientos recibidos: "
        f"{payload['total_requirements']}"
    )

    print(
        f"Primero: "
        f"{requirements[0]['requirement_id']}"
    )

    print(
        f"Último: "
        f"{requirements[-1]['requirement_id']}"
    )

    print()
    print(
        "AER analyze endpoint test: OK"
    )


def test_missing_document() -> None:
    """Valida la petición sin documento."""
    client = Client(
        HTTP_HOST="localhost",
    )

    response = client.post(
        reverse(
            "aer_test_case:analyze"
        ),
        {},
    )

    assert response.status_code == 400

    payload = response.json()

    assert payload["ok"] is False

    assert (
        payload["code"]
        == "ERR_NO_FILE"
    )


def run_tests() -> None:
    """Ejecuta las pruebas locales del endpoint."""
    test_real_document()
    test_missing_document()

    print(
        "AER analyze endpoint tests: OK"
    )


if __name__ == "__main__":
    run_tests()