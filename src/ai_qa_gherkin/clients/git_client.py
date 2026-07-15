from __future__ import annotations
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
