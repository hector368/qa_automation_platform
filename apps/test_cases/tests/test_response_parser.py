import csv
import io

from django.test import SimpleTestCase

from apps.test_cases.services.ado_csv import (
    ADO_COLUMNS,
    ADO_CSV_HEADER,
)
from apps.test_cases.services.response_parser import (
    extract_csv_only,
)


class ResponseParserTests(SimpleTestCase):
    def test_extracts_csv_from_markdown(self) -> None:
        csv_row = self._build_row()

        raw_response = (
            "```csv\n"
            f"{ADO_CSV_HEADER}\n"
            f"{csv_row}\n"
            "```"
        )

        result = extract_csv_only(
            raw_response,
        )

        self.assertTrue(
            result.startswith(
                ADO_CSV_HEADER
            )
        )

        self.assertIn(
            "Test Case",
            result,
        )

    def test_extracts_csv_after_extra_text(self) -> None:
        csv_row = self._build_row()

        raw_response = (
            "Aquí está el resultado:\n"
            f"{ADO_CSV_HEADER}\n"
            f"{csv_row}"
        )

        result = extract_csv_only(
            raw_response,
        )

        self.assertTrue(
            result.startswith(
                ADO_CSV_HEADER
            )
        )

    def test_returns_empty_when_response_is_empty(
        self,
    ) -> None:
        self.assertEqual(
            extract_csv_only(""),
            "",
        )

    @staticmethod
    def _build_row() -> str:
        row = [""] * len(ADO_COLUMNS)
        row[1] = "Test Case"
        row[2] = "TEMP.001.001"

        output = io.StringIO()
        writer = csv.writer(
            output,
            lineterminator="",
        )
        writer.writerow(row)

        return output.getvalue()