from __future__ import annotations
import re
from typing import Any
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models import (ConfluenceContext, GitContext, IssueContext)

log = get_logger("collector_service")

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