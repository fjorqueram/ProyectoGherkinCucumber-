from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models.domain import GeneratedFeature
from ai_qa_gherkin.services.domain_rules import DomainRules
from ai_qa_gherkin.utils.gherkin_text import GherkinText
from ai_qa_gherkin.utils.text_cleaner import TextCleaner

log = get_logger("gherkin_service")


@dataclass(frozen=True)
class RenderScenario:
    rule: str
    name: str
    steps: list[str]
    tags: list[str]


class GherkinService:
    """Genera archivos .feature a partir de analisis multisource."""

    def __init__(self, domain_rules: DomainRules | None = None) -> None:
        self.text_cleaner = TextCleaner()
        self.domain_rules = domain_rules or DomainRules()
        log.info("GherkinService initialized")

    def generate_from_analysis(self, analysis: dict[str, Any]) -> GeneratedFeature:
        log.info(f"Generating Gherkin for {analysis.get('issue_key', 'UNKNOWN')}")

        issue_key = analysis.get("issue_key", "UNKNOWN")
        raw = analysis.get("raw", {})
        happy_paths = [
            path
            for path in raw.get("happy_paths", [])
            if not self._has_foreign_issue_key(path, issue_key)
        ]
        scenarios = self._build_scenarios(happy_paths, raw.get("error_scenarios", []))

        scope_summary = analysis.get("scope_summary", "")
        lines = self._feature_header(issue_key, scope_summary, scenarios)
        seen_steps: set[str] = set()
        for rule, rule_scenarios in self._group_by_rule(scenarios).items():
            lines.extend(["", f"  Regla: {rule}"])
            for scenario in rule_scenarios:
                lines.extend(self._scenario_lines(scenario, seen_steps))

        gherkin_text = self.text_cleaner.clean("\n".join(lines))
        log.info(f"Generated {len(happy_paths)} scenarios for {issue_key}")

        return GeneratedFeature(
            feature_name=f"{issue_key}.feature",
            gherkin_text=gherkin_text,
            language="es",
            tags=self._feature_tags(scenarios, scope_summary),
            scenarios_count=len(happy_paths),
            source_issue_key=issue_key,
        )

    def _build_scenarios(
        self,
        happy_paths: list[dict[str, Any]],
        error_scenarios: list[dict[str, Any]],
    ) -> list[RenderScenario]:
        scenarios = []
        for idx, path in enumerate(happy_paths, 1):
            steps = self._polish_steps(path.get("steps", []))
            name = self._scenario_name_from_steps(path.get("name", f"Escenario {idx}"), steps)
            scenarios.append(RenderScenario(
                rule=self._rule_for(name, steps),
                name=name,
                steps=steps,
                tags=self._functional_tags(name, steps),
            ))

        for error in error_scenarios:
            description = error.get("description", "")
            context, action = self._error_context_and_action(description)
            steps = self._polish_steps([
                f"Dado que {context}",
                f"Cuando {action}",
                f"Entonces {error.get('expected_outcome', '')}",
            ])
            name = self._error_scenario_name(description, context, action, error.get("error_type", "validation"))
            scenarios.append(RenderScenario(
                rule=self._rule_for(name, steps),
                name=name,
                steps=steps,
                tags=self._functional_tags(name, steps),
            ))

        return self._dedupe_render_scenarios(scenarios)

    def _feature_header(
        self,
        issue_key: str,
        scope_summary: str,
        scenarios: list[RenderScenario],
    ) -> list[str]:
        title = self._feature_title(scope_summary)
        return [
            "# language: es",
            "",
            " ".join(self._feature_tags(scenarios, scope_summary)),
            f"Caracter\u00edstica: {title}",
            f"  Historia relacionada: {issue_key}",
        ]

    def _scenario_lines(self, scenario: RenderScenario, seen_steps: set[str]) -> list[str]:
        if scenario.rule == self.domain_rules.extension_rule_name():
            return self._extension_outline_lines(scenario.tags)

        lines = ["", f"    {' '.join(scenario.tags)}", f"    Escenario: {scenario.name}"]
        lines.extend(f"      {self._make_step_unique(step, scenario.name, seen_steps)}" for step in scenario.steps)
        return lines

    def _extension_outline_lines(self, tags: list[str]) -> list[str]:
        outline = self.domain_rules.extension_outline()
        scenario_name = outline.get("scenario", "Mostrar \u00edcono seg\u00fan tipo de archivo")
        headers = outline.get("headers", ["extensi\u00f3n", "\u00edcono"])
        examples = outline.get("examples", [])
        return [
            "",
            f"    {' '.join(tags)}",
            f"    Esquema del escenario: {scenario_name}",
            f'      Dado que existe un archivo complementario con extensi\u00f3n "<{headers[0]}>"',
            "      Cuando se muestra la tabla de archivos complementarios",
            f'      Entonces se renderiza el \u00edcono "<{headers[1]}>" en la fila del archivo',
            "",
            "      Ejemplos:",
            f"        | {headers[0]} | {headers[1]} |",
            *[f"        | {example[0]} | {example[1]} |" for example in examples],
        ]

    def _feature_tags(self, scenarios: list[RenderScenario], scope_summary: str) -> list[str]:
        return self.domain_rules.feature_tags([scenario.tags for scenario in scenarios], scope_summary)

    def _feature_title(self, scope_summary: str) -> str:
        clean = TextCleaner.clean(scope_summary, auto_learn=False)
        clean = re.sub(r"^\[[^\]]+\]\s*\[[^\]]+\]\s*-\s*", "", clean).strip()
        return self.domain_rules.feature_title(clean)

    def _group_by_rule(self, scenarios: list[RenderScenario]) -> dict[str, list[RenderScenario]]:
        grouped: dict[str, list[RenderScenario]] = {}
        for scenario in scenarios:
            if scenario.rule == self.domain_rules.extension_rule_name() and scenario.rule in grouped:
                continue
            grouped.setdefault(scenario.rule, []).append(scenario)
        return grouped

    def _rule_for(self, name: str, steps: list[str]) -> str:
        return self.domain_rules.rule_for(" ".join([name, *steps]))

    def _functional_tags(self, name: str, steps: list[str]) -> list[str]:
        return self.domain_rules.tags_for(" ".join([name, *steps]))

    @classmethod
    def _dedupe_render_scenarios(cls, scenarios: list[RenderScenario]) -> list[RenderScenario]:
        seen: set[tuple[str, str]] = set()
        result: list[RenderScenario] = []
        for scenario in scenarios:
            fingerprint = (
                scenario.rule,
                GherkinText.fold_accents(scenario.name).lower(),
            )
            if fingerprint in seen:
                continue
            if any(cls._equivalent_render_scenario(scenario, existing) for existing in result):
                log.debug(f"Skipping equivalent rendered scenario: {scenario.name[:80]}")
                continue
            seen.add(fingerprint)
            result.append(scenario)
        return result

    @classmethod
    def _equivalent_render_scenario(cls, left: RenderScenario, right: RenderScenario) -> bool:
        if left.rule != right.rule:
            return False

        left_steps = {GherkinText.core_step_for_dedupe(step) for step in left.steps}
        right_steps = {GherkinText.core_step_for_dedupe(step) for step in right.steps}
        left_steps.discard("")
        right_steps.discard("")
        if left_steps & right_steps:
            return True

        left_tokens = GherkinText.scenario_tokens(left.name, left.steps)
        right_tokens = GherkinText.scenario_tokens(right.name, right.steps)
        if not left_tokens or not right_tokens:
            return False

        intersection = sum((left_tokens & right_tokens).values())
        union = sum((left_tokens | right_tokens).values())
        similarity = intersection / union if union else 0.0
        return similarity >= 0.25 and cls._same_verifiable_outcome(left.steps, right.steps)

    @staticmethod
    def _same_verifiable_outcome(left_steps: list[str], right_steps: list[str]) -> bool:
        left_then = GherkinService._first_step_body(left_steps, ("Entonces", "Then"))
        right_then = GherkinService._first_step_body(right_steps, ("Entonces", "Then"))
        if not left_then or not right_then:
            return False
        left_tokens = set(GherkinText.scenario_tokens("", [left_then]))
        right_tokens = set(GherkinText.scenario_tokens("", [right_then]))
        if not left_tokens or not right_tokens:
            return False
        return len(left_tokens & right_tokens) / len(left_tokens | right_tokens) >= 0.50

    def _polish_steps(self, steps: list[str]) -> list[str]:
        polished = [self._polish_text(str(step)) for step in steps if str(step).strip()]
        return self._ensure_gherkin_steps(polished)

    @staticmethod
    def _ensure_gherkin_steps(steps: list[str]) -> list[str]:
        if all(GherkinText.is_step_line(step) for step in steps):
            return steps

        keywords = ["Dado que", "Cuando", "Entonces"]
        coerced = []
        for idx, step in enumerate(steps[:3]):
            if GherkinText.is_step_line(step):
                coerced.append(step)
                continue
            keyword = keywords[min(idx, len(keywords) - 1)]
            coerced.append(f"{keyword} {step.strip()}")
        return coerced or GherkinText.fallback_steps()

    def _polish_text(self, text: str) -> str:
        result = GherkinText.normalize_spaces(text).rstrip(" .")
        for source, target in self.domain_rules.text_replacements().items():
            result = re.sub(rf"\b{source}\b", target, result, flags=re.IGNORECASE)
        for pattern, replacement in self.domain_rules.phrase_repairs():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        result = GherkinService._normalize_step_sentence(result)
        return result

    @staticmethod
    def _normalize_step_sentence(text: str) -> str:
        match = re.match(
            r"^(Dado que|Dado|Cuando|Entonces|Y|Pero)\s+(.+)$",
            text.strip(),
            flags=re.IGNORECASE,
        )
        if not match:
            return text

        body = match.group(2).strip()
        body = re.sub(r"^(El|La|Los|Las|Un|Una|Se)\b", lambda m: m.group(1).lower(), body)
        return f"{match.group(1)} {body}"

    def _error_context_and_action(self, description: str) -> tuple[str, str]:
        mapping = self.domain_rules.error_mapping(description)
        if mapping:
            return mapping["context"], mapping["action"]
        return description or "existe una condici\u00f3n de error", "el usuario completa la acci\u00f3n solicitada"

    def _error_action_from_description(self, description: str) -> str:
        return self._error_context_and_action(description)[1]

    def _error_scenario_name(
        self,
        description: str,
        context: str,
        action: str,
        fallback: str,
    ) -> str:
        mapping = self.domain_rules.error_mapping(" ".join([description, context, action]))
        if mapping:
            return mapping["name"]
        return self._polish_text(description or fallback)

    def _scenario_name_from_steps(self, raw_name: str, steps: list[str]) -> str:
        cleaned_name = GherkinText.normalize_scenario_name(self._polish_text(raw_name))
        all_text = GherkinText.fold_accents(" ".join([cleaned_name, *steps])).lower()
        if "checkbox" in all_text or "seleccionar todos" in all_text or "acciones masivas" in all_text:
            return self.domain_rules.checkbox_action(all_text)

        first_given = self._first_step_body(steps, ("Dado", "Given"))
        if not first_given or GherkinText.normalize_step(cleaned_name) != GherkinText.normalize_step(first_given):
            return self._polish_text(cleaned_name)

        action = self._business_action(cleaned_name, steps)
        context = self._context_phrase(cleaned_name)
        name = GherkinText.normalize_spaces(f"{action} {context}".strip())
        return self._polish_text(self._trim_title(name)) if len(name) >= 5 else self._polish_text(cleaned_name)

    def _business_action(self, scenario_name: str, steps: list[str]) -> str:
        when = self._first_step_body(steps, ("Cuando", "When"))
        then = self._first_step_body(steps, ("Entonces", "Then"))
        haystack = GherkinText.fold_accents(" ".join([scenario_name, when, then])).lower()

        action_patterns = [
            ("checkbox", self.domain_rules.checkbox_action(haystack)),
            ("seleccionar todos", self.domain_rules.checkbox_action(haystack)),
            ("descarga", "Descargar archivo"),
            ("descargar", "Descargar archivo"),
            ("eliminar", "Eliminar archivo"),
            ("agregar", "Agregar archivo"),
            ("paginacion", "Navegar archivos paginados"),
            ("no es visible", "Restringir acceso a otros archivos"),
            ("deshabilitada", "Restringir acceso a otros archivos"),
            ("icono", "Mostrar icono de archivo"),
            ("configuracion regional", "Mostrar textos regionalizados"),
            ("otros archivos", "Visualizar pesta\u00f1a Otros archivos"),
        ]
        for keyword, action in action_patterns:
            if keyword in haystack:
                return action
        return self._sentence_case(when or then or scenario_name)

    @staticmethod
    def _trim_title(text: str, limit: int = 120) -> str:
        text = GherkinText.normalize_spaces(text).strip(" .")
        if len(text) <= limit:
            return text
        trimmed = text[:limit].rsplit(" ", 1)[0].strip(" .,;:")
        return trimmed if len(trimmed) >= 5 else text[:limit].strip(" .,;:")

    @staticmethod
    def _context_phrase(text: str) -> str:
        normalized = GherkinText.fold_accents(text).lower()
        context_patterns = [
            ("permisos de lectura", "con permisos de lectura"),
            ("permisos de escritura", "con permisos de escritura"),
            ("permisos de visualizacion", "con permisos de visualizaci\u00f3n"),
            ("permisos de agregar", "con permisos para agregar archivo"),
            ("sin permisos", "sin permisos"),
            ("no tiene permisos", "sin permisos"),
            ("sin archivos", "sin archivos complementarios disponibles"),
            ("no existen archivos", "sin archivos complementarios disponibles"),
            ("existen archivos", "con archivos complementarios disponibles"),
            ("excede el limite", "con paginaci\u00f3n"),
            ("extension no", "con extensi\u00f3n no soportada"),
            ("extension", "con extensi\u00f3n soportada"),
            ("configuracion regional no", "sin configuraci\u00f3n regional"),
            ("configuracion regional", "con configuraci\u00f3n regional"),
        ]
        for keyword, phrase in context_patterns:
            if keyword in normalized:
                return phrase
        return ""

    @staticmethod
    def _first_step_body(steps: list[str], keywords: tuple[str, ...]) -> str:
        lower_keywords = tuple(keyword.lower() for keyword in keywords)
        for step in steps:
            stripped = step.strip()
            if stripped.lower().startswith(lower_keywords):
                return GherkinText.strip_step_keyword(stripped)
        return ""

    @staticmethod
    def _sentence_case(text: str) -> str:
        text = GherkinText.normalize_spaces(text)
        return f"{text[:1].upper()}{text[1:]}" if text else ""

    def _make_step_unique(self, step: str, scenario_name: str, seen_steps: set[str]) -> str:
        normalized = GherkinText.normalize_step(step)
        if not normalized:
            return step
        if normalized not in seen_steps:
            seen_steps.add(normalized)
            return step

        candidate = self._duplicate_step_variant(step, scenario_name)
        suffix = 2
        while GherkinText.normalize_step(candidate) in seen_steps:
            candidate = f"{self._duplicate_step_variant(step, scenario_name)} ({suffix})"
            suffix += 1

        seen_steps.add(GherkinText.normalize_step(candidate))
        return candidate

    @staticmethod
    def _duplicate_step_variant(step: str, scenario_name: str) -> str:
        match = re.match(
            r"^(Dado|Given|Cuando|When|Entonces|Then|Y|And|Pero|But)\s+(.+)$",
            step.strip(),
            flags=re.IGNORECASE,
        )
        context = re.sub(
            r"^(el|la|los|las|un|una)\s+",
            "",
            scenario_name.strip(),
            flags=re.IGNORECASE,
        )
        context = GherkinService._context_phrase(context) or f"para {GherkinText.normalize_spaces(context).strip(' .')[:80]}"
        if not match:
            return f"{step} {context}"
        return f"{match.group(1)} {match.group(2).strip()} {context}"

    @staticmethod
    def _has_foreign_issue_key(path: dict[str, Any], issue_key: str) -> bool:
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
        name = GherkinText.normalize_scenario_name(
            TextCleaner.clean(scenario.get("name", "Escenario"), auto_learn=False)
        )
        lines = [f"  {tags}", f"    Escenario: {name}"]
        lines.extend(
            f"        {TextCleaner.clean(step, auto_learn=False)}"
            for step in scenario.get("steps", [])
        )
        return lines

    @staticmethod
    def _format_error_scenario(error: dict[str, Any]) -> list[str]:
        error_type = TextCleaner.clean(error.get("error_type", "validation"), auto_learn=False)
        description = TextCleaner.clean(error.get("description", ""), auto_learn=False)
        expected = TextCleaner.clean(error.get("expected_outcome", ""), auto_learn=False)
        return [
            "  @error-handling",
            f"    Escenario: Error - {error_type}",
            f"        Dado que {description}",
            "        Cuando ocurre un error",
            f"        Entonces {expected}",
        ]
