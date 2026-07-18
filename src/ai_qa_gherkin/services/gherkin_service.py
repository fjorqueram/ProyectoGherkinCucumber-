from __future__ import annotations
import re
import os
from datetime import datetime
from typing import Any
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models.domain import GeneratedFeature
from ai_qa_gherkin.utils.text_cleaner import TextCleaner

log = get_logger("gherkin_service")

class GherkinScenario:
    """Representa un escenario Gherkin individual."""

    def __init__(self, name: str, given: list[str], when: list[str], then: list[str], tags: list[str] | None = None, language: str = "es",) -> None:
        self.name = name
        self.given = given
        self.when = when
        self.then = then
        self.tags = tags or []
        self.language = language

    def to_gherkin(self, indent: int = 4) -> str:
        """Genera texto Gherkin del escenario."""
        spacing = " " * indent
        result = ""

        # Tags
        if self.tags:
            result += f"{spacing}@" + " @".join(self.tags) + "\n"

        # Nombre
        scenario_kw = "Escenario:" if self.language == "es" else "Scenario:"
        result += f"{spacing}{scenario_kw} {self.name}\n"

        # Palabras clave según idioma
        if self.language == "es":
            given_kw, and_kw = "Dado", "Y"
            when_kw = "Cuando"
            then_kw = "Entonces"
        else:
            given_kw, and_kw = "Given", "And"
            when_kw = "When"
            then_kw = "Then"

        # Given
        for i, step in enumerate(self.given):
            keyword = given_kw if i == 0 else and_kw
            result += f"{spacing * 2}{keyword} {step}\n"

        # When
        for i, step in enumerate(self.when):
            keyword = when_kw if i == 0 else and_kw
            result += f"{spacing * 2}{keyword} {step}\n"

        # Then
        for i, step in enumerate(self.then):
            keyword = then_kw if i == 0 else and_kw
            result += f"{spacing * 2}{keyword} {step}\n"

        return result.strip()  # Eliminar espacios en blanco al final
    
class GherkinFeature:
    """Representa un Feature Gherkin completo."""

    def __init__(self, feature_name: str, description: str = "", language: str = "es", tags: list[str] | None = None,) -> None:
        self.feature_name = feature_name
        self.description = description
        self.language = language
        self.tags = tags or []
        self.scenarios: list[GherkinScenario] = []
        self.background_steps: dict[str, list[str]] = {"given": [], "when": [], "then": []}

    def add_scenario(self, scenario: GherkinScenario) -> None:
        """Agrega un escenario al feature."""
        self.scenarios.append(scenario)

    def set_background(self, given: list[str] | None = None, when: list[str] | None = None, then: list[str] | None = None) -> None:
        """Establece pasos de Background para el feature."""
        if given:
            self.background_steps["given"] = given
        if when:
            self.background_steps["when"] = when
        if then:
            self.background_steps["then"] = then

    def to_gherkin(self) -> str:
        """Genera texto Gherkin completo del feature."""
        result = ""

        # Header de lenguaje
        if self.language == "es":
            result += "# language: es\n"
        elif self.language == "en":
            result += "# language: en\n"

        result += "\n"

        # Tags del Feature
        if self.tags:
            result += "@" + " @".join(self.tags) + "\n"
            
        # Feature
        result += f"Característica: {self.feature_name}\n"

        # Descripción
        if self.description:
            result += f"  {self.description}\n"

        result += "\n"

        # Background
        if any(self.background_steps.values()):
            result += "  Antecedentes:\n"
            for step in self.background_steps["given"]:
                result += f"    Dado {step}\n"
            for step in self.background_steps["when"]:
                result += f"    Cuando {step}\n"
            for step in self.background_steps["then"]:
                result += f"    Entonces {step}\n"
            result += "\n"

        # Scenarios
        for scenario in self.scenarios:
            # Pasar language al scenario
            scenario.language = self.language
            result += scenario.to_gherkin()
            result += "\n"

        return result.strip()  # Eliminar espacios en blanco al final
        
class GherkinService:
    """
    Servicio que genera Gherkin desde análisis de negocio.
    Usa templates y prompts versionados para garantizar consistencia.
    """

    def __init__(self, output_dir: str = "output/features") -> None:
        self.output_dir = output_dir
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Carga el template de prompt desde archivo."""
        # En producción, cargar desde prompts/gherkin_prompt.txt
        # Por ahora, retorna template hardcoded
        return """Genera escenarios Gherkin en español basado en:

REGLAS DE NEGOCIO:
{business_rules}

PRECONDICIONES:
{preconditions}

CAMINOS FELICES:
{happy_paths}

ERRORES Y VALIDACIONES:
{error_scenarios}

REQUISITOS GHERKIN:
1. Lenguaje: Español
2. Formato: Given-When-Then
3. Máximo 10 pasos por escenario
4. Nombres descriptivos sin detalles técnicos
5. Cubrir happy path + errores principales
6. Incluir tags @smoke, @regression según corresponda

SALIDA ESPERADA:
Devuelve solo escenarios en formato Gherkin, sin explicaciones."""

    def generate_from_analysis(self, analysis_result: dict[str, Any]) -> GeneratedFeature:
        """Genera Feature Gherkin desde análisis."""
        log.info(f"Generating Gherkin for {analysis_result.get('issue_key')}")

        # Limpiar todos los datos
        scope = TextCleaner.clean(analysis_result.get("scope_summary", "Feature"))

        issue_key = analysis_result.get("issue_key", "UNKNOWN")
        scope = analysis_result.get("scope_summary", "Feature")
        raw_data = analysis_result.get("raw", {})
        
        # Extraer datos reales
        happy_paths = raw_data.get("happy_paths", [])
        error_scenarios = raw_data.get("error_scenarios", [])
        business_rules = analysis_result.get("business_rules", [])

        # Construir feature
        feature = GherkinFeature(
            feature_name=scope,
            description=f"Feature relacionada a {issue_key}",
            language="es",
            tags=["smoke", "regression"],
        )

        # Agregar Background (precondiciones comunes)
        feature.set_background(
            given=[
                "que el sistema está disponible",
                "que tengo credenciales válidas",
            ]
        )

        # **NUEVO: Generar escenarios desde happy_paths extraídos**
        scenario_count = 0
        for i, hp in enumerate(happy_paths):
            if isinstance(hp, dict):
                name = hp.get("name", f"Escenario {i+1}").strip()
                steps = hp.get("steps", [])
                
                # Limpiar nombre: remover caracteres rotos y truncar
                name = name.split("Dado")[0].strip()  # Cortar donde empieza "Dado"
                name = ''.join(c for c in name if ord(c) >= 32 or c in '\n\t')  # Remover caracteres inválidos
                name = name[:80].strip()
                
                # Dividir steps en Given/When/Then
                given_steps, when_steps, then_steps = self._split_gherkin_steps(steps)
                
                if given_steps or when_steps or then_steps:
                    scenario = GherkinScenario(
                        name=name,
                        given=given_steps or ["que el sistema está preparado"],
                        when=when_steps or ["se ejecuta la acción"],
                        then=then_steps or ["se obtiene el resultado esperado"],
                        tags=["smoke"] if i == 0 else ["validation"],
                        language="es",
                    )
                    feature.add_scenario(scenario)
                    scenario_count += 1

        # **Generar escenarios de error desde error_scenarios**
        for i, es in enumerate(error_scenarios):
            if isinstance(es, dict):
                name = es.get("error_type", f"Validación {i+1}")
                description = es.get("description", "")
                expected = es.get("expected_outcome", "")
                
                if description or expected:
                    error_scenario = GherkinScenario(
                        name=f"Error: {name}",
                        given=[f"que {description[:80]}"],
                        when=["se intenta procesar la solicitud"],
                        then=[f"{expected[:100]}"],
                        tags=["validation"],
                        language="es",
                    )
                    feature.add_scenario(error_scenario)
                    scenario_count += 1

        # Fallback: Si no hay escenarios, crear uno genérico
        if scenario_count == 0:
            default_scenario = GherkinScenario(
                name="Flujo principal",
                given=["que el usuario está autenticado"],
                when=["ejecuta la funcionalidad"],
                then=["se obtiene el resultado esperado"],
                tags=["smoke"],
                language="es",
            )
            feature.add_scenario(default_scenario)

        # Generar texto Gherkin
        gherkin_text = feature.to_gherkin()
        
        log.info(f"Generated {scenario_count} scenarios for {issue_key}")

        return GeneratedFeature(
            feature_name=scope,
            gherkin_text=gherkin_text,
            language="es",
            tags=["smoke", "regression"],
            scenarios_count=scenario_count,
            source_issue_key=issue_key,
        )

    def _split_gherkin_steps(self, steps: list[str]) -> tuple[list[str], list[str], list[str]]:
        """Divide steps en Given/When/Then basado en keywords."""
        given, when, then = [], [], []
        
        for step in steps:
            # Limpiar automáticamente
            step = TextCleaner.clean(step)
            step_lower = step.lower()
            
            # Clasificar step
            if any(kw in step_lower for kw in ["dado", "given"]):
                step_cleaned = step.lstrip("Dado ").lstrip("Given ").strip()
                if step_cleaned and len(step_cleaned) > 3:
                    given.append(step_cleaned)
            elif any(kw in step_lower for kw in ["cuando", "when"]):
                step_cleaned = step.lstrip("Cuando ").lstrip("When ").strip()
                if step_cleaned and len(step_cleaned) > 3:
                    when.append(step_cleaned)
            elif any(kw in step_lower for kw in ["entonces", "then"]):
                step_cleaned = step.lstrip("Entonces ").lstrip("Then ").strip()
                if step_cleaned and len(step_cleaned) > 3:
                    then.append(step_cleaned)
        
        return given, when, then

    def validate_gherkin(self, gherkin_text: str) -> tuple[bool, list[str]]:
        """
        Valida sintaxis básica de Gherkin.
        Retorna (es_válido, lista_de_errores).
        """
        errors = []

        lines = gherkin_text.split("\n")
        in_feature = False
        in_scenario = False
        indent_level = 0

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                continue  # Ignorar comentarios y líneas vacías
            
            # Detectar Feature
            if stripped.startswith("Característica:") or stripped.startswith("Feature:"):
                in_feature = True
                in_scenario = False
                continue
            
            # Detectar Scenario
            if stripped.startswith("Escenario:") or stripped.startswith("Scenario:"):
                if not in_feature:
                    errors.append(f"Línea {line_num}: Escenario sin Feature")
                in_scenario = True
                continue

            # Validar palabras clave
            valid_keywords = [
                "Dado", "Given",
                "Cuando", "When",
                "Entonces", "Then",
                "Y", "And",
                "Pero", "But",
                "Antecedentes", "Background",
            ]

            if in_scenario and stripped and not any(stripped.startswith(kw) for kw in valid_keywords):
                errors.append(f"Línea {line_num}: Paso sin palabra clave válida")

        if not in_feature:
            errors.append("No se encontró definición de Feature")

        return (len(errors) == 0, errors)
    
    def save_feature_file(self, generated_feature: GeneratedFeature, output_dir: str | None = None) -> str:
        """
        Guarda el Feature en archivo.
        Retorna la ruta del archivo creado.
        """

        output_dir = output_dir or self.output_dir
        os.makedirs(output_dir, exist_ok=True)

        filename = f"{generated_feature.source_issue_key}.feature"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(generated_feature.gherkin_text)

        log.info(f"Feature saved to {filepath}")
        return filepath
    
    def get_prompt_for_llm(self, analysis_result: dict[str, Any]) -> str:
        """
        Construye el prompt para enviar a LLM.
        Útil para integración con APIs de IA.
        """
        business_rules = "\n".join(f"- {rule}" for rule in analysis_result.get("business_rules", []))
        preconditions = analysis_result.get("raw", {}).get("preconditions", [])
        precond_text = "\n".join(f"- {p.get('precondition', '')}" for p in preconditions)
        happy_paths = analysis_result.get("raw", {}).get("happy_paths", [])
        happy_text = "\n".join(f"- {h.get('name', '')}" for h in happy_paths)
        error_scenarios = analysis_result.get("raw", {}).get("error_scenarios", [])
        error_text = "\n".join(f"- {e.get('description', '')}" for e in error_scenarios)

        return self.prompt_template.format(
            business_rules=business_rules or "N/A",
            preconditions=precond_text or "N/A",
            happy_paths=happy_text or "N/A",
            error_scenarios=error_text or "N/A",
        )
            