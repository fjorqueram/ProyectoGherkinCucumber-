from __future__ import annotations
import sys
from ai_qa_gherkin.clients.confluence_client import ConfluenceClient

def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/smoke_confluence_client.py <TEXTO_BUSQUEDA> [LIMIT]")
        print('Ejemplo: python scripts/smoke_confluence_client.py "DYF-4325" 5')
        return 1

    query = sys.argv[1].strip()
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    client = ConfluenceClient()
    pages = client.search_pages_by_text(query, limit=limit)

    print("\n=== CONFLUENCE SMOKE ===")
    print(f"Query: {query}")
    print(f"Limit: {limit}")
    print(f"Found: {len(pages)}")

    for i, p in enumerate(pages, start=1):
        print(f"\n[{i}] id={p.id}")
        print(f"title: {p.title}")
        print(f"url:   {p.url}")
        print(f"content chars: {len(p.content)}")
        preview = (p.content or "").replace("\n", " ").strip()
        print(f"preview: {preview[:220]}{'...' if len(preview) > 220 else ''}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())