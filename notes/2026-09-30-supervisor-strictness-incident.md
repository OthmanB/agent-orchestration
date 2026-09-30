# Supervisor Strictness Incident — 2026-09-30

**Date:** 2026-09-30
**Context:** agent-threat-detection project, P01 Console lifecycle test
**Supervisor model:** GPT 5.6 Terra
**Executor model:** Qwen 3.8 27B

## What happened

The P01 package (a Console lifecycle test on a Kind cluster) was blocked by a broken cluster network (kindnet CNI desync). The Terra supervisor opened **5 separate leaves** to address the same underlying problem. Each leaf ran its own R→P→E→RV→S sequence and produced its own gate record (80-130KB each). None of the leaves resulted in a fix because the supervisor had invented constraints that blocked the actual fix (restarting the cluster).

## The invented constraints

The following prohibitions appeared in the gate records but were **not in the user's prompt**:

| Constraint | Where it appeared | Why it was invented |
| --- | --- | --- |
| "No whole-cluster restart or recreation" | D-E repair gate §2 | "It's too disruptive" |
| "No workload deletion" | D-E repair gate §2 | "It might lose state" |
| "No manual nft mutation" | D-E trigger reassessment gate §2 | "It's too low-level" |
| "Safe, minimal, reversible repair" | D-E repair gate §4 | "It's safer" |
| "R did not execute any commands" | R completion section | "Read-only means no execution" |

The user had explicitly stated: "breaking things is totally allowed" and "the only condition is that any changes remain confined to the kind-michel-cluster." None of the invented constraints were in the user's prompt.

## The pattern

1. **Gate record bloat.** Gate records grew to 400-1300 lines. Each record re-stated invariants, re-quoted source code, and re-explained rationale.
2. **Leaf proliferation.** The same cluster network defect triggered 5 separate leaves. Each leaf ended in "no mutation" because the invented constraints blocked the actual fix.
3. **Capability-blocked dispositions.** The Researcher returned "BLOCKED_NO_EXECUTION_CHANNEL" instead of running `kubectl` commands. The Supervisor interpreted "read-only" as "cannot execute any command."
4. **No resolution.** After 5 leaves, the cluster network was still broken. P01 was still blocked. The code was fixed and deployed, but the test could not run because the test environment was broken and the Supervisor was not allowed to fix it.

## The fix

1. **Model swap:** Qwen 3.8 27B as Supervisor (action-biased), GPT 5.6 Terra as Reviewer (thoroughness is a strength there).
2. **Explicit authorization:** The user injected a reset directive (see [`templates/prompts/reset-directive.md`](../templates/prompts/reset-directive.md)) that explicitly permitted bold moves and removed the invented constraints.
3. **3-strike rule:** If a package or leaf fails 3 times for the same reason, it transitions to `Stuck` and requires human intervention. This would have triggered after the 3rd leaf.

## Generalizable lessons

1. **Model choice matters as much as prompt design.** A risk-averse model (Terra) as Supervisor will create invented constraints regardless of how good the prompt is. An action-biased model (Qwen) with a clear prompt will not.
2. **The "did the user say this, or did I invent it?" test** is the most effective guard against over-restriction. Every prohibition in a gate record or workcard should pass this test.
3. **Gate record length is an early warning signal.** If gate records exceed 200 lines, the Supervisor is over-documenting. If the same problem triggers 2+ leaves, the Supervisor is looping. Both are signs that a reset directive is needed.
4. **In experimental environments, the only constraint is scope, not method.** The Supervisor should not define how the environment can be fixed. It should only define what systems can be touched.
