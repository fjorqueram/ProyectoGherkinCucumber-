import os
import requests

token = os.getenv("GIT_TOKEN")
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
}

tests = [
    ("USER", "https://api.github.com/user"),
    ("REPO", "https://api.github.com/repos/imed/cme-cme"),
    ("COMMITS", "https://api.github.com/repos/imedcl/cme-cme/commits?per_page=1"),
]

for name, url in tests:
    r = requests.get(url, headers=headers, timeout=20)
    print(f"\n{name} -> {r.status_code}")
    print(r.text[:250])