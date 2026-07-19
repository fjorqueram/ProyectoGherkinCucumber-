"""Utilidades para limpiar y normalizar texto antes de generar Gherkin."""
from __future__ import annotations
import re
import unicodedata
from ftfy import fix_text

class TextCleaner:
    """Limpia texto corrupto sin aprender correcciones semánticas."""

    @classmethod
    def clean(cls, text: str, auto_learn: bool = False) -> str:
        """
        Repara mojibake/Unicode con ftfy y normaliza espacios sin romper Gherkin.

        ``auto_learn`` queda como argumento compatible con llamadas existentes,
        pero no se usa: para escenarios .feature evitamos aprender cambios de palabras.
        """
        if not text:
            return text

        cleaned = fix_text(str(text), normalization="NFC")
        cleaned = unicodedata.normalize("NFC", cleaned)
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        lines = []
        for line in cleaned.split("\n"):
            indent_match = re.match(r"^[ \t]*", line)
            indent = indent_match.group(0).replace("\t", "    ") if indent_match else ""
            content = line[len(indent_match.group(0)):] if indent_match else line

            content = content.translate(
                str.maketrans({
                    "\u00a0": " ",
                    "\u200b": "",
                    "\ufeff": "",
                })
            )
            content = re.sub(r"[ \t\f\v]+", " ", content)
            content = re.sub(r"\s+([,.;:!?])", r"\1", content)
            content = re.sub(r"([¿¡])\s+", r"\1", content)
            lines.append((indent + content).rstrip())

        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        return cleaned.strip()
