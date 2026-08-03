"""
Esquemas de validación para el análisis de documentos PDD/FDD.

Este módulo define el contrato JSON esperado del análisis realizado por
Claude sobre el PDD/FDD utilizado por el generador PEP.
"""
from __future__ import annotations

import logging
from math import ceil
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from apps.pep.exceptions import ResponseParsingError


logger = logging.getLogger(__name__)

AnalysisStatus = Literal["completado"]
CalculationStatus = Literal["ok", "error_validacion"]
StressBase = Literal["periodo_normal", "periodo_maximo"]
TechnologyDetection = Literal["explicita", "inferida", "no_encontrada"]

MissingField = Literal[
    "descripcion_breve_proceso",
    "calendario_frecuencia",
    "cantidad_periodo_normal.cantidad",
]

CalculationType = Literal["estres", "verificacion"]

PhaseCode = Literal[
    "planificacion",
    "preparacion",
    "ejecucion",
    "cierre_uat",
]

class TechnologyData(BaseModel):
    """
    Tecnología detectada desde el PDD/FDD.

    La tecnología debe representar la herramienta, plataforma, framework,
    producto o entorno usado para construir la solución.
    """

    model_config = ConfigDict(extra="forbid")

    valor: str | None
    tipo_deteccion: TechnologyDetection
    justificacion: str | None

    @model_validator(mode="after")
    def validate_technology_consistency(self) -> "TechnologyData":
        """
        Valida coherencia entre valor, tipo de detección y justificación.
        """
        if self.tipo_deteccion == "no_encontrada":
            if self.valor is not None:
                raise ValueError(
                    "tecnologia.valor debe ser null cuando "
                    "tipo_deteccion es no_encontrada."
                )

            if self.justificacion is not None:
                raise ValueError(
                    "tecnologia.justificacion debe ser null cuando "
                    "tipo_deteccion es no_encontrada."
                )

            return self

        if not (self.valor or "").strip():
            raise ValueError(
                "tecnologia.valor es obligatorio cuando la tecnología "
                "fue explícita o inferida."
            )

        if self.tipo_deteccion == "inferida":
            if not (self.justificacion or "").strip():
                raise ValueError(
                    "tecnologia.justificacion es obligatoria cuando "
                    "la tecnología fue inferida."
                )

        return self


class ProcessQuantityData(BaseModel):
    """
    Cantidad de elementos procesados durante un periodo.
    """

    model_config = ConfigDict(extra="forbid")

    cantidad: float | None = Field(default=None, gt=0)
    unidad_elemento: str | None = None

    @field_validator("unidad_elemento")
    @classmethod
    def clean_unit(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Limpia la unidad del elemento procesado.
        """
        if value is None:
            return None

        clean_value = " ".join(value.split())
        return clean_value or None

class PhaseSupplyContextData(BaseModel):
    """
    Contexto documental de los insumos para una fase de pruebas.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    frecuencia: str | None = None
    tipo_dato: str | None = None
    caracteristicas: list[str] = Field(
        default_factory=list,
    )

    @field_validator(
        "frecuencia",
        "tipo_dato",
    )
    @classmethod
    def clean_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Limpia valores textuales opcionales.
        """
        if value is None:
            return None

        clean_value = " ".join(
            value.split()
        )

        return clean_value or None

    @field_validator(
        "caracteristicas",
        mode="before",
    )
    @classmethod
    def normalize_characteristics(
        cls,
        value: Any,
    ) -> Any:
        """
        Convierte características nulas o individuales a una lista.
        """
        if value is None:
            return []

        if isinstance(
            value,
            str,
        ):
            clean_value = " ".join(
                value.split()
            )

            if not clean_value:
                return []

            return [
                clean_value,
            ]

        return value

    @field_validator(
        "caracteristicas"
    )
    @classmethod
    def clean_characteristics(
        cls,
        values: list[str],
    ) -> list[str]:
        """
        Limpia características y elimina duplicados.
        """
        characteristics: list[str] = []
        seen: set[str] = set()

        for value in values:
            clean_value = " ".join(
                (value or "").split()
            )

            if not clean_value:
                continue

            comparison_value = (
                clean_value.casefold()
            )

            if comparison_value in seen:
                continue

            seen.add(
                comparison_value
            )

            characteristics.append(
                clean_value
            )

        return characteristics

class SupplyPhasesContextData(BaseModel):
    """
    Contexto documental de los insumos por fase de pruebas.

    La ausencia de estos datos no bloquea el cálculo matemático.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    planificacion: PhaseSupplyContextData = Field(
        default_factory=PhaseSupplyContextData,
    )

    preparacion: PhaseSupplyContextData = Field(
        default_factory=PhaseSupplyContextData,
    )

    ejecucion: PhaseSupplyContextData = Field(
        default_factory=PhaseSupplyContextData,
    )

    cierre_uat: PhaseSupplyContextData = Field(
        default_factory=PhaseSupplyContextData,
    )

    @field_validator(
        "planificacion",
        "preparacion",
        "ejecucion",
        "cierre_uat",
        mode="before",
    )
    @classmethod
    def normalize_phase_context(
        cls,
        value: Any,
    ) -> Any:
        """
        Convierte una fase nula en un contexto vacío.
        """
        if value is None:
            return {}

        return value

class ProcessContextData(BaseModel):
    """
    Contexto operativo y volumétrico extraído del PDD/FDD.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    descripcion_breve_proceso: str | None = None
    calendario_frecuencia: str | None = None
    cantidad_periodo_normal: ProcessQuantityData
    cantidad_periodo_maximo: ProcessQuantityData
    contexto_insumos_por_fase: SupplyPhasesContextData = Field(
        default_factory=SupplyPhasesContextData,
    )

    @field_validator(
        "descripcion_breve_proceso",
        "calendario_frecuencia",
    )
    @classmethod
    def clean_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Limpia valores textuales opcionales.
        """
        if value is None:
            return None

        clean_value = " ".join(
            value.split()
        )

        return clean_value or None

    @field_validator(
        "contexto_insumos_por_fase",
        mode="before",
    )
    @classmethod
    def normalize_supply_phases_context(
        cls,
        value: Any,
    ) -> Any:
        """
        Convierte un contexto de fases nulo en un objeto vacío.
        """
        if value is None:
            return {}

        return value

class PercentageQuantityData(BaseModel):
    """
    Resultado de un cálculo porcentual simple.
    """

    model_config = ConfigDict(extra="forbid")

    porcentaje: int = Field(ge=0)
    cantidad: int = Field(ge=0)


class TypedPercentageQuantityData(BaseModel):
    """
    Resultado porcentual asociado a un tipo de prueba.
    """

    model_config = ConfigDict(extra="forbid")

    tipo: CalculationType
    porcentaje: int = Field(ge=0)
    cantidad: int = Field(ge=0)


class DevelopmentPlanData(BaseModel):
    """
    Plan de insumos para las fases de Development.
    """

    model_config = ConfigDict(extra="forbid")

    fase_1: PercentageQuantityData
    fase_2: PercentageQuantityData
    fase_3: TypedPercentageQuantityData


class DeploymentPlanData(BaseModel):
    """
    Insumos para Deployment/UAT.

    Deployment debe considerar únicamente el escenario productivo al 120%.
    """

    model_config = ConfigDict(extra="forbid")

    uat_productivo: TypedPercentageQuantityData


class CalculationTraceData(BaseModel):
    """
    Trazabilidad matemática de un cálculo de insumos.
    """

    model_config = ConfigDict(extra="forbid")

    calculo: str | None = None
    valor_base: float = Field(ge=0)
    porcentaje_aplicado: int = Field(ge=0)
    resultado_sin_redondear: float = Field(ge=0)
    resultado_final: int = Field(ge=0)

class SupplyPhaseData(BaseModel):
    """
    Fila final del plan de insumos por fase de pruebas.
    """

    model_config = ConfigDict(extra="forbid")

    fase: PhaseCode
    fase_proceso: str
    nivel_prueba: str
    cantidad: int = Field(ge=0)
    unidad_elemento: str | None = None
    porcentaje_aplicado: int = Field(ge=0)
    frecuencia: str | None = None
    tipo_dato: str | None = None
    caracteristicas: list[str] = Field(
        default_factory=list,
    )

class SupplyPlanData(BaseModel):
    """
    Plan calculado de insumos para pruebas.
    """

    model_config = ConfigDict(extra="forbid")

    nombre_proceso: str | None = None
    frecuencia: str | None = None
    unidad_elemento: str | None = None
    insumos_base_periodo_normal: int = Field(ge=0)
    insumos_estres_120: int = Field(ge=0)
    development: DevelopmentPlanData
    deployment: DeploymentPlanData
    trazabilidad_calculos: list[CalculationTraceData]
    criterio_calculo: str | None = None
    nota_deployment: str | None = None
    fases_prueba: list[SupplyPhaseData] = Field(
        default_factory=list,
    )


class SupplyCalculationData(BaseModel):
    """
    Estado y resultado del cálculo de insumos.
    """

    model_config = ConfigDict(extra="forbid")

    estado_calculo: CalculationStatus
    datos_faltantes: list[MissingField]
    mensaje_validacion: str | None = None
    base_calculo_estres: StressBase | None = None
    plan_insumos: SupplyPlanData | None = None


class PddAnalysisData(BaseModel):
    """
    Resultado validado del análisis completo del PDD/FDD.
    """

    model_config = ConfigDict(extra="forbid")

    estado_analisis: AnalysisStatus
    tecnologia: TechnologyData
    requerimientos: list[str]
    contexto_proceso: ProcessContextData
    calculo_insumos: SupplyCalculationData
    advertencias: list[str]

    @model_validator(mode="after")
    def validate_supply_calculation(
        self,
    ) -> "PddAnalysisData":
        """
        Verifica el cálculo de insumos sin modificarlo.
        """
        calculation = self.calculo_insumos
        context = self.contexto_proceso

        if calculation.estado_calculo == "error_validacion":
            if calculation.plan_insumos is not None:
                raise ValueError(
                    "plan_insumos debe ser null cuando "
                    "estado_calculo es error_validacion."
                )

            if calculation.base_calculo_estres is not None:
                raise ValueError(
                    "base_calculo_estres debe ser null cuando "
                    "estado_calculo es error_validacion."
                )

            if not calculation.datos_faltantes:
                raise ValueError(
                    "datos_faltantes no puede estar vacío cuando "
                    "estado_calculo es error_validacion."
                )

            if not (
                calculation.mensaje_validacion or ""
            ).strip():
                raise ValueError(
                    "mensaje_validacion es obligatorio cuando "
                    "estado_calculo es error_validacion."
                )

            return self

        if calculation.plan_insumos is None:
            raise ValueError(
                "plan_insumos es obligatorio cuando "
                "estado_calculo es ok."
            )

        if calculation.datos_faltantes:
            raise ValueError(
                "datos_faltantes debe estar vacío cuando "
                "estado_calculo es ok."
            )

        if calculation.mensaje_validacion is not None:
            raise ValueError(
                "mensaje_validacion debe ser null cuando "
                "estado_calculo es ok."
            )

        normal_quantity = (
            context.cantidad_periodo_normal.cantidad
        )

        if normal_quantity is None:
            raise ValueError(
                "cantidad_periodo_normal.cantidad es "
                "obligatoria para un cálculo exitoso."
            )

        maximum_quantity = (
            context.cantidad_periodo_maximo.cantidad
        )

        if maximum_quantity is not None:
            expected_stress_base = "periodo_maximo"
            stress_quantity = maximum_quantity
        else:
            expected_stress_base = "periodo_normal"
            stress_quantity = normal_quantity

        if (
            calculation.base_calculo_estres
            != expected_stress_base
        ):
            raise ValueError(
                "base_calculo_estres no coincide con la "
                "volumetría disponible."
            )

        expected_normal_quantity = ceil(
            normal_quantity
        )

        expected_phase_50 = ceil(
            normal_quantity * 0.50
        )

        expected_stress_120 = ceil(
            stress_quantity * 1.20
        )

        plan = calculation.plan_insumos

        if (
            plan.insumos_base_periodo_normal
            != expected_normal_quantity
        ):
            raise ValueError(
                "insumos_base_periodo_normal no coincide "
                "con la cantidad del periodo normal."
            )

        if (
            plan.insumos_estres_120
            != expected_stress_120
        ):
            raise ValueError(
                "insumos_estres_120 no corresponde al "
                "120% de la base de estrés."
            )

        if plan.development.fase_1.porcentaje != 50:
            raise ValueError(
                "development.fase_1 debe usar 50%."
            )

        if (
            plan.development.fase_1.cantidad
            != expected_phase_50
        ):
            raise ValueError(
                "development.fase_1.cantidad no "
                "corresponde al 50% del periodo normal."
            )

        if plan.development.fase_2.porcentaje != 50:
            raise ValueError(
                "development.fase_2 debe usar 50%."
            )

        if (
            plan.development.fase_2.cantidad
            != expected_phase_50
        ):
            raise ValueError(
                "development.fase_2.cantidad no "
                "corresponde al 50% del periodo normal."
            )

        if plan.development.fase_3.tipo != "estres":
            raise ValueError(
                "development.fase_3.tipo debe ser estres."
            )

        if plan.development.fase_3.porcentaje != 120:
            raise ValueError(
                "development.fase_3 debe usar 120%."
            )

        if (
            plan.development.fase_3.cantidad
            != expected_stress_120
        ):
            raise ValueError(
                "development.fase_3.cantidad no "
                "corresponde al 120% de la base de estrés."
            )

        uat = plan.deployment.uat_productivo

        if uat.tipo != "estres":
            raise ValueError(
                "deployment.uat_productivo.tipo debe "
                "ser estres."
            )

        if uat.porcentaje != 120:
            raise ValueError(
                "deployment.uat_productivo debe usar 120%."
            )

        if uat.cantidad != expected_stress_120:
            raise ValueError(
                "deployment.uat_productivo.cantidad no "
                "corresponde al 120% de la base de estrés."
            )

        return self
    
    @field_validator("requerimientos")
    @classmethod
    def clean_requirements(
        cls,
        values: list[str],
    ) -> list[str]:
        """
        Limpia requerimientos y elimina duplicados conservando el orden.
        """
        requirements: list[str] = []
        seen: set[str] = set()

        for value in values:
            clean_value = " ".join((value or "").split())

            if not clean_value:
                continue

            comparison_value = clean_value.casefold()

            if comparison_value in seen:
                continue

            seen.add(comparison_value)
            requirements.append(clean_value)

        return requirements

    @field_validator("advertencias")
    @classmethod
    def clean_warnings(
        cls,
        values: list[str],
    ) -> list[str]:
        """
        Limpia las advertencias devueltas por el modelo.
        """
        return [
            clean_value
            for value in values
            if (clean_value := " ".join((value or "").split()))
        ]

def _normalize_pdd_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Normaliza variaciones controladas del contrato PDD/FDD.

    El contexto de insumos pertenece a contexto_proceso. Si el modelo
    lo devuelve accidentalmente en la raíz, se mueve a su ubicación
    correcta antes de validar.
    """
    normalized_payload = dict(payload)

    root_phase_context = normalized_payload.pop(
        "contexto_insumos_por_fase",
        None,
    )

    process_context = normalized_payload.get(
        "contexto_proceso"
    )

    if not isinstance(
        process_context,
        dict,
    ):
        return normalized_payload

    normalized_context = dict(
        process_context
    )

    if (
        root_phase_context is not None
        and "contexto_insumos_por_fase"
        not in normalized_context
    ):
        normalized_context[
            "contexto_insumos_por_fase"
        ] = root_phase_context

    normalized_payload[
        "contexto_proceso"
    ] = normalized_context

    return normalized_payload

def validate_pdd_payload(
    payload: dict[str, Any],
) -> PddAnalysisData:
    """
    Valida el JSON producido durante el análisis PDD/FDD.

    Args:
        payload: Diccionario obtenido de la respuesta del modelo.

    Returns:
        Resultado PDD/FDD validado.

    Raises:
        ResponseParsingError: Cuando el payload no cumple el contrato.
    """
    normalized_payload = _normalize_pdd_payload(
        payload
    )

    try:
        return PddAnalysisData.model_validate(
            normalized_payload
        )
    except ValidationError as exc:
        for error in exc.errors(
            include_url=False
        ):
            location = ".".join(
                str(part)
                for part in error.get(
                    "loc",
                    (),
                )
            )

            logger.error(
                (
                    "Error de esquema PDD/FDD. "
                    "location=%s type=%s message=%s"
                ),
                location,
                error.get("type"),
                error.get("msg"),
            )

        raise ResponseParsingError(
            "El análisis PDD/FDD no cumple "
            "la estructura esperada."
        ) from exc