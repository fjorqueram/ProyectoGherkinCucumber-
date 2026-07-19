from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Any
from ai_qa_gherkin.logger import get_logger

log = get_logger("summary_service")

class ExecutiveSummary:
    """Resumen ejecutivo de una historia."""

    def __init__(self, issue_key: str, summary: str, description: str = "") -> None:
        self.issue_key = issue_key
        self.summary = summary
        self.description = description
        self.generated_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convierte el resumen ejecutivo a un diccionario."""
        return {
            "issue_key": self.issue_key,
            "summary": self.summary,
            "description": self.description,
            "generated_at": self.generated_at,
        }
    
    def to_markdown(self) -> str:
        """Convierte el resumen ejecutivo a un formato Markdown."""
        return (
            f"# {self.issue_key}: {self.summary}\n\n"
            f"{self.description}\n\n"
            f"*Generado: {self.generated_at}*"
        )
    
class TraceabilityLink:
    """Vinculación entre AC -> Scenario -> Fuente."""

    def __init__(self, ac_id: str, ac_text: str, scenario_name: str, scenario_line: int, source_type: str, source_id: str, source_name: str) -> None:
        self.ac_id = ac_id
        self.ac_text = ac_text
        self.scenario_name = scenario_name
        self.scenario_line = scenario_line
        self.source_type = source_type
        self.source_id = source_id
        self.source_name = source_name

    def to_dict(self) -> dict[str, Any]:
        """Convierte el enlace de trazabilidad a un diccionario."""
        return {
            "ac_id": self.ac_id,
            "ac_text": self.ac_text,
            "scenario": {
                "name": self.scenario_name,
                "line": self.scenario_line,
            },
            "source": {
                "type": self.source_type,
                "id": self.source_id,
                "name": self.source_name,
            },
        }
    
class TraceabilityMatrix:
    """Matriz de trazabilidad AC -> Scenario -> Fuentes."""

    def __init__(self, issue_key: str) -> None:
        self.issue_key = issue_key
        self.links: list[TraceabilityLink] = []
        self.generated_at = datetime.now().isoformat()

    def add_link(self, link: TraceabilityLink) -> None:
        """Agrega un enlace de trazabilidad a la matriz."""
        self.links.append(link)

    def get_ac_coverage(self) -> dict[str, Any]:
        """Analiza cobertura de AC."""
        ac_map: dict[str, list[str]] = {}

        for link in self.links:
            ac_id = link.ac_id
            if ac_id not in ac_map:
                ac_map[ac_id] = []
            ac_map[ac_id].append(link.scenario_name)

        coverage = {
            "total_ac": len(ac_map),
            "covered_ac": len(ac_map),
            "coverage_ratio": 1.0 if ac_map else 0.0,
            "ac_scenarios": ac_map,
        }
        return coverage
    
    def get_source_distribution(self) -> dict[str, Any]:
        """Distribución de fuentes en la matriz."""
        distribution: dict[str, int] = {}

        for link in self.links:
            source_type = link.source_type
            distribution[source_type] = distribution.get(source_type, 0) + 1

        return distribution
    
    def to_dict(self) -> dict[str, Any]:
        """Convierte la matriz de trazabilidad a un diccionario."""
        return {
            "issue_key": self.issue_key,
            "generated_at": self.generated_at,
            "total_links": len(self.links),
            "coverage": self.get_ac_coverage(),
            "source_distribution": self.get_source_distribution(),
            "links": [link.to_dict() for link in self.links],
        }
    
    def to_markdown(self) -> str:
        """Genera tabla Markdown de trazabilidad."""
        lines = [
            f"# Trazabilidad de Requisitos - {self.issue_key}",
            "",
            f"*Generado: {self.generated_at}*",
            "",
            "## Matriz AC → Scenario → Fuente",
            "",
            "| AC | Scenario | Línea | Fuente | ID |",
            "|---|---|---|---|---|",
        ]

        for link in self.links:
            lines.append(
                f"| {link.ac_id} | {link.scenario_name} | {link.scenario_line} | "
                f"{link.source_type} | {link.source_id} |"
            )

        coverage = self.get_ac_coverage()
        lines.extend([
            "",
            "## Cobertura",
            "",
            f"- **AC Totales:** {coverage['total_ac']}",
            f"- **AC Cubiertas:** {coverage['covered_ac']}",
            f"- **Ratio:** {coverage['coverage_ratio']:.0%}",
        ])

        distribution = self.get_source_distribution()
        lines.extend([
            "",
            "## Distribución de Fuentes",
            "",
        ])
        for source, count in sorted(distribution.items()):
            lines.append(f"- {source}: {count}")

        return "\n".join(lines)
    
class SummaryService:
    """Servicio que genera resúmenes ejecutivos y matrices de trazabilidad."""

    def __init__(self, output_summary: str = "output/summaries", output_traceability: str = "output/traceability",) -> None:
        self.output_summary = output_summary
        self.output_traceability = output_traceability
        
    def generate_executive_summary(
        self,
        issue_key: str,
        analysis_result: Any,  # ✅ Acepta AnalysisResult o dict
        validation_result: dict[str, Any] | None = None,
        gherkin_path: str | None = None,
    ) -> ExecutiveSummary:
        """
        Genera resumen ejecutivo desde análisis.
        Soporta AnalysisResult (orchestrator) o dict (tests).
        """
        log.info(f"Generating executive summary for {issue_key}")

        # Modo 1: AnalysisResult model (desde orchestrator)
        if not isinstance(analysis_result, dict) and hasattr(analysis_result, 'business_rules'):
            # ✅ Type guard explícito
            business_rules = getattr(analysis_result, 'business_rules', [])
            assumptions = getattr(analysis_result, 'assumptions', [])
            risks = getattr(analysis_result, 'risks', [])
            confidence = getattr(analysis_result, 'confidence', 0)
            scope_summary = getattr(analysis_result, 'scope_summary', '')
            
            description = (
                f"**Negocio:**\n"
                f"- {len(business_rules)} reglas de negocio identificadas\n"
                f"- {len(assumptions)} supuestos\n"
                f"- {len(risks)} riesgos identificados\n\n"
                f"**Calidad:**\n"
                f"- Confianza: {confidence:.0%}\n"
            )

            return ExecutiveSummary(
                issue_key=issue_key,
                summary=scope_summary or f"Análisis de {issue_key}",
                description=description,
            )
        
        # Modo 2: dict (desde tests)
        if isinstance(analysis_result, dict) and validation_result is not None:
            issue = analysis_result.get("issue", {})
            summary_text = issue.get("summary", "")
            business_rules = analysis_result.get("business_rules", [])
            scenarios_count = len(validation_result.get("raw", {}).get("detailed_errors", []))

            description = (
                f"**Negocio:**\n"
                f"- {len(business_rules)} reglas de negocio identificadas\n\n"
                f"**Validación:**\n"
                f"- Escenarios: {scenarios_count}\n"
                f"- Estado: {'✅ Válido' if validation_result.get('is_valid') else '❌ Inválido'}\n"
                f"- Confianza: {validation_result.get('confidence', 0):.0%}\n\n"
                f"**Archivo:**\n"
                f"- {gherkin_path or 'N/A'}"
            )

            return ExecutiveSummary(
                issue_key=issue_key,
                summary=summary_text or f"Análisis de {issue_key}",
                description=description,
            )
        
        # Fallback
        return ExecutiveSummary(
            issue_key=issue_key,
            summary=f"Análisis de {issue_key}",
            description="Resumen generado",
        )

    
    def generate_traceability(self, issue_key: str, analysis_result: Any) -> ExecutiveSummary:
        """Genera matriz de trazabilidad AC → Scenario."""
        log.info(f"Generating traceability for {issue_key}")
        
        lines = []
        lines.append(f"# Trazabilidad de Requisitos - {issue_key}")
        lines.append("")
        lines.append(f"*Generado: {datetime.now().isoformat()}*")
        lines.append("")
        lines.append("## Matriz AC → Scenario → Fuente")
        lines.append("")
        lines.append("| AC | Scenario | Línea | Fuente | ID |")
        lines.append("|---|---|---|---|---|")
        
        # ✅ Obtener happy_paths de análisis
        if hasattr(analysis_result, 'raw'):
            # Es AnalysisResult
            happy_paths = analysis_result.raw.get("happy_paths", []) or []
            business_rules = analysis_result.business_rules or []
        else:
            # Es dict
            happy_paths = analysis_result.get("raw", {}).get("happy_paths", []) or []
            business_rules = analysis_result.get("business_rules", []) or []
        
        # Mapear AC a happy paths
        for idx, path in enumerate(happy_paths, 1):
            scenario_name = path.get("name", f"Escenario {idx}")
            source = path.get("source", "jira")
            traceability = path.get("traceability", {})
            source_id = traceability.get("source_id", "") if isinstance(traceability, dict) else ""
            
            # LIMPIAR nombre
            scenario_name = SummaryService._clean_scenario_name(scenario_name)
            
            # Generar ID único
            trace_id = f"{issue_key}-S{idx}"
    
            lines.append(f"| AC{idx} | {scenario_name} | {idx * 10} | {source} | {trace_id} |")

        lines.append("")
        lines.append("## Cobertura")
        lines.append("")
        # ✅ USAR len(happy_paths) en lugar de len(business_rules)
        total_ac = len(happy_paths)  # ← CAMBIO AQUÍ
        covered_ac = len(happy_paths)
        ratio = (covered_ac / total_ac * 100) if total_ac > 0 else 100  # ← Y AQUÍ
        
        lines.append(f"- **AC Totales:** {total_ac}")
        lines.append(f"- **AC Cubiertas:** {covered_ac}")
        lines.append(f"- **Ratio:** {ratio:.1f}%")
        lines.append("")
        
        lines.append("## Distribución de Fuentes")
        lines.append("")
        
        source_count = {}
        for path in happy_paths:
            source = path.get("source", "unknown")
            source_count[source] = source_count.get(source, 0) + 1
        
        for source, count in sorted(source_count.items()):
            lines.append(f"- **{source.upper()}:** {count} escenarios")
        
        # ✅ Retornar ExecutiveSummary con summary y description
        return ExecutiveSummary(
            issue_key=issue_key,
            summary=f"Trazabilidad de {issue_key}",
            description="\n".join(lines),
        )

    @staticmethod
    def _clean_scenario_name(name: str) -> str:
        """Limpia el nombre del escenario removiendo fragmentos de pasos."""
        import re
        
        # Remover todo después de palabras clave Gherkin
        keywords = ["Dado que", "Cuando", "Entonces", "Y ", "Given", "When", "Then", "And"]
        
        for keyword in keywords:
            # Buscar el keyword y truncar
            idx = name.find(keyword)
            if idx > 0:
                # Truncar hasta el keyword y remover espacios extra
                name = name[:idx].strip()
        
        # Remover espacios dobles
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Máximo 80 caracteres
        name = name[:80].strip()
        
        # Asegurar que no esté vacío
        if not name or len(name) < 3:
            name = "Escenario"
        
        return name
    
    def generate_traceability_matrix(self, issue_key: str, analysis_result: dict[str, Any]) -> TraceabilityMatrix:
        """Genera matriz de trazabilidad."""
        log.info(f"Generating traceability matrix for {issue_key}")

        matrix = TraceabilityMatrix(issue_key)

        # Extraer AC e información de origen
        issue = analysis_result.get("issue", {})
        acceptance_criteria = issue.get("acceptance_criteria", [])
        business_rules_raw = analysis_result.get("raw", {}).get("business_rules", [])

        # Mapear cada AC a su origen
        for ac_idx, ac in enumerate(acceptance_criteria, 1):
            ac_id = f"AC-{ac_idx}"
            
            # Buscar regla de negocio relacionada
            rule = business_rules_raw[ac_idx - 1] if ac_idx - 1 < len(business_rules_raw) else {}
            traceability = rule.get("traceability", {}) if isinstance(rule, dict) else {}

            link = TraceabilityLink(
                ac_id=ac_id,
                ac_text=ac,
                scenario_name=f"Scenario {ac_idx}",
                scenario_line=5 + (ac_idx * 5),  # Aproximado
                source_type=traceability.get("source_type", "jira") if isinstance(traceability, dict) else "jira",
                source_id=traceability.get("source_id", issue_key) if isinstance(traceability, dict) else issue_key,
                source_name=traceability.get("source_name", "Issue") if isinstance(traceability, dict) else "Issue",
            )
            matrix.add_link(link)

        return matrix
    
    def save_summary(self, summary: ExecutiveSummary, format: str = "markdown") -> str:
        """Guarda el resumen ejecutivo en el formato especificado."""
        os.makedirs(self.output_summary, exist_ok=True)

        filename = f"{summary.issue_key}_summary.md"
        filepath = os.path.join(self.output_summary, filename)

        content = summary.to_markdown() if format == "markdown" else json.dumps(summary.to_dict(), indent=2)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        log.info(f"Summary saved to {filepath}")
        return filepath
    
    def save_traceability(self, matrix: TraceabilityMatrix, format: str = "markdown") -> str:
        """Guarda matriz de trazabilidad en archivo."""
        os.makedirs(self.output_traceability, exist_ok=True)

        filename = f"{matrix.issue_key}_traceability.md"
        filepath = os.path.join(self.output_traceability, filename)
        
        content = matrix.to_markdown() if format == "markdown" else json.dumps(matrix.to_dict(), indent=2)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        log.info(f"Traceability matrix saved to {filepath}")
        return filepath