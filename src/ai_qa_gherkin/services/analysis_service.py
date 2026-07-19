from __future__ import annotations
import re
import html
from dotenv import load_dotenv
from typing import Any, Literal, cast
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models.domain import (
    JiraIssue,
    BusinessRule,
    Precondition,
    HappyPath,
    ErrorScenario,
    TraceabilityLink,
)
from ai_qa_gherkin.clients.llm_client import LLMClient

log = get_logger("analysis_service")
load_dotenv()

RuleCategory = Literal["general", "validation", "permission", "performance"]
SourceType = Literal["jira", "confluence", "git", "llm"]

class AnalysisService:
    """Servicio de anÃ¡lisis con soporte para LLM real o mock."""

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
        self.business_rules = []
        self.preconditions = []
        self.happy_paths = []
        self.error_scenarios = []

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

        # âœ… EXTRAER issue_key PRIMERO
        actual_issue_data = issue_data.get("issue", {}) if isinstance(issue_data.get("issue"), dict) else issue_data
        issue_key = (
            actual_issue_data.get("key")
            or actual_issue_data.get("issue_key")
            or issue_data.get("key")
            or issue_data.get("issue_key", "UNKNOWN")
        )
        log.info(f"Processing issue_key: {issue_key}")

        # âœ… PASAR issue_key a los mÃ©todos
        self._extract_from_issue(issue_data)

        # Si hay contexto multisource, extraer de Confluence y Git
        if "confluence" in issue_data and issue_data.get("confluence"):
            self._extract_from_confluence(issue_data.get("confluence", {}), issue_key)
        if "git" in issue_data and issue_data.get("git"):
            self._extract_from_git(issue_data.get("git", {}))

        if self.use_llm and self.llm_client:
            llm_result = self.llm_client.extract_business_rules(issue_data)
            self._process_llm_result(llm_result, issue_data)
            self._deduplicate_happy_paths()

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
            "issue_key": issue_key,
            "scope_summary": actual_issue_data.get("summary", issue_data.get("summary", "")),
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
                        "source": hp.source,  # â† AGREGAR source
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
        """Realiza anÃ¡lisis mock."""
        # Extraer issue_key del contexto
        issue_key = context.get("issue", {}).get("issue_key", "UNKNOWN")

        if context.get("issue"):
            self._extract_from_issue(context["issue"])
        if context.get("confluence"):
            self._extract_from_confluence(context["confluence"], issue_key)  # âœ… AGREGAR issue_key
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

        # Si es lista, Ãºnela
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

                # âœ… MEJORADO: Extraer nombre ANTES del primer "Dado/Cuando/Entonces"
                scenario_name = None

                # Buscar la primera lÃ­nea que NO sea un paso Gherkin
                lines_in_block = block.split('\n')

                for line in lines_in_block:
                    line_stripped = line.strip()

                    # Saltar lÃ­neas vacÃ­as
                    if not line_stripped:
                        continue

                    # Si la lÃ­nea comienza con palabra clave Gherkin, hemos pasado el nombre
                    if any(line_stripped.lower().startswith(kw) for kw in
                        ["dado", "cuando", "entonces", "y ",
                            "given", "when", "then", "and "]):
                        break

                    # Esta es la lÃ­nea del nombre
                    if scenario_name is None:
                        scenario_name = line_stripped
                        break

                # Si no encontrÃ³ nombre, usar fallback
                if not scenario_name:
                    scenario_name = f"Escenario {block_idx}"

                # Limpiar nombre: mÃ¡ximo 80 caracteres, sin fragmentos de pasos
                scenario_name = scenario_name[:80].strip()

                # Remover fragmentos de pasos al final (ej: "Dado que el usuario tiene")
                # Si el nombre termina con palabras incompletas de un paso, truncar
                if any(scenario_name.lower().endswith(kw) for kw in
                    ["dado que", "cuando ", "entonces ", "dado que el", "cuando ", "y "]):
                    # Truncar en el Ãºltimo espacio
                    parts = scenario_name.rsplit(' ', 2)
                    scenario_name = parts[0] if parts else scenario_name

                # Asegurar que el nombre no sea vacÃ­o
                if not scenario_name or len(scenario_name) < 3:
                    scenario_name = f"Escenario {block_idx}"

                log.debug(f"Processing scenario {block_idx}: {scenario_name}")

                # Extraer steps
                steps = self._extract_gherkin_steps(block)

                if steps and len(steps) >= 2:
                    log.info(f"âœ“ Adding scenario: {scenario_name} ({len(steps)} steps)")

                    happy_path = HappyPath(
                        name=scenario_name,
                        steps=steps,
                        traceability=trace,
                        source="jira",  # âœ… AGREGAR source
                    )
                    self.happy_paths.append(happy_path)
                else:
                    log.debug(f"âœ— Scenario {block_idx} rejected: only {len(steps)} steps")

            log.info(f"Total happy_paths extracted: {len(self.happy_paths)}")

        # Fallback
        if not self.happy_paths and summary:
            log.warning("No happy paths found, using fallback")
            happy_path = HappyPath(
                name=f"Happy path for {summary}",
                steps=["User initiates", "System processes", "Result returned"],
                traceability=trace,
                source="jira",  # âœ… AGREGAR source
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

    def _extract_from_jira(self, issue: dict[str, Any], traceability: TraceabilityLink | None = None) -> None:
        """Alias compatible para codigo/tests previos."""
        self._extract_from_issue(issue)

    def _extract_from_confluence(self, confluence: dict[str, Any], issue_key: str) -> None:
        """Extrae escenarios desde Confluence encontrada."""
        pages = confluence.get("pages", [])
        if not pages and confluence:
            pages = [
                {
                    "page_id": confluence.get("page_id"),
                    "id": confluence.get("page_id"),
                    "title": confluence.get("page_title") or confluence.get("title") or "Confluence",
                    "content": confluence.get("content", ""),
                    "url": confluence.get("page_url") or confluence.get("url", ""),
                    "user_steps": confluence.get("user_steps", []),
                }
            ]

        if not pages:
            return

        log.info(f"Extracting from {len(pages)} Confluence pages for {issue_key}")

        for page in pages:
            page_id = page.get("page_id") or page.get("id")
            title = page.get("title", "")
            content = page.get("content", "")

            trace = TraceabilityLink(
                source_type="confluence",
                source_id=str(page_id or ""),
                source_name=str(title or ""),
                url=str(page.get("url", "") or ""),
            )

            # âœ… Limpiar contenido HTML
            clean_content = self._clean_html_simple(content)

            # âœ… Extraer pasos de la descripciÃ³n
            steps = self._steps_from_user_steps(page.get("user_steps", []))
            if not steps:
                steps = self._generate_steps_from_confluence(clean_content)

            if steps and len(steps) >= 2:
                happy_path = HappyPath(
                    name=self._scenario_name_from_confluence(title, clean_content),
                    steps=steps,
                    traceability=trace,
                    source="confluence",
                )
                self.happy_paths.append(happy_path)
                log.info(f"âœ“ Created scenario from Confluence: {title[:60]} ({len(steps)} steps)")
            else:
                log.warning(f"âœ— Confluence page '{title}' rejected: only {len(steps)} steps")

    def _clean_html_simple(self, content: str) -> str:
        """Limpia entidades HTML del contenido."""

        # Decodificar entidades HTML
        content = html.unescape(content)

        # Remover tags HTML
        content = re.sub(r'<[^>]+>', '\n', content)

        # Remover espacios mÃºltiples
        content = ' '.join(content.split())

        return content

    def _generate_steps_from_confluence(self, content: str) -> list[str]:
        """
        Genera pasos Gherkin automÃ¡ticamente desde contenido de Confluence.
        Si no encuentra pasos explÃ­citos, crea pasos genÃ©ricos.
        """
        import re

        steps = []

        try:
            # âœ… Estrategia 1: Buscar lÃ­neas con palabras clave Gherkin
            lines = content.split('\n')

            for line in lines:
                line = line.strip()

                if not line or len(line) < 10:
                    continue

                lower_line = line.lower()

                if (lower_line.startswith("dado que ") or
                    lower_line.startswith("cuando ") or
                    lower_line.startswith("entonces ") or
                    lower_line.startswith("y ")):

                    if len(line) > 120:
                        line = line[:120] + "..."

                    steps.append(line)
                    log.debug(f"  + Found Gherkin step: {line[:80]}")

            # âœ… Estrategia 2: Si no encontrÃ³, crear pasos genÃ©ricos del contenido
            if not steps and content:
                # Dividir contenido en oraciones/puntos
                sentences = re.split(r'[\.;:]', content)
                sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]

                if sentences:
                    # Tomar primeras 3 oraciones como pasos
                    steps.append(f"Dado que {sentences[0][:80]}")

                    if len(sentences) > 1:
                        steps.append(f"Cuando {sentences[1][:80]}")

                    if len(sentences) > 2:
                        steps.append(f"Entonces {sentences[2][:80]}")

                    log.debug(f"  Generated {len(steps)} generic steps from content")

            # âœ… Estrategia 3: Si aÃºn estÃ¡ vacÃ­o, usar pasos mÃ­nimos
            if not steps:
                steps = [
                    "Dado que se accede a la funcionalidad",
                    "Cuando se ejecuta la acciÃ³n",
                    "Entonces se verifica el resultado"
                ]
                log.debug(f"  Using fallback generic steps")

            log.info(f"Generated {len(steps)} steps from Confluence content")

        except Exception as e:
            log.warning(f"Error generating Confluence steps: {e}")
            # Fallback mÃ­nimo
            steps = [
                "Dado que se accede a la funcionalidad",
                "Cuando se ejecuta la acciÃ³n",
                "Entonces se verifica el resultado"
            ]

        return steps

    def _extract_steps_from_confluence_content(self, content: str) -> list[str]:
        """Extrae pasos Gherkin del contenido de Confluence."""
        steps = []

        try:
            # Buscar lÃ­neas que empiecen con palabras clave Gherkin
            lines = content.split('\n')

            for line in lines:
                line = line.strip()

                if not line:
                    continue

                # Detectar palabras clave Gherkin (case-insensitive)
                lower_line = line.lower()

                if (lower_line.startswith("dado que ") or
                    lower_line.startswith("cuando ") or
                    lower_line.startswith("entonces ") or
                    lower_line.startswith("y ")):

                    # âœ… Truncar si es muy largo
                    if len(line) > 120:
                        line = line[:120] + "..."

                    steps.append(line)
                    log.debug(f"  + Confluence step: {line[:80]}")

            log.debug(f"Extracted {len(steps)} steps from Confluence content")

        except Exception as e:
            log.warning(f"Error extracting Confluence steps: {e}")

        return steps

    def _extract_from_git(self, git: dict[str, Any], issue_key: str | None = None) -> None:
        """Extrae reglas de negocio desde cambios Git."""
        log.debug(f"Extracting from git {git.get('commit_sha')}")

        commit_sha = git.get("commit_sha", "")
        changed_files = git.get("changed_files", [])
        diff_summary = git.get("diff_summary", "")
        if not commit_sha and git.get("commits"):
            first_commit = git["commits"][0]
            if isinstance(first_commit, dict):
                commit_sha = first_commit.get("sha", "")

        trace = TraceabilityLink(
            source_type="git",
            source_id=str(commit_sha or ""),
            source_name=str(diff_summary or "Code changes"),
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

        for idx, scenario in enumerate(git.get("test_scenarios", []) or [], 1):
            self.happy_paths.append(
                HappyPath(
                    name=f"Regresion Git {idx}",
                    steps=[
                        "Dado que los cambios relacionados estan disponibles",
                        f"Cuando se valida {str(scenario)[:100]}",
                        "Entonces el comportamiento esperado se mantiene",
                    ],
                    traceability=trace,
                    source="git",
                )
            )

    def _steps_from_user_steps(self, user_steps: list[str]) -> list[str]:
        clean_steps = [str(step).strip() for step in user_steps if str(step).strip()]
        if not clean_steps:
            return []
        steps = [f"Dado que {clean_steps[0][:100]}"]
        if len(clean_steps) > 1:
            steps.append(f"Cuando {clean_steps[1][:100]}")
        if len(clean_steps) > 2:
            steps.append(f"Entonces {clean_steps[2][:100]}")
        return steps

    def _scenario_name_from_confluence(self, title: str, content: str) -> str:
        base = title or "Escenario desde Confluence"
        if "first time" in base.lower() or "primer" in content.lower() or "nuevo" in content.lower():
            return f"Onboarding - {base[:55]}"
        return base[:70]

    def _deduplicate_happy_paths(self) -> None:
        seen = set()
        deduped = []
        for path in self.happy_paths:
            fingerprint = re.sub(r"\s+", " ", path.name.strip().lower())
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            deduped.append(path)
        self.happy_paths = deduped

    def _count_by_source(self, source: str) -> int:
        return len([hp for hp in self.happy_paths if hp.source == source])

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
            "Riesgo de regresiÃ³n en flujos relacionados",
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
        issue = context.get("issue", {}) if isinstance(context.get("issue"), dict) else context
        issue_key = issue.get("issue_key") or issue.get("key") or context.get("issue_key", "")

        trace = TraceabilityLink(
            source_type="llm",
            source_id=str(issue_key or ""),
            source_name="LLM Analysis",
        )

        # Business Rules
        for rule_data in llm_result.get("business_rules", []):
            if isinstance(rule_data, dict):
                rule = BusinessRule(
                    rule=rule_data.get("description", ""),
                    traceability=trace,
                    category=self._normalize_rule_category(rule_data.get("category", "general")),
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
            precondition = (
                prec_data
                if isinstance(prec_data, str)
                else str(prec_data.get("description", "")) if isinstance(prec_data, dict) else str(prec_data)
            )
            precond = Precondition(
                precondition=precondition,
                traceability=trace,
            )
            self.preconditions.append(precond)

        # Happy Paths
        for path_data in llm_result.get("happy_paths", []):
            if isinstance(path_data, dict):
                steps = self._normalize_steps(path_data.get("steps", []))
                if len(steps) < 2:
                    continue
                happy_path = HappyPath(
                    name=str(path_data.get("name") or "Happy Path"),
                    steps=steps,
                    traceability=self._trace_from_llm_path(path_data, trace),
                    source=self._source_from_llm_path(path_data),
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

    def _normalize_steps(self, steps: Any) -> list[str]:
        if isinstance(steps, str):
            raw_steps = [line.strip() for line in steps.splitlines()]
        elif isinstance(steps, list):
            raw_steps = [str(step).strip() for step in steps]
        else:
            raw_steps = []
        return [step for step in raw_steps if step]

    def _source_from_llm_path(self, path_data: dict[str, Any]) -> SourceType:
        source = str(path_data.get("source") or "jira").lower()
        if source in {"jira", "confluence", "git"}:
            return cast(SourceType, source)
        return "jira"

    def _normalize_rule_category(self, category: Any) -> RuleCategory:
        value = str(category or "general").lower()
        if value in {"general", "validation", "permission", "performance"}:
            return cast(RuleCategory, value)
        return "general"

    def _trace_from_llm_path(self, path_data: dict[str, Any], default_trace: TraceabilityLink) -> TraceabilityLink:
        source = self._source_from_llm_path(path_data)
        return TraceabilityLink(
            source_type=source,
            source_id=str(path_data.get("source_id") or default_trace.source_id),
            source_name=str(path_data.get("source_name") or default_trace.source_name),
            url=str(path_data.get("source_url") or ""),
        )

    def get_summary(self) -> str:
        """Retorna resumen textual del anÃ¡lisis."""
        return (
            f"Analysis Summary:\n"
            f"  Business Rules: {len(self.business_rules)}\n"
            f"  Preconditions: {len(self.preconditions)}\n"
            f"  Happy Paths: {len(self.happy_paths)}\n"
            f"  Error Scenarios: {len(self.error_scenarios)}\n"
            f"  Confidence: {self._calculate_confidence():.1%}"
        )
