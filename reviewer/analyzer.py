"""Code analysis engine - breaks down diffs into reviewable chunks."""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    STYLE = "style"


class IssueCategory(Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    LOGIC = "logic"
    ERROR_HANDLING = "error_handling"
    DOCUMENTATION = "documentation"
    BEST_PRACTICE = "best_practice"


@dataclass
class DiffHunk:
    file_path: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    content: str
    language: str = ""

    @property
    def added_lines(self) -> list[str]:
        return [l[1:] for l in self.content.splitlines() if l.startswith("+")]

    @property
    def removed_lines(self) -> list[str]:
        return [l[1:] for l in self.content.splitlines() if l.startswith("-")]


@dataclass
class ReviewIssue:
    file_path: str
    line: int
    severity: Severity
    category: IssueCategory
    title: str
    description: str
    suggestion: Optional[str] = None


@dataclass
class FileAnalysis:
    file_path: str
    language: str
    hunks: list[DiffHunk] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0


LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "jsx", ".tsx": "tsx", ".java": "java", ".go": "go",
    ".rs": "rust", ".rb": "ruby", ".php": "php", ".c": "c",
    ".cpp": "cpp", ".h": "c", ".hpp": "cpp", ".cs": "csharp",
    ".swift": "swift", ".kt": "kotlin", ".scala": "scala",
    ".sh": "bash", ".yml": "yaml", ".yaml": "yaml",
    ".json": "json", ".md": "markdown", ".sql": "sql",
    ".html": "html", ".css": "css", ".scss": "scss",
}


def detect_language(file_path: str) -> str:
    for ext, lang in LANG_MAP.items():
        if file_path.endswith(ext):
            return lang
    return "text"


def parse_diff(diff_text: str) -> list[FileAnalysis]:
    """Parse a unified diff into structured file analyses."""
    files: list[FileAnalysis] = []
    current_file: Optional[FileAnalysis] = None
    current_hunk_lines: list[str] = []
    current_hunk_header: Optional[tuple] = None

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            if current_file and current_hunk_header and current_hunk_lines:
                _add_hunk(current_file, current_hunk_header, current_hunk_lines)
                current_hunk_lines = []
                current_hunk_header = None
            match = re.search(r"b/(.+)$", line)
            if match:
                path = match.group(1)
                current_file = FileAnalysis(
                    file_path=path,
                    language=detect_language(path),
                )
                files.append(current_file)

        elif line.startswith("@@") and current_file:
            if current_hunk_header and current_hunk_lines:
                _add_hunk(current_file, current_hunk_header, current_hunk_lines)
                current_hunk_lines = []
            match = re.search(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
            if match:
                current_hunk_header = (
                    int(match.group(1)),
                    int(match.group(2) or "1"),
                    int(match.group(3)),
                    int(match.group(4) or "1"),
                )

        elif current_hunk_header and current_file:
            current_hunk_lines.append(line)
            if line.startswith("+") and not line.startswith("+++"):
                current_file.additions += 1
            elif line.startswith("-") and not line.startswith("---"):
                current_file.deletions += 1

    if current_file and current_hunk_header and current_hunk_lines:
        _add_hunk(current_file, current_hunk_header, current_hunk_lines)

    return files


def _add_hunk(
    file_analysis: FileAnalysis,
    header: tuple,
    lines: list[str],
) -> None:
    hunk = DiffHunk(
        file_path=file_analysis.file_path,
        old_start=header[0],
        old_count=header[1],
        new_start=header[2],
        new_count=header[3],
        content="\n".join(lines),
        language=file_analysis.language,
    )
    file_analysis.hunks.append(hunk)


def build_review_prompt(file_analyses: list[FileAnalysis], pr_title: str = "", pr_body: str = "") -> str:
    """Build a comprehensive review prompt for MiMo."""
    parts = [
        "You are an expert code reviewer. Analyze the following pull request changes and provide a detailed review.",
        "",
        "## Review Guidelines",
        "1. Look for bugs, logic errors, and edge cases",
        "2. Check for security vulnerabilities (SQL injection, XSS, hardcoded secrets, etc.)",
        "3. Evaluate error handling completeness",
        "4. Check for performance issues (N+1 queries, unnecessary loops, memory leaks)",
        "5. Verify code style and best practices for the language",
        "6. Suggest improvements with specific code examples",
        "",
    ]

    if pr_title:
        parts.append(f"## PR Title: {pr_title}")
    if pr_body:
        parts.append(f"## PR Description:\n{pr_body[:500]}")
    parts.append("")

    for fa in file_analyses:
        parts.append(f"## File: {fa.file_path} ({fa.language})")
        parts.append(f"Changes: +{fa.additions} -{fa.deletions}")
        for hunk in fa.hunks:
            parts.append(f"\n### Lines {hunk.new_start}-{hunk.new_start + hunk.new_count}")
            parts.append(f"```{hunk.language}")
            parts.append(hunk.content)
            parts.append("```")
        parts.append("")

    parts.extend([
        "## Output Format",
        "Provide your review as a structured response with:",
        "1. **Summary**: 2-3 sentence overview of the changes",
        "2. **Issues Found**: List each issue with:",
        "   - File and line number",
        "   - Severity: CRITICAL / WARNING / INFO / STYLE",
        "   - Category: bug / security / performance / style / logic / error_handling",
        "   - Description of the issue",
        "   - Suggested fix (with code if applicable)",
        "3. **Positive Observations**: What was done well",
        "4. **Overall Score**: Rate 1-10 with brief justification",
    ])

    return "\n".join(parts)


def build_summary_prompt(file_analyses: list[FileAnalysis], pr_title: str = "", pr_body: str = "") -> str:
    """Build a prompt for generating a PR summary."""
    file_list = []
    total_add = 0
    total_del = 0
    for fa in file_analyses:
        file_list.append(f"- {fa.file_path} (+{fa.additions} -{fa.deletions})")
        total_add += fa.additions
        total_del += fa.deletions

    return "\n".join([
        "Summarize this pull request in a clear, concise way.",
        f"PR Title: {pr_title}" if pr_title else "",
        f"PR Description: {pr_body[:300]}" if pr_body else "",
        f"Total changes: +{total_add} -{total_del} across {len(file_analyses)} files",
        "",
        "Files changed:",
        *file_list,
        "",
        "Provide:",
        "1. One-paragraph summary of what this PR does",
        "2. Key changes listed as bullet points",
        "3. Any potential risks or areas needing attention",
    ])
