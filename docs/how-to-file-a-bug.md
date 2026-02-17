# How to File a Bug During Testing

You found something broken while testing — nice catch! This guide walks you through reporting it step by step.

**Where you are**: You're working through a testing checklist (e.g., #270 Components) and one of the items didn't work as expected.

**What you'll do**: Take a screenshot, comment on the testing issue, file a bug issue, and update the board. Four steps, about 5 minutes.

---

## Step 1: Take a Screenshot

Before you do anything else, capture what you're seeing:

1. Press **Windows + Shift + S** to open the snipping tool
2. Drag to select the area showing the problem
3. The screenshot is now on your clipboard — you'll paste it later

> **Tip**: If the bug involves something disappearing or a sequence of actions, take the screenshot right when the problem is visible.

---

## Step 2: Comment on the Testing Issue

You should already have the testing issue open (e.g., #270 Components). Scroll to the bottom and add a comment:

1. Click the **comment box** at the bottom of the issue
2. Copy and paste this template, then fill it in:

   ```
   **Item**: (copy the checkbox text from above)
   **Expected**: (what should have happened)
   **Actual**: (what actually happened)
   **Steps to reproduce**:
   1. (first thing you did)
   2. (next thing you did)
   3. (when it broke)
   ```

3. Paste your screenshot — click in the comment box and press **Ctrl + V**. GitHub will upload it automatically.
4. Click the green **"Comment"** button

### Example

> **Item**: Rotation works for all orientations
> **Expected**: Diode should render correctly at 270 degrees
> **Actual**: Diode disappears from the canvas after pressing R three times
> **Steps to reproduce**:
> 1. Place an LED from the component palette
> 2. Press R three times to rotate to 270 degrees
> 3. Component vanishes from the canvas
>
> *(screenshot pasted here)*

---

## Step 3: Create a Bug Issue

Now you'll file a separate issue so the developers can track and fix the bug.

### 3a. Open the New Issue Page

Open a **new tab** and go to:
https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/new

### 3b. Write the Title

Start with `BUG:` followed by a short description of what went wrong. Examples:

- `BUG: Diode disappears after rotating 270 degrees`
- `BUG: Wire doesn't connect to resistor terminal`
- `BUG: Undo crashes app after deleting annotation`

### 3c. Write the Body

Copy and paste the comment you just wrote in Step 2 — you don't need to rewrite it.

Then add one line at the bottom:

```
Found during #270 testing
```

Replace `#270` with whichever testing issue you were working from. GitHub automatically turns `#270` into a clickable link.

### 3d. Add the Bug Label

1. In the **right sidebar**, click **"Labels"**
2. Type `bug` in the search box
3. Click the **`bug`** label to select it

### 3e. Submit

Click the green **"Submit new issue"** button.

---

## Step 4: Update the Testing Board

1. Go to the **[Human Testing board](https://github.com/orgs/SDSMT-Capstone-Spice-GUI-Team/projects/3)**
2. Find your testing issue in the **"Testing"** column
3. Drag it to the **"Bugs Found"** column

**You're done!** The developers will see the bug and prioritize it. You don't need to do anything else.

---

## Quick Reference

| Step | What | Where |
|------|------|-------|
| 1 | Take a screenshot | **Win + Shift + S** |
| 2 | Comment on the testing issue | Bottom of the testing issue (e.g., #270) |
| 3 | Create a bug issue | [New issue page](https://github.com/SDSMT-Capstone-Spice-GUI-Team/Spice-GUI/issues/new) |
| 4 | Move the card on the board | Testing board → "Bugs Found" |

---

## FAQ

### What if I find multiple bugs in one testing section?

File a separate bug issue for each one (repeat Steps 1–3 for each). You only need to move the card to "Bugs Found" once.

### What if some items pass and some fail?

That's normal. Check off the items that work, leave the failing ones unchecked, and file bugs for the failures.

### What if I'm not sure whether it's a bug?

Leave a comment on the testing issue describing what you observed and ask: "Is this expected behavior?" Someone will respond. You don't need to file a bug issue if you're unsure.

### Do I need to assign the bug to someone?

No. Leave it unassigned — the developers will triage and assign it.
