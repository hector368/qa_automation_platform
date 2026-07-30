from django.test import SimpleTestCase

from apps.pep.exceptions import ResponseParsingError
from apps.pep.schemas.pdd_schema import (
    validate_pdd_payload,
)


class PddSchemaTests(SimpleTestCase):
    def test_validates_pdd_payload(self) -> None:
        result = validate_pdd_payload(
            self._build_payload()
        )

        self.assertEqual(
            result.estado_analisis,
            "completado",
        )

        self.assertEqual(
            result.tecnologia.valor,
            "Power Automate Desktop",
        )

        self.assertEqual(
            result.requerimientos,
            [
                "Consultar solicitudes",
                "Validar información",
            ],
        )

    def test_removes_duplicate_requirements(self) -> None:
        payload = self._build_payload()

        payload["requerimientos"] = [
            "Consultar solicitudes",
            " consultar solicitudes ",
            "Validar información",
        ]

        result = validate_pdd_payload(
            payload
        )

        self.assertEqual(
            result.requerimientos,
            [
                "Consultar solicitudes",
                "Validar información",
            ],
        )

    def test_rejects_old_deployment_structure(
        self,
    ) -> None:
        payload = self._build_payload()

        payload["calculo_insumos"]["plan_insumos"][
            "deployment"
        ] = {
            "cambio_entorno_o_insumos": {
                "tipo": "estres",
                "porcentaje": 120,
                "cantidad": 120,
            },
            "mismo_entorno_e_insumos": {
                "tipo": "verificacion",
                "porcentaje": 50,
                "cantidad": 50,
            },
        }

        with self.assertRaises(
            ResponseParsingError,
        ):
            validate_pdd_payload(
                payload
            )

    def test_rejects_extra_fields(self) -> None:
        payload = self._build_payload()
        payload["campo_inventado"] = True

        with self.assertRaises(
            ResponseParsingError,
        ):
            validate_pdd_payload(
                payload
            )

    @staticmethod
    def _build_payload() -> dict[str, object]:
        return {
            "estado_analisis": "completado",
            "tecnologia": {
                "valor": "Power Automate Desktop",
                "tipo_deteccion": "explicita",
                "justificacion": None,
            },
            "requerimientos": [
                "Consultar solicitudes",
                "Validar información",
            ],
            "contexto_proceso": {
                "descripcion_breve_proceso": (
                    "Procesar solicitudes."
                ),
                "calendario_frecuencia": "Diaria",
                "cantidad_periodo_normal": {
                    "cantidad": 100,
                    "unidad_elemento": "solicitudes",
                },
                "cantidad_periodo_maximo": {
                    "cantidad": 150,
                    "unidad_elemento": "solicitudes",
                },
                "contexto_insumos_por_fase": {
                    "planificacion": {
                        "frecuencia": "Diaria",
                        "tipo_dato": "Excel",
                        "caracteristicas": [
                            "Registros de solicitudes",
                        ],
                    },
                    "preparacion": {
                        "frecuencia": "Diaria",
                        "tipo_dato": "Excel",
                        "caracteristicas": [
                            "Registros validados",
                        ],
                    },
                    "ejecucion": {
                        "frecuencia": "Diaria",
                        "tipo_dato": "Excel / ServiceNow",
                        "caracteristicas": [
                            "Datos transaccionales",
                        ],
                    },
                    "cierre_uat": {
                        "frecuencia": "Diaria",
                        "tipo_dato": "Documento",
                        "caracteristicas": [
                            "Evidencias de ejecución",
                        ],
                    },
                },
            },
            "calculo_insumos": {
                "estado_calculo": "ok",
                "datos_faltantes": [],
                "mensaje_validacion": None,
                "base_calculo_estres": "periodo_maximo",
                "plan_insumos": {
                    "nombre_proceso": (
                        "Procesar solicitudes."
                    ),
                    "frecuencia": "Diario",
                    "unidad_elemento": "solicitudes",
                    "insumos_base_periodo_normal": 100,
                    "insumos_estres_120": 180,
                    "development": {
                        "fase_1": {
                            "porcentaje": 50,
                            "cantidad": 50,
                        },
                        "fase_2": {
                            "porcentaje": 50,
                            "cantidad": 50,
                        },
                        "fase_3": {
                            "tipo": "estres",
                            "porcentaje": 120,
                            "cantidad": 180,
                        },
                    },
                    "deployment": {
                        "uat_productivo": {
                            "tipo": "estres",
                            "porcentaje": 120,
                            "cantidad": 180,
                        },
                    },
                    "trazabilidad_calculos": [],
                    "criterio_calculo": None,
                    "nota_deployment": None,
                },
            },
            "advertencias": [],
        }