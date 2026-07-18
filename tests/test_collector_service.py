import pytest

from ai_qa_gherkin.services.collector_service import ContextCollector


class TestContextCollector:
    def setup_method(self):
        """Setup antes de cada test."""
        self.collector = ContextCollector()

    def test_collect_empty_context(self):
        """Test recolectar contexto vacío."""
        result = self.collector.collect()

        assert result["issue"]["issue_key"] == "UNKNOWN"
        assert result["confluence"] == {}  # ← CAMBIAR de None a {}
        assert result["git"] == {}  # ← CAMBIAR de None a {}

    def test_collect_issue_only(self):
        """Test recolectar solo issue."""
        issue_data = {
            "issue_key": "DYF-123",
            "summary": "Test Feature",
            "description": "Test description",
            "acceptance_criteria": ["AC1", "AC2"],
        }

        result = self.collector.collect(issue=issue_data)

        assert result["issue"]["issue_key"] == "DYF-123"
        assert result["issue"]["summary"] == "Test Feature"
        assert len(result["issue"]["acceptance_criteria"]) == 2
        assert result["issue_key"] == "DYF-123"
        assert result["primary_scope"] == "Test Feature"

    def test_collect_with_confluence(self):
        """Test recolectar con Confluence."""
        issue_data = {
            "issue_key": "DYF-123",
            "summary": "Test",
            "description": "",
            "acceptance_criteria": [],
        }

        confluence_data = {
            "page_id": "456",
            "title": "Spec Page",
            "content": "This is the spec",
            "url": "https://confluence.com/page/456",
        }

        result = self.collector.collect(
            issue=issue_data,
            confluence=confluence_data,
        )

        # Type guard
        assert isinstance(result["confluence"], dict)
        assert result["confluence"]["page_id"] == "456"
        assert result["confluence"]["title"] == "Spec Page"

    def test_collect_with_git(self):
        """Test recolectar con Git."""
        issue_data = {
            "issue_key": "DYF-123",
            "summary": "Test",
            "description": "",
            "acceptance_criteria": [],
        }

        git_data = {
            "commit_sha": "abc123def",
            "changed_files": ["src/feature.py", "tests/test_feature.py"],
            "diff_summary": "Add feature implementation",
            "branch": "feature/test",
            "author": "developer@example.com",
        }

        result = self.collector.collect(
            issue=issue_data,
            git=git_data,
        )

        # Type guard
        assert isinstance(result["git"], dict)
        assert result["git"]["commit_sha"] == "abc123def"
        assert len(result["git"]["changed_files"]) == 2

    def test_collect_all_sources(self):
        """Test recolectar de todas las fuentes."""
        issue_data = {
            "issue_key": "DYF-789",
            "summary": "Complete Feature",
            "description": "Full description",
            "acceptance_criteria": ["AC1", "AC2", "AC3"],
            "issue_type": "Story",
            "labels": ["important", "urgent"],
            "priority": "High",
        }

        confluence_data = {
            "page_id": "789",
            "title": "Feature Spec",
            "content": "Detailed specifications",
            "url": "https://confluence.com/spec",
        }

        git_data = {
            "commit_sha": "xyz789",
            "changed_files": ["module.py", "test_module.py"],
            "diff_summary": "Implementation",
            "branch": "main",
            "author": "qa@team.com",
        }

        result = self.collector.collect(
            issue=issue_data,
            confluence=confluence_data,
            git=git_data,
        )

        # Validar issue
        assert result["issue"]["issue_key"] == "DYF-789"
        assert result["issue"]["issue_type"] == "Story"
        assert len(result["issue"]["acceptance_criteria"]) == 3

        # Validar confluence (type guard)
        assert isinstance(result["confluence"], dict)
        assert result["confluence"]["page_id"] == "789"
        assert "specifications" in result["confluence"]["content"]

        # Validar git (type guard)
        assert isinstance(result["git"], dict)
        assert result["git"]["commit_sha"] == "xyz789"
        assert len(result["git"]["changed_files"]) == 2

        # Validar merged
        assert result["issue_key"] == "DYF-789"
        assert result["primary_scope"] == "Complete Feature"

    def test_normalize_issue_minimal(self):
        """Test normalizar issue mínimo."""
        issue_data = {"issue_key": "TEST-1", "summary": "Test"}

        normalized = self.collector._normalize_issue(issue_data)

        assert normalized["issue_key"] == "TEST-1"
        assert normalized["summary"] == "Test"
        assert normalized["description"] == ""
        assert normalized["acceptance_criteria"] == []

    def test_normalize_issue_full(self):
        """Test normalizar issue completo."""
        issue_data = {
            "issue_key": "TEST-2",
            "summary": "Full Issue",
            "description": "Long description",
            "acceptance_criteria": ["AC1", "AC2"],
            "issue_type": "Story",
            "labels": ["tag1", "tag2"],
            "priority": "Medium",
        }

        normalized = self.collector._normalize_issue(issue_data)

        assert normalized["issue_key"] == "TEST-2"
        assert normalized["issue_type"] == "Story"
        assert len(normalized["labels"]) == 2
        assert normalized["priority"] == "Medium"

    def test_normalize_issue_none(self):
        """Test normalizar issue None."""
        normalized = self.collector._normalize_issue(None)

        assert normalized["issue_key"] == "UNKNOWN"
        assert normalized["summary"] == ""
        assert normalized["acceptance_criteria"] == []

    def test_normalize_confluence_none(self):
        """Test normalizar confluence None."""
        normalized = self.collector._normalize_confluence(None)
        assert normalized is None

    def test_normalize_confluence_minimal(self):
        """Test normalizar confluence mínimo."""
        confluence_data = {"page_id": "123", "title": "Page"}

        normalized = self.collector._normalize_confluence(confluence_data)
        
        # Type guard: verificar que no es None
        assert normalized is not None
        assert normalized["page_id"] == "123"
        assert normalized["title"] == "Page"
        assert normalized["content"] == ""

    def test_normalize_git_none(self):
        """Test normalizar git None."""
        normalized = self.collector._normalize_git(None)
        assert normalized is None

    def test_normalize_git_full(self):
        """Test normalizar git completo."""
        git_data = {
            "commit_sha": "abc123",
            "changed_files": ["file1.py", "file2.py"],
            "diff_summary": "Changes",
            "branch": "main",
            "author": "dev@example.com",
        }

        normalized = self.collector._normalize_git(git_data)
        
        # Type guard: verificar que no es None
        assert normalized is not None
        assert normalized["commit_sha"] == "abc123"
        assert len(normalized["changed_files"]) == 2
        assert normalized["branch"] == "main"

    def test_extract_primary_scope_short(self):
        """Test extraer scope corto."""
        issue = {"summary": "Short"}

        scope = self.collector._extract_primary_scope(issue)

        assert scope == "Short"

    def test_extract_primary_scope_long(self):
        """Test extraer scope largo (trunca a 100 chars)."""
        long_summary = "A" * 150

        issue = {"summary": long_summary}

        scope = self.collector._extract_primary_scope(issue)

        assert len(scope) == 100
        assert scope == "A" * 100

    def test_extract_primary_scope_empty(self):
        """Test extraer scope vacío."""
        issue = {"summary": ""}

        scope = self.collector._extract_primary_scope(issue)

        assert scope == ""

    def test_combine_acceptance_criteria(self):
        """Test combinar criterios de aceptación."""
        issue = {
            "acceptance_criteria": ["Must do A", "Must do B", "Must do C"]
        }

        combined = self.collector._combine_acceptance_criteria(issue)

        assert len(combined) == 3
        assert "Must do A" in combined

    def test_combine_acceptance_criteria_empty(self):
        """Test combinar criterios vacíos."""
        issue = {"acceptance_criteria": []}

        combined = self.collector._combine_acceptance_criteria(issue)

        assert combined == []

    def test_collect_missing_keys(self):
        """Test recolectar cuando faltan keys."""
        issue_data = {
            "issue_key": "TEST-3",
            # Falta summary, description, acceptance_criteria
        }

        result = self.collector.collect(issue=issue_data)

        assert result["issue"]["issue_key"] == "TEST-3"
        assert result["issue"]["summary"] == ""
        assert result["issue"]["acceptance_criteria"] == []

    def test_merged_context_structure(self):
        """Test estructura del contexto merged."""
        issue_data = {
            "issue_key": "STRUCT-1",
            "summary": "Test",
            "description": "",
            "acceptance_criteria": [],
        }

        result = self.collector.collect(issue=issue_data)

        # Validar estructura esperada
        assert "issue" in result
        assert "confluence" in result
        assert "git" in result
        assert "primary_scope" in result
        assert "combined_acceptance_criteria" in result
        assert "issue_key" in result

    def test_collect_preserves_data_integrity(self):
        """Test que collect preserva la integridad de datos."""
        original_issue = {
            "issue_key": "INTEG-1",
            "summary": "Preserve Data",
            "description": "Important description",
            "acceptance_criteria": ["AC1", "AC2"],
        }

        result = self.collector.collect(issue=original_issue)

        assert result["issue"]["summary"] == original_issue["summary"]
        assert result["issue"]["description"] == original_issue["description"]
        assert result["issue"]["acceptance_criteria"] == original_issue["acceptance_criteria"]