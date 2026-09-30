# Model Assignment

Which model for which role, and why. This is based on observed behavior in the agent-threat-detection project (2026-09), where GPT 5.6 Terra as Supervisor produced a cascading chain of over-restrictive gate records and Qwen 3.8 27B as Executor performed reliably.

**Last updated:** 2026-09-30. Researcher and Planner model choices are still under discussion.

## Current assignment

| Role | Model | Status | Rationale |
| --- | --- | --- | --- |
| **S — Supervisor** | Qwen 3.8 27B (`vllm-tp2-local/qwen3.8-27b-q4-gpukv-native`) | Decided | Needs to bias toward action, not create restrictions. Needs to make decisions quickly and dispatch the next role. Over-documentation is a failure mode. |
| **P — Planner** | Claude Sonnet 5 (`github-copilot/claude-sonnet-5`) | Under discussion | P needs to be careful and precise, good at citing references. Ideally Opus 5.5, but cost-prohibitive. Sonnet 5 is the cost-effective choice. |
| **R — Researcher** | DeepSeek Flash (`deepseek/deepseek-flash`) | Under discussion | Needs to run commands without hesitation, report what it finds. Currently DeepSeek Flash in the OMP config. Qwen 3.8 27B is also viable. |
| **E — Executor** | Qwen 3.8 27B (`vllm-tp2-local/qwen3.8-27b-q4-gpukv-native`) | Decided | Needs to follow the workcard precisely. Needs to run tests and record results. Does not need to over-think. |
| **RV — Reviewer** | GPT 5.6 Terra or GPT 6 Sol (`openai-codex/gpt-5.6-terra` / `openai-codex/gpt-6-sol`) | Decided | Same cost per token. Needs to be careful, catch inconsistencies, produce structured findings. The risk-aversion that hurts S is a strength here. |
| **O — Observer** | Qwen 3.8 27B | Decided | Needs to translate jargon to plain English. Needs to be concise. Terra is too formal for this role. |

## The Terra strictness problem

GPT 5.6 Terra, when used as Supervisor, exhibited a consistent pattern:

1. **Invented constraints.** Terra added prohibitions that the user did not state: "no cluster restart," "no workload deletion," "no manual nft mutation," "safe, minimal, reversible repair." None of these were in the user's prompt.
2. **Interpreted "read-only" as "cannot execute."** When Terra was the Researcher, it returned "BLOCKED_NO_EXECUTION_CHANNEL" instead of running `kubectl` commands.
3. **Gate record bloat.** Terra's gate records grew to 400-1300 lines. Each record re-stated invariants, re-quoted source code, and re-explained rationale.
4. **Leaf proliferation.** The same cluster network defect triggered 5 separate leaves before the root cause was addressed.

The root cause was not a prompt failure. It was a model characteristic: Terra is thorough, careful, and risk-averse. These are excellent qualities for a Reviewer. They are harmful qualities for a Supervisor whose job is to make decisions and move forward.

**The fix:** use Qwen 3.8 27B as Supervisor (action-biased), use Terra as Reviewer (thoroughness is a strength there). Include the experimental-environment declaration in the dispatch prompt. Apply the 3-strike rule.

See [`notes/2026-09-30-supervisor-strictness-incident.md`](../notes/2026-09-30-supervisor-strictness-incident.md) for the full incident report.

## Model swap mid-process

If you need to swap the model for a role mid-process:

1. Record the swap in the gate record: "S model changed from X to Y at [timestamp], reason: [reason]."
2. The new model inherits the current state from the gate records. It does not need to re-read the full history.
3. The swap does not reset the 3-strike counter. If a package was at 2 strikes before the swap, it is still at 2 strikes after.

## What matters more than the model

The model choice matters, but the prompt design matters more. A risk-averse model with a clear "bias toward action" prompt and an explicit "do not create restrictions the user did not state" instruction will outperform an action-biased model with a vague prompt.

The three most important prompt elements:

1. **The experimental-environment declaration** (see [`04-experimental-environment.md`](04-experimental-environment.md))
2. **The scope boundary** (what systems can be touched; not how)
3. **The "did the user say this, or did I invent it?" test** (for every prohibition the agent is about to write)
