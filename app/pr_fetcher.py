import httpx
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


async def fetch_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """
    Fetch unified diff for a PR using GitHub API.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {"Accept": "application/vnd.github.v3.diff"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers, timeout=30.0)
        r.raise_for_status()
        return r.text
