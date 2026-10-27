# AGENTS.md — agent-orchestration

Rules for agent sessions running from this directory (OMP Supervisor sessions,
standalone Observer sessions). This file is auto-loaded at session start and
survives context compaction.

## Sources of truth

- Orchestration model: `markdown/00-orchestration-model.md`
- Role contracts: `markdown/02-role-contracts/`
- Design principles: `markdown/07-design-principles.md`
- OMP integration notes: `omp/`
- Prompt templates: `templates/prompts/`

## Experimental environment posture (standing)

This orchestration runs in a **safely isolated test environment**. The systems
it drives (including the `pipelineml-tester` dashboard) are **capability-
assessment tools — not production, never internet-facing**.

- The only constraint is **scope** (what systems may be touched), not **method**
  (how they may be touched). See `markdown/04-experimental-environment.md`.
- **Do not invent constraints.** Before writing any "No X", apply the test:
  *did the user say this, or did I invent it?* If it was invented, flag it to the
  user instead of adding it.
- **Do not add production security hardening, monitoring, or operational
  tooling** that the task's vision/directive does not require.
- This section is standing policy and is re-asserted on every context compaction.

## Parallel execution (concurrent leaves)

OMP supports concurrent subagents via `task.maxConcurrency` in
`~/.omp/agent/config.yml` (OMP default is 32; this campaign sets it to 2).
Standing policy for this orchestration root:

- Up to **two** leaves may run concurrently. Rationale: the execution role runs
  on a local vLLM server with a 3-concurrent-session budget; one session is
  reserved for lightweight/smol model calls.
- Parallel leaves must have **independent scope**: disjoint files, and separate
  sub-repositories where possible. Two leaves must never touch the same file,
  the same git branch state, or the same deployment resource.
- Within a leaf the role sequence stays serial: R → P → E → RV → S.
  Parallelism is across leaves, never within one.
- Each parallel leaf is a separate executor subagent holding exactly one
  workcard; this does not violate the executor contract ("one workcard at a
  time").
- **Always serialize** the following, even between parallel leaves:
  - git commits and pushes on the canonical branch
  - deploys and cluster state mutations against the shared cluster
    (currently `kind-michel-cluster`)
  A leaf that needs a serialized step waits for the other leaf to release it.
