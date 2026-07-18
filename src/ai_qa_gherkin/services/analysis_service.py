from __future__ import annotations
import re
from typing import Any
from dotenv import load_dotenv
from typing import Any, cast
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models.domain import (
    JiraIssue,
    BusinessRule,
    Precondition,
    HappyPath,
    ErrorScenario,
    TraceabilityLink,
    AnalysisResult,
)
from ai_qa_gherkin.clients.llm_client import LLMClient
from ai_qa_gherkin.utils.text_cleaner import TextCleaner

log = get_logger("analysis_service")
load_dotenv()

class AnalysisService:
    """Servicio de análisis con soporte para LLM real o mock."""

    def __init__(self, use_llm: bool = False) -> None:
        self.use_llm = use_llm
        try:
            self.llm_client = LLMClient() if use_llm else None
            if use_llm:
                log.info("LLMClient initialized successfully")
        except ValueError as e:
            log.warning(f"LLMClient initialization failed: {str(e)}, using mock mode")
            self.use_llm = False
            self.llm_client = None
        
        self.business_rules: list[BusinessRule] = []
        self.preconditions: list[Precondition] = []
        self.happy_paths: list[HappyPath] = []
        self.error_scenarios: list[ErrorScenario] = []

    def analyze(self, issue: JiraIssue | dict[str, Any]) -> dict[str, Any]:
        """Analiza un issue y extrae reglas de negocio, precondiciones y escenarios."""
        log.info("Starting analysis of issue")

        # Convertir Pydantic model a dict real
        try:
            if isinstance(issue, dict):
                issue_data: dict[str, Any] = issue
            elif hasattr(issue, 'model_dump'):
                issue_data = cast(dict[str, Any], dict(issue.model_dump()))
            elif hasattr(issue, 'dict'):
                issue_data = cast(dict[str, Any], dict(issue.dict()))
            else:
                issue_data = cast(dict[str, Any], issue.__dict__)
        except Exception as e:
            log.error(f"Conversion error: {e}")
            issue_data = {}
        
        log.info(f"Issue data converted: {len(issue_data)} keys")
        
        self._extract_from_issue(issue_data)

        # Helper para convertir modelos
        def to_dict(obj: Any) -> Any:
            try:
                if isinstance(obj, dict):
                    return obj
                if hasattr(obj, 'model_dump'):
                    return dict(obj.model_dump())
                if hasattr(obj, 'dict'):
                    return dict(obj.dict())
                return obj.__dict__ if hasattr(obj, '__dict__') else obj
            except Exception as e:
                log.warning(f"to_dict error: {e}")
                return str(obj)

        # Compilar resultado
        result: dict[str, Any] = {
            "issue_key": issue_data.get("key", "UNKNOWN"),
            "scope_summary": issue_data.get("summary", ""),
            "business_rules": [
                {
                    "rule": br.rule,
                    "category": br.category,
                    "traceability": to_dict(br.traceability),
                }
                for br in self.business_rules
            ],
            "preconditions": [
                {
                    "precondition": pc.precondition,
                    "traceability": to_dict(pc.traceability),
                }
                for pc in self.preconditions
            ],
            "raw": {
                "happy_paths": [
                    {
                        "name": hp.name,
                        "steps": hp.steps,
                        "traceability": to_dict(hp.traceability),
                    }
                    for hp in self.happy_paths
                ],
                "error_scenarios": [
                    {
                        "error_type": es.error_type,
                        "description": es.description,
                        "expected_outcome": es.expected_outcome,
                        "traceability": to_dict(es.traceability),
                    }
                    for es in self.error_scenarios
                ],
            },
        }

        log.info(f"Analysis complete: {len(self.happy_paths)} scenarios, {len(self.business_rules)} rules")

        return result

    def _analyze_with_mock(self, context: dict[str, Any]) -> None:
        """Realiza análisis mock."""
        if context.get("issue"):
            self._extract_from_issue(context["issue"])
        if context.get("confluence"):
            self._extract_from_confluence(context["confluence"])
        if context.get("git"):
            self._extract_from_git(context["git"])

    def _extract_from_issue(self, issue: dict[str, Any]) -> None:
        """Extrae reglas de negocio, precondiciones y escenarios desde Jira issue."""
        
        # Si es la estructura merged, extrae el issue real
        if "issue" in issue and isinstance(issue.get("issue"), dict):
            actual_issue = issue.get("issue", {})
        else:
            actual_issue = issue
        
        # Obtener datos del issue
        issue_key = actual_issue.get("key") or actual_issue.get("issue_key", "")
        summary = actual_issue.get("summary", "")
        description = actual_issue.get("description", "")
        
        # Buscar acceptance criteria - CONVERTIR A STRING SI ES LISTA
        acceptance_criteria = (
            actual_issue.get("acceptance_criteria") or 
            issue.get("combined_acceptance_criteria", "")
        )
        
        # Si es lista, únela
        if isinstance(acceptance_criteria, list):
            acceptance_criteria = " ".join(str(x) for x in acceptance_criteria)
        else:
            acceptance_criteria = str(acceptance_criteria)

        log.info(f"Extracted: key={issue_key}")
        log.info(f"Summary: {summary[:80] if summary else 'EMPTY'}")
        log.info(f"AC length: {len(acceptance_criteria)}")
        
        # Traceabilidad base
        trace = TraceabilityLink(
            source_type="jira",
            source_id=issue_key,
            source_name=summary,
        )

        # Regla de negocio principal
        if summary:
            main_rule = BusinessRule(
                rule=f"Feature '{summary}' must be implemented",
                traceability=trace,
                category="general",
            )
            self.business_rules.append(main_rule)

        # **Dividir por "Escenario X:" y procesar cada uno**
        if acceptance_criteria:
            log.info(f"Processing acceptance criteria ({len(acceptance_criteria)} chars)")
            
            # Dividir en bloques de escenarios
            scenario_blocks = re.split(r'Escenario\s+\d+:', acceptance_criteria)
            
            log.info(f"Found {len(scenario_blocks)} scenario blocks")
            
            for block_idx, block in enumerate(scenario_blocks[1:], 1):  # Skip header
                block = block.strip()
                if not block:
                    continue
                
                # Obtener nombre (primer párrafo antes de "Dado")
                match = re.search(r'^([^.]+)', block)
                scenario_name = match.group(1)[:80] if match else f"Escenario {block_idx}"
                
                log.debug(f"Processing scenario {block_idx}: {scenario_name}")
                
                # Extraer steps
                steps = self._extract_gherkin_steps(block)
                
                if steps and len(steps) >= 2:
                    log.info(f"✓ Adding scenario: {scenario_name} ({len(steps)} steps)")
                    
                    happy_path = HappyPath(
                        name=scenario_name,
                        steps=steps,
                        traceability=trace,
                    )
                    self.happy_paths.append(happy_path)
                else:
                    log.debug(f"✗ Scenario {block_idx} rejected: only {len(steps)} steps")

            log.info(f"Total happy_paths extracted: {len(self.happy_paths)}")

        # Fallback
        if not self.happy_paths and summary:
            log.warning("No happy paths found, using fallback")
            happy_path = HappyPath(
                name=f"Happy path for {summary}",
                steps=["User initiates", "System processes", "Result returned"],
                traceability=trace,
            )
            self.happy_paths.append(happy_path)

    def _extract_gherkin_steps(self, scenario_text: str) -> list[str]:
        """Extrae pasos Gherkin de un escenario."""
        steps = []
        
        # Primero, reemplaza espacios dobles con newline
        scenario_text = scenario_text.replace("  ", "\n")
        
        lines = scenario_text.split("\n")
        
        for line in lines:
            line = line.strip()
            
            # Buscar palabras clave Gherkin al inicio
            if line and any(line.lower().startswith(kw) for kw in 
                        ["dado", "cuando", "entonces", "y ", "dado que", "cuando ", "entonces "]):
                # Limpiar espacios extra
                line = " ".join(line.split())
                steps.append(line)
                log.debug(f"  + Step: {line[:80]}")
        
        log.debug(f"Extracted {len(steps)} steps from scenario")
        return steps

    def _extract_from_confluence(self, confluence: dict[str, Any]) -> None:
        """Extrae reglas de negocio desde Confluence."""
        log.debug(f"Extracting from confluence {confluence.get('page_id')}")

        page_id = confluence.get("page_id", "")
        title = confluence.get("title", "")
        content = confluence.get("content", "")

        trace = TraceabilityLink(
            source_type="confluence",
            source_id=page_id,
            source_name=title,
        )

        # Buscar patrones comunes
        if "validation" in content.lower():
            rule = BusinessRule(
                rule="Input validation must be performed",
                traceability=trace,
                category="validation",
            )
            self.business_rules.append(rule)

        if "permission" in content.lower() or "access" in content.lower():
            rule = BusinessRule(
                rule="Access control and permissions must be enforced",
                traceability=trace,
                category="permission",
            )
            self.business_rules.append(rule)
        
        if "error" in content.lower() or "exception" in content.lower():
            error_scenario = ErrorScenario(
                error_type="validation",
                description="Invalid input provided",
                expected_outcome="Error message displayed to user",
                traceability=trace,
            )
            self.error_scenarios.append(error_scenario)

    def _extract_from_git(self, git: dict[str, Any]) -> None:
        """Extrae reglas de negocio desde cambios Git."""
        log.debug(f"Extracting from git {git.get('commit_sha')}")

        commit_sha = git.get("commit_sha", "")
        changed_files = git.get("changed_files", [])
        diff_summary = git.get("diff_summary", "")

        trace = TraceabilityLink(
            source_type="git",
            source_id=commit_sha,
            source_name=diff_summary or "Code changes",
        )

        # Detectar tipos de cambios
        test_files = [f for f in changed_files if "test" in f.lower()]
        if test_files:
            rule = BusinessRule(
                rule=f"Feature must have test coverage ({len(test_files)} test files)",
                traceability=trace,
                category="validation",
            )
            self.business_rules.append(rule)

        # Boundary testing
        if any("boundary" in f for f in changed_files):
            error_scenario = ErrorScenario(
                error_type="boundary",
                description="Boundary values provided",
                expected_outcome="System handles edge cases gracefully",
                traceability=trace,
            )
            self.error_scenarios.append(error_scenario)

    def _extract_assumptions(self, context: dict[str, Any]) -> list[str]:
        """Extrae supuestos del contexto."""
        return [
            "Issue is well-defined with clear acceptance criteria",
            "All required integrations are available",
            "Network connectivity is stable",
        ]
    
    def _extract_risks(self, context: dict[str, Any]) -> list[str]:
        """Extrae riesgos potenciales."""
        return [
            "Integration failures with external services",
            "Data validation edge cases",
            "Performance issues with large datasets",
            "Concurrent access conflicts",
        ]
    
    def _calculate_confidence(self) -> float:
        """Calcula nivel de confianza."""
        total_extractions = (
            len(self.business_rules)
            + len(self.preconditions)
            + len(self.happy_paths)
            + len(self.error_scenarios)
        )

        confidence = min(0.5 + (total_extractions * 0.05), 1.0)
        return round(confidence, 2)
    
    def _process_llm_result(self, llm_result: dict[str, Any], context: dict[str, Any]) -> None:
        """Procesa resultado del LLM."""
        issue = context.get("issue", {})
        issue_key = issue.get("issue_key", "")
        
        trace = TraceabilityLink(
            source_type="llm",
            source_id=issue_key,
            source_name="LLM Analysis",
        )

        # Business Rules
        for rule_data in llm_result.get("business_rules", []):
            if isinstance(rule_data, dict):
                rule = BusinessRule(
                    rule=rule_data.get("description", ""),
                    traceability=trace,
                    category=rule_data.get("category", "general"),
                )
            else:
                rule = BusinessRule(
                    rule=str(rule_data),
                    traceability=trace,
                    category="general",
                )
            self.business_rules.append(rule)

        # Preconditions
        for prec_data in llm_result.get("preconditions", []):
            precond = Precondition(
                precondition=prec_data if isinstance(prec_data, str) else prec_data.get("description", ""),
                traceability=trace,
            )
            self.preconditions.append(precond)

        # Happy Paths
        for path_data in llm_result.get("happy_paths", []):
            if isinstance(path_data, dict):
                happy_path = HappyPath(
                    name=path_data.get("name", "Happy Path"),
                    steps=path_data.get("steps", []),
                    traceability=trace,
                )
            else:
                happy_path = HappyPath(
                    name="Happy Path",
                    steps=[str(path_data)],
                    traceability=trace,
                )
            self.happy_paths.append(happy_path)

        # Error Scenarios
        for error_data in llm_result.get("error_scenarios", []):
            if isinstance(error_data, dict):
                error_scenario = ErrorScenario(
                    error_type=error_data.get("error_type", "validation"),
                    description=error_data.get("description", ""),
                    expected_outcome=error_data.get("expected_outcome", ""),
                    traceability=trace,
                )
            else:
                error_scenario = ErrorScenario(
                    error_type="validation",
                    description=str(error_data),
                    expected_outcome="Error handled gracefully",
                    traceability=trace,
                )
            self.error_scenarios.append(error_scenario)

        log.info(f"Processed LLM result: {len(self.business_rules)} rules extracted")
    
    def get_summary(self) -> str:
        """Retorna resumen textual del análisis."""
        return (
            f"Analysis Summary:\n"
            f"  Business Rules: {len(self.business_rules)}\n"
            f"  Preconditions: {len(self.preconditions)}\n"
            f"  Happy Paths: {len(self.happy_paths)}\n"
            f"  Error Scenarios: {len(self.error_scenarios)}\n"
            f"  Confidence: {self._calculate_confidence():.1%}"
        )