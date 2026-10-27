# OMP Integration Guide

This directory contains OMP-specific integration details. The core orchestration model, role contracts, state machine, and prompt templates are in the parent `markdown/` and `templates/` directories and are harness-agnostic.

## OMP subagent setup

OMP (Oh My Pi) dispatches subagents via its `task` tool. Within a leaf, dispatch is serial (R→P→E→RV→S). OMP also supports concurrent subagents (`task.maxConcurrency` in `~/.omp/agent/config.yml`; OMP default is 32) — this campaign sets it to 2, so up to two independent leaves may run in parallel. See `AGENTS.md` § Parallel execution at the repo root for the scope and serialization rules.

See [`subagent-setup.md`](subagent-setup.md) for the concrete OMP subagent definitions.

## OMP gate record conventions

In OMP, gate records are stored in:

```
evidence/omp-gates/{{PACKAGE_ID}}.md
```

One gate record per terminal package attempt. If a package goes through multiple R→P→E→RV→S cycles, use numbered files:

```
evidence/omp-gates/P01-cycle-1.md
evidence/omp-gates/P01-cycle-2.md
```

The terminal gate record (last cycle) references previous cycles. It does not re-state their content.

## OMP workcard conventions

Workcards are stored in:

```
evidence/omp-workcards/{{WORKCARD_ID}}.md
```

## OMP limitations

### No "above the Supervisor" role

OMP does not support a role that sits above the Supervisor. The Observer (O) cannot be an OMP subagent that monitors the Supervisor in real time. Instead:

- The Observer runs in a **separate session** (e.g., a separate OpenCode or OMP conversation).
- The Observer reads gate records from disk.
- The Observer produces a plain-English summary.
- The human user reads the summary and decides whether to intervene.

This is the "manual feedback loop" described in [`markdown/02-role-contracts/observer.md`](../markdown/02-role-contracts/observer.md).

### Subagent concurrency

OMP supports concurrent subagents: `task.maxConcurrency` in `~/.omp/agent/config.yml`
caps how many run at once (OMP default 32; this campaign sets 2). The standing
policy (see `AGENTS.md` § Parallel execution at the repo root):

- Up to two independent leaves may run concurrently (local vLLM session budget).
- Parallel leaves must touch disjoint files — separate sub-repositories where
  possible.
- Within a leaf, roles stay serial (R → P → E → RV → S).
- Git commits on the canonical branch and cluster deploy/mutation steps are
  always serialized between parallel leaves.

### No auto-trigger for the Observer

OMP does not support scheduled background tasks. The Observer must be triggered manually by the human user. If you want periodic Observer checks, run the Observer prompt in a separate session on a schedule (e.g., every 2-3 hours).

## OMP prompt injection

In OMP, the Supervisor prompt is injected as the initial user message to the Supervisor session. The subagent prompts (R, P, E, RV) are injected when the Supervisor dispatches each role.

The prompt templates in [`templates/prompts/`](../templates/prompts/) are designed to be copy-pasted into OMP subagent sessions with the placeholders filled in.

## OMP model configuration

Each subagent file in `agent-orchestration/.omp/agents/` carries a `model: "@<alias>"` frontmatter alias; the alias resolves through `modelRoles` in `~/.omp/agent/config.yml`. S is not a subagent — it is the main session, set by `modelRoles.supervisor`. Current assignment (see [`markdown/03-model-assignment.md`](../markdown/03-model-assignment.md)):

| Role | Model | Config location |
| --- | --- | --- |
| S — Supervisor | `anthropic/claude-sonnet-5-5:high` | `modelRoles.supervisor` (main session) |
| P — Planner | `anthropic/claude-sonnet-5-5:xhigh` | `.omp/agents/planner.md` → `modelRoles.plan` |
| R — Researcher | `deepseek/deepseek-flash:high` | `.omp/agents/researcher.md` → `modelRoles.research` |
| E — Executor | `vllm-tp2-local/qwen3.8-27b-q4-gpukv-native:xhigh` | `.omp/agents/executor.md` → `modelRoles.execution` |
| RV — Reviewer | `openai-codex/gpt-6.1-sol:high` | `.omp/agents/reviewer.md` → `modelRoles.review` |

The Observer is not an OMP subagent. It runs in a separate session with its own model (local Qwen 3.8 27B, i.e. the `default` role, recommended).
