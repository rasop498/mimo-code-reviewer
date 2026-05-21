# MiMo Code Review Agent

**Automated pull request review powered by Xiaomi MiMo V2.5 API**

An intelligent code review agent that automatically analyzes GitHub pull requests, detects bugs, security vulnerabilities, and code quality issues — all powered by the ultra-low-cost Xiaomi MiMo V2.5 model.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Tests](https://img.shields.io/badge/tests-39%20passed-green)
![License](https://img.shields.io/badge/license-MIT-green)
![MiMo](https://img.shields.io/badge/powered%20by-MiMo%20V2.5-orange)

---

## The Problem

Code reviews are critical but expensive and slow:
- **Human reviews** take 30-60 min per PR and create bottlenecks
- **AI reviews with GPT-4/Claude** cost $0.01-0.10 per review (adds up fast at scale)
- **No automated review** means bugs, security holes, and bad patterns slip through

| Review Method | Cost per Review | Speed | Quality |
|---|---|---|---|
| Human reviewer | $25-50/hour | 30-60 min | High but inconsistent |
| GPT-4o | ~$0.05-0.10 | 10-30s | Good |
| Claude Sonnet | ~$0.03-0.08 | 10-30s | Good |
| **MiMo V2.5** | **~$0.0001** | **5-15s** | **Good for code review** |

**MiMo V2.5 is 100-500x cheaper** while being specifically optimized for code understanding.

---

## Solution: MiMo Code Review Agent

A lightweight Python server that:

1. **Listens for GitHub webhooks** — auto-triggers on PR open/update
2. **Parses unified diffs** — extracts file changes, detects languages
3. **Sends to MiMo V2.5** — structured prompts for bug/security/style review
4. **Posts review comments** — directly on the PR with inline suggestions
5. **Tracks costs** — real-time dashboard of token usage and savings

### Architecture

```
┌─────────────┐     ┌──────────────────────┐     ┌──────────────┐
│   GitHub     │────▶│  MiMo Code Reviewer  │────▶│  MiMo V2.5   │
│   Webhook    │     │  (Flask Server)      │     │  API         │
│   PR Event   │     │                      │     │  (Xiaomi)    │
└─────────────┘     │  ┌────────────────┐  │     └──────────────┘
                     │  │ Diff Parser    │  │
                     │  │ 20+ languages  │  │
                     │  └────────────────┘  │
                     │  ┌────────────────┐  │     ┌──────────────┐
                     │  │ Review Engine  │  │────▶│  GitHub API   │
                     │  │ Bug/Security   │  │     │  Post Review  │
                     │  └────────────────┘  │     └──────────────┘
                     │  ┌────────────────┐  │
                     │  │ Cost Tracker   │  │
                     │  │ Stats API      │  │
                     │  └────────────────┘  │
                     └──────────────────────┘
```

### What It Detects

| Category | Examples |
|---|---|
| **Bugs** | Null pointer, off-by-one, race conditions, logic errors |
| **Security** | SQL injection, XSS, hardcoded secrets, shell injection |
| **Performance** | N+1 queries, unnecessary loops, memory leaks |
| **Error Handling** | Missing try/catch, unchecked return values |
| **Style** | Naming conventions, dead code, complexity |
| **Best Practices** | SOLID violations, missing docs, anti-patterns |

### Supported Languages

Python, JavaScript, TypeScript, Go, Rust, Java, C/C++, Ruby, PHP, Swift, Kotlin, Scala, SQL, Shell, YAML, and more (20+ languages via automatic detection).

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/rasop498/mimo-code-reviewer.git
cd mimo-code-reviewer
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your keys:
# MIMO_API_KEY=your_key_from_platform.xiaomimimo.com
# GITHUB_TOKEN=your_github_token
```

### 3. Run

**As webhook server** (auto-review PRs):
```bash
python -m reviewer
# Server starts on http://0.0.0.0:9900
```

**Review a specific PR** (CLI):
```bash
python -m reviewer.cli pr https://github.com/owner/repo/pull/123
```

**Review local changes** (CLI):
```bash
git add .
python -m reviewer.cli diff
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/review` | Manually review a PR |
| `POST` | `/review/diff` | Review a raw diff |
| `POST` | `/webhook` | GitHub webhook handler |
| `GET` | `/health` | Health check |
| `GET` | `/stats` | Usage statistics |

### Example: Manual PR Review

```bash
curl -X POST http://localhost:9900/review \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "torvalds",
    "repo": "linux",
    "pr_number": 42,
    "post_comment": false
  }'
```

### Example: Review Raw Diff

```bash
curl -X POST http://localhost:9900/review/diff \
  -H "Content-Type: application/json" \
  -d '{
    "diff": "diff --git a/test.py b/test.py\n...",
    "title": "Fix login"
  }'
```

---

## GitHub Webhook Setup

1. Go to your repo → **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `https://your-server.com/webhook`
3. **Content type**: `application/json`
4. **Secret**: (same as `GITHUB_WEBHOOK_SECRET` in .env)
5. **Events**: Select **Pull requests**

Now every new PR will be automatically reviewed!

---

## How It Works

### 1. Diff Parsing Engine
Parses unified diffs into structured `FileAnalysis` objects with language detection, line-level tracking, and hunk extraction.

### 2. Smart Prompt Construction
Builds context-aware review prompts that include:
- PR title and description for context
- File-by-file changes with language hints
- Structured output format for consistent reviews

### 3. MiMo V2.5 Inference
Sends two requests per review:
- **Summary request**: Quick overview of changes
- **Detail request**: Deep analysis of bugs, security, performance

### 4. Cost Optimization
- MiMo V2.5 is ~$0.0001 per review
- 1000 reviews = ~$0.10 total
- Real-time cost tracking via `/stats` endpoint

---

## Cost Comparison

For a team doing 50 PRs/day (1500/month):

| Provider | Cost/Month | Annual |
|---|---|---|
| GPT-4o | $75-150 | $900-1800 |
| Claude Sonnet | $45-120 | $540-1440 |
| **MiMo V2.5** | **$0.15** | **$1.80** |

**Savings: 99.8%** compared to GPT-4o.

---

## Testing

```bash
# Run all 39 tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_analyzer.py -v
```

Tests cover:
- Diff parsing (19 tests) — multi-file, multi-language, edge cases
- Review engine (6 tests) — issue counting, comment formatting, mock reviews
- CLI parser (4 tests) — URL parsing, error handling
- Prompt building (4 tests) — content verification
- Data structures (6 tests) — hunk properties, language detection

---

## Project Structure

```
mimo-code-reviewer/
├── reviewer/
│   ├── __init__.py          # Package metadata
│   ├── __main__.py          # Entry point (server mode)
│   ├── analyzer.py          # Diff parser & prompt builder
│   ├── cli.py               # CLI interface
│   ├── config.py            # Configuration management
│   ├── github_client.py     # GitHub API client
│   ├── mimo_client.py       # MiMo API client
│   ├── reviewer.py          # Core review engine
│   └── server.py            # Flask webhook server
├── tests/
│   ├── test_analyzer.py     # 25 tests
│   ├── test_cli.py          # 4 tests
│   └── test_reviewer.py     # 10 tests
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

---

## Integration with Hermes Agent

This project integrates with the Hermes AI Agent ecosystem via 9Router:

```
Telegram User
    │
    ▼
Hermes Agent (Telegram Bot)
    │
    ▼
9Router (Model Router, port 20128)
    │
    ├──▶ Kiro/Claude (complex reasoning)
    └──▶ MiMo Code Reviewer (code review, port 9900)
              │
              └──▶ MiMo V2.5 API (Xiaomi)
```

Users can request code reviews directly through Telegram, and the agent routes the request to MiMo Code Reviewer for analysis.

---

## Real-World Use Case

Running on AWS VPS (`3.107.0.2`) with:
- **9Router v0.4.50** — multi-model routing (4 Kiro connections)
- **Hermes Agent v0.14.0** — Telegram bot with 162 skills
- **MiMo Code Reviewer** — automated PR reviews

The setup handles code reviews for multiple repositories at near-zero cost, while keeping premium models (Claude via Kiro) available for complex reasoning tasks.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built for the Xiaomi MiMo Orbit 100T Creator Program*
*Powered by MiMo V2.5 — ultra-low-cost AI inference from Xiaomi*
