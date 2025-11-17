from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from typing import Optional

from .pr_fetcher import fetch_pr_diff
from .diff_parser import parse_hunks_from_patch
from .orchestrator import analyze_hunks
from .github_post import post_review_to_github

load_dotenv()

app = FastAPI(title="Gemini PR Reviewer")


class PRRequest(BaseModel):
    owner: Optional[str] = None
    repo: Optional[str] = None
    pr_number: Optional[int] = None
    diff_text: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/review-pr")
async def review_pr(req: PRRequest):
    """
    Accept either:
      - { owner, repo, pr_number }  --> fetches PR diff from GitHub
      - { diff_text }               --> use provided unified diff
    """
    if req.diff_text:
        patch_text = req.diff_text
    else:
        if not (req.owner and req.repo and req.pr_number):
            raise HTTPException(status_code=400, detail="owner, repo, pr_number OR diff_text required")
        patch_text = await fetch_pr_diff(req.owner, req.repo, int(req.pr_number))

    hunks = parse_hunks_from_patch(patch_text)
    if not hunks:
        return {"count": 0, "findings": [], "message": "no changes detected"}

    findings = await analyze_hunks(hunks)

    posted = None
    if all([req.owner, req.repo, req.pr_number]) and os.getenv("GITHUB_TOKEN"):
        try:
            posted = await post_review_to_github(req.owner, req.repo, int(req.pr_number), findings)
        except Exception as e:
            posted = {"error": str(e)}

    return {"count": len(findings), "findings": findings, "posted": posted}


@app.post("/review-diff")
async def review_diff(payload: dict):
    diff_text = payload.get("diff_text")
    if not diff_text:
        raise HTTPException(status_code=400, detail="diff_text required")
    hunks = parse_hunks_from_patch(diff_text)
    findings = await analyze_hunks(hunks)
    return {"count": len(findings), "findings": findings}
