import os
import tempfile

import pytest

from ai_qa_gherkin.services.summary_service import (
    ExecutiveSummary,
    SummaryService,
    TraceabilityLink,
    TraceabilityMatrix,
)


class TestExecutiveSummary:
    def test_create_summary(self):
        summary = ExecutiveSummary(
            issue_key="DYF-123",
            summary="Test Feature",
            description="Test description",
        )
        assert summary.issue_key == "DYF-123"
        assert summary.summary == "Test Feature"

    def test_summary_to_markdown(self):
        summary = ExecutiveSummary(
            issue_key="DYF-123",
            summary="Test Feature",
            description="Description",
        )
        md = summary.to_markdown()
        assert "DYF-123" in md
        assert "Test Feature" in md


class TestTraceabilityLink:
    def test_create_link(self):
        link = TraceabilityLink(
            ac_id="AC1",
            ac_text="Must do X",
            scenario_name="Scenario 1",
            scenario_line=10,
            source_type="jira",
            source_id="DYF-123",
            source_name="Issue",
        )
        assert link.ac_id == "AC1"
        assert link.source_type == "jira"

    def test_link_to_dict(self):
        link = TraceabilityLink(
            ac_id="AC1",
            ac_text="Must do X",
            scenario_name="Scenario 1",
            scenario_line=10,
            source_type="confluence",
            source_id="456",
            source_name="Spec",
        )
        data = link.to_dict()
        assert data["ac_id"] == "AC1"
        assert data["source"]["type"] == "confluence"


class TestTraceabilityMatrix:
    def test_create_matrix(self):
        matrix = TraceabilityMatrix("DYF-123")
        assert matrix.issue_key == "DYF-123"
        assert len(matrix.links) == 0

    def test_add_link(self):
        matrix = TraceabilityMatrix("DYF-123")
        link = TraceabilityLink(
            ac_id="AC1",
            ac_text="Must",
            scenario_name="Scenario 1",
            scenario_line=10,
            source_type="jira",
            source_id="DYF-123",
            source_name="Issue",
        )
        matrix.add_link(link)
        assert len(matrix.links) == 1

    def test_matrix_coverage(self):
        matrix = TraceabilityMatrix("DYF-123")
        matrix.add_link(TraceabilityLink("AC1", "Must", "Scenario 1", 10, "jira", "DYF-123", "Issue"))
        matrix.add_link(TraceabilityLink("AC2", "Must", "Scenario 2", 15, "jira", "DYF-123", "Issue"))

        coverage = matrix.get_ac_coverage()
        assert coverage["total_ac"] == 2
        assert coverage["covered_ac"] == 2
        assert coverage["coverage_ratio"] == 1.0

    def test_matrix_source_distribution(self):
        matrix = TraceabilityMatrix("DYF-123")
        matrix.add_link(TraceabilityLink("AC1", "Must", "S1", 10, "jira", "DYF-123", "Issue"))
        matrix.add_link(TraceabilityLink("AC2", "Must", "S2", 15, "confluence", "456", "Spec"))

        dist = matrix.get_source_distribution()
        assert dist["jira"] == 1
        assert dist["confluence"] == 1

    def test_matrix_to_markdown(self):
        matrix = TraceabilityMatrix("DYF-123")
        matrix.add_link(TraceabilityLink("AC1", "Must X", "Scenario 1", 10, "jira", "DYF-123", "Issue"))

        md = matrix.to_markdown()
        assert "DYF-123" in md
        assert "AC1" in md
        assert "Scenario 1" in md
        assert "jira" in md


class TestSummaryService:
    def test_generate_executive_summary(self):
        analysis = {
            "issue": {
                "issue_key": "DYF-123",
                "summary": "Test Feature",
            },
            "business_rules": ["Rule 1", "Rule 2"],
            "raw": {"business_rules": []},
        }
        validation = {
            "is_valid": True,
            "confidence": 0.95,
            "raw": {"detailed_errors": []},
        }

        service = SummaryService()
        summary = service.generate_executive_summary(
            issue_key="DYF-123",
            analysis_result=analysis,
            validation_result=validation,
            gherkin_path="output/features/DYF-123.feature",
        )

        assert summary.issue_key == "DYF-123"
        assert "2 reglas de negocio" in summary.description

    def test_generate_traceability_matrix(self):
        analysis = {
            "issue": {
                "issue_key": "DYF-123",
                "acceptance_criteria": ["AC1", "AC2"],
            },
            "raw": {"business_rules": []},
        }

        service = SummaryService()
        matrix = service.generate_traceability_matrix("DYF-123", analysis)

        assert matrix.issue_key == "DYF-123"
        assert len(matrix.links) == 2

    def test_save_summary(self):
        summary = ExecutiveSummary(
            issue_key="DYF-123",
            summary="Test",
            description="Test description",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            service = SummaryService(output_summary=tmpdir)
            filepath = service.save_summary(summary)

            assert os.path.exists(filepath)
            with open(filepath, "r") as f:
                content = f.read()
                assert "DYF-123" in content

    def test_save_traceability(self):
        matrix = TraceabilityMatrix("DYF-123")
        matrix.add_link(TraceabilityLink("AC1", "Must", "S1", 10, "jira", "DYF-123", "Issue"))

        with tempfile.TemporaryDirectory() as tmpdir:
            service = SummaryService(output_traceability=tmpdir)
            filepath = service.save_traceability(matrix)

            assert os.path.exists(filepath)
            with open(filepath, "r") as f:
                content = f.read()
                assert "AC1" in content