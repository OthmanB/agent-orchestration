# Leaf Creation

A leaf is a temporary, self-contained R→P→E→RV→S sequence for a defect or sub-problem found during implementation. The parent package is paused while the leaf runs. When the leaf is resolved, the parent package resumes.

## When to create a leaf

Create a leaf when:

- E encounters a **specific, bounded defect** that blocks the parent package (e.g., a bug in a dependency, a test environment failure that needs a targeted fix)
- The defect is **nameable**: "the X function has a Y bug" or "the Z service is in a bad state"
- The fix is **bounded**: it can be described in a workcard, not a new plan

## When NOT to create a leaf

Do NOT create a leaf when:

- The "defect" is the **normal state of the test environment** (e.g., a broken CNI that just needs a restart, a stale cache that just needs clearing). The correct action is to fix the environment, not to open a leaf.
- The "defect" is **the parent package's own problem** (e.g., the workcard is wrong, the approach is wrong). The correct action is to revise the workcard (P), not to open a leaf.
- You have already opened **2 leaves for the same underlying problem**. If 2 leaves have failed, the 3rd will likely fail too. Stop and apply the 3-strike rule: transition to `Stuck` and request human intervention.

## Leaf lifecycle

```
Parent package in Implementing
  → E encounters defect D
  → S opens leaf for D
  → Leaf: R (diagnose D) → P (plan fix) → E (implement fix) → RV (review) → S (record)
  → Leaf resolved
  → Parent package resumes Implementing
```

The leaf has its own gate record, but it is **short** (target: 100 lines, half the parent's target). The leaf gate record names:

1. The parent package and the defect that triggered the leaf
2. R's diagnosis (what is broken, why)
3. P's fix (what to change, where)
4. E's implementation (what was done)
5. RV's disposition (accepted / findings)
6. The leaf's terminal state: `resolved` (defect fixed, parent resumes) or `escalated` (defect is larger than expected, needs parent plan revision)

## Anti-pattern: leaf proliferation

The Terra supervisor incident demonstrated leaf proliferation: the same cluster network defect (kindnet CNI desync) triggered 5 separate leaves before the root cause was addressed. Each leaf ran its own R→P→E→RV→S sequence, produced its own gate record, and ended in "no mutation" because the "safe, minimal, reversible" constraint (invented by the supervisor) blocked the actual fix (restarting the cluster).

**The rule:** if 2 leaves have been opened for the same underlying problem, the 3rd leaf is not opened. Instead, S transitions the package to `Stuck` and records:

- The 2 (or 3) leaf attempts and their outcomes
- The common root cause
- The specific action that is blocked (and what is blocking it)
- The request for human intervention

The human then decides: is the fix a cluster restart? Is the fix a scope change? Is the fix a different approach entirely?

## Leaf vs. parent plan revision

A leaf is for a **defect within the parent package's scope**. If the defect requires changing the parent plan's decisions or invariants, it is not a leaf — it is a **material plan revision**, which requires escalation to the user.

| Situation | Action |
| --- | --- |
| Bug in a dependency function | Leaf: fix the bug, resume parent |
| Test environment is broken | Fix the environment (E), no leaf needed |
| Workcard is wrong | Revise the workcard (P), no leaf needed |
| Parent plan's invariant is wrong | Escalate to user (material revision) |
| Same defect blocks 3 leaves | Stuck state, human intervention |
