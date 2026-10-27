# Model Assignment

Which model for which role, and why. This is based on observed behavior in the agent-threat-detection project (2026-09), where GPT 5.6 Terra as Supervisor produced a cascading chain of over-restrictive gate records and Qwen 3.8 27B as Executor performed reliably.

**Last updated:** 2026-10-27. Model choices are decided for all roles.

## Current assignment

| Role | Model | Status | Rationale |
| --- | --- | --- | --- |
| **S — Supervisor** | Claude Sonnet 5.5 (`anthropic/claude-sonnet-5-5:high`) | Decided | Needs to make decisions quickly and dispatch the next role; over-documentation is a failure mode. Sonnet class is careful — the risk-aversion that hurt the Terra incident is managed by the standing mitigations below. |
| **P — Planner** | Claude Sonnet 5.5 (`anthropic/claude-sonnet-5-5:xhigh`) | Decided | P needs to be careful and precise, good at citing references. |
| **R — Researcher** | DeepSeek Flash (`deepseek/deepseek-flash:high`) | Decided | Needs to run commands without hesitation and report what it finds. |
| **E — Executor** | Qwen 3.8 27B (`vllm-tp2-local/qwen3.8-27b-q4-gpukv-native:xhigh`) | Decided | Needs to follow the workcard precisely, run tests, record results. Does not need to over-think. |
| **RV — Reviewer** | GPT 6.1 Sol (`openai-codex/gpt-6.1-sol:high`) | Decided | Needs to be careful, catch inconsistencies, produce structured findings. It is the last-resort model of the fallback chain. |
| **O — Observer** | Qwen 3.8 27B (`vllm-tp2-local/...`, the `default` role) | Decided | Needs to translate jargon to plain English. Needs to be concise. |

## Fallback chains

Configured in `retry.fallbackChains` (`~/.omp/agent/config.yml`), triggered by rate-limit/quota errors:

- **S + P (shared):** `anthropic/claude-sonnet-5-5` → `github-copilot/claude-sonnet-5.5:xhigh` → `openai-codex/gpt-6.1-sol:xhigh`. Both roles resolve to the same catalog model, so one chain covers them: Anthropic window hit → Copilot's 5h/weekly windows → Codex.
- **R — Researcher:** `deepseek/deepseek-flash` → `vllm-tp2-local/qwen3.8-27b-q4-gpukv-native:xhigh` (DeepSeek key unavailable or limit hit → local).
- **No chain:** E/default/smol/slow run on the local vLLM server and have nowhere to hop if the server or the link is down; RV (`openai-codex/gpt-6.1-sol`) is the last-resort model of the chain.


## The Terra strictness problem

GPT 5.6 Terra, when used as Supervisor, exhibited a consistent pattern:

1. **Invented constraints.** Terra added prohibitions that the user did not state: "no cluster restart," "no workload deletion," "no manual nft mutation," "safe, minimal, reversible repair." None of these were in the user's prompt.
2. **Interpreted "read-only" as "cannot execute."** When Terra was the Researcher, it returned "BLOCKED_NO_EXECUTION_CHANNEL" instead of running `kubectl` commands.
3. **Gate record bloat.** Terra's gate records grew to 400-1300 lines. Each record re-stated invariants, re-quoted source code, and re-explained rationale.
4. **Leaf proliferation.** The same cluster network defect triggered 5 separate leaves before the root cause was addressed.

The root cause was not a prompt failure. It was a model characteristic: Terra is thorough, careful, and risk-averse. These are excellent qualities for a Reviewer. They are harmful qualities for a Supervisor whose job is to make decisions and move forward.

**The fix:** use Qwen 3.8 27B as Supervisor (action-biased), use Terra as Reviewer (thoroughness is a strength there). Include the experimental-environment declaration in the dispatch prompt. Apply the 3-strike rule.

**Current state (2026-10-27):** S and P are on the Sonnet class (Claude Sonnet 5.5) again, for precision. This is the risk-averse family the incident flagged, so the standing mitigations apply: the experimental-environment declaration in every dispatch prompt, the 3-strike rule, the reset directive (`templates/prompts/reset-directive.md`), and the gate-record model-identity requirement. If the over-restriction pattern recurs, apply the reset directive first, then consider reverting S to local Qwen.

See [`notes/2026-09-30-supervisor-strictness-incident.md`](../notes/2026-09-30-supervisor-strictness-incident.md) for the full incident report.

## Model quota fallback behavior

- The harness handles the configured fallback chains transparently; orchestration does not perform quota health-checks or model-service operations.
- The gate record must name the model that **actually** performed the role's work (after any fallback), not the one that was requested.
- A quota or transport attempt on role work is not an engineering strike (see the 3-strike rule).

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
