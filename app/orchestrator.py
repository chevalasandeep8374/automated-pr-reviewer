# app/orchestrator.py
import asyncio
from typing import List, Dict
from .agents import analyze_hunk

# concurrency limit
CONCURRENCY = 6

async def _run_hunk(hunk: Dict) -> List[Dict]:
    loop = asyncio.get_running_loop()
    # analyze_hunk is synchronous, run in executor
    return await loop.run_in_executor(None, analyze_hunk, hunk)

async def analyze_hunks(hunks: List[Dict]) -> List[Dict]:
    """
    Run analyze_hunk on all hunks concurrently (bounded concurrency).
    Merge results, deduplicate globally and sort by severity.
    """
    sem = asyncio.Semaphore(CONCURRENCY)

    async def worker(h):
        async with sem:
            try:
                return await _run_hunk(h)
            except Exception:
                return []

    tasks = [worker(h) for h in hunks]
    nested = await asyncio.gather(*tasks)

    # flatten
    flat = [item for sub in nested for item in sub]

    # normalize fields and ensure hunk_text exists
    for it in flat:
        it.setdefault("file", it.get("file", ""))
        it.setdefault("line", int(it.get("line", 1)))
        it.setdefault("hunk_text", it.get("hunk_text", ""))

    # global dedupe by (file, line, title)
    seen = set()
    deduped = []
    for it in flat:
        key = (it.get("file"), it.get("line"), it.get("issue_title"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    # sort by severity (high->medium->low) then confidence desc
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    deduped.sort(key=lambda x: (severity_rank.get(x.get("severity", "low"), 2), -float(x.get("confidence", 0))))

    return deduped
