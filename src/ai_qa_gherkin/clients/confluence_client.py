from __future__ import annotations
import httpx
from ai_qa_gherkin.config import settings
from ai_qa_gherkin.logger import get_logger
from ai_qa_gherkin.models.domain import ConfluencePage
from ai_qa_gherkin.retry import retry_policy, TransientError, PermanentError

log = get_logger("confluence_client")

class ConfluenceClient:
    def __init__(self) -> None:
        self.base_url = settings.confluence_base_url.rstrip("/")
        self.auth = (settings.confluence_email, settings.confluence_api_token)
        self.timeout = settings.confluence_timeout_seconds 

    def _handle_http_error(self, response: httpx.Response) -> None:
        if response.status_code in {429, 502, 503, 504}:
            raise TransientError(f"Confluence transient error: {response.status_code}: {response.text[:250]}")
        if response.status_code >= 400:
            raise PermanentError(f"Confluence permanent error: {response.status_code}: {response.text[:250]}")
    
    def build_page_url(self, item: dict) -> str:
        links = item.get("_links", {}) or {}
        base = links.get("base", "") or ""
        webui = links.get("webui", "") or ""
        page_id = str(item.get("id", "")) or ""

        # Caso ideal: base + webui
        if base and webui:
            return f"{base}{webui}"
        
        # Caso frecuente cloud: solo webui
        if webui:
            if webui.startswith("/"):
                return f"{self.base_url}{webui}"
            return f"{self.base_url}/{webui}"
        
        # Fallback universal por pageId
        if page_id:
            return f"{self.base_url}/pages/viewpage.action?pageId={page_id}"
        
        return ""  # No se pudo construir la URL

    @retry_policy()
    def search_pages_by_text(self, text: str, limit: int = 5) -> list[ConfluencePage]:
        """
        Busca páginas por texto usando CQL.
        """
        url = f"{self.base_url}/rest/api/content/search"
        params = {
            "cql": f'text ~ "{text}"',
            "limit": limit,
            "expand": "body.storage"
        }
        log.info(f"Searching Confluence pages for text: {text}")

        try:
            with httpx.Client(auth=self.auth, timeout=self.timeout) as client:
                r = client.get(url, params=params)
                if r.status_code >= 400:
                    self._handle_http_error(r)
                data = r.json()
        except httpx.TimeoutException as e:
            raise TransientError(f"Confluence request timed out: {e}") from e
        except httpx.NetworkError as e:
            raise TransientError(f"Confluence network error: {e}") from e
        
        pages: list[ConfluencePage] = []
        for it in data.get("results", []) or []:
            page_id = str(it.get("id", "") or "")
            title = str(it.get("title", "") or "")
            content = ((it.get("body", {}) or {}).get("storage", {}) or {}).get("value", "") or ""
            page_url = self.build_page_url(it)

            pages.append(
                ConfluencePage(
                    id=page_id, 
                    title=title, 
                    content=content, url=page_url
                    )
                )
            
        return pages