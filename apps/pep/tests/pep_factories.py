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
    """Construye información PDD/FDD validada."""
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
                "calendario_frecuencia": "Diario",
                "cantidad_periodo_normal": {
                    "cantidad": 100,
                    "unidad_elemento": "solicitudes",
                },
                "cantidad_periodo_maximo": {
                    "cantidad": 150,
                    "unidad_elemento": "solicitudes",
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
                    "criterio_calculo": (
                        "Development utiliza 50%, 50% "
                        "y estrés al 120%."
                    ),
                    "nota_deployment": (
                        "Deployment/UAT utiliza insumos "
                        "productivos y entorno productivo."
                    ),
                },
            },
            "advertencias": [],
        }
    )