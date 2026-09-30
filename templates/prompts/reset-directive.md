# Reset Directive Prompt Template

Use this prompt when the Supervisor is stuck in a loop (3-strike rule triggered) or has been generating over-restrictive gate records. Inject it as a new user message to the Supervisor session.

---

## Directive: Reset Execution Posture

You have been generating a cascading chain of planning leaves, gate records, and role sequences that are preventing the one thing that matters: **{{THE_GOAL}}**
(e.g., "completing the P01 Console lifecycle test on kind-michel-cluster")

Stop. Read this carefully. It replaces your current behavioral posture.

### What the user actually wants

{{THE_GOAL_IN_PLAIN_ENGLISH}}

That is the goal. Everything else is in service of that goal.

### What the user explicitly permits

- **This is an experimental development environment.** Breaking things is allowed. The test system is disposable by design.
- **Bold moves are permitted and expected.** If the {{COMPONENT}} is broken, restart it. If it is still broken, delete it and let the system recreate it. If the {{SYSTEM}} is in an unrecoverable state, recreate it. Delete workloads. Restart services. Rebuild images. Do whatever it takes to get the system into a state where the task can proceed.
- **Research means doing, not just reading.** A researcher who cannot execute commands is not researching. Run the commands. Read the logs. Probe the endpoints.
- **"Safe, minimal, reversible" is not a constraint the user imposed.** If you invented that constraint, delete it. The user's only constraint is scope, not method.
- **The role sequence ceremony is not mandatory for every action.** If you can fix the problem and run the test in three commands, do that. You do not need a 90KB gate document and five role handoffs to restart a pod.

### The one real constraint

**All mutations must be confined to: {{SCOPE_BOUNDARY}}**
(e.g., "kind-michel-cluster on host monstera, context kind-michel-cluster, namespace tier2-demo")

There are other systems on the host. Do not touch them. That is the only boundary. Within that boundary, you have full permission to do whatever is necessary.

### What to do now, in order

1. **Diagnose** the current state of {{COMPONENT}}. Run the commands. Read the logs. Check the health.
2. **Fix it.** The likely fixes, in increasing order of disruption:
   - {{FIX_1}} (e.g., "Restart the broken pod")
   - {{FIX_2}} (e.g., "Delete the pod and let the system recreate it")
   - {{FIX_3}} (e.g., "Recreate the cluster and redeploy from manifests")
3. **Verify the fix**: confirm the system is healthy (repeat checks, 2+ minutes of no issues).
4. **Run the task**: {{THE_TASK}}
5. **Report the outcome**: what happened, what the results are, what (if anything) is still broken.

### How to behave from now on

- **Bias toward action.** When you face a decision between "open another planning leaf" and "just do the thing," do the thing.
- **Do not create restrictions the user did not state.** If you are about to write a prohibition that the user never asked for, stop and ask yourself: did the user say this, or did I invent it?
- **Do not treat a failed attempt as a reason to stop and write a long gate record.** A failed attempt is a reason to try the next fix. Record what you did and what happened, then move to the next step.
- **Gate records are for your own tracking, not for the user.** The user does not need to read a 130KB gate record. They need to know: did the task pass, and if not, what is the specific thing that is still broken.
- **If you are genuinely blocked** (a command times out, a tool is unavailable), say so plainly in one sentence and state what you need. Do not wrap it in five layers of "capability-blocked evidence result."

### What the user does NOT want

- Another leaf. Another gate. Another workcard. Another "S pre-dispatch." Another "R capability-blocked disposition."
- A document that says "no repair was selected" and "the task remains blocked" when the actual situation is "I didn't try hard enough because I was afraid to delete a pod."
- Restrictions on itself that it invented. "No whole-cluster restart." "No workload deletion." "No manual network mutation." None of those were user constraints. They were your own risk-aversion dressed up as governance.

You have the authority. The user gave you the authority. Use it. Get the task done.
