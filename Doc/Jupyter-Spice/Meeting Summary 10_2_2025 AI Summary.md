
---
title: "Meeting Notes — Middle Manager"
date: 2025-10-02
tags: [senior-design, meeting, recap, timeline, docs]
participants: [Team, Middle Manager,]
location: Veteran Center (temporary) — targeting EP 241
---

# Meeting 10/02/2025 — Middle Manager

## TL;DR
- **Timeline set:** Charter (next week), **Discovery** (~2 weeks), **Reqs & Specs v1** (by end of Oct), **PDR** pre-break, **CDR** end of semester with working **proof-of-concept** (PoC).
- **Work cadence:** Standing block **Tuesdays 11–5** (+ light top-up hours to average ~10 hrs/person/week).
- **PoC scope (CDR):** Front-end can **read a netlist**, **emulate/run**, and **show outputs**; verify with scope screenshots vs. simulation. UI editing is stretch if time allows.
- **Docs:** Move notes to **Obsidian** (Markdown in repo). Keep **Activity Log** + **Meeting Notes**. Over-document rather than under-document.
- **Logistics:** Secure **EP 241** as dedicated space; align comms with **McGough* (Signal or alt); include **Ben** on meetings.

---

## Decisions & Agreements
- **Deliverables (Fall):**
  - **Project Charter** finalized **next week** with firm dates.
  - **Discovery document** (problem, constraints, goals) **within ~2 weeks**.
  - **Requirements & Specifications v1** **by Oct 31**; revise after **PDR** feedback; lock for **CDR**.
  - **PoC for CDR:** Minimal viable demo = import netlist → emulate → present outputs that match bench measurements.

- **Spring focus:** Feature completeness, testing, polish, and **Design Fair** demo (short, skimmable; poster + 1–2 laptops).

- **Weekly rhythm:** **Tue 11–5** in a shared space; bring other work if blocked, but stay co-located for quick help/unblocking.

---

## Proof-of-Concept (CDR Target Shape)
- **Functionality:** Import **netlist** → simulate/emulate in the front end → display plots/values.
- **Demo circuits:** Start with a **full-wave rectifier**; add one additional canonical circuit.
- **Validation:** Capture **oscilloscope screenshots** of the physical build and show **match** with simulated output.
- **Stretch goal:** Reusable **555 timer** subcircuit to demonstrate composability.

---

## Documentation Standards
- Repo structure example:
- - /project-root  
	/src  
	/netlists  
	/documentation <-- Obsidian vault root  
	Activity Log.md  
	Meeting Notes/  
	2025-10-02 — Middle Manager.md <-- this file  
	Charter/  
	Discovery/  
	Reqs-Specs/  
	Demos/
- **Activity Log:** Brief, link-rich entries pointing to artifacts (Charter, Discovery, Reqs/Specs, notes).
- **Meeting Notes:** One markdown per meeting with TL;DR, decisions, actions, dates.
- Keep demos and posters **simple & skimmable** (Design Fair audience ≈ skim readers).

---

## Timeline (Working)
- **Project Charter:** due **next week**.
- **Discovery complete:** **~2 weeks** from today.
- **Reqs/Specs v1:** **by Oct 31** (target).
- **PDR:** **pre-Thanksgiving** (exact date TBD) → incorporate feedback.
- **CDR:** **end of semester** with PoC demo.

---

## Action Items
- [ ] **Draft Project Charter** with concrete dates and milestones  
    _Owner:_ Team · _Due:_ **Next Tue** · _Links:_ (add)
- [ ] **Finish Discovery doc** (problem, constraints, goals)  
    _Owner:_ Team · _Due:_ **~2 weeks** · _Links:_ (add)
- [ ] **Reqs/Specs v1 outline → v1 complete**  
    _Owner:_ Team · _Start:_ now · _Due:_ **Oct 31**
- [ ] **Workspace request (EP 241)** — email **McGough (cc: team) re: access & storage; include **Ben**  
    _Owner:_ Jeremy · _Due:_ **Today/Tomorrow** · _Status:_ ( )
- [ ] **Set comms channel with McGough** (Signal or alternative) & share Tue 11–5 cadence  
    _Owner:_ Jeremy · _Due:_ **This week**
- [ ] **Install Obsidian** and create `/documentation` vault; add **Activity Log** + **Meeting Notes** templates  
    _Owner:_ All · _Due:_ **Next Tue**
- [ ] **Demo plan** — pick PoC circuits and define sim vs. bench **test protocol** (how we’ll match outputs)  
    _Owner:_ Team · _Due:_ **1 week before PDR**
- [ ] **Room for Tuesdays** — hold consistent space 11–5 (or fallback); record location in Activity Log  
    _Owner:_ Team · _Due:_ **Before next Tue**
- [ ] **Add Slack link** to **timeline PPT** in `/documentation/Index.md`  
    _Owner:_ (assign) · _Due:_ **Next Tue**

---

## Risks & Mitigations
- **No dedicated space** → hardware validation slows.  
**Mitigation:** Early request for **EP 241** (or equivalent); escalate if blocked.
- **Soft deadlines** → drift.  
**Mitigation:** Charter with hard dates; quick review at start of each Tuesday block.
- **Under-documentation** → rework later.  
**Mitigation:** “Docs first” habit; log decisions immediately in Obsidian.
- **Scope creep (UI editing vs emulation)** → CDR at risk.  
**Mitigation:** Lock PoC scope now; defer editing features unless ahead of schedule.

---

## Open Questions
- Exact **PDR/CDR dates** from course staff?  
- Final decision on **Signal vs. other** comms with McNew?  
- Any additional **course-required docs** (PCR expectations, activity log format)?  
- Confirm **equipment availability** (scopes, probes) and check-out/storage policy for EP 241.

---

## Next 7-Day Checklist
- [x] Everyone installs **Obsidian**; `/documentation` vault exists in repo.
- [ ] **Charter** draft ready for Tuesday review.
- [ ] **Email McNew** about **EP 241**, include **Ben**, propose Tue 11–5 cadence & comms.
- [ ] PoC circuit shortlist chosen (**rectifier + one more**); initial test protocol noted.
- [ ] Slack link to **timeline PPT** added to Obsidian **Index.md**.

---

### Links & Artifacts
- Timeline PPT (Slack): _(add link)_  
- Charter (draft): _(add link)_  
- Discovery (draft): _(add link)_  
- Reqs/Specs v1: _(add link)_  
- Demo circuits & scope captures: _(add links)_


