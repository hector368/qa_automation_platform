"""Esquemas de respuesta del AER Test Case Generator."""

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator


PriorityType = Literal[1, 2]


class AerTestCase(BaseModel):
    """Representa un caso de prueba generado para AER."""

    model_config = ConfigDict(
        extra="forbid",
    )

    description: str = Field(
        min_length=1,
    )
    expected_result: str = Field(
        min_length=1,
    )
    exception_text: str | None = None
    input: str | None = None
    comments: str | None = None
    priority: PriorityType

    @field_validator(
        "description",
        "expected_result",
        "exception_text",
        "input",
        "comments",
        mode="before",
    )
    @classmethod
    def normalize_text(
        cls,
        value: object,
    ) -> object:
        """Normaliza valores de texto devueltos por el modelo."""
        if value is None:
            return None

        if not isinstance(value, str):
            return value

        normalized_value = value.strip()

        if not normalized_value:
            return None

        return normalized_value

    @model_validator(mode="after")
    def validate_priority(
        self,
    ) -> "AerTestCase":
        """Valida la relación entre prioridad y excepción."""
        if (
            self.priority == 1
            and self.exception_text
        ):
            raise ValueError(
                "Priority 1 represents a Happy Path and "
                "cannot include exception text."
            )

        if (
            self.priority == 2
            and not self.exception_text
        ):
            raise ValueError(
                "Priority 2 represents an Exception and "
                "must include exception text."
            )

        return self


class AerTestCasePayload(BaseModel):
    """Representa únicamente el contenido generado por Claude."""

    model_config = ConfigDict(
        extra="forbid",
    )

    is_testable: bool
    not_testable_reason: str | None = None
    test_cases: list[AerTestCase]

    @field_validator(
        "not_testable_reason",
        mode="before",
    )
    @classmethod
    def normalize_payload_text(
        cls,
        value: object,
    ) -> object:
        """Normaliza textos generales generados por Claude."""
        if value is None:
            return None

        if not isinstance(value, str):
            return value

        normalized_value = value.strip()

        if not normalized_value:
            return None

        return normalized_value

    @model_validator(mode="after")
    def validate_testability(
        self,
    ) -> "AerTestCasePayload":
        """Valida coherencia entre testabilidad y casos."""
        if self.is_testable and not self.test_cases:
            raise ValueError(
                "A testable requirement must contain "
                "at least one test case."
            )

        if (
            not self.is_testable
            and self.test_cases
        ):
            raise ValueError(
                "A non-testable requirement cannot "
                "contain test cases."
            )

        if (
            not self.is_testable
            and not self.not_testable_reason
        ):
            raise ValueError(
                "A non-testable requirement must "
                "include a reason."
            )

        if (
            self.is_testable
            and self.not_testable_reason
        ):
            raise ValueError(
                "A testable requirement cannot include "
                "a not-testable reason."
            )

        return self


class AerTestCaseResponse(AerTestCasePayload):
    """Representa el resultado final asociado al requerimiento."""

    requirement_id: str = Field(
        min_length=1,
    )
    requirement_title: str = Field(
        min_length=1,
    )

    @field_validator(
        "requirement_id",
        "requirement_title",
        mode="before",
    )
    @classmethod
    def normalize_requirement_text(
        cls,
        value: object,
    ) -> object:
        """Normaliza los metadatos del requerimiento."""
        if not isinstance(value, str):
            return value

        return value.strip()