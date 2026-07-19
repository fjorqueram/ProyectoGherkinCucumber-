from __future__ import annotations

import re
from typing import Any

from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models.domain import GeneratedFeature
from ai_qa_gherkin.utils.text_cleaner import TextCleaner

log = get_logger("gherkin_service")


class GherkinService:
    """Genera archivos .feature a partir de análisis multisource."""

    def __init__(self) -> None:
        self.text_cleaner = TextCleaner()
        log.info("GherkinService initialized")

    def generate_from_analysis(self, analysis: dict[str, Any]) -> GeneratedFeature:
        """Genera un feature Gherkin desde análisis."""
        log.info(f"Generating Gherkin for {analysis.get('issue_key', 'UNKNOWN')}")

        issue_key = analysis.get("issue_key", "UNKNOWN")
        scope_summary = analysis.get("scope_summary", "")
        raw = analysis.get("raw", {})

        happy_paths = [
            path
            for path in raw.get("happy_paths", [])
            if not self._has_foreign_issue_key(path, issue_key)
        ]
        error_scenarios = raw.get("error_scenarios", [])

        lines = []
        lines.append("# language: es")
        lines.append("")

        tags = ["@smoke", "@regression"]
        lines.append(" ".join(tags))

        feature_title = scope_summary if scope_summary else f"Feature {issue_key}"
        lines.append(f"Característica: {feature_title}")
        lines.append(f"  Feature relacionada a {issue_key}")
        lines.append("")

        lines.append("  Antecedentes:")
        lines.append("    Dado que el sistema está disponible")
        lines.append("    Dado que tengo credenciales válidas")
        lines.append("")

        for idx, path in enumerate(happy_paths, 1):
            name = path.get("name", f"Escenario {idx}")
            steps = path.get("steps", [])
            source = path.get("source", "jira")

            name = self._clean_scenario_name(name)
            tag = self._get_tag_for_source(source)
            lines.append(f"@{tag}")
            lines.append(f"  Escenario: {name}")

            for step in steps:
                lines.append(f"    {step}")

            lines.append("")

        for error in error_scenarios:
            error_type = error.get("error_type", "validation")
            description = error.get("description", "")
            expected_outcome = error.get("expected_outcome", "")

            lines.append("@error-handling")
            lines.append(f"  Escenario: {error_type} - {description}")
            lines.append(f"    Entonces {expected_outcome}")
            lines.append("")

        gherkin_text = self.text_cleaner.clean("\n".join(lines))

        log.info(f"Generated {len(happy_paths)} scenarios for {issue_key}")

        return GeneratedFeature(
            feature_name=f"{issue_key}.feature",
            gherkin_text=gherkin_text,
            language="es",
            tags=tags,
            scenarios_count=len(happy_paths),
            source_issue_key=issue_key,
        )

    @staticmethod
    def _get_tag_for_source(source: str) -> str:
        """Retorna el tag apropiado según la fuente."""
        source_lower = source.lower()

        if source_lower == "jira":
            return "jira"
        if source_lower == "confluence":
            return "confluence"
        if source_lower == "git":
            return "git"
        return "validation"

    @staticmethod
    def _clean_scenario_name(name: str) -> str:
        """Limpia el nombre del escenario removiendo fragmentos de pasos."""
        name = TextCleaner.clean(name, auto_learn=False)
        keywords = ["Dado que", "Cuando", "Entonces", "Y ", "Given", "When", "Then", "And"]

        for keyword in keywords:
            idx = name.find(keyword)
            if idx > 0:
                name = name[:idx].strip()

        name = re.sub(r"\s+", " ", name).strip()
        name = name[:80].strip()

        if not name or len(name) < 3:
            name = "Escenario"

        return name

    @staticmethod
    def _has_foreign_issue_key(path: dict[str, Any], issue_key: str) -> bool:
        """Evita escribir escenarios ligados a otra issue en el .feature."""
        traceability = path.get("traceability", {}) or {}
        values = [
            path.get("name", ""),
            " ".join(str(step) for step in path.get("steps", []) or []),
            traceability.get("source_id", ""),
            traceability.get("source_name", ""),
            traceability.get("url", ""),
        ]
        text = " ".join(str(value) for value in values)
        found_keys = set(re.findall(r"\b[A-Z]+-\d+\b", text, flags=re.IGNORECASE))
        return any(key.upper() != issue_key.upper() for key in found_keys)

    @staticmethod
    def _format_scenario(scenario: dict[str, Any], tags: str = "@smoke") -> list[str]:
        """Formatea un escenario Gherkin."""
        lines = []

        name = GherkinService._clean_scenario_name(scenario.get("name", "Escenario"))
        steps = scenario.get("steps", [])

        lines.append(f"  {tags}")
        lines.append(f"    Escenario: {name}")

        for step in steps:
            lines.append(f"        {TextCleaner.clean(step, auto_learn=False)}")

        return lines

    @staticmethod
    def _format_error_scenario(error: dict[str, Any]) -> list[str]:
        """Formatea un escenario de error."""
        lines = []

        error_type = TextCleaner.clean(error.get("error_type", "validation"), auto_learn=False)
        description = TextCleaner.clean(error.get("description", ""), auto_learn=False)
        expected = TextCleaner.clean(error.get("expected_outcome", ""), auto_learn=False)

        lines.append("  @error-handling")
        lines.append(f"    Escenario: Error - {error_type}")
        lines.append(f"        Dado que {description}")
        lines.append("        Cuando ocurre un error")
        lines.append(f"        Entonces {expected}")

        return lines
