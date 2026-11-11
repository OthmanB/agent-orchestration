# E Completion — SOLO-REFM / B2 (stage 1: pure library)

- Date: 2026-11-09. Lab `pipelineml-model-exploratory-work/reference-model-study/`. Stage 2 (batching, refresh_run, scripts, plots), live batch and finalize are NOT done here.
- **Commit 1: `eebebe9`** `feat(refstudy): add refresh-study pipeline, pod generator, knee finder and sustainable-pods table` (15 files, explicit `git add`, `git diff --cached --check` clean, not pushed).

## 1. Changed files
`config/refresh_study.yaml` (all tunables + `smoke:` block) · `src/refstudy/compute/{refresh_config,podgen,arrivals,pipeline,knee,budget,sustain}.py` · `tests/test_compute_{refresh_config,podgen,arrivals,pipeline,knee,budget,sustain}.py`.

## 2. Commands run
- Preflight: `git status --short` (clean of foreign files), `git log --oneline | grep -c "compute-scaling library"` → `1`; `from refstudy.compute.config import load_shared` → ok; `df -h /` → 41 GiB free (92 %).
- `.venv/bin/python -m pytest tests/test_compute_{refresh_config,podgen,arrivals,pipeline,knee,budget,sustain}.py -rs` → **125 passed, 0 skipped** (6.2 s; 3 extra repeats of the pipeline-heavy set all green, no flakiness). `tests/test_compute_config.py` (B1) still 24 passed.
- `.venv/bin/ruff check config src/refstudy/compute/{…7 modules…} tests/test_compute_{…7…}.py` → `All checks passed!`; `grep -c "print("` on the 7 modules → 0 each.
- `git check-ignore -v results/b2-refresh-cuda.json; echo rc=$?` → `rc=1` (not ignored).

## 3. One-off real-data PodWorld check (step 3; no model)
`PodWorld.from_loader(cfg)` on the packaged flat load:
```
n_src_pods=10 series_len_min=51729   (per-source transformed lengths 51729…51902)
T=11520 unique_windows=170    T=5760 unique_windows=190
T=11520 shape=(4, 11520) dtype=float32 nan=False differ(0,1)=True differ(0,10)=True
T=5760  shape=(4, 5760)  dtype=float32 nan=False differ(0,1)=True differ(0,10)=True
source NaN count total=0     describe={'n_src_pods': 10, 'series_len_min': 51729, 'unique_windows': {'11520': 170, '5760': 190}, 'seed': 20261109}
```
Load 1.8 s. Row means (pod 0, T=11520): cpu increments 16.39 (the cpu counter advances ≈ one cpu-second per ~16.4 s sample), mem 2.5e8, rx 5924, tx 3831.

## 4. Sanity of the simulator scale vs B1
`test_scaled_service_times_match_b1_measured_scale` reads `results/b1-scaling-cuda.json` (V=4, N=11520 median 391.8 ms) and `cfg.fetch.latency_s(11520)=0.2704 s`, `cfg.chain.latency_s=0.010 s`, runs them at 1/100 scale (60 pods): overlap pods/s within [0.6, 1.02]/infer_s (accelerator-bound), sequential > 1.3× slower than overlap; real-time equivalent ≈ 2.5 pods/s ⇒ >150 pods per 300 s tick. Nothing from B1 is a constant in code.

## 5. Deviations / decisions (all inside the card's contract)
1. `run_pass` timelines/backlog are derived post-hoc from per-pod timestamps (exact event lists, thread-safe); `PodTiming` also carries `index, pod, status (done|dropped|cancelled), t_drop`; `PassResult` carries `n_pods`.
2. Reserved variant name `"sequential"` selects the single-thread path (`pipeline.SEQUENTIAL`); `variants.sequential: {}` loads as `VariantCfg("sequential",1,1,block,1,0)`. Scorer threads = `workers`.
3. Deadline: stops admitting AND cancels admitted pods not yet started by a worker; pods already fetched drain (`aborted = deadline fired and cancelled>0`).
4. Smoke merge: mappings merge, lists replace, but `grid.target_pass_wall_s` is replaced wholesale (a plain merge would leave 11520/5760 keys that violate "keys ⊂ context.points"). YAML `reference_budgets` entries carry explicit `informational`/`plot` (no code defaults); overlap carries explicit `max_batch_wait_s: 0.0`. `1.0e6` is not a float for PyYAML → `1000000.0`.
5. `Budget` module holds `Budget/validate_budgets/budgets_from_config`; `refresh_config` stores `refresh_budget_s` + `reference_budgets` (primary=False) and validates through `budget.validate_budgets`. Imports from B1: `refstudy.compute.config.load_shared`, `refstudy.common.config.{load_yaml,require}` only (no B1 hook missing).
6. `unique_windows(T)` = Σ over source pods of ⌈(L_p−T+1)/stride⌉ (distinct non-wrapped shifts at pass 0); `PodWorld.wrapped(k,pass,T)` reports a wrapped shift. Window values are compute-realistic only (irregular timestamps ignored; consecutive samples = consecutive steps).
7. `find_knee` extra method `insufficient_points` (< `knee.min_points` points when extrapolation is needed); constant-series guard treats a fitted slope below 1e-9·max T over the measured span as `unbounded`.
8. The hand-written dry-run tests use only stub stages; no model, no GPU, no network.

## 6. Not done (as of commit 1)
Stage 2 (later done here, see "Stage 2" section below: commit `b375742`), the live batch and the finalize pass.

---

# Stage 2 — runner + batching wrapper + figures (RESUME of the interrupted stage)

- Date: 2026-11-09. **Commit 2: `b375742`** `feat(refstudy): add refresh-study runner, batching wrapper and figures` (10 files, explicit `git add`, `git diff --cached --check` clean, not pushed).
- The aborted run's on-disk files (`batching.py`, `refresh_run.py`, both scripts, the 3 test files, plus the `refresh_study.yaml`/`refresh_config.py`/`test_compute_refresh_config.py` mods) were reviewed against the card, kept, and completed. No stage-1 API was wrapped or changed; no B1 hook was missing.

## S2.1 Files (all under `reference-model-study/`, committed in `b375742`)
`src/refstudy/compute/{batching,refresh_run}.py` (new) · `scripts/{run_refresh,plot_refresh}.py` (new) · `tests/test_compute_{batching,refresh_run,refresh_plots}.py` (new) · `config/refresh_study.yaml` + `src/refstudy/compute/refresh_config.py` + `tests/test_compute_refresh_config.py` (mods: 4 new tunables — `batch.probe_warmup`, `batch.probe_runs`, `batch.warm_wait_s`, `grid.dedupe_frac` — that the runner consumes; they were already on disk from the aborted attempt and are consistent with "every tunable in YAML").

## S2.2 Commands and results
- `.venv/bin/python -m pytest tests/test_compute_{batching,refresh_run,refresh_plots,refresh_config,podgen,arrivals,pipeline,knee,budget,sustain}.py -rs` → **155 passed, 0 failed, 0 skipped** (43 s; rerun after the figure fix, still 155 passed).
- `.venv/bin/ruff check` on the 9 owned Python paths → `All checks passed!` (YAML is not a ruff target; ruff mis-parses it).
- `grep -rn "print(" src/refstudy/compute scripts/run_refresh.py scripts/plot_refresh.py` → empty (rc=1).
- `env -u REFM_LIVE .venv/bin/python scripts/run_refresh.py --config config/refresh_study.yaml --device mps --smoke` → `REFUSED: --device mps is a live batch; set REFM_LIVE=1`, **exit 4** ✓.
- `git diff --check` → clean; `git check-ignore -v results/b2-refresh-cuda.json` → **rc=1** ✓.
- `git show --stat b375742` → exactly the 10 owned files (A1c's concurrent harness/part1 files in the tree were NOT staged).

## S2.3 Flaky test found and fixed (recorded, not loosened)
First suite run: `1 failed, 82 passed`. Failing: `test_compute_refresh_run.py::test_batching_ineffective_skips_batched_variant` (`assert True is False` on `batching_effective`). Root cause: `FlatBF` makes B=1 and B=2 tie on pods/s *by construction* (`cost = 0.01·n`), so the YAML `min_gain: 1.10` is decided by sleep-quantization noise alone at 10–20 ms sleeps. Fix is inside the TEST (no gate loosened): the test now runs with `min_gain=3.0` via `replace(base, batch=replace(base.batch, min_gain=3.0))`, making "no gain" decisive; a comment records why. 3/3 consecutive reruns of the test and 2 full-suite reruns after the fix: green. The runner logic (`choose_b_star`) was unchanged and is still covered by `test_choose_b_star_rule`.

## S2.4 CPU smoke with the real model (step 6; context 240, `--out throwaway/b2-smoke-cpu.json`)
`.venv/bin/python scripts/run_refresh.py --config config/refresh_study.yaml --device cpu --smoke --out throwaway/b2-smoke-cpu.json` → **exit 0, wall ≈ 76 s** (doc `started_utc` 08:44:22 → `finished_utc` 08:46:01 incl. data + model load; 22 measured runs total; `timesfm 3.0.2`, `torch 2.15.0`, python 3.12.15, forecaster `timesfm3.torch.timesfm3_forecaster.TimesFM3Forecaster`).
- All stages present: `probe`, `numerics`, `calibrations` (3), `runs` with stages `{calibrate:6, grid:6, stagger:6, validate:2, pool_sweep:2}`, `validations` (2). `provenance` block present (model_call/prep measured; fetch/chain/arrivals modelled; power disabled), `power.scope = system_whole`, `probe.b_star = 2`, `batching_effective = True` (13.80 vs 6.67 pods/s, B=2 vs B=1 at ctx 240), `probe.pods_per_s_b1 = 6.67`.
- `numerics.single_vs_batched.max_abs_diff = 0.0` (CPU as the card expects; ptp 2.55e8, rel 0.0, rel_per_variate_max 0.0). `packed_vs_separate.max_abs_diff = 5,169,104` (rel 0.0203) — variate packing measurably mixes pods even on CPU torch.
- `calibrations`: sequential `T = -0.007 + 0.176·N`, overlap `0.025 + 0.155·N`, batched_overlap `0.030 + 0.074·N` (s/s/pod). `validations` `sustained_ratio`: sequential 0.990, batched_overlap 1.018 (ρ=1.3, no thermal drop-off at this scale).
- **Resume proof**: immediate rerun of the same command → exit 0, **3.9 s**, 16× "already measured", 0 new runs; `probe`/`numerics` "already in the document: skipped". Doc byte-identical in run count (22) before/after.

## S2.5 Smoke plots (step 7; `--results-dir throwaway --out-dir throwaway`)
exit 0; outputs: `b2-refresh-vs-pods.png` 79,089 B (624×442), `b2-power-vs-pods.png` 54,028 B (624×884, "no power data" panels — power disabled in smoke), `b2-queue-backpressure.png` 114,348 B (624×1326), all PNG magic verified by the test; plus `b2-sustainable.json` and `b2-headline.json`.
- `b2-sustainable.json`: **15 rows = 3 variants × 5 budgets** (incl. informational `ui_green`, `refit_cadence`; `refit_cadence` absent from the figure's budget lines per `plot:false`), all `extrapolated_linear` (smoke measures only N ≤ 23 ≪ knees); `accelerator_bound` for cpu/tick: 4,045 pods @ 13.48 pods/s (b_star=2, `derived_from_probe`); `stability`: ρ* ≈ 0.808/0.805/0.8 (batched/overlap/sequential), `pods_unbounded_at_tick` 3265/1545/1375.
- Headline (verbatim): `On cpu (system_whole), a 0.0416667-day context: 3965 pods (extrapolated) refresh within 300 s (batched_overlap; nan J/pod).` — `nan J/pod` is the expected smoke artifact (power disabled ⇒ `joules_per_pod=None` → `math.nan` in `render_headline`); live docs carry power.

## S2.6 Deviations / decisions (stage 2)
1. `fig_refresh` x-axis: the card requires the SAME x axis per device column; with `sharex="col"` matplotlib's last `set_xlim` wins, so the limit is now computed per column as the max over all rows (measured points, extrapolated continuations, knee markers) and applied after each column is drawn. `fig_power` already accumulated its limit across contexts.
2. Flaky-test fix as in S2.3 (test-only; runner/gate semantics untouched).
3. `sustained_ratio` implemented exactly as the card: `done(W)/(W/2)/μ̂` where `done(W)` = completions in `(W/2, W]` = pipeline's `done_second_half` (verified against `summarize`).
4. Smoke doc's `outputs.refresh` default already targets `throwaway/b2-smoke-{device}.json`; step 6's explicit `--out` matches it. Throwaway outputs are git-ignored (not committed).
5. No change to `choose_b_star` cap logic: `cap = min(variants[batched_overlap].capacity // 2) = 32`; argmax pods/s among ok rows ≤ cap, ties → smaller batch; `batching_effective` iff b_star>1 and gain ≥ `min_gain` over B=1.
6. Vision-model figure inspection was unavailable (404) during this session; figures are verified by size/dimensions/magic + the `test_compute_refresh_plots` assertions, not by a human eye.

## S2.7 Open items for the live worker
Nothing code-side. See "LIVE BATCH — what the live worker needs" below (also in the workcard M0–M2; commands verified against the committed code).

## LIVE BATCH — what the live worker needs
**Files on the host:** committed `reference-model-study/{src,scripts,config,tests,data}` (lab `main` at/after `b375742`); weights under `artifacts/` (non-commercial, never synced as code); packaged flat-load data + manifest. Result lands in `results/b2-refresh-{cuda,mps,mlx,cpu}.json` (git-tracked, rsync back to `$LAB/reference-model-study/results/`).

**Commands (one process per device, order cuda → mps → mlx → cpu):**
- M0 CUDA host sync (~5 min): rsync code/config/`data/raw/flat-load`/manifest to `rtx-4000-test:refm-lab/reference-model-study/` (no `--delete`), verify 10 pods load and GPU idle.
- M1 CUDA (~2 h): `ssh rtx-4000-test 'cd ~/refm-lab/reference-model-study && REFM_LIVE=1 PYTHONUNBUFFERED=1 nohup timeout 9000 .venv/bin/python scripts/run_refresh.py --config config/refresh_study.yaml --device cuda > throwaway/b2-live-cuda.log 2>&1 &'`
- M2 Mac, per device mps → mlx → cpu (~2 h each): `cd $LAB/reference-model-study && REFM_LIVE=1 PYTHONUNBUFFERED=1 timeout 9000 .venv/bin/python scripts/run_refresh.py --config config/refresh_study.yaml --device <d> 2>&1 | tee throwaway/b2-live-<d>.log`. Mac preconditions: `ExternalConnected=Yes` (AC), no other CPU job, load1 < 2, no `CPU_Speed_Limit` below 100.
- **Expected wall ≈ 2 h per device** (probe ~3 min + numerics ~1 min + grid: 2 contexts × (calibration 2 passes + 5/3 targets) × 3 variants ≈ 65 min + stagger 4 ρ × 3 variants ≈ 20 min + validate 2 × (300+≤150 s) ≈ 15 min + pool_sweep 7 × ~45 s ≈ 5 min + idle blocks ≈ 8 min). Mac total ≈ 6 h, CUDA ≈ 2 h.
- **Resumable**: any crash/interruption → rerun the exact same command; runs are skipped by key, probe/numerics by doc presence. Slice with `--stage grid,validate`, `--context 11520`, `--variant batched_overlap` if needed.
- **Exit codes**: 0 ok; 1 a run raised or prerequisite missing (record verbatim, rerun); 2 hygiene/AC abort before first measurement (fix environment, rerun — nothing was measured); 3 AC lost mid-run (plug in, rerun — file kept); 4 refusal (operator error: `REFM_LIVE=1` missing).
- Host stress-ng load ≈ 17 on CUDA is recorded, never enforced; the model inference runs on 1 torch thread and the pipeline sleeps for the modelled fetch, **but the host CPU is NOT "otherwise idle"** — the permanent tester-workload stress keeps the host CPU saturated, and the pipeline's prep/arrival-gate/dispatch/wakeup threads all run on that saturated host CPU (RV-B F3). These are shared-host end-to-end numbers, not isolated GPU ceilings.

---

# Fix A — apply RV-B findings F1 (blocker) and F4 (should-fix)

- Date: 2026-11-09. Executor RefmEB2fixA, slice B2-fixA. F2/F3/F5/F6 are out of scope for this slice.

## F1 — calibration rounding destroyed the batched study (blocker)
- Root cause (`src/refstudy/compute/refresh_run.py` `Runner.calibrate`): the YAML `grid.calibration_pods = [10, 30]` was rounded up to the variant batch. With the real probe `B* = 32`, both `round_up_to(10,32)` and `round_up_to(30,32)` are `32`, so both calibration passes used the same run key; the second resumed the first, leaving < 2 usable points, `calibrate` returned `None`, the grid was skipped, and `stage_stagger`/`stage_validate` then raised `ValueError` on the nonexistent calibration.
- Fix: choose **strictly increasing** rounded calibration counts, advancing a collapsed count by one batch (`[10,30]`, `B=32` → `[32,64]`). `B*` (the measured batch) and the fit semantics (`T = a + s*N`) are unchanged; no threshold, gate, or `reference/` file was touched.
- Regression (`tests/test_compute_refresh_run.py` `test_collapsed_calibration_counts_advance_one_batch`): uses the **actual** YAML counts `[10,30]` with a probe that yields `B*=32` (call-overhead stub, `probe_warmup=0`,`probe_runs=1`), runs `probe,grid,stagger,validate` for `batched_overlap` at context 240. It asserts: two **distinct** calibration runs (`n_pods = [32,64]`, two distinct resume keys), a calibration entry with `batch=32` and points `[32,64]`, and that the dependent `stage_stagger`/`stage_validate` lookups succeeded (stagger+validate runs and a `validations` entry exist, no `ValueError`). Stub/fake-model style (`StubBF` + `Hooks` + `PodWorld`), matching the module's existing tests.

## F4 — a failed required hygiene probe could be recorded as clean (should-fix)
- Root cause (`src/refstudy/compute/hygiene.py`): a failed GPU-process command set `gpu_other_procs=None` and `check` ignored `None` even when the YAML cap was `0`; likewise a missing/unparseable `load`/`top` observation bypassed its rule. So `polluted=false` could hold despite a failed REQUIRED probe.
- Fix: `snapshot` now records a **missing observation** as `None` for the probes that back an enabled check — `load` (uptime failed or unparseable), `top` (top command failed, or non-empty output with no parseable rows; a successful empty table stays `[]`), and `gpu_other_procs` (nvidia-smi command failed) — and `check` reports a **violation naming the probe** for any enabled check whose required observation is missing. Distinguishes unknown/failed (violation) from disabled (`cap`/`enforce_cpu` off, no violation). **Live thresholds are untouched**; smoke relaxations remain explicit (the `smoke:` block already sets `enforce_cpu:false`/`require_ac:false`). `ac` (already fail-closed via `require_ac`), `therm_limit` (a throttle detector: absent `CPU_Speed_Limit` = no active limit = clean), and the `gpu cap is null` (disabled) cases are unchanged.
- Tests (`tests/test_compute_hygiene.py`, probes stubbed as the existing tests do):
  - `test_check_fail_closed_missing_gpu_probe`: capped profile + `gpu_other_procs=None` → violation naming the gpu probe; uncapped profile → clean.
  - `test_check_fail_closed_missing_load_and_top`: `load=None` / `top=None` under `enforce_cpu` → violations naming the load/top probes; the disabled cuda host stays clean without them.
  - `test_snapshot_probe_failures_are_observations`: monkeypatched probe argv — a failing GPU command → `gpu_other_procs=None` + violation; a successful **empty** top table → `top=[]` (clean, not a failure); an **unparseable** top table → `top=None` + violation; an **unparseable** uptime line → `load=None` + violation.

## Checks
- `pytest tests/test_compute_*.py` → **238 passed, 0 skipped**.
- `ruff check` on `src/refstudy/compute/{refresh_run,hygiene}.py` and `tests/test_compute_{refresh_run,hygiene}.py` → All checks passed.
- `git diff --check` → clean.

## Not changed (open, out of scope)
Findings F2 (regular-grid input), F3 (live-interpretation text), F5 (power presentation/resolution), F6 (power attribution / evidence mismatches) remain open for their owning slices.

---

# Fix B — apply RV-B finding F2 (blocker): regular-grid timestamp-aligned PodWorld input per operator D8

- Date: 2026-11-09. Executor RefmEB2fixB, slice B2-fixB. F3/F5/F6 out of scope.

## F2 — real-data PodWorld bypassed binding regular-grid decision D8 (blocker)
- Root cause (`src/refstudy/compute/podgen.py`, `config/refresh_study.yaml`): the B2 `PodWorld` loader discarded timestamps, differentiated counters by sample index, truncated all metric arrays to the shortest length, and stacked positionally ("no resampling" in the docstring). D8 (operator, 2026-11-09) requires TimesFM-3 input on a REGULAR GRID with the cadence and missing-sample policy explicit in the consuming YAML, and names B2 `PodWorld` specifically. It also kept resampling/alignment out of the measured prep path, and the index-differenced counter rows were not time-aligned with the gauge rows.
- Fix:
  - **Reuse the committed resampler** — `PodWorld` now imports `to_grid` / `pod_origin` from `refstudy.refcompare.grid` (C1 slice 1a, commit `5d657f8`); nothing copied, no refcompare file modified. Each source pod's raw `(ts, value)` series is resampled onto the regular grid `g_j = origin + cadence*j`: gauge rows linearly interpolated at `g_j`, counter rows as per-step increments of the interpolated cumulative (the increment ENDING at `g_j`), so **all 4 continuous metrics share one time axis**. Grid points outside the raw range, across raw gaps `> max_gap_seconds`, or across a counter reset are **NaN and passed through** for the model to fill.
  - **YAML-first, with provenance**: new `grid_input:` block in `config/refresh_study.yaml` (`cadence_seconds: 15.0`, `tick_seconds: 300.0`, `missing.policy: nan`, `missing.max_gap_seconds: 35.0`) with a provenance comment naming `refcompare.yaml` / `reference.yaml` counterparts; missing key → `ValueError` via `require`. A test (`test_yaml_grid_input_agrees_with_refcompare`) asserts the two YAMLs agree on **cadence and max_gap** (and policy); `refresh_config` additionally rejects a non-`nan` policy and a cadence that does not divide the tick.
  - **Provenance in the run docs**: `PodWorld.describe()` now carries a `grid` sub-block (cadence, tick, origin rule, missing policy, max gap, resampler provenance) inside the `podworld` block of every result document.
  - **Windows built from the grid**: `window(k, pass, T)` slices the pod's `(V, L)` grid at a start in GRID steps (`(c*shift_stride + pass*pass_shift) mod (L - T + 1)`), same lazy per-call / distinct-per-virtual-pod design, perturbation unchanged (NaN-safe: the affine scale uses the mean of FINITE values only). `start_index` / `unique_windows` / `describe` use raw endpoints only (never resample), so the document is buildable before the measured stages.
  - **Measured vs one-time cost (stated)**: the full-series grid per source pod is a **lab-side one-time step** — computed lazily inside the first `window()` call that touches the pod, i.e. INSIDE the measured preparation path (never precomputed outside it), cached thereafter; the **per-window slice + perturbation always runs measured** inside `window()`. Verified by test with a resampler call counter: init=0 calls, first `window`=4 (one pod, 4 metrics), repeat=4 (cached), second pod=8.
- Tests (`tests/test_compute_podgen.py`, rewritten): regular-grid counter row == hand-computed increments (`v[j]-v[j-1]`, first NaN), gauge row == raw values on an exact grid; counter+gauge rows equal length, one window start per pod; jittered (10–35 s spacing) and missing-sample (6 raw samples deleted mid-series; gap ≫ 35 s) resampling with a hand-computed 4-point case (exact NaN positions, interpolated value `20 + (5/15)·10`); window-local NaN alignment; `nan_counts()` (one first-increment NaN per counter row + gap NaNs) and `describe` provenance vs YAML; two virtual pods differ; determinism; all-below-unique-windows distinct; wrap + perturbation bounds; context-too-long / bad-args / missing-series / non-increasing-ts rejections; `grid_input` missing-key (4 keys named) and bad-value regressions.
- CPU smoke on the packaged real data (`PodWorld.from_loader(cfg)`): `n_src_pods=10`, per-pod grid length 56578–56579 (block-aligned origin), `T=11520`: shape `(4, 11520)`, dtype float32, NaN fraction 0.00041 (only the leading counter increments), `unique_windows=190`; `T=5760`: shape `(4, 5760)`, NaN fraction 0.00082, `unique_windows=210`; pods 0/1 differ. `nan_counts = {cpu: 56, mem: 46, rx_bytes: 59, tx_bytes: 59}` (mem NaNs = post-last-sample tail only — no gap exceeded 35 s). Load + construct 1.9 s.
- Checks: `pytest tests/test_compute_*.py -q` → **253 passed, 0 skipped**; `ruff check` on `src/refstudy/compute/{podgen,refresh_config}.py` + `tests/test_compute_podgen.py` → All checks passed; `git diff --check` → clean.
- Consequence for the old measurements: `results/b2-refresh-cuda.json` (and friends) remain **old, fixed-shape compute measurements** — their `podworld.series_len_min` (51729) was the positional truncated length, now the grid length (56578). S decides whether corrected prep materially requires remeasurement; old data is not relabelled.

---

# Fix C — apply RV-B findings F5 (code: power presentation + resolution rule) and F3/F6 (evidence text)

- Date: 2026-11-10. Executor RefmEB2fixC, slice B2-fixC. F1/F2 already fixed in Fix A/B.

## F5 — power presentation and resolution rule (code)

### F5-a — shared x-limits across the refresh and power figures
- Root cause (`scripts/plot_refresh.py`): `fig_refresh` and `fig_power` each accumulated their own per-column `row_xmax`/`xmax`, so the two figures' pod-count axes were not on the same scale and a side-by-side comparison was misleading.
- Fix: a new `pods_xlimits(docs, table, cfg) -> dict[str, float]` computes the **per-device union** of the measured max `N`, the extrapolated-continuation `x_end = (ymax − fit.a_s)/fit.s_s_per_pod` for `extrapolated_linear` knee rows, and the knee-marker pod counts; `xmax = max(..., 10.0)` is shared. `fig_refresh(docs, table, cfg, xlims)` and `fig_power(docs, cfg, xlims)` now take the shared dict and both call `_style_pods_axis(ax, xlims[dev])` (xlim = `(0.8, max(xmax*1.5, 10.0))`). `main()` computes `xlims = pods_xlimits(docs, table, cfg)` once after the `--table-only` return; the old per-column accumulation was removed from both figures.
- Test (`tests/test_compute_refresh_plots.py` `test_refresh_and_power_share_pods_x_limits`): the shared limit exceeds the 240 measured max; the refresh and power figures report **identical** `get_xlim()` on the device axes; the power axis is wider than its own points.

### F5-b — unresolved power points drawn hollow in all three power panels
- Root cause (`scripts/plot_refresh.py` `fig_power`): only the W panel marked unresolved points hollow; the energy and J/pod panels drew them solid, so an unresolvable run looked like a real measurement.
- Fix: unresolved points are hollow (`mfc="none"`) in **all three panels** (W axis, energy axis, J/pod twin). The J/pod markers were changed from `marker="x"` to a hollow-capable `marker="o"`; the J/pod ylabel is now `"J per pod (dotted)"`.
- Test (`tests/test_compute_refresh_plots.py` `test_unresolved_power_points_hollow_in_all_panels`): when a run is unresolved, **every** circular marker in the figure has `get_markerfacecolor() == "none"`; when one run is resolved, the mix is hollow + solid.

### F5-c — scope-specific power-resolution rule, YAML-first
- Root cause (`src/refstudy/compute/power.py`): `energy_record` resolved a run on the single amplitude rule (`excess > min_resolvable_w · resolution_k`) alone; there was no minimum-window or minimum-sample guard, and the rule could not be scoped. `calibrate:sequential:ctx5760:n10` (a 3.8 s pass, 15 samples on a coarse 250 ms sampler) was the first case it let through.
- Fix:
  - `src/refstudy/compute/config.py` `PowerSpec` gains two **defaulted** fields `min_window_s_by_scope: dict[str, float]` and `min_samples_by_scope: dict[str, int]` (empty by default). B1's `_parse_power`/`load_compute_config`/`load_shared` are **unchanged**, so B1 `test_compute_config.py`, `test_compute_scaling.py` (5.0 s/21 samples, `resolved=True`) and B1's smoke path stay green — empty dicts mean `.get(scope, 0.0/1)` imposes no floor.
  - `src/refstudy/compute/power.py` `energy_record` now resolves only when **all three** clauses hold: `excess > threshold` **and** `window >= cfg.min_window_s_by_scope.get(scope, 0.0)` **and** `stats["n"] >= cfg.min_samples_by_scope.get(scope, 1)`. Docstring updated to the 3-clause rule.
  - `src/refstudy/compute/refresh_config.py` adds `_overlay_power_resolution(shared, cfg)`: requires a `power.resolution` dict and, per present scope, a `min_window_s` (float ≥ 0) and `min_samples` (int ≥ 1); builds a new `PowerSpec` via `dataclasses.replace` and returns `replace(shared, power=new_power)`. `load_refresh_config` now overlays this onto the shared `PowerSpec`. Because `cfg` is post-smoke-merge, the smoke relaxation is picked up automatically — **YAML-first, no code-level smoke branch**.
  - `config/refresh_study.yaml` `power:` block:
    ```yaml
    power:
      enabled: true
      resolution:
        system_whole: {min_window_s: 30.0, min_samples: 30}
    ```
    and the smoke block relaxes it to `system_whole: {min_window_s: 0.0, min_samples: 1}`. `gpu_board` is **deliberately absent** → no floor → the committed CUDA results (scope `gpu_board`) are unaffected. `config/compute_scaling.yaml` (the shared B1 file) was **not** changed.
  - `src/refstudy/compute/sustain.py` adds `_power_resolved(runs)` → `None` if no run's power dict carries a `resolved` key (power disabled), else `all(flags)`; the row dict now exposes `power_resolved` between `mean_w` and `power_scope`.
- Tests:
  - `tests/test_compute_power.py`: `test_energy_record_short_mac_window_is_unresolved` (a 10 s `system_whole` window is unresolved despite passing the amplitude rule under a 30 s/30 floor; a 40 s adequate window resolves; the same 10 s window under `gpu_board` with empty dicts resolves); `test_energy_record_sample_count_rule` (a 40 s window with 6 sparse samples is unresolved under `min_samples: 30`; 41 dense samples resolves).
  - `tests/test_compute_refresh_plots.py` `test_sustainable_table_exposes_power_resolved`: the `power_resolved` row is `False` when any power run is unresolved, `True` when all resolve, `None` when no run carries a power flag.
  - `tests/test_compute_refresh_config.py` `test_loads_real_yaml` asserts `cfg.shared.power.min_window_s_by_scope == {"system_whole": 30.0}` / `min_samples_by_scope == {"system_whole": 30}`; new `test_smoke_merge_relaxes_power_resolution` (smoke → 0.0/1, live → 30.0/30); the `_MISSING` list gained `power.resolution.system_whole.min_window_s` and `power.resolution.system_whole.min_samples` so a missing required key still names itself.

## F3 / F6 — evidence-text corrections (no lab code)

All in `agent-orchestration/evidence/` (uncommitted here; orchestration commits wait for the operator):
- `E-B2-live.md`: (F3) host load `12.5–15.3` → **12.25–20.02** with a new shared-host blockquote — the host CPU is **not** otherwise idle, and these are shared-host end-to-end numbers, not isolated GPU ceilings; the `1.66–1.93×` overlap gain is corrected to **1.66–1.75×** from the knee table, with 1.93× attributed to the accelerator-only probe; the 89 % pool_sweep drop is qualified as a **simultaneous-burst admission experiment**, not a production steady-state loss rate; the stagger saturation onset is corrected to **ρ=1.1** (12.12 % seq / 13.10 % overlap, both > 5 %, first crossing 1.1 not 1.4, `rho* ≈ 0.969`); the sustained-run `0.971` is qualified as **sequential@11520-only** and does **not** prove no thermal drop-off nor validate all knees. (F6) the power section intro is reworded to "**Mean total board power** … board mean `mean_w` (total), not the excess above idle." A PRE-D8-fix banner marks the whole file as a superseded old fixed-shape measurement.
- `E-A2-live.md` (F6): the MLX `rss after load` is corrected `2593.1 MB` → **2590.75 MB** (matches committed `results/a2-smoke-mlx.json` `rss_after_load_mb`); the Power section gains a caveat that the whole-process smoke windows include model load and the second CPU forecaster for the parity block, so the +2004/+4083 mW differences are **not** isolated MPS/MLX inference energy and not a controlled backend comparison.
- `E-B1-live.md` (F6): the parity line is corrected `threads=6` → **threads=1** (`run_scaling.py:109–113` keeps CUDA's 1-thread budget for the CPU reference forecaster); the "~50 W" energy-loop figure is re-labelled a **mean**, not a measured peak; the resident-model ~7 W idle gap is kept as a measured observation but its attribution to the resident CUDA context alone is marked an **[INFERENCE]** (DVFS/thermal settling not separated).
- `E-B2.md:96` (F3) and `omp-workcards/refm-B2.md:59` (F3): the "host CPU is otherwise idle" clause is dropped and replaced with the shared-host-CPU caveat.

## Checks
- `pytest tests/test_compute_*.py -q` → **261 passed, 0 skipped**.
- `ruff check` on `scripts/plot_refresh.py`, `src/refstudy/compute/{power,config,refresh_config,sustain}.py`, and `tests/test_compute_{refresh_plots,power,refresh_config}.py` → All checks passed.
- `git diff --check` → clean.

## Not changed (open)
F1 and F2 were already fixed in Fix A and Fix B respectively; nothing is left open for B2. The F2 remeasurement decision (whether the corrected regular-grid prep materially changes the committed CUDA numbers) remains S's call — no old data was relabelled.

## Commit
- `f8c618d` — `fix(refstudy): shared plot limits, unresolved-power markers and power resolution rule (B2 fix C)` (lab repo; the evidence files above are uncommitted).

