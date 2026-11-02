# OMP on monstera — environment preparation for the tier-c-v2-migration campaign

**Date:** 2026-11-02 10:17 JST (authored)
**Executor:** an opencode session running **on monstera** (`michel@monstera`),
working directory `/home/michel/Work/appthrust`.
**Purpose:** make monstera able to host the OMP Supervisor session for the
`tier-c-v2-migration` campaign, mirroring the laptop's OMP configuration, so
that the campaign (including the ~1.5 h live proof on `kind-michel-cluster`)
runs with **no Tailscale in the loop** (user decision D6).
**Campaign docs:** `agent-orchestration/markdown/plans/tier-c-v2-migration/`
(vision: `agent-orchestration/evidence/solo-mode-plans/agent-threat-detector-v2-vision.md`).

**Scope of this runbook (and ONLY this):** install OMP, sync the needed
repositories, write the OMP config files, verify vLLM + kubectl + GitHub
auth, create the tmux session. **Do not touch the cluster. Do not modify any
repository. Do not create GitHub repos. Do not handle or invent API keys** —
when a credential is needed, stop and ask the user.

## 0. State as found (verified from the laptop by SSH, 2026-11-02 10:17 JST)

- Present on monstera: `kubectl` (/usr/local/bin/kubectl), `git`, `python3`, `tmux`.
- **Not** present: OMP, `~/.omp/`.
- `/home/michel/Work/appthrust/` exists and contains: `pipelineml-anomaly-detector`,
  `pipelineml-anomaly-injector`, `pipelineml-log-analyser`,
  `pipelineml-log-anomaly-detector`, `pipelineml-shared`, `pipelineml-tester`,
  `pipelineml-training-daemon`, plus `deploy-tests/`, `experiments/`,
  `instructions/`, `logs/`, `notes/`, `gpu_test.py`,
  `tierc-dashboard-cii-p9ztnsdl/` (retired host dashboard — leave alone).
- **Missing repos to clone:** `agent-orchestration`, `agent-threat-detection`,
  `agent-threat-tier-c`.
- The kind cluster `kind-michel-cluster` runs on this host; vLLM (Qwen 3.8 27B)
  serves on the host at port 8080 (reached from inside kind as 172.18.0.1:8080).

## 1. Install OMP (pin the laptop's version)

```sh
curl -fsSL https://omp.sh/install | sh -s -- --binary --ref v18.13.3
omp --version        # expect: omp/18.13.3
```

If the installer lands the binary outside `PATH`, locate it
(`ls ~/.local/bin/omp`) and note the path.

## 2. Sync the repositories (mirror the laptop layout)

For each repo: if the directory exists, `git -C <dir> fetch --all && git -C <dir> status --short`
and **leave it as-is if it has local changes** (report instead of touching);
otherwise clone. All clones go into `/home/michel/Work/appthrust/`.

| Repo | URL | Notes |
|---|---|---|
| `agent-orchestration` | `https://github.com/OthmanB/agent-orchestration.git` | orchestration home; S launches from here |
| `agent-threat-detection` | `https://github.com/appthrust/agent-threat-detection.git` | source of the demo controller + generator (frozen after V2-0 tag) |
| `agent-threat-tier-c` | `https://github.com/appthrust/agent-threat-tier-c.git` | source of T-layer + pre-processor (frozen after V2-0 tag) |
| `pipelineml-tester` | `https://github.com/appthrust/pipelineml-tester.git` | source of the dashboard (update if present) |
| `pipelineml-log-analyser` | `https://github.com/appthrust/pipelineml-log-analyser.git` | chart path only (update if present) |
| `pipelineml-log-anomaly-detector` | `https://github.com/appthrust/pipelineml-log-anomaly-detector.git` | chart path only (update if present) |

`agent-threat-detector-v2` is **created later by the campaign (V2-0)** — if it
already exists on GitHub at run time, clone it too.

GitHub auth for cloning/pushing: verify `git ls-remote https://github.com/appthrust/pipelineml-tester.git HEAD`
succeeds. If it prompts or fails, **stop and ask the user** for the credential
mechanism (SSH key or token) they want on this host.

## 3. OMP configuration (mirror the laptop, two adjustments)

Create `~/.omp/agent/` and write **`config.yml`** exactly as below (it is the
laptop's `~/.omp/agent/config.yml`, unchanged):

```yaml
setupVersion: 2
modelRoles:
  default: vllm-tp2-local/qwen3.8-27b-q4-gpukv-native:xhigh
  review: openai-codex/gpt-6.1-sol:high
  supervisor: anthropic/claude-sonnet-5-5:high
  execution: vllm-tp2-local/qwen3.8-27b-q4-gpukv-native:xhigh
  research: deepseek/deepseek-flash:high
  plan: anthropic/claude-sonnet-5-5:xhigh
  task: "@execution"
  live_openai: vllm-tp2-local/qwen3.8-27b-q4-gpukv-native:xhigh
  live_copilot: vllm-tp2-local/qwen3.8-27b-q4-gpukv-native:xhigh
  smol: vllm-tp2-local/qwen3.8-27b-q4-gpukv-native:xhigh
  slow: vllm-tp2-local/qwen3.8-27b-q4-gpukv-native:xhigh
retry:
  fallbackChains:
    deepseek/deepseek-flash:
      - vllm-tp2-local/qwen3.8-27b-q4-gpukv-native:xhigh
    anthropic/claude-sonnet-5-5:
      - github-copilot/claude-sonnet-5.5:xhigh
      - openai-codex/gpt-6.1-sol:xhigh
defaultThinkingLevel: high
modelRoleStorage: global
secrets:
  enabled: true
tools:
  approvalMode: yolo
bash:
  patterns:
    - match: systemctl *
      approval: prompt
    - match: service *
      approval: prompt
async:
  enabled: true
task:
  maxConcurrency: 2
  maxRecursionDepth: 2
  isolation:
    enabled: false
composer:
  shape: pi
steeringMode: one-at-a-time
memory:
  backend: "off"
dev:
  autoqaConsent: granted
codexResets:
  autoRedeem: "no"
```

Write **`models.yml`** as the laptop's, with the **one** adjustment that the
vLLM provider is host-local here (`127.0.0.1` instead of the laptop's
Tailscale IP):

```yaml
providers:
  vllm-tp2-local:
    baseUrl: "http://127.0.0.1:8080/v1"
    api: openai-completions
    apiKey: AI_SERVER_API_KEY
    authHeader: true
    models:
      - id: qwen3.8-27b-q4-gpukv-native
        name: Qwen3.8 27B Q4 GPU-KV, 262k
        reasoning: true
        contextWindow: 262144
        maxTokens: 32768
        thinking:
          mode: effort
          efforts: [minimal, low, medium, high, xhigh]
          defaultLevel: medium
        compat:
          qwenTemplateReasoningEffort: true
  deepseek:
    baseUrl: "https://api.deepseek.com/v1"
    api: openai-completions
    apiKey: DEEPSEEK_API_KEY
    authHeader: true
    models:
      - id: deepseek-flash
        name: DeepSeek V4.1 Flash
        reasoning: true
        contextWindow: 128000
        maxTokens: 8192
        thinking:
          mode: effort
          efforts: [low, medium, high, xhigh]
          defaultLevel: medium
```

The project-level subagent definitions (`agent-orchestration/.omp/agents/*.md`)
come with the cloned repo — do **not** recreate them by hand.

## 4. Provider credentials (user-supplied — never invented)

The campaign needs working credentials for: `anthropic` (S + P roles),
`openai-codex` (RV role), `deepseek` (R role), and the local vLLM (E role;
`AI_SERVER_API_KEY` — the host vLLM may accept any non-empty value).
**Do not copy secrets from the laptop and do not guess.** Stop and ask the user
how they want each provided on this host (OMP `/login` flows, environment
variables, or OMP secrets). Record in the final report which ones are set and
which are still pending — pending credentials are a `waiting_external` item
for the campaign, not a failure of this runbook.

## 5. Verification checklist (all must pass; report each)

1. `omp --version` → `omp/18.13.3`.
2. `ls /home/michel/Work/appthrust/agent-orchestration/AGENTS.md` exists.
3. `git -C /home/michel/Work/appthrust/agent-orchestration log --oneline -1` works.
4. vLLM: `curl -s -m 10 http://127.0.0.1:8080/v1/models | head -c 200` returns a JSON model list containing `qwen3.8-27b-q4-gpukv-native`.
5. Cluster: `kubectl --context kind-michel-cluster -n threat-detection-tierc get pods` lists the 5 live pods (analyser, detector, controller, dashboard, preprocessor) Running.
6. OMP model discovery: `omp models vllm-tp2-local` (or equivalent discovery) shows the Qwen model; if the command name differs in 18.13.3, use the closest read-only equivalent and note it.
7. GitHub: `git ls-remote https://github.com/appthrust/pipelineml-tester.git HEAD` succeeds.
8. Credentials status per §4 (list set / pending).

## 6. tmux session + Supervisor launch (the handover point)

```sh
tmux new-session -d -s v2-campaign
tmux send-keys -t v2-campaign 'cd /home/michel/Work/appthrust/agent-orchestration && omp' C-m
tmux attach -t v2-campaign   # (for the user; the opencode session may stay detached)
```

The Supervisor session launched from `agent-orchestration/` auto-loads that
repo's `AGENTS.md` (campaign posture, parallel-leaf policy). The Supervisor's
first prompt is the campaign dispatch: read
`markdown/plans/tier-c-v2-migration/plan.md` + `s-decisions.md` and start wave 1.
**The opencode prep session does NOT start the Supervisor's work** — it stops
once §5 is green and the tmux session exists, and reports.

## 7. Out of scope / stop conditions

- Any cluster mutation, repo modification, GitHub repo creation, or secret
  handling → out of scope; stop and report.
- No internet egress for the cloud providers (anthropic/openai-codex/deepseek)
  → report as a blocker (the campaign cannot run S/P/RV without it).
- vLLM down or model missing → report; the E role cannot run without it.
- Anything that conflicts with `agent-orchestration/AGENTS.md` → the AGENTS.md
  wins; record the conflict.

**Report at the end:** checklist results (§5, pass/fail per line), the pending
credential list, the tmux session state, and any deviations from this runbook.
