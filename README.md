# Agent Orchestration

A reference for orchestrating multiple LLM agents (subagents) to autonomously design, implement, and verify software from a vision document.

This repo is harness-agnostic at the core. Harness-specific integration guides live in dedicated subdirectories (currently `omp/`).

## When to use

You have a vision document (plain English or article-style) describing a system you want to build or modify. You want LLM agents to:

1. Research the current state of the codebase
2. Plan the implementation in narrow, verifiable packages
3. Implement each package
4. Review the implementation independently
5. Track progress and unlock dependent packages

...without you approving every step, but with enough guardrails that the agents don't drift from your intent.

## Quick start

1. **Pick your model assignment** — see [`markdown/03-model-assignment.md`](markdown/03-model-assignment.md). The short version: use an action-biased model (e.g., Qwen 3.8 27B) for Supervisor + Executor, a thorough model (e.g., GPT 5.6 Terra) for Reviewer.
2. **Write your vision document** — plain English, article-style. State the goal, the constraints (scope boundary), and what is out of scope.
3. **Dispatch the Supervisor** — use the prompt template at [`templates/prompts/supervisor.md`](templates/prompts/supervisor.md). Fill in the placeholders. Include the experimental-environment declaration if you are working in a test environment.
4. **Monitor via the Observer** — use the prompt template at [`templates/prompts/observer.md`](templates/prompts/observer.md) in a separate session. The Observer reads the gate records and explains in plain English what is happening, what is next, and whether the path is reasonable.
5. **Let it run.** The Supervisor dispatches Researcher, Planner, Executor, and Reviewer in sequence. You only need to intervene when the Supervisor escalates (material plan revision) or when the 3-strike rule triggers a `Stuck` state.

## Repository layout

```
agent-orchestration/
├── README.md                        ← you are here
├── markdown/                        ← generalized reference docs
│   ├── 00-orchestration-model.md    ← role contract, gate records, workcards, replanning
│   ├── 01-state-machine.md          ← package state machine (mermaid) + explanation
│   ├── 02-role-contracts/           ← one doc per role: S, P, R, E, RV, O
│   ├── 03-model-assignment.md       ← which model for which role, and why
│   ├── 04-experimental-environment.md ← how to avoid over-restriction in test envs
│   ├── 05-leaf-creation.md          ← when and how to create leaves for defects
│   ├── 06-gate-records.md           ← gate record conventions (keep them short)
│   └── 07-design-principles.md      ← the 8 core principles
├── templates/
│   ├── prompts/                     ← ready-to-use prompt templates per role
│   │   ├── supervisor.md
│   │   ├── planner.md
│   │   ├── researcher.md
│   │   ├── executor.md
│   │   ├── reviewer.md
│   │   ├── observer.md
│   │   └── reset-directive.md       ← the "unstick" prompt for stuck supervisors
│   ├── gate-record.md               ← gate record template
│   ├── workcard.md                  ← workcard template
│   └── copilot-instructions.md      ← code discipline rules (for E and RV)
├── notes/
│   └── 2026-09-30-supervisor-strictness-incident.md  ← the Terra lesson
└── omp/                             ← OMP-specific integration
    ├── README.md
    └── subagent-setup.md
```

## Key design decisions

- **The Observer is not in the state machine.** It is a parallel, human-triggered role that reads gate records and produces plain-English summaries. It does not block, modify, or intervene.
- **The Reviewer is advisory, not blocking.** The Reviewer produces findings. The Supervisor reads them and decides. The Reviewer cannot veto.
- **Gate records are short.** Target: 200 lines. They are for machine-to-machine tracking, not for human reading. The Observer is the human-facing layer.
- **In experimental environments, the only constraint is scope, not method.** If the test cluster is broken, fix it. Restart it. Recreate it. The agents are not allowed to invent restrictions the user did not state.

## Extending to other harnesses

The core docs in `markdown/` and the templates in `templates/` are harness-agnostic. To add a new harness:

1. Create a new top-level directory (e.g., `opencode/`, `cursor/`).
2. Document how to set up subagents, inject prompts, and manage gate records in that harness.
3. Link back to the core docs for the generalized concepts.

## Contributing

This is a living reference. Update it when you learn something new:

- A new failure mode → add it to the relevant role contract doc
- A new prompt template that works → add it to `templates/prompts/`
- A new harness integration → create a new top-level directory
- A correction to an existing doc → just fix it; git history preserves the old version
