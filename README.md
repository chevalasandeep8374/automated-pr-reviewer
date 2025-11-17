🚀 AI-Powered Pull Request Reviewer
A GenAI-driven multi-agent code review system built with FastAPI
🌟 Overview
This project is a production-style automated Pull Request Reviewer that analyzes code diffs and posts intelligent review comments directly on GitHub — just like a senior software engineer.

It was designed for a GenAI Backend Engineering Challenge, demonstrating expertise in:

Python backend architecture

FastAPI

GitHub REST API

Multi-agent systems

LLM-powered reasoning

Async design patterns

Real-world debugging and code analysis

This reviewer can analyze Python, JavaScript/React, HTML/CSS, and general code diffs.

🧠 Key Features
🔹 Multi-Agent Review System
Each code change is analyzed by specialized agents:

Agent	Responsibilities
🧩 Syntax Agent	Undefined variables, missing imports, broken DOM selectors
🔒 Security Agent	Injection risk, unsafe eval, sensitive patterns
⚡ Performance Agent	Nested loops, expensive operations, O(n²) patterns
✨ Readability Agent	Poor naming, inconsistent formatting, unclear logic
🧪 Tests Agent	Missing tests, untested branches, new logic without coverage

All agents run in parallel using asynchronous orchestration.

🔹 GitHub Pull Request Integration
Fully automated end-to-end pipeline:

Fetch PR diff using GitHub API

Parse and understand modified lines

Run multi-agent reasoning

Generate human-like structured review comments

Post comments back to the PR using GitHub Reviews API

🔹 Diff-Based Analysis
Understands the exact changed lines:

Added lines

Removed lines

File paths

Hunk ranges

Uses unidiff for accurate diff parsing.

🔹 FastAPI Backend
Clean, modular architecture:

css
Copy code
automated-pr-reviewer/
│── README.md
│── requirements.txt
│── .env.example
│── app/
│   ├── main.py
│   ├── pr_fetcher.py
│   ├── diff_parser.py
│   ├── orchestrator.py
│   ├── agents.py
│   └── github_post.py
└── tests/
    └── sample.patch
🔧 Technologies Used
Python 3.10+

FastAPI

httpx (async REST client)

asyncio

unidiff

GitHub REST API

LLM-style multi-agent reasoning

🔐 Environment Setup
1️⃣ Install dependencies
bash
Copy code
pip install -r requirements.txt
2️⃣ Create .env file
ini
Copy code
GITHUB_TOKEN=your_personal_access_token
Ensure your token has:

repo

pull_request

contents:read

permissions.

▶️ Running the Server
bash
Copy code
uvicorn app.main:app --reload
The API will run at:

arduino
Copy code
http://localhost:8000
📡 API Endpoints
🔹 POST /review-pr
Fetch PR → Analyze → Post comments to GitHub.

Body example:

json
Copy code
{
  "owner": "your-github-username",
  "repo": "your-repository",
  "pr_number": 1
}
🔹 POST /review-diff
Manually review raw unified diff.

Body example:

json
Copy code
{
  "diff_text": "diff --git a/file.js b/file.js ..."
}
