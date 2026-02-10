# Agent Feedback Directory

Session feedback from autonomous Claude Code workflow sessions. Insights are consolidated periodically into the best practices document.

## Current Files

| File | Purpose |
|------|---------|
| `CONSOLIDATED-BEST-PRACTICES.md` | Single source of truth — pain points, best practices, multi-agent coordination patterns, CLAUDE.md update tracker |
| `2026-02-10-roadmap-epics-proposal.md` | Epics proposal for board prioritization (awaiting decision) |
| `session-template.md` | Template for future session summary files |

## Usage

- **New session feedback**: Create a file named `YYYY-MM-DD-session-N-feedback.json` using the template
- **Periodic consolidation**: Merge session files into `CONSOLIDATED-BEST-PRACTICES.md`, then delete the originals
- **Process changes**: Update `CONSOLIDATED-BEST-PRACTICES.md` first, then apply to `CLAUDE.md` via PR
