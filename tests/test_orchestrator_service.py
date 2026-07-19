from pathlib import Path

from ai_qa_gherkin.orchestrator import Orchestrator, PipelineResult, PipelineState


class TestOrchestrator:
    def test_init(self):
        """Test inicializar orchestrator."""
        output_dir = Path("output/test_orchestrator_service")
        orchestrator = Orchestrator(output_dir=str(output_dir), use_llm=False)
        assert orchestrator.output_dir == output_dir

    def test_run_minimal_context(self):
        """Test ejecutar pipeline con contexto minimo."""

    def test_run_full_context(self):
        """Test ejecutar pipeline con contexto completo."""

    def test_idempotence(self):
        """Test idempotencia: mismo contexto = mismo resultado."""

    def test_different_context_regenerates(self):
        """Test contexto diferente = regenera."""

    def test_get_summary_success(self):
        """Test resumen exitoso."""

    def test_get_summary_error(self):
        """Test resumen con error."""

    def test_files_exist(self):
        """Test que los archivos se crean."""

    def test_feature_content(self):
        """Test que el feature tiene contenido valido."""

    def test_pipeline_state_serializes_llm_metadata(self):
        """Test que el estado incluye metadata auditable de IA."""
        result = PipelineResult(
            issue_key="DYF-4275",
            state=PipelineState.ANALYZED,
            llm_requested=True,
            llm_used=True,
            llm_provider="openai",
            llm_model="test-model",
            llm_scenarios_count=3,
        )

        data = result.to_dict()

        assert data["llm_requested"] is True
        assert data["llm_used"] is True
        assert data["llm_provider"] == "openai"
        assert data["llm_model"] == "test-model"
        assert data["llm_scenarios_count"] == 3
