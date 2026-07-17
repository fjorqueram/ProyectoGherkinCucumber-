from datetime import datetime
import pytest

from ai_qa_gherkin.models import (
    AnalysisResult,
    ConfluenceContext,
    ConfluencePage,
    ExecutionResult,
    GeneratedFeature,
    GitCommit,
    GitContext,
    IssueContext,
    JiraIssue,
    PublishResult,
    PullRequest,
    ValidationResult,
    XrayImportResponse,
)


class TestJiraIssue:
    def test_create_minimal(self):
        issue = JiraIssue(key="DYF-123", summary="Test issue")
        assert issue.key == "DYF-123"
        assert issue.summary == "Test issue"
        assert issue.description == ""
        assert issue.links == []

    def test_serialize(self):
        issue = JiraIssue(
            key="DYF-123",
            summary="Test",
            description="Desc",
            links=["DYF-124"],
        )
        data = issue.model_dump()
        assert data["key"] == "DYF-123"
        assert data["links"] == ["DYF-124"]

    def test_deserialize(self):
        data = {"key": "DYF-123", "summary": "Test"}
        issue = JiraIssue(**data)
        assert issue.key == "DYF-123"


class TestConfluencePage:
    def test_create(self):
        page = ConfluencePage(
            id="123",
            title="My Page",
            url="https://wiki.example.com/pages/123",
            content="Content here",
        )
        assert page.id == "123"
        assert page.title == "My Page"


class TestGitCommit:
    def test_create(self):
        commit = GitCommit(
            sha="abc123",
            message="Fix bug",
            url="https://github.com/org/repo/commit/abc123",
        )
        assert commit.sha == "abc123"


class TestPullRequest:
    def test_create(self):
        pr = PullRequest(
            id="456",
            title="Add feature",
            url="https://github.com/org/repo/pull/42",
            state="open",
        )
        assert pr.id == "456"
        assert pr.state == "open"


class TestXrayImportResponse:
    def test_create_success(self):
        resp = XrayImportResponse(
            success=True,
            payload={"updatedOrCreatedTests": [{"key": "QA-52627"}]},
        )
        assert resp.success is True
        assert "updatedOrCreatedTests" in resp.payload


class TestIssueContext:
    def test_create_full(self):
        ctx = IssueContext(
            issue_key="DYF-4307",
            summary="Smoke test",
            description="Test description",
            acceptance_criteria=["AC1", "AC2"],
            links=["DYF-4306"],
        )
        assert ctx.issue_key == "DYF-4307"
        assert len(ctx.acceptance_criteria) == 2


class TestConfluenceContext:
    def test_create(self):
        ctx = ConfluenceContext(
            page_id="789",
            title="Requirements",
            url="https://wiki/page/789",
        )
        assert ctx.page_id == "789"


class TestGitContext:
    def test_create(self):
        ctx = GitContext(
            repo_url="https://github.com/org/repo",
            branch="main",
            commit_sha="def456",
            changed_files=["src/main.py", "tests/test_main.py"],
        )
        assert ctx.branch == "main"
        assert len(ctx.changed_files) == 2


class TestAnalysisResult:
    def test_create(self):
        result = AnalysisResult(
            issue_key="DYF-4307",
            scope_summary="Import feature to Xray",
            business_rules=["BR1: Feature must be valid Gherkin"],
            assumptions=["Xray project exists"],
            risks=["Network timeout"],
            confidence=0.95,
        )
        assert result.issue_key == "DYF-4307"
        assert result.confidence == 0.95
        assert len(result.business_rules) == 1

    def test_confidence_validation(self):
        with pytest.raises(ValueError):
            AnalysisResult(
                issue_key="DYF-123",
                scope_summary="Test",
                confidence=1.5,  # > 1.0 invalid
            )


class TestGeneratedFeature:
    def test_create(self):
        feature = GeneratedFeature(
            feature_name="Smoke Xray import",
            gherkin_text="Feature: Test\n  Scenario: Test",
            source_issue_key="DYF-4307",
            scenarios_count=1,
        )
        assert feature.feature_name == "Smoke Xray import"
        assert feature.language == "es"
        assert isinstance(feature.generated_at, datetime)

    def test_serialize_with_datetime(self):
        feature = GeneratedFeature(
            feature_name="Test",
            gherkin_text="Feature: Test",
        )
        data = feature.model_dump_json()
        assert "generated_at" in data


class TestValidationResult:
    def test_valid_feature(self):
        result = ValidationResult(
            is_valid=True,
            syntax_ok=True,
            lint_ok=True,
            errors=[],
            warnings=[],
            confidence=0.9,
        )
        assert result.is_valid is True

    def test_invalid_with_errors(self):
        result = ValidationResult(
            is_valid=False,
            syntax_ok=False,
            errors=[{"message": "Invalid Gherkin syntax at line 3"}],
            confidence=0.8,
        )
        assert result.is_valid is False
        assert len(result.errors) == 1


class TestPublishResult:
    def test_xray_publish(self):
        result = PublishResult(
            success=True,
            destination="xray",
            project_key="QA",
            created_keys=["QA-52627"],
            url="https://imed.atlassian.net/browse/QA-52627",
        )
        assert result.success is True
        assert result.destination == "xray"

    def test_invalid_destination(self):
        with pytest.raises(ValueError):
            PublishResult(
                success=True,
                destination="invalid_dest",  # type: ignore
            )


class TestExecutionResult:
    def test_create(self):
        result = ExecutionResult(
            success=True,
            total=5,
            passed=4,
            failed=1,
            skipped=0,
            duration_seconds=12.5,
            execution_key="QA-EXEC-123",
            test_keys=["QA-52627", "QA-52628"],
        )
        assert result.success is True
        assert result.passed == 4
        assert result.failed == 1

    def test_all_passed(self):
        result = ExecutionResult(
            success=True,
            total=3,
            passed=3,
        )
        assert result.failed == 0