from decimal import Decimal

from django.test import SimpleTestCase

from apps.pep.services.token_usage import (
    TokenUsage,
    calculate_token_cost,
)


class TokenUsageTests(SimpleTestCase):
    def test_combines_usage(self) -> None:
        first = TokenUsage(
            input_tokens=100,
            output_tokens=20,
        )

        second = TokenUsage(
            input_tokens=50,
            output_tokens=10,
        )

        combined = first + second

        self.assertEqual(
            combined.input_tokens,
            150,
        )

        self.assertEqual(
            combined.output_tokens,
            30,
        )

        self.assertEqual(
            combined.total_tokens,
            180,
        )

    def test_calculates_cost(self) -> None:
        usage = TokenUsage(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )

        cost = calculate_token_cost(
            usage=usage,
            input_rate_per_million=Decimal("2"),
            output_rate_per_million=Decimal("4"),
        )

        self.assertEqual(
            cost.input_usd,
            Decimal("2.000000"),
        )

        self.assertEqual(
            cost.output_usd,
            Decimal("4.000000"),
        )

        self.assertEqual(
            cost.total_usd,
            Decimal("6.000000"),
        )
