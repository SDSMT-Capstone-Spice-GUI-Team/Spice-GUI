# Architecture Decision Records (ADRs)

This directory contains **Architecture Decision Records** - documents that capture important architectural decisions made during the development of SDM Spice.

---

## What is an ADR?

An ADR records the **context, decision, and consequences** of significant architectural choices. They help current and future developers understand:
- **Why** decisions were made
- **What alternatives** were considered
- **What trade-offs** were accepted

---

## When to Create an ADR

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

**Not every decision needs an ADR** - skip for:
- Minor implementation details
- Reversible choices
- Tactical code decisions

---

## How to Create an ADR

### 1. Choose a Number
Number ADRs sequentially: `001-`, `002-`, `003-`, etc.

### 2. Use the Template

```markdown
# ADR XXX: [Short Title]

**Date:** YYYY-MM-DD
**Status:** [Proposed | Accepted | Deprecated | Superseded]
**Deciders:** [Who was involved]

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
```

### 3. File Naming Convention

`XXX-kebab-case-title.md`

Examples:
- `001-local-first-no-user-accounts.md`
- `002-qt6-over-electron.md`
- `003-json-circuit-file-format.md`

---

## Updating ADRs

ADRs are **immutable** once accepted. If a decision changes:
1. Create a new ADR that supersedes the old one
2. Update the old ADR's status to `Superseded by ADR XXX`
3. Explain why the decision changed in the new ADR

---

## Current ADRs

| Number | Title | Status |
|--------|-------|--------|
| [001](001-local-first-no-user-accounts.md) | Local-First Architecture Without User Accounts | Accepted |
| [002](002-mvc-architecture-zero-qt-dependencies.md) | MVC Architecture with Zero PyQt6 Dependencies in Core Logic | Accepted |
| [003](003-json-circuit-file-format.md) | JSON Circuit File Format | Accepted |
| [004](004-ngspice-external-simulation-engine.md) | ngspice as External Simulation Engine | Accepted |
| [005](005-pyqt6-desktop-framework.md) | PyQt6 Desktop Application Framework | Accepted |
| [006](006-pytest-github-actions-testing.md) | pytest and GitHub Actions for Testing Strategy | Accepted |
| [007](007-ruff-linting-code-quality.md) | Ruff for Linting and Code Quality | Accepted |
| [008](008-grid-aligned-layout-10px.md) | Grid-Aligned Layout with 10px Snap | Accepted |

---

## Further Reading

- [Architecture Decision Records (ADR) on GitHub](https://adr.github.io/)
- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) by Michael Nygard
