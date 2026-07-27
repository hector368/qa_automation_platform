from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from apps.test_cases.exceptions import (
    PromptConfigurationError,
)
from apps.test_cases.services.prompt_loader import (
    load_test_cases_prompt,
)


class PromptLoaderTests(SimpleTestCase):
    def test_loads_valid_prompt(self) -> None:
        with TemporaryDirectory() as directory:
            prompt_path = (
                Path(directory)
                / "prompt.txt"
            )

            prompt_path.write_text(
                "Genera casos de prueba.",
                encoding="utf-8",
            )

            result = load_test_cases_prompt(
                prompt_path,
            )

            self.assertEqual(
                result,
                "Genera casos de prueba.",
            )

    def test_rejects_missing_prompt(self) -> None:
        missing_path = Path(
            "ruta_inexistente_prompt.txt"
        )

        with self.assertRaises(
            PromptConfigurationError,
        ):
            load_test_cases_prompt(
                missing_path,
            )

    def test_rejects_empty_prompt(self) -> None:
        with TemporaryDirectory() as directory:
            prompt_path = (
                Path(directory)
                / "prompt.txt"
            )

            prompt_path.write_text(
                "   ",
                encoding="utf-8",
            )

            with self.assertRaises(
                PromptConfigurationError,
            ):
                load_test_cases_prompt(
                    prompt_path,
                )