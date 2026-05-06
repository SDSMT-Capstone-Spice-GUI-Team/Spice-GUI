# How to File a Bug During Testing

You found something broken while testing — nice catch! This guide walks you through reporting it step by step.

**Where you are**: You're working through a testing checklist (e.g., #270 Components) and one of the items didn't work as expected.

**What you'll do**: Take a screenshot, click "report bug", fill in a few blanks, and update the board. Three steps, about 3 minutes.

---

## Step 1: Take a Screenshot

Before you do anything else, capture what you're seeing:

1. Press **Windows + Shift + S** to open the snipping tool
2. Drag to select the area showing the problem
3. The screenshot is now on your clipboard — you'll paste it later

> **Tip**: If the bug involves something disappearing or a sequence of actions, take the screenshot right when the problem is visible.

---

## Step 2: Click "report bug" and Fill In the Form

Every checklist item has a **report bug** link next to it. Here's what to do:

### 2a. Click the Link

Find the checklist item that failed. At the end of the line you'll see a blue **report bug** link. Click it.

This opens a new browser tab with a pre-filled bug report. The title, item name, testing issue number, and `bug` label are already set for you.

### 2b. Fill In the Blanks

The form has a few fields for you to complete:

| Field | What to write |
|-------|---------------|
| **Expected** | What should have happened |
| **Actual** | What actually happened |
| **Steps to reproduce** | Number the steps you took, starting from the app being open |
| **Screenshot** | Click in the field and press **Ctrl + V** to paste your screenshot |

### 2c. Submit

Click the green **"Submit new issue"** button. That's it — the bug is filed with the right label and a link back to the testing issue.

### Example

Here's what a filled-in bug report looks like:

> **Item**: Rotation works for all orientations
> **Testing issue**: #270
>
> **Expected**: Diode should render correctly at 270 degrees
>
> **Actual**: Diode disappears from the canvas after pressing R three times
>
> **Steps to reproduce**:
> 1. Place an LED from the component palette
> 2. Press R three times to rotate to 270 degrees
> 3. Component vanishes from the canvas
>
> **Screenshot**: *(pasted image here)*

---

## Step 3: Update the Testing Board

1. Go to the **[Human Testing board](https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3)**
2. Find your testing issue in the **"Testing"** column
3. Drag it to the **"Bugs Found"** column

**You're done!** The developers will see the bug and prioritize it. You don't need to do anything else.

---

## Quick Reference

| Step | What | Where |
|------|------|-------|
| 1 | Take a screenshot | **Win + Shift + S** |
| 2 | Click **report bug** next to the failing item, fill in blanks, submit | Link on the checklist item |
| 3 | Move the card on the board | Testing board → "Bugs Found" |

---

## FAQ

### What if I find multiple bugs in one testing section?

File a separate bug issue for each one (click "report bug" on each failing item). You only need to move the card to "Bugs Found" once.

### What if some items pass and some fail?

That's normal. Check off the items that work, leave the failing ones unchecked, and click "report bug" for the failures.

### What if I'm not sure whether it's a bug?

Leave a comment on the testing issue describing what you observed and ask: "Is this expected behavior?" Someone will respond. You don't need to file a bug issue if you're unsure.

### Do I need to assign the bug to someone?

No. Leave it unassigned — the developers will triage and assign it.

### What if the "report bug" link is missing?

You can file a bug manually: go to the [new issue page](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/new?template=bug-from-testing.md&labels=bug), fill in the template, and add `Found during #NNN testing` in the body (replace `#NNN` with your testing issue number).
