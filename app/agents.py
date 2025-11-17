# app/agents.py
from typing import List, Dict, Optional
import re

# -------------------------
# Utilities
# -------------------------
def _make_finding(file: str,
                  line: int,
                  title: str,
                  explanation: str,
                  suggestion: str,
                  severity: str = "low",
                  confidence: float = 0.5,
                  category: str = "general",
                  source: Optional[List[str]] = None) -> Dict:
    return {
        "file": file,
        "line": int(line or 1),
        "issue_title": title,
        "explanation": explanation,
        "suggestion": suggestion,
        "severity": severity,
        "confidence": round(float(confidence), 2),
        "category": category,
        "source": source or []
    }

def _normalize_file(path: str) -> str:
    return (path or "").lower()

def detect_language(file_path: str) -> str:
    f = _normalize_file(file_path)
    if f.endswith((".html", ".htm")):
        return "html"
    if f.endswith((".js", ".jsx", ".mjs", ".ts", ".tsx")):
        return "js"
    if f.endswith((".py",)):
        return "py"
    if f.endswith((".css",)):
        return "css"
    if f.endswith((".json", ".yaml", ".yml")):
        return "config"
    if f.endswith((".md", ".markdown")):
        return "md"
    return "other"

# -------------------------
# Syntax / Style Agent
# -------------------------
def syntax_agent(hunk: Dict) -> List[Dict]:
    findings = []
    file = hunk.get("file")
    lang = detect_language(file)
    added = hunk.get("added", [])
    start = hunk.get("start", 1)

    for offset, line in enumerate(added):
        lineno = start + offset
        # tabs
        if "\t" in line:
            findings.append(_make_finding(
                file, lineno,
                "Tab character detected",
                "This line contains a tab; many projects prefer spaces for indentation.",
                "Replace tabs with spaces (run formatter like Prettier/Black) and commit formatting changes.",
                severity="low", confidence=0.45, category="style", source=["syntax_agent"]
            ))
        # overly long lines
        if len(line) > 120:
            findings.append(_make_finding(
                file, lineno,
                "Long line (>120 chars)",
                f"Line length is {len(line)} characters which reduces readability.",
                "Wrap long expressions or extract logic into helper functions. Run code formatters.",
                severity="low", confidence=0.5, category="style", source=["syntax_agent"]
            ))
        # JS missing semicolon heuristic
        if lang == "js":
            t = line.strip()
            if t and re.match(r"^(var |let |const |return |console\.|if\s*\(|for\s*\()", t) and not t.endswith(";") and not t.endswith("{") and not t.endswith("}"):
                findings.append(_make_finding(
                    file, lineno,
                    "Possible missing semicolon",
                    "This JavaScript line looks like a statement but does not end with a semicolon; project may require semicolons.",
                    "Add semicolon or apply your project's linter/prettier rules.",
                    severity="low", confidence=0.4, category="style", source=["syntax_agent"]
                ))
    return findings

# -------------------------
# JavaScript/React Agent
# -------------------------
def js_agent(hunk: Dict) -> List[Dict]:
    findings = []
    file = hunk.get("file")
    added = "\n".join(hunk.get("added", []))
    start = hunk.get("start", 1)

    # duplicate declarations
    names = re.findall(r"\b(?:let|const|var)\s+([A-Za-z_\$][A-Za-z0-9_\$]*)", added)
    for n in set(names):
        if names.count(n) > 1:
            findings.append(_make_finding(
                file, start,
                "Duplicate variable declaration",
                f"`{n}` is declared multiple times in this change; this can cause confusion or shadowing bugs.",
                "Remove redundant declarations and reuse the existing variable or rename appropriately.",
                severity="low", confidence=0.6, category="js", source=["js_agent"]
            ))

    # React createRoot / DOM ID issues
    if "createRoot" in added or "ReactDOM.render" in added:
        if re.search(r"getElementById\(['\"]\s*['\"]\)", added) or re.search(r"getElementById\(['\"]\s*['\"]\)", added.replace(" ", "")):
            findings.append(_make_finding(
                file, start,
                "Invalid DOM selector in React mount",
                "document.getElementById('') or empty selector will return null and cause mount errors.",
                "Ensure you pass a valid element ID (e.g. 'root') or create the element before mounting.",
                severity="high", confidence=0.95, category="bug", source=["js_agent"]
            ))

    # direct DOM innerHTML
    if re.search(r"\.innerHTML\s*=", added):
        findings.append(_make_finding(
            file, start,
            "Direct use of innerHTML",
            "Assigning to innerHTML with dynamic content can introduce XSS vulnerabilities.",
            "Prefer textContent or safe templating libraries; sanitize untrusted content before rendering.",
            severity="high", confidence=0.9, category="security", source=["js_agent"]
        ))

    # heavy loops on top-level
    if re.search(r"^\s*(for\s*\(|while\s*\()", added, flags=re.MULTILINE):
        findings.append(_make_finding(
            file, start,
            "Potential expensive top-level loop",
            "Large loops executed during module evaluation or on initial load may block the main thread.",
            "Move heavy work to async tasks, requestAnimationFrame, or web workers.",
            severity="medium", confidence=0.7, category="performance", source=["js_agent"]
        ))

    return findings

# -------------------------
# HTML Agent
# -------------------------
def html_agent(hunk: Dict) -> List[Dict]:
    findings = []
    file = hunk.get("file")
    added = "\n".join(hunk.get("added", []))
    start = hunk.get("start", 1)

    # missing alt attributes
    if "<img" in added and "alt=" not in added:
        findings.append(_make_finding(
            file, start,
            "Image missing alt attribute",
            "Image added without an alt attribute reduces accessibility.",
            "Add descriptive alt=\"...\" text to images for accessibility and SEO.",
            severity="low", confidence=0.8, category="accessibility", source=["html_agent"]
        ))

    # inline event handlers
    if re.search(r"on\w+\s*=", added):
        findings.append(_make_finding(
            file, start,
            "Inline event handler used",
            "Inline handlers mix markup and logic and can increase XSS risk.",
            "Move handlers to external JS and use addEventListener().",
            severity="medium", confidence=0.75, category="security", source=["html_agent"]
        ))

    # blocking script tags detection
    script_tags = re.findall(r"<script\b[^>]*>", added, flags=re.IGNORECASE)
    for tag in script_tags:
        if "async" not in tag.lower() and "defer" not in tag.lower() and 'type="module"' not in tag.lower():
            findings.append(_make_finding(
                file, start,
                "Blocking <script> tag added",
                "Adding a script tag without async/defer can block page parsing and hurt performance.",
                "Add async/defer or move scripts to the end of body; bundle/minify to reduce blocking.",
                severity="medium", confidence=0.85, category="performance", source=["html_agent"]
            ))

    return findings

# -------------------------
# Python Agent
# -------------------------
def py_agent(hunk: Dict) -> List[Dict]:
    findings = []
    file = hunk.get("file")
    added = "\n".join(hunk.get("added", []))
    start = hunk.get("start", 1)

    # duplicate FastAPI app init (common in your repo)
    if "FastAPI(" in added and re.search(r"\bapp\s*=\s*FastAPI\(", added):
        # If file contains the initialization multiple times in added lines
        if added.count("FastAPI(") > 1 or re.search(r"app\s*=\s*FastAPI\(", added) and "app =" in added and added.count("app =") > 1:
            findings.append(_make_finding(
                file, start,
                "Duplicate FastAPI() initialization",
                "Creating multiple FastAPI() instances will result in routing and middleware not working as expected.",
                "Keep a single FastAPI() instance (app) and reuse it; remove duplicate initialization.",
                severity="high", confidence=0.95, category="bug", source=["py_agent"]
            ))

    # time.sleep in async code
    if "time.sleep(" in added and ("async def" in added or "await" in added):
        findings.append(_make_finding(
            file, start,
            "Blocking sleep in async code",
            "time.sleep() blocks the event loop when called in async contexts and can make the app unresponsive.",
            "Use await asyncio.sleep() in async functions or run blocking code in a threadpool.",
            severity="high", confidence=0.9, category="performance", source=["py_agent"]
        ))

    # eval/exec
    if re.search(r"\beval\(|\bexec\(", added):
        findings.append(_make_finding(
            file, start,
            "Use of eval/exec",
            "Using eval/exec on dynamic input is dangerous and can execute arbitrary code.",
            "Avoid eval/exec; use safe parsing libraries or strictly validate input.",
            severity="high", confidence=0.96, category="security", source=["py_agent"]
        ))

    # missing docstring heuristic
    if re.search(r"^\s*def\s+\w+\s*\(.*\):", added, flags=re.MULTILINE):
        # if next non-empty added line isn't a docstring
        lines = [l for l in added.splitlines()]
        for idx, l in enumerate(lines):
            if re.match(r"^\s*def\s+\w+\s*\(.*\):", l):
                # look ahead
                look = "".join(lines[idx+1: idx+4]).strip()
                if not look.startswith(('"""', "'''")):
                    findings.append(_make_finding(
                        file, start + idx,
                        "Missing docstring for new function",
                        "It's good practice to add a docstring describing function behavior and parameters.",
                        "Add a concise docstring (PEP 257) to describe inputs, outputs, and side effects.",
                        severity="low", confidence=0.6, category="readability", source=["py_agent"]
                    ))
    return findings

# -------------------------
# Security Agent (cross-language)
# -------------------------
def security_agent(hunk: Dict) -> List[Dict]:
    findings = []
    file = hunk.get("file")
    added_text = "\n".join(hunk.get("added", []))
    start = hunk.get("start", 1)

    # Hard-coded secrets
    if re.search(r"(api_key|apiKey|secret|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{6,}['\"]", added_text, re.IGNORECASE):
        findings.append(_make_finding(
            file, start,
            "Possible hard-coded secret",
            "This hunk appears to introduce a credential or secret in source code.",
            "Move secrets to environment variables or a secret manager; rotate impacted keys.",
            severity="high", confidence=0.95, category="security", source=["security_agent"]
        ))

    # SQL concatenation pattern (naive)
    if re.search(r"SELECT .* \+ .*", added_text, re.IGNORECASE) or re.search(r"f\".*SELECT.*\{.*\}.*\"", added_text):
        findings.append(_make_finding(
            file, start,
            "Possible SQL concatenation",
            "SQL constructed by string concatenation or interpolation can be vulnerable to injection.",
            "Use parameterized queries from your DB library (prepared statements / parameter substitution).",
            severity="high", confidence=0.9, category="security", source=["security_agent"]
        ))

    return findings

# -------------------------
# Performance Agent (cross-language)
# -------------------------
def performance_agent(hunk: Dict) -> List[Dict]:
    findings = []
    file = hunk.get("file")
    added_text = "\n".join(hunk.get("added", []))
    start = hunk.get("start", 1)
    lang = detect_language(file)

    # repeated DOM queries / heavy loops
    if lang == "js" and re.search(r"\b(getElementById|querySelector(All)?)\(", added_text):
        if len(re.findall(r"\b(getElementById|querySelector(All)?)\(", added_text)) > 3:
            findings.append(_make_finding(
                file, start,
                "Multiple DOM queries",
                "Multiple similar DOM queries may indicate non-optimal DOM access which can slow rendering.",
                "Cache DOM references, reuse them and avoid repeated queries in loops.",
                severity="low", confidence=0.6, category="performance", source=["performance_agent"]
            ))

    # nested loops for python
    if lang == "py" and re.search(r"for .*:\n\s+for .*:", added_text):
        findings.append(_make_finding(
            file, start,
            "Potential nested loops",
            "Nested loops can cause O(n^2) behavior on large inputs.",
            "Consider using sets/maps or algorithmic improvements to reduce complexity.",
            severity="medium", confidence=0.75, category="performance", source=["performance_agent"]
        ))

    # blocking script tag handled in html_agent

    return findings

# -------------------------
# Readability agent (cross-language)
# -------------------------
def readability_agent(hunk: Dict) -> List[Dict]:
    findings = []
    file = hunk.get("file")
    added_lines = hunk.get("added", [])
    start = hunk.get("start", 1)

    if len(added_lines) > 60:
        findings.append(_make_finding(
            file, start,
            "Large change hunk",
            "This hunk is large which makes review and reasoning harder.",
            "Split into smaller commits or extract functions and add tests for pieces.",
            severity="low", confidence=0.6, category="readability", source=["readability_agent"]
        ))

    # long lines - complementary
    if any(len(l) > 140 for l in added_lines):
        findings.append(_make_finding(
            file, start,
            "Very long lines present",
            "Long lines reduce readability and can hide complexity.",
            "Break into smaller statements or helpers; run project formatter.",
            severity="low", confidence=0.55, category="readability", source=["readability_agent"]
        ))

    return findings

# -------------------------
# Tests / Coverage agent (smarter)
# -------------------------
def tests_agent(hunk: Dict) -> List[Dict]:
    findings = []
    file = hunk.get("file")
    added_text = "\n".join(hunk.get("added", []))
    start = hunk.get("start", 1)
    lang = detect_language(file)

    # skip if the change is itself a test file
    if re.search(r"(test_|_test|tests?/)", file, re.IGNORECASE):
        return findings

    # heuristics for meaningful changes
    logic_patterns = [r"\bif\b", r"\belse\b", r"\breturn\b", r"\bfor\b", r"\bwhile\b", r"\btry\b", r"\bexcept\b"]
    contains_logic = any(re.search(p, added_text) for p in logic_patterns)
    contains_fn = bool(re.search(r"\bdef\s+\w+\(|function\s+\w+|\w+\s*=\s*\(.*\)\s*=>", added_text))
    contains_db = bool(re.search(r"(cursor\.execute|db\.|insert|update|delete|save\()", added_text, re.IGNORECASE))
    contains_api = bool(re.search(r"\b(fetch|axios|requests\.)\b", added_text))

    if any([contains_logic, contains_fn, contains_db, contains_api]):
        explanation = []
        if contains_logic:
            explanation.append("This change introduces branching or control flow which should be validated.")
        if contains_fn:
            explanation.append("A function is added/changed; functions should be covered by direct unit tests.")
        if contains_db:
            explanation.append("Database operations were added — tests should assert query correctness and edge cases.")
        if contains_api:
            explanation.append("External API calls were introduced — use mocks in tests to validate behavior.")

        findings.append(_make_finding(
            file, start,
            "Missing test coverage for meaningful changes",
            " ".join(explanation),
            "Add unit/integration tests for normal cases, edge cases, failure paths, and mock external services.",
            severity="medium", confidence=0.78, category="testing", source=["tests_agent"]
        ))

    return findings

# -------------------------
# Public analyzer entrypoint
# -------------------------
def analyze_hunk(hunk: Dict) -> List[Dict]:
    """
    Runs language-specific and cross-cutting agents on the provided hunk
    and returns a deduplicated list of findings.
    """
    file = hunk.get("file", "")
    lang = detect_language(file)

    runners = [
        syntax_agent,
        security_agent,
        performance_agent,
        readability_agent,
        tests_agent
    ]

    # add language-specific agents
    if lang == "js":
        runners.insert(1, js_agent)
    if lang == "html":
        runners.insert(1, html_agent)
    if lang == "py":
        runners.insert(1, py_agent)

    results: List[Dict] = []
    for r in runners:
        try:
            results.extend(r(hunk))
        except Exception:
            # resilient: don't fail entire analysis if one agent errors
            continue

    # dedupe by (title, line) while preserving order
    seen = set()
    deduped = []
    for item in results:
        key = (item.get("issue_title"), item.get("line"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped
