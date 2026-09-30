# Workcard Template

Copy this template for each workcard. The workcard is a short execution contract, not a second architecture plan.

---

# Workcard: {{PACKAGE_ID}}

- Parent plan: `{{PARENT_PLAN_PATH}}` (revision {{REVISION}})
- Date: {{DATE}}
- Status: {{draft | accepted | completed | superseded}}

## Objective

{{ONE_SENTENCE: what this package achieves}}

## Non-goals

- {{THING_1_THIS_PACKAGE_DOES_NOT_DO}}
- {{THING_2_THIS_PACKAGE_DOES_NOT_DO}}

## Exact scope

### Files to modify
| File | What changes |
| --- | --- |
| `{{FILE_1}}` | {{ONE_LINE_DESCRIPTION}} |
| `{{FILE_2}}` | {{ONE_LINE_DESCRIPTION}} |

### Files NOT to modify
- `{{FILE_X}}` — {{WHY}}

### Configuration keys
| Key | New value / constraint |
| --- | --- |
| `{{KEY_1}}` | {{VALUE_OR_SCHEMA}} |

## Preserved invariants

- {{INVARIANT_1}} (from parent plan §{{SECTION}})
- {{INVARIANT_2}} (from parent plan §{{SECTION}})

## R's key findings

- {{FINDING_1_THAT_AFFECTS_IMPLEMENTATION}}
- {{FINDING_2_THAT_AFFECTS_IMPLEMENTATION}}

## E acceptance behavior

- Test command: `{{TEST_COMMAND}}`
- Expected result: {{PASS/FAIL CRITERIA}}
- Smoke command (if applicable): `{{SMOKE_COMMAND}}`
- Expected smoke result: {{WHAT_TO_OBSERVE}}

## RV review checklist

- [ ] Diff touches only the files listed in "Exact scope"
- [ ] All preserved invariants are intact
- [ ] Tests pass
- [ ] Code discipline rules followed (YAML-first, no hardcoded params, structured logging)

## Gate evidence path

`{{GATE_RECORD_PATH}}`

## Unlocked dependents

- {{DEPENDENT_PACKAGE_1}} (if this package promotes)
- {{DEPENDENT_PACKAGE_2}}
