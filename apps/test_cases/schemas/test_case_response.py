"""
Modelos de respuesta para la generación de casos de prueba.

Este módulo define la estructura tolerante recibida desde el modelo
y la estructura validada utilizada internamente por la aplicación.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


NonEmptyText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]


class RawTestStep(BaseModel):
    """Paso de prueba recibido directamente desde el modelo."""

    model_config = ConfigDict(
        extra="ignore",
    )

    action: str | None = None
    expected: str | None = None


class RawTestCase(BaseModel):
    """Caso de prueba tolerante recibido desde el modelo."""

    model_config = ConfigDict(
        extra="ignore",
    )

    classification: str | None = None
    objective: str | None = None
    expected_result: str | None = None

    preconditions: (
        list[str]
        | str
        | None
    ) = None

    steps: list[RawTestStep] | None = None


class RawNotTestableResult(BaseModel):
    """Información recibida para un requerimiento no testeable."""

    model_config = ConfigDict(
        extra="ignore",
    )

    objective: str | None = None
    reason: str | None = None
    missing_information: str | None = None
    required_definition: str | None = None

class RawRequirementReview(BaseModel):
    """Evaluación funcional recibida directamente desde el modelo."""

    model_config = ConfigDict(
        extra="ignore",
    )

    level: str | None = None
    reason: str | None = None

    areas: (
        list[str]
        | str
        | None
    ) = None

    functional_blocks: (
        list[str]
        | str
        | None
    ) = None

class RawRequirementResponse(BaseModel):
    """Respuesta tolerante completa recibida desde el modelo."""

    model_config = ConfigDict(
        extra="ignore",
    )

    test_cases: list[RawTestCase] | None = None
    not_testable: RawNotTestableResult | None = None
    requirement_review: RawRequirementReview | None = None


class TestStep(BaseModel):
    """Paso de prueba validado para uso interno."""

    model_config = ConfigDict(
        extra="forbid",
    )

    action: NonEmptyText
    expected: NonEmptyText


class TestCase(BaseModel):
    """Caso de prueba validado para uso interno."""

    model_config = ConfigDict(
        extra="forbid",
    )

    classification: Literal[
        "happy_path",
        "exception",
    ]

    objective: NonEmptyText
    expected_result: NonEmptyText

    preconditions: list[NonEmptyText] = Field(
        default_factory=list,
    )

    steps: list[TestStep] = Field(
        min_length=1,
    )


class NotTestableResult(BaseModel):
    """Resultado validado para un requerimiento no testeable."""

    model_config = ConfigDict(
        extra="forbid",
    )

    objective: NonEmptyText
    reason: NonEmptyText
    missing_information: NonEmptyText
    required_definition: NonEmptyText

class RequirementReview(BaseModel):
    """Evaluación funcional validada de un requerimiento."""

    model_config = ConfigDict(
        extra="forbid",
    )

    level: Literal[
        "adequate",
        "high_concentration",
        "saturated",
    ]

    reason: NonEmptyText

    areas: list[NonEmptyText] = Field(
        default_factory=list,
    )

    functional_blocks: list[NonEmptyText] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_review_content(
        self,
    ) -> "RequirementReview":
        """Valida el contenido requerido según el nivel."""

        if (
            self.level == "high_concentration"
            and not self.areas
        ):
            raise ValueError(
                "high_concentration requiere indicar "
                "las áreas de concentración."
            )

        if self.level == "saturated":
            if not self.areas:
                raise ValueError(
                    "saturated requiere indicar "
                    "las áreas de saturación."
                )

            if not self.functional_blocks:
                raise ValueError(
                    "saturated requiere indicar "
                    "los bloques funcionales."
                )

        return self

class RequirementTestCases(BaseModel):
    """Resultado funcional validado de un requerimiento."""

    model_config = ConfigDict(
        extra="forbid",
    )

    test_cases: list[TestCase] = Field(
        default_factory=list,
    )

    not_testable: NotTestableResult | None = None
    
    requirement_review: RequirementReview

    @model_validator(mode="after")
    def validate_result_mode(
        self,
    ) -> "RequirementTestCases":
        """
        Valida que exista un único tipo de resultado.

        Returns:
            Respuesta validada.

        Raises:
            ValueError: Cuando existen casos y resultado no testeable
                al mismo tiempo, o cuando ambos están ausentes.
        """
        has_test_cases = bool(
            self.test_cases
        )

        has_not_testable = (
            self.not_testable is not None
        )

        if has_test_cases == has_not_testable:
            raise ValueError(
                "La respuesta debe contener casos de prueba "
                "o un resultado no testeable, pero no ambos."
            )

        return self