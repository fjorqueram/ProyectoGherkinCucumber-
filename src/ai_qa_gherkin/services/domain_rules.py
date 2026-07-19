from __future__ import annotations

import json
import os
from importlib.resources import files
from pathlib import Path
from typing import Any

from ai_qa_gherkin.utils.gherkin_text import GherkinText


class DomainRules:
    """Carga reglas de dominio configurables para renderizar Gherkin."""

    DEFAULT_FEATURE_TAGS = ["@regression"]
    DEFAULT_FEATURE_TITLE = "Visualización y acciones de la funcionalidad"
    DEFAULT_RULE = "Visualización de archivos complementarios"

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data if data is not None else self._load_default()

    @classmethod
    def from_file(cls, path: str | Path) -> "DomainRules":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def _load_default(cls) -> dict[str, Any]:
        override_path = os.getenv("GHERKIN_DOMAIN_RULES_FILE", "").strip()
        if override_path:
            return json.loads(Path(override_path).read_text(encoding="utf-8"))

        resource = files("ai_qa_gherkin.resources").joinpath("domain_rules.json")
        return json.loads(resource.read_text(encoding="utf-8"))

    def feature_title(self, scope_summary: str) -> str:
        clean = scope_summary.strip()
        text = self._fold(clean)
        for profile in self.data.get("feature_profiles", []):
            if self._matches(text, profile):
                return str(profile["title"])
        return clean or self.DEFAULT_FEATURE_TITLE

    def feature_tags(self, scenario_tags: list[list[str]], scope_summary: str) -> list[str]:
        tags = list(self.DEFAULT_FEATURE_TAGS)
        text = self._fold(scope_summary)
        for profile in self.data.get("feature_profiles", []):
            if self._matches(text, profile):
                tags.extend(profile.get("tags", []))

        for tag_group in scenario_tags:
            tags.extend(tag for tag in tag_group if tag.startswith("@") and tag != "@funcional")
        return list(dict.fromkeys(tags))

    def rule_for(self, text: str) -> str:
        folded = self._fold(text)
        for mapping in self.data.get("rule_mappings", []):
            if self._matches(folded, mapping):
                return str(mapping["name"])
        return self.DEFAULT_RULE

    def tags_for(self, text: str) -> list[str]:
        folded = self._fold(text)
        tags = ["@funcional"]
        for mapping in self.data.get("tag_mappings", []):
            if self._matches(folded, mapping):
                tags.append(str(mapping["tag"]))
        return list(dict.fromkeys(tags))

    def text_replacements(self) -> dict[str, str]:
        return {str(key): str(value) for key, value in self.data.get("text_replacements", {}).items()}

    def phrase_repairs(self) -> list[tuple[str, str]]:
        return [
            (str(rule["pattern"]), str(rule["replacement"]))
            for rule in self.data.get("phrase_repairs", [])
        ]

    def extension_rule_name(self) -> str:
        return str(self.data.get("extension_outline", {}).get("rule", "Íconos por extensión"))

    def extension_outline(self) -> dict[str, Any]:
        return self.data.get("extension_outline", {})

    def checkbox_action(self, text: str) -> str:
        folded = self._fold(text)
        rules = self.data.get("checkbox_actions", {})
        if any(keyword in folded for keyword in rules.get("paginated_match_any", [])):
            return str(rules.get("paginated", "Seleccionar todos los archivos visibles en la página"))
        return str(rules.get("default", "Mostrar acciones masivas al seleccionar múltiples archivos"))

    def error_mapping(self, text: str) -> dict[str, str] | None:
        folded = self._fold(text)
        for mapping in self.data.get("error_mappings", []):
            if self._matches(folded, mapping):
                return {
                    "context": str(mapping["context"]),
                    "action": str(mapping["action"]),
                    "name": str(mapping["name"]),
                }
        return None

    @staticmethod
    def _fold(text: str) -> str:
        return GherkinText.fold_accents(text).lower()

    @staticmethod
    def _matches(text: str, rule: dict[str, Any]) -> bool:
        match_any = [str(value).lower() for value in rule.get("match_any", [])]
        match_all = [str(value).lower() for value in rule.get("match_all", [])]
        any_ok = not match_any or any(value in text for value in match_any)
        all_ok = not match_all or all(value in text for value in match_all)
        return any_ok and all_ok
