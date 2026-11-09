# E-P3 — calibration-mapper refit loop + degeneracy guard (implementation report)

Date 2026-11-06. Repo `pipelineml-anomaly-detector`, branch
`feature/cnn2dlstm-bayesian-statistical-detector-v2`, HEAD `eadd2e3`. Workcard
`evidence/omp-workcards/solo-ops-P3.md` (S DECISION D1-D3 + slow-scenario policy
approved as written). All changes uncommitted. Env:
`cd analyser; export PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared
PY=/tmp/solo-p3-venv/bin/python` (venv pre-existed, Python 3.10.22 — R-P3 §5 recipe).

## 1. Files changed (exactly the Contract + six test files; verified `git diff --stat`)

Production (Contract 1-6):
- `analyser/config/detector-common.yaml` — `degeneracy.min_calm_span_ratio: 1.0` (6-space indent).
- `deploy/k8s/solo-card6/configmap.yaml` — same key (10-space indent) + one header line
  (P3 image refuses to start without the key). P1 values (ttl 900 / 11.0 / 13.0) untouched.
- `analyser/solo_mode/config.py` — `_require_key(calibration,"degeneracy")` + mapping check
  (message names `solo_mode.fusion.calibration.degeneracy`) + `_require_positive_number(…,"min_calm_span_ratio")`. No code default.
- `analyser/solo_mode/fusion.py` — new `calm_span_ratio(scores, anomaly_threshold, normal_threshold, tau, prior) -> float` (D1 lower-quartile ramp; `ValueError` on `not 0<normal<anomaly<1` / `prior<=0` / non-finite / out-of-band scores; `calibration_order_index` guard applies).
- `analyser/solo_mode/state.py` — DDL + `_migrate_pod_calibration` gain `mapper_healthy INTEGER NOT NULL DEFAULT 0` + `last_fit_attempt_epoch REAL` (logged `ALTER` per missing column, pre-P3 rows read 0); `get_pod_calibration` returns the two; `complete_scored_tick` gains **required keyword-only** `mapper_healthy`, `last_fit_attempt_epoch`; `upsert_pod_calibration` gains optional (default `False`/`None`) for test seeding.
- `analyser/solo_mode/driver.py` — `handle_solo_request`: reads `mapper_healthy`/`last_fit_attempt_epoch`/previous provenance; `refit_due` (D2: not-healthy ⇒ every valid tick; healthy ⇒ `tick_end − last >= L_cal*T`); attempt stamped on every evaluated window; adopt iff gate **and** new `_calibration_guard_passes` (isotonic-only; `ValueError` ⇒ `(False,None)`+WARN); on adopt `mapper_healthy=True` + provenance (18 keys unchanged + `fit_count` + `calm_span_ratio`); no-adopt leaves everything untouched; publication `if scored and mapper and mapper_healthy`; passes the two kwargs; module docstring + inline comments rewritten (refit loop; last-adopted provenance).
- `analyser/exporter.py` — **X1 only**: `scored = calibrated or cal_state_str == "scored"`; the two inventory `status` lines use it. Nothing else touched (restore/cleanup/`calibrated` verified unchanged).

Docs (Contract 7, markdown only, no new file):
- `markdown/2026-10-09-solo-mode-runtime-cutover.md` — retitled the provenance bullet ("One-time" → "Provenance of the last adopted window"), updated the ~:815 sentence, added a ≤25-line dated addendum under "Calibration-gate liveness" (refit loop, guard + floor, `mapper_healthy`/raw sub-state, D2 pacing, `DEFAULT 0` migration, last-adopted provenance + `fit_count`/`calm_span_ratio`, X1).
- `markdown/2026-10-09-solo-mode-export-dashboard.md` §7.2 — status line (raw-scored ⇒ `scored`).
- `markdown/2026-10-09-solo-mode-config-schema.md` — table row for `fusion.calibration.degeneracy`.

Tests (six): `test_solo_fusion.py` (+3 `calm_span_ratio`), `test_solo_state.py`
(kwargs + P3-column roundtrip + pre-P3 migration leg), `test_solo_driver.py`
(+`_seed_p_raw` + 6 new), `test_solo_exporter.py` (+raw-scored fraction/restore),
`test_solo_mode_config.py` (+`degeneracy` key + validation test),
`test_dashboard_api_routes.py` (+raw-scored pods-list test).

`git diff --stat`: 16 files, +1188/−62. P4/`AGENTS.md`/untracked items byte-identical
(`git status --short` before/after match `git-before.txt`).

## 2. Fast suite — P3 tree vs pristine baseline

Command (workcard E-acceptance #1):
`$PY -m pytest tests/unit/test_solo_fusion.py test_solo_state.py test_solo_window_store.py test_solo_driver.py test_solo_exporter.py test_solo_mode_config.py test_split_config_loader.py test_config_validation.py test_solo_throughput.py test_solo_diagnostics.py test_solo_scan.py test_solo_noise.py test_solo_fresh_api.py test_solo_baseline.py test_solo_mlflow_absence.py test_dashboard_api_routes.py test_exporter.py tests/integration/test_canonical_route_contracts.py test_solo_scenarios.py -m 'not slow' -q`

| | baseline (pristine) | P3 tree |
|---|---|---|
| passed | 554 | **566** |
| failed | 0 | **0** |
| deselected | 20 (slow) | 20 (slow) |
| wall | 104.9 s | 287.9 s |

Δ = +12 new tests: fusion 20→23 (+3), state 38→38 (extended in place), driver 42→48 (+6),
exporter 21→22 (+1), config (10 added in `test_rule14c` sub-asserts, file count steady),
dashboard routes +1 (new `test_solo_raw_scored_pod_not_pipeline_critical`).
**All green.** (`test_solo_dashboard_routes.py` never run, per hard rule.)

Note: running `test_dashboard_api_routes.py` *in isolation* (not the workcard's combined
command) fails `test_build_bayesian_debug_payload_uses_shared_prediction_diagnostics` with
`ModuleNotFoundError: No module named 'mlflow'` — reproduced identically on the **pristine**
tree (`/tmp/solo-p3-base`), so it is an env-only isolation artifact, NOT a P3 regression.
The workcard's combined command passes that test (566/0). This is the "two env-only mlflow
failures in (e)" the card anticipates.

## 3. Slow-scenario policy (workcard E-acceptance #2)

All 20 params run once on the P3 tree (≤3 parallel, 3-at-a-time waves; macOS bash 3.2
has no `wait -n` — the first naive launcher over-spawned and was killed+restarted; no
partial result reused). Logs `/tmp/solo-p3-e/slow/`. Pristine baseline tree at
`/tmp/solo-p3-base` (`git archive HEAD`).

**P3 result: all 20 FAIL**, uniformly `fixture_unscorable` — "the native healthy
calibration gate **never committed** (L_cal contiguous scored window absent); zero
held-out denominator at the gate commit." 0 adoptions in every log. Each log carries the
P3 refit-loop signature `solo calibration not adopted … gate=… guard_ok=False
calm_span_ratio≈1e-13..0.27 floor=1; publishing raw`.

**Decisive classification finding.** Across the 20 logs there are **1062
`gate=True guard_ok=False`** lines and 1272 `gate=False` lines, and **0**
`calibration gate passed` (adopt) lines. I.e. on P3 the D1 guard **actively blocks
gate-passing windows** (the gate passes the held-out exceedance bound, but the fit-half
p_raw distribution is a narrow "pile" — `calm_span_ratio` ≤ 0.27 « 1.0 floor — so the
guard rejects and the gate never commits). This is the **expected-by-design class** the
S DECISION names: *"a failure whose gate never committed because the guard rejected a
pile window is expected by design … recorded, not fixed; no fixture/synth/YAML/guard
edit."* The fixture p_raw is a nearly-healthy pile (the same shape as the live pod
windows, whose ratio I measured ≈0.0000–0.017), so the guard rejecting it is correct.

**Regression reconciliation — COMPLETE: 0 P3 regressions.** Workcard #2 rule: *only a
param that passes at baseline and fails after is a regression.* Every P3 failure was
reconciled against the pristine baseline tree (`/tmp/solo-p3-base`):
- **5 exempt (D-d, already-measured baseline failures, not re-run):**
  20261012-{healthy, one_metric, group3, slow_drift} + 20261013-healthy.
- **15 non-exempt P3 failures re-run on the pristine baseline (bg_74 + bg_75): ALL 15
  FAIL at baseline too.** Not one passes at baseline ⇒ **no P3 regression.**
  - `20261013-one_metric` (bg_74): baseline FAIL, "gate committed AFTER onset
    (block_end 347400 ≥ onset 270000)".
  - bg_75 (14 params): `20261012-blip` committed-after-onset(290400);
    `20261013-group3` after-onset(347400); `20261013-slow_drift` never-committed;
    `20261013-blip` never-committed; `20261014-healthy` after-onset(307800);
    `20261014-one_metric` after-onset(335100); `20261014-group3` after-onset(343500);
    `20261014-slow_drift` never-committed; `20261014-blip` after-onset(307800);
    `20261015-healthy` never-committed; `20261015-one_metric` after-onset(351000);
    `20261015-group3` after-onset(351000); `20261015-slow_drift` never-committed;
    `20261015-blip` never-committed.

**Complete slow table (param | P3 result | baseline result | class):**

| param | P3 | baseline | class |
|---|---|---|---|
| 20261012-healthy | FAIL (never-commit) | FAIL (D-d exempt) | pre-existing |
| 20261012-one_metric | FAIL (never-commit) | FAIL (D-d exempt) | pre-existing |
| 20261012-group3 | FAIL (never-commit) | FAIL (D-d exempt) | pre-existing |
| 20261012-slow_drift | FAIL (never-commit) | FAIL (D-d exempt) | pre-existing |
| 20261012-blip | FAIL (never-commit) | FAIL (after-onset 290400) | pre-existing + guard-by-design |
| 20261013-healthy | FAIL (never-commit) | FAIL (D-d exempt) | pre-existing |
| 20261013-one_metric | FAIL (never-commit) | FAIL (after-onset 347400) | pre-existing + guard-by-design |
| 20261013-group3 | FAIL (never-commit) | FAIL (after-onset 347400) | pre-existing + guard-by-design |
| 20261013-slow_drift | FAIL (never-commit) | FAIL (never-commit) | pre-existing |
| 20261013-blip | FAIL (never-commit) | FAIL (never-commit) | pre-existing |
| 20261014-healthy | FAIL (never-commit) | FAIL (after-onset 307800) | pre-existing + guard-by-design |
| 20261014-one_metric | FAIL (never-commit) | FAIL (after-onset 335100) | pre-existing + guard-by-design |
| 20261014-group3 | FAIL (never-commit) | FAIL (after-onset 343500) | pre-existing + guard-by-design |
| 20261014-slow_drift | FAIL (never-commit) | FAIL (never-commit) | pre-existing |
| 20261014-blip | FAIL (never-commit) | FAIL (after-onset 307800) | pre-existing + guard-by-design |
| 20261015-healthy | FAIL (never-commit) | FAIL (never-commit) | pre-existing |
| 20261015-one_metric | FAIL (never-commit) | FAIL (after-onset 351000) | pre-existing + guard-by-design |
| 20261015-group3 | FAIL (never-commit) | FAIL (after-onset 351000) | pre-existing + guard-by-design |
| 20261015-slow_drift | FAIL (never-commit) | FAIL (never-commit) | pre-existing |
| 20261015-blip | FAIL (never-commit) | FAIL (never-commit) | pre-existing |

**Net: 0 regressions. 20/20 P3 failures are pre-existing (all fail at baseline) or the
guard-by-design "rejected a pile window → gate never committed" class.** The P3 guard
converts some baseline "committed-late" failures into "never-committed" failures, but the
test verdict is unchanged (fail→fail) in every case. No param passed at baseline and
failed on P3.

## 4. Guard-statistic self-check (offline, matches the card's D1 probe)

`fusion.calm_span_ratio` on the shipped isotonic config (n=144, τ=0.02 ⇒ m=141, k=36):
- live pile U(0.0013,0.0019)+4 spikes@0.98 → **0.017** (reject; the old `x_(m)−x_(1)`
  reads **97.9**, would adopt the degenerate map) ✓
- wide U(0,0.95) → **27.65** (pass) ✓

## 5. Offline demo (E-acceptance #4) — `/tmp/solo-p3-e/demo.py` → `demo.out`

```
(a) LIVE 288-tick windows: gate + guard + REAL handle_solo_request tick
b4xkt  gate=0 ratio=0.0000 floor=1.0 verdict=RAW | label=raw p_pub==p_raw=1 healthy=0
… (all 10 live pods: gate=0, ratio≈0.0000, verdict=RAW, real tick raw, p_pub==p_raw, no adopt)

(b) SLIDING probe (live 288 + 400 calm ticks): old x_(m) vs NEW guard, first adopting window
b4xkt  59 (~5h)   -        mjnlq  60 (~5h)   -      rzpzm  59 (~5h)   -
hcfj7  59 (~5h)   -        vlsl8  61 (~5h)   -      2vwwd  60 (~5h)   -
7gjdg  59 (~5h)   -        c5bdh  60 (~5h)   -      m7pr8  59 (~5h)   -
qsv2m  59 (~5h)   -
TOTAL: old statistic adopted on 10/10 pods; NEW guard adopted on 0/10 (expect 0/10)

(c) SYNTHETIC wide-spread window ⇒ adopted + reopen replay
synthetic window: gate=1 ratio=27.131 floor=1.0
adopt=1 label=calibrated state=scored fit_count=1 calm_span_ratio=27.131
reopen replay: probability_label=calibrated calibration_state=scored p_published==p_raw=0
```
Matches the card: live windows **rejected** (all raw), sliding probe **0/10** new-guard
adoptions (vs 10/10 for R's `x_(m)`), synthetic **adopted** (`mapper_healthy`,
`calibrated`). Offline ≠ deployed (the live Deployment restart smoke is S's, workcard S-step 4).

## 6. Deviations / card notes
- **None on mechanism.** D1/D2/D3/X1 implemented exactly as decided; thresholds read-only.
- **Slow outcome matches the card's explicit expectation.** The S DECISION and
  "Accepted debt" (workcard S-step 6) both record "scenario fixtures unscorable under the
  guard" as anticipated. My reconciliation proves it is not a P3 regression: all 20 fail
  at baseline; the guard only changes *why* some fail (late-commit → never-commit), never
  turning a passing fixture into a failing one. Recorded, not fixed — per policy, no
  fixture/`synth.py`/YAML/guard edit.
- `fit_count` for a legacy pod counts the existing (inert) mapper as fit #1, per "Open
  points" (absent provenance + persisted mapper ⇒ base 1 ⇒ first adopt lands on 2; fresh
  pod ⇒ 1).
- Slow runner: macOS bash 3.2 lacks `wait -n`; switched to 3-at-a-time waves (≤3 parallel
  honored). No `synth.py`/fixture/YAML/guard edits, per the approved policy.
- Protected laws (p_raw, Simes, strike window, Markov/sojourn/prior, ESS, α_strike/α_fuse,
  0.2/0.8) untouched; label domain `{raw, calibrated}`; `calibrated` label-driven; no new
  gate/counter/timer.

## 7. Residual notes for Main / S (not E's action)
- **0 slow regressions** — verified. No param needs escalating.
- The workcard's "two env-only mlflow failures in (e)" cross-reference is dangling (no
  item (e) exists). Observed: the authoritative combined fast run is **566/0** (cleaner
  than the card's "2 env-only failures" expectation). Running `test_dashboard_api_routes.py`
  *in isolation* reproduces `test_build_bayesian_debug_payload_uses_shared_prediction_
  diagnostics` → `ModuleNotFoundError: mlflow` **identically on the pristine tree**
  (58 passed/1 failed) — env-only, not P3.
- Live Deployment restart smoke (S-step 4) + ≥24 h acceptance (S-step 5) remain S's.

---

# Revision 1 (SOLO-OPS-P3-rev1, 2026-11-06)

RV-P3 rejected the round-1 diff on 1 robustness blocker (findings 1-3); S
accepted all three and approved `solo-ops-P3-rev1.md` as written. This
section records the revision.

## R1.1 The blocker → D1′ (narrowest-k-window "shorth") statistic

RV proved (real ticks, n=144, π=.01, τ=.02, 0.2/0.8, floor 1) that D1's
`x_(k)−x_(1)` reads only the FIRST k-window, so one low point or a broad
bottom quartile certifies a narrow pile:
- **A** `[.0013]+linspace(.0115,.0121,143)` ⇒ D1 ratio **1.034** → adopted,
  calm .0117 → 0.28;
- **B** `linspace(.0013,.01141,36)+linspace(.01142,.01202,108)` ⇒ **1.011** →
  adopted, calm → 0.49.

D1′ (approved): `calm_span_ratio = min_{1≤i≤m−k+1} (x_(i+k−1) − x_(i)) / pi`
on the sorted fit half (`k`, `m` unchanged; 36/141 at n=144). Window i=1 is
the D1 value, so **new ≤ old pointwise** — everything D1 rejected stays
rejected; the guard now also rejects the two ill-conditioned shapes.

## R1.2 Edits (contract + tests + docs only; no new file)

- `fusion.py` `calm_span_ratio` body → `np.min(srt[k-1:m] - srt[:m-k+1]) /
  prior`; docstring rewritten (narrowest window; ≤ first-window; k=1 ⇒ 0).
  No other function touched.
- `driver.py`: module docstring guard wording; adopt-branch **fit_count base
  fix (#2)** — `int(previous_provenance["fit_count"])` only when the dict
  carries the key, else `1 if previous_mapper_persisted else 0` (covers
  provenance-present-without-key AND absent), then +1; not-adopted INFO now
  ends `keeping the healthy calibrated mapper.` when the pod holds a
  verified-healthy mapper (same condition as the publication line) else
  `publishing raw.` (#3); guard-error WARN now `(not adopting; the pod keeps
  its current publication…)`; persist comment + `state.py` docstring now
  state `mapper_healthy` is a **carried-forward flag** and a COMPLETE
  gate/guard-failing window **stamps** the attempt (only incomplete windows
  don't).
- `detector-common.yaml`: comment only → `# narrowest p_raw interval (in
  units of prior_anomaly_rate) over which the fitted map may rise by the
  normal threshold`. Key/floor 1.0 and both YAMLs' values UNCHANGED;
  ConfigMap P1 values (ttl 900 / 11.0 / 13.0) intact.
- Test comments updated (`test_solo_fusion.py` D1′ wording;
  `test_solo_driver.py` narrowest-window wording; `test_solo_exporter.py`
  "n=2 fit half has m=1 ⇒ k=1 ⇒ ratio 0").
- Docs: cutover addendum Guard bullet → D1′ (min-window formula, ≤ first-
  window, the 1.03/1.01 contrast, honest limit); config-schema row → min-
  window statistic. All remaining `x_(k) − x_(1)` mentions are contrast/
  history text only.

## R1.3 New regression tests (4 fusion + 4 driver; all via real ticks where
    applicable)

- `test_solo_fusion.py`: `…_single_low_outlier_pile_is_degenerate` (RV-A ⇒
  ratio < 0.05 while the independent first-window > 1), `…_broad_lower_
  tail_pile_is_degenerate` (RV-B + twice-wider ⇒ < 0.05; first-window ≥ 1
  and interior `x_(k)−x_(⌈k/2⌉)` ≥ 1 on the wider variant — no fixed-rank
  statistic passes this test), `…_n2_is_zero` (n=2 ⇒ k=1 ⇒ 0), `…_
  never_exceeds_first_window` (400 seeded fits: shorth ≤ first-window).
- `test_solo_driver.py` (production n=144: default L_cal=288, n_bins 48,
  `_seed_p_raw`, `end=t0+2*T`, one real `_drive`):
  `test_isotonic_single_low_outlier_pile_stays_raw` (RV-A: asserts
  `_calibration_gate_passes(...) is True` FIRST — the gate alone would
  adopt — then `_calibration_guard_passes(...)[0] is False`; real tick
  `raw`, `p_published==p_raw`, `mapper_healthy` False, no persisted mapper,
  attempt stamped == end) and `…_broad_lower_tail_pile_stays_raw` (RV-B,
  same shape). `test_legacy_provenance_fit_count`: fresh adopt ⇒ 1; legacy
  18-key provenance (P3 keys stripped) + persisted mapper ⇒ **2**; next
  refit ⇒ 3; legacy mapper with provenance None ⇒ 2. `test_
  retained_healthy_failed_refit_logs_keep_not_raw` (caplog): healthy row +
  degenerate due window ⇒ label `calibrated` and the "not adopted" record
  contains `keeping the healthy calibrated mapper` and NOT `publishing
  raw`; a `mapper_healthy=False` row on the same window ⇒ `publishing raw.`;
  the NaN guard-error WARN contains `not adopting` and not `publishing raw`.

## R1.4 Verification (all run)

- **Planner acceptance:** `/tmp/solo-p3-plan2/check_impl.py` → `CHECK_IMPL_OK`
  (impl == independent shorth on 3000 random fits, 0 violations of
  ≤ first-window; RV-A 0.0148 / RV-B 0.0196 / twice-wider 0.0196 /
  pile+4 spikes 0.0119 all reject; wide U(0,.95) seed 0 = 17.303 accept).
  `eval_stats.py` (candidates table: C4 shorth max-reject 0.030 vs
  min-accept 9.265; 0 must-reject rows adopted, vs C0's 10), `fuzz_guard.py`
  (6000 fits; accepted-by-shorth max published rise 0.246 ≤ 0.25; 2187
  C0-only accepts with J≥0.5 that shorth rejects), `sliding.py` (24,060
  windows, 12,420 gate passes, **0 shorth adotions**; max shorth 3.1e-05)
  — all reproduce the card's table; `/tmp/solo-p3-plan2/` kept intact.
- **Fast suite (workcard command):** **574 passed / 0 failed / 20
  deselected** in 104.4 s (round-1 566 + 4 fusion + 4 driver new tests;
  0 env-only mlflow in the combined run). Per-file: fusion 23→27, driver
  48→52; all 20 pre-existing P3 tests (incl. both affine adoptions and the
  raw-scored exporter restore) still pass unchanged.
- **Demo** (`/tmp/solo-p3-e/demo.py` → `demo-rev1.out`), per the card:
  - (a) 12 live windows (10 saved `/tmp/solo-p3-r/` + 2 fresh
    `/tmp/solo-p3-rv/live_{b4xkt,mjnlq}.json`): all gate=0, shorth
    ratio 0.0000 (max over the 12 fit halves **3.0e-07** « 1.0), real tick
    `raw`, `p_pub==p_raw`, `healthy=0` — all rejected;
  - (b) sliding probe: **0/12 shorth adoptions** (contrast: `x_(m)−x_(1)`
    12/12 at ~5 h; D1 `x_(k)−x_(1)` 0/12);
  - (c) wide window (seed 0, U(0,.95)/U(0,.5)): **adopted**,
    `calm_span_ratio=17.303` (D1 was 27.131), `fit_count=1`; fresh store
    over the same SQLite replays `calibrated`/`scored`;
  - (d) RV-A real tick: gate **True**, shorth **0.0148** (D1 first-window
    1.034) ⇒ `raw`; RV-B real tick: gate **True**, shorth **0.0196** (D1
    1.011) ⇒ `raw`.
- **Slow scenarios:** per the card, the guard path is pointwise STRONGER
  (shorth ≤ D1) and round 1 found **0 baseline-pass params**, so no
  baseline-pass→fail can appear and no previously-failing param can now
  pass — the all-20-fail classification of round 1 is unaffected
  (shorth ≤ D1 ⇒ the slow table is unchanged, per the card §7). Confirmed
  on the rev1 tree with the card's spot check `20261014-healthy` plus 5
  spread guard-rejected params (20261012-{healthy,one_metric},
  20261013-group3, 20261014-one_metric, 20261015-group3): all fail with
  the SAME no-commit class — `fixture_unscorable` (gate never committed)
  with `gate=True guard_ok=False` pile rejections present in every log,
  and the new `keeping the healthy calibrated mapper` phrase correctly
  absent (no healthy mapper is ever held in these fixtures). [results:
  see R1.6 delta below]
- **Diff scope:** `git diff --stat` vs `/tmp/solo-p3-e/git-before.txt` = the
  same 16 contract files, now +1599/−62 (rev1 adds no file); P4 /
  `AGENTS.md` / untracked items byte-identical.

## R1.5 Deviations / notes

- None on mechanism: D1′/D2/D3/X1 as approved; floor and key UNCHANGED
  (YAML + ConfigMap 1.0); thresholds still read-only (pick `k`).
- Honest limit (from the card, carried into the gate record): the guarantee
  is "no raw interval narrower than `floor·π` holds k bulk scores"; a
  contrived staircase of <k-point clusters separated by ≥ π still passes
  (published swings ≤ ≈0.2, not the 0→0.8 live sawtooth); a Gaussian calm
  bulk with σ ≈ 2π sits at the floor (59 % pass), U(.005,.075) passes 98 %.
- The `fit_count` base rule now matches RV 2 exactly: legacy row with the
  18-key provenance (no `fit_count`) + persisted mapper ⇒ 2; provenance
  None + mapper ⇒ 2; fresh ⇒ 1; refit ⇒ prev+1 (all four legs tested).

## R1.6 Slow-scenario delta vs round 1 (confirmed, 6 params)

Card §7: the slow table is unaffected (shorth ≤ D1 pointwise). Confirmed on
the rev1 tree with the card's spot check + 5 spread guard-rejected params.
Every one fails with the **same no-commit class** and the **same
`gate=True guard_ok=False` rejection counts as round 1** (the gate logic is
untouched; the guard now reads shorth ≤ D1 but still rejects every pile
window, so the outcome and the gate/guard split are unchanged):

| param | round-1 gate=True/guard=False | rev1 gate=True/guard=False | rev1 result |
|---|---:|---:|---|
| 20261012-healthy | 88 | 88 | FAIL (never-commit) |
| 20261012-one_metric | 119 | 119 | FAIL (never-commit) |
| 20261013-group3 | 43 | 43 | FAIL (never-commit) |
| 20261014-healthy (card spot check) | 152 | 152 | FAIL (never-commit) |
| 20261014-one_metric | 84 | 84 | FAIL (never-commit) |
| 20261015-group3 | 31 | 31 | FAIL (never-commit) |

All 6: `fixture_unscorable` (gate never committed), `publishing raw` log
lines present, and `keeping the healthy calibrated mapper` count 0 (no
healthy mapper is ever held in these fixtures — consistent with #3's new
phrase, which would only fire for a retained healthy mapper). **Delta vs
round 1: none** — the guard got stricter, not looser; 0 baseline-pass→fail
can appear and none did. Logs: `/tmp/solo-p3-e/slow-rev1/`.

## R1.7 Doc-only correction (RV-P3-rev1 accepted_with_findings, 1 should-fix)

The cutover addendum Guard (D1′) bullet overstated the floor ("a `p_raw` move of one `pi` may lift the published value by at most the normal threshold" — RV measured an accepted mapper rising 0.23235 across π where it crosses its UNGUARDED empirical tail); rewritten to the bulk-only statement: the floor bounds the narrowest raw interval over which the fitted map rises by about the normal threshold **within the guarded bulk ranks 1..m**, beyond which (the empirical tail) the map is not covered by the guard and the held-out gate remains the criterion. The config-schema row was already bulk-scoped (no change needed); the `detector-common.yaml` comment gained the matching "within the guarded bulk" qualifier (comment only; no value change — floor stays 1.0, ConfigMap unchanged). `test_solo_mode_config.py` re-run: 97 passed.
