


## Executive Summary
Aligned on vision and process for a freshman-friendly SPICE GUI: drag-and-drop canvas that generates a netlist for NGSpice. Set weekly cadence with the middle manager, chose Slack for formal comms, Obsidian for docs, and GitHub with a strict PR workflow. Near-term focus: stand up Slack + calendar, finalize repo workflow, populate backlog with prioritized issues, and progress the MVP (canvas → wiring → netlist → run).

---

## Attendees
- **Middle Manager:** Ben (EE; advisor/mentor/manager)
- **Team:** Jeremy (CS), John (CS), Marc (EE), Micah (EE)

## Project Goal
- Build a **Visio/Draw.io-style SPICE GUI** for freshmen EEs: place components, wire them, **generate SPICE netlist**, and run via **NGSpice**.
- **MVP:** canvas, components (GND, V+, resistor), add/connect items, generate netlist, run, read node data.
- **Approach:** Agile sprints; iterate fast with test circuits from EE side.

## Current Status
- Git branching scheme drafted; test branch pushed.
- Initial **canvas window** PR opened (awaiting/confirming review).
- EE test circuits in progress for verification.
- Discovery underway on SPICE file/stat conventions.

## Decisions
### Cadence & Meetings
- **Weekly with manager:** **Thu 11:00–11:30 (extendable to 12:00)**.
- **Stakeholder (Miguel):** ~every other Thu at 11:00 (availability dependent).
- Create a **Google Calendar** invite for all attendees.
- Meetings may be **recorded**; save summary + (optional) raw transcript.

### Communication
- **Primary (formal):** **Slack** workspace/channel for team + manager.
- **Secondary (informal):** SMS group for quick pings.
- GitHub is the source of truth for files; screenshots OK in Slack.

### Documentation
- **Platform:** **Obsidian** (Markdown + LaTeX).
- Repo `/docs` (or `/documentation`) holds Activity Log, Meeting Notes, specs.
- Awaiting **faculty templates**; manager may provide stop-gap docs.

### Version Control (GitHub)
- **Repo structure:**
  - `/app` → **all source code** (`.py`, etc.)
  - `/docs` → Obsidian markdown
  - `/testing` → test assets as needed
- **Branch naming:** `<owner>/<short-topic>`; append issue #s (e.g., `john/issue-42`).
- **Workflow:** **Pull → Edit → Commit → Push → PR**; resolve **all PR conversations** before merge.
- **Always pull before editing.**
- **No secrets/personal info** in Git (API keys, tokens, IDs).

### Issue Tracking / Backlog
- Use GitHub Issues with:
  - Clear description + acceptance criteria
  - **Priority:** 1-Low, 2-Med, 3-High, 4-Critical, 5-Beyond-Critical
  - Labels: `milestone-*`, `bug`, `feature`, `doc`, etc.
- Engineers pull the highest priority ready item; priorities can be escalated.

## Risks / Dependencies
- **Faculty deliverables & deadlines** still **pending** (noted ~15% grade weight for docs).
- **Stakeholder travel** → every-other-week cadence.
- Tool fragmentation risk mitigated by standardizing on **Slack + GitHub + Calendar**.

## Near-Term Plan (Next 7–10 Days)
1. **Comms & Calendar:** Create Slack channel; invite manager; send Google Calendar for Thu 11:00–12:00.
2. **Repo Hygiene:** Confirm manager GitHub access (membership + 2FA); add **CONTRIBUTING.md**.
3. **Backlog Build-out:** Convert MVP/whiteboard items to issues with priorities & acceptance criteria; seed milestones.
4. **MVP Progress:**
   - Canvas: place/move/delete components.
   - Wiring: connect pins; basic validation.
   - Netlist: export from graph; smoke-test in NGSpice.
   - EE test circuits: divider, RC, op-amp buffer, etc.
5. **Docs:** Initialize Obsidian vault in `/docs`; add Architecture Overview, MVP spec, Meeting Notes, Activity Log template.

## Open Questions
- **Faculty:** When are official **deliverables + deadlines** and templates arriving?
- **Stakeholder:** Any constraints on **component palette** for MVP? Netlist format expectations?
- **Manager:** Preferred **labels/milestones** naming; any additional reporting cadence beyond weekly?

---

## Action Items
| #   | Action                                                                                 | Owner       | Due          |
| --- | -------------------------------------------------------------------------------------- | ----------- | ------------ |
| 1   | Create **Slack** workspace/channel; invite manager                                     | Jeremy/John | ASAP         |
| 2   | Send **Google Calendar** invite (Thu 11:00–12:00)                                      | Marc        | ASAP         |
| 3   | Confirm **GitHub access** for manager (membership + 2FA)                               | John        | ASAP         |
| 4   | Add **CONTRIBUTING.md** (branching, PR, priorities)                                    | Jeremy      | Next meeting |
| 5   | Populate **backlog** with MVP issues + priorities + milestones                         | Team        | Next meeting |
| 6   | Prepare **EE test circuits** for validation                                            | Micah       | Next meeting |
| 7   | Land **canvas/wiring/netlist** skeleton PRs                                            | Jeremy/John | Next meeting |
| 8   | Initialize **Obsidian** `/docs` with templates (Activity Log, Meeting Notes, MVP spec) | John        | Next meeting |

## Notes
- Implementation language is **Python** (acknowledged typing/indentation pitfalls).
- Do **not** touch `/app` unless editing source; other top-level folders OK for docs/design assets.
