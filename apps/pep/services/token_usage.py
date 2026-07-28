"""
Modelos y cálculos para métricas de tokens y costo estimado.

Los costos utilizan Decimal para evitar errores de precisión monetaria.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Final


TOKENS_PER_MILLION: Final[Decimal] = Decimal("1000000")
COST_PRECISION: Final[Decimal] = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Tokens consumidos por una o varias llamadas al modelo."""

    input_tokens: int = 0
    output_tokens: int = 0

    def __post_init__(self) -> None:
        if self.input_tokens < 0:
            raise ValueError(
                "input_tokens no puede ser negativo."
            )

        if self.output_tokens < 0:
            raise ValueError(
                "output_tokens no puede ser negativo."
            )

    @property
    def total_tokens(self) -> int:
        """Obtiene la suma de tokens de entrada y salida."""
        return self.input_tokens + self.output_tokens

    def __add__(
        self,
        other: "TokenUsage",
    ) -> "TokenUsage":
        """Combina el uso de dos llamadas."""
        if not isinstance(other, TokenUsage):
            return NotImplemented

        return TokenUsage(
            input_tokens=(
                self.input_tokens
                + other.input_tokens
            ),
            output_tokens=(
                self.output_tokens
                + other.output_tokens
            ),
        )

    def to_dict(self) -> dict[str, int]:
        """Convierte las métricas a un diccionario serializable."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_anthropic(
        cls,
        usage: Any,
    ) -> "TokenUsage":
        """Construye métricas desde la respuesta de Anthropic."""
        if usage is None:
            return cls()

        return cls(
            input_tokens=int(
                getattr(
                    usage,
                    "input_tokens",
                    0,
                )
                or 0
            ),
            output_tokens=int(
                getattr(
                    usage,
                    "output_tokens",
                    0,
                )
                or 0
            ),
        )


@dataclass(frozen=True, slots=True)
class TokenCost:
    """Costo estimado de una ejecución."""

    input_usd: Decimal
    output_usd: Decimal

    @property
    def total_usd(self) -> Decimal:
        """Obtiene el costo total."""
        return self.input_usd + self.output_usd

    def to_dict(self) -> dict[str, float | str]:
        """Convierte el costo a un payload para la interfaz."""
        return {
            "currency": "USD",
            "input_usd": float(self.input_usd),
            "output_usd": float(self.output_usd),
            "total_usd": float(self.total_usd),
            "total_usd_formatted": (
                f"${self.total_usd:.6f}"
            ),
        }


def calculate_token_cost(
    *,
    usage: TokenUsage,
    input_rate_per_million: Decimal,
    output_rate_per_million: Decimal,
) -> TokenCost:
    """
    Calcula el costo estimado a partir de tokens y tarifas.

    Args:
        usage: Tokens consumidos.
        input_rate_per_million: Tarifa de entrada por millón.
        output_rate_per_million: Tarifa de salida por millón.

    Returns:
        Costo estimado.

    Raises:
        ValueError: Cuando alguna tarifa es negativa.
    """
    if input_rate_per_million < 0:
        raise ValueError(
            "La tarifa de entrada no puede ser negativa."
        )

    if output_rate_per_million < 0:
        raise ValueError(
            "La tarifa de salida no puede ser negativa."
        )

    input_cost = (
        Decimal(usage.input_tokens)
        / TOKENS_PER_MILLION
        * input_rate_per_million
    ).quantize(
        COST_PRECISION,
        rounding=ROUND_HALF_UP,
    )

    output_cost = (
        Decimal(usage.output_tokens)
        / TOKENS_PER_MILLION
        * output_rate_per_million
    ).quantize(
        COST_PRECISION,
        rounding=ROUND_HALF_UP,
    )

    return TokenCost(
        input_usd=input_cost,
        output_usd=output_cost,
    )