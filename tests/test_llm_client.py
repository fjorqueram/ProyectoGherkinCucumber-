import httpx
import pytest
from unittest.mock import MagicMock, Mock, patch

from ai_qa_gherkin.clients.llm_client import LLMClient


VALID_RESPONSE = """{
    "business_rules": ["Rule 1", "Rule 2"],
    "preconditions": ["Precond 1"],
    "happy_paths": [{
        "name": "Given contexto When accion Then resultado",
        "steps": [
            "Dado que existe un contexto valido",
            "Cuando ejecuto la accion principal",
            "Entonces obtengo el resultado esperado"
        ],
        "source": "jira",
        "source_id": "DYF-123",
        "source_name": "Test",
        "source_url": ""
    }],
    "error_scenarios": ["Error 1"]
}"""


class TestLLMClient:
    @pytest.fixture
    def mock_openai(self):
        """Mock del SDK OpenAI."""
        with patch("ai_qa_gherkin.clients.llm_client.openai") as mock:
            yield mock

    def _mock_chat_response(self, content: str) -> MagicMock:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = content
        return mock_response

    def test_llm_client_init_openai(self, mock_openai, monkeypatch):
        """Test inicializacion OpenAI."""
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        mock_openai.OpenAI.return_value = MagicMock()

        client = LLMClient()

        assert client.provider == "openai"
        mock_openai.OpenAI.assert_called_once()

    def test_extract_business_rules_openai(self, mock_openai, monkeypatch):
        """Test extraccion de reglas con OpenAI."""
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_chat_response(VALID_RESPONSE)
        mock_openai.OpenAI.return_value = mock_client

        client = LLMClient()
        result = client.extract_business_rules({
            "issue": {"issue_key": "DYF-123", "summary": "Test"},
            "confluence": {},
            "git": {},
        })

        assert len(result["business_rules"]) == 2
        assert len(result["preconditions"]) == 1
        assert len(result["happy_paths"]) == 1

    def test_extract_business_rules_rejects_invalid_json(self, mock_openai, monkeypatch):
        """Test: respuesta no JSON falla explicitamente."""
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_chat_response("not-json")
        mock_openai.OpenAI.return_value = mock_client

        client = LLMClient()

        with pytest.raises(ValueError, match="invalid JSON"):
            client.extract_business_rules({"issue": {"issue_key": "DYF-123"}})

    def test_extract_business_rules_rejects_empty_scenarios(self, mock_openai, monkeypatch):
        """Test: respuesta sin escenarios utiles falla explicitamente."""
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = self._mock_chat_response("""{
            "business_rules": [],
            "preconditions": [],
            "happy_paths": [],
            "error_scenarios": []
        }""")
        mock_openai.OpenAI.return_value = mock_client

        client = LLMClient()

        with pytest.raises(ValueError, match="happy_path"):
            client.extract_business_rules({"issue": {"issue_key": "DYF-123"}})

    def test_extract_business_rules_sanitizes_provider_errors(self, mock_openai, monkeypatch):
        """Test: errores del proveedor se reportan sin payload crudo."""
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        raw_error = RuntimeError("raw provider body should not leak")
        raw_error.status_code = 429
        raw_error.body = {"error": {"code": "insufficient_quota", "message": "billing details"}}

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = raw_error
        mock_openai.OpenAI.return_value = mock_client

        client = LLMClient()

        with pytest.raises(ValueError) as exc:
            client.extract_business_rules({"issue": {"issue_key": "DYF-123"}})

        message = str(exc.value)
        assert "openai request failed: 429 insufficient_quota" in message
        assert "billing details" not in message
        assert "raw provider body" not in message

    def test_openai_compatible_uses_base_url_and_model(self, mock_openai, monkeypatch):
        """Test: endpoint compatible usa base_url/API key configurados."""
        monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
        monkeypatch.setenv("LLM_BASE_URL", "https://models.example.test/v1")
        monkeypatch.setenv("LLM_API_KEY", "compatible-key")
        monkeypatch.setenv("LLM_MODEL", "custom/model")
        mock_openai.OpenAI.return_value = MagicMock()

        client = LLMClient()

        assert client.provider == "openai_compatible"
        assert client.model == "custom/model"
        mock_openai.OpenAI.assert_called_once_with(
            api_key="compatible-key",
            base_url="https://models.example.test/v1",
            timeout=60.0,
        )

    def test_ollama_has_safe_local_defaults(self, mock_openai, monkeypatch):
        """Test: Ollama no requiere key externa."""
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        monkeypatch.delenv("LLM_BASE_URL", raising=False)
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        mock_openai.OpenAI.return_value = MagicMock()

        client = LLMClient()

        assert client.provider == "ollama"
        assert client.model == "llama3.1"
        mock_openai.OpenAI.assert_called_once_with(
            api_key="ollama",
            base_url="http://localhost:11434/v1",
            timeout=60.0,
        )

    def test_github_models_calls_inference_api(self, monkeypatch):
        """Test: GitHub Models usa la API de inferencia con token GitHub."""
        monkeypatch.setenv("LLM_PROVIDER", "github_models")
        monkeypatch.setenv("GITHUB_MODELS_TOKEN", "ghp_test")
        monkeypatch.setenv("GITHUB_MODELS_MODEL", "openai/gpt-4.1")

        captured: dict[str, object] = {}

        class FakeHttpClient:
            def __init__(self, timeout: float):
                captured["timeout"] = timeout

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return None

            def post(self, url, headers, json):
                captured["url"] = url
                captured["headers"] = headers
                captured["json"] = json
                response = Mock()
                response.raise_for_status.return_value = None
                response.json.return_value = {
                    "choices": [{"message": {"content": VALID_RESPONSE}}]
                }
                return response

        with patch("ai_qa_gherkin.clients.llm_client.httpx.Client", FakeHttpClient):
            client = LLMClient()
            result = client.extract_business_rules({"issue": {"issue_key": "DYF-123"}})

        assert client.provider == "github_models"
        assert captured["url"] == "https://models.github.ai/inference/chat/completions"
        assert captured["headers"]["Authorization"] == "Bearer ghp_test"
        assert captured["json"]["model"] == "openai/gpt-4.1"
        assert len(result["happy_paths"]) == 1

    def test_github_models_sanitizes_http_errors(self, monkeypatch):
        """Test: errores HTTP de GitHub Models no filtran payload crudo."""
        monkeypatch.setenv("LLM_PROVIDER", "github_models")
        monkeypatch.setenv("GITHUB_MODELS_TOKEN", "ghp_test")

        class FakeHttpClient:
            def __init__(self, timeout: float):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return None

            def post(self, url, headers, json):
                request = httpx.Request("POST", url)
                response = httpx.Response(
                    403,
                    request=request,
                    json={"error": {"code": "models_access_denied", "message": "raw denied"}},
                )
                response.raise_for_status()

        with patch("ai_qa_gherkin.clients.llm_client.httpx.Client", FakeHttpClient):
            client = LLMClient()
            with pytest.raises(ValueError) as exc:
                client.extract_business_rules({"issue": {"issue_key": "DYF-123"}})

        message = str(exc.value)
        assert "github_models request failed: 403 models_access_denied" in message
        assert "raw denied" not in message

    def test_prompt_includes_github_evidence(self, mock_openai, monkeypatch):
        """Test: el prompt entrega evidencia GitHub a la IA."""
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        mock_openai.OpenAI.return_value = MagicMock()

        client = LLMClient()
        prompt = client._build_prompt({
            "issue": {"issue_key": "DYF-4275", "summary": "Otros archivos"},
            "confluence": {},
            "git": {
                "status": "found",
                "search_key": "DYF-4275",
                "owner": "org",
                "repo": "repo",
                "branches": [{"name": "feature/DYF-4275-otros-archivos"}],
                "prs": [{"id": "42", "title": "DYF-4275 permisos", "state": "open", "url": "https://github/pr/42"}],
                "commits": [{"sha": "abc123456", "message": "DYF-4275 agrega permisos"}],
                "files": [{"filename": "src/OtrosArchivos.tsx", "status": "modified", "changes": 10}],
                "diff_summary": "Archivos y permisos actualizados",
            },
        })

        assert "EVIDENCIA GITHUB RELACIONADA" in prompt
        assert "feature/DYF-4275-otros-archivos" in prompt
        assert "src/OtrosArchivos.tsx" in prompt
        assert 'source="git"' in prompt
