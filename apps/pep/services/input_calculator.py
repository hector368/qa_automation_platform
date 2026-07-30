"""
Cálculo determinístico del plan de insumos para pruebas.

Las cantidades extraídas del PDD/FDD son utilizadas como entrada para
aplicar las reglas de negocio definidas para Development y Deployment.
"""

from __future__ import annotations

from math import ceil

from apps.pep.schemas.pdd_schema import (
    CalculationTraceData,
    DeploymentPlanData,
    DevelopmentPlanData,
    PddAnalysisData,
    PercentageQuantityData,
    PhaseCode,
    PhaseSupplyContextData,
    ProcessContextData,
    SupplyCalculationData,
    SupplyPhaseData,
    SupplyPlanData,
    TypedPercentageQuantityData,
)


VALIDATION_MESSAGE = (
    "[ERROR DE VALIDACIÓN: INSUMOS INSUFICIENTES] "
    "No es posible calcular la proyección de insumos porque faltan "
    "datos mandatorios en los requisitos. Acción requerida: proporcionar "
    "los datos ausentes para poder proceder con el cálculo del plan de "
    "capacidad y pruebas de estrés."
)


def recalculate_insumo_plan(
    pdd_data: PddAnalysisData,
) -> PddAnalysisData:
    """
    Recalcula el plan de insumos usando reglas determinísticas.

    Args:
        pdd_data: Resultado validado del análisis PDD/FDD.

    Returns:
        Resultado PDD/FDD con cálculo de insumos verificado.
    """
    calculation = build_insumo_calculation(
        pdd_data.contexto_proceso,
    )

    return pdd_data.model_copy(
        update={
            "calculo_insumos": calculation,
        },
    )


def build_insumo_calculation(
    context: ProcessContextData,
) -> SupplyCalculationData:
    """
    Construye el cálculo de insumos a partir del contexto del proceso.

    Args:
        context: Contexto operativo extraído del PDD/FDD.

    Returns:
        Cálculo validado del plan de insumos.
    """
    missing_fields = _get_missing_fields(context)

    if missing_fields:
        return SupplyCalculationData(
            estado_calculo="error_validacion",
            datos_faltantes=missing_fields,
            mensaje_validacion=VALIDATION_MESSAGE,
            base_calculo_estres=None,
            plan_insumos=None,
        )

    normal_quantity = context.cantidad_periodo_normal.cantidad

    if normal_quantity is None:
        raise ValueError(
            "La cantidad del periodo normal no puede ser None "
            "después de validar campos obligatorios."
        )

    maximum_quantity = context.cantidad_periodo_maximo.cantidad

    if maximum_quantity is not None:
        stress_base_name = "periodo_maximo"
        stress_base_quantity = maximum_quantity
    else:
        stress_base_name = "periodo_normal"
        stress_base_quantity = normal_quantity

    phase_50 = _calculate_percentage(
        normal_quantity,
        50,
    )

    stress_120 = _calculate_percentage(
        stress_base_quantity,
        120,
    )
    
    unit = _resolve_unit(context)

    supply_phases = _build_supply_phase_rows(
        context=context,
        unit=unit,
        phase_50=phase_50,
        stress_120=stress_120,
    )

    traces = [
        _build_trace(
            calculation_name="development_fase_1",
            base_value=normal_quantity,
            percentage=50,
        ),
        _build_trace(
            calculation_name="development_fase_2",
            base_value=normal_quantity,
            percentage=50,
        ),
        _build_trace(
            calculation_name="development_fase_3",
            base_value=stress_base_quantity,
            percentage=120,
        ),
        _build_trace(
            calculation_name="deployment_uat_productivo",
            base_value=stress_base_quantity,
            percentage=120,
        ),
    ]

    plan = SupplyPlanData(
        nombre_proceso=context.descripcion_breve_proceso,
        frecuencia=context.calendario_frecuencia,
        unidad_elemento=unit,
        insumos_base_periodo_normal=ceil(
            normal_quantity
        ),
        insumos_estres_120=stress_120,
        development=DevelopmentPlanData(
            fase_1=PercentageQuantityData(
                porcentaje=50,
                cantidad=phase_50,
            ),
            fase_2=PercentageQuantityData(
                porcentaje=50,
                cantidad=phase_50,
            ),
            fase_3=TypedPercentageQuantityData(
                tipo="estres",
                porcentaje=120,
                cantidad=stress_120,
            ),
        ),
        deployment=DeploymentPlanData(
            uat_productivo=TypedPercentageQuantityData(
                tipo="estres",
                porcentaje=120,
                cantidad=stress_120,
            ),
        ),
        trazabilidad_calculos=traces,
        criterio_calculo=_build_calculation_criterion(
            stress_base_name,
        ),
        nota_deployment=_build_deployment_note(),
        fases_prueba=supply_phases,
    )

    return SupplyCalculationData(
        estado_calculo="ok",
        datos_faltantes=[],
        mensaje_validacion=None,
        base_calculo_estres=stress_base_name,
        plan_insumos=plan,
    )

def _build_supply_phase_rows(
    *,
    context: ProcessContextData,
    unit: str | None,
    phase_50: int,
    stress_120: int,
) -> list[SupplyPhaseData]:
    """
    Construye las filas del plan de insumos para el PEP.
    """
    phase_contexts = (
        context.contexto_insumos_por_fase
    )

    return [
        _build_supply_phase(
            phase="planificacion",
            phase_name="Planificación",
            test_level="Pruebas Unitarias",
            quantity=phase_50,
            unit=unit,
            percentage=50,
            phase_context=(
                phase_contexts.planificacion
            ),
        ),
        _build_supply_phase(
            phase="preparacion",
            phase_name="Preparación",
            test_level="Pruebas de Integración",
            quantity=phase_50,
            unit=unit,
            percentage=50,
            phase_context=(
                phase_contexts.preparacion
            ),
        ),
        _build_supply_phase(
            phase="ejecucion",
            phase_name="Ejecución",
            test_level=(
                "Pruebas de Sistema / End-to-End"
            ),
            quantity=stress_120,
            unit=unit,
            percentage=120,
            phase_context=(
                phase_contexts.ejecucion
            ),
        ),
        _build_supply_phase(
            phase="cierre_uat",
            phase_name="Cierre",
            test_level=(
                "Pruebas de Aceptación / UAT"
            ),
            quantity=stress_120,
            unit=unit,
            percentage=120,
            phase_context=(
                phase_contexts.cierre_uat
            ),
        ),
    ]


def _build_supply_phase(
    *,
    phase: PhaseCode,
    phase_name: str,
    test_level: str,
    quantity: int,
    unit: str | None,
    percentage: int,
    phase_context: PhaseSupplyContextData,
) -> SupplyPhaseData:
    """
    Combina el cálculo de Python con el contexto documental.
    """
    return SupplyPhaseData(
        fase=phase,
        fase_proceso=phase_name,
        nivel_prueba=test_level,
        cantidad=quantity,
        unidad_elemento=unit,
        porcentaje_aplicado=percentage,
        frecuencia=phase_context.frecuencia,
        tipo_dato=phase_context.tipo_dato,
        caracteristicas=(
            phase_context.caracteristicas
        ),
    )

def _get_missing_fields(
    context: ProcessContextData,
) -> list[str]:
    """
    Identifica los campos obligatorios faltantes.
    """
    missing_fields: list[str] = []

    if not context.descripcion_breve_proceso:
        missing_fields.append("descripcion_breve_proceso")

    if not context.calendario_frecuencia:
        missing_fields.append("calendario_frecuencia")

    if context.cantidad_periodo_normal.cantidad is None:
        missing_fields.append(
            "cantidad_periodo_normal.cantidad"
        )

    return missing_fields


def _calculate_percentage(
    base_value: float,
    percentage: int,
) -> int:
    """
    Calcula un porcentaje y redondea hacia arriba.
    """
    result = base_value * (percentage / 100)
    return ceil(result)


def _build_trace(
    calculation_name: str,
    base_value: float,
    percentage: int,
) -> CalculationTraceData:
    """
    Construye la trazabilidad matemática de un cálculo.
    """
    raw_result = base_value * (percentage / 100)

    return CalculationTraceData(
        calculo=calculation_name,
        valor_base=base_value,
        porcentaje_aplicado=percentage,
        resultado_sin_redondear=raw_result,
        resultado_final=ceil(raw_result),
    )


def _resolve_unit(
    context: ProcessContextData,
) -> str | None:
    """
    Obtiene la unidad principal del elemento procesado.
    """
    return (
        context.cantidad_periodo_normal.unidad_elemento
        or context.cantidad_periodo_maximo.unidad_elemento
    )


def _build_deployment_note() -> str:
    """
    Construye la nota funcional para Deployment/UAT.
    """
    return (
        "Para Deployment/UAT se considera el 120% con insumos "
        "productivos y entorno productivo. La diferencia aplica cuando "
        "cambia el tipo de insumos o el entorno utilizado para la ejecución."
    )


def _build_calculation_criterion(
    stress_base_name: str,
) -> str:
    """
    Describe el criterio utilizado para la base de estrés.
    """
    if stress_base_name == "periodo_maximo":
        return (
            "El periodo normal se utilizó para las pruebas al 50%. "
            "El periodo máximo se utilizó exclusivamente como base "
            "para los cálculos de estrés al 120%."
        )

    return (
        "No se detectó un periodo máximo válido. El periodo normal "
        "se utilizó como base para las pruebas al 50% y para los "
        "cálculos de estrés al 120%."
    )