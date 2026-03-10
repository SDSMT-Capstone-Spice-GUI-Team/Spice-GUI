

## What we’re building (in simple terms)
A tiny desktop app where you can drop basic electronic parts (like a battery and resistors) onto a blank area, tell the app how those parts are connected, press **Run**, and get numbers back from a simulator that say what the voltages are.  
Think of it like a super-basic circuit sandbox.

---

## Where things stand
- A shared workspace on **GitHub** is set up.  
  - **GitHub** = the team’s online folder for code plus a to-do board.  
  - A **Project board** (our to-do list) exists, and a **code repo** (the actual code folder) now exists too.  
  - You and John will get/accept invites and start adding tasks/ideas there.  
- **Tech choice:** use Qt (a popular toolkit) to build the app window and the draggable area.  
- **People:** you (lead) and John will split work so you’re not editing the same file at the same time.  
- **Meetings:** weekly Thursdays at **11:00 AM** with Dr. McGough.  
  - Meeting with Dr. McGough today at 2:30 PM, but we prefer future slots before 2 PM.

---

## How we’ll work (no jargon)
- The board has three simple lanes:  
  - **To Do** = backlog of tasks/ideas  
  - **Doing** = in progress  
  - **Done** = completed  
- Anyone can add a card to **To Do** when they think of a feature/bug/idea.  
- In check-ins we pick what’s realistic for the next week and move those to **Doing**.  
- Record short screen videos of other circuit tools you like; we’ll copy the good interaction ideas.

---

## First milestone: the tiniest useful version (our MVP)
We’re aiming for a bare-bones version that proves end-to-end flow:

1. A blank workspace you can click on (**canvas**).  
2. Add parts with a right-click menu (no fancy side palette needed at first).  
   - Parts for v0.0: **Resistor**, **Voltage Source (battery)**, **Ground**  
3. Tell the app what’s connected to what by typing simple labels on the little “pins” of each part.  
   - Example: label both pins you want connected as `mid`; label ground as `0` (zero).  
   - Why labels instead of drawing wires? It’s way faster to build and still unambiguous.  
4. Build a text description of the circuit (**netlist**) from those parts + labels.  
   - A netlist is literally just lines of text like `R1 in mid 1k` that a simulator understands.  
5. Run the simulator (**ngspice**) and show the plain text results on screen.  
   - Pretty graphs come later; numbers are enough for v0.0.  
6. Demo circuit: a **voltage divider** (a battery feeding two resistors in series).  
   - We’ll read the voltage at the junction between the resistors and verify it matches the textbook formula.

---

## What’s not required yet
- Fancy side palettes  
- Wire-drawing  
- Beautiful plots  

(*Nice to have later, not needed for v0.0.*)

---

## Who is doing what
_(subject to re-confirm in chat if Jeremy wants to reassign)_

- **GUI/Canvas lane (front end)**  
  - Make the window, the blank area, right-click “add part,” drag/move parts, type pin labels, pan/zoom.  
  - Show simple warnings (e.g., “you forgot ground”).  

- **Models/Simulator lane (back end)**  
  - Define how a “part” is stored in code (its id, pins, and values like “1kΩ”).  
  - Convert the on-screen parts + labels into a proper netlist text file.  
  - Run ngspice, capture its text, and display it.  

- **Project/Infra**  
  - Repo scaffolding (folders, README, install steps), issue/PR templates, labels, basic CI checks.  
  - Lock in recurring Thursday 11am; ask McGough for pre-2p windows.

---

## What “done” looks like for v0.0
- You can place a **battery**, **ground**, and **two resistors** on the canvas.  
- You can type labels on their pins (ground is labeled `0`).  
- Clicking **Run** creates a valid netlist file and calls ngspice.  
- The results pane shows voltages, including the “middle” node of the divider, matching the expected `R2/(R1+R2) × Vin`.

---

## Immediate next steps (today → this week)
- Accept the GitHub invite. Drop in task cards for anything you think we’ll need.  
- **Front end:** spike the canvas with right-click “Add Resistor/Voltage/Ground,” drag to move, click pin to label.  
- **Back end:** stub a netlist like the example below, wire up a “Run” button to launch ngspice, and print stdout.  
- Prepare a one-click **“Voltage Divider”** preset that places parts with default labels so we can demo fast.  
- Send scheduling requests (Thu 11a weekly; Mcgough before 2p).

---
![[Pasted image 20251002123819.png]]
![[Pasted image 20251002123835.png]]

Ignore `.control` for this version.  
The one we will be looking for will be **`.op` (DC operating point)**, not **DC sweep**.

---

## Tiny glossary (even plainer)

- **GitHub Project board**: our shared to-do list with cards you drag from “To Do” to “Done.”

- **Repo (repository)**: the shared code folder on GitHub.

- **Qt**: a toolkit to make app windows, buttons, and the draggable canvas.

- **Canvas**: the blank area where we drop parts.

- **Ground / node 0**: the universal “zero volts” reference point in circuits.

- **Labeling pins**: typing the same name on two pins means “these are connected.”

- **Netlist**: a simple text file that lists each part and which pins are connected to which names.

- **ngspice**: the calculator program that reads the netlist and outputs voltages/currents.

- **Voltage divider**: two resistors in a row; the middle point has a fraction of the battery voltage.

- **MVP**: the smallest, simplest app that does something genuinely useful end-to-end.
