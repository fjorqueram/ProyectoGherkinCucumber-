
from __future__ import annotations
import json
import os
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI
from ai_qa_gherkin.logger import get_logger

log = get_logger("llm_client")
load_dotenv()


class LLMClient:
    """Cliente para interactuar con OpenAI."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured in .env")
        
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        log.info(f"LLMClient initialized with model: {self.model}")

    def extract_business_rules(self, merged_context: dict[str, Any]) -> dict[str, Any]:
        """Extrae reglas de negocio usando OpenAI."""
        issue = merged_context.get("issue", {})
        issue_key = issue.get("issue_key", "UNKNOWN")
        summary = issue.get("summary", "")
        description = issue.get("description", "")
        ac = issue.get("acceptance_criteria", [])

        prompt = f"""Analiza este requisito y extrae información para generar escenarios Gherkin.

    REQUISITO:
    - Issue: {issue_key}
    - Resumen: {summary}
    - Descripción: {description}
    - Criterios de Aceptación:
    {chr(10).join(f'  • {c}' for c in ac) if ac else '  (ninguno)'}

    TAREAS:
    1. Identifica 3-5 reglas de negocio principales
    2. Lista 2-3 supuestos implícitos
    3. Identifica 1-3 riesgos potenciales
    4. Define 1-2 caminos felices (happy paths) con sus pasos
    5. Sugiere 1-2 escenarios de error

    Responde SOLO en JSON válido (sin markdown):
    {{
        "business_rules": [
            {{"description": "regla1", "category": "general"}},
            {{"description": "regla2", "category": "validation"}}
        ],
        "preconditions": [
            "supuesto1",
            "supuesto2"
        ],
        "happy_paths": [
            {{
                "name": "Camino feliz principal",
                "steps": ["paso1", "paso2", "paso3"]
            }}
        ],
        "error_scenarios": [
            {{
                "error_type": "validation",
                "description": "Input inválido",
                "expected_outcome": "Error mostrado al usuario"
            }}
        ]
    }}
    """

        try:
            log.info(f"Calling OpenAI {self.model} for {issue_key}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
            )

            # Validar que content no sea None
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Empty response from OpenAI")

            response_text = response.choices[0].message.content.strip()
            
            # Limpiar markdown si viene
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
            log.warning(f"Returning empty result for {issue_key}")
            return {
                "business_rules": [],
                "preconditions": [],
                "happy_paths": [],
                "error_scenarios": [],
            }
        except Exception as e:
            log.error(f"Error calling OpenAI: {str(e)}")
            log.warning(f"Returning empty result for {issue_key}")
            return {
                "business_rules": [],
                "preconditions": [],
                "happy_paths": [],
                "error_scenarios": [],
            }