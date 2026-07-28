from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from apps.pep.exceptions import PromptConfigurationError
from apps.pep.services.prompt_loader import (
    load_pap_prompt,
)

from apps.pep.services.prompt_loader import (
    load_pap_prompt,
    load_pdd_prompt,
)

class PapPromptLoaderTests(SimpleTestCase):
    def test_loads_valid_prompt(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "pap_prompt.txt"

            path.write_text(
                "Analiza el documento PAP.",
                encoding="utf-8",
            )

            result = load_pap_prompt(
                path
            )

            self.assertEqual(
                result,
                "Analiza el documento PAP.",
            )

    def test_removes_utf8_bom(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "pap_prompt.txt"

            path.write_text(
                "\ufeffPrompt PAP",
                encoding="utf-8",
            )

            result = load_pap_prompt(
                path
            )

            self.assertEqual(
                result,
                "Prompt PAP",
            )

    def test_rejects_missing_prompt(self) -> None:
        with self.assertRaises(
            PromptConfigurationError,
        ):
            load_pap_prompt(
                Path("prompt_pap_inexistente.txt")
            )

    def test_rejects_empty_prompt(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "pap_prompt.txt"

            path.write_text(
                "   ",
                encoding="utf-8",
            )

            with self.assertRaises(
                PromptConfigurationError,
            ):
                load_pap_prompt(
                    path
                )
    def test_loads_valid_pdd_prompt(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "pdd_prompt.txt"
    
            path.write_text(
                "Analiza el documento PDD/FDD.",
                encoding="utf-8",
            )
    
            result = load_pdd_prompt(
                path
            )
    
            self.assertEqual(
                result,
                "Analiza el documento PDD/FDD.",
            )
    
    
    def test_rejects_empty_pdd_prompt(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "pdd_prompt.txt"
    
            path.write_text(
                "",
                encoding="utf-8",
            )
    
            with self.assertRaises(
                PromptConfigurationError,
            ):
                load_pdd_prompt(
                    path
                )