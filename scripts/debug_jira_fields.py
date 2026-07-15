from ai_qa_gherkin.clients.jira_client import JiraClient
import json

c = JiraClient()
raw = c.get_issue_raw("DYF-4325")  # cambia por una issue real
print(json.dumps(raw.get("fields", {}), indent=2, ensure_ascii=False))