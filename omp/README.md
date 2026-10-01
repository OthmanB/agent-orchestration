# OMP Integration Guide

This directory contains OMP-specific integration details. The core orchestration model, role contracts, state machine, and prompt templates are in the parent `markdown/` and `templates/` directories and are harness-agnostic.

## OMP subagent setup

OMP (Oh My Pi) supports serialized subagent dispatch: one active subagent at a time, dispatched by the Supervisor. This maps naturally to the R→P→E→RV→S role sequence.

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

### Single active subagent

OMP permits only one active subagent at a time. This means:

- Roles are strictly serialized (R → P → E → RV → S).
- Parallel work is not possible within a single OMP session.
- If you need parallel work (e.g., two independent packages), run two separate OMP sessions.

### No auto-trigger for the Observer

OMP does not support scheduled background tasks. The Observer must be triggered manually by the human user. If you want periodic Observer checks, run the Observer prompt in a separate session on a schedule (e.g., every 2-3 hours).

## OMP prompt injection

In OMP, the Supervisor prompt is injected as the initial user message to the Supervisor session. The subagent prompts (R, P, E, RV) are injected when the Supervisor dispatches each role.

The prompt templates in [`templates/prompts/`](../templates/prompts/) are designed to be copy-pasted into OMP subagent sessions with the placeholders filled in.

## OMP model configuration

In OMP, the model for each role is configured in the subagent definition. The recommended assignment (see [`markdown/03-model-assignment.md`](../markdown/03-model-assignment.md)):

| Role | Model | OMP config key |
| --- | --- | --- |
| S — Supervisor | `vllm-tp2/qwen3.8-27b-q4-gpukv-native:high`| `supervisor.model` (main session: `modelRoles.default` / `modelRoles.supervisor`) |
| P — Planner |  `github-copilot/claude-sonnet-5` | `planner.model` |
| R — Researcher | `deepseek/deepseek-flash` | `researcher.model` |
| E — Executor | `vllm-tp2/qwen3.8-27b-q4-gpukv-native:high`| `executor.model` |
| RV — Reviewer | `openai-codex/gpt-5.6-terra` or `openai-codex/gpt-6-sol`| `reviewer.model` |

The Observer is not an OMP subagent. It runs in a separate session with its own model (Qwen 3.8 27B recommended).
