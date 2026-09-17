"""Catálogo de estatus de la matriz MSP_QA."""

from __future__ import annotations

from typing import Any, Final


# Campo de la fila que corresponde a la columna ESTATUS.
STATUS_FIELD: Final[str] = "status"

STATUS_IN_PROGRESS: Final[str] = "Proceso"
STATUS_RELEASED: Final[str] = "Liberado"
STATUS_SUSPENDED: Final[str] = "Suspendido"
STATUS_CANCELLED: Final[str] = "Cancelado"

# Orden en que se ofrecen en la interfaz. Coincide con la lista
# desplegable que la matriz tiene configurada en la columna ESTATUS,
# así que cualquier otro texto quedaría marcado como inválido en la
# hoja de cálculo.
STATUS_OPTIONS: Final[tuple[str, ...]] = (
    STATUS_IN_PROGRESS,
    STATUS_RELEASED,
    STATUS_SUSPENDED,
    STATUS_CANCELLED,
)

# Equivalencia entre el campo State del work item de Azure DevOps y el
# estatus de la matriz. Los estados que no aparecen aquí (Proposed,
# Resolved, Not applicable) no definen un estatus: la celda se deja
# como esté y la decide una persona desde la interfaz.
AZURE_STATE_MAP: Final[dict[str, str]] = {
    "active": STATUS_IN_PROGRESS,
    "closed": STATUS_RELEASED,
    "cancelled": STATUS_CANCELLED,
    "canceled": STATUS_CANCELLED,
}

STATUS_BY_NORMALIZED: Final[dict[str, str]] = {
    option.casefold(): option
    for option in STATUS_OPTIONS
}


def normalize_status(raw_value: Any) -> str | None:
    """
    Devuelve el estatus canónico, o None cuando viene vacío.

    Un valor vacío significa que la columna ESTATUS no se toca, para
    respetar lo que ya esté capturado en la matriz.

    Args:
        raw_value: Valor recibido de la interfaz o de Azure DevOps.

    Returns:
        El estatus con la escritura exacta que usa la matriz.

    Raises:
        ValueError: Cuando el valor no es uno de los cuatro estatus.
    """
    clean_value = str(raw_value or "").strip()

    if not clean_value:
        return None

    canonical_value = STATUS_BY_NORMALIZED.get(clean_value.casefold())

    if canonical_value is None:
        raise ValueError(
            "must be one of: " + ", ".join(STATUS_OPTIONS),
        )

    return canonical_value


def map_azure_state(raw_state: Any) -> str | None:
    """
    Traduce el State de un work item al estatus de la matriz.

    Un estado sin equivalencia devuelve None, de modo que la columna
    ESTATUS quede intacta y la resuelva una persona.

    Args:
        raw_state: Valor del campo State en Azure DevOps.

    Returns:
        El estatus equivalente, o None si no hay equivalencia.
    """
    clean_state = str(raw_state or "").strip().casefold()

    return AZURE_STATE_MAP.get(clean_state)
