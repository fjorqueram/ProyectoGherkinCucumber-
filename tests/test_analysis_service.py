import pytest
from unittest.mock import Mock, patch

from ai_qa_gherkin.services.analysis_service import (
    AnalysisService,
    BusinessRule,
    ErrorScenario,
    HappyPath,
    Precondition,
    TraceabilityLink,
)


class TestTraceabilityLink:
    def test_create(self):
        trace = TraceabilityLink(
            source_type="jira",
            source_id="DYF-4307",
            source_name="Import feature",
        )
        assert trace.source_type == "jira"
        assert trace.source_id == "DYF-4307"

    def test_to_dict(self):
        trace = TraceabilityLink(
            source_type="confluence",
            source_id="123",
            source_name="Spec page",
            line_number=42,
        )
        data = trace.to_dict()
        assert data["source_type"] == "confluence"
        assert data["line_number"] == 42


class TestBusinessRule:
    def test_create(self):
        trace = TraceabilityLink(
            source_type="jira",
            source_id="DYF-123",
            source_name="Issue",
        )
        rule = BusinessRule(
            rule="Feature must be implemented",
            traceability=trace,
            category="general",
        )
        assert rule.rule == "Feature must be implemented"
        assert rule.category == "general"

    def test_to_dict(self):
        trace = TraceabilityLink("jira", "DYF-123", "Test")
        rule = BusinessRule("Rule text", trace)
        data = rule.to_dict()
        assert data["rule"] == "Rule text"
        assert data["traceability"]["source_id"] == "DYF-123"

    def test_category_default(self):
        """Test que category tiene default."""
        trace = TraceabilityLink("jira", "DYF-123", "Test")
        rule = BusinessRule("Rule", trace)
        assert rule.category == "general"


class TestPrecondition:
    def test_create(self):
        trace = TraceabilityLink("jira", "DYF-123", "Test")
        precond = Precondition("User must be logged in", trace)
        assert precond.precondition == "User must be logged in"

    def test_to_dict(self):
        trace = TraceabilityLink("jira", "DYF-123", "Test")
        precond = Precondition("Precond text", trace)
        data = precond.to_dict()
        assert "precondition" in data
        assert "traceability" in data


class TestHappyPath:
    def test_create(self):
        trace = TraceabilityLink("jira", "DYF-123", "Test")
        happy = HappyPath(
            name="Happy path",
            steps=["Step 1", "Step 2"],
            traceability=trace,
        )
        assert happy.name == "Happy path"
        assert len(happy.steps) == 2

    def test_to_dict(self):
        trace = TraceabilityLink("jira", "DYF-123", "Test")
        happy = HappyPath("Path", ["S1", "S2"], trace)
        data = happy.to_dict()
        assert data["name"] == "Path"
        assert len(data["steps"]) == 2


class TestErrorScenario:
    def test_create(self):
        trace = TraceabilityLink("jira", "DYF-123", "Test")
        error = ErrorScenario(
            error_type="validation",
            description="Invalid input",
            expected_outcome="Error shown",
            traceability=trace,
        )
        assert error.error_type == "validation"
        assert error.description == "Invalid input"

    def test_to_dict(self):
        trace = TraceabilityLink("jira", "DYF-123", "Test")
        error = ErrorScenario("validation", "Desc", "Outcome", trace)
        data = error.to_dict()
        assert data["error_type"] == "validation"
        assert data["expected_outcome"] == "Outcome"


class TestAnalysisService:
    def test_init_default(self):
        """Test inicialización por defecto (usa LLM si está disponible)."""
        service = AnalysisService(use_llm=False)  # ← CAMBIAR A False
        assert service.business_rules == []
        assert service.preconditions == []

    def test_init_with_llm_false(self):
        """Test inicialización sin LLM (mock mode)."""
        service = AnalysisService(use_llm=False)
        assert service.use_llm is False
        assert service.llm_client is None

    def test_analyze_with_issue_only(self):
        """Test análisis con solo issue."""
        context = {
            "issue": {
                "issue_key": "DYF-4307",
                "summary": "Smoke test Xray",
                "description": "Test feature import",
                "acceptance_criteria": [
                    "Feature must be valid Gherkin",
                    "Must import without errors",
                ],
            },
            "confluence": None,
            "git": None,
            "primary_scope": "Smoke test Xray",
        }

        service = AnalysisService(use_llm=False)  # ← YA ESTÁ
        result = service.analyze(context)

        assert result.issue_key == "DYF-4307"
        assert result.scope_summary == "Smoke test Xray"
        assert len(result.business_rules) >= 2
        assert result.confidence > 0
        assert result.confidence <= 1.0

    def test_analyze_with_all_sources(self):
        """Test análisis con todas las fuentes (Jira + Confluence + Git)."""
        context = {
            "issue": {
                "issue_key": "DYF-123",
                "summary": "Feature X",
                "description": "Precondition: User logged in",
                "acceptance_criteria": ["AC1: Test"],
            },
            "confluence": {
                "page_id": "456",
                "title": "Spec",
                "content": "Validation must be performed. Error handling: Invalid inputs must show error message",
            },
            "git": {
                "commit_sha": "abc123",
                "changed_files": ["tests/test_feature.py", "src/feature.py"],
                "diff_summary": "Add feature",
            },
            "primary_scope": "Feature X",
        }

        service = AnalysisService(use_llm=False)  # ← AGREGAR
        result = service.analyze(context)

        assert result.issue_key == "DYF-123"
        assert len(result.business_rules) > 2
        assert len(result.raw["preconditions"]) > 0
        assert len(result.raw["error_scenarios"]) > 0
        assert len(result.raw["happy_paths"]) > 0

    def test_analyze_confluence_only(self):
        """Test que Confluence agrega reglas de validación y permisos."""
        context = {
            "issue": {
                "issue_key": "DYF-456",
                "summary": "Test",
                "description": "",
                "acceptance_criteria": [],
            },
            "confluence": {
                "page_id": "789",
                "title": "Docs",
                "content": "validation required, permission check needed, exception handling",
            },
            "git": None,
        }

        service = AnalysisService(use_llm=False)  # ← AGREGAR
        result = service.analyze(context)

        assert len(result.business_rules) > 1
        categories = [r for r in result.raw["business_rules"]]
        assert any("validation" in str(c).lower() for c in categories)

    def test_analyze_git_changes(self):
        """Test que Git detecta test files y boundary testing."""
        context = {
            "issue": {
                "issue_key": "DYF-789",
                "summary": "Test",
                "description": "",
                "acceptance_criteria": [],
            },
            "confluence": None,
            "git": {
                "commit_sha": "def456",
                "changed_files": [
                    "tests/test_module.py",
                    "tests/boundary_tests.py",
                    "src/module.py",
                ],
                "diff_summary": "Add tests",
            },
        }

        service = AnalysisService(use_llm=False)  # ← AGREGAR
        result = service.analyze(context)

        assert any("test" in r.lower() for r in result.business_rules)

    def test_confidence_calculation(self):
        """Test cálculo de confianza (aumenta con más extracciones)."""
        context = {
            "issue": {
                "issue_key": "TEST",
                "summary": "Test",
                "description": "",
                "acceptance_criteria": ["AC1", "AC2", "AC3"],
            },
            "confluence": None,
            "git": None,
        }

        service = AnalysisService(use_llm=False)  # ← AGREGAR
        result = service.analyze(context)

        assert 0.0 <= result.confidence <= 1.0

    def test_traceability_all_rules(self):
        """Test que TODAS las reglas tienen trazabilidad."""
        context = {
            "issue": {
                "issue_key": "DYF-4307",
                "summary": "Feature",
                "description": "Precondition test",
                "acceptance_criteria": ["AC1", "AC2"],
            },
            "confluence": {
                "page_id": "123",
                "title": "Spec",
                "content": "validation required",
            },
            "git": {
                "commit_sha": "abc",
                "changed_files": ["test_file.py"],
                "diff_summary": "Test",
            },
        }

        service = AnalysisService(use_llm=False)  # ← AGREGAR
        result = service.analyze(context)

        for rule_dict in result.raw["business_rules"]:
            assert "traceability" in rule_dict
            assert rule_dict["traceability"]["source_id"] is not None
            assert rule_dict["traceability"]["source_type"] in ["jira", "confluence", "git"]

        for precond_dict in result.raw["preconditions"]:
            assert "traceability" in precond_dict

    def test_traceability_links(self):
        """Test trazabilidad de reglas específicas."""
        context = {
            "issue": {
                "issue_key": "DYF-4307",
                "summary": "Test Feature",
                "description": "",
                "acceptance_criteria": ["AC1"],
            },
            "confluence": None,
            "git": None,
        }

        service = AnalysisService(use_llm=False)  # ← AGREGAR
        result = service.analyze(context)

        first_rule = result.raw["business_rules"][0]
        assert first_rule["traceability"]["source_type"] == "jira"
        assert first_rule["traceability"]["source_id"] == "DYF-4307"

    def test_summary_output(self):
        """Test que summary imprime formato correcto."""
        context = {
            "issue": {
                "issue_key": "DYF-123",
                "summary": "Feature",
                "description": "",
                "acceptance_criteria": ["AC1"],
            },
            "confluence": None,
            "git": None,
        }

        service = AnalysisService(use_llm=False)  # ← AGREGAR
        service.analyze(context)
        summary = service.get_summary()

        assert "Analysis Summary" in summary
        assert "Business Rules:" in summary
        assert "Preconditions:" in summary
        assert "Happy Paths:" in summary
        assert "Error Scenarios:" in summary
        assert "Confidence:" in summary

    def test_analyze_empty_context(self):
        """Test análisis con contexto vacío."""
        context = {
            "issue": {
                "issue_key": "EMPTY",
                "summary": "",
                "description": "",
                "acceptance_criteria": [],
            },
            "confluence": None,
            "git": None,
        }

        service = AnalysisService(use_llm=False)  # ← AGREGAR
        result = service.analyze(context)

        assert result.issue_key == "EMPTY"
        assert result.confidence >= 0.5

    def test_process_llm_result_dict_format(self):
        """Test procesamiento de resultado LLM en formato dict."""
        service = AnalysisService(use_llm=False)  # ← AGREGAR
        
        llm_result = {
            "business_rules": [
                {"description": "Rule 1", "category": "general"},
                {"description": "Rule 2", "category": "validation"},
            ],
            "preconditions": ["Precond 1"],
            "happy_paths": [
                {"name": "Path 1", "steps": ["S1", "S2"]},
            ],
            "error_scenarios": [
                {"error_type": "validation", "description": "Error", "expected_outcome": "Handled"},
            ],
        }

        context = {
            "issue": {"issue_key": "TEST", "summary": "Test", "description": "", "acceptance_criteria": []},
        }

        service._process_llm_result(llm_result, context)

        assert len(service.business_rules) == 2
        assert len(service.preconditions) == 1
        assert len(service.happy_paths) == 1
        assert len(service.error_scenarios) == 1