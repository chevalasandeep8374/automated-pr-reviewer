import os
import httpx
from typing import List, Dict

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def format_comment_body(f: Dict) -> str:
    title = f.get("issue_title", "Suggestion")
    explanation = f.get("explanation", "")
    suggestion = f.get("suggestion", "")
    confidence = f.get("confidence", 0.5)
    return f"**{title}**  · *confidence: {confidence:.2f}*\n\n{explanation}\n\n**Suggestion:** {suggestion}"

async def post_review_to_github(owner: str, repo: str, pr_number: int, findings: List[Dict]):
    """
    Posts a single review containing multiple comments to the PR.
    Note: GitHub expects `position` (diff position) for reviews. Here we use a simple mapping:
    `position = line` as a best-effort approach for small diffs.
    For production you should compute exact diff positions from the patch.
    """
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN not set")

    comments = []
    for f in findings:
        comments.append({
            "path": f.get("file"),
            "position": f.get("line", 1),
            "body": format_comment_body(f)
        })

    payload = {
        "body": "Automated review by Gemini PR Reviewer",
        "event": "COMMENT",
        "comments": comments
    }

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=headers, timeout=30.0)
        r.raise_for_status()
        return r.json()
