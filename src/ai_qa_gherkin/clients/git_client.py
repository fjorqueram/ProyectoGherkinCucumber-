from __future__ import annotations
import re
from typing import Any
from urllib.parse import quote
import httpx
from ai_qa_gherkin.config import settings
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models.domain import GitCommit, PullRequest
from ai_qa_gherkin.retry import retry_policy, TransientError, PermanentError

log = get_logger("git_client")

class GitClient:
    """
    MVP para GitHub API.
    Si usas GitLab, luego hacemos adapter.
    """
    def __init__(self) -> None:
        self.base_url = settings.git_api_base_url.rstrip("/")
        self.token = settings.git_token
        self.timeout = settings.git_timeout_seconds
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }

    def _handle_error(self, response: httpx.Response) -> None:
        if response.status_code in (429, 502, 503, 504):
            raise TransientError(f"Git Transient: {response.status_code}: {response.text[:250]}")
        if response.status_code >= 400:
            raise PermanentError(f"Git Permanent: {response.status_code}: {response.text[:250]}")
        
    @retry_policy()
    def search_commits_by_issue_key(self, owner: str, repo: str, issue_key: str, limit: int = 10) -> list[GitCommit]:
        """
        Busca commits en un repositorio que contengan el issue_key en su mensaje.
        """
        url = f"{self.base_url}/search/commits"
        params = {
            "q": f"{issue_key} repo:{owner}/{repo}",
            "order": "desc",
            "per_page": limit,
        }
        headers = {**self.headers, "Accept": "application/vnd.github.cloak-preview+json"}

        log.info(f"Searching commits for issue_key {issue_key} in {owner}/{repo}")
        try:
            with httpx.Client(timeout=self.timeout, headers=headers) as client:
                response = client.get(url, params=params)
                if response.status_code >= 400:
                    self._handle_error(response)
                data = response.json()
        except httpx.TimeoutException as e:
            raise TransientError(f"Git Timeout: {e}") from e
        except httpx.NetworkError as e:
            raise TransientError(f"Git Network Error: {e}") from e
        
        commits: list[GitCommit] = []
        for it in data.get("items", []) or []:
            commits.append(
                GitCommit(
                    sha=it.get("sha", ""),
                    message=(it.get("commit", {}).get("message", "") or ""),
                    url=it.get("html_url", ""),
                )
            )
        return commits
    
    def search_prs_by_commit_sha(self, owner: str, repo: str, issue_key: str, limit: int = 10) -> list[PullRequest]:
        """
        Busca PRs en un repositorio que contengan el commit_sha.
        """
        url = f"{self.base_url}/search/issues"
        params = {
            "q": f"{issue_key} repo:{owner}/{repo} is:pr",
            "order": "desc",
            "per_page": limit,
        }

        log.info(f"Searching PRs for issue_key {issue_key} in {owner}/{repo}")
        try:
            with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
                response = client.get(url, params=params)
                if response.status_code >= 400:
                    self._handle_error(response)
                data = response.json()
        except httpx.TimeoutException as e:
            raise TransientError(f"Git Timeout: {e}") from e
        except httpx.NetworkError as e:
            raise TransientError(f"Git Network Error: {e}") from e

        prs: list[PullRequest] = []
        for it in data.get("items", []) or []:
            prs.append(
                PullRequest(
                    id=str(it.get("number", "")),
                    title=it.get("title", ""),
                    url=it.get("html_url", ""),
                    state=it.get("state", ""),
                )
            )
        return prs

    @retry_policy()
    def search_branches_by_issue_key(
        self,
        owner: str,
        repo: str,
        issue_key: str,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Busca ramas cuyo nombre contenga la issue_key."""
        url = f"{self.base_url}/repos/{owner}/{repo}/branches"
        branches: list[dict[str, Any]] = []
        page = 1
        issue_pattern = self._issue_key_pattern(issue_key)

        log.info(f"Searching branches for issue_key {issue_key} in {owner}/{repo}")
        try:
            with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
                while len(branches) < limit:
                    response = client.get(url, params={"per_page": 100, "page": page})
                    if response.status_code >= 400:
                        self._handle_error(response)

                    items = response.json() or []
                    if not items:
                        break

                    for item in items:
                        name = str(item.get("name", ""))
                        if issue_pattern.search(name):
                            branches.append({
                                "name": name,
                                "sha": item.get("commit", {}).get("sha", ""),
                                "url": item.get("commit", {}).get("url", ""),
                            })
                            if len(branches) >= limit:
                                break
                    page += 1
        except httpx.TimeoutException as e:
            raise TransientError(f"Git Timeout: {e}") from e
        except httpx.NetworkError as e:
            raise TransientError(f"Git Network Error: {e}") from e

        return branches

    @retry_policy()
    def search_prs_by_issue_key(
        self,
        owner: str,
        repo: str,
        issue_key: str,
        limit: int = 10,
    ) -> list[PullRequest]:
        """Busca PRs que mencionen la issue_key en titulo, rama o cuerpo indexado."""
        url = f"{self.base_url}/search/issues"
        params = {
            "q": f"{issue_key} repo:{owner}/{repo} is:pr",
            "order": "desc",
            "per_page": limit,
        }

        log.info(f"Searching PRs for issue_key {issue_key} in {owner}/{repo}")
        try:
            with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
                response = client.get(url, params=params)
                if response.status_code >= 400:
                    self._handle_error(response)
                data = response.json()
        except httpx.TimeoutException as e:
            raise TransientError(f"Git Timeout: {e}") from e
        except httpx.NetworkError as e:
            raise TransientError(f"Git Network Error: {e}") from e

        prs: list[PullRequest] = []
        issue_pattern = self._issue_key_pattern(issue_key)
        for it in data.get("items", []) or []:
            title = str(it.get("title", "") or "")
            if not issue_pattern.search(title):
                log.debug(f"Skipping PR outside {issue_key}: {title[:120]}")
                continue
            prs.append(
                PullRequest(
                    id=str(it.get("number", "")),
                    title=title,
                    url=it.get("html_url", ""),
                    state=it.get("state", ""),
                )
            )
        return prs

    @retry_policy()
    def get_pr_files(self, owner: str, repo: str, pr_number: str | int) -> list[dict[str, Any]]:
        """Obtiene archivos modificados por un PR."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        try:
            with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
                response = client.get(url, params={"per_page": 100})
                if response.status_code >= 400:
                    self._handle_error(response)
                data = response.json()
        except httpx.TimeoutException as e:
            raise TransientError(f"Git Timeout: {e}") from e
        except httpx.NetworkError as e:
            raise TransientError(f"Git Network Error: {e}") from e

        return [
            {
                "filename": item.get("filename", ""),
                "status": item.get("status", ""),
                "additions": item.get("additions", 0),
                "deletions": item.get("deletions", 0),
                "changes": item.get("changes", 0),
                "patch": item.get("patch", ""),
            }
            for item in data or []
        ]

    @retry_policy()
    def compare_branch(
        self,
        owner: str,
        repo: str,
        base_branch: str,
        branch: str,
    ) -> dict[str, Any]:
        """Compara una rama contra base_branch para obtener archivos/commits."""
        compare_ref = f"{quote(base_branch, safe='')}...{quote(branch, safe='')}"
        url = f"{self.base_url}/repos/{owner}/{repo}/compare/{compare_ref}"
        try:
            with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
                response = client.get(url)
                if response.status_code >= 400:
                    self._handle_error(response)
                data = response.json()
        except httpx.TimeoutException as e:
            raise TransientError(f"Git Timeout: {e}") from e
        except httpx.NetworkError as e:
            raise TransientError(f"Git Network Error: {e}") from e

        return {
            "status": data.get("status", ""),
            "ahead_by": data.get("ahead_by", 0),
            "behind_by": data.get("behind_by", 0),
            "commits": [
                {
                    "sha": commit.get("sha", ""),
                    "message": commit.get("commit", {}).get("message", ""),
                    "url": commit.get("html_url", ""),
                }
                for commit in data.get("commits", []) or []
            ],
            "files": [
                {
                    "filename": item.get("filename", ""),
                    "status": item.get("status", ""),
                    "additions": item.get("additions", 0),
                    "deletions": item.get("deletions", 0),
                    "changes": item.get("changes", 0),
                    "patch": item.get("patch", ""),
                }
                for item in data.get("files", []) or []
            ],
        }

    @staticmethod
    def _issue_key_pattern(issue_key: str) -> Any:
        return re.compile(rf"(?<![A-Z0-9]){re.escape(issue_key)}(?!\d)", re.IGNORECASE)
