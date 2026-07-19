from __future__ import annotations
from typing import Any
import httpx
from ai_qa_gherkin.config import settings
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models.domain import JiraIssue
from ai_qa_gherkin.retry import retry_policy, TransientError, PermanentError

log = get_logger("jira_client")

class JiraClient:
    def __init__(self) -> None:
        self.base_url = settings.jira_base_url.rstrip("/")
        self.auth = (settings.jira_email, settings.jira_api_token)
        self.timeout = settings.jira_timeout_seconds

    def _handle_http_error(self, response: httpx.Response) -> None:
        code = response.status_code
        msg = f"Jira error: {code} - {response.text[:300]}"

        if code in {429, 502, 503, 504}:
            raise TransientError(msg)
        if code >= 400:
            raise PermanentError(msg)
        
    @retry_policy()
    def get_issue_raw(self, issue_key: str) -> dict[str, Any]:
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"

        # Pedimos solo lo necesario. Ojo: customfield_10000 NO es AC en tu caso.
        params = {"fields": "summary,description,issuelinks,labels,project,issuetype"}

        log.info(f"Fetching Jira issue {issue_key}")

        try:
            with httpx.Client(auth=self.auth, timeout=self.timeout) as client:
                r = client.get(url, params=params)
                if r.status_code >= 400:
                    self._handle_http_error(r)
                data = r.json()
                if not isinstance(data, dict):
                    raise PermanentError(f"Invalid Jira payload for {issue_key}")
                return data
        except httpx.TimeoutException as e:
            raise TransientError(f"Jira request timed out: {e}") from e
        except httpx.NetworkError as e:
            raise TransientError(f"Jira network error: {e}") from e
        
    def _extract_text_from_adf(self, node: Any) -> str:
        """Extrae texto plano de ADF."""
        if isinstance(node, dict):
            current = node.get("text", "")
            content = node.get("content", []) or []
            return current + "".join(self._extract_text_from_adf(c) for c in content)
        if isinstance(node, list):
            return "".join(self._extract_text_from_adf(x) for x in node)
        return ""
    
    def _extract_gherkin_codeblocks_from_adf(self, adf: dict[str, Any]) -> str:
        """Devuelve texto de codeBlocks language=gherkin (si hay varios, concatena)."""
        blocks: list[str] = []

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                if node.get("type") == "codeBlock":
                    attrs = node.get("attrs", {}) or {}
                    lang = (attrs.get("language") or "").lower()
                    if lang == "gherkin":
                        text = self._extract_text_from_adf(node.get("content", [])).strip()
                        if text:
                            blocks.append(text)

                for c in node.get("content", []) or []:
                    walk(c)
            
            elif isinstance(node, list):
                for x in node:
                    walk(x)

        walk(adf)
        return "\n\n".join(blocks).strip()
    
    def _extract_ac_section_from_plain_text(self, description_text: str) -> str:
        """
        Fallback si no hay codeBlock gherkin:
        intenta cortar desde 'CRITERIOS DE ACEPTACIÓN'.
        """

        if not description_text:
            return ""
        
        normalized = description_text.lower()
        markers = [
            "criterios de aceptación",
            "criterios de aceptacion",
            "acceptance criteria",
        ]

        idx = -1
        for m in markers:
            idx = normalized.find(m)
            if idx != -1:
                break

        if idx == -1:
            return ""
        
        return description_text[idx:].strip()
    
    def _extract_links(self, fields: dict[str, Any]) -> list[str]:
        links: list[str] = []

        for item in fields.get("issuelinks", []) or []:
            inward = (item.get("inwardIssue") or {})
            outward = (item.get("outwardIssue") or {})
            if inward.get("key"):
                links.append(str(inward["key"]))
            if outward.get("key"):
                links.append(str(outward["key"]))
        return sorted(set(links))

    def get_issue(self, issue_key: str) -> JiraIssue:
        """
        Siempre retorna JiraIssue o lanza excepción.
        (evita Pylance reportReturnType)
        """

        data = self.get_issue_raw(issue_key)
        if not isinstance(data, dict):
            raise PermanentError(f"Invalid Jira response for {issue_key}")
        
        fields = data.get("fields", {}) or {}
        if not isinstance(fields, dict):
            raise PermanentError(f"Missing fields in Jira response for {issue_key}")
        
        summary = str(fields.get("summary") or "")
        desc_adf = fields.get("description", {}) or {}
        description = self._extract_text_from_adf(desc_adf).strip()

        # 1) preferimos codeBlock gherkin
        acceptance_criteria = self._extract_gherkin_codeblocks_from_adf(desc_adf)

        # 2) fallback por sección textual
        if not acceptance_criteria:
            acceptance_criteria = self._extract_ac_section_from_plain_text(description)

        links = self._extract_links(fields)

        return JiraIssue(
            key=str(data.get("key") or issue_key),
            summary=summary,
            description=description,
            acceptance_criteria=acceptance_criteria,
            links=links,
            raw=data,
        )
    
    def get_issue_comments(self, issue_key: str) -> list[dict]:
        """Obtiene comentarios de un issue."""
        try:
            url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
            params = {"fields": "comment"}
            
            log.info(f"Fetching comments for {issue_key}")
            
            with httpx.Client(auth=self.auth, timeout=self.timeout) as client:
                r = client.get(url, params=params)
                if r.status_code >= 400:
                    self._handle_http_error(r)
                
                issue_data = r.json()
                comments = issue_data.get('fields', {}).get('comment', {}).get('comments', [])
                
                # ✅ CONVERTIR A STRING SI ES NECESARIO
                result = []
                for c in comments:
                    body = c.get('body', '')
                    
                    # Si body es dict (ADF), extraer texto
                    if isinstance(body, dict):
                        body = self._extract_text_from_adf(body)
                    
                    result.append({'body': str(body)})
                
                return result
        except Exception as e:
            log.warning(f"Failed to get comments for {issue_key}: {e}")
            return []

    @retry_policy()
    def get_remote_links(self, issue_key: str) -> list[dict[str, str]]:
        """Obtiene enlaces remotos asociados a una tarjeta Jira."""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/remotelink"
        log.info(f"Fetching remote links for {issue_key}")

        try:
            with httpx.Client(auth=self.auth, timeout=self.timeout) as client:
                r = client.get(url)
                if r.status_code >= 400:
                    self._handle_http_error(r)
                data = r.json()
        except httpx.TimeoutException as e:
            raise TransientError(f"Jira request timed out: {e}") from e
        except httpx.NetworkError as e:
            raise TransientError(f"Jira network error: {e}") from e

        links: list[dict[str, str]] = []
        for item in data if isinstance(data, list) else []:
            obj = item.get("object", {}) or {}
            links.append(
                {
                    "url": str(obj.get("url") or ""),
                    "title": str(obj.get("title") or ""),
                }
            )
        return links

    def get_confluence_page(self, page_id: str) -> dict[str, Any] | None:
        """
        Obtiene una página de Confluence por ID.
        
        Puede recibir:
        - page_id: "4612161537"
        - Retorna: dict con page_id, title, content, url
        """
        try:
            log.info(f"Fetching Confluence page {page_id}")
            
            # ✅ Construir URL de Confluence API
            # Formato: https://imed.atlassian.net/wiki/api/v2/pages/{page_id}
            confluence_url = f"https://imed.atlassian.net/wiki/api/v2/pages/{page_id}"
            
            params = {
                "body-format": "storage"  # Obtener en formato HTML/storage
            }
            
            with httpx.Client(auth=self.auth, timeout=self.timeout) as client:
                r = client.get(confluence_url, params=params)
                
                if r.status_code == 404:
                    log.warning(f"Confluence page {page_id} not found")
                    return None
                
                if r.status_code >= 400:
                    log.warning(f"Failed to get Confluence page: {r.status_code}")
                    return None
                
                page_data = r.json()
                
                # ✅ Extraer campos relevantes
                page = {
                    "page_id": page_id,
                    "id": page_id,
                    "title": page_data.get("title", ""),
                    "content": page_data.get("body", {}).get("storage", {}).get("value", ""),
                    "url": page_data.get("_links", {}).get("webui", ""),
                }
                
                log.info(f"✓ Fetched Confluence page: {page['title']}")
                return page
                
        except Exception as e:
            log.warning(f"Failed to get Confluence page {page_id}: {e}")
            return None

    def search_related_documentation(self, issue_key: str) -> list[dict]:
        """Busca documentación relacionada a un issue."""
        try:
            log.info(f"Searching related documentation for {issue_key}")
            # Por ahora retorna vacío, se puede mejorar después
            return []
        except Exception as e:
            log.debug(f"Documentation search failed: {e}")
            return []
