"""Esquemas de respuesta para excepciones AER."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from apps.aer_test_case.schemas.test_case_response import (
    AerTestCase,
)


ExceptionType = Literal[
    "business",
    "system",
]


class AerExceptionResult(BaseModel):
    """Representa una excepción identificada por Claude."""

    model_config = ConfigDict(
        extra="forbid",
    )

    exception_id: str = Field(
        min_length=1,
    )

    exception_type: ExceptionType

    exception_name: str = Field(
        min_length=1,
    )

    test_cases: list[AerTestCase] = Field(
        min_length=1,
    )

    @field_validator(
        "exception_id",
        "exception_name",
        mode="before",
    )
    @classmethod
    def normalize_text(
        cls,
        value: object,
    ) -> object:
        """Normaliza textos identificados por Claude."""
        if not isinstance(value, str):
            return value

        return value.strip()


class AerExceptionsPayload(BaseModel):
    """Representa todas las excepciones detectadas por Claude."""

    model_config = ConfigDict(
        extra="forbid",
    )

    exceptions: list[AerExceptionResult]