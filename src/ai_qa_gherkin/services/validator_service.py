from __future__ import annotations
import re
from enum import Enum
from typing import Any
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models import ValidationResult

log = get_logger("validator_service")

class SeverityLevel(Enum):
    """Niveles de severidad para validaciones."""
    CRITICAL = "critical"   # Bloquea publicación
    ERROR = "error"         # Bloquea publicación
    WARNING = "warning"     # Advertencia, pero permite publicar
    INFO = "info"           # Información, no bloquea

class ValidationRule:
    """Regla de validación individual."""

    def __init__(self, rule_id: str, name: str, severity: SeverityLevel, description: str) -> None:
        self.rule_id = rule_id
        self.name = name
        self.severity = severity
        self.description = description

    def to_dict(self) -> dict[str, Any]:
        """Convierte la regla de validación a un diccionario."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "severity": self.severity.value,
            "description": self.description
        }
    
class ValidationError:
    """Error de validación encontrado."""

    def __init__(self, rule: ValidationRule, message: str = "", line_number: int | None = None, suggestion: str = "",) -> None:
        self.rule = rule
        self.message = message
        self.line_number = line_number
        self.suggestion = suggestion

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule.rule_id,
            "severity": self.rule.severity.value,
            "line": self.line_number,
            "message": self.message,
            "suggestion": self.suggestion,
        }
    
class GherkinValidator:
    """
    Validador que aplica reglas de calidad Gherkin.
    Valida tanto estructura como semántica.
    """
    
    def __init__(self) -> None:
        self.errors: list[ValidationError] = []
        self.rules = self._initialize_rules()
        self.scenario_keywords = ("Escenario:", "Scenario:")
        self.outline_keywords = ("Escenario Esquema:", "Esquema del escenario:", "Scenario Outline:")
        self.examples_keywords = ("Examples:", "Ejemplos:")

    def _initialize_rules(self) -> dict[str, ValidationRule]:
        """Inicializa todas las reglas de validación."""
        return {
            "feature_required": ValidationRule(
                rule_id="FEATURE_REQUIRED",
                name="Feature obligatorio",
                severity=SeverityLevel.CRITICAL,
                description="Cada archivo debe tener exactamente 1 Feature",
            ),
            "scenario_required": ValidationRule(
                rule_id="SCENARIO_REQUIRED",
                name="Al menos 1 Scenario",
                severity=SeverityLevel.CRITICAL,
                description="Feature debe tener al menos 1 Scenario",
            ),
            "when_then_required": ValidationRule(
                rule_id="WHEN_THEN_REQUIRED",
                name="When + Then obligatorio",
                severity=SeverityLevel.CRITICAL,
                description="Scenario debe tener When y Then",
            ),
            "ambiguous_step": ValidationRule(
                rule_id="AMBIGUOUS_STEP",
                name="Paso ambiguo",
                severity=SeverityLevel.ERROR,
                description="Paso no debe ser ambiguo o demasiado genérico",
            ),
            "unclear_name": ValidationRule(
                rule_id="UNCLEAR_NAME",
                name="Nombre poco claro",
                severity=SeverityLevel.WARNING,
                description="Nombre debe ser descriptivo y comprensible",
            ),
            "missing_examples": ValidationRule(
                rule_id="MISSING_EXAMPLES",
                name="Outline sin Examples",
                severity=SeverityLevel.ERROR,
                description="Scenario Outline debe tener bloque Examples",
            ),
            "duplicate_scenario": ValidationRule(
                rule_id="DUPLICATE_SCENARIO",
                name="Escenario duplicado",
                severity=SeverityLevel.WARNING,
                description="No debería haber escenarios duplicados",
            ),
            "incomplete_coverage": ValidationRule(
                rule_id="INCOMPLETE_COVERAGE",
                name="Cobertura incompleta",
                severity=SeverityLevel.WARNING,
                description="No cubre todas las AC",
            ),
            "invalid_syntax": ValidationRule(
                rule_id="INVALID_SYNTAX",
                name="Sintaxis inválida",
                severity=SeverityLevel.CRITICAL,
                description="Gherkin tiene errores de sintaxis",
            ),
        }
    
    def validate(self, gherkin_text: str, acceptance_criteria: list[str] | None = None) -> ValidationResult:
        """
        Valida Feature Gherkin completo.
        Retorna ValidationResult con detalle de errores.
        """
        log.info("Starting Gherkin validation")

        self.errors = []
        acceptance_criteria = acceptance_criteria or []

        # Validaciones estructurales
        self._validate_structure(gherkin_text)

        # Validaciones semánticas
        if not self.errors:  # Solo si estructura es válida
            self._validate_semantics(gherkin_text)
            self._validate_coverage(gherkin_text, acceptance_criteria)

        # Determinar si es válido
        blocking_errors = [
            e for e in self.errors
            if e.rule.severity in [SeverityLevel.CRITICAL, SeverityLevel.ERROR]
        ]

        is_valid = len(blocking_errors) == 0
        confidence = self._calculate_confidence(is_valid, blocking_errors)

        log.info(
            f"Validation complete: {len(self.errors)} errors, "
            f"valid={is_valid}, confidence={confidence:.2f}"
        )

        return ValidationResult(
            is_valid=is_valid,
            errors=[e.to_dict() for e in self.errors],
            warnings=[e.to_dict() for e in self.errors if e.rule.severity == SeverityLevel.WARNING],
            confidence=confidence,
            raw={
                "total_errors": len(self.errors),
                "critical_errors": len([e for e in self.errors if e.rule.severity == SeverityLevel.CRITICAL]),
                "blocking_errors": len(blocking_errors),
            },
        )

    def _validate_structure(self, gherkin_text: str) -> None:
        """Valida estructura básica de Gherkin."""
        log.debug("Validating structure")

        lines = gherkin_text.split("\n")

        # Buscar Feature
        feature_count = 0
        feature_line = None
        scenario_count = 0
        outline_count = 0

        for line_num, line in enumerate(lines, 1):
            stripped = line.lstrip()

            if stripped.startswith("Característica:") or stripped.startswith("Feature:"):
                feature_count += 1
                feature_line = line_num
            elif stripped.startswith(self.scenario_keywords):
                scenario_count += 1
            elif stripped.startswith(self.outline_keywords):
                outline_count += 1
                # Validar que Outline tenga Examples
                self._validate_outline_has_examples(lines, line_num) 

        # Validar Feature
        if feature_count == 0:
            error = ValidationError(
                rule=self.rules["feature_required"],
                message="No se encontró Feature en el archivo",
                suggestion="Agregue 'Característica: <nombre>' al inicio",
            )
            self.errors.append(error)
        elif feature_count > 1:
            error = ValidationError(
                rule=self.rules["feature_required"],
                line_number=feature_line,
                message=f"Se encontraron {feature_count} Features (máximo 1)",
                suggestion="Mantenga solo 1 Feature por archivo",
            )
            self.errors.append(error)

        # Validar Scenarios
        total_scenarios = scenario_count + outline_count
        if total_scenarios == 0:
            error = ValidationError(
                rule=self.rules["scenario_required"],
                message="No se encontraron Scenarios",
                suggestion="Agregue al menos 1 'Escenario:' o 'Escenario Esquema:'",
            )
            self.errors.append(error)

        # Validar When + Then en cada Scenario
        self._validate_when_then(lines)
    
    def _validate_outline_has_examples(self, lines: list[str], outline_line: int) -> None:
        """Valida que Scenario Outline tenga bloque Examples."""
        has_examples = False

        for line in lines[outline_line:]:
            stripped = line.lstrip()
            if stripped.startswith(self.examples_keywords):
                has_examples = True
                break
            elif stripped.startswith(self.scenario_keywords + self.outline_keywords):
                break

        if not has_examples:
            error = ValidationError(
                rule=self.rules["missing_examples"],
                line_number=outline_line,
                message="Scenario Outline sin bloque Examples",
                suggestion="Agregue bloque 'Ejemplos:' con datos de prueba",
            )
            self.errors.append(error)

    def _validate_when_then(self, lines: list[str]) -> None:
        """Valida que cada Scenario tenga al menos un When y un Then."""
        in_scenario = False
        scenario_line = None
        has_when = False
        has_then = False

        for line_num, line in enumerate(lines, 1):
            stripped = line.lstrip()

            if not stripped or stripped.startswith("#"):
                continue

            # Detectar inicio Scenario
            if stripped.startswith(self.scenario_keywords + self.outline_keywords):
                # Validar scenario anterior
                if in_scenario and (not has_when or not has_then):
                    error = ValidationError(
                        rule=self.rules["when_then_required"],
                        line_number=scenario_line,
                        message="Scenario sin When y/o Then",
                        suggestion="Agregue 'Cuando' y 'Entonces' (o equivalentes)",
                    )
                    self.errors.append(error)

                # Iniciar nuevo scenario
                in_scenario = True
                scenario_line = line_num
                has_when = False
                has_then = False

            elif in_scenario:
                if stripped.startswith(("Cuando", "When")):
                    has_when = True
                elif stripped.startswith(("Entonces", "Then")):
                    has_then = True

        # Validar último scenario
        if in_scenario and (not has_when or not has_then):
            error = ValidationError(
                rule=self.rules["when_then_required"],
                line_number=scenario_line,
                message="Scenario sin When y/o Then",
                suggestion="Agregue 'Cuando' y 'Entonces'",
            )
            self.errors.append(error)
        
    def _validate_semantics(self, gherkin_text: str) -> None:
        """Valida semántica y claridad de pasos."""
        log.debug("Validating semantics")

        lines = gherkin_text.split("\n")
        ambiguous_patterns = [
            r"^(Dado|Given|Cuando|When|Entonces|Then)\s+(test|algo|data|info|stuff|cosas)$",
            r"^(Dado|Given|Cuando|When|Entonces|Then)\s+\d+$",  # Solo números
            r"^(Dado|Given|Cuando|When|Entonces|Then)\s+[a-z]{1,3}$",  # Muy corto
        ]

        seen_steps = set()
        duplicate_steps_found = set()

        for line_num, line in enumerate(lines, 1):
            stripped = line.lstrip()

            if not stripped or stripped.startswith("#"):
                continue

            # Detectar pasos (Given, When, Then, And, But)
            if any(stripped.startswith(kw) for kw in ["Dado", "Given", "Cuando", "When", "Entonces", "Then", "Y", "And", "Pero", "But"]):
                # Buscar patrones ambiguos
                for pattern in ambiguous_patterns:
                    if re.match(pattern, stripped, re.IGNORECASE):
                        error = ValidationError(
                            rule=self.rules["ambiguous_step"],
                            line_number=line_num,
                            message=f"Paso ambiguo o poco específico: '{stripped}'",
                            suggestion="Use lenguaje claro y descriptivo",
                        )
                        self.errors.append(error)
                
                # Detectar pasos duplicados
                # Extraer solo el texto del paso, sin la palabra clave
                step_text = re.sub(r"^(Dado|Given|Cuando|When|Entonces|Then|Y|And|Pero|But)\s+", "", stripped, flags=re.IGNORECASE).strip()
                step_normalized = step_text.lower()
                
                if step_normalized in seen_steps:
                    if step_normalized not in duplicate_steps_found:
                        error = ValidationError(
                            rule=self.rules["duplicate_scenario"],
                            line_number=line_num,
                            message=f"Paso duplicado detectado: '{step_text}'",
                            suggestion="Elimine o refactorice pasos duplicados",
                        )
                        self.errors.append(error)
                        duplicate_steps_found.add(step_normalized)
                else:
                    seen_steps.add(step_normalized)
            
            # Validar nombres de Scenario
            if stripped.startswith(self.scenario_keywords + self.outline_keywords):
                name = stripped.split(":", 1)[1].strip()
                if len(name) < 5 or len(name) > 100:
                    error = ValidationError(
                        rule=self.rules["unclear_name"],
                        line_number=line_num,
                        message=f"Nombre de Scenario poco descriptivo: '{name}'",
                        suggestion="Use nombres entre 5 y 100 caracteres, descriptivos",
                    )
                    self.errors.append(error)

    def _validate_coverage(self, gherkin_text: str, acceptance_criteria: list[str]) -> None:
        """Valida cobertura de AC en Gherkin."""
        log.debug("Validating AC coverage")

        if not acceptance_criteria:
            log.info("No acceptance criteria provided, skipping coverage validation")
            return
        
        # Palabras clave de AC que deberían aparecer en Gherkin
        covered_ac = []
        text_lower = gherkin_text.lower()

        for ac in acceptance_criteria:
            ac_lower = ac.lower()
            # Extraer palabras clave (primeras 3-5)
            words = ac_lower.split()[:3]
            if any(word in text_lower for word in words):
                covered_ac.append(ac)

        coverage_ratio = len(covered_ac) / len(acceptance_criteria) if acceptance_criteria else 1.0

        if coverage_ratio < 0.8: # Menos del 80%
            error = ValidationError(
                rule=self.rules["incomplete_coverage"],
                message=f"Cobertura de AC: {coverage_ratio:.0%} (mínimo 80%)",
                suggestion=f"Agregue Scenarios para cubrir más AC",
            )
            self.errors.append(error)

    def _calculate_confidence(self, is_valid: bool, blocking_errors: list[ValidationError]) -> float:
        """Calcula confianza en la validación."""
        if is_valid:
            # Base 0.9 si es válido
            warning_count = len([e for e in self.errors if e.rule.severity == SeverityLevel.WARNING])
            confidence = max(0.5, 0.95 - (warning_count * 0.05))  # Reduce confianza por cada warning
        else:
            # Base 0.2 si es inválido
            confidence = max(0.1, 0.2 - (len(blocking_errors) * 0.1))  # Reduce confianza por cada error crítico o error

        return round(min(confidence, 1.0), 2)  # Limitar a 1.0 máximo
    
    def get_summary(self) -> str:
        """Resumen textual de validación."""
        total = len(self.errors)
        critical = len([e for e in self.errors if e.rule.severity == SeverityLevel.CRITICAL])
        errors = len([e for e in self.errors if e.rule.severity == SeverityLevel.ERROR])
        warnings = len([e for e in self.errors if e.rule.severity == SeverityLevel.WARNING])

        return (
            f"Validation Summary:\n"
            f"  Total issues: {total}\n"
            f"  Critical: {critical}\n"
            f"  Errors: {errors}\n"
            f"  Warnings: {warnings}\n"
            f"  Status: {'✅ VALID' if critical + errors == 0 else '❌ INVALID'}"
        )
