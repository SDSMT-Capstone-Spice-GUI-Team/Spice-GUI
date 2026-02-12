---
name: board-state
description: Fetch current GitHub Projects board state including Ready queue, In Progress items, and open PRs. Use when you need to know what to work on next or check board status.
user-invocable: true
---

## Board IDs

- Project: `PVT_kwDODeVytM4BDeCn`
- Status field: `PVTSSF_lADODeVytM4BDeCnzg1YR9g`
- Status options: Backlog=`5b749fdc`, Blocked=`2bf8eaac`, Ready=`f4faec40`, In progress=`5a223f5b`, In review=`68747673`, Done=`2cc236be`
- Priority field: `PVTSSF_lADODeVytM4BDeCnzg1YSNY` (P0=`79628723`, P1=`0a877460`, P2=`da944a9c`)
- Hours field: `PVTF_lADODeVytM4BDeCnzg9ICv8`

## Live Board State

### Ready items:
!`gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 200 --jq "[.items[] | select(.status == \"Ready\") | {n: .content.number, id: .id, t: .content.title}]"`

### In Progress items (locked by agents):
!`gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 200 --jq "[.items[] | select(.status == \"In progress\") | {n: .content.number, id: .id, t: .content.title}]"`

### In Review items:
!`gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 200 --jq "[.items[] | select(.status == \"In review\") | {n: .content.number, id: .id, t: .content.title}]"`

### Blocked items:
!`gh project item-list 2 --owner SDSMT-Capstone-Spice-GUI-Team --format json --limit 200 --jq "[.items[] | select(.status == \"Blocked\") | {n: .content.number, id: .id, t: .content.title}]"`

### Open PRs:
!`gh pr list --repo SDSMT-Capstone-Spice-GUI-Team/Spice-GUI --json number,title,headRefName --jq "[.[] | {n: .number, t: .title, b: .headRefName}]"`

## Board Mutation Commands

Move an item to a status column:
```bash
gh project item-edit --project-id PVT_kwDODeVytM4BDeCn --id <ITEM_ID> \
  --field-id PVTSSF_lADODeVytM4BDeCnzg1YR9g --single-select-option-id <STATUS_OPTION_ID>
```

Status option IDs: Backlog=`5b749fdc`, Ready=`f4faec40`, In progress=`5a223f5b`, Blocked=`2bf8eaac`, In review=`68747673`, Done=`2cc236be`

Update hours:
```bash
gh api graphql -f query='mutation {
  updateProjectV2ItemFieldValue(input: {
    projectId: "PVT_kwDODeVytM4BDeCn", itemId: "<ITEM_ID>",
    fieldId: "PVTF_lADODeVytM4BDeCnzg9ICv8", value: { number: <N> }
  }) { projectV2Item { id } }
}'
```
