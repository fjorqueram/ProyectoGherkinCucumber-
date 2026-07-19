from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import ClassVar


class GherkinText:
    """Helpers compartidos para limpiar, detectar y comparar texto Gherkin."""

    STEP_KEYWORD_PATTERN = re.compile(
        r"^(Dado que|Dado|Given|Cuando|When|Entonces|Then|Y|And|Pero|But)\s+",
        flags=re.IGNORECASE,
    )
    STEP_PREFIXES = ("dado que ", "dado ", "cuando ", "entonces ", "y ")
    SOURCE_TAGS: ClassVar[dict[str, str]] = {"jira": "jira", "confluence": "confluence", "git": "git"}
    FALLBACK_STEPS: ClassVar[tuple[str, ...]] = (
        "Dado que se accede a la funcionalidad",
        "Cuando se ejecuta la accion",
        "Entonces se verifica el resultado",
    )
    DEDUPE_STOPWORDS: ClassVar[set[str]] = {
        "dado", "que", "cuando", "entonces", "y", "el", "la", "los", "las",
        "un", "una", "de", "del", "en", "se", "por", "para", "con", "sin",
        "al", "a", "su", "sus", "es", "son", "tiene", "usuario",
    }
    GENERIC_DEDUPE_STEPS: ClassVar[set[str]] = {
        "se carga la pestana 'otros archivos'",
        "se visualiza la tabla de archivos complementarios",
        "visualiza la tabla de archivos complementarios",
    }

    @classmethod
    def source_tag(cls, source: str) -> str:
        return cls.SOURCE_TAGS.get(source.lower(), "validation")

    @classmethod
    def fallback_steps(cls) -> list[str]:
        return list(cls.FALLBACK_STEPS)

    @classmethod
    def strip_step_keyword(cls, text: str) -> str:
        return cls.STEP_KEYWORD_PATTERN.sub("", text.strip()).strip()

    @classmethod
    def is_step_line(cls, text: str) -> bool:
        return text.strip().lower().startswith(cls.STEP_PREFIXES)

    @classmethod
    def normalize_step(cls, step: str) -> str:
        text = cls.strip_step_keyword(step).strip(" .,;:")
        text = text.replace('"', "'")
        return cls.fold_accents(cls.normalize_spaces(text)).lower()

    @classmethod
    def normalize_scenario_name(cls, name: str) -> str:
        text = cls.strip_step_keyword(name)
        for keyword in ("Dado que", "Cuando", "Entonces", "Y ", "Given", "When", "Then", "And"):
            idx = text.find(keyword)
            if idx > 0:
                text = text[:idx].strip()
        text = cls.normalize_spaces(text).strip(" .")
        return text if len(text) >= 3 else "Escenario"

    @classmethod
    def extract_steps(
        cls,
        content: str,
        min_length: int = 1,
        max_length: int | None = None,
    ) -> list[str]:
        steps = []
        for raw_line in content.splitlines():
            line = cls.normalize_spaces(raw_line)
            if len(line) < min_length or not cls.is_step_line(line):
                continue
            if max_length and len(line) > max_length:
                line = line[:max_length] + "..."
            steps.append(line)
        return steps

    @classmethod
    def scenario_tokens(cls, name: str, steps: list[str]) -> Counter[str]:
        text = cls.fold_accents(" ".join([name, *steps])).lower()
        words = re.findall(r"[a-zA-Z0-9]+", text)
        return Counter(word for word in words if len(word) > 2 and word not in cls.DEDUPE_STOPWORDS)

    @classmethod
    def core_step_for_dedupe(cls, step: str) -> str:
        normalized = cls.normalize_step(step)
        if normalized in cls.GENERIC_DEDUPE_STEPS:
            return ""
        return normalized if len(normalized) >= 18 else ""

    @staticmethod
    def fold_accents(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        return "".join(char for char in normalized if not unicodedata.combining(char))

    @staticmethod
    def normalize_spaces(text: str) -> str:
        return re.sub(r"\s+", " ", text.strip())
