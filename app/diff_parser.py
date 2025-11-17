from unidiff import PatchSet
from typing import List, Dict

def parse_hunks_from_patch(text: str) -> List[Dict]:
    """
    Parse unified diff into a list of hunks. Each hunk has:
    { file, hunk_text, added (list), removed (list), start (target_start) }
    """
    ps = PatchSet(text.splitlines(keepends=True))
    hunks = []
    for patched_file in ps:
        for hunk in patched_file:
            added = [line.value.rstrip("\n") for line in hunk if line.is_added]
            removed = [line.value.rstrip("\n") for line in hunk if line.is_removed]
            hunks.append({
                "file": patched_file.path,
                "hunk_text": str(hunk),
                "added": added,
                "removed": removed,
                "start": hunk.target_start or 1,
            })
    return hunks
