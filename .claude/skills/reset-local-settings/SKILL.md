---
name: reset-local-settings
description: Clean up .claude/settings.local.json which accumulates one-off approved commands over sessions. Backs up and resets to minimal config.
user-invocable: true
---

## What This Does

`.claude/settings.local.json` accumulates one-off command approvals over time (hardcoded IDs, escaped PowerShell commands, old env paths). This skill resets it to a clean state.

## Steps

1. Check current file size:
   ```bash
   wc -l .claude/settings.local.json
   ```

2. Back up the file:
   ```bash
   cp .claude/settings.local.json .claude/settings.local.json.bak
   ```

3. Reset to minimal config — write this content to `.claude/settings.local.json`:
   ```json
   {
     "permissions": {
       "allow": []
     },
     "additionalDirectories": [
       "c:\\Users\\101097205"
     ]
   }
   ```

4. Inform the user to restart the Claude Code session for changes to take effect.

## Notes

- The shared `settings.json` already covers all standard commands (git, gh, make, python, formatters)
- Most patterns in `settings.local.json` are duplicates of `settings.json` or stale one-off approvals
- If you find you frequently need a command, add it to `settings.json` instead (that's tracked in git)
- The backup file (`.bak`) can be deleted once you confirm everything works
