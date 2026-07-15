from typing import Any
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