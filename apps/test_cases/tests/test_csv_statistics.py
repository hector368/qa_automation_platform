from django.test import SimpleTestCase

from apps.test_cases.services.ado_csv import (
    ADO_NCOLS,
    dump_ado_rows,
)
from apps.test_cases.services.csv_statistics import (
    compute_csv_stats,
)


class CsvStatisticsTests(SimpleTestCase):
    def test_returns_zero_for_empty_csv(self) -> None:
        result = compute_csv_stats("")

        self.assertEqual(
            result["requirements_total"],
            0,
        )

        self.assertEqual(
            result["test_cases_total"],
            0,
        )

    def test_counts_requirements_and_test_cases(
        self,
    ) -> None:
        first = [""] * ADO_NCOLS
        first[1] = "Test Case"
        first[2] = "CFC.003.001.001"
        first[8] = "Resultado esperado"

        second = [""] * ADO_NCOLS
        second[1] = "Test Case"
        second[2] = "CFC.003.001.002"
        second[8] = "Resultado esperado"

        third = [""] * ADO_NCOLS
        third[1] = "Test Case"
        third[2] = "CFC.003.002.001"
        third[8] = "Resultado esperado"

        csv_text = dump_ado_rows(
            [
                first,
                second,
                third,
            ]
        )

        result = compute_csv_stats(
            csv_text,
        )

        self.assertEqual(
            result["requirements_total"],
            2,
        )

        self.assertEqual(
            result["test_cases_total"],
            3,
        )