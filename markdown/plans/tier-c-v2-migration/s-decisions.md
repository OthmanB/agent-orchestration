# Tier C v2 migration — user decisions (binding for S / P / R / E / RV)

Date: 2026-11-02. Recorded by the Observer from the user's explicit answers in
the walk-through session. These resolve the vision's open design points; R
researches within them, P plans within them, and only a **material revision**
(needing user approval) may change one.

| # | Question | Decision | Why (user's words, condensed) |
|---|---|---|---|
| D1 | Demo delivery route | **Direct to the analyser `/ingest`** (like the pre-processor). The in-pod mTLS gateway, the Vector hop, the `tier2-source-upstream-tls` Secret, and the Tier 2 sender/gateway code are dropped from the Tier C system. | The gateway/Vector mechanism is Tier 2's "too complex mechanics"; the retained path is LLM-normalized intents → analysis system. |
| D2 | Repository topology | **Single new repo `agent-threat-detector-v2`** absorbing the T-layer, the pre-processor, the demo controller, the dashboard, all configs, all three image builds, and all Tier C docs. | User's ideal (c): all deployment images (except analyser/detector, config-only reference) in one own repository. |
| D3 | New repo name | `agent-threat-detector-v2`. | Confirmed 2026-11-02. |
| D4 | Old repos after the new demo passes | **Remove and freeze:** remove the `tier_c` subpackage + `config/tier-c.yaml` + entrypoint + tests from pipelineml-tester; archive `agent-threat-tier-c`; freeze `agent-threat-detection` (Tier 2 history; its dormant `tier2_bootstrap_producer` in pipelineml-tester stays — it is Tier 2, not Tier C). | No Tier C code should remain in Tier 2-named places. The user first asked what in pipelineml-tester is Tier 2-specific; answer: only the dormant bootstrap producer — the rest is the Tier C dashboard (moved, not lost). |
| D5 | Tests | **Phase 1: do NOT port tests that are known-failing at baseline** (record them instead). Then a deliberate pass (V2-6) decides which *additional* tests are genuinely required. | "Tests were mostly over-complicated… work with the fresh repo for tests and avoid circumvolutions and over-complications." |
| D6 | Live-proof environment | **OMP runs on monstera itself** (working dir `/home/michel/Work/appthrust`, tmux session), mirroring the laptop's OMP configuration; the preparatory setup is a **separate runbook** (`agent-orchestration/instructions/2026-11-02/omp-on-monstera-setup.md`) executed by an opencode session on monstera before the Supervisor dispatch. | "That would solve 99% of the problem I had so far (no more tailscale issues)." |
| D7 | Image digests | Re-pin all digests at cutover from the published images (workflow job logs). Resolves the observed live-vs-local detector digest discrepancy (`sha256:ea031f…` vs `sha256:4ef9cd…`) without a separate investigation of which is "current". | Accepted as-is. |
| D8 | Naming on the cluster | New generation id (distinct from `tierc-dashboard-incluster-g1`); cluster identity **`tier-c-local-demo`**; pod family **unchanged** (`deployment-assistant-tier-c-v0`); namespace unchanged (`threat-detection-tierc`); scenario texts re-authored in the new repo (old texts = history). | Removes the last "tier 2" strings from the live Tier C path; a fresh generation absorbs the identity rename safely. |
| D9 | Analyser / detector | **Untouched** — their repos, code, images, and scored semantics are out of scope; the new repo references their Helm charts and image digests (configuration only). | User's exception (c): "excepted of course of analyser and detector images, which are not the same program; only configuration could be cited". |
| D10 | Campaign artifacts | Vision in `agent-orchestration/evidence/solo-mode-plans/`; plan/workcards/gates/record in `agent-orchestration/markdown/plans/tier-c-v2-migration/` (the campaign creates and freezes repos, so it is not owned by any single source repo; precedent: `tier-c-end-to-end-demo`). | Precedent-based placement; keeps the new repo clean. |

## Verification expectations carried into the plan

- V2-7 (live proof) is the only package that may mutate the cluster; it runs
  from monstera (D6) and must show: full demo lifecycle to `critical` +
  pre-processor smoke, with the old generation's objects verifiably unchanged.
- The pre-processor's proven event shape (9-key body, byte-parity) is a
  preserved invariant of V2-2's `tc_delivery` — the direct demo route must
  emit the same shape the live pre-processor already emits.
