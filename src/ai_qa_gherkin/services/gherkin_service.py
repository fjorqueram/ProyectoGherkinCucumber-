from __future__ import annotations
import re
import os
from datetime import datetime
from typing import Any
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models import GeneratedFeature

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
        """
        Genera Feature Gherkin desde análisis.
        
        En producción, aquí se integraría una llamada a LLM (OpenAI/Claude).
        Por ahora, genera estructura básica automáticamente.
        """
        log.info(f"Generating Gherkin for {analysis_result.get('issue_key')}")

        issue_key = analysis_result.get("issue_key", "UNKNOWN")
        scope = analysis_result.get("scope_summary", "Feature")
        business_rules = analysis_result.get("business_rules", [])
        error_scenarios = analysis_result.get("raw", {}).get("error_scenarios", [])

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

        # Happy Path
        happy_scenario = GherkinScenario(
            name="Flujo exitoso de la funcionalidad",
            given=[
                "que el usuario está autenticado",
                "que existe la información requerida",
            ],
            when=[
                "el usuario ejecuta la acción",
                "el sistema procesa la solicitud",
            ],
            then=[
                "se obtiene el resultado esperado",
                "se registra la acción en logs",
            ],
            tags=["smoke"],
            language="es",  # ← agregar
        )
        feature.add_scenario(happy_scenario)

        # Escenario de validación
        if business_rules:
            validation_scenario = GherkinScenario(
                name="Validación de entrada",
                given=["que el usuario intenta ingresar datos inválidos"],
                when=["el usuario envía la solicitud"],
                then=[
                    "el sistema rechaza la entrada",
                    "se muestra mensaje de error descriptivo",
                ],
                tags=["validation"],
                language="es",  # ← agregar
            )
            feature.add_scenario(validation_scenario)

        # Escenario de error
        if error_scenarios:
            error_scenario = GherkinScenario(
                name="Manejo de errores",
                given=["que ocurre un error en el sistema"],
                when=["el usuario intenta la acción nuevamente"],
                then=[
                    "se muestra mensaje de error amigable",
                    "se permite reintentar la acción",
                ],
                tags=["error-handling"],
                language="es",  # ← agregar
            )
            feature.add_scenario(error_scenario)

        # Generar texto Gherkin
        gherkin_text = feature.to_gherkin()

        # Crear GeneratedFeature
        generated = GeneratedFeature(
            feature_name=scope,
            gherkin_text=gherkin_text,
            language="es",
            tags=["smoke", "regression"],
            scenarios_count=len(feature.scenarios),
            source_issue_key=issue_key,
        )

        log.info(f"Generated {len(feature.scenarios)} scenarios for {issue_key}")

        return generated
        
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
            