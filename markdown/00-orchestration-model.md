# Orchestration Model

**Status:** Generalized reference. Derives from the OMP autonomous execution orchestration used in the agent-threat-detection project (2026-09). Stripped of task-specific content.

## Decision

The Supervisor (S) executes the approved plan packages without requesting per-package confirmation. S owns the dependency graph, dispatches the role sequence, records each gate, and promotes only evidence-backed packages. Product-code mutation remains delegated to the Executor (E).

This document defines the execution governance. It does not prescribe the technical content of any specific plan.

## Role Contract

| Role | Owns | Must not own |
| --- | --- | --- |
| **S — Supervisor** | package queue, dependency checks, integration decisions, gate records, retry/replan routing, final evidence promotion | direct product-code implementation |
| **P — Planner** | package workcard, exact file/symbol/test map, narrow subplans, revisions that remain within approved scope | product-code mutation, changing a parent decision/invariant without escalation |
| **R — Researcher** | current-source and external fact finding, contract/compatibility evidence, live-environment inventory | code/config mutation |
| **E — Executor** | one approved workcard at a time: implementation, targeted checks, and declared smoke path | changing scope, committing/pushing (unless authorized), concurrent workcards |
| **RV — Reviewer** | independent acceptance review of E's diff/evidence: invariants, regression risk, test quality, and gate criteria | source mutation, replacement architecture, approving unsupported claims |
| **O — Observer** | plain-English translation of gate records for the human user; assessment of whether the path is reasonable | code review, code modification, blocking any role, participating in the state machine |

P and R may produce new workcards/evidence files. E is the only role that changes product files. S may update only planning/evidence artifacts required to record a gate. O is read-only and does not participate in the state machine.

## Standard Package State Machine

See [`01-state-machine.md`](01-state-machine.md) for the full diagram and explanation.

## Gate Record

S writes one gate record after every terminal package attempt. The record must contain:

1. parent plan/package and workcard revision;
2. P's accepted scope, files, and unchanged invariants;
3. R's source evidence, including unresolved external conditions;
4. E's changed files and only the commands/smokes actually observed;
5. RV disposition and every resolved finding;
6. resulting state: `promoted`, `retrying`, `waiting_external`, or `escalated`;
7. dependents unlocked or still blocked;
8. the model identity used for S and any recorded model transition.

A package cannot unlock a successor from an E completion, test result, or deployment status alone. It needs the S gate record with RV acceptance and the package's required smoke/evidence.

**Length target:** 200 lines. If the gate record exceeds this, split it or summarize. See [`06-gate-records.md`](06-gate-records.md).

## Workcards And Role Sequence

P creates a workcard only when current source/evidence can affect implementation details. A workcard is a short execution contract, not a second architecture plan:

```text
Package id and parent-plan revision
Objective and non-goals
Exact files/symbols/config keys
Preserved invariants
R questions and source evidence
E acceptance behavior and test/smoke command
RV review checklist
Gate evidence path and unlocked dependents
```

Normal role sequence:

1. **S** verifies predecessor gates and reserves the package.
2. **R** verifies current source, deployed/configured inputs, and external-owner assertions. R may run read-only and read-and-mutate commands against the target environment.
3. **P** narrows or revises the workcard from that evidence. If no current fact changed, P reuses the parent-plan workcard.
4. **S** accepts the workcard when it preserves the parent plan's decisions and invariants.
5. **E** implements one workcard, runs its targeted checks after mutation, and performs a declared smoke where available.
6. **RV** reviews the diff plus E evidence. Findings are advisory; S decides whether to act on them.
7. **E** corrects accepted review findings and reruns the affected checks/smoke.
8. **S** writes the gate record and starts the earliest newly unblocked package.

## Autonomous Replanning

P may revise a workcard without human approval when the revision:

- changes only file/symbol selection, test/smoke details, fixture mapping, or package sequencing;
- preserves every decision and invariant in the parent plan;
- does not add a component, repository boundary, deployment target, or release coupling beyond the explicitly approved scope; and
- receives RV review before S promotes the package.

S records the before/after workcard revision and rationale in the gate record. Failed tests, routine review findings, transient service availability, and expected incompatible imports are handled through this loop.

## Escalation

S requests human approval only when evidence shows that completing a package requires a **material parent-plan revision**. The escalation record names the failed gate, alternatives, source evidence, blast radius, and a recommended revision.

A missing service, failed test, rejected config, ordinary code-review finding, or unavailable external response is not itself material. S retries, narrows the workcard, waits, or records `waiting_external` first.

**3-strike rule:** if a package or leaf fails 3 times for the same underlying reason, S transitions the package to the `Stuck` state and requests human intervention. See [`01-state-machine.md`](01-state-machine.md#stuck-state).

## Authorization Boundary

The execution plan authorizes autonomous progression through the accepted package DAG. The specific authorization (what is and is not permitted) is defined in the user's dispatch prompt and the parent plan. This document does not authorize or prohibit specific actions; it defines the process by which S, P, R, E, and RV interact.

## Completion

S declares the overall plan complete only after every non-deferred package is `promoted`, every deferred/blocked package has its stated gate record, and the final evidence index links all package records and residual experimental limits.
