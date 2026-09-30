# Design Principles

Eight principles that govern the orchestration model. These are the "why" behind the role contracts, the state machine, and the prompt templates.

## 1. Bias toward action

When in doubt between "open another planning leaf" and "just do the thing," do the thing. A failed attempt is data. Record what happened and move to the next step.

The anti-pattern is the agent that spends more time planning the action than performing it. If the plan is "restart the cluster" and the cluster is broken, restart the cluster. Do not write a 40-page gate record about why restarting the cluster might be risky.

## 2. No invented constraints

If a prohibition is not in the user's prompt, it does not exist. The agent must not add restrictions that the user did not state.

The test: before writing any "No X" in a gate record or workcard, ask: **did the user say this, or did I invent it?** If the answer is "I invented it," do not write it. If the agent believes the prohibition is necessary, flag it to the user: "I recommend adding 'No X' because Y. Please confirm."

This is the single most important principle for preventing the Terra strictness problem. See [`04-experimental-environment.md`](04-experimental-environment.md).

## 3. Scope boundary, not method boundary

Define **what systems can be touched**. Do not define **how** they can be touched.

Correct: "Only `kind-michel-cluster` on host `monstera`. Do not touch other clusters."
Incorrect: "No cluster restart, no workload deletion, no manual nft mutation, safe minimal reversible repair."

The first is a scope boundary. The second is a method boundary. In an experimental environment, method boundaries block progress. In a production environment, they are appropriate.

## 4. Gate records are for tracking, not for the user

The gate record is a machine-to-machine document. The next S session reads it to understand the current state. The Observer is the human-facing layer.

This means:
- Gate records are short (≤ 200 lines)
- Gate records link to evidence documents; they do not duplicate them
- Gate records record decisions and evidence; they do not record reasoning
- The user does not need to read gate records. The Observer translates them.

## 5. Advisory review, not blocking review

The Reviewer produces findings. The Supervisor reads them and decides. The Reviewer cannot say "no, this does not pass." It can say "here's what I noticed, here's what I think is wrong, here's what I'd check."

This prevents the Reviewer from becoming a second Supervisor. The Supervisor is the only role that makes decisions. The Reviewer provides input.

In practice: RV's disposition is `accepted_with_findings`. S reads the findings. If a finding is valid, S dispatches E to correct it. If a finding is a style preference, S dismisses it. The package does not stop on RV's word alone.

## 6. Leaf creation is a tool, not a fallback

A leaf is for a **specific, bounded defect**. It is not a general-purpose "let's investigate this" mechanism.

If the "defect" is the normal state of the test environment (a broken CNI, a stale cache), the correct action is to fix the environment, not to open a leaf. If 2 leaves have been opened for the same underlying problem, the 3rd is not opened. The package transitions to `Stuck` and the human decides.

See [`05-leaf-creation.md`](05-leaf-creation.md).

## 7. The Observer is for humans

The Observer translates. It does not intervene. It does not block. It does not participate in the state machine.

The Observer runs in a separate session and reads the gate records from disk. It produces plain-English summaries. The human user reads the summaries and decides whether to intervene.

The Observer can be auto-triggered on a schedule, but its primary use is on-demand: "I want to understand what is happening."

## 8. A broken test environment is not a code problem

If the test cluster's network is broken, the fix is to fix the network. Not to create 5 leaves. Not to write 3 gate documents. Not to open a "D-E kindnet CNI desync reassessment" package.

The correct sequence:
1. **Diagnose** (R): run the commands, read the logs, identify the root cause.
2. **Fix** (E): do the fix, even if it is disruptive. Restart the cluster. Delete the namespace. Rebuild from manifests.
3. **Verify** (E): confirm the environment is healthy before proceeding.
4. **Record** (S): one short gate record section. What was broken, what was done, what is the state now.

This is not a defect. This is not a leaf. This is the normal cost of working in a test environment.
