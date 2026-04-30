# ADR-003: Branching Strategy (develop + main)

**Date**: 2026-02-10 (formalized 2026-02-11)
**Status**: Accepted
**Participants**: Jeremy (Software Architect), Claude Agent (Opus 4.6)
**Last reviewed:** 2026-04-29 — still in effect.

## Decision

The project uses a `develop` + `main` branching model with ephemeral epic and issue branches. Agents develop against `develop`; only the project owner promotes code to `main` after human testing passes.

## Context

With up to 5 concurrent coding agents plus human contributors, all PRs targeting `main` caused frequent merge conflicts (especially in `main_window.py`, ~1700 lines). Students and EE team members needed a stable branch for testing that wouldn't break mid-session. The project needed to decouple "code-complete" from "human-verified."

The solution adds one permanent branch (`develop`) as an integration point, with ephemeral `epic/<name>` branches to contain conflicts within related feature groups.

## Branch Topology

```
main                              <- always human-verified, student-safe
├── develop                       <- integration branch, CI must pass
│   ├── epic/<name>               <- grouped multi-issue feature work
│   │   └── issue-<N>-<description>
│   └── issue-<N>-<description>   <- standalone fixes/features
└── release/vX.Y                  <- cut from develop for releases
```

| Branch | Base | PR Target | Who Merges | Protection |
|--------|------|-----------|------------|------------|
| `main` | — | — | Jeremy | Require PR, no direct push |
| `develop` | `main` | `main` (via release) | PR mgmt agents + Jeremy | Require CI pass |
| `epic/<name>` | `develop` | `develop` | Jeremy reviews | Require CI pass |
| `issue-<N>-*` | epic or develop | epic or develop | Coding agents | — |

## Branch Resolution Algorithm

Agents determine their base branch deterministically:

1. Check issue body for explicit `Base-Branch: <branch>` override
2. Check issue labels for `epic:<name>` — if found, base = `epic/<name>` (create from develop if it doesn't exist)
3. Default: base = `develop`

## Promotion Model

- **Pre-production (current)**: Rolling promotion — Jeremy merges `develop` to `main` per-issue or in small batches after human testing passes
- **Beta releases**: Cut `release/vX.Y` from `develop`, stabilize (bug fixes only), then merge to `main` and tag
- **Gate**: Human testing on Project #3 board must pass before any promotion to `main`

## Consequences

- Agents target `develop` (or `epic/<name>`), never `main` directly
- Merge conflicts are contained within epic branches instead of colliding on `main`
- `main` is always safe for students and stakeholders to clone
- Human testing is the gate between `develop` and `main` (see ADR-002)
- One additional permanent branch (`develop`) to maintain — acceptable overhead for the team size
- Epic branches are ephemeral (weeks) and cleaned up after merging to `develop`

## Full Design Document

For the complete analysis including options considered, team composition, role interactions, and implementation phases, see [Doc/Handoff/design-discussions/2026-02-10-epic-workflow-and-branch-strategy.md](../../Doc/Handoff/design-discussions/2026-02-10-epic-workflow-and-branch-strategy.md). (The associated CLAUDE-md proposal draft has been archived alongside it; CLAUDE.md itself was extracted from this repo to a separate workflow repo — commit `c251561`.)

---

## Reality Check (2026-04-29)

**Decision still in effect.** The full branch topology has been used in production through 2.5 months of multi-agent development:

- `main` remained human-verified throughout the period.
- `develop` was the integration branch; `design-fair` was an epic-style branch that merged into develop on 2026-04-21 (#937).
- Roughly 70 issues across two large merge waves (Apr 1 audit-remediation, Apr 13 Design-Fair polish) shipped through the algorithm in this ADR without merge-conflict crises on `main_window.py` (the original motivating hotspot).
- Branch protection on `main` and `develop` is in place.
- CI runs on `main`, `develop`, and `epic/**` per the algorithm.

The "Pre-production" rolling-promotion model is still in use — the next team will need to perform the first `develop` → `main` promotion since the Design-Fair work landed (see Final Progress Report §6 Future Work, item F1).

The "release/vX.Y" beta-release branch convention has not yet been exercised; cutting `release/v1.0` from the current `develop` is the recommended first action for the successor team.
