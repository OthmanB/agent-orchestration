# Gate Record Template

Copy this template for each gate record. Target: 200 lines maximum.

---

# {{PACKAGE_ID}} — {{ROLE}} Gate Record

- Date: {{DATE}}
- Status: {{promoted | retrying | waiting_external | escalated | stuck}}

## 1. Context

- Parent plan: `{{PARENT_PLAN_PATH}}`
- Workcard revision: {{WORKCARD_REVISION}}
- This gate records: {{ONE_SENTENCE_SUMMARY}}

## 2. Evidence

### R findings (summary)
{{2-5 BULLET POINTS. LINK TO FULL EVIDENCE DOC. DO NOT RE-QUOTE.}}

### E changed files
| File | Change |
| --- | --- |
| `{{FILE_1}}` | {{ONE_LINE_SUMMARY}} |
| `{{FILE_2}}` | {{ONE_LINE_SUMMARY}} |

### Commands run
| Command | Result |
| --- | --- |
| `{{CMD_1}}` | {{PASS/FAIL, EXIT CODE}} |
| `{{CMD_2}}` | {{PASS/FAIL, EXIT CODE}} |

### Smoke evidence
{{WHAT WAS OBSERVED. LINK TO FULL EVIDENCE DOC IF LONG.}}

## 3. Review

- RV disposition: {{accepted | accepted_with_findings | rejected}}
- Findings:
  1. {{FILE:LINE}} — {{ISSUE}} → S decision: {{accepted / dismissed / deferred}}
  2. {{FILE:LINE}} — {{ISSUE}} → S decision: {{accepted / dismissed / deferred}}

## 4. State

- Terminal state: {{STATE}}
- Dependents unlocked: {{LIST OR "none"}}
- Not-exercised items: {{LIST OR "none"}}

## 5. Next

- Next role: {{ROLE}} (if not terminal)
- Next package: {{PACKAGE_ID}} (if this is terminal)
