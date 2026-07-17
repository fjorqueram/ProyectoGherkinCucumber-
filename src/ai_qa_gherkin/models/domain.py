from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

class JiraIssue(BaseModel):
    key: str
    summary: str
    description: str = ""
    acceptance_criteria: str = ""
    links: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)

class ConfluencePage(BaseModel):
    id: str
    title: str
    url: str
    content: str = ""

class GitCommit(BaseModel):
    sha: str
    message: str
    url: str

class PullRequest(BaseModel):
    id: str
    title: str
    url: str
    state: str

class XrayImportResponse(BaseModel):
    success: bool
    payload: dict[str, Any] = Field(default_factory=dict)

# ===== Nuevos modelos solicitados =====

class IssueContext(BaseModel):
    issue_key: str
    summary: str
    description: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class ConfluenceContext(BaseModel):
    page_id: str
    title: str
    url: str
    content: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class GitContext(BaseModel):
    repo_url: str = ""
    branch: str = ""
    commit_sha: str = ""
    changed_files: list[str] = Field(default_factory=list)
    diff_summary: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class AnalysisResult(BaseModel):
    issue_key: str
    scope_summary: str
    business_rules: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    raw: dict[str, Any] = Field(default_factory=dict)


class GeneratedFeature(BaseModel):
    feature_name: str
    gherkin_text: str
    language: str = "es"
    tags: list[str] = Field(default_factory=list)
    scenarios_count: int = 0
    source_issue_key: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
class ValidationResult(BaseModel):
    is_valid: bool
    syntax_ok: bool = True
    lint_ok: bool = True
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    confidence: float
    raw: dict[str, Any] | None = None


class PublishResult(BaseModel):
    success: bool
    destination: Literal["xray", "jira", "confluence", "git", "local"] = "xray"
    project_key: str = ""
    created_keys: list[str] = Field(default_factory=list)
    updated_keys: list[str] = Field(default_factory=list)
    url: str = ""
    message: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    success: bool
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    execution_key: str = ""
    test_keys: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    