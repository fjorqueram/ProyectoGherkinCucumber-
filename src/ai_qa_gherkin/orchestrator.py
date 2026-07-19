from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models.domain import AnalysisResult
from ai_qa_gherkin.services.analysis_service import AnalysisService
from ai_qa_gherkin.services.collector_service import ContextCollector
from ai_qa_gherkin.services.gherkin_service import GherkinService
from ai_qa_gherkin.services.summary_service import SummaryService
from ai_qa_gherkin.services.validator_service import GherkinValidator
from ai_qa_gherkin.clients.xray_client import XrayClient
from ai_qa_gherkin.retry import PermanentError, TransientError

log = get_logger("orchestrator")

class PipelineState(str ,Enum):
    """Estados del pipeline."""

    IDLE = "idle"
    COLLECTED = "collected"
    ANALYZED = "analyzed"
    GENERATED = "generated"
    VALIDATED = "validated"
    PUBLISHED = "published"
    FAILED = "failed"

@dataclass
class PipelineResult:
    """Resultado del pipeline."""

    issue_key: str
    state: PipelineState
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Rutas de archivos
    feature_path: str | None = None
    summary_path: str | None = None
    traceability_path: str | None = None
    state_path: str | None = None  # ← AGREGAR

    # Datos del pipeline
    collected_context: dict[str, Any] = field(default_factory=dict)
    analysis_result: AnalysisResult | None = None
    feature_content: str | None = None
    validation_result: dict[str, Any] = field(default_factory=dict)

    # Metadatos del pipeline
    context_hash: str | None = None
    error: str | None = None
    duration_seconds: float = 0.0
    confidence: float = 0.7  # ← AGREGAR
    llm_requested: bool = False
    llm_used: bool = False
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_error: str | None = None
    llm_scenarios_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convierte el resultado del pipeline a un diccionario."""
        return {
            "issue_key": self.issue_key,
            "state": self.state.value,
            "timestamp": self.timestamp,
            "feature_path": self.feature_path,
            "summary_path": self.summary_path,
            "traceability_path": self.traceability_path,
            "state_path": self.state_path,  # ← AGREGAR
            "context_hash": self.context_hash,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "confidence": self.confidence,  # ← AGREGAR
            "llm_requested": self.llm_requested,
            "llm_used": self.llm_used,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_error": self.llm_error,
            "llm_scenarios_count": self.llm_scenarios_count,
            "validation_result": self.validation_result,
        }
    
class Orchestrator:
    """
    Orquestador end-to-end del pipeline.
    
    Flujo:
    1. Collect: Recolecta contexto (Jira + Confluence + Git)
    2. Analyze: Analiza con IA/mock para extraer reglas
    3. Generate: Genera Feature Gherkin
    4. Validate: Valida calidad del Gherkin
    5. Summarize: Crea resumen y trazabilidad
    
    Idempotencia: Por ISSUE_KEY + hash_context
    """

    def __init__(self, output_dir: str = "output", use_llm: bool = False,) -> None:
        self.output_dir = Path(output_dir)
        self.use_llm = use_llm

        # Crear directorios
        self.features_dir = self.output_dir / "features"
        self.summaries_dir = self.output_dir / "summaries"
        self.traceability_dir = self.output_dir / "traceability"
        self.state_dir = self.output_dir / "state"

        for dir_path in [self.features_dir, self.summaries_dir, self.traceability_dir, self.state_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Servicios
        self.collector = ContextCollector()
        self.analyzer = AnalysisService(use_llm=use_llm)
        self.gherkin_service = GherkinService()
        self.validator = GherkinValidator()
        self.summary_generator = SummaryService()

        log.info(f"Orchestrator initialized (use_llm={use_llm}, output_dir={output_dir})")

    def run_pipeline(self, issue_key: str, issue_data: dict[str, Any] | None = None) -> PipelineResult:
        """
        Ejecuta el pipeline completo.
        
        Args:
            issue_key: Clave de Jira (ej: DYF-123)
            
        Returns:
            PipelineResult con estado y rutas de archivos
        """
        start_time = datetime.now()
        result = PipelineResult(issue_key=issue_key, state=PipelineState.IDLE)
        self._apply_llm_metadata(result)

        try:
            log.info(f"Starting pipeline for {issue_key}")

            # 1. COLLECT
            log.info("Step 1: Collecting context...")
            result = self._collect(result, issue_data, None, None)
            if result.state == PipelineState.FAILED:
                return result

            # 2. ANALYZE
            log.info("Step 2: Analyzing context...")
            result = self._analyze(result)
            if result.state == PipelineState.FAILED:
                return result

            # 3. GENERATE
            log.info("Step 3: Generating Gherkin...")
            result = self._generate(result)
            if result.state == PipelineState.FAILED:
                return result

            # 4. VALIDATE
            log.info("Step 4: Validating Gherkin...")
            result = self._validate(result)
            if result.state == PipelineState.FAILED:
                return result

            # 5. SUMMARIZE
            log.info("Step 5: Generating summary and traceability...")
            result = self._summarize(result)
            if result.state == PipelineState.FAILED:
                return result

            # Marcar como publicado
            result.state = PipelineState.PUBLISHED
            log.info(f"Pipeline completed successfully for {issue_key}")

        except Exception as e:
            result.state = PipelineState.FAILED
            result.error = str(e)
            log.error(f"Pipeline failed for {issue_key}: {str(e)}", exc_info=True)

        finally:
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            self._save_state(result)

        return result
    
    def _collect(self, result: PipelineResult, issue_data: dict[str, Any] | None, confluence_data: dict[str, Any] | None, git_data: dict[str, Any] | None,) -> PipelineResult:
        """Paso 1: Recolectar contexto."""
        try:
            log.info(f"Collecting context for {result.issue_key}...")
            
            # ✅ USAR LOS NUEVOS PARÁMETROS DE collector.collect()
            merged_context = self.collector.collect(
                issue_key=result.issue_key,  # ← NUEVO PARÁMETRO
                confluence_search="",
                git_repo=("fjorqueram", "ProyectoGherkinCucumber")  # ← NUEVO PARÁMETRO (configurable)
            )
            
            # Calcular hash para idempotencia
            context_hash = self._calculate_context_hash(merged_context)

            # Verificar si ya fue procesado (idempotencia)
            cached_result = self._load_cached_result(result.issue_key, context_hash)
            if cached_result:
                log.info(f"Found cached result for {result.issue_key}")
                return cached_result
            
            result.collected_context = merged_context
            result.context_hash = context_hash
            result.state = PipelineState.COLLECTED

            log.info(f"Context collected for {result.issue_key} (hash: {context_hash[:8]}...)")
            return result
        
        except Exception as e:
            result.state = PipelineState.FAILED
            result.error = f"Collection failed: {str(e)}"
            log.error(f"Collection error: {str(e)}")
            return result
        
    def _analyze(self, result: PipelineResult) -> PipelineResult:
        """Paso 2: Analizar contexto con IA."""
        try:
            analysis_dict = self.analyzer.analyze(result.collected_context)
            
            # Extraer solo los strings de business_rules
            business_rules = []
            for br in analysis_dict.get("business_rules", []):
                if isinstance(br, dict):
                    business_rules.append(br.get("rule", ""))
                else:
                    business_rules.append(str(br))
            
            # Convertir dict a AnalysisResult
            result.analysis_result = AnalysisResult(
                issue_key=analysis_dict.get("issue_key", result.issue_key),
                scope_summary=analysis_dict.get("scope_summary", ""),
                business_rules=business_rules,
                assumptions=self.analyzer._extract_assumptions(result.collected_context),
                risks=self.analyzer._extract_risks(result.collected_context),
                raw=analysis_dict.get("raw", {}),
                confidence=self.analyzer._calculate_confidence(),
            )
            self._apply_llm_metadata(result)
            
            result.state = PipelineState.ANALYZED

            log.info(
                f"Analysis complete: {len(result.analysis_result.business_rules)} rules, "
                f"confidence: {result.analysis_result.confidence}"
            )
            return result
        
        except Exception as e:
            self._apply_llm_metadata(result)
            result.state = PipelineState.FAILED
            result.error = f"Analysis failed: {str(e)}"
            log.error(f"Analysis error: {str(e)}")
            return result
        
    def _generate(self, result: PipelineResult) -> PipelineResult:
        """Paso 3: Generar Feature Gherkin."""
        try:
            if result.analysis_result is None:
                raise ValueError("No analysis result available for generation.")
            
            # Convertir AnalysisResult a dict para GherkinService
            analysis_dict = {
                "issue_key": result.issue_key,
                "scope_summary": result.analysis_result.scope_summary,
                "business_rules": result.analysis_result.business_rules,
                "raw": {
                    "preconditions": result.analysis_result.raw.get("preconditions", []),
                    "happy_paths": result.analysis_result.raw.get("happy_paths", []),
                    "error_scenarios": result.analysis_result.raw.get("error_scenarios", []),
                },
            }
            
            # Generar feature
            generated_feature = self.gherkin_service.generate_from_analysis(analysis_dict)
            
            feature_content = generated_feature.gherkin_text

            # Guardar archivo .feature
            feature_path = self.features_dir / f"{result.issue_key}.feature"
            feature_path.write_text(feature_content, encoding="utf-8")

            result.feature_content = feature_content
            result.feature_path = str(feature_path)
            result.state = PipelineState.GENERATED

            log.info(f"Feature generated: {feature_path}")
            return result
        
        except Exception as e:
            result.state = PipelineState.FAILED
            result.error = f"Generation failed: {str(e)}"
            log.error(f"Generation error: {str(e)}")
            return result

    def _validate(self, result: PipelineResult) -> PipelineResult:
        """Paso 4: Validar calidad del Gherkin."""
        try:
            if result.feature_content is None:
                raise ValueError("No feature content available for validation.")
            
            # Validar Gherkin
            validation_result = self.validator.validate(result.feature_content)
            
            # Actualizar confianza
            result.confidence = validation_result.confidence  # ← AGREGAR
            
            # Guardar resultado de validación
            result.validation_result = {
                "is_valid": validation_result.is_valid,
                "confidence": validation_result.confidence,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "raw": validation_result.raw,
            }

            # Si hay errores críticos o de error, fallar
            if not validation_result.is_valid:
                result.state = PipelineState.FAILED
                error_count = len(validation_result.errors)
                result.error = f"Validation failed: {error_count} issues found"
                log.error(f"Validation failed: {result.error}")
                return result
            
            result.state = PipelineState.VALIDATED
            warning_count = len(validation_result.warnings)
            log.info(f"Validation passed: {warning_count} warnings")
            return result
        
        except Exception as e:
            result.state = PipelineState.FAILED
            result.error = f"Validation failed: {str(e)}"
            log.error(f"Validation error: {str(e)}")
            return result
        
    def _summarize(self, result: PipelineResult) -> PipelineResult:
        """Paso 5: Generar resumen y trazabilidad."""
        try:
            if result.analysis_result is None:
                raise ValueError("No analysis result available")

            # Generar summary
            summary = self.summary_generator.generate_executive_summary(
                issue_key=result.issue_key,
                analysis_result=result.analysis_result,
                validation_result=result.validation_result,
                gherkin_path=result.feature_path,
            )

            # Guardar summary
            summary_path = self.summaries_dir / f"{result.issue_key}_summary.md"
            summary_path.write_text(summary.to_markdown(), encoding="utf-8")
            result.summary_path = str(summary_path)

            # Generar trazabilidad
            traceability = self.summary_generator.generate_traceability(
                issue_key=result.issue_key,
                analysis_result=result.analysis_result,
            )

            # Guardar trazabilidad
            traceability_path = self.traceability_dir / f"{result.issue_key}_traceability.md"
            traceability_path.write_text(traceability.to_markdown(), encoding="utf-8")
            result.traceability_path = str(traceability_path)

            log.info(
                f"Summary and traceability generated: {summary_path}, {traceability_path}"
            )
            return result

        except Exception as e:
            result.state = PipelineState.FAILED
            result.error = f"Summarization failed: {str(e)}"
            log.error(f"Summarization error: {str(e)}")
            return result
        
    def _calculate_context_hash(self, context: dict[str, Any]) -> str:
        """Calcula hash SHA256 del contexto para idempotencia."""
        context_json = json.dumps(context, sort_keys=True, default=str)
        return hashlib.sha256(context_json.encode("utf-8")).hexdigest()
    
    def _load_cached_result(self, issue_key: str, context_hash: str) -> PipelineResult | None:
        """Carga resultado en caché si existe y hash coincide."""

        state_file = self.state_dir / f"{issue_key}_{context_hash}.json"

        if not state_file.exists():
            return None

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            if state_data.get("context_hash") == context_hash:
                # Crear resultado desde estado guardado
                result = PipelineResult(  # ← DESINDENT aquí
                    issue_key=issue_key,
                    state=PipelineState(state_data["state"]),
                    timestamp=state_data["timestamp"],
                    feature_path=state_data.get("feature_path"),
                    summary_path=state_data.get("summary_path"),
                    traceability_path=state_data.get("traceability_path"),
                    context_hash=context_hash,
                    duration_seconds=state_data.get("duration_seconds", 0),
                    llm_requested=state_data.get("llm_requested", False),
                    llm_used=state_data.get("llm_used", False),
                    llm_provider=state_data.get("llm_provider"),
                    llm_model=state_data.get("llm_model"),
                    llm_error=state_data.get("llm_error"),
                    llm_scenarios_count=state_data.get("llm_scenarios_count", 0),
                )
                log.info(f"Loaded cached result for {issue_key}")
                return result
        except Exception as e:
            log.warning(f"Failed to load cached result: {str(e)}")

        return None
    
    def _save_state(self, result: PipelineResult) -> None:
        """Guarda estado del pipeline para idempotencia."""
        try:
            state_file = self.state_dir / f"{result.issue_key}_state.json"
            state_data = result.to_dict()

            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2)

            log.debug(f"State saved for {result.issue_key}: {state_file}")
        except Exception as e:
            log.warning(f"Failed to save state: {str(e)}")

    def _apply_llm_metadata(self, result: PipelineResult) -> None:
        metadata = self.analyzer.get_llm_metadata()
        result.llm_requested = bool(metadata.get("llm_requested"))
        result.llm_used = bool(metadata.get("llm_used"))
        result.llm_provider = metadata.get("llm_provider")
        result.llm_model = metadata.get("llm_model")
        result.llm_error = metadata.get("llm_error")
        result.llm_scenarios_count = int(metadata.get("llm_scenarios_count") or 0)

    def get_summary(self, result: PipelineResult) -> str:
        """Retorna resumen textual del resultado."""
        lines = [
            "=" * 70,
            f"Pipeline Result: {result.issue_key}",
            "=" * 70,
            f"Status: {result.state.value}",
            f"Duration: {result.duration_seconds:.2f}s",
            f"Timestamp: {result.timestamp}",
            "",
        ]

        if result.error:
            lines.append(f"❌ Error: {result.error}")
        else:
            lines.append("✅ Success")
            lines.append("")
            lines.append("📁 Output Files:")
            if result.feature_path:
                lines.append(f"   Feature: {result.feature_path}")

            if result.summary_path:
                lines.append(f"   Summary: {result.summary_path}")

            if result.traceability_path:
                lines.append(f"   Traceability: {result.traceability_path}")

            if result.analysis_result:
                lines.append("")
                lines.append("📊 Analysis Result:")
                lines.append(f"   Business Rules: {len(result.analysis_result.business_rules)}")
                lines.append(f"   Assumptions: {len(result.analysis_result.assumptions)}")
                lines.append(f"   Risks: {len(result.analysis_result.risks)}")
                lines.append(f"   Confidence: {result.analysis_result.confidence:.0%}")

            if result.validation_result:
                lines.append("")
                lines.append("🔍 Validation Result:")
                # Los errores y warnings ya son dicts
                errors = len(result.validation_result.get("errors", []))
                warnings = len(result.validation_result.get("warnings", []))
                confidence = result.validation_result.get("confidence", 0)
                lines.append(f"   Errors: {errors}")
                lines.append(f"   Warnings: {warnings}")
                lines.append(f"   Confidence: {confidence:.0%}")

        lines.append("=" * 70)
        return "\n".join(lines)
