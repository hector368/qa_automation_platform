from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

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
    """Pruebas del cliente de Claude."""

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
        """Devuelve texto y consumo desde una respuesta válida."""
        client = Mock()

        response = SimpleNamespace(
            content=[
                SimpleNamespace(
                    text="respuesta válida"
                ),
            ],
            usage=SimpleNamespace(
                input_tokens=25,
                output_tokens=10,
            ),
        )

        stream = MagicMock()

        stream.get_final_message.return_value = (
            response
        )

        stream_manager = MagicMock()

        stream_manager.__enter__.return_value = (
            stream
        )

        stream_manager.__exit__.return_value = (
            None
        )

        client.messages.stream.return_value = (
            stream_manager
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

        client.messages.stream.assert_called_once_with(
            model="test-model",
            max_tokens=100,
            temperature=0,
            system="Reglas",
            messages=[
                {
                    "role": "user",
                    "content": "Documento",
                },
            ],
        )

        stream.get_final_message.assert_called_once_with()

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
        """Rechaza respuestas sin bloques de texto."""
        client = Mock()

        response = SimpleNamespace(
            content=[],
            usage=None,
        )

        stream = MagicMock()

        stream.get_final_message.return_value = (
            response
        )

        stream_manager = MagicMock()

        stream_manager.__enter__.return_value = (
            stream
        )

        stream_manager.__exit__.return_value = (
            None
        )

        client.messages.stream.return_value = (
            stream_manager
        )

        get_client_mock.return_value = client

        with self.assertRaises(
            ClaudeResponseError,
        ):
            call_claude(
                system_prompt="Reglas",
                user_text="Documento",
            )

    def test_rejects_empty_prompt(
        self,
    ) -> None:
        """Rechaza un system prompt vacío."""
        with self.assertRaises(
            ClaudeConfigurationError,
        ):
            call_claude(
                system_prompt="",
                user_text="Documento",
                model="test-model",
                max_tokens=100,
            )