from __future__ import annotations
import re
import html
from typing import Any
from dotenv import load_dotenv
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models.domain import (ConfluenceContext, GitContext, IssueContext)
from ai_qa_gherkin.clients.confluence_client import ConfluenceClient
from ai_qa_gherkin.clients.jira_client import JiraClient
from ai_qa_gherkin.clients.git_client import GitClient

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
        # Remover URLs (opcional, segÃºn necesidad)
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
        Extrae lÃ­neas de Acceptance Criteria de texto libre.
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
    Recolecta informaciÃ³n de mÃºltiples fuentes (Jira, Confluence, Git)
    y normaliza en un contexto Ãºnico para IA.
    """
    def __init__(self) -> None:
        self.normalizer = TextNormalizer()
        self.jira_client = JiraClient()
        self.confluence_client = ConfluenceClient()
        self.git_client = GitClient()

    def collect_issue_context(self, issue_data: dict[str, Any]) -> IssueContext:
        """
        Normaliza un issue de Jira en IssueContext.

        Entrada tÃ­pica:
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
        Normaliza una pÃ¡gina Confluence en ConfluenceContext.

        Entrada tÃ­pica:
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

        Entrada tÃ­pica:
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
        Fusiona contextos de mÃºltiples fuentes en un Ãºnico objeto
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

    def collect(
        self,
        issue_key: str,
        confluence_search: str = "",
        git_repo: tuple[str, str] | None = None,
        confluence_search_text: str | None = None,
    ) -> dict[str, Any]:
        """
        Recolecta contexto de mÃºltiples fuentes con estrategia robusta.

        Flujo para Confluence:
        1. Buscar en la tarjeta (links)
        2. Buscar en comentarios de la tarjeta
        3. Buscar por parÃ¡metro issue_key en Jira API

        Si falla cualquier paso, continÃºa sin romper.
        """
        log.info(f"Collecting context for {issue_key}")

        jira_client = self.jira_client
        confluence_client = self.confluence_client
        search_text = confluence_search_text if confluence_search_text is not None else confluence_search

        # ========== PASO 1: OBTENER ISSUE JIRA ==========
        jira_issue = None
        try:
            jira_issue = jira_client.get_issue(issue_key)
            normalized_issue = {
                "key": jira_issue.key,
                "issue_key": jira_issue.key,
                "summary": jira_issue.summary,
                "description": jira_issue.description,
                "acceptance_criteria": jira_issue.acceptance_criteria or [],
                "links": jira_issue.links or [],
            }
            log.info(f"âœ“ Fetched Jira issue: {issue_key}")
        except Exception as e:
            log.error(f"Failed to fetch Jira issue {issue_key}: {e}")
            normalized_issue = {
                "key": issue_key,
                "issue_key": issue_key,
                "summary": "",
                "description": "",
                "acceptance_criteria": [],
                "links": [],
                "error": str(e),
            }

        # ========== PASO 2: BUSCAR CONFLUENCE (3 ESTRATEGIAS) ==========
        confluence_data = {}
        try:
            confluence_pages = self._find_confluence_pages(
                jira_client,
                confluence_client,
                issue_key,
                jira_issue,
                search_text=search_text,
            )
            if confluence_pages:
                confluence_data = confluence_pages
                first_page = (confluence_pages.get("pages") or [{}])[0]
                confluence_data.update({
                    "page_id": first_page.get("page_id", ""),
                    "page_title": first_page.get("title", ""),
                    "page_url": first_page.get("url", ""),
                    "content": first_page.get("content", ""),
                    "user_steps": self._extract_user_steps_from_content(first_page.get("content", "")),
                })
                confluence_data["step_count"] = len(confluence_data["user_steps"])
                confluence_data["all_pages"] = confluence_data["pages"]
                log.info(f"Found {len(confluence_pages.get('pages', []))} Confluence pages")
            else:
                log.info("âœ“ No Confluence pages found, continuing...")
        except Exception as e:
            log.warning(f"Confluence search failed: {e}, continuing...")

        # ========== PASO 3: BUSCAR GIT (SI SE PROPORCIONA REPO) ==========
        git_data = {}
        try:
            if git_repo:
                git_data = self._find_git_commits(git_repo, issue_key)
                log.info(f"âœ“ Found Git commits for {issue_key}")
            else:
                log.info("Git repo not provided, skipping Git collection")
        except Exception as e:
            log.warning(f"Git search failed: {e}, continuing...")

        # ========== UNIFICAR CONTEXTO ==========
        merged_context = {
            "issue": normalized_issue,
            "confluence": confluence_data,
            "git": git_data,
            "issue_key": issue_key,
        }

        log.info("Context collection complete")
        return merged_context

    def _collect_jira(self, issue_key: str) -> dict[str, Any]:
        """Compatibilidad: recolecta y normaliza solo Jira."""
        issue = self.jira_client.get_issue(issue_key)
        return {
            "key": issue.key,
            "issue_key": issue.key,
            "summary": self.normalizer.normalize(issue.summary),
            "description": self.normalizer.normalize(issue.description),
            "acceptance_criteria": issue.acceptance_criteria,
            "links": issue.links,
            "raw": issue.raw,
        }

    def _collect_confluence(self, search_text: str, issue_key: str) -> dict[str, Any]:
        """Compatibilidad: busca paginas de Confluence por texto libre."""
        pages = self.confluence_client.search_pages_by_text(search_text, limit=5)
        if not pages:
            return {}

        first = pages[0]
        user_steps = self._extract_user_steps_from_content(first.content)
        return {
            "page_id": first.id,
            "page_title": first.title,
            "page_url": first.url,
            "content": first.content,
            "user_steps": user_steps,
            "step_count": len(user_steps),
            "all_pages": [self._confluence_model_to_dict(page) for page in pages],
            "pages": [self._confluence_model_to_dict(page) for page in pages],
            "issue_key": issue_key,
        }

    def _collect_git(self, issue_key: str, git_repo: tuple[str, str]) -> dict[str, Any]:
        """Compatibilidad: recolecta commits/PRs relacionados al issue."""
        owner, repo = git_repo
        commits = self.git_client.search_commits_by_issue_key(owner, repo, issue_key) or []
        prs = []
        if commits:
            prs = self.git_client.search_prs_by_commit_sha(owner, repo, issue_key) or []

        commit_dicts = [self._model_to_dict(commit) for commit in commits]
        pr_dicts = [self._model_to_dict(pr) for pr in prs]
        changed_files: list[str] = []

        return {
            "owner": owner,
            "repo": repo,
            "commits": commit_dicts,
            "commit_count": len(commit_dicts),
            "prs": pr_dicts,
            "pr_count": len(pr_dicts),
            "changed_files": changed_files,
            "test_scenarios": self._extract_test_scenarios(commit_dicts, changed_files),
        }

    def _find_confluence_pages(self, jira_client, confluence_client, issue_key: str, jira_issue=None, search_text: str = "") -> dict[str, Any]:
        """
        Busca documentacion Confluence usando solo la key ingresada:
        1. Links vinculados a Jira
        2. URLs en comentarios
        3. Busqueda CQL por issue_key
        """
        confluence_pages: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add_page(page: dict[str, Any], source: str, require_issue_key: bool = True) -> None:
            page_id = str(page.get("page_id") or page.get("id") or "")
            url = str(page.get("url") or "")
            if require_issue_key and not self._matches_issue_key(page, issue_key):
                log.debug(
                    f"  Skipping Confluence page outside {issue_key}: "
                    f"{page.get('title') or url or page_id}"
                )
                return
            fingerprint = page_id or url
            if not fingerprint or fingerprint in seen:
                return
            seen.add(fingerprint)
            page["source"] = source
            page["evidence_excerpt"] = self._build_evidence_excerpt(page.get("content", ""))
            confluence_pages.append(page)

        log.info("[Confluence 1/3] Searching for linked pages in issue...")
        for page_ref in self._search_confluence_in_issue_links(jira_client, issue_key, jira_issue):
            page_id = page_ref.get("page_id") or page_ref.get("id")
            if page_id:
                try:
                    page = confluence_client.get_page_by_id(str(page_id))
                    if page:
                        add_page(self._confluence_model_to_dict(page), "jira_link")
                        continue
                except Exception as e:
                    log.debug(f"  Failed to fetch linked Confluence page {page_id}: {e}")
            add_page(page_ref, "jira_link")

        log.info("[Confluence 2/3] Searching in issue comments...")
        try:
            comments = jira_client.get_issue_comments(issue_key) or []
            log.info(f"  Found {len(comments)} comments")

            for comment_idx, comment in enumerate(comments):
                comment_text = comment.get("body", "") or ""
                page_ids = self._extract_confluence_urls_from_text(comment_text)

                if page_ids:
                    log.info(f"  Found {len(page_ids)} Confluence URLs in comment {comment_idx}")

                for page_id in page_ids:
                    try:
                        page = confluence_client.get_page_by_id(page_id)
                        if page:
                            add_page(self._confluence_model_to_dict(page), "jira_comment")
                            log.info(f"  Fetched page {page_id}: {page.title or 'Unknown'}")
                    except Exception as e:
                        log.debug(f"  Failed to fetch page {page_id}: {e}")

        except Exception as e:
            log.debug(f"  Strategy 2 failed: {e}")

        log.info(f"[Confluence 3/3] Searching Confluence by issue_key '{issue_key}'...")
        try:
            for page in self._search_confluence_by_issue_key(confluence_client, issue_key):
                add_page(page, "confluence_search")
        except Exception as e:
            log.debug(f"  Strategy 3 failed: {e}")

        for query in self._build_confluence_queries(issue_key, jira_issue, search_text):
            log.info(f"[Confluence extra] Searching Confluence by text '{query[:60]}'...")
            try:
                require_issue_key = query != search_text
                for page in confluence_client.search_pages_by_text(query, limit=5):
                    add_page(
                        self._confluence_model_to_dict(page),
                        "confluence_search",
                        require_issue_key=require_issue_key,
                    )
            except Exception as e:
                log.debug(f"  Extra Confluence search failed for '{query}': {e}")

        if confluence_pages:
            log.info(f"Found {len(confluence_pages)} unique Confluence pages")
            return {"pages": confluence_pages}

        log.info("No Confluence pages found after all strategies")
        return {}

    def _build_confluence_queries(self, issue_key: str, jira_issue: Any, search_text: str) -> list[str]:
        """Construye busquedas adicionales sin repetir la key del issue."""
        candidates = []
        if search_text:
            candidates.append(search_text)
        if jira_issue and getattr(jira_issue, "summary", ""):
            candidates.append(str(jira_issue.summary))

        seen = {issue_key.lower()}
        result = []
        for candidate in candidates:
            normalized = self.normalizer.normalize(candidate)
            if normalized and normalized.lower() not in seen:
                seen.add(normalized.lower())
                result.append(normalized)
        return result

    def _matches_issue_key(self, page: dict[str, Any], issue_key: str) -> bool:
        """Valida coincidencia exacta de issue para resultados de busqueda CQL."""
        haystack = " ".join(
            str(page.get(field, "") or "")
            for field in ("page_id", "id", "title", "url", "content")
        )
        return re.search(rf"(?<![A-Z0-9-]){re.escape(issue_key)}(?![A-Z0-9-])", haystack, re.IGNORECASE) is not None

    def _search_confluence_in_issue_links(self, jira_client, issue_key: str, jira_issue) -> list[dict[str, Any]]:
        """Busca links de Confluence vinculados a la tarjeta Jira."""
        pages: list[dict[str, Any]] = []
        link_candidates: list[str] = []

        if jira_issue and hasattr(jira_issue, "links") and jira_issue.links:
            link_candidates.extend(str(link) for link in jira_issue.links)

        try:
            remote_links = jira_client.get_remote_links(issue_key)
        except Exception as e:
            log.debug(f"  Remote links lookup failed: {e}")
            remote_links = []

        for remote_link in remote_links:
            link_candidates.append(remote_link.get("url", ""))
            link_candidates.append(remote_link.get("title", ""))

        if jira_issue and getattr(jira_issue, "description", ""):
            link_candidates.append(str(jira_issue.description))

        if not link_candidates:
            log.debug("  No issue links found")
            return pages

        log.info(f"  Checking {len(link_candidates)} issue link candidates...")

        for link in link_candidates:
            link_str = str(link)
            if "http" in link_str and ("confluence" in link_str.lower() or "wiki" in link_str.lower()):
                page_id = self._extract_confluence_page_id(link_str)
                if page_id:
                    pages.append({"page_id": page_id, "id": page_id, "url": link_str})

        return pages

    def _search_confluence_by_issue_key(self, confluence_client, issue_key: str) -> list[dict[str, Any]]:
        """Busca en Confluence por la key de Jira ingresada por el usuario."""
        try:
            results = confluence_client.search_pages_by_text(issue_key, limit=10)
            return [self._confluence_model_to_dict(page) for page in results]
        except Exception as e:
            log.debug(f"  Confluence search failed: {e}", exc_info=True)
            return []

    def _confluence_model_to_dict(self, page) -> dict[str, Any]:
        """Convierte ConfluencePage a la estructura esperada por el analizador."""
        return {
            "page_id": page.id,
            "id": page.id,
            "title": page.title,
            "content": page.content,
            "url": page.url,
        }

    def _build_evidence_excerpt(self, content: str, max_chars: int = 280) -> str:
        """Crea un extracto corto y sanitizado para trazabilidad."""
        clean = self.normalizer.normalize(re.sub(r"<[^>]+>", " ", html.unescape(str(content))))
        return clean[:max_chars]

    def _model_to_dict(self, item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return item
        if hasattr(item, "model_dump"):
            return dict(item.model_dump())
        if hasattr(item, "dict"):
            return dict(item.dict())
        return dict(getattr(item, "__dict__", {}))

    def _extract_user_steps_from_content(self, content: str) -> list[str]:
        clean = self._build_evidence_excerpt(content, max_chars=4000)
        steps = []
        for part in re.split(r"[\n.;]", clean):
            part = part.strip(" -*\t")
            if len(part) >= 8:
                steps.append(part)
        return self.normalizer.remove_duplicates(steps[:10])

    def _extract_test_scenarios(self, commits: list[dict[str, Any]], changed_files: list[str]) -> list[str]:
        scenarios = []
        for commit in commits:
            message = str(commit.get("message", ""))
            if any(word in message.lower() for word in ["fix", "bug", "feat", "test", "security", "validation"]):
                scenarios.append(f"Validar cambio: {message[:100]}")
        for file_path in changed_files:
            if "test" in file_path.lower():
                scenarios.append(f"Ejecutar cobertura asociada a {file_path}")
        return self.normalizer.remove_duplicates(scenarios)
    def _extract_confluence_urls_from_text(self, text: str) -> list[str]:
        """Extrae page_ids de URLs de Confluence en texto."""
        page_ids = []

        # âœ… PatrÃ³n: https://imed.atlassian.net/wiki/spaces/KB/pages/4612161537
        urls = re.findall(
            r'https?://[^\s\)]+(?:confluence|wiki)[^\s\)]*?/pages/(\d+)',
            text,
            re.IGNORECASE
        )

        for page_id in urls:
            if page_id not in page_ids:
                page_ids.append(page_id)
                log.debug(f"  Extracted page_id from URL: {page_id}")

        return page_ids

    def _find_git_commits(self, git_repo: tuple[str, str], issue_key: str) -> dict[str, Any]:
        """
        Busca commits en Git vinculados al issue_key.
        """
        owner, repo = git_repo

        commits = []

        try:
            # Buscar commits que mencionen el issue_key
            commits = self.git_client.search_commits_by_issue_key(owner, repo, issue_key) or []
            log.info(f"  Found {len(commits)} commits mentioning {issue_key}")
        except Exception as e:
            log.debug(f"  Git search failed: {e}")

        if commits:
            prs = self.git_client.search_prs_by_commit_sha(owner, repo, issue_key) or []
            commit_dicts = [self._model_to_dict(commit) for commit in commits]
            pr_dicts = [self._model_to_dict(pr) for pr in prs]
            return {
                "commits": commit_dicts,
                "commit_count": len(commit_dicts),
                "owner": owner,
                "repo": repo,
                "prs": pr_dicts,
                "pr_count": len(pr_dicts),
                "changed_files": [],
                "test_scenarios": self._extract_test_scenarios(commit_dicts, []),
            }

        return {}

    def _extract_confluence_page_id(self, link: str | dict) -> str | None:
        """Extrae page_id de un link de Confluence."""
        link_str = str(link)

        # âœ… PatrÃ³n 1: /wiki/spaces/KB/pages/4612161537
        match = re.search(r'/pages/(\d+)', link_str)
        if match:
            return match.group(1)

        # PatrÃ³n 2: page_id=4612161537
        match = re.search(r'page_id=(\d+)', link_str)
        if match:
            return match.group(1)

        # âœ… PatrÃ³n 3: URL URL-encoded con ?xpis=...
        # Extraer todo antes del ?
        base_url = link_str.split('?')[0]
        match = re.search(r'/pages/(\d+)', base_url)
        if match:
            return match.group(1)

        log.debug(f"Could not extract page_id from: {link_str[:80]}")
        return None

    def _parse_ac_text(self, ac_text: str) -> list[str]:
        """
        Parsea AC en diferentes formatos:
        - Escenario X: ...
        - AC1: / AC 1: / Criterio 1:
        - Given/When/Then
        - - Bullet points
        - * Asteriscos
        """
        if not ac_text:
            return []

        criteria = []
        lines = ac_text.split("\n")

        current_scenario = ""

        for line in lines:
            line_stripped = line.strip()

            if not line_stripped:
                if current_scenario:
                    criteria.append(current_scenario)
                    current_scenario = ""
                continue

            # Detectar inicio de escenario/criterio
            if any(marker in line_stripped.lower() for marker in [
                "escenario", "ac ", "ac1", "ac2", "criterio", "requirement"
            ]):
                if current_scenario:
                    criteria.append(current_scenario)
                current_scenario = line_stripped

            # Detectar Gherkin steps (Dado/Cuando/Entonces / Given/When/Then)
            elif any(marker in line_stripped.lower() for marker in [
                "dado ", "cuando ", "entonces ",
                "given ", "when ", "then "
            ]):
                if current_scenario:
                    current_scenario += f" {line_stripped}"
                else:
                    current_scenario = line_stripped

            # Detectar bullet points
            elif line_stripped.startswith(("-", "*", "â€¢", "â†’")):
                cleaned = line_stripped.lstrip("-*â€¢â†’").strip()
                if cleaned and len(cleaned) > 5:
                    if current_scenario:
                        current_scenario += f" | {cleaned}"
                    else:
                        current_scenario = cleaned

        # Agregar Ãºltimo
        if current_scenario:
            criteria.append(current_scenario)

        # Normalizar y filtrar
        criteria = [c.strip() for c in criteria if len(c.strip()) > 10]
        return self.normalizer.remove_duplicates(criteria)

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
        """Combina criterios de aceptaciÃ³n."""
        return issue.get("acceptance_criteria", [])
