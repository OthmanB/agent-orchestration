# Tier C v2 migration — plan (sketch, 2026-11-02)

**Status: SKETCH — pre-R/P input.** Written by the Observer from the 2026-11-02
dependency audit; P adopts, narrows, or revises it after R's wave-1 research.
Nothing here is a workcard until P issues one and S accepts it.

- Parent vision: `agent-orchestration/evidence/solo-mode-plans/agent-threat-detector-v2-vision.md`
- Binding user decisions: `s-decisions.md` D1–D10 (this directory)
- Campaign home: this directory (`plan.md`, `workcard-v2<N>.md`,
  `evidence/v2<N>-gate.md`, `record.md`, `accepted-debt.md`)
- Source repos (frozen baselines, tagged by V2-0): `agent-threat-detection`,
  `agent-threat-tier-c`, `pipelineml-tester` (+ read-only: `pipelineml-log-analyser`,
  `pipelineml-log-anomaly-detector` for chart paths/digests)
- Target repo: `github.com/appthrust/agent-threat-detector-v2` (D3)

## 1 Packages (owner E; V2-7 and V2-8 are S)

| Id | Objective | Needs | Wave | Acceptance (short form) |
|---|---|---|---|---|
| V2-0 | Create target repo + layout; tag baselines of all source repos; snapshot live cluster (pods, digests, ConfigMap hashes, generation id, Secrets inventory) | — | W1 | repo exists empty-of-code; baseline tags recorded in `evidence/v2-0-gate.md`; cluster snapshot file committed |
| V2-1 | Move T-layer (`tc_intent`) + pre-processor (`tc_preprocessor`) + their configs/tests/Dockerfile/image workflow; `cluster` → `tier-c-local-demo` in preprocessor YAML (D8) | V2-0 | W1 | `git diff` of moved packages empty modulo renames; preprocessor closed-schema loader green on moved YAML; old repo untouched (frozen at tag) |
| V2-2 | Move demo controller → `tc_demo`; add `tc_delivery` (9-key event render + POST `/ingest`, fail-closed, counters); replace the 4 Tier 2 imports; self-contained `demo.yaml` (new `pipeline:` section, no `tier2_config_path`, no gateway/vector keys); move `dashboard.yaml`, `preprocessor.yaml` authorities | V2-1 (`tc_intent` import) | W2 | tc_demo suite (green subset, D5) passes; `demo.yaml` validates offline with zero external-repo reads; event bytes byte-identical to the proven pre-processor body for the same intent |
| V2-3 | Move dashboard → `tc_dashboard` + `config/tier-c.yaml`; rewrite `staging.py`/`bridge.py` for the single-repo layout (one source root, no `tier2-config.yaml` staged-bytes check — replaced by `pipeline.yaml` check) | V2-1 | W2 (∥ V2-2, disjoint files; commits serialized) | dashboard tests (green subset, D5) pass; staging byte-equality check passes against the new single-repo ConfigMap layout |
| V2-4 | Rewrite `generate_demo.py` (single repo; values generation moved in from `external-pipeline`; no Tier 2/tester/tier-c cross-repo imports — loaders moved in as `tc_*` config packages); `pipeline.yaml` + compact validator; `bootstrap-tierc.yaml`; three Dockerfiles; three image workflows; publish + digest pins | V2-2, V2-3 | W3 | `--check` deterministic regeneration; the two Helm values files diff vs the old ones shows ONLY generation/identity changes; 3 images published, digests recorded in gate |
| V2-5 | Naming/generation cutover values: new generation id + feature root, `tier-c-local-demo` scope identity in values, re-authored scenario texts, egress trims (drop Vector + TLS targets; keep analyser/prometheus/provider/DNS), secret reuse list | V2-4 | W4 | offline validation green; rendered artifact set complete and `--check`-stable |
| V2-6 | Docs: `operator-guide.md` (Mode 1 demo / Mode 2 pre-processor, each with fresh install + daily use + teardown), `config-reference.md`; test-coverage review pass (D5) — record which new tests are actually needed | V2-4 | W4 (∥ V2-5) | docs name no Tier 2 symbol; coverage decision recorded in gate with file list |
| V2-7 | **Live proof, S-only, from monstera OMP (D6):** fresh generation rollout on `kind-michel-cluster` ns `threat-detection-tierc`; demo lifecycle `validate → normal(48) → explicit acceptance → attack(20) → critical`; pre-processor smoke (irregular text → forwarded == analyser accepted delta → detector `/api/pods` buckets growing); evidence | V2-4..V2-6 | W5 | full gate record with observed numbers; old generation untouched (its ConfigMap hashes unchanged) |
| V2-8 | Decommission: remove `src/pipelineml_tester/tier_c/` + `config/tier-c.yaml` + entrypoint + tests from pipelineml-tester (D4); archive `agent-threat-tier-c`; freeze `agent-threat-detection` (add FROZEN banner, no Tier C files remain in living tree); final record + accepted-debt | V2-7 promoted | W6 | old repos at recorded tags + freeze commits; no Tier C code outside `agent-threat-detector-v2` |

## 2 Schedule (max 2 leaves; see `agent-orchestration/AGENTS.md` § Parallel execution)

- W1: V2-0 (S) → V2-1. W2: V2-2 ∥ V2-3 (disjoint file sets in the new repo;
  canonical-branch commits serialized). W3: V2-4. W4: V2-5 ∥ V2-6.
  W5: V2-7 (S-only, serialized, ~1.5 h, from monstera). W6: V2-8.
- E commits locally only (`git commit --only` on card paths, no `git add -A`).
  S-only: pushes, workflow/digest observation, every `kubectl` mutation, live
  smoke, record. The old repos are never written to before V2-8.

## 3 Pinned values (binding unless P escalates a material revision)

| Item | Value |
|---|---|
| Target repo | `github.com/appthrust/agent-threat-detector-v2`, canonical branch `main` |
| Package dirs | `src/tc_intent`, `src/tc_preprocessor`, `src/tc_demo`, `src/tc_delivery`, `src/tc_dashboard` |
| Config files | `config/{tier-c-intent,tier-c-preprocessor,demo,dashboard,preprocessor,tier-c,pipeline,timing-inventory}.yaml` |
| Images | `ghcr.io/appthrust/agent-threat-detector-v2/{tc-demo-controller,tc-dashboard,tc-preprocessor}` — digest-pinned, built only by the new repo's workflows |
| Namespace / context | `threat-detection-tierc` / `kind-michel-cluster` (unchanged; fresh generation coexists) |
| Generation | NEW id (V2-5 names it; must be distinct from `tierc-dashboard-incluster-g1`); feature root derived from it |
| Cluster identity | `tier-c-local-demo` (replaces `tier2-local-demo` everywhere: preprocessor `identity.cluster`, analyser `scope_filters.cluster`, detector `source.missing_cluster_value` context, event `cluster` key) |
| Pod family | `deployment-assistant-tier-c-v0` (UNCHANGED — shared-baseline design decision D3 of the pre-processor plan; renaming it would orphan the scope filters) |
| Secrets | reuse `regcred`, `tier-c-live-runner-credentials`, `tierc-demo-dashboard-credentials` (all already Tier C-named); `tier2-source-upstream-tls` is NOT used by any v2 manifest |
| Scenario texts | re-authored by V2-5 in the new repo (the old texts stay as history in the frozen repo); semantics preserved (one normal preview; multi-entity secret/exec/egress attack) |
| Demo paces/durations | unchanged: 67 s bucket, `[1,2,3]` events/cycle, 48/24/20/1 buckets |
| Reference acceptance | unchanged: 40 minimum scores, 3 stability observations, 412 s score-age budget, 134 s finalization lag |
| Analyser/detector | repos, code, and feature semantics untouched; only new-generation Helm values (V2-4/V2-5) |

## 4 Test policy (D5, binding)

1. **Port only tests that are green at the source-repo baseline** and still
   meaningful after the move. Known baseline failures are recorded (from
   R's V2-0/V2-4 research, e.g. the 3 recorded `test_generate_demo.py`
   failures tied to the old two-repo layout) and **not** ported.
2. No test is ported to make the suite "look big"; no test is weakened to pass.
3. V2-6 runs the explicit coverage review: minimum required set = closed-schema
   loaders (every moved config), generator determinism (`--check`),
   `tc_delivery` event byte-parity against the proven live body, staging
   byte-equality, and the fail-closed matrices that already exist green.
   Anything else is a deliberate, recorded decision.
4. Accepted debt (findings recorded, not fixed) goes to `accepted-debt.md`.

## 5 Live-proof procedure (V2-7, S-only, from the monstera OMP session)

Prereqs: `instructions/2026-11-02/omp-on-monstera-setup.md` checklist green;
vLLM up on the host; all three images published with digests recorded; V2-5
artifacts `--check`-stable.

1. `kubectl --context kind-michel-cluster` sanity: old pods + generation state
   unchanged (record hashes before touching anything).
2. Roll out the fresh generation: Helm releases (new values), then controller,
   dashboard, pre-processor manifests; rollouts to Ready.
3. Demo lifecycle (dashboard or CLI): `validate` → `normal-training` (48
   buckets) → explicit reference acceptance (40 distinct / 3 ticks) →
   `attack` (20 buckets) → observe `critical` on the attack comparison.
4. Pre-processor smoke: irregular operator text via `POST /api/items`
   (port-forward from monstera); `forwarded` counter == analyser `accepted`
   delta; detector `/api/pods` shows the family with growing `n_buckets`.
5. Record `evidence/v2-7-gate.md` (numbers, run ids, image digests, timestamps);
   verify old-generation objects untouched.

## 6 Known unknowns (R resolves in wave 1)

- Exact `pipeline.yaml` key set and the moved generator's values-stage seam (§8-2 of the vision).
- Which of the ~20 staged `tier2_*` modules are truly dead on every path.
- Baseline-failing test lists per source repo (D5 input).
- New-repo CI prerequisites vs the source repos' proven workflows.
- Current cluster Secret/ConfigMap inventory for the fresh install.
- Live detector image digest discrepancy (`ea031f…` live vs `4ef9cd…` local) —
  R determines which is current; V2-4 pins digests from the published images anyway.
- Live-runner jobs disposition (recommend: archive, do not move).

## 7 Deviations & escalation

P may revise file/symbol/test/sequencing details autonomously (00-model:
Autonomous Replanning). Any change to a §3 pinned value, to the package set, or
to the scored pipeline is a **material revision → S escalates to the user**.
3-strike rule applies per package/leaf.
