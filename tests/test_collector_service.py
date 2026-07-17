import pytest

from ai_qa_gherkin.services.collector_service import ContextCollector, TextNormalizer


class TestTextNormalizer:
    def test_normalize_clean_text(self):
        text = "  Hello   world  \n\n  test  "
        result = TextNormalizer.normalize(text)
        assert result == "Hello world test"

    def test_normalize_empty(self):
        assert TextNormalizer.normalize("") == ""
        assert TextNormalizer.normalize(None) == ""

    def test_remove_duplicates(self):
        items = ["AC1", "ac1", "AC2", "AC1"]
        result = TextNormalizer.remove_duplicates(items)
        assert len(result) == 2
        assert "AC1" in result or "ac1" in result
        assert "AC2" in result

    def test_extract_ac_lines_with_ac_prefix(self):
        text = """
        AC1: User can login
        AC2: Password is required
        AC3: Email must be valid
        """
        result = TextNormalizer.extract_ac_lines(text)
        assert len(result) == 3
        assert "User can login" in result
        assert "Password is required" in result

    def test_extract_ac_lines_with_bullet(self):
        text = """
        - Criteria 1
        * Criteria 2
        - Criteria 3
        """
        result = TextNormalizer.extract_ac_lines(text)
        assert len(result) == 3
        assert "Criteria 1" in result

    def test_extract_ac_lines_empty(self):
        result = TextNormalizer.extract_ac_lines("")
        assert result == []


class TestContextCollector:
    def test_collect_issue_context(self):
        issue_data = {
            "key": "DYF-4307",
            "summary": "  Import feature to Xray  ",
            "description": "AC1: Feature must be valid\nAC2: Must import successfully",
            "labels": ["smoke", "xray", "smoke"],
            "issuelinks": [],
        }

        collector = ContextCollector()
        result = collector.collect_issue_context(issue_data)

        assert result.issue_key == "DYF-4307"
        assert result.summary == "Import feature to Xray"
        assert len(result.acceptance_criteria) >= 2
        assert len(result.links) == 0

    def test_collect_confluence_context(self):
        page_data = {
            "id": "123456",
            "title": "  Test Specification  ",
            "body": {
                "storage": {
                    "value": "<p>This is a test page</p>"
                }
            },
            "_links": {"self": "https://wiki.example.com/pages/123456"}
        }

        collector = ContextCollector()
        result = collector.collect_confluence_context(page_data)

        assert result.page_id == "123456"
        assert result.title == "Test Specification"
        assert "test page" in result.content.lower()

    def test_collect_git_context(self):
        git_data = {
            "repo_url": "https://github.com/org/repo",
            "branch": "  main  ",
            "commit_sha": "abc123def456",
            "changed_files": ["src/main.py", "tests/test.py", "src/main.py"],
            "diff_summary": "Added feature X"
        }

        collector = ContextCollector()
        result = collector.collect_git_context(git_data)

        assert result.repo_url == "https://github.com/org/repo"
        assert result.branch == "main"
        assert len(result.changed_files) == 2  # sin duplicados

    def test_merge_contexts(self):
        from ai_qa_gherkin.models import IssueContext

        issue = IssueContext(
            issue_key="DYF-4307",
            summary="Test feature",
            acceptance_criteria=["AC1", "AC2"]
        )

        collector = ContextCollector()
        merged = collector.merge_contexts(issue=issue)

        assert merged["primary_scope"] == "Test feature"
        assert len(merged["combined_acceptance_criteria"]) >= 2
        assert merged["issue"] is not None
        assert merged["confluence"] is None
        assert merged["git"] is None