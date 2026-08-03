"""Datos controlados para pruebas del generador PEP."""

from __future__ import annotations

from apps.pep.schemas.pap_schema import (
    PapExtractionData,
    validate_pap_payload,
)
from apps.pep.schemas.pdd_schema import (
    PddAnalysisData,
    validate_pdd_payload,
)
def build_pap_data(
    *,
    project_id: str | None = "CFC.003",
) -> PapExtractionData:
    """Construye información PAP validada."""
    return validate_pap_payload(
        {
            "nombre_proyecto": "Proyecto de prueba",
            "id_proyecto": project_id,
            "nombre_cliente": "Cliente de prueba",
            "roles": {
                "desarrollador": [
                    "Persona Desarrollo",
                ],
                "tester": [
                    "Persona Testing",
                ],
                "scrum_master": [
                    "Persona Scrum",
                ],
                "delivery_manager": None,
                "business_analyst": None,
                "arquitecto": None,
                "code_reviewer": None,
            },
            "requisitos_software": {
                "texto_introductorio": None,
                "items": [
                    "Microsoft Excel",
                    "Power Automate Desktop",
                ],
            },
            "requisitos_hardware": {
                "texto_introductorio": None,
                "items": [
                    "Equipo con 8 GB de RAM",
                ],
            },
            "advertencias": [],
        }
    )


def build_pdd_data() -> PddAnalysisData:
    """Construye un resultado PDD/FDD final simulado."""
    return validate_pdd_payload(
        {
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
                        "tipo_dato": (
                            "Excel / ServiceNow"
                        ),
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
                "base_calculo_estres": (
                    "periodo_maximo"
                ),
                "plan_insumos": {
                    "nombre_proceso": (
                        "Procesar solicitudes."
                    ),
                    "frecuencia": "Diaria",
                    "unidad_elemento": (
                        "solicitudes"
                    ),
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
                    "trazabilidad_calculos": [
                        {
                            "calculo": (
                                "development_fase_1"
                            ),
                            "valor_base": 100,
                            "porcentaje_aplicado": 50,
                            "resultado_sin_redondear": (
                                50.0
                            ),
                            "resultado_final": 50,
                        },
                        {
                            "calculo": (
                                "development_fase_2"
                            ),
                            "valor_base": 100,
                            "porcentaje_aplicado": 50,
                            "resultado_sin_redondear": (
                                50.0
                            ),
                            "resultado_final": 50,
                        },
                        {
                            "calculo": (
                                "development_fase_3"
                            ),
                            "valor_base": 150,
                            "porcentaje_aplicado": 120,
                            "resultado_sin_redondear": (
                                180.0
                            ),
                            "resultado_final": 180,
                        },
                        {
                            "calculo": (
                                "deployment_uat_productivo"
                            ),
                            "valor_base": 150,
                            "porcentaje_aplicado": 120,
                            "resultado_sin_redondear": (
                                180.0
                            ),
                            "resultado_final": 180,
                        },
                    ],
                    "criterio_calculo": (
                        "El periodo normal se utilizó "
                        "para las fases al 50% y el "
                        "periodo máximo para las fases "
                        "al 120%."
                    ),
                    "nota_deployment": (
                        "Para Deployment/UAT se "
                        "considera el 120% con insumos "
                        "productivos y entorno "
                        "productivo."
                    ),
                    "fases_prueba": [
                        {
                            "fase": "planificacion",
                            "fase_proceso": (
                                "Planificación"
                            ),
                            "nivel_prueba": (
                                "Pruebas Unitarias"
                            ),
                            "cantidad": 50,
                            "unidad_elemento": (
                                "solicitudes"
                            ),
                            "porcentaje_aplicado": 50,
                            "frecuencia": "Diaria",
                            "tipo_dato": "Excel",
                            "caracteristicas": [
                                "Registros de solicitudes",
                            ],
                        },
                        {
                            "fase": "preparacion",
                            "fase_proceso": (
                                "Preparación"
                            ),
                            "nivel_prueba": (
                                "Pruebas de Integración"
                            ),
                            "cantidad": 50,
                            "unidad_elemento": (
                                "solicitudes"
                            ),
                            "porcentaje_aplicado": 50,
                            "frecuencia": "Diaria",
                            "tipo_dato": "Excel",
                            "caracteristicas": [
                                "Registros validados",
                            ],
                        },
                        {
                            "fase": "ejecucion",
                            "fase_proceso": "Ejecución",
                            "nivel_prueba": (
                                "Pruebas de Sistema / "
                                "End-to-End"
                            ),
                            "cantidad": 180,
                            "unidad_elemento": (
                                "solicitudes"
                            ),
                            "porcentaje_aplicado": 120,
                            "frecuencia": "Diaria",
                            "tipo_dato": (
                                "Excel / ServiceNow"
                            ),
                            "caracteristicas": [
                                "Datos transaccionales",
                            ],
                        },
                        {
                            "fase": "cierre_uat",
                            "fase_proceso": "Cierre",
                            "nivel_prueba": (
                                "Pruebas de Aceptación / "
                                "UAT"
                            ),
                            "cantidad": 180,
                            "unidad_elemento": (
                                "solicitudes"
                            ),
                            "porcentaje_aplicado": 120,
                            "frecuencia": "Diaria",
                            "tipo_dato": "Documento",
                            "caracteristicas": [
                                "Evidencias de ejecución",
                            ],
                        },
                    ],
                },
            },
            "advertencias": [],
        }
    )