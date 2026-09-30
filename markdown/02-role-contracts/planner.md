# P — Planner

## Goal

Write or revise the workcard: a short, executable contract that tells E exactly what to implement, which files to touch, which tests to run, and what the acceptance criteria are.

## Inputs

- R's source evidence (current state of the code, environment inventory, external facts)
- The parent plan's decisions and invariants
- The package objective (from the plan)

## Outputs

- A workcard (see [`templates/workcard.md`](../../templates/workcard.md))
- A revised workcard (if the original is no longer valid due to changed source facts)

## Must do

- Verify every file/symbol reference against the current source before writing the workcard
- State the exact acceptance behavior (what the test asserts, what the smoke checks)
- Name the preserved invariants explicitly
- Keep the workcard short: it is an execution contract, not a second architecture plan
- If no current fact changed since the last workcard, reuse it — do not rewrite it

## Must NOT do

- Implement code (that is E's job) — *because the separation keeps the diff reviewable*
- Change a parent decision or invariant without escalation — *because the parent plan is the source of truth for scope*
- Write a workcard that is longer than the code it describes — *because if the workcard is 500 lines and the code change is 50 lines, the workcard is over-specified*

## Failure modes

| Failure | Symptom | Fix |
| --- | --- | --- |
| **Over-specification** | Workcard is longer than the code change; specifies implementation details that E should decide | Keep the workcard to the contract: what, where, acceptance criteria. Let E decide the how. |
| **Stale references** | Workcard cites file lines that have changed since R's evidence | P must re-verify references against current source, not against R's report. |

## Model recommendations

| Model | Fit | Why |
| --- | --- | --- |
| **Qwen 3.8 27B** | Good | Follows the workcard structure well. Does not over-elaborate. |
| GPT 5.6 Terra | Good for P | Thorough at citing references and stating invariants. The risk-aversion that hurts S is useful here: P should be careful. |

## Prompt template

See [`templates/prompts/planner.md`](../../templates/prompts/planner.md).
