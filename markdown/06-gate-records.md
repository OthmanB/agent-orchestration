# Gate Record Conventions

A gate record is a tracking document written by the Supervisor after every terminal package attempt. It is for machine-to-machine communication: the next S session reads it to understand the current state. The Observer is the human-facing layer.

## Length target

**200 lines maximum.** If the gate record exceeds this, split it or summarize.

The Terra supervisor's gate records were 400-1300 lines. The difference: Terra re-stated invariants, re-quoted source code, and re-explained rationale in every gate record. The generalized convention is: **link to the invariant, don't re-quote it. Summarize the finding, don't re-derive it.**

## Required sections

A gate record has 5-7 sections:

```markdown
# [Package ID] — [Role] Gate Record

- Date: [date]
- Status: [promoted | retrying | waiting_external | escalated | stuck]

## 1. Context
- Parent plan and workcard revision
- What this gate records (one sentence)

## 2. Evidence
- R's findings (summary, not full quote)
- E's changed files and commands run
- Test results (pass/fail, which tests)
- Smoke evidence (what was observed)

## 3. Review
- RV disposition: [accepted | accepted_with_findings | rejected]
- Findings (list, each with file + issue + recommended fix)
- S's decision on each finding (accepted / dismissed / deferred)

## 4. State
- Terminal state of this package
- Dependents unlocked or still blocked
- Not-exercised items (if any)

## 5. Next
- Next role to dispatch (if not terminal)
- Next package in queue (if this is terminal)
```

## What NOT to include

- **Re-stated invariants.** Link to the parent plan's invariant section. Do not re-quote it.
- **Re-quoted source code.** Reference the file and line. Do not paste the code.
- **Re-explained rationale.** The workcard has the rationale. The gate record records what happened, not why it was planned.
- **Raw command output.** Record the command and the result (pass/fail, exit code). Do not paste the full stdout unless it is short and critical.
- **Model reasoning.** The gate record records decisions and evidence. It does not record the LLM's chain of thought.

## Gate record vs. evidence document

The gate record is the **summary**. The evidence document is the **detail**.

| | Gate record | Evidence document |
| --- | --- | --- |
| **Length** | ≤ 200 lines | Any length |
| **Audience** | Next S session, Observer | Human user (via Observer), audit trail |
| **Content** | What happened, what is next | Full command outputs, full diffs, full test results |
| **When written** | At the end of each role's completion | During the role's execution |

The gate record links to the evidence document. It does not duplicate it.

## Multiple gate records for the same package

If a package goes through multiple R→P→E→RV→S cycles (e.g., RV finds an issue, E corrects it, RV re-reviews), there is **one gate record per cycle**. The cycles are numbered:

```
evidence/omp-gates/P01-cycle-1.md
evidence/omp-gates/P01-cycle-2.md
```

The terminal gate record (the last cycle) references the previous cycles. It does not re-state their content.
