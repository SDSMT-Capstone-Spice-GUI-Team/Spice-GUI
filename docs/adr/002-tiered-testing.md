# ADR-002: Tiered Testing Model

**Date**: 2026-02-11
**Status**: Accepted
**Participants**: Jeremy (Software Architect), Claude Agent (Opus 4.6)

## Decision

Quality assurance uses a two-gate model that separates automated testing (blocks merge) from human testing (blocks release/promotion to `main`).

## Context

Claude Code agents develop features faster than humans can test them. During a single session, agents may complete 3-8 issues. This created a 132-item manual testing backlog. The project needs both rapid development throughput and verified quality.

The solution is to decouple the merge gate (fast, automated) from the verification gate (slower, human-driven). Agents stay productive; humans maintain quality accountability.

## Gate Model

```
Agent completes issue
        │
        ▼
┌─────────────────────┐
│   GATE 1: PR Merge   │  Automated, blocks merge to develop
│                       │
│  ✓ CI green (tests    │
│    + lint + format)   │
│  ✓ Tests added at     │
│    appropriate layer  │
│  ✓ Human testing item │
│    filed if needed    │
└───────────┬───────────┘
            │
            ▼
┌─────────────────────┐
│   GATE 2: Promotion  │  Human, blocks merge to main
│                       │
│  ✓ Human testing      │
│    checklist passed   │
│  ✓ Bugs filed and     │
│    triaged            │
└───────────────────────┘
```

## Test Expectations by Change Type

| Change Type | Automated Tests | Human Testing Item? |
|-------------|----------------|-------------------|
| Bug fix | ≥1 regression test that reproduces the bug | Only if visual/interaction |
| New feature | Tests covering core behavior at appropriate layer | Yes, for UI-visible behavior |
| Refactor | Existing tests must pass, no new tests required | No |
| UI-only | Structural assertions where applicable | Yes, always |

Tests should cover the *behavior*, not just the *count*. A single test that exercises the real code path is worth more than five tests that assert obvious properties.

## Human Testing Infrastructure

- **Testing board**: [Project #3](https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3) with columns: Ready to Test → Testing → Passed / Bugs Found
- **Testing issues**: #269-#279 organized by feature area (Smoke Test, Components, Wires, etc.)
- **Testing guide**: `docs/human-testing-guide.md` for non-engineer testers
- **Bug flow**: failure → comment on testing issue → file separate `bug` issue → Backlog on dev board

## Visual Testing Strategy

- **Now**: Structural/geometric assertions (terminal positions, bounding boxes, z-order, scene membership). These survive visual redesigns.
- **Deferred**: Pixel-baseline screenshot regression testing. Will be added after human testing feedback stabilizes visual preferences (component symbols, color schemes, theme styling).

## Consequences

- Agents stay fast — Gate 1 is fully automated
- Human testing is decoupled from merge timing — no bottleneck on development
- Release/promotion to `main` requires verified code — students always get tested builds
- The human testing board is a living document — agents add items as they ship features
- Bugs from human testing enter the dev board at Backlog for triage
