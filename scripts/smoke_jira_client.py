from __future__ import annotations

import json
import sys

from ai_qa_gherkin.clients.jira_client import JiraClient


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/smoke_jira_client.py <ISSUE_KEY>")
        print("Ejemplo: python scripts/smoke_jira_client.py DYF-4325")
        return 1

    issue_key = sys.argv[1].strip()
    client = JiraClient()

    issue = client.get_issue(issue_key)

    print("\n=== JIRA ISSUE (NORMALIZADA) ===")
    print(f"Key: {issue.key}")
    print(f"Summary: {issue.summary}")
    print(f"Links: {issue.links}")
    print(f"Description chars: {len(issue.description)}")
    print(f"AC chars: {len(issue.acceptance_criteria)}")

    print("\n--- Acceptance Criteria (preview 1200 chars) ---")
    print(issue.acceptance_criteria[:1200] if issue.acceptance_criteria else "(vacío)")

    raw = client.get_issue_raw(issue_key)
    print("\n=== RAW FIELDS KEYS ===")
    print(", ".join(sorted((raw.get("fields") or {}).keys())))

    print("\n=== RAW SAMPLE (project/issuetype/labels) ===")
    sample = {
        "project": (raw.get("fields") or {}).get("project"),
        "issuetype": (raw.get("fields") or {}).get("issuetype"),
        "labels": (raw.get("fields") or {}).get("labels"),
    }
    print(json.dumps(sample, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())