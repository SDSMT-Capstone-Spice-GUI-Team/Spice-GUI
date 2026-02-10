# Roadmap Restructure: Epics for Agent Prioritization

**Date:** 2026-02-10
**Status:** Proposal — awaiting decision

---

## Problem

The Roadmap (`wiki/Roadmap.md`) is a human-facing changelog/vision document. Agents don't read it during their work loop — they read `CLAUDE.md` and query the GitHub board. The board is nearly drained:

- **Ready:** #147 (print preview) only
- **In Progress:** #127 (wire labels), #144 (Monte Carlo)
- **Backlog:** Empty

The Roadmap has Phases 2-7 of aspirational features not represented as issues, and 25+ lines of backward-looking "Recently Completed" that don't aid prioritization.

## Existing Board Infrastructure

The board already has fields that support Epics:

| Field | Values |
|-------|--------|
| **Priority** | P0, P1, P2 |
| **Size** | XS, S, M, L, XL |
| **Parent issue** | GitHub's native Epic mechanism |
| **Sub-issues progress** | Auto-tracked |

Field IDs (cached):
- Priority field: query `gh project field-list 2`
- Priority options: P0=`79628723`, P1=`0a877460`, P2=`da944a9c`
- Size options: XS=`6c6483d2`, S=`f784b110`, M=`7515a9f1`, L=`817d0097`, XL=`db339eb2`

## Proposed Epic Structure

| Epic | Maps to Roadmap | Example child issues | Priority |
|------|-----------------|---------------------|----------|
| **Stability & Polish** | Phase 1 tail | #26 (properties panel bug), #127 (wire labels), #147 (print), bug fixes | P0 |
| **Advanced Simulation** | New | #144 (Monte Carlo), sensitivity analysis, convergence improvements | P1 |
| **Export & Sharing** | Phase 2 | Circuit reports, template library, batch CLI operations | P1 |
| **Instructor Tools** | Phase 3 | Assignment templates, verification scripts, rubrics | P2 |
| **Scripting & Automation** | Phase 6 | Python API, batch simulation, Jupyter integration | P2 |

## How It Would Flow

```
Roadmap (wiki)           Board (GitHub Projects)         Agent (CLAUDE.md)
---------------          ----------------------         -----------------
Defines Epics    ->      Epic issues (Parent)     ->    "Query Ready items,
and priority             with child issues               prefer highest-
order                    tagged P0 > P1 > P2             priority Epic"
```

## Changes Required

### 1. Create Epic issues on GitHub
- Create one issue per Epic with the `epic` label
- Each Epic issue contains a task list linking to child issues
- Use GitHub's native "Parent issue" / "Sub-issues" to link them

### 2. Restructure Roadmap (`wiki/Roadmap.md`)
- **Replace** the 25-line "Recently Completed" list with a compact version history table
- **Replace** Phases 2-7 aspirational feature lists with links to the actual Epic issues on the board (single source of truth — no duplication)
- **Add** a "Priority Queue" section — the one place to update when steering agent work direction

### 3. Update CLAUDE.md agent workflow
Change step 2 from:
> "Query board for next **Ready** item (prefer higher priority, lower issue number)"

To:
> "Query board for next **Ready** item. Prefer P0 over P1 over P2. Within the same priority, prefer the Epic closest to completion (most sub-issues done). Within the same Epic, prefer lower issue number."

### 4. Populate the board
- Create child issues under each Epic for concrete work items
- Set Priority and Size on each
- Move items to Ready as appropriate

## Benefits

- **Agents get strategic direction** — they know what *area* of the product to advance, not just which issue number is lowest
- **Single source of truth** — Roadmap links to Epics on the board instead of duplicating feature lists
- **Easy steering** — change agent focus by adjusting Epic priorities, not individual issues
- **Progress visibility** — GitHub's sub-issues progress bar shows Epic completion at a glance
- **Board doesn't go empty** — Epics provide a natural pipeline for creating new Ready items

## Wiki Updates Already Completed (this session)

Before this proposal, the following wiki pages were updated to reflect all In Review / completed features:

- **Components.md** — Added 11 new components (dependent sources, semiconductors, switches)
- **Keyboard-Shortcuts.md** — Full rewrite: all current shortcuts, configurable keybindings section
- **Analysis-Types.md** — Added Temperature Sweep, Parameter Sweep, FFT/Harmonic Analysis sections
- **User-Interface-Overview.md** — Full rewrite: dark mode, probes, cursors, annotations, auto-save, all menus
- **File-Formats.md** — Export/import sections updated from "Planned" to "Implemented", added SPICE syntax for new components
- **Home.md** — Expanded feature list, updated status to "Phase 1 complete"
- **Roadmap.md** — Updated Phase 1 features (15 -> 30 items), Recently Completed, In Progress, Next Up

## In Review Items on Board

18 items are in "In Review" status. Almost all are closed/merged:
- #145, #56, #53, #78, #77, #76, #121, #123, #124, #32, #139, #140, #141, #142, #143, #146, #154 — all **closed**
- #26 (Properties panel bug) — still **open**, needs attention

These should be moved to Done (except #26 which needs investigation).
