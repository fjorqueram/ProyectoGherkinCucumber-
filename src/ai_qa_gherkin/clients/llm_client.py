from __future__ import annotations
import json
import openai
from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential
from ai_qa_gherkin.config import settings
from ai_qa_gherkin.logger import get_logger

log = get_logger("llm_client")

class LLMClient:
    """Cliente para interactuar con LLM (OpenAI, Anthropic, etc.)."""

    def __init__(self) -> None:
        self.provider = settings.llm_provider.lower()
        self.timeout = settings.llm_timeout_seconds

        if self.provider == "openai":
            try:
                self.client = openai.OpenAI(api_key=settings.openai_api_key)
                self.model = settings.openai_model
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

        log.info(f"LLMClient initialized with provider={self.provider}, model={self.model}")

    @retry(
        stop=stop_after_attempt(settings.retry_max_attempts),
        wait=wait_exponential(
            multiplier=1,
            min=settings.retry_min_seconds,
            max=settings.retry_max_seconds,
        ),
    )
    def extract_business_rules(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Extrae reglas de negocio usando LLM.
        
        Args:
            context: Contexto merged con issue, confluence, git
            
        Returns:
            Dict con business_rules, preconditions, happy_paths, error_scenarios
        """
        log.info("Extracting business rules using LLM")

        prompt = self._build_analysis_prompt(context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert QA engineer specializing in BDD and Gherkin scenarios.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.7,
                timeout=self.timeout,
            )

            content = response.choices[0].message.content
            
            # ← VERSIÓN CONCISA
            if not content:
                log.warning("LLM returned empty content, using fallback")
                return self._get_fallback_result()
            
            result = self._parse_llm_response(content)
            log.info("Successfully extracted business rules from LLM")
            return result

        except Exception as e:
            log.error(f"LLM extraction failed: {str(e)}")
            raise
    
    def _get_fallback_result(self) -> dict[str, Any]:
        """Retorna estructura vacía cuando LLM falla."""
        return {
            "business_rules": [],
            "preconditions": [],
            "happy_paths": [],
            "error_scenarios": [],
            "assumptions": [],
            "risks": [],
        }

    def _build_analysis_prompt(self, context: dict[str, Any]) -> str:
        """Construye prompt para análisis."""
        issue = context.get("issue", {})
        confluence = context.get("confluence") or {}  # ← AGREGAR: or {}
        git = context.get("git") or {}  # ← AGREGAR: or {}

        prompt = f"""
        Analyze the following context and extract structured business rules, preconditions, happy paths, and error scenarios.

        ISSUE (Jira):
        - Key: {issue.get('issue_key', 'N/A')}
        - Summary: {issue.get('summary', 'N/A')}
        - Description: {issue.get('description', 'N/A')}
        - Acceptance Criteria: {json.dumps(issue.get('acceptance_criteria', []), indent=2)}

        DOCUMENTATION (Confluence):
        - Title: {confluence.get('title', 'N/A')}
        - Content: {confluence.get('content', 'N/A')[:500]}...

        CODE CHANGES (Git):
        - Commit: {git.get('commit_sha', 'N/A')}
        - Changed Files: {json.dumps(git.get('changed_files', []), indent=2)}
        - Summary: {git.get('diff_summary', 'N/A')}

        TASK:
        Extract and return a JSON object with:
        1. business_rules: list of business rules
        2. preconditions: list of preconditions
        3. happy_paths: list of happy paths (successful scenarios)
        4. error_scenarios: list of error/validation scenarios
        5. assumptions: list of assumptions
        6. risks: list of potential risks

        Each item should include:
        - description (string)
        - category (string: general, validation, permission, performance, etc.)
        - priority (high, medium, low)

        Return ONLY valid JSON, no markdown or extra text.
        """
        return prompt
    
    def _parse_llm_response(self, content: str) -> dict[str, Any]:
        """
        Parsea respuesta del LLM.
        
        Espera JSON con estructura:
        {{
            "business_rules": [...],
            "preconditions": [...],
            "happy_paths": [...],
            "error_scenarios": [...],
            "assumptions": [...],
            "risks": [...]
        }}
        """
        try:
            # Limpiar markdown si lo hay
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content)

            # Validar estructura mínima
            required_keys = [
                "business_rules",
                "preconditions",
                "happy_paths",
                "error_scenarios",
            ]
            for key in required_keys:
                if key not in result:
                    result[key] = []

            return result

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse LLM response: {str(e)}")
            log.debug(f"Raw content: {content[:200]}")
            # Retornar estructura vacía en caso de error
            return {
                "business_rules": [],
                "preconditions": [],
                "happy_paths": [],
                "error_scenarios": [],
                "assumptions": [],
                "risks": [],
            }