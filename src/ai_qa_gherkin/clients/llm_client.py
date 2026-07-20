from __future__ import annotations

import html
import json
import os
import re
from typing import Any

import httpx
import openai
from dotenv import load_dotenv

from ai_qa_gherkin.logger import get_logger

log = get_logger("llm_client")
load_dotenv()


class LLMClient:
    """Cliente LLM configurable para OpenAI, Azure, GitHub Models y endpoints compatibles."""

    OPENAI_COMPATIBLE_PROVIDERS = {"openai", "azure_openai", "openai_compatible", "ollama", "lm_studio"}

    def __init__(self) -> None:
        self.provider = self._env("LLM_PROVIDER", "openai").lower()
        self.model = self._resolve_model()
        self.temperature = float(self._env("LLM_TEMPERATURE", "0.2"))
        self.max_tokens = int(self._env("LLM_MAX_TOKENS", "5000"))
        self.timeout = float(self._env("LLM_TIMEOUT_SECONDS", "60"))
        self.client: Any | None = None
        self.github_models_base_url = self._env("GITHUB_MODELS_BASE_URL", "https://models.github.ai")
        self.github_models_org = self._env("GITHUB_MODELS_ORG", "")
        self.github_models_token = ""

        if self.provider in self.OPENAI_COMPATIBLE_PROVIDERS:
            self.client = self._build_openai_compatible_client()
        elif self.provider == "github_models":
            self.github_models_token = self._require_env("GITHUB_MODELS_TOKEN", fallback="GITHUB_TOKEN")
        else:
            supported = ", ".join(sorted(self.OPENAI_COMPATIBLE_PROVIDERS | {"github_models"}))
            raise ValueError(f"Unsupported LLM_PROVIDER '{self.provider}'. Supported providers: {supported}")

        log.info(f"LLMClient initialized with provider={self.provider}, model={self.model}")

    def extract_business_rules(self, merged_context: dict[str, Any]) -> dict[str, Any]:
        """Extrae reglas y escenarios usando Jira + Confluence como evidencia."""
        issue = merged_context.get("issue", {}) or {}
        issue_key = issue.get("issue_key") or issue.get("key") or merged_context.get("issue_key", "UNKNOWN")
        prompt = self._build_prompt(merged_context)

        log.info(f"Calling {self.provider} model {self.model} for {issue_key}")
        response_text = self._create_chat_completion(prompt).strip()
        if not response_text:
            raise ValueError(f"Empty response from {self.provider}")

        response_text = self._strip_markdown_json(response_text)

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"{self.provider} returned invalid JSON") from e

        self._validate_result(result)
        log.info(f"LLM analysis complete for {issue_key}")
        return result

    def _build_prompt(self, merged_context: dict[str, Any]) -> str:
        issue = merged_context.get("issue", {}) or {}
        issue_key = issue.get("issue_key") or issue.get("key") or merged_context.get("issue_key", "UNKNOWN")
        summary = issue.get("summary", "")
        description = issue.get("description", "")
        acceptance_criteria = issue.get("acceptance_criteria", [])
        ac_text = (
            acceptance_criteria
            if isinstance(acceptance_criteria, str)
            else "\n".join(f"- {item}" for item in acceptance_criteria)
        )

        confluence_pages = (merged_context.get("confluence", {}) or {}).get("pages", [])
        if not confluence_pages and merged_context.get("confluence"):
            confluence_pages = [merged_context.get("confluence", {})]
        confluence_text = "\n\n".join(
            self._format_confluence_page_for_prompt(page) for page in confluence_pages[:5]
        )
        git_text = self._format_git_for_prompt(merged_context.get("git", {}) or {})

        return f"""
Analiza este requisito y genera activos para escenarios Gherkin en espanol.

REQUISITO JIRA
- Issue: {issue_key}
- Resumen: {summary}
- Descripcion: {description}
- Criterios de aceptacion:
{ac_text or "(ninguno)"}

DOCUMENTACION CONFLUENCE RELACIONADA
{confluence_text or "(sin paginas Confluence encontradas)"}

EVIDENCIA GITHUB RELACIONADA
{git_text or "(sin evidencia GitHub encontrada)"}

INSTRUCCIONES
1. Usa Jira como fuente base, Confluence como evidencia funcional y GitHub como evidencia tecnica complementaria.
2. Genera escenarios adicionales cuando Confluence o GitHub aporten reglas, flujos, validaciones, permisos, errores, archivos modificados o comportamientos no cubiertos por Jira.
3. No dupliques escenarios equivalentes.
4. Usa pasos Gherkin observables en espanol: Dado/Cuando/Entonces/Y.
5. No inventes reglas sin evidencia. Si algo es supuesto, colocalo en preconditions o assumptions.
6. Para cada happy_path informa source, source_id, source_name y source_url si aplica.
7. Si hay documentacion Confluence/FTU de la issue, genera entre 4 y 8 happy_paths con source="confluence" cubriendo flujos principales, estados vacios, permisos, acciones, validaciones, errores y bordes que esten descritos.
8. Si hay evidencia GitHub, genera escenarios source="git" solo para comportamientos verificables derivados de PRs, commits, archivos modificados o diff_summary.
9. Evita escenarios genericos tipo "Onboarding" si el FTU contiene reglas concretas; usa nombres de negocio especificos.

Responde SOLO JSON valido, sin markdown:
{{
  "business_rules": [
    {{"description": "regla", "category": "general"}}
  ],
  "preconditions": [
    "precondicion o supuesto"
  ],
  "happy_paths": [
    {{
      "name": "Given contexto When accion Then resultado",
      "steps": ["Dado que ...", "Cuando ...", "Entonces ..."],
      "source": "jira",
      "source_id": "{issue_key}",
      "source_name": "{summary}",
      "source_url": ""
    }}
  ],
  "error_scenarios": [
    {{
      "error_type": "validation",
      "description": "condicion de error",
      "expected_outcome": "resultado esperado observable"
    }}
  ]
}}
"""

    def _create_chat_completion(self, prompt: str) -> str:
        if self.provider == "github_models":
            return self._create_github_models_completion(prompt)
        return self._create_openai_compatible_completion(prompt)

    def _create_openai_compatible_completion(self, prompt: str) -> str:
        if not self.client:
            raise ValueError(f"{self.provider} client is not initialized")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
        except Exception as e:
            raise ValueError(
                f"{self.provider} request failed: {self._sanitize_provider_error(e)}"
            ) from e

        if not response.choices or not response.choices[0].message.content:
            raise ValueError(f"Empty response from {self.provider}")
        return response.choices[0].message.content

    def _create_github_models_completion(self, prompt: str) -> str:
        url = self._github_models_inference_url()
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.github_models_token}",
            "X-GitHub-Api-Version": self._env("GITHUB_MODELS_API_VERSION", "2026-03-10"),
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            raise ValueError(
                f"github_models request failed: {self._sanitize_provider_error(e)}"
            ) from e

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError("github_models returned an invalid chat completion shape") from e
        return str(content or "")

    def _build_openai_compatible_client(self) -> Any:
        if self.provider == "openai":
            return openai.OpenAI(
                api_key=self._require_env("OPENAI_API_KEY"),
                timeout=self.timeout,
            )

        if self.provider == "azure_openai":
            return openai.AzureOpenAI(
                api_key=self._require_env("AZURE_OPENAI_API_KEY"),
                azure_endpoint=self._require_env("AZURE_OPENAI_ENDPOINT"),
                api_version=self._env("AZURE_OPENAI_API_VERSION", "2024-10-21"),
                timeout=self.timeout,
            )

        base_url = self._resolve_base_url()
        api_key = self._resolve_api_key()
        return openai.OpenAI(api_key=api_key, base_url=base_url, timeout=self.timeout)

    def _resolve_model(self) -> str:
        if self.provider == "github_models":
            return self._env("GITHUB_MODELS_MODEL", self._env("LLM_MODEL", "openai/gpt-4.1"))
        if self.provider == "azure_openai":
            return self._env("AZURE_OPENAI_DEPLOYMENT", self._env("LLM_MODEL", "gpt-4o-mini"))
        if self.provider == "ollama":
            return self._env("OLLAMA_MODEL", self._env("LLM_MODEL", "llama3.1"))
        if self.provider == "lm_studio":
            return self._env("LM_STUDIO_MODEL", self._env("LLM_MODEL", "local-model"))
        return self._env("LLM_MODEL", self._env("OPENAI_MODEL", "gpt-4o-mini"))

    def _resolve_base_url(self) -> str:
        if self.provider == "ollama":
            return self._env("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        if self.provider == "lm_studio":
            return self._env("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
        return self._require_env("LLM_BASE_URL")

    def _resolve_api_key(self) -> str:
        if self.provider == "ollama":
            return self._env("OLLAMA_API_KEY", "ollama")
        if self.provider == "lm_studio":
            return self._env("LM_STUDIO_API_KEY", "lm-studio")
        return self._require_env("LLM_API_KEY")

    def _github_models_inference_url(self) -> str:
        base_url = self.github_models_base_url.rstrip("/")
        if self.github_models_org:
            return f"{base_url}/orgs/{self.github_models_org}/inference/chat/completions"
        return f"{base_url}/inference/chat/completions"

    def _validate_result(self, result: dict[str, Any]) -> None:
        if not isinstance(result, dict):
            raise ValueError(f"{self.provider} response must be a JSON object")

        happy_paths = result.get("happy_paths", [])
        if not isinstance(happy_paths, list) or not happy_paths:
            raise ValueError(f"{self.provider} response must include at least one happy_path")

        valid_paths = 0
        for path in happy_paths:
            if not isinstance(path, dict):
                continue
            name = str(path.get("name") or "").strip()
            steps = path.get("steps", [])
            if isinstance(steps, str):
                steps = [line.strip() for line in steps.splitlines() if line.strip()]
            if not name or not isinstance(steps, list):
                continue
            normalized_steps = [str(step).strip() for step in steps if str(step).strip()]
            has_when = any(step.lower().startswith(("cuando", "when")) for step in normalized_steps)
            has_then = any(step.lower().startswith(("entonces", "then")) for step in normalized_steps)
            if len(normalized_steps) >= 3 and has_when and has_then:
                valid_paths += 1

        if valid_paths == 0:
            raise ValueError(f"{self.provider} response does not include valid Gherkin scenarios")

    def _sanitize_provider_error(self, error: Exception) -> str:
        status_code = getattr(error, "status_code", None)
        code = self._extract_error_code(getattr(error, "body", None))

        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            try:
                code = self._extract_error_code(error.response.json())
            except ValueError:
                code = None

        if status_code and code:
            return f"{status_code} {code}"
        if status_code:
            return f"{status_code}"
        return error.__class__.__name__

    def _extract_error_code(self, error_body: Any) -> str | None:
        if not isinstance(error_body, dict):
            return None
        nested_error = error_body.get("error", {})
        if isinstance(nested_error, dict):
            code = nested_error.get("code") or nested_error.get("type")
            return str(code) if code else None
        code = error_body.get("code") or error_body.get("type")
        return str(code) if code else None

    def _format_confluence_page_for_prompt(self, page: dict[str, Any]) -> str:
        page_id = page.get("page_id") or page.get("id") or ""
        title = page.get("title") or page.get("page_title") or ""
        url = page.get("url") or page.get("page_url") or ""
        content = self._clean_confluence_content(str(page.get("content") or ""))
        excerpt = content[:8000]
        return (
            f"- Page ID: {page_id}\n"
            f"  Title: {title}\n"
            f"  URL: {url}\n"
            f"  Clean content:\n{excerpt}"
        )

    def _format_git_for_prompt(self, git: dict[str, Any]) -> str:
        if not git or git.get("status") == "not_found":
            return ""

        branches = ", ".join(
            branch.get("name", "") for branch in git.get("branches", [])[:5]
        )
        prs = "\n".join(
            f"- PR #{pr.get('id')}: {pr.get('title')} ({pr.get('state')}) {pr.get('url')}"
            for pr in git.get("prs", [])[:5]
        )
        commits = "\n".join(
            f"- {commit.get('sha', '')[:8]}: {str(commit.get('message', '')).splitlines()[0]}"
            for commit in git.get("commits", [])[:8]
        )
        files = "\n".join(
            f"- {item.get('filename')} ({item.get('status', 'modified')}, {item.get('changes', 0)} cambios)"
            for item in git.get("files", [])[:12]
        )

        return "\n".join([
            f"- Status: {git.get('status')}",
            f"- Search key: {git.get('search_key')}",
            f"- Repo: {git.get('owner')}/{git.get('repo')}",
            f"- Branches: {branches or '(ninguna)'}",
            f"- PRs:\n{prs or '(ninguno)'}",
            f"- Commits:\n{commits or '(ninguno)'}",
            f"- Changed files:\n{files or '(ninguno)'}",
            f"- Diff summary: {git.get('diff_summary') or '(sin resumen)'}",
        ])

    def _clean_confluence_content(self, content: str) -> str:
        content = html.unescape(content)
        content = re.sub(r"</(p|li|tr|h[1-6]|td|th|div)>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"<[^>]+>", " ", content)
        lines = [" ".join(line.split()) for line in content.splitlines()]
        return "\n".join(line for line in lines if line)

    def _strip_markdown_json(self, response_text: str) -> str:
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        return response_text.strip()

    def _require_env(self, key: str, fallback: str | None = None) -> str:
        value = self._env(key, "")
        if not value and fallback:
            value = self._env(fallback, "")
        if not value:
            fallback_msg = f" or {fallback}" if fallback else ""
            raise ValueError(f"{key}{fallback_msg} not configured in .env")
        return value

    @staticmethod
    def _env(key: str, default: str) -> str:
        value = os.getenv(key)
        return value if value not in (None, "") else default
