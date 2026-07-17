import pytest
from unittest.mock import Mock, patch, MagicMock

from ai_qa_gherkin.clients.llm_client import LLMClient


class TestLLMClient:
    @pytest.fixture
    def mock_openai(self):
        """Mock del cliente OpenAI."""
        with patch("ai_qa_gherkin.clients.llm_client.openai") as mock:
            yield mock

    def test_llm_client_init(self, mock_openai):
        """Test inicialización del cliente."""
        mock_openai.OpenAI.return_value = MagicMock()
        client = LLMClient()
        assert client.provider == "openai"

    def test_extract_business_rules(self, mock_openai):
        """Test extracción de reglas."""
        # Mock respuesta
        mock_response = MagicMock()
        mock_response.choices[0].message.content = """{
            "business_rules": ["Rule 1", "Rule 2"],
            "preconditions": ["Precond 1"],
            "happy_paths": ["Path 1"],
            "error_scenarios": ["Error 1"]
        }"""

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        client = LLMClient()
        context = {
            "issue": {"issue_key": "DYF-123", "summary": "Test"},
            "confluence": {},
            "git": {},
        }

        result = client.extract_business_rules(context)

        assert len(result["business_rules"]) == 2
        assert len(result["preconditions"]) == 1