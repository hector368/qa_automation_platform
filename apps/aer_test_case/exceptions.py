"""Excepciones específicas del AER Test Case Generator."""


class AerTestCaseError(Exception):
    """Excepción base del AER Test Case Generator."""


class RequirementSegmentationError(AerTestCaseError):
    """Indica un error al segmentar requerimientos."""


class AerJsonGenerationError(AerTestCaseError):
    """Indica que Claude no devolvió el JSON esperado."""


class AerTraceabilityError(AerTestCaseError):
    """Indica una inconsistencia de trazabilidad en la respuesta."""