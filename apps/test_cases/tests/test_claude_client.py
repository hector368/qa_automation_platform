from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.test import override_settings

from apps.test_cases.exceptions import (
    ClaudeConfigurationError,
    ClaudeResponseError,
)
from apps.test_cases.services.claude_client import (
    call_claude,
)


class ClaudeClientTests(SimpleTestCase):
    @override_settings(
        ANTHROPIC_API_KEY="test-key",
        CLAUDE_MODEL="test-model",
        MAX_TOKENS=100,
    )
    @patch(
        "apps.test_cases.services."
        "claude_client.get_client"
    )
    def test_returns_text_and_usage(
        self,
        get_client_mock: Mock,
    ) -> None:
        client = Mock()

        client.messages.create.return_value = (
            SimpleNamespace(
                content=[
                    SimpleNamespace(
                        text="respuesta válida"
                    )
                ],
                usage=SimpleNamespace(
                    input_tokens=25,
                    output_tokens=10,
                ),
            )
        )

        get_client_mock.return_value = client

        result = call_claude(
            system_prompt="Reglas",
            user_text="Documento",
        )

        self.assertEqual(
            result.text,
            "respuesta válida",
        )

        self.assertEqual(
            result.usage.input_tokens,
            25,
        )

        self.assertEqual(
            result.usage.output_tokens,
            10,
        )

    @override_settings(
        ANTHROPIC_API_KEY="test-key",
        CLAUDE_MODEL="test-model",
        MAX_TOKENS=100,
    )
    @patch(
        "apps.test_cases.services."
        "claude_client.get_client"
    )
    def test_rejects_empty_response(
        self,
        get_client_mock: Mock,
    ) -> None:
        client = Mock()

        client.messages.create.return_value = (
            SimpleNamespace(
                content=[],
                usage=None,
            )
        )

        get_client_mock.return_value = client

        with self.assertRaises(
            ClaudeResponseError,
        ):
            call_claude(
                system_prompt="Reglas",
                user_text="Documento",
            )

    def test_rejects_empty_prompt(self) -> None:
        with self.assertRaises(
            ClaudeConfigurationError,
        ):
            call_claude(
                system_prompt="",
                user_text="Documento",
                model="test-model",
                max_tokens=100,
            )