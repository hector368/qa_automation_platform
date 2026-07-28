from django.test import SimpleTestCase

from apps.pep.schemas.pdd_schema import (
    ProcessContextData,
    ProcessQuantityData,
)
from apps.pep.services.input_calculator import (
    build_insumo_calculation,
)


class InputCalculatorTests(SimpleTestCase):
    def test_uses_maximum_period_for_stress(self) -> None:
        context = ProcessContextData(
            descripcion_breve_proceso=(
                "Procesar solicitudes de clientes."
            ),
            calendario_frecuencia="Diario",
            cantidad_periodo_normal=ProcessQuantityData(
                cantidad=100,
                unidad_elemento="solicitudes",
            ),
            cantidad_periodo_maximo=ProcessQuantityData(
                cantidad=150,
                unidad_elemento="solicitudes",
            ),
        )

        result = build_insumo_calculation(
            context
        )

        self.assertEqual(
            result.estado_calculo,
            "ok",
        )

        self.assertEqual(
            result.base_calculo_estres,
            "periodo_maximo",
        )

        plan = result.plan_insumos

        self.assertIsNotNone(
            plan
        )

        assert plan is not None

        self.assertEqual(
            plan.development.fase_1.cantidad,
            50,
        )

        self.assertEqual(
            plan.development.fase_2.cantidad,
            50,
        )

        self.assertEqual(
            plan.development.fase_3.cantidad,
            180,
        )

        self.assertEqual(
            plan.deployment.uat_productivo.cantidad,
            180,
        )

        self.assertEqual(
            plan.deployment.uat_productivo.porcentaje,
            120,
        )

    def test_uses_normal_period_when_maximum_is_missing(
        self,
    ) -> None:
        context = ProcessContextData(
            descripcion_breve_proceso=(
                "Procesar facturas."
            ),
            calendario_frecuencia="Semanal",
            cantidad_periodo_normal=ProcessQuantityData(
                cantidad=33,
                unidad_elemento="facturas",
            ),
            cantidad_periodo_maximo=ProcessQuantityData(
                cantidad=None,
                unidad_elemento=None,
            ),
        )

        result = build_insumo_calculation(
            context
        )

        self.assertEqual(
            result.base_calculo_estres,
            "periodo_normal",
        )

        plan = result.plan_insumos

        assert plan is not None

        self.assertEqual(
            plan.development.fase_1.cantidad,
            17,
        )

        self.assertEqual(
            plan.development.fase_3.cantidad,
            40,
        )

        self.assertEqual(
            plan.deployment.uat_productivo.cantidad,
            40,
        )

    def test_returns_validation_error_when_data_is_missing(
        self,
    ) -> None:
        context = ProcessContextData(
            descripcion_breve_proceso=None,
            calendario_frecuencia=None,
            cantidad_periodo_normal=ProcessQuantityData(
                cantidad=None,
                unidad_elemento=None,
            ),
            cantidad_periodo_maximo=ProcessQuantityData(
                cantidad=None,
                unidad_elemento=None,
            ),
        )

        result = build_insumo_calculation(
            context
        )

        self.assertEqual(
            result.estado_calculo,
            "error_validacion",
        )

        self.assertIsNone(
            result.plan_insumos
        )

        self.assertEqual(
            result.datos_faltantes,
            [
                "descripcion_breve_proceso",
                "calendario_frecuencia",
                "cantidad_periodo_normal.cantidad",
            ],
        )

    def test_rounds_decimal_results_up(self) -> None:
        context = ProcessContextData(
            descripcion_breve_proceso=(
                "Procesar registros."
            ),
            calendario_frecuencia="Mensual",
            cantidad_periodo_normal=ProcessQuantityData(
                cantidad=10.5,
                unidad_elemento="registros",
            ),
            cantidad_periodo_maximo=ProcessQuantityData(
                cantidad=None,
                unidad_elemento=None,
            ),
        )

        result = build_insumo_calculation(
            context
        )

        plan = result.plan_insumos

        assert plan is not None

        self.assertEqual(
            plan.insumos_base_periodo_normal,
            11,
        )

        self.assertEqual(
            plan.development.fase_1.cantidad,
            6,
        )

        self.assertEqual(
            plan.insumos_estres_120,
            13,
        )