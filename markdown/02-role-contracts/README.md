# Role Contracts

One document per role. Each document defines:

- **Goal**: what this role is trying to achieve
- **Inputs**: what it receives
- **Outputs**: what it produces
- **Must do**: positive list
- **Must NOT do**: negative list (kept minimal; each item justified)
- **Failure modes**: what goes wrong when misconfigured
- **Model recommendations**: which models work well
- **Prompt template**: link to the ready-to-use prompt

| Role | Document |
| --- | --- |
| S — Supervisor | [supervisor.md](supervisor.md) |
| P — Planner | [planner.md](planner.md) |
| R — Researcher | [researcher.md](researcher.md) |
| E — Executor | [executor.md](executor.md) |
| RV — Reviewer | [reviewer.md](reviewer.md) |
| O — Observer | [observer.md](observer.md) |

## Design note on "Must NOT do"

The "Must NOT do" list is intentionally short. Each prohibition must have a "because" clause. If the justification is "it's safer" or "it's more minimal," that is not a valid reason in an experimental environment. See [`04-experimental-environment.md`](../04-experimental-environment.md) for the full discussion.

The Terra supervisor incident demonstrated what happens when this list grows organically: the supervisor invented constraints like "no cluster restart," "no workload deletion," and "researcher cannot run commands," none of which were in the user's prompt. Each constraint was "reasonable" in isolation, but together they made it impossible to complete the task.
