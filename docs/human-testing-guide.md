# Human Testing Guide

This guide walks you through regression testing the Spice-GUI application. No programming experience is required — just follow the steps in order.

**What is regression testing?** All the code changes (pull requests) have already been merged into the main branch. Your job is to open the app, try each feature, and report whether it works correctly. You are testing the current state of the app, not individual code changes.

### Where to Find What to Test

- **Testing board**: https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3 — this is your home base. Each card is a testing section with checkboxes you can tick off directly on GitHub.
- **Overview issue**: [#278](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/278) — has a table of all testing issues and setup instructions.

### Which Setup Path Should I Use?

| Path | Best for | Prerequisites |
|------|----------|---------------|
| **Option A — Windows Installer** (recommended) | Testing released builds, regression testing the installed app, testers who don't write code | None — everything is bundled |
| **Option B — From Source** | Testing unmerged PRs, testing on macOS/Linux, development work | Python, Git, VSCode |

If you're only running through the testing board and don't need to test code that hasn't been released yet, **use Option A**.

---

## Part 1A: One-Time Setup — Windows Installer (Recommended)

This is the simplest way to get started. No programming tools needed.

### 1A.1 Download and Install

1. Go to the [Releases page](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/releases)
2. Under the latest release, download the file named **`SpiceGUI-vX.Y.Z-win64-setup.exe`**
3. Run the installer — if Windows SmartScreen warns you, click **"More info"** then **"Run anyway"** (this is normal for unsigned software)
4. Follow the installer prompts. For most testers, the defaults are fine

For detailed installation steps and screenshots, see the **[Installation Guide](installation-guide.md)**.

### 1A.2 Verify the App Runs

1. Launch Spice GUI from the Start Menu or desktop shortcut
2. The Spice-GUI window should appear. If it does, setup is complete! Close the app.

> **Trouble?** See the [Installation Guide troubleshooting section](installation-guide.md#troubleshooting) for solutions to common problems.

---

## Part 1A-Extra: Testing the Installer Itself

In addition to testing the app's features, you can verify the installer works correctly. Run through these checks after a fresh install:

| Check | What to verify |
|-------|----------------|
| **Per-user install** | Run the installer and choose "Install for current user only" — no admin prompt should appear |
| **All-users install** | Run the installer and choose "Install for all users" — requires admin, installs to Program Files |
| **.spice file association** | If you selected "Associate .spice files", double-clicking a `.spice` file should open Spice GUI |
| **Desktop icon** | If you selected "Create a desktop icon", a shortcut should appear on the desktop |
| **Start Menu entry** | Spice GUI should appear in the Start Menu |
| **Uninstall** | Uninstall via Settings > Apps — the app should be fully removed |

---

## Part 1B: One-Time Setup — From Source (Windows)

Use this path if you need to test unmerged code or run on macOS/Linux. You only need to do this once on your machine.

### 1B.1 Install Python

1. Go to https://www.python.org/downloads/
2. Download the latest **Python 3.11+** installer for Windows
3. **Important**: On the first screen of the installer, check the box that says **"Add python.exe to PATH"**
4. Click "Install Now" and wait for it to finish
5. Verify it worked: open a terminal (see next step) and type:
   ```
   python --version
   ```
   You should see something like `Python 3.12.x`. If you see an error, restart your computer and try again.

### 1B.2 Open a Terminal in VSCode

Throughout this guide, "terminal" means the built-in terminal inside VSCode:

1. Open VSCode
2. Press **Ctrl + `** (the backtick key, located above Tab) to open the terminal panel at the bottom
3. All commands in this guide should be typed into this terminal

### 1B.3 Clone the Repository

1. Open VSCode
2. Open the terminal (Ctrl + `)
3. Navigate to where you want the project folder. For example:
   ```
   cd Documents
   ```
4. Clone the repository:
   ```
   git clone https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI.git
   ```
5. Open the cloned folder in VSCode: **File > Open Folder** and select the `Spice-GUI` folder you just created

### 1B.4 Set Up the Python Environment

1. Open the terminal in VSCode (Ctrl + `)
2. Create a virtual environment (this keeps project files separate from your system):
   ```
   python -m venv .venv
   ```
3. Activate the virtual environment:
   ```
   .venv\Scripts\activate
   ```
   You should see `(.venv)` appear at the start of your terminal line. **This must be active every time you test.**
4. Install the project's dependencies:
   ```
   pip install -r app/requirements.txt
   ```
   This will download everything the app needs to run. It may take a minute.

### 1B.5 Verify the App Runs

1. Make sure `(.venv)` is showing in your terminal
2. Start the application using one of these methods:
   - **Option A — Play button**: Press **F5**. If a dropdown appears, select **"Run Spice-GUI"**.
   - **Option B — Terminal command**:
     ```
     python app/main.py
     ```
3. The Spice-GUI window should appear. If it does, setup is complete! Close the app.

> **Trouble?** If you see `ModuleNotFoundError`, your virtual environment probably isn't active. Look for `(.venv)` in your terminal. If it's missing, run `.venv\Scripts\activate` and then `pip install -r app/requirements.txt` again.

---

## Part 2: Starting a Testing Session

Do these steps every time you sit down to test.

### 2.1 Launch the App

**If you installed via the Windows installer (Part 1A):**

1. Check for updates: visit the [Releases page](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/releases) and compare the latest version to your installed version (shown in **Help > About**). If a newer version is available, download and run the new installer — it will upgrade in place.
2. Launch Spice GUI from the Start Menu or desktop shortcut.

**If you installed from source (Part 1B):**

1. Open VSCode
2. **File > Open Folder** > select the `Spice-GUI` folder
3. Open the terminal (Ctrl + `)
4. Activate the virtual environment:
   ```
   .venv\Scripts\activate
   ```
5. Pull the latest code:
   ```
   git checkout main
   git pull
   ```
6. Update dependencies (in case new ones were added since last time):
   ```
   pip install -r app/requirements.txt
   ```
7. Press **F5** (and select "Run Spice-GUI" if prompted) or run `python app/main.py` in the terminal.

You are now ready to test!

---

## Part 3: How Testing Works

### 3.1 Pick an Issue From the Board

1. Go to the **[Human Testing board](https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3)**
2. In the **"Ready to Test"** column, pick a card that interests you
3. Drag it to the **"Testing"** column (this tells others you're working on it)
4. Click into the issue — you'll see a checklist of things to try

Here are the available sections:

| Issue | Section | Items | Needs ngspice? |
|-------|---------|-------|----------------|
| [#269](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/269) | Smoke Test | 6 | 1 item |
| [#270](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/270) | Components | 22 | 4 items |
| [#271](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/271) | Selection & Clipboard | 9 | No |
| [#272](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/272) | Wires | 16 | No |
| [#273](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/273) | Undo/Redo | 3 | No |
| [#279](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/279) | Annotations | 7 | No |
| [#274](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/274) | File Operations | 18 | No |
| [#275](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/275) | Simulation | 20 | Yes (all) |
| [#276](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/276) | Plot Features | 14 | Yes (all) |
| [#277](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/277) | User Interface | 17 | No |

You do **not** need to test everything in one session. Pick one section and work through it.

> **No ngspice?** That's fine — skip issues #275 and #276, and skip any individual items marked "Requires ngspice" in other sections.

### 3.2 Work Through the Checklist

Each issue has checkboxes you can check off directly on GitHub (click the checkbox in the issue body). For each item:

1. Try the described action in the app
2. If it works: check the box on the GitHub issue
3. If it fails: click the **report bug** link next to the item (see Part 4 below)

### 3.3 How to Read Test Items

Here are some common patterns in the checklist:

| The checklist says... | What to do |
|---|---|
| "File > Export as PDF" | Click the **File** menu at the top, then click **Export as PDF** |
| "right-click canvas" | Right-click on the drawing area (the grid in the center) |
| "Ctrl+Z undoes the action" | Do something first (like move a component), then press **Ctrl+Z** |
| "save and reload preserves..." | Save (Ctrl+S), close the app, reopen it, open the same file, check it's the same |
| "verify status bar message" | Look at the thin bar at the very bottom of the app window for text |

---

## Part 4: Recording and Reporting Results

### 4.1 Tracking as You Go

Check off items directly on the GitHub issue as you test them. GitHub checkboxes are interactive — just click them.

### 4.2 When Everything in a Section Passes

1. Leave a quick comment on the issue confirming:

   ```
   ### Testing Results

   Tested on [date], Windows [version]
   All items verified — everything works as expected.
   ```

2. On the **[Human Testing board](https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3)**, drag the issue from **"Testing"** to **"Passed"**

### 4.3 When Something Fails

Each checklist item has a **report bug** link next to it. Click it — a new tab opens with the title, item name, testing issue number, and `bug` label already filled in. Fill in the Expected/Actual/Steps/Screenshot blanks and submit. See [How to File a Bug](how-to-file-a-bug.md) for the detailed step-by-step.

After filing, drag the testing issue to **"Bugs Found"** on the **[Human Testing board](https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3)**.

> **Tip**: You can report some items passing and others failing in the same session. Check off what works, leave failing ones unchecked, and click "report bug" for each failure.

### 4.4 If You're Not Sure Whether Something is a Bug

Leave a comment on the testing issue describing what you observed and ask: "Is this expected behavior?" Someone will respond.

---

## Part 5: Moving On

After a testing session:
1. Close the app
2. Your results are saved in your GitHub comments — no need to do anything else
3. Next time, start from **Part 2** again (pull latest code, since new fixes may have been merged)

---

## Quick Reference

### Installer Path (Part 1A)

| Step | What to Do |
|------|------------|
| **Start session** | Check [Releases](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/releases) for updates > launch from Start Menu |
| **Find what to test** | Go to the [Human Testing board](https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3), pick from "Ready to Test" |
| **Claim it** | Drag the issue to "Testing" on the board |
| **Test** | Try each item, check boxes directly on the GitHub issue |
| **All passed** | Comment "all verified", move to "Passed" |
| **Bug found** | Click "report bug" link on the item, fill in blanks, submit. Move to "Bugs Found" ([detailed guide](how-to-file-a-bug.md)) |
| **Not sure** | Comment with question, leave in "Testing" |

### From-Source Path (Part 1B)

| Step | What to Do |
|------|------------|
| **Start session** | Open VSCode > activate venv > `git checkout main && git pull` > `pip install -r app/requirements.txt` |
| **Run the app** | Press **F5** (select "Run Spice-GUI") or `python app/main.py` |
| **Find what to test** | Go to the [Human Testing board](https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3), pick from "Ready to Test" |
| **Claim it** | Drag the issue to "Testing" on the board |
| **Test** | Try each item, check boxes directly on the GitHub issue |
| **All passed** | Comment "all verified", move to "Passed" |
| **Bug found** | Click "report bug" link on the item, fill in blanks, submit. Move to "Bugs Found" ([detailed guide](how-to-file-a-bug.md)) |
| **Not sure** | Comment with question, leave in "Testing" |

---

## Troubleshooting

### Installer Path

| Problem | Solution |
|---------|----------|
| Windows SmartScreen blocks the installer | Click **"More info"** then **"Run anyway"** — this is normal for unsigned software |
| App won't start (missing DLL error) | Install the [Visual C++ Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe) and restart your computer |
| App is quarantined by antivirus | Restore from quarantine and add an exclusion for the Spice GUI install folder. See the [Installation Guide](installation-guide.md#troubleshooting) |
| Simulations fail ("ngspice not found") | Open **Edit > Preferences** and check the ngspice path. See the [Installation Guide](installation-guide.md#troubleshooting) |

### From-Source Path

| Problem | Solution |
|---------|----------|
| `python` is not recognized | Reinstall Python. Make sure **"Add to PATH"** is checked on the installer's first screen. Restart VSCode after installing. |
| `ModuleNotFoundError` when running the app | Your virtual environment isn't active. Run `.venv\Scripts\activate` (look for `(.venv)` in the terminal), then `pip install -r app/requirements.txt`. |
| App window doesn't appear | Run `python app/main.py` in the terminal to see error messages. Copy the error text and post it as a GitHub issue. |
| F5 doesn't show "Run Spice-GUI" | Make sure you opened the `Spice-GUI` folder itself in VSCode (not a parent folder). The file `.vscode/launch.json` must exist in the project. |
| Everything looks weird or broken after pulling | Run `pip install -r app/requirements.txt` — new dependencies may have been added. |
| Terminal says "not recognized" for `git` | Git is not installed. Download it from https://git-scm.com/download/win and restart VSCode. |

---

## For Agents: Adding New Testing Items

When you ship a PR with UI-visible behavior, add a checkbox to the appropriate testing issue. After editing issue checklists, regenerate the pre-filled "report bug" links:

```bash
python scripts/generate_bug_links.py          # dry-run preview
python scripts/generate_bug_links.py --apply   # update all issues on GitHub
```

The script is idempotent — it strips existing links and regenerates them, so it's safe to re-run after adding or editing items.

To add a **new testing issue** to the set, add its number and section name to the `TESTING_ISSUES` dict in `scripts/generate_bug_links.py`.
