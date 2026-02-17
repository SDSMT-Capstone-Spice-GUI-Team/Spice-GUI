"""Generate pre-filled bug report links for human testing checklist items.

For each testing issue, rewrites the issue body so every checklist item gets
a [report bug](...) link that opens a new GitHub issue pre-filled with:
  - Title: BUG: <item text>
  - Label: bug
  - Body: structured template with item name and testing issue number

Usage:
    python scripts/generate_bug_links.py          # dry-run: prints to stdout
    python scripts/generate_bug_links.py --apply   # updates issues via gh CLI

Idempotent: safe to re-run. Existing [report bug] links are stripped and
regenerated, so the script works both for first-time setup and for refreshing
links after checklist items are added or edited.

For agents: when you add new checklist items to a testing issue (e.g., after
shipping a PR with UI-visible changes), re-run this script with --apply to
regenerate all links. Or use make_bug_url() and add_links_to_body() directly
if you only need to update a single issue.

To add a NEW testing issue: add its number and section name to
TESTING_ISSUES dict below, then run with --apply.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

REPO = "SDSMT-Capstone-Spice-GUI-Team/Spice-GUI"
BASE_URL = f"https://github.com/{REPO}/issues/new"

# Testing issues: number -> section name
TESTING_ISSUES = {
    269: "Smoke Test",
    270: "Components",
    271: "Selection & Clipboard",
    272: "Wires",
    273: "Undo/Redo",
    274: "File Operations",
    275: "Simulation",
    276: "Plot Features",
    277: "User Interface",
    279: "Annotations",
}

CHECKBOX_RE = re.compile(r"^(- \[[ x]\] )(.+)$")


def make_bug_url(item_text: str, issue_number: int) -> str:
    """Build a pre-filled GitHub new-issue URL."""
    # Strip any existing [report bug](...) suffix
    item_text = re.sub(r"\s*\[report bug\]\([^)]*\)\s*$", "", item_text)

    # Clean text for title: strip markdown bold markers and PR refs
    clean = item_text.replace("**", "")
    title = f"BUG: {clean}"

    body = (
        f"**Item**: {item_text}\n"
        f"**Testing issue**: #{issue_number}\n"
        f"\n"
        f"**Expected**: \n"
        f"\n"
        f"**Actual**: \n"
        f"\n"
        f"**Steps to reproduce**:\n"
        f"1. \n"
        f"2. \n"
        f"3. \n"
        f"\n"
        f"**Screenshot**: (paste with Ctrl+V)\n"
    )

    params = urllib.parse.urlencode(
        {"labels": "bug", "title": title, "body": body}, quote_via=urllib.parse.quote
    )
    return f"{BASE_URL}?{params}"


def add_links_to_body(body: str, issue_number: int) -> str:
    """Add [report bug] links to every checkbox line in the body."""
    lines = body.split("\n")
    result = []
    for line in lines:
        m = CHECKBOX_RE.match(line)
        if m:
            prefix = m.group(1)  # "- [ ] " or "- [x] "
            item_text = m.group(2).strip()
            # Remove existing link if re-running
            item_text = re.sub(
                r"\s*\[report bug\]\([^)]*\)\s*$", "", item_text
            ).strip()
            url = make_bug_url(item_text, issue_number)
            result.append(f"{prefix}{item_text} — [report bug]({url})")
        else:
            result.append(line)
    return "\n".join(result)


def fetch_issue_body(issue_number: int) -> str:
    """Fetch an issue body via gh CLI."""
    proc = subprocess.run(
        ["gh", "issue", "view", str(issue_number), "--repo", REPO, "--json", "body"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)["body"]


def update_issue_body(issue_number: int, new_body: str) -> None:
    """Update an issue body via gh CLI using a temp file (Windows-safe)."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(new_body)
        tmp_path = f.name
    try:
        subprocess.run(
            [
                "gh",
                "issue",
                "edit",
                str(issue_number),
                "--repo",
                REPO,
                "--body-file",
                tmp_path,
            ],
            check=True,
        )
    finally:
        os.unlink(tmp_path)


def main():
    apply = "--apply" in sys.argv

    for issue_number, section_name in TESTING_ISSUES.items():
        print(f"\n{'='*60}")
        print(f"Issue #{issue_number}: {section_name}")
        print(f"{'='*60}")

        body = fetch_issue_body(issue_number)
        new_body = add_links_to_body(body, issue_number)

        # Count links added
        link_count = new_body.count("[report bug]")
        print(f"  {link_count} checklist items with [report bug] links")

        if apply:
            update_issue_body(issue_number, new_body)
            print(f"  Updated issue #{issue_number}")
        else:
            # Show first modified checkbox as a sample
            for line in new_body.split("\n"):
                if "[report bug]" in line:
                    # Truncate for display
                    display = line[:120] + "..." if len(line) > 120 else line
                    print(f"  Sample: {display}")
                    break

    if not apply:
        print(f"\n{'='*60}")
        print("DRY RUN — no issues were modified.")
        print("Run with --apply to update the issues on GitHub.")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
