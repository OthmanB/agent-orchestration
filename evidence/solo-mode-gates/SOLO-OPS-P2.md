# SOLO-OPS-P2 — solo dashboard UI batch — Gate Record

- Date: 2026-11-06 · Status: **promoted** (live real-browser acceptance on the deployed image)
- S: `anthropic/claude-sonnet-5-5`. R/P/E/RV per `omp/subagent-setup.md` (configured models; actual runtime not independently verified by S).

## 1. Context
- Parent: vision §3-P2 / supervisor prompt. Workcards `evidence/omp-workcards/solo-ops-P2.md` + `solo-ops-P2-rev1.md` (one revision cycle). One file: `analyser/dashboard_assets/index.html` (+708/−53 lines). P1's ConfigMap shipped in the same rollout (SOLO-OPS-P1.md).

## 2. Evidence
- R-P2 (`E-solo-dashboard-ops/R-P2.md`) refinements, all consistent with the vision (no contradiction of §2): (1) the CDF lives per metric at `reference_models[m].residual_cdf` (`points` `[residual,cdf]` ×570 + raw `residuals` ×570 → PDF without API change); (2) no "mode" field exists in `/system` or `/pods` — solo gating rides `active_model_family`/selection; (3) the external `/timeseries` ring for the solo pod is unstable (60 points then 0) → timeline is rendered **client-side** from the already-fetched 288-tick `/solo` payload (no route change; external-pod contract untouched).
- P resolved the open points: pre-selection gate = non-empty pod list with every row `solo_statistical` (else the selection) so Baseline/Lineage are grayed on first paint; gray = class + `aria-disabled` + tooltip + click guards (never hidden: the Playwright test asserts the link visible); Guide inline in `index.html`, always visible; decision rule uses `≥` per code (`_decision_from_probability`), not the report's `>`.
- E v1 smoke 44/44, integration 3/3 + static bundle 7/7. **RV-P2 rejected v1** (`RV-P2.md`): 1 blocker + 7 should-fix. S accepted all 8, E fixed in revision 1 (`E-P2.md` "Revision 1"):
  1 [blocker] timeline decisions all `unknown` (threshold-shape mismatch — gray markers on all 288 live points); 2 stale "No timeseries data" node after empty→populated; 3 null `p_published` plotted as 0; 4 null residual/CDF/PDF inputs coerced to 0; 5 invalid/out-of-range timestamps counted or throwing; 6 Pod-Level prose still said raw = "calibrating"; 7 Guide CDF wording contradicted mid-rank semantics; 8 timeline ISO-UTC vs other charts epoch-ms → same tick 9 h apart in Asia/Tokyo (now epoch-ms everywhere, `type:'date'`).
- RV re-review (`RV-P2-rev1.md`): **accepted_with_findings**, 0 blockers, 1 should-fix: `soloRenderTimeline`'s `finiteNumber()` still maps an explicit JSON `null`/`''` threshold to a 0-line. S decision: **recorded as accepted debt, not fixed** (campaign posture; real payload thresholds are always numeric or absent — absent already yields no line; no scored number or main flow is affected). Smoke after rev1: 64/64 (44 + 20 new), tests 10/10, syntax OK; tz alignment delta 0 in Asia/Tokyo and UTC.
- 29 unit failures in `analyser/.venv_test` are missing modules (`tabulate`/`hickle`/`shared`), independent of `index.html` (RV sampled 3 files; E per-file census 801 pass / 29 fail). This blocks nothing in P2; **P3 needs a proper env (R-P3 item 5)**.

## 3. Commits / image / rollout
- Commits (feature branch `feature/cnn2dlstm-bayesian-statistical-detector-v2`, ordinary, no force; pushed — push of ordinary commits to the existing feature branch is implied by the prompt's build-via-GitHub-workflow loop): `e887f68` P1 ConfigMap, `37ca32e` P2 UI, `eadd2e3` digest pin (`deployment.yaml` header+`image:`, `deploy/k8s/README.md`).
- Build: `docker-build.yml` `workflow_dispatch`, `no_cache=false`, run **42185359776**, headSha `37ca32e78a1381d80c6478096b27bd909d1b63ca`, build amd64 08:44:47Z + arm64 08:48:08Z + merge 08:48:25Z, conclusion success. Merged index digest (from the merge job log, pushed to both branch tag and sha tag `…-v2-37ca32e`): `sha256:9bc505fe34b1be1ec6125b0c3aacb694cecd28227741a1686e3fe7e0667a7947`; runnable amd64 `e3f9687c…`, arm64 `2d2c5c9d…`.
- Rollout (solo Deployment only, S): `kubectl apply` solo ConfigMap (diff live→new = 3 keys) then `kubectl set image` → `Recreate`; set-image timestamp **2026-11-06T08:50:06Z**; new pod `pipelineml-anomaly-detector-solo-6cc64d899f-k24zm` container started 08:56:21Z (6 min pull), Ready, 0 restarts. Spec preserved (verified live): strategy Recreate, fsGroup 999, resources 250m/1Gi–1/3Gi, PVC `…-solo-state`, ConfigMap `…-solo-config`, Service unchanged, API=false config.
- Route (only): `ssh rtx-4000-test` → `$HOME/.local/bin/kubectl --context kind-rtx-4000-cluster`. (Locating the cluster, S ran two read-only listings on monstera `kind-michel-cluster` — wrong cluster, no mutation.)
- **Forward:** the user's `127.0.0.1:8080` forward (k9s pod-bound) ended with the Recreate (HTTP 000) — not stopped/renewed by S. Supervisor-owned equivalent: `127.0.0.1:18086` → solo Service (service `solo-preview-18086`, 129600 s remote cap; kill at campaign end).

## 4. Protected pair before/after (rollout)
`E-solo-dashboard-ops/protected-before-rollout-p2.txt` vs `protected-after-rollout-p2.txt`: **identical** (ml-components Deployments uid/resourceVersion/replicas/image, all pod uid/start/restarts, ConfigMaps rv) — detector `…-7ee1951` rv 7376946, training-daemon `…-3a3f23c` rv 54419, tester orchestrator + 4 workload deployments, mlflow. Nothing in ml-components touched.

## 5. Acceptance (real Chromium, deployed image, `http://127.0.0.1:18086/dashboard/`)
Tab opened by `browser`, headless Chromium, 1440×900; artifacts `E-solo-dashboard-ops/s-live-shots/*.png`.
- First paint, no selection: Baseline link + Lineage tab `aria-disabled=true` with tooltip "Not applicable in solo mode — …"; Lineage click does not activate its panel; System/Health + Maintenance enabled; Guide tab present.
- Selected non-default pod (`…checkout-worker-v1-…-2vwwd`, 6th row) + non-default metric `container_memory_working_set_bytes`, window scrolled to 1500 px: **5 automatic `/pods` refreshes and 4 `/solo` fetches over 22 s with no manual action** → metric, scrollY (1500), pod-list scroll, `#solo-panel` visibility and CDF-chart page offset (3250) all unchanged.
- CDF: marker `(x=-9875.1, y=0.390351)`; nearest curve point y=0.390351, dx=0 → **on the curve** (was y=1.0), `y<1`. PDF histogram (570 residuals) in the same card, left of CDF (box x=102 vs 726, widths 612).
- Axis titles on all five solo charts (observed/per-tick/pod-level: x "Time", `type:date`; CDF/PDF: x "residual (observed − expected), metric units", y `F(r)`/`density`); 4 formula lines present; two norms stated in the per-tick prose + Guide. Pod-level curves labelled "Published p — calibrated: mapper(p_raw)" / "Raw Markov posterior p_raw".
- Probability and Decision Timeline: 288 plotted points, `#chart-point-count`=288, no "No timeseries data" node; marker colours by decision (live: 203 normal / 85 undecided). Maintenance line: "… Export/delete act on this process's event-history store (not model or scoring state)".
- Guide: 6 menu entries, first page "The scoring chain" active, each entry activates exactly one page. Screenshots read by S (guide-chain, dashboard-top).
- Indicator B: all 10 pods green (P1). Indicator A still `warning` for most pods (calibration sawtooth) — **P3's job**, intentionally untouched here.
- Not exercised: viewport <1024 px on the deployed image (RV did 900 px on the local proxy); `Plotly.Plots.resize` after hidden-tab refresh (accepted limitation, heals on next 5 s tick).

## 6. State / Next
- P2 terminal: promoted; accepted-debt entries appended to `evidence/solo-mode-plans/accepted-debt.md` (null-threshold zero-line; baseline round-trip from `baseline.html`/`history.html`; `/solo` 7.4 MB per 5 s tick unchanged).
- Dependents unlocked: **P3** (R dispatched immediately after the live proof). P3 image will be built from a later commit; P2 image is the proven base.
