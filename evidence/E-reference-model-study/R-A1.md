# R-A1 — faithful reference, noise law, scoring chain, harness feasibility (Part 1 research)

**Researcher:** R-A1. **Date:** 2026-11-09.
**Sources (read-only):** `pipelineml-anomaly-detector` @ `5bcc7f9128d55e38d3c09838b3af0699edc4973b` (working tree has 3 unrelated modified paths; I changed nothing), `pipelineml-shared` @ `942b8807f63e614fe3542ed2ba1268046291bfeb`. Deployed config `deploy/k8s/solo-card6/configmap.yaml`; repo default `analyser/config/detector-common.yaml`; scenario fixture `analyser/config/solo-scenarios.yaml` + `analyser/solo_mode/scenarios/synth.py`.
**Legend:** OBSERVED = command output in this session; SOURCE = file:line; INFERENCE = my reading, not executed.

## 1. Context verification

| Check | Result | Evidence |
|---|---|---|
| Campaign context read | yes | `evidence/E-reference-model-study/CAMPAIGN-CONTEXT.md` |
| Production source present, line counts | baseline 133, noise 756, fusion 644, driver 2298, scan 2752, synth 1870 | `wc -l` OBSERVED |
| Lab runtime available | `/tmp/solo-p3-venv/bin/python` = repo venv, numpy 2.3.4 / scipy 1.15.7 / pyyaml, **no sklearn** | OBSERVED |
| Cluster reachable in this session | **no** — the dashboard forward `127.0.0.1:8086` that served the live facts below was open earlier in this session and is now refused (`curl` exit 7) | OBSERVED |
| Live data used below | `/api/dashboard/pods` rows and `p3_ticks.jsonl` (6776 rows) fetched earlier this session from that forward | OBSERVED (payloads no longer on disk) |

## 2. Q1 — the faithful reference (STL-lite, continuous metrics)

### 2.1 Geometry

- **Blocks, not samples.** Everything is in 5-min blocks (`T = 300 s`, `dt = 30 min`, `Dt = 2 d`). SOURCE `driver.py:290-320` (`_depth_ticks`, `_gate_window_ticks`, `_warmup_state`), config `window: {Dt: 2d, dt: 30m, sampling_cadence: 16s}` (`deploy/k8s/solo-card6/configmap.yaml:79-84`; repo default `15s` at `analyser/config/detector-common.yaml:249`).
- **Fit window length = `Dt/dt − 1` = 570 blocks**, not 576: the window is `[b − Dt, b − dt)` for refit block `b`. SOURCE `scan.py:1098` `build_one` (`fit_end = b − dt`), live payload `fit_window = (1794021800, 1794191000)` count = 570.
- **Trend term = arithmetic mean of the raw block values in the window** (`T = raw_mean`). It is *not* an STL trend/loess. SOURCE `baseline.py:69-113` `stl_lite_fit`, `noise.py:456` `StlLiteRunningState` docstring.
- **48 centred phase-bin means**: `phase_of(ts) = floor(((ts − anchor) % 86400) / (86400/48))` → 30-min bins, anchor conventionally 0/midnight; `S(j) = mean(bin j) − T` (so `Σ_bins S(j)·n_j ≈ 0`, no double counting of the mean); **empty bin → `S = 0`** → `forecast = T` (trend-only fallback). SOURCE `baseline.py:36-66` (`phase_of`), `baseline.py:115-127` (`stl_lite_forecast`, `seasonal_by_phase.get(bin_, 0.0)`).
- **Forecast at step t:** `M_k(t) = T + S(phase(t))`. No leakage guard is enforced in `stl_lite_forecast` itself; the guard is the *window* (the fit window never contains the scored block).
- **Warm-up / minimum gates:** `noise.min_fit_blocks: 48` (a fit needs ≥48 blocks); a metric is fusable only when its strike ring is full `window_fill ≥ min_strikes_to_score = 3` (`fusion.py:89` `metric_is_eligible`); `undersampling.min_effective_samples: 36` and `validity.min_point_fraction: 0.95` gate data-quality, not the reference. SOURCE config + `fusion.py:89`.
- **ESS:** `noise.bartlett_ess(block_values, max_lag=144)` (`noise.py:229`, `config noise.bartlett_max_lag: 144`) is used by the drift/validity diagnostics, **not** on the per-tick scoring path. **[SUPERSEDED by A1c/E-A1c (RV-A1 F2, 2026-11-09):]** the Bartlett ESS **is** on the scoring path — production `scan.py:1320-1332` rejects a refit cycle whose fit-window block values have ESS < `min_effective_samples` (36), so that cycle serves no model and the metric is uncomputable/unscored until a later cycle passes; on the S1 diurnal scenario the faithful chain therefore scores only 732/1872 ticks (D14). This line's "not on the per-tick scoring path" reading (that the floor only gates data-quality diagnostics, not reference availability) is wrong for the reference-serving decision.

### 2.2 The 30-minute tail (what is excluded, and where)

- The **fit** excludes the 30 min immediately preceding the refit block: `fit_end = refit_block − dt` (`scan.py:1098`+). SOURCE.
- The **scored** tick then uses the *frozen* model for the 6 ticks of the refit cycle (`T/dt = 6`), so relative to the scored block the tail is **30 min at the first tick after a refit and 25 min at the sixth** — the vision's "exactly 30 min" is true only at the refit tick. INFERENCE from `scan.run_build_cycle` + live payload (`fit_end = block_start − 1800` for a tick 300 s into the cycle).
- The residual **CDPF population** is the model's persisted residual record (570 entries), whose newest entry is at `fit_end`, i.e. the scored block's own residual is *never* in the population (no self-inclusion). OBSERVED on the live payload: `n_residuals = 570`, `residuals.first = fit_start`, `residuals.last = fit_end`, and recomputing `mid_rank_cdf`+`two_sided_surprise` over that 570-vector reproduced the live per-metric p exactly.

### 2.3 Compute-budget coarsening — fit only

- Config: `undersampling.boxcar {mode: jumping, over: duration, value: 5m}`, `auto {enabled: true, max_boxcar_multiple: 4, max_steps: 5}`, `min_effective_samples: 36` (`configmap.yaml:115-124`).
- `scan.py:1732-1765` chooses a `fit_multiple` (1.0 → up to `max_boxcar_multiple`) when the refit threatens the tick budget and records it as **provenance only**; `build_one` computes the residual record and the CDF on **full (un-coarsened) blocks** (`scan.py:1288`, `1837`).
- **CONSEQUENCE (INFERENCE, code-verified):** the coarsening does not touch the forecast formula, the residual population or p; it can only shrink the *number of blocks* fed to a fit attempt. For the lab this means a reimplementation may ignore `fit_multiple` entirely for accuracy purposes — but must keep the *window length in blocks*.

### 2.4 Alternative methods (identify only)

`baseline.stl_lite_fit(..., method=...)` dispatches `"ma"` → `ma_only_fit` (`baseline.py:130`: `S ≡ 0`, `T` = window mean) and `"sarima"` → `sarima_fit`/`sarima_forecast` (statsmodels, subprocess with `max_fit_seconds: 30`, `order (1,0,1)`, `seasonal_order (0,0,0,0)`). SOURCE `baseline.py:69-238`, config `baseline.continuous.sarima`.

### 2.5 Box-car law and units

- **Gauge (memory):** block value = **mean of the samples inside the block**; **counter (cpu, rx/tx bytes):** block value = **mean of the *increments* over the block**, where an increment is attributed to the interval that *ends* at its sample timestamp `t_end` (right-closed). SOURCE `scan.py:459-490` `tick_aligned_blocks` docstring.
- **"Block not aligned" rule:** a counter point is only attributed if the sample raster is aligned to the tick grid within `validity.counter_max_gap: 35s`; otherwise the block is dropped (the metric becomes uncomputable for that tick, never padded). OBSERVED in the fixture log: `"solo pod degraded: 1/11 metrics uncomputable"`, and the campaign figure caption "gap: block not aligned → no tick, not scored, not padded" (generate.py:457 annotation).
- **Samples per block:** 300/15 = 20 in the repo config; **300/16 = 18.75 in the deployed ConfigMap** — so the deployed cluster cannot average "20 samples" and the block mean is over the 18–19 samples that fall in the interval. OBSERVED (config values) + INFERENCE (arithmetic).
- **Units to fix in the lab** (all observed from the live/report chain): CPU = `container_cpu_usage_seconds_total`, a counter in **CPU·seconds per raw sample** — the block value is therefore a mean of per-interval CPU-seconds, i.e. ~cores × interval; the dashboard *displays* `s-rate/10` (docs §9 note, `markdown/2026-11-06-solo-dashboard-operations-report.md:505-560`). Memory = `container_memory_working_set_bytes`, gauge, **MiB** after ÷2²⁰. Network = `container_network_*_bytes_total`, counter, **bytes per raw sample** (⇒ MiB/s after ÷2²⁰ ÷ cadence). Live flat load OBSERVED: cpu ~16.4 (displayed units), memory ~244 MiB, rx ~5.7–6.2 KB/s.
- **Lab recommendation:** store blocks in *native counter units* and state a single conversion (`value_display = block / cadence` for counters, `/2^20` for memory) in the harness config, so that reference and residual are computed on one consistent scale.

## 3. Q2 — noise law and scoring chain, end to end

1. **Residual:** `r_t = observed(block at tick) − M(block_start)` where `M` comes from the model **frozen at the last refit** (`T + S(phase(block_start))`). SOURCE `driver.py:1105` `_score_continuous`.
2. **Empirical mid-rank CDF** over the persisted residual window (570 entries): `F(v) = (min(c, N−1) + 0.5)/N`, `c = #{r < v}` with the *last* rank used for ties (`right − 1`). SOURCE `noise.py:692-739` `mid_rank_cdf`. Ties therefore take the *upper* mid-rank; the current tick's residual is excluded (§2.2).
3. **Two-sided surprise:** `p = F(−|r|) + 1 − F(|r|)`; floor `1/N` (INFERENCE confirmed numerically: for N=852 a maximal residual gives exactly 0.001174 = 1/N). SOURCE `noise.py:740-756` `two_sided_surprise`.
4. **Strike:** one strike iff `p < alpha_strike` (0.05), counted over the last `window_ticks = 4` ticks with `semantics: window`; the metric is **eligible** only if the ring is full (`window_fill ≥ 3`). SOURCE `fusion.py:44-111` (`strike_count`, `beta_binomial_tail`, `metric_is_eligible`).
5. **Simes fusion:** `tilde_p = min_k (K·p_(k)/k)` over the *eligible* metrics (K = eligible count); `alpha_fuse = 0.05`. SOURCE `fusion.py:112-129` `simes_p`.
6. **S_pod / evidence:** `S_pod = Σ_k w_k·(−ln tilde_p_k)` (`metric_weights.default = 1.0`), `ell = ell_of(S_pod, k_eff, gamma)` with `k_eff` = effective independent evidence from the metric correlation matrix and `h1_scale_gamma: 2.0`; signed evidence with `evidence_gain {rising 3.0, falling 1.0}`. SOURCE `fusion.py:130-287`.
7. **Markov posterior:** 2 states (`MUTURITY_STATE_COLD/WARM`), transition matrix from `prior_anomaly_rate = 0.01` and `mean_anomaly_sojourn_ticks = 6` (`fusion.markov_matrix`), `update_posterior` gives `p_posterior`. SOURCE `fusion.py:267-307`, `shared/bayesian/common.py`. Quiet-state floor: with all `tilde_p = 1` the posterior is **0.0012881** — which is exactly the value the 10 live pods publish (OBSERVED).
8. **Calibration mapper:** isotonic fit on the healthy window (`calibration.mapper: isotonic`, `n_bins: 48`, `fit_half`=L_cal window), gate = held-out exceedance (`calibration.gate {window: 1d, max_fare_multiple: 2.0, warmup_state: calibrating}`), **degeneracy guard** `min_calm_span_ratio: 1.0` (`fusion.py:333` `calm_span_ratio`); if not adopted → `p_published = p_raw`, `probability_label = "raw"`. SOURCE `driver.py:1970-2075` (`_calibration_guard_passes`, `_fit_mapper`, `_apply_mapper`), `fusion.py:464-644`.
9. **Rare-count metrics:** negative-binomial (`baseline.rare_count_fit/rare_count_surprise`, `baseline.py:239-330`), scored by `driver._score_rare_count` (`driver.py:1197`); they enter Simes exactly like continuous metrics.
10. **Do the three continuous signals alone yield a valid published probability?** YES. `simes_p` normalises by the *eligible* count K, so a 3-continuous pod fuses with K=3 (and `k_eff ≈ 1`, as in the campaign's 3-signal description); count metrics are not a prerequisite. SOURCE + INFERENCE (`fusion.py:112-170`, `metric_is_eligible` only checks ring fill).

### 3.1 Config values actually used (deployed ConfigMap)

| key | value | where it acts |
|---|---|---|
| `window.Dt` / `window.dt` | `2d` / `30m` | fit-window length 570 blocks; refit cadence |
| `window.sampling_cadence` | `16s` (repo default `15s`) | samples per block |
| `window.min_cycles_per_period` | `2` | scenario-fixture validation only |
| `baseline.continuous.default_method` | `stl_lite` | reference method |
| `baseline.continuous.seasonal.period` / `phase_bins_per_period` / `min_points_per_phase` | `daily` / `48` / `4` | phase model |
| `noise.min_fit_blocks` | `48` | minimum blocks per fit |
| `noise.bartlett_max_lag` | `144` | ESS (diagnostics) |
| `undersampling.boxcar` / `auto.max_boxcar_multiple` | `5m` / `4` | fit-budget coarsening (fit only) |
| `undersampling.min_effective_samples` | `36` | data-quality gate |
| `strikes.window_ticks` / `alpha_strike` / `semantics` / `min_strikes_to_score` | `4` / `0.05` / `window` / `3` | strike ring, k-of-n = 3-of-4 |
| `fusion.gate` / `alpha_fuse` | `simes` / `0.05` | fusion |
| `fusion.metric_weights.default` | `1.0` | S_pod weights |
| `fusion.prior_anomaly_rate` / `markov.mean_anomaly_sojourn_ticks` | `0.01` / `6` | Markov prior + sojourn |
| `fusion.markov.h1_scale_gamma` / `evidence_gain` | `2.0` / `{rising 3.0, falling 1.0}` | evidence mapping |
| `fusion.calibration.mapper` / `isotonic.n_bins` | `isotonic` / `48` | mapper |
| `fusion.calibration.gate.window` / `max_fare_multiple` | `1d` / `2.0` | adoption gate (L_cal = 288 ticks) |
| `fusion.calibration.degeneracy.min_calm_span_ratio` | `1.0` | P3 degeneracy guard |
| `thresholds.source` | `applied-models` | reads `normal_threshold 0.2`, `anomaly_threshold 0.8` |
| `validity.counter_block_min_fraction` / `counter_max_gap` | `0.9` / `35s` | box-car admission |
| `persistence.scored_tick_history.depth` | `1d` | strike ring storage |
| `pool.workers` / `max_queue_depth` | `4` / `8` | refit concurrency |

## 4. Q3 — importability from a lab venv, and the three options

### 4.1 Import-time dependencies (OBSERVED: imported with only numpy/pyyaml/scipy present, no DB, no MLflow, no cluster)

| module | imports at load time | needs a running service? |
|---|---|---|
| `solo_mode.baseline` | numpy, math, subprocess, sys | no |
| `solo_mode.noise` | numpy; `baseline` lazily inside functions | no |
| `solo_mode.fusion` | numpy, math; `shared.bayesian.short_term`; **sklearn is imported lazily inside `fit_isotonic_calibration` / `isotonic_from_control_points`** | no (sklearn wheel needed only for the mapper) |
| `solo_mode.config` | pyyaml, typing | no |
| `solo_mode.window_store` | **sqlite3 (stdlib)** — accepts `path=":memory:"` | no |
| `solo_mode.driver` | sqlite3, `prometheus_client` **lazily** | no |
| `solo_mode.scan` | imports `driver` | no |
| `solo_mode.scenarios.synth` | numpy, yaml | no |

All eight imported successfully in `/tmp/solo-p3-venv`. **sklearn, mlflow, prometheus_client, pandas were NOT installed and NOT needed for import.** SOURCE + OBSERVED.

### 4.2 Entry points to call (exact signatures)

- `baseline.phase_of(ts, period_seconds, phase_bins, phase_anchor_epoch) -> int` (`baseline.py:36`)
- `baseline.stl_lite_fit(window, t1, period_seconds, phase_bins, phase_anchor_epoch) -> dict` (`baseline.py:69`)
- `baseline.stl_lite_forecast(fit, t1, period_seconds, phase_bins, phase_anchor_epoch) -> float` (`baseline.py:115`)
- `noise.rolling_one_step_residuals_incremental(blocks, min_fit_blocks, method, period_seconds=None, phase_bins=None, phase_anchor_epoch=0.0, starting_state=None) -> list[(ts, r)]` (`noise.py:592`) — **this is the production residual engine**
- `noise.rolling_one_step_residuals_oracle(blocks, fit_fn, forecast_fn, min_fit_blocks)` (`noise.py:663`) — test-only full-refit path
- `noise.mid_rank_cdf(residuals) -> Callable[[float], float]` (`noise.py:692`), `noise.two_sided_surprise(cdf, r) -> float` (`noise.py:740`)
- `fusion.strike_count(p_history, alpha_strike, semantics) -> int` (`:44`), `fusion.metric_is_eligible(window_fill, min_strikes_to_score)` (`:89`), `fusion.simes_p(tilde_p)` (`:112`), `fusion.k_eff(corr)` (`:130`), `fusion.S_pod(tilde_p, weights)` (`:170`), `fusion.ell_of(S_pod, k_eff, gamma)` (`:196`), `fusion.markov_matrix(pi, T_A)` (`:267`), `fusion.update_posterior(...)` (`:288`), `fusion.calm_span_ratio(...)` (`:333`), `fusion.fit_isotonic_calibration(...)` (`:500`, sklearn), `fusion.evaluate_isotonic_gate(...)` (`:616`, sklearn)
- `driver._score_continuous(window_store, model, pod_key, metric_name, tick_end, T, solo_cfg)` (`driver.py:1105`), `driver._score_all_metrics(store, pod_key, tick_end, T, prev_strikes)` (`:1267`), `driver.handle_solo_request(rt_config, request_context, in_ctx, *, read_src=...)` (`:1408`)
- `scan.build_one(...)` (`:1098`), `scan.run_build_cycle(...)` (`:2353`)
- `scenarios.synth.prepare_scenario`, `validate_scenario_yaml`, `run_scenario`, `compute_criteria`, `make_fetch_fn` (`synth.py:575`+)

### 4.3 The three options

| | (a) lab imports production read-only via `sys.path` | (b) pin a verbatim copy + parity test | (c) faithful reimplementation + parity test |
|---|---|---|---|
| reproducibility | breaks when the sibling repo moves (it is dirty today) | exact, pinned to `5bcc7f9` / `942b880` | exact only where the parity test covers |
| cost | ~0 | ~10 files, licence/maintenance drag | highest, but the code is small (reference ≈40 lines, CDF+surprise ≈20) |
| lab autonomy | low (lab results depend on an external working tree) | high | highest |
| risk | silent drift between paper and code | drift on refresh | numeric divergence in edge cases (ties, empty bins, NaN) |

**RECOMMENDATION: (c) reimplement, with (b) as a frozen test oracle.** Rationale: the numeric core is ~200 lines; a verbatim copy would drag `solo_mode` package plumbing (config validation, sqlite stores) into the lab forever, while re‑implementation keeps the lab runnable on synthetic data with numpy only. The parity test removes (c)'s risk because the production functions *are* callable in-process (no cluster, no DB) — proven below.

### 4.4 Parity test — proven recipes (all three executed now, bit-exact)

- **P1 function parity (CDF/surprise):** production `mid_rank_cdf` vs a 10-line numpy port, 55 probes including ±1e9, exact ties and `residual+1e-12` → **max |Δ| = 0.000e+00**; floor check `p(max r) = 1/N = 0.001174` for N=852.
- **P2 reference parity (running state):** `rolling_one_step_residuals_incremental` (O(1) production path) vs `rolling_one_step_residuals_oracle` (full refit per block) on 900 synthetic blocks → **max |Δ| = 0.000e+00**, 852 residuals each. *This is the single most valuable fixture*: it proves the incremental state machine, the 48-bin phase model, the trend term and the empty-bin fallback in one assertion.
- **P3 chain parity:** `driver._score_all_metrics` with `SoloWindowStore(path=":memory:")` vs the lab pipeline on the same 3-signal block series → compare `p_raw` per tick (threshold 1e-12).
- **P4 end-to-end:** the packaged 10-pod 15 s flat series (leaf A3) → both chains → identical `p_raw` sequence.
- **Real-data gold fixture (optional but strong):** a `/api/dashboard/pods` payload carries `reference_models[m].residuals.values` (570 floats) + `last`; recomputing the CDF on it reproduced the live per-metric p exactly. Leaf A1 should save one payload as `tests/fixtures/live_payload_<ts>.json`.

**Deterministic harness exists:** `solo_mode/scenarios/synth.py` (`python -m solo_mode.scenarios.synth`) is seeded, headless, writes `scores.csv` with `p_raw`/`p_published` per tick, and **completes in 360 s wall for 1200 ticks / 1 pod / 11 metrics** (OBSERVED, exit 0). Existing tests: `analyser/tests/{integration,unit}/test_solo_*` cover it; no test currently asserts p for an arbitrary series, so A1 should add the P1–P3 fixtures.

## 5. Q4 — what `generate.py` does

- 479 lines, pure numpy + matplotlib, **imports nothing from production** (SOURCE `generate.py:1-40`); constants `TOTAL=1440` (5 d of blocks), `PERIOD=86400`, `NBINS=48`, `DT=6`, `DTB=582`, `ALPHA_STRIKE=0.05`, `START=864` (OBSERVED: printed from the module).
- Six synthetic cases: `sim_diurnal` (S1), `sim_drift_step` (S2, +12 CPU-units at display 12:00), `sim_noise_increase` (S3, noise 1.5→4.5 / 12→36 at display 24:00, two 6-unit CPU spikes), `sim_anomaly_burst` (S4, two 18-block bursts), `sim_counter_gaps` (S5, NaN net every 2 h), `sim_mixed` (S6, diurnal + mem drift + burst). Own RNG (`default_rng(1..6)`), white noise only.
- `reference_and_p(x, avail)`: window `[i−582, i−DT)`, i.e. **576 blocks**; per-block refit; residual CDF over the *same* 576-block span; mid-rank + two-sided formula identical to production.
- **Deviations from production (complete list):**
 1. window 576 blocks vs production 570 (`Dt−dt`);
 2. refit **every block** vs production's 6-block refit cycle with a frozen model between refits;
 3. therefore the tail is exactly 30 min vs production's 25–30 min at scoring time;
 4. residual population recomputed over a sliding window each block vs production's persisted, incrementally-appended 570-entry record;
 5. `min_fit` threshold 8 available samples vs `min_fit_blocks = 48`;
 6. own white-noise generators, no AR(1)/factor structure, no count metrics, no box-car/gap attribution, no units law (memory in MiB constants, network in raw units);
 7. no strike ring, no Simes, no `k_eff`, no Markov, no mapper, no thresholds (it plots single per-metric p only);
 8. NaN handling by simple masking, no `counter_block_min_fraction` (0.9) admission rule.
- **Caption numbers, re-derived by calling `generate.py`'s own functions (OBSERVED):** S2 step p = 0.00174 (`≈` the 1/576 floor), p(+12 h) = 0.0365 → caption "about 0.04" ✔, p(+36 h) = 0.684 → "about 0.7" ✔, quiet median before step 0.503; S3 p at the calm spike = 0.0017 vs caption "0.037" ✘, at the noisy spike = 0.311 → "0.31" ✔, median p calm 0.475 / noisy 0.181, `P(p<0.05)` 0.058 → 0.219, `P(p<0.004)` 0.017 → 0.019; S4 burst medians 0.0017 and 0.0156 → caption "≈0.002 / ≈0.018" ✔, cpu strike count 14/17 per burst vs caption "14/18" (block 0 is unscorable) ≈✔; S1 (from the archived run) corr 0.97 / residual sd 1.58 → caption "0.97 / 1.6 vs 1.5 injected" ✔.
- **NOT reproducible from the shipped file:** the caption's "about 0.003" strike line (per-metric floor at N=576 is 0.001736 and the step-block value is 0.00174) and the "strike fraction 78/80" (generate.py has 3 signals × 18 blocks = 54 scorable blocks per burst; the 80-block basis is not derivable). Both must be recomputed by A1 from a stated population.

## 6. Q5 — the four yardstick quantities and the published-probability definition

**What production actually publishes under flat load (OBSERVED):** 10 pods, all rows `label = raw`, `calibration_state = scored`, `p_published = 0.001288119712904` (the quiet-state posterior floor), 11 reference metrics, `n_residuals = 570`. `p3_ticks.jsonl` (6776 ticks): `p_raw` min = median = 0.0012881, max 0.99952; the 3140 rows labelled `calibrated` are all **pre-P3** (2026-11-05 08:00→13:00); after the 2026-11-06 16:00 revert every row is `raw` — consistent with `SOLO-OPS-P3.md` §2/§10 and the P3 memory report's band 0.0013–0.0042. So **the live 0.0013–0.0042 band is p_raw**, and its width comes from rare single-metric strikes (4-tick ring, k=3, p_strike 0.05 ⇒ a cluster needs 3 strikes in 4 ticks), not from the floor.

**What the lab gets on synthetic data (OBSERVED, fixture run):** `status = fixture_unscorable`; 599 scored ticks of 1200, **first scored tick 584**; `p_raw` min 0.000787 / median 0.001291 / max 0.070215; **0 of 599 ticks > 0.2**; `calibration_state` always `calibrating`; `probability_label` always `raw`; guard log `gate=False guard_ok=False calm_span_ratio=2.77e-06 floor=1`. ⇒ the mapper is never adopted on a flat synthetic load, by design (`min_calm_span_ratio = 1.0`), exactly as in production.

**RECOMMENDATION — yardstick on `p_raw`, not `p_published`.** Justification: (i) it is what production publishes (no verified mapper); (ii) the isotonic map is fitted per reference on that reference's own healthy window, so a calibrated value is not comparable across references — the same anomaly maps to different numbers for STL-lite and TimesFM-3, which destroys the Part 2 comparison; (iii) the mapper gate is unreachable for flat synthetic controls. Report `p_published` as a secondary column only when the gate passes, and record `calibration_state` per tick so the two are never mixed. Consequence: the lab measures raw detector sensitivity, so any gain from calibration is invisible — state this in the limitation profile.

**Definitions (fix these in the workcard):**
- Tick grid: 5-min ticks; **drop ticks < 584** (first tick with a full model + CDF, measured) and every tick whose state is not `scored`.
- Onset: the generator's injected onset tick (ground truth), never inferred from p.
- Detection latency = `first j ≥ onset with p_raw > 0.2` − onset, in ticks; censored `> horizon` when there is no crossing.
- False-positive rate = `#{non-anomalous scored ticks with p_raw > 0.2} / #{non-anomalous scored ticks}`, excluding the warm-up and a **4-tick guard band** right after the anomaly ends (ring still warm).
- Settling time = ticks from the anomaly end until `p_raw ≤ baseline + tol` for **6 consecutive ticks** (one refit cycle + 1 = the model's own memory); baseline = median `p_raw` over the pre-onset quiet segment, `tol = max(0.05, 3·MAD of that segment)`; censored as "not settled within horizon". A pure `p ≤ 0.2` test is unusable here: the floor is 0.0013 and quiet values swing by ~0.05.
- Reference fidelity on quiet segments = MAE and RMSE of `observed − forecast` over contiguous stretches with no injected anomaly and ≥ 582 ticks after the last one, per signal, in native units.

## 7. Q6 — the flat control

- The production flat-load *shape* comes from an out-of-repo tester: `baseline_constant_small` in `pipelineml-tester/test/load_test/baselines/constant_small.yaml` — 200 mCPU, 128 MiB, 0 rps, 0 net, 10 pods, seed 42, 3600 s, uniform. SOURCE (file read). It is **not** produced by `solo_mode/scenarios`; the fixture synthesises its own load.
- Live flat measurement for comparison (docs §8, OBSERVED): working set 244 MiB, CPU display 16.4, rx 5.7–6.2 KB/s ⇒ different magnitudes from the tester's 200 mCPU / 128 MiB. **Define the lab flat control in the lab's own units, not by copying the tester YAML.**
- Chain meaning of the band: with no strikes `S_pod = 0` ⇒ `p_raw` sits exactly at 0.0012881; an excursion to ~0.0042 needs a metric to cross. So a synthetic flat control must produce a **point mass at 0.0012881** plus sparse excursions; any flat run whose `p_raw` leaves 0.0012–0.005 is a harness bug.

## 8. Q7 — structural-limit generators for Part 2 §5

**Hard constraint (OBSERVED, source):** the fixture supports **one sinusoid, one period**, and `synth.py:383-389` requires `86400 % period_ticks == 0`. Allowed 5-min periods: 288 (24 h), 144 (12 h), 96 (8 h), 72 (6 h), 48 (4 h), 36 (3 h), 24 (2 h), 16 (90 m). A weekly period (2016) is **rejected**; multi-period is not expressible. SOURCE `solo-scenarios.yaml:16-17,55-57`.

**Measured representability (OBSERVED, production `rolling_one_step_residuals_incremental`, 1500 blocks, amplitude 6 units, noise sd 1.5):** baseline noise only sd 1.595 / MAE 1.274; 6 h 1.706; 3 h 2.044 / MAE 1.631; 2 h 2.395 / MAE 1.949; **2.5 h non-divisor 4.702 / MAE 4.095**; 7 h non-divisor 4.725. ⇒ a period dividing the day is absorbed as a 30-min staircase (mild residual growth); a non-divisor period is not representable (residual ≈ full oscillation) — and those are the periods the fixture refuses.

**Proposed specs:**
- (i) *Multiple recurring cycles* — requires a generator extension:
 ```yaml
 generator:
 period_ticks: 288          # legacy single-period key retained
 harmonics:                 # NEW: additive, amplitudes/phases drawn once per seed
 - {period_ticks: 288,  amplitude: 6.0, phase: 0.0}    # daily
 - {period_ticks: 72,   amplitude: 3.0, phase: 1.1}    # 6 h
 - {period_ticks: 2016, absolute_ticks: true, amplitude: 4.0, phase: 0.4}  # weekly
 ```
 plus dropping the `86400 % period_ticks` check for `absolute_ticks: true`. Keep `ar_phi: 0.5`, `variance_weights [0.1, 0.7, 0.2]`, `groups: [[0,1,2]]`.
- (ii) *Dominant sub-daily* — expressible today for divisors: `period_ticks: 36` (3 h), amplitude 6–10 units CPU / 60–100 MiB memory / 0.5 MiB/s rx, so it dominates the 6-unit diurnal term and the 48-bin model can only chase a staircase. Add a **non-divisor twin** (absolute period 9000 s = 2.5 h, amplitude 6) — today rejected by the fixture, and the sharpest structural test.
- Both must report quiet MAE/RMSE, `P(p>0.2)` on quiet stretches (expected *raised*: the noise law sees a correlated residual), burst latency and settling.

## 9. Q8 — compute cost of the present reference

- `stl_lite_fit` on 576 blocks: **0.198 ms/call**; `stl_lite_forecast` **0.0004 ms/call**; `mid_rank_cdf` **0.014 ms** per metric per tick; `two_sided_surprise` **0.09 ms** (OBSERVED, `perf_counter` averages earlier in this session).
- One refit = 1 fit + 570-block residual replay ≈ 0.2–1 ms per metric; a 10-pod × 11-metric pass ≈ 0.02–0.1 s CPU — 3–4 orders of magnitude below a foundation-model forward pass; this is the number Phase B must contrast with TimesFM-3.
- Cadences: ingest `T = 300 s`; **refit every `dt = 1800 s`** (`driver.py:2293`, two-cadence step `driver.py:2219-2298`); calibration refit **every tick while no healthy mapper exists** (`driver.py:1676-1686`). End-to-end fixture wall: **0.30 s/tick** for 1 pod × 11 metrics including sqlite (1200 ticks / 360 s, OBSERVED).

## 10. CONTRADICTIONS (vision vs source) — hard-stop inputs for S

| # | Vision says | Source says | Severity |
|---|---|---|---|
| C1 | Part 1 §6: the campaign "extends the existing scenario fixture harness … rather than inventing a new one" | the delivered generator (`scenario-figures/generate.py`) imports nothing from production and re-implements reference + p with different geometry (§5) | **hard** — deliverable provenance |
| C2 | Part 1 §2: window "2 d of 5-min blocks ending 30 min before" (576 blocks) | production window = 570 blocks (`Dt − dt`); tail is 25–30 min at scoring time because the model is frozen 6 ticks | measurement caveat |
| C3 | Part 1 §3: p against "the empirical noise law of the same two-day window" | population is a persisted 570-entry record appended incrementally, not recomputed per tick | measurement caveat |
| C4 | Part 1 §4 S1 caption: sawtooth repeats "on the CPU and memory signals" | `generate.py:99-101`: CPU only; memory is a pure 40-unit sinusoid | caption error |
| C5 | Part 1 §4 S4: the burst "does not need to be synthesised at all, because one is already recorded" | Figure 4 comes from `sim_anomaly_burst` (`generate.py:129-141`), i.e. synthetic | **hard** — S4 data source |
| C6 | campaign context + report: "15 s raw, mean of 20 samples/block" | deployed ConfigMap `sampling_cadence: 16s`; repo default `15s` ⇒ 18.75 samples/block | config drift |
| C7 | Part 1 §4 captions call ~0.003 "the strike line" | `generate.py` shades `ALPHA_STRIKE = 0.05`; per-metric floor at N=576 is 0.001736 | caption error |
| C8 | campaign: flat band 0.0013–0.0042 with "no degenerate mapper ever adopted" | 0.0013–0.0042 **is p_raw**; `calibrated` rows exist pre-P3 (2026-11-05) and were reverted | terminology |

## 11. Commands run (read-only; scratch in /tmp only)

`wc -l` / `grep -n` over `solo_mode/*.py` + configs; `git rev-parse HEAD` both repos; python probes in `/tmp/solo-p3-venv`: import matrix (8 modules), `stl_lite_fit` benchmark, parity P1/P2 (0.0 diffs), sub-daily representability sweep, `generate.py` caption re-derivation; fixture run `python -m solo_mode.scenarios.synth --scenario healthy --seed 20261012 --horizon 1200` → `/tmp/refm-scratch/out/healthy1` (exit 0, `run.json` status `fixture_unscorable`); scratch config copies deleted. No writes to the cluster, production source or the lab repo.

## 12. Recommendations for the Planner

1. Make leaf A1 a **faithful port** (option c); production functions used only inside the parity test (P1–P3).
2. Pin the oracle: `pipelineml-anomaly-detector@5bcc7f9` + `pipelineml-shared@942b880`, named in the parity test docstring.
3. Reference signature to implement: `fit(window_blocks, t1) → (trend, seasonal[48])`, `forecast = trend + seasonal[phase(t)]`, empty bin → seasonal 0.
4. Window = **570 blocks** ending `refit_block − 30 min`; model frozen 6 ticks; residuals appended, never recomputed.
5. p = `(min(c, N−1)+0.5)/N` with `c = #{r < v}` (upper rank on ties), then `F(−|r|) + 1 − F(|r|)`; floor `1/N`.
6. Implement the strike ring (4 ticks, k=3, p<0.05), Simes (`min K·p_(k)/k`), `S_pod = Σ −ln tilde_p`, and the 2-state Markov posterior (π=0.01, sojourn 6) — all cheap, and together they are the whole chain.
7. Do **not** put the mapper in the accuracy path; keep `calibration_state` in outputs and expect `calibrating/raw` always (`min_calm_span_ratio = 1.0` blocks adoption).
8. Build S1–S6 **in the production `ScenarioSpec` dialect** (`period_ticks: 288`, `ar_phi: 0.5`, `variance_weights [0.1,0.7,0.2]`, `groups: [[0,1,2]]`, offsets 32/32/32) so the same fixtures feed the production chain — this replaces `generate.py` and resolves C1.
9. Fix the fixture memory baseline caveat: `continuous_units["1"].baseline_offset = 32.0` MiB is **not** the live 244 MiB; A1 must raise it or document the offset before comparing magnitudes with packaged real data.
10. Flat control: 3 signals, diurnal amp 6/40/0.3, white noise 1.5/12/0.15, no counts, horizon ≥ 1200 ticks; expected = point mass at p_raw 0.0012881 with excursions ≤ 0.005.
11. Yardstick on `p_raw` with §6 definitions verbatim — they are leaf C's acceptance contract.
12. Extend the fixture generator with `harmonics` + `absolute_ticks` *before* writing the Part-2 §5 structural scenarios (today both specs are inexpressible).
13. Assert the reproducing caption numbers as regression tests (S2 12 h→0.036, 36 h→0.684; S4 medians 0.0017/0.0156; S3 noisy spike 0.311) and **re-derive** the two that do not (0.003 "strike line", 78/80).
14. Keep the measured scored-tick start (584) as the warm-up cut; earlier ticks are unscorable by construction.
15. Budget: ~0.2 ms/refit/metric for the reference vs 0.30 s/tick fixture wall — quote both to Phase B so foundation-model compute is not mixed with harness overhead.

## 13. Open questions that need an operator decision

1. **Cadence authority:** `15 s` (repo default, 20 samples/block, matches existing figures) or `16 s` (deployed ConfigMap, 18.75 samples/block)? It changes the sample-mean law in every synthetic raw series (C6).
2. **S4 data source:** Part 1 §4 calls the burst "already recorded" while the delivered figure is synthetic (C5). If the real P3 burst is the required S4 input, leaf A3 must package it; otherwise the caption must be corrected.
3. **Fixture horizon:** the shipped healthy scenario at 1200 ticks never becomes calibrable (`fixture_unscorable`). Confirm the lab target (≥ ~2 d warm-up + 288 scored ticks, e.g. 2400) before A1 fixes harness defaults.
