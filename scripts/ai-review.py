#!/usr/bin/env python3
"""
AI-powered PR review script for Spice-GUI.

Reads a PR diff and metadata, sends them to Claude for review,
posts a structured review comment, and sets outputs for auto-merge.

Environment variables (set by GitHub Actions):
    ANTHROPIC_API_KEY: API key for Anthropic
    GH_TOKEN: GitHub token for posting comments
    PR_NUMBER: Pull request number
    REPO: Repository in owner/repo format
    DIFF_SIZE: Size of the diff in bytes
"""

import json
import os
import subprocess
import sys

import anthropic

MAX_DIFF_CHARS = 80_000
MAX_DIFF_BYTES = 500_000
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096

DEPENDENCY_FILES = {
    "app/requirements.txt",
    "requirements-dev.txt",
    "app/requirements-dev.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
}

CI_CD_PATTERNS = (
    ".github/workflows/",
    ".github/actions/",
    "Dockerfile",
    "docker-compose",
)


def read_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def truncate_diff(diff, max_chars=MAX_DIFF_CHARS):
    if len(diff) <= max_chars:
        return diff, False
    truncated = diff[:max_chars]
    last_marker = truncated.rfind("\ndiff --git ")
    if last_marker > max_chars * 0.5:
        truncated = truncated[:last_marker]
    return truncated, True


def detect_sensitive_changes(changed_files):
    has_new_deps = any(f in DEPENDENCY_FILES for f in changed_files)
    modifies_ci = any(
        f.startswith(p) for f in changed_files for p in CI_CD_PATTERNS
    )
    return has_new_deps, modifies_ci


def build_review_prompt(diff, pr_title, pr_body, changed_files, was_truncated):
    file_list = "\n".join(f"  - {f}" for f in changed_files)
    truncation_note = ""
    if was_truncated:
        truncation_note = (
            "\n**NOTE**: The diff was truncated due to size. "
            "Review what is provided but flag that some changes are not shown.\n"
        )

    return f"""You are a senior software engineer reviewing a pull request for the Spice-GUI
project, a Python/PyQt6 circuit simulation application.

## Project Context
- Stack: Python 3.11+, PyQt6, ngspice
- Architecture: MVC pattern (models/, controllers/, GUI/, simulation/)
- Models have zero Qt dependencies
- Linter: ruff (E, F, W rules; line-length 120)
- Tests: pytest (unit/ and integration/)
- Conventions: lowercase imperative commit messages, branch naming issue-<N>-description

## PR Information
**Title**: {pr_title}
**Description**: {pr_body or "(no description provided)"}

**Changed files**:
{file_list}
{truncation_note}
## PR Diff
```diff
{diff}
```

## Review Instructions

Analyze this PR for:
1. **Correctness**: Logic errors, off-by-one errors, missing edge cases
2. **Test Coverage**: Are new features/changes covered by tests?
3. **Security**: Injection risks, unsafe deserialization, credential exposure
4. **Breaking Changes**: API changes, removed public methods, changed signatures
5. **Architecture**: Does it follow MVC? Are models free of Qt imports?

Respond with EXACTLY this JSON structure and nothing else:

{{
  "summary": "2-3 sentence summary of what this PR does.",
  "issues": [
    {{
      "severity": "critical|warning|suggestion",
      "file": "path/to/file.py",
      "line": 42,
      "description": "Description of the issue."
    }}
  ],
  "recommendation": "approve|request_changes",
  "recommendation_reason": "One sentence explaining the recommendation.",
  "test_coverage_assessment": "adequate|needs_improvement|not_applicable",
  "breaking_changes_detected": false
}}

Rules:
- "approve" if no critical issues. Warnings/suggestions alone do NOT block approval.
- "request_changes" only for critical-severity issues.
- Be pragmatic: this is an educational capstone project. Don't nitpick style that ruff handles.
- Respond ONLY with JSON. No markdown fences, no preamble."""


def call_anthropic(prompt):
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def parse_review_response(response_text):
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        return {
            "summary": "AI review failed to produce valid JSON output.",
            "issues": [{
                "severity": "warning",
                "file": "N/A",
                "line": 0,
                "description": f"Parse error: {e}. Raw: {text[:300]}",
            }],
            "recommendation": "request_changes",
            "recommendation_reason": "Review output could not be parsed; flagging for human review.",
            "test_coverage_assessment": "not_applicable",
            "breaking_changes_detected": False,
        }


def format_review_comment(review, has_new_deps, modifies_ci, was_truncated):
    severity_emoji = {
        "critical": ":red_circle:",
        "warning": ":yellow_circle:",
        "suggestion": ":blue_circle:",
    }

    rec = review.get("recommendation", "request_changes")
    if rec == "approve":
        rec_line = ":white_check_mark: **Recommendation: APPROVE**"
    else:
        rec_line = ":x: **Recommendation: REQUEST CHANGES**"

    lines = [
        "## :robot: AI Code Review",
        "",
        f"**Summary**: {review.get('summary', 'No summary available.')}",
        "",
        rec_line,
        f"> {review.get('recommendation_reason', '')}",
        "",
    ]

    flags = []
    if has_new_deps:
        flags.append(":package: **New dependencies detected** — requires human review.")
    if modifies_ci:
        flags.append(":gear: **CI/CD config modified** — requires human review.")
    if was_truncated:
        flags.append(":scissors: **Diff was truncated** — only partial review possible.")
    if review.get("breaking_changes_detected"):
        flags.append(":warning: **Breaking changes detected** — verify backward compatibility.")

    if flags:
        lines.append("### Flags")
        lines.extend(flags)
        lines.append("")

    issues = review.get("issues", [])
    if issues:
        lines.append("### Issues Found")
        lines.append("")
        for issue in issues:
            sev = issue.get("severity", "suggestion")
            emoji = severity_emoji.get(sev, ":blue_circle:")
            file_ref = issue.get("file", "")
            line_num = issue.get("line", "")
            loc = f"`{file_ref}:{line_num}`" if file_ref and line_num else (
                f"`{file_ref}`" if file_ref else ""
            )
            lines.append(
                f"- {emoji} **{sev.upper()}** {loc}: {issue.get('description', '')}"
            )
        lines.append("")
    else:
        lines.append("No issues found. :tada:")
        lines.append("")

    coverage = review.get("test_coverage_assessment", "not_applicable")
    coverage_labels = {
        "adequate": ":white_check_mark: Adequate",
        "needs_improvement": ":warning: Needs improvement",
        "not_applicable": ":grey_question: Not applicable",
    }
    lines.append(f"**Test Coverage**: {coverage_labels.get(coverage, coverage)}")
    lines.append("")
    lines.append("---")
    lines.append("*Automated review by Claude AI*")

    return "\n".join(lines)


def post_comment(pr_number, repo, comment):
    subprocess.run(
        ["gh", "pr", "comment", pr_number, "--repo", repo, "--body", comment],
        check=True,
    )


def set_output(name, value):
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"OUTPUT: {name}={value}")


def main():
    pr_number = os.environ.get("PR_NUMBER", "")
    repo = os.environ.get("REPO", "")
    diff_size = int(os.environ.get("DIFF_SIZE", "0"))

    if not pr_number or not repo:
        print("ERROR: PR_NUMBER and REPO environment variables required.")
        return 1

    try:
        diff = read_file("pr_diff.patch")
    except FileNotFoundError:
        print("ERROR: pr_diff.patch not found.")
        return 1

    try:
        meta = json.loads(read_file("pr_meta.json"))
    except (FileNotFoundError, json.JSONDecodeError):
        meta = {"title": "(unknown)", "body": "", "files": []}

    pr_title = meta.get("title", "(unknown)")
    pr_body = meta.get("body", "") or ""
    changed_files = [f.get("path", "") for f in meta.get("files", [])]

    has_new_deps, modifies_ci = detect_sensitive_changes(changed_files)

    if diff_size > MAX_DIFF_BYTES:
        comment = (
            "## :robot: AI Code Review\n\n"
            f":scissors: **Diff too large for AI review** ({diff_size:,} bytes).\n\n"
            "This PR requires manual human review.\n\n---\n*Automated review by Claude AI*"
        )
        post_comment(pr_number, repo, comment)
        set_output("recommendation", "request_changes")
        set_output("has_new_deps", str(has_new_deps).lower())
        set_output("modifies_ci", str(modifies_ci).lower())
        return 0

    diff, was_truncated = truncate_diff(diff)
    prompt = build_review_prompt(diff, pr_title, pr_body, changed_files, was_truncated)

    try:
        response_text = call_anthropic(prompt)
    except anthropic.APIError as e:
        comment = (
            "## :robot: AI Code Review\n\n"
            f":warning: **AI review failed**: {e}\n\n"
            "This PR requires manual human review.\n\n---\n*Automated review by Claude AI*"
        )
        post_comment(pr_number, repo, comment)
        set_output("recommendation", "request_changes")
        set_output("has_new_deps", str(has_new_deps).lower())
        set_output("modifies_ci", str(modifies_ci).lower())
        return 0

    review = parse_review_response(response_text)
    comment = format_review_comment(review, has_new_deps, modifies_ci, was_truncated)
    post_comment(pr_number, repo, comment)

    set_output("recommendation", review.get("recommendation", "request_changes"))
    set_output("has_new_deps", str(has_new_deps).lower())
    set_output("modifies_ci", str(modifies_ci).lower())

    print(f"Review posted. Recommendation: {review.get('recommendation')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
