from __future__ import annotations
import re
from typing import Any
from dotenv import load_dotenv
import os
import requests
from typing import Any
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models import (ConfluenceContext, GitContext, IssueContext)

log = get_logger("collector_service")
load_dotenv()

class TextNormalizer:
    """Normaliza y limpia texto (quita ruido, duplicados, espacios extras)."""

    @staticmethod
    def normalize(text: str | None) -> str:
        """Limpia texto: espacios, saltos extra, caracteres especiales."""
        if not text:
            return ""
        
        # Remover espacios extra
        text = re.sub(r"\s+", " ", text).strip()
        # Remover URLs (opcional, según necesidad)
        # text = re.sub(r'https?://\S+', '', text)
        return text
    
    @staticmethod
    def remove_duplicates(items: list[str]) -> list[str]:
        """Elimina duplicados manteniendo orden."""
        seen = set()
        result = []
        for item in items:
            normalized = item.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(item.strip())
        return result
    
    @staticmethod
    def extract_ac_lines(text: str) -> list[str]:
        """
        Extrae líneas de Acceptance Criteria de texto libre.
        Busca patrones como:
        - AC1: ...
        - Criterio 1: ...
        - - ...
        """
        if not text:
            return []
        
        lines = text.split("\n")
        criteria = []

        for line in lines:
            line = line.strip()
            if re.match(r"^(AC\d+|Criterio\s+\d+|[-*])\s*[:\s]", line, re.IGNORECASE):
                # Remover prefijo
                cleaned = re.sub(r"^(AC\d+|Criterio\s+\d+|[-*])\s*[:]*\s*","",line,flags=re.IGNORECASE,)
                if cleaned:
                    criteria.append(cleaned)

        return TextNormalizer.remove_duplicates(criteria)

class ContextCollector:
    """
    Recolecta información de múltiples fuentes (Jira, Confluence, Git)
    y normaliza en un contexto único para IA.
    """
    def __init__(self) -> None:
        self.normalizer = TextNormalizer()

    def collect_issue_context(self, issue_data: dict[str, Any]) -> IssueContext:
        """
        Normaliza un issue de Jira en IssueContext.

        Entrada típica:
        {
            'key': 'DYF-4307',
            'summary': '...',
            'description': '...',
            'customfield_10XXX': 'AC1: ...\\nAC2: ...',
            'labels': [...],
            ...
        }
        """
        log.info(f"Collecting issue context from {issue_data.get('key', 'unknown')}")

        issue_key = issue_data.get("key", "")
        summary = self.normalizer.normalize(issue_data.get("summary", ""))
        description = self.normalizer.normalize(issue_data.get("description", ""))

        # Extraer acceptance criteria
        ac_text = issue_data.get("customfield_acceptance_criteria", "")
        if not ac_text:
            ac_text = issue_data.get("description", "")

        acceptance_criteria = self.normalizer.extract_ac_lines(ac_text)

        # Extraer labels
        labels = issue_data.get("labels", [])
        labels = self.normalizer.remove_duplicates(labels)

        # Extraer links relacionados
        links = []
        for link in issue_data.get("issuelinks", []):
            linked_key = (link.get("outwardIssue", {}).get("key") or link.get("inwardIssue", {}).get("key"))
            if linked_key:
                links.append(linked_key)
            links = self.normalizer.remove_duplicates(links)

        return IssueContext(
            issue_key=issue_key,
            summary=summary,
            description=description,
            acceptance_criteria=acceptance_criteria,
            links=links,
            raw=issue_data,
        )
    
    def collect_confluence_context(self, page_data: dict[str, Any]) -> ConfluenceContext:
        """
        Normaliza una página Confluence en ConfluenceContext.

        Entrada típica:
        {
            'id': '123456',
            'title': 'Specification',
            'url': 'https://wiki.../pages/123456',
            'body': { 'storage': { 'value': '<p>content</p>' } },
            ...
        }
        """
        log.info(f"Collecting confluence context from {page_data.get('id', 'unknown')}")

        page_id = page_data.get("id", "")
        title = self.normalizer.normalize(page_data.get("title", ""))
        url = page_data.get("_links", {}).get("self", "")

        # Extraer contenido (puede ser HTML o plaintext)
        content = ""
        if "body" in page_data:
            body = page_data.get("body", {})
            if isinstance(body, dict) and "storage" in body:
                content = body["storage"].get("value", "")
            elif isinstance(body, dict) and "plain_text" in body:
                content = body["plain_text"].get("value", "")
            elif isinstance(body, str):
                content = body

        content = self.normalizer.normalize(content)

        return ConfluenceContext(
            page_id=page_id,
            title=title,
            url=url,
            content=content,
            raw=page_data,
        )

    def collect_git_context(self, git_data: dict[str, Any]) -> GitContext:
        """
        Normaliza datos de Git (commits, PRs, diffs) en GitContext.

        Entrada típica:
        {
            'repo_url': 'https://github.com/org/repo',
            'branch': 'main',
            'commit_sha': 'abc123',
            'changed_files': ['src/main.py', 'tests/test.py'],
            'diff_summary': '...',
            ...
        }
        """
        log.info(f"Collecting git context from {git_data.get('repo_url', 'unknown')}")

        repo_url = git_data.get("repo_url", "")
        branch = self.normalizer.normalize(git_data.get("branch", ""))
        commit_sha = git_data.get("commit_sha", "")
        changed_files = git_data.get("changed_files", [])
        changed_files = self.normalizer.remove_duplicates(changed_files)

        diff_summary = self.normalizer.normalize(git_data.get("diff_summary", ""))

        return GitContext(
            repo_url=repo_url,
            branch=branch,
            commit_sha=commit_sha,
            changed_files=changed_files,
            diff_summary=diff_summary,
            raw=git_data,
        )      
    
    def merge_contexts(self, issue: IssueContext | None = None, confluence: ConfluenceContext | None = None, git: GitContext | None = None,) -> dict[str, Any]:
        """
        Fusiona contextos de múltiples fuentes en un único objeto
        listo para procesamiento por IA.

        Retorna un dict normalizado con prioridad: Jira > Confluence > Git.
        """
        log.info("Merging contexts from multiple sources")

        merged = {
            "issue": issue.model_dump() if issue else None,
            "confluence": confluence.model_dump() if confluence else None,
            "git": git.model_dump() if git else None,
            "primary_scope": "",
            "combined_acceptance_criteria": [],
            "all_labels": [],
            "related_issue": [],
        }

        # Scope principal (de issue si existe)
        if issue:
            merged["primary_scope"] = issue.summary
            merged["related_issue"] = issue.links

        # AC combinadas
        ac_set = set()
        if issue:
            ac_set.update(issue.acceptance_criteria)
        merged["combined_acceptance_criteria"].extend(ac_set)

        # Labels combinados
        label_set = set()
        if issue:
            label_set.update(issue.links)
        merged["all_labels"].extend(label_set)

        return merged
    
    def collect(self, issue: dict[str, Any] | None = None, confluence: dict[str, Any] | None = None, git: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Recolecta y normaliza contexto de múltiples fuentes.
        
        Si issue contiene "issue_key", trae datos reales de Jira.
        """
        log.info("Collecting context from multiple sources")

        # Si se pasa issue_key, traer de Jira
        if issue and "issue_key" in issue and not issue.get("summary"):
            issue = self._fetch_from_jira(issue["issue_key"])

        # Normalizar cada fuente
        normalized_issue = self._normalize_issue(issue)
        normalized_confluence = self._normalize_confluence(confluence) or {}
        normalized_git = self._normalize_git(git) or {}

        # Unificar en contexto merged
        merged_context: dict[str, Any] = {
            "issue": normalized_issue,
            "confluence": normalized_confluence,
            "git": normalized_git,
            "primary_scope": self._extract_primary_scope(normalized_issue),
            "combined_acceptance_criteria": self._combine_acceptance_criteria(
                normalized_issue
            ),
            "issue_key": normalized_issue.get("issue_key", "UNKNOWN"),
        }

        log.info("Context collection complete")
        return merged_context
    
    def _fetch_from_jira(self, issue_key: str) -> dict[str, Any]:
        """Trae datos reales de Jira API."""
        jira_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
        jira_email = os.getenv("JIRA_EMAIL", "")
        jira_token = os.getenv("JIRA_API_TOKEN", "")

        if not jira_url or not jira_email or not jira_token:
            log.warning(f"Jira credentials not configured, using mock data for {issue_key}")
            return {"issue_key": issue_key, "summary": f"Mock: {issue_key}"}

        try:
            url = f"{jira_url}/rest/api/3/issues/{issue_key}"
            response = requests.get(
                url,
                auth=(jira_email, jira_token),
                headers={"Accept": "application/json"}
            )

            if response.status_code == 200:
                jira_data = response.json()
                fields = jira_data.get("fields", {})
                
                # Extraer criterios de aceptación del campo Description o custom field
                description = fields.get("description", "")
                ac = self._extract_ac_from_description(description)

                log.info(f"Fetched {issue_key} from Jira: {fields.get('summary')}")
                
                return {
                    "issue_key": issue_key,
                    "summary": fields.get("summary", ""),
                    "description": description or "",
                    "acceptance_criteria": ac,
                    "status": fields.get("status", {}).get("name", ""),
                    "assignee": fields.get("assignee", {}).get("displayName", ""),
                    "priority": fields.get("priority", {}).get("name", ""),
                }
            else:
                log.error(f"Jira API error: {response.status_code} - {response.text}")
                return {"issue_key": issue_key, "summary": f"Error fetching {issue_key}"}

        except Exception as e:
            log.error(f"Error fetching from Jira: {str(e)}")
            return {"issue_key": issue_key, "summary": f"Error: {str(e)}"}
        
    def _extract_ac_from_description(self, description: str) -> list[str]:
        """Extrae criterios de aceptación del description."""
        if not description:
            return []
        
        criteria = []
        lines = description.split("\n")
        
        in_ac_section = False
        for line in lines:
            line = line.strip()
            
            # Buscar sección de AC
            if line.lower().startswith("acceptance criteria") or line.lower().startswith("criterios de aceptación"):
                in_ac_section = True
                continue
            
            # Si estamos en sección de AC
            if in_ac_section:
                if line.startswith("-") or line.startswith("*") or line.startswith("•"):
                    criteria.append(line.lstrip("-*•").strip())
                elif line == "":
                    continue
                elif line.startswith(("##", "###", "Given", "When", "Then")):
                    break
        
        return criteria


    def _normalize_issue(self, issue: dict[str, Any] | None) -> dict[str, Any]:
        """Normaliza datos de Jira issue."""
        if not issue:
            return {
                "issue_key": "UNKNOWN",
                "summary": "",
                "description": "",
                "acceptance_criteria": [],
            }

        return {
            "issue_key": issue.get("issue_key", ""),
            "summary": issue.get("summary", ""),
            "description": issue.get("description", ""),
            "acceptance_criteria": issue.get("acceptance_criteria", []),
            "issue_type": issue.get("issue_type", ""),
            "labels": issue.get("labels", []),
            "priority": issue.get("priority", ""),
        }

    def _normalize_confluence(self, confluence: dict[str, Any] | None) -> dict[str, Any] | None:
        """Normaliza datos de Confluence."""
        if not confluence:
            return None

        return {
            "page_id": confluence.get("page_id", ""),
            "title": confluence.get("title", ""),
            "content": confluence.get("content", ""),
            "url": confluence.get("url", ""),
        }

    def _normalize_git(self, git: dict[str, Any] | None) -> dict[str, Any] | None:
        """Normaliza datos de Git."""
        if not git:
            return None

        return {
            "commit_sha": git.get("commit_sha", ""),
            "changed_files": git.get("changed_files", []),
            "diff_summary": git.get("diff_summary", ""),
            "branch": git.get("branch", ""),
            "author": git.get("author", ""),
        }

    def _extract_primary_scope(self, issue: dict[str, Any]) -> str:
        """Extrae el scope principal del issue."""
        summary = issue.get("summary", "")
        return summary[:100]  # Primeros 100 caracteres

    def _combine_acceptance_criteria(self, issue: dict[str, Any]) -> list[str]:
        """Combina criterios de aceptación."""
        return issue.get("acceptance_criteria", [])