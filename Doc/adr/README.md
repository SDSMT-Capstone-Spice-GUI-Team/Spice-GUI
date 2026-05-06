# Architecture Decision Records (ADRs)

This directory captures the **architectural decisions** made during the development of SDM Spice — the *why*, *what was considered*, and *what trade-offs were accepted* for each significant choice.

> **Consolidated 2026-04-29.** ADRs were previously split across `Doc/decisions/` and `docs/adr/` with conflicting numbering. All foundational ADRs were renumbered into the 004–011 range under `Doc/adr/`; ADRs 001–003 (added 2026-02-11) keep their original numbering. See [Doc/Handoff/design-discussions/](../Handoff/design-discussions/) for long-form design discussions that informed but are not themselves ADRs. Architecture *guides* (canvas internals, GUI protocols) live in [Doc/architecture/](../architecture/).

---

## Current ADRs

| # | Title | Status | Last reviewed |
|---|-------|--------|---------------|
| [001](001-mvc-testability.md) | MVC Architecture for Testability | Accepted | 2026-04-29 |
| [002](002-tiered-testing.md) | Tiered Testing Model | Accepted | 2026-04-29 |
| [003](003-branching-strategy.md) | Branching Strategy (develop + main) | Accepted | 2026-04-29 |
| [004](004-local-first-no-user-accounts.md) | Local-First Architecture Without User Accounts | Accepted | 2026-04-29 |
| [005](005-mvc-architecture-zero-qt-dependencies.md) | MVC Architecture with Zero PyQt6 Dependencies in Core Logic | Accepted | 2026-04-29 |
| [006](006-json-circuit-file-format.md) | JSON Circuit File Format | Accepted (schema_version v1 added Apr 2026) | 2026-04-29 |
| [007](007-ngspice-external-simulation-engine.md) | ngspice as External Simulation Engine | Accepted | 2026-04-29 |
| [008](008-pyqt6-desktop-framework.md) | PyQt6 Desktop Application Framework | Accepted | 2026-04-29 |
| [009](009-pytest-github-actions-testing.md) | pytest and GitHub Actions for Testing Strategy | Accepted | 2026-04-29 |
| [010](010-ruff-linting-code-quality.md) | Ruff for Linting and Code Quality | Accepted, **partially superseded** (black + isort + bandit added) | 2026-04-29 |
| [011](011-grid-aligned-layout-10px.md) | Grid-Aligned Layout with 10px Snap | Accepted | 2026-04-29 |

### Topical groupings

- **Foundation:** [004 Local-first](004-local-first-no-user-accounts.md) · [005 MVC](005-mvc-architecture-zero-qt-dependencies.md) · [006 JSON format](006-json-circuit-file-format.md) · [007 ngspice](007-ngspice-external-simulation-engine.md) · [008 PyQt6](008-pyqt6-desktop-framework.md) · [011 Grid 10px](011-grid-aligned-layout-10px.md)
- **Testing & quality:** [001 MVC for testability](001-mvc-testability.md) · [002 Tiered testing](002-tiered-testing.md) · [009 pytest + GHA](009-pytest-github-actions-testing.md) · [010 Ruff (+ black, isort, bandit)](010-ruff-linting-code-quality.md)
- **Process:** [003 Branching strategy](003-branching-strategy.md)

---

## What is an ADR?

An ADR records the **context, decision, and consequences** of a significant architectural choice. They help current and future developers understand:
- **Why** decisions were made
- **What alternatives** were considered
- **What trade-offs** were accepted

Each ADR in this directory now ends with a **Reality Check** section dated 2026-04-29 noting any drift between the original decision and current practice. If the next team finds an ADR materially out of date, the convention below ("Updating ADRs") applies.

---

## When to create a new ADR

Create an ADR when making decisions about:
- System architecture (local vs cloud, monolith vs services)
- Technology choices (frameworks, libraries, databases)
- Design patterns and conventions
- Security or privacy approaches
- Integration strategies
- Performance trade-offs

**Examples:**
- "Should we use a REST API or GraphQL?"
- "Do we need user accounts?"
- "Which database should we use?"
- "How should we handle circuit file format?"

**Not every decision needs an ADR** — skip for:
- Minor implementation details
- Reversible choices
- Tactical code decisions

If the decision benefits from long-form discussion (multiple options, role/team analysis, phased rollout), draft it as a **design discussion** in `Doc/Handoff/design-discussions/` first; once accepted, distil it into an ADR here that links back to the discussion. ADR-003 + the 2026-02-10 epic-workflow discussion are the worked example.

---

## How to create an ADR

### 1. Choose a number
Sequentially after the highest existing ADR (currently 011 — next is **012**).

### 2. Use the template

```markdown
# ADR XXX: [Short Title]

**Date:** YYYY-MM-DD
**Status:** [Proposed | Accepted | Deprecated | Superseded by ADR YYY]
**Deciders:** [Who was involved]
**Last reviewed:** YYYY-MM-DD

---

## Context
What is the issue we're addressing? What constraints exist?

## Decision
What did we decide to do?

## Consequences
What becomes easier or harder as a result?

### Positive
✅ Benefits of this decision

### Negative
❌ Drawbacks or limitations

### Mitigation Strategies
How we'll address the negative consequences

## Alternatives Considered
What other options did we evaluate and why were they rejected?

## References
Links to relevant code, docs, or discussions

## Reality Check (added on later review)
Drift between this decision and current practice. Empty until first revisit.
```

### 3. File naming convention

`XXX-kebab-case-title.md`

Examples:
- `004-local-first-no-user-accounts.md`
- `008-pyqt6-desktop-framework.md`
- `011-grid-aligned-layout-10px.md`

---

## Updating ADRs

ADRs are **immutable once accepted** for the original decision text. To reflect drift or new context:

- **Small clarification or evidence update:** add or extend the **Reality Check** section at the end of the existing ADR. Do not rewrite the original Context / Decision / Consequences body.
- **Decision changed:** create a new ADR that **supersedes** the old one. Update the old ADR's status line to `Superseded by ADR YYY`. Explain why the decision changed in the new ADR.
- **Decision partially changed:** mark the original `Accepted, partially superseded` and explain the affected scope in a Reality Check (see ADR-010 for an example).

---

## Further reading

- [Architecture Decision Records (ADR) on GitHub](https://adr.github.io/)
- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) by Michael Nygard
