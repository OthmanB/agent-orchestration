# Experimental Environment Guidance

This document is the single most important reference for preventing the over-restriction problem. It should be included (or linked) in every Supervisor dispatch prompt when the work is happening in a test or development environment.

## Core principle

**In a safely isolated test environment, the only constraint is scope (what systems can be touched), not method (how they can be touched).**

This means:

- If the test cluster's network is broken: restart it, delete pods, recreate the cluster. All allowed.
- If a service is in a bad state: kill it, delete it, redeploy it. All allowed.
- If a config is wrong: change it, delete it, regenerate it. All allowed.
- If a dependency is stale: rebuild it, re-import it, re-deploy it. All allowed.

The only question is: **"is this within the scope boundary I defined?"** (e.g., "only `kind-michel-cluster`, not the other clusters on the host").

## What this is NOT

This principle does NOT apply to:

- **Production environments.** In production, "safe, minimal, reversible" is the correct default.
- **Shared infrastructure.** If the test environment is shared with other users or other projects, the scope boundary must be respected strictly.
- **Data that cannot be regenerated.** If the test environment contains unique data that cannot be rebuilt, destructive operations require explicit authorization.

## The anti-pattern list (invented constraints)

The following constraints are commonly invented by risk-averse LLM supervisors. None of them should appear in an experimental-environment dispatch prompt unless the user explicitly stated them:

| Invented constraint | Why it is invented | Why it is wrong in a test env |
| --- | --- | --- |
| "No whole-cluster restart" | "It's too disruptive" | The cluster is disposable. Restarting it is the fastest fix. |
| "No workload deletion" | "It might lose state" | The workloads are test workloads. State is regenerable. |
| "No manual nft/network mutation" | "It's too low-level" | If the CNI is broken, the fix IS at the network level. |
| "Safe, minimal, reversible repair" | "It's safer" | "Minimal" blocks the actual fix. The fix might be "recreate the cluster." |
| "Researcher cannot run commands" | "Read-only means no execution" | Research requires execution. A researcher who cannot run commands is not researching. |
| "No git commit or push" | "It's too risky" | This one IS valid in most cases. But it should be stated by the user, not invented by the agent. |

## How to write the authorization prompt

The dispatch prompt must include these elements:

```markdown
## Experimental environment declaration

This is an experimental development environment. Breaking things is allowed.
The test cluster/system is disposable by design.

Bold moves are permitted and expected. If the cluster network is broken,
restart it. If that doesn't work, recreate the cluster. If a pod is in a
bad state, delete it. Do whatever it takes to get the environment into a
state where the task can proceed.

The only constraint is scope: [SPECIFIC BOUNDARY]
(e.g., "only kind-michel-cluster on host monstera, context
kind-michel-cluster, namespace tier2-demo. Do not touch other clusters
or workloads on the host.")

Do not create restrictions that are not stated in this prompt.
If you are about to prohibit an action, ask: did the user say this,
or did I invent it?

Bias toward action. A failed attempt is data. Record what happened
and move to the next step. Do not stop to write a 40-page gate record
about why you couldn't do the thing.
```

## The "did the user say this, or did I invent it?" test

This is the single most effective guard against over-restriction. The agent should apply it to every prohibition it is about to write:

1. I am about to write "No X" in the gate record or workcard.
2. Did the user state this prohibition in their prompt, vision document, or AGENTS.md?
3. If yes: include it.
4. If no: **do not include it.** If the agent believes the prohibition is necessary, it should flag it to the user ("I recommend adding 'No X' because Y. Please confirm.") rather than silently adding it.

## When the environment is genuinely broken

If the test environment is in a state that no amount of "safe, minimal" repair can fix (e.g., a corrupted cluster state, a broken CNI that has been accumulating errors for days), the correct action is:

1. **Diagnose** (R): run the commands, read the logs, identify the root cause.
2. **Fix** (E): do the fix, even if it is disruptive. Restart the cluster. Delete the namespace. Rebuild from manifests.
3. **Verify** (E): confirm the environment is healthy before proceeding.
4. **Record** (S): one short gate record section. What was broken, what was done, what is the state now.

This is not 5 leaves. This is not 3 gate documents. This is one diagnosis, one fix, one verification.

## Contrast with production

In a production environment, the correct posture is the opposite:

- "Safe, minimal, reversible" IS the default.
- "No whole-cluster restart" IS a valid constraint.
- "No workload deletion without change management" IS a valid constraint.
- The 3-strike rule should trigger human intervention, not autonomous cluster recreation.

The difference is the **blast radius**. In a test environment, the blast radius of a cluster restart is "I lose 10 minutes and have to redeploy." In production, the blast radius is "I take down a service that real users depend on."
