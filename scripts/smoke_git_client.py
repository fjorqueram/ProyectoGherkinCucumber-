from __future__ import annotations

import argparse
from ai_qa_gherkin.clients.git_client import GitClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for GitClient (GitHub API).")
    parser.add_argument("--owner", required=True, help="GitHub owner/org, e.g. imed")
    parser.add_argument("--repo", required=True, help="GitHub repo, e.g. cme-motor")
    parser.add_argument("--issue-key", required=True, help="Issue key, e.g. DYF-4325")
    parser.add_argument("--limit", type=int, default=10, help="Max results per search")
    args = parser.parse_args()

    client = GitClient()

    print("\n=== GIT SMOKE ===")
    print(f"Repo: {args.owner}/{args.repo}")
    print(f"Issue key: {args.issue_key}")
    print(f"Limit: {args.limit}")

    commits = client.search_commits_by_issue_key(
        owner=args.owner,
        repo=args.repo,
        issue_key=args.issue_key,
        limit=args.limit,
    )
    prs = client.search_prs_by_commit_sha(
        owner=args.owner,
        repo=args.repo,
        issue_key=args.issue_key,
        limit=args.limit,
    )

    print(f"\nCommits found: {len(commits)}")
    for i, c in enumerate(commits, start=1):
        first_line = (c.message or "").splitlines()[0] if c.message else ""
        print(f"[C{i}] {c.sha[:10]} | {first_line}")
        print(f"     {c.url}")

    print(f"\nPRs found: {len(prs)}")
    for i, pr in enumerate(prs, start=1):
        print(f"[PR{i}] #{pr.id} [{pr.state}] {pr.title}")
        print(f"      {pr.url}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())