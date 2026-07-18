from __future__ import annotations
from typing import Any
from dotenv import load_dotenv
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models.domain import (
    BusinessRule,
    Precondition,
    HappyPath,
    ErrorScenario,
    TraceabilityLink,
    AnalysisResult,
)
from ai_qa_gherkin.clients.llm_client import LLMClient

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

    def analyze(self, merged_context: dict[str, Any]) -> AnalysisResult:
        """
        Analiza contexto merged y extrae reglas, precondiciones,
        caminos felices y errores.
        """
        log.info("Starting analysis of merged context")
        
        issue_data = merged_context.get("issue") or {}
        issue_key = issue_data.get("issue_key") or merged_context.get("issue_key", "UNKNOWN")
        scope = merged_context.get("primary_scope", "")

        # Limpiar análisis previos
        self.business_rules = []
        self.preconditions = []
        self.happy_paths = []
        self.error_scenarios = []

        # Usar LLM o mock
        if self.use_llm and self.llm_client is not None:
            log.info(f"Analyzing {issue_key} with LLM")
            try:
                llm_result = self.llm_client.extract_business_rules(merged_context)
                self._process_llm_result(llm_result, merged_context)
            except Exception as e:
                log.warning(f"LLM analysis failed: {str(e)}, falling back to mock")
                self._analyze_with_mock(merged_context)
        else:
            # Análisis manual mockeado
            log.info(f"Analyzing {issue_key} with mock rules")
            self._analyze_with_mock(merged_context)

        # Construir AnalysisResult
        analysis_result = AnalysisResult(
            issue_key=issue_key,
            scope_summary=scope,
            business_rules=[br.rule for br in self.business_rules],
            assumptions=self._extract_assumptions(merged_context),
            risks=self._extract_risks(merged_context),
            confidence=self._calculate_confidence(),
            raw={
                "business_rules": [br.model_dump() for br in self.business_rules],
                "preconditions": [pc.model_dump() for pc in self.preconditions],
                "happy_paths": [hp.model_dump() for hp in self.happy_paths],
                "error_scenarios": [es.model_dump() for es in self.error_scenarios],
            },
        )

        log.info(
            f"Analysis complete: {len(self.business_rules)} rules, "
            f"{len(self.preconditions)} preconditions, "
            f"{len(self.happy_paths)} happy paths, "
            f"{len(self.error_scenarios)} error scenarios"
        )

        return analysis_result

    def _analyze_with_mock(self, context: dict[str, Any]) -> None:
        """Realiza análisis mock."""
        if context.get("issue"):
            self._extract_from_issue(context["issue"])
        if context.get("confluence"):
            self._extract_from_confluence(context["confluence"])
        if context.get("git"):
            self._extract_from_git(context["git"])

    def _extract_from_issue(self, issue: dict[str, Any]) -> None:
        """Extrae reglas de negocio, precondiciones desde Jira issue."""
        log.debug(f"Extracting from issue {issue.get('issue_key')}")

        issue_key = issue.get("issue_key", "")
        summary = issue.get("summary", "")
        description = issue.get("description", "")

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

        # Acceptance Criteria como reglas
        for ac in issue.get("acceptance_criteria", []):
            rule = BusinessRule(
                rule=ac,
                traceability=trace,
                category="validation",
            )
            self.business_rules.append(rule)

        # Precondiciones
        if "precondition" in description.lower() or "prerequisite" in description.lower():
            precond = Precondition(
                precondition=description,
                traceability=trace,
            )
            self.preconditions.append(precond)

        # Camino feliz
        if summary:
            happy_path = HappyPath(
                name=f"Happy path for {summary}",
                steps=[
                    "User initiates the feature",
                    "System validates inputs",
                    "Feature is executed successfully",
                    "Result is returned to user",
                ],
                traceability=trace,
            )
            self.happy_paths.append(happy_path)

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