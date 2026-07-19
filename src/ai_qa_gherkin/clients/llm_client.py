from __future__ import annotations

import json
import os
from typing import Any

import openai
from dotenv import load_dotenv

from ai_qa_gherkin.logger import get_logger

log = get_logger("llm_client")
load_dotenv()


class LLMClient:
    """Cliente para interactuar con OpenAI."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in .env")

        self.provider = "openai"
        self.client = openai.OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        log.info(f"LLMClient initialized with model: {self.model}")

    def extract_business_rules(self, merged_context: dict[str, Any]) -> dict[str, Any]:
        """Extrae reglas y escenarios usando Jira + Confluence como evidencia."""
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

        prompt = f"""
Analiza este requisito y genera activos para escenarios Gherkin en español.

REQUISTO JIRA
- Issue: {issue_key}
- Resumen: {summary}
- Descripcion: {description}
- Criterios de aceptacion:
{ac_text or "(ninguno)"}

DOCUMENTACION CONFLUENCE RELACIONADA
{confluence_text or "(sin paginas Confluence encontradas)"}

INSTRUCCIONES
1. Usa Jira como fuente base y Confluence como evidencia complementaria.
2. Genera escenarios adicionales cuando Confluence aporte reglas, flujos, validaciones o errores no cubiertos por Jira.
3. No dupliques escenarios equivalentes.
4. Usa pasos Gherkin observables en español: Dado/Cuando/Entonces/Y.
5. No inventes reglas sin evidencia. Si algo es supuesto, colocalo en preconditions o assumptions.
6. Para cada happy_path informa source, source_id, source_name y source_url si aplica.

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

        try:
            log.info(f"Calling OpenAI {self.model} for {issue_key}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=3000,
            )

            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Empty response from OpenAI")

            response_text = response.choices[0].message.content.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            result = json.loads(response_text)
            log.info(f"LLM analysis complete for {issue_key}")
            return result

        except json.JSONDecodeError as e:
            log.error(f"JSON parse error from OpenAI: {str(e)}")
            return self._empty_result()
        except Exception as e:
            log.error(f"Error calling OpenAI: {str(e)}")
            return self._empty_result()

    def _format_confluence_page_for_prompt(self, page: dict[str, Any]) -> str:
        page_id = page.get("page_id") or page.get("id") or ""
        title = page.get("title") or page.get("page_title") or ""
        url = page.get("url") or page.get("page_url") or ""
        content = str(page.get("content") or "")
        excerpt = content[:4000]
        return (
            f"- Page ID: {page_id}\n"
            f"  Title: {title}\n"
            f"  URL: {url}\n"
            f"  Content excerpt: {excerpt}"
        )

    def _empty_result(self) -> dict[str, Any]:
        return {
            "business_rules": [],
            "preconditions": [],
            "happy_paths": [],
            "error_scenarios": [],
        }
