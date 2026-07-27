from django.test import SimpleTestCase

from apps.test_cases.services.ado_csv import (
    ADO_CSV_HEADER,
    ADO_NCOLS,
    dump_ado_rows,
    enforce_structure_and_titles,
    ensure_csv_header,
    parse_ado_rows,
)


class AdoCsvTests(SimpleTestCase):
    def test_adds_header(self) -> None:
        row = ",".join(
            [""] * ADO_NCOLS
        )

        result = ensure_csv_header(row)

        self.assertTrue(
            result.startswith(
                ADO_CSV_HEADER
            )
        )

    def test_does_not_duplicate_header(self) -> None:
        result = ensure_csv_header(
            ADO_CSV_HEADER
        )

        self.assertEqual(
            result,
            ADO_CSV_HEADER,
        )

    def test_lenient_parser_pads_short_row(
        self,
    ) -> None:
        rows = parse_ado_rows(
            "a,b,c",
            strict=False,
        )

        self.assertEqual(
            len(rows[0]),
            ADO_NCOLS,
        )

    def test_strict_parser_rejects_short_row(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError,
        ):
            parse_ado_rows(
                "a,b,c",
                strict=True,
            )

    def test_enforces_metadata_and_steps(
        self,
    ) -> None:
        source_row = [""] * ADO_NCOLS
        source_row[1] = "Test Case"
        source_row[4] = "Ingresar al sistema"
        source_row[5] = "El sistema muestra el inicio"
        source_row[6] = "Functional"
        source_row[7] = "1"
        source_row[8] = "Acceso exitoso"
        source_row[9] = "Validar acceso"
        source_row[10] = "Positivo"
        source_row[11] = "Contar con credenciales"

        rows, total = enforce_structure_and_titles(
            [source_row],
            project_id="CFC.003",
            requirement_number=2,
            tc_start=1,
            assigned_to="Usuario QA",
        )

        self.assertEqual(
            total,
            1,
        )

        self.assertEqual(
            rows[0][2],
            "CFC.003.002.001",
        )

        self.assertEqual(
            rows[0][12],
            "Design",
        )

        self.assertEqual(
            rows[0][13],
            "CFC.003",
        )

        self.assertEqual(
            rows[0][14],
            "Usuario QA",
        )

        self.assertEqual(
            rows[1][3],
            "1",
        )

        dumped = dump_ado_rows(rows)

        self.assertIn(
            "CFC.003.002.001",
            dumped,
        )