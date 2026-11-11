# E Completion — SOLO-REFM A1c

- Date: 2026-11-09. Executor `RefmEA1cS1`. Card: `evidence/omp-workcards/refm-A1c.md`. Lab: `pipelineml-model-exploratory-work/reference-model-study`.

## Stage 1 — library + tests (Commit 1)

### 1. Changed files (Commit 1 = `7bbe268`, `feat(refstudy): add four-quantity harness and quantile-band figure template`)
- `config/harness.yaml` — stage-1 sections only (reference, chain, seeds, figure_seed, scoring, flat_control, sensitivity, plot); `captions`/`real`/`outputs` are added by stages 2–3 with their parsers.
- `src/refstudy/harness/{__init__,config,metrics,evaluate,aggregate}.py` — config loader, pure-numpy four quantities, `evaluate_records`/`evaluate_reference`, `aggregate_seeds`/`profile_rows`.
- `src/refstudy/plotting/{__init__,bands,figure}.py` — `QuantileBand`, `build_figure`, `save_figure`.
- `tests/test_harness_{config,metrics,evaluate,aggregate}.py`, `tests/test_plotting_{bands,figure}.py`.

### 2. Preflight (1.0)
- `git log --oneline -10` head: `7cbda00` B1, `ca0fd63` A1a stage 2b, `26acad5` A1b S1–S4/S6/FLAT, `2519ee4` A1a stage 2a. A1b Commit 2 (S5/S7/S8) NOT on disk — waived by S for this stage (tests use S4/S3/FLAT only).
- `git status --short` at start: clean for owned paths.
- Imports `run_pod, score_pod, TickRecord, ReferenceRun, check_no_leakage, get_scenario, encode_raw, loader` OK.
- Fact 2 signatures (literal):
  `run_pod(raw, cfg, *, provider=None, forced_gaps=None, observed_cells=None, cold_start_t0=None) -> PodRun` ✓.
  `TickRecord` fields `[tick_end, scored, skip_reason, p_raw, p_simes, S_pod, k_eff, eligible, degraded_fraction, metrics]` ✓.
  `MetricTick` fields `[observed, forecast, residual, p, tilde_p, n_k, eligible, reason, model_t0, ess]` ✓.
- **Mismatches found (adapted inside owned files only, `reference/` untouched):**
  1. `run_pod` is keyed by CANONICAL metric name (`container_cpu_usage_seconds_total`…), not by short; `Scenario.raw` is keyed by short ⇒ harness maps `raw={scenario.names[s]: scenario.raw[s]}`.
  2. With `include_rare_count=False` `run_pod` STILL demands raw for every continuous entry incl. `tx_bytes` (disabled in the scenarios) ⇒ `ValueError: run_pod: raw series missing for metrics: ['container_network_transmit_bytes_total']`. A 3-metric dict is therefore only accepted with `metrics.entries` restricted to the scenario's enabled signals. `HarnessConfig.ref_synth` = `dataclasses.replace(ref, metrics=replace(ref.metrics, include_rare_count=False, entries=<cpu,mem,rx_bytes>))`; `reference.yaml` unedited; `degraded.mandatory_metrics` (cpu) unaffected.
- Smoke `run_pod(FLAT seed1 n=700 raw, cfg_K3)`: 700 records, first scored `k+1` = **584**, 0.06 s. `df -h /`: 461G, 41G free (92 %).

### 3. Test / lint results (1.4)
- `.venv/bin/python -m pytest tests/test_harness_*.py tests/test_plotting_*.py -rs` → **100 passed, 0 skipped** (3.6 s).
- `.venv/bin/ruff check src/refstudy/harness src/refstudy/plotting tests/test_harness_*.py tests/test_plotting_*.py` → All checks passed; `ruff format` clean. `git diff --check` clean.
- `grep -rn "solo_mode\|sys.path" src/refstudy/harness src/refstudy/plotting` → empty.
- Highlights: leaking provider (`fit_end + T`) ⇒ `ValueError leakage`; `evaluate_records(run.records)` ≡ `evaluate_reference` ≡ explicit `StlLiteProvider`; `p_raw` NaN exactly where `k+1<584` or unscored (S4 n=900); first valid `k+1`=584.

### 4. Smoke evidence (full-size, single seed, not a gate)
S4 seed 1 n=1872 (0.46 s incl. generation): event 0 latency 2 / settle 17, event 1 latency 5 / settle 4; FPR 0.1124 (140/1245); fidelity MAE cpu 1.28, mem 10.18, rx 0.132. FLAT seed 1 n=1872: FPR **0.1156** (149/1289), `p_raw` frac in flat band 0.768, q99 0.989 — i.e. the default factor-AR(1) FLAT is NOT a flat `p_raw` at the point mass; the FP episodes are 6-tick Markov-sojourn runs (e.g. k=629–634). Reported as measured; no tuning. Figure rendered (S4 + synthetic cpu band) and inspected: layout, spans, bands, threshold lines correct.

### 5. Deviations / notes
- Preflight mismatches 1–2 above (canonical keys; entries restricted to enabled signals).
- `QuantileBand.at(level)` interpolates linearly between neighbouring levels (outside the level range ⇒ `ValueError`): the card's configured inner band `[0.25, 0.75]` is not among the 9 TimesFM decile levels `0.1..0.9`, so an exact lookup could not serve both. Medians/outer (0.1/0.5/0.9) are exact.
- `QuantileBand.ticks` = tick-end epoch seconds (`TickRecord.tick_end` axis).
- `settling()` takes an extra `onset` argument (baseline window is defined before the onset while `start` is the end for bounded events); `fidelity_mask` takes `(onset, end|None)` pairs and applies the stricter of `fp_guard_ticks`/`min_quiet_ticks_after_anomaly` (identical to the card's AND of the two conditions).
- MAD in `tol` is the raw (unscaled) median absolute deviation.
- Module sizes: `evaluate.py` 226, `config.py` 210 lines (card says ≤ 200; not split further to avoid adding unowned files).
- `fidelity` regime split is reported per signal as `fidelity_by_regime` (list of `{lo, hi, mae, rmse, bias, n}`; `[]` when the scenario has no regime).

## Stage 1b — adapt the harness to the 11-metric production-shaped chain (D12)
Scenarios now carry cpu, mem, rx_bytes, tx_bytes + 7 quiet rare counts (A1b stage 3 `76451a6`; pure-Poisson packet coupling `d41c91f` already in the tree when the final numbers below were taken).
- `config/harness.yaml`: `chain.synthetic_include_rare_count: true` (K=11); new `sensitivity.k3 {metrics: [cpu, mem, rx_bytes], include_rare_count: false}` (the old chain as a documented sensitivity, built inside `HarnessConfig.ref_k3` by restricting the entries; `ref_synth` stays the K=11 chain); `plot.signals: [cpu, mem, rx_bytes]` (displayed columns) and `plot.colors.tx_bytes`.
- `harness/config.py`: `K3Cfg`, `Sensitivity.k3`, `HarnessConfig.ref_k3`, `PlotCfg.signals`; fail-fast if the synthetic/K3 rare flag is on while `scenarios.yaml rare_counts.enabled` is false; `sensitivity.k3.metrics` must be enabled continuous signals; `plot.signals` unique scenario signals; colors required for every enabled scenario signal.
- `harness/evaluate.py`: `evaluate_reference(provider, scenario, hcfg, *, chain=None)` runs `scenario.chain_raw()` (11 canonical metrics) through `hcfg.ref_synth` (or `chain`, e.g. `hcfg.ref_k3`); fidelity/p/strike arrays are stored for every continuous signal the chain served (cpu, mem, rx_bytes, tx_bytes; three for K=3).
- `plotting/figure.py`: columns = `plot.signals` (tx mirrors rx and is NOT plotted); the p_raw strip and quantities use the full chain; `bands` for a non-plotted signal -> `ValueError`.
- Tests fixed to the new contract (no assertion weakened): `run_pod(s4.chain_raw(), ...)`, 4-signal strike checks, 3-column titles; added tests for the 11-metric chain shape, the K=3 sensitivity (3 signals, identical continuous forecasts, different p_raw), the synthetic-flag-off chain and the rare-flag/scenario consistency check, new config keys (missing/mistyped/invalid).
- Gates: `pytest tests/test_harness_*.py tests/test_plotting_*.py -q` -> 114 passed, 0 skipped; ruff check + format clean on owned paths.
- FLAT seed 1, n=1872 (reported, not tuned): **K=11 FPR 0.0396 (51/1289), `p_raw` median 0.001289, q99 0.809, frac in flat band [0.0012, 0.005] 0.901**; fidelity MAE cpu 1.298, mem 10.17, rx 0.1326, tx 0.1324 (n=1289 each). K=3 sensitivity reproduces the stage-1 smoke exactly: FPR 0.1156 (149/1289), band fraction 0.768, q99 0.989. K=11 improves FLAT markedly but does NOT reach production's 0/599 above 0.2 (still above `flat_control.max_outside_fraction` 0.02): residual single-metric strikes on the factor-AR(1) noise (cpu/mem/rx/tx level of noise) still lift Simes/Markov on some ticks — reported as measured.

## Stage 2 — Part-1 runs + caption regression + ESS diagnostics (Commit 2)

Resumed after an abort mid-run: 6 new files + 3 modified files were already on disk (`harness/{caption_targets,captions,ess,profile,profile_config}.py`, modified `harness/{aggregate,evaluate}.py` + `config/harness.yaml`). All reviewed against the card: kept, and finished with `scripts/run_part1.py`, `tests/test_harness_captions.py`, `tests/test_harness_profile.py`, the real runs, and the outputs. Commit 2 = `194938f` (`data(refstudy): record Part-1 limitation profile, figures and caption regression`) — paths: `scripts/run_part1.py`, `src/refstudy/harness/{caption_targets,captions,ess,profile,profile_config,aggregate,evaluate}.py`, `tests/test_harness_{captions,profile}.py`, `config/harness.yaml`, `results/part1-{profile.json,profile.csv,caption-regression.json}`, `figures/part1-scenario-{1,2,3,4,5,6,7,8,flat}.png`.

### 1. Commands + outputs
- `scripts/run_part1.py --config config/harness.yaml --stage scenarios`: 180 runs (9 scenarios × 5 seeds base + white 3×5 + k3 9×5 + ess_off 5×5 + snr 5×5×2) on 4 workers, **56.3 s total wall** (budget 40 min; per-run wall min 0.51 / median 1.41 / mean 1.22 / max 2.04 s). `stage scenarios: flat_band_violation=True (56.4 wall s)`.
- `--stage captions`: **4.5 s wall**; `reproduced=6, changed=7, recomputed=2, not_derivable=5`.
- Gates: `pytest tests/test_harness_*.py tests/test_plotting_*.py -q` → **129 passed, 0 skipped** (15.5 s); `ruff check` + `ruff format --check` on `src/refstudy/harness src/refstudy/plotting scripts/run_part1.py tests/test_harness_*.py tests/test_plotting_*.py` → clean; `git diff --check` clean; `grep -rn "solo_mode\|sys.path" src/refstudy/harness src/refstudy/plotting` → empty.
- PNG check: all 9 figures 1980×1410 px (height > 800), non-blank (grey std 40–51, 0–255 range). Vision-model inspection unavailable this session (Bedrock 404 on the vision endpoint); instead verified structurally: 10 axes (3×3 + p_raw strip), 3 strike lines at α_strike (0.05), 1 line at 0.2 in the strip, 3 zero lines, `FPR` text on every figure, `latency` on S4; S4 re-render is byte-identical to the committed PNG.

### 2. Profile table (straight from `results/part1-profile.json`, base K=11 chain, 5 seeds, mean±sd [min,max], ticks)
| scenario | first valid k+1 | FPR | p_raw>0.2 | latency (mean±sd [min,max]) | settle | fidelity MAE cpu / mem / rx |
|---|---|---|---|---|---|---|
| S1 | 612–624 | 0.470±0.011 [0.455,0.483] | 0.470 | no events | – | 1.31±0.06 / 10.32±0.41 / 0.130±0.008 |
| S2 | 584 (all) | 0.038±0.010 [0.028,0.047] | 0.089 | drift 41.8±26.8 [1,69]; step 3±0 [3,3] | drift 48.8±29.3 [5,81]; step `settle_censored` ×5 | 1.33±0.05 / 10.42±0.63 / 0.129±0.007 |
| S3 | 594–624 | 0.467±0.014 [0.454,0.481] | 0.463 | E1 42.2±5.0 [35,47]; E2 25.8±29.1 [3,68] (1 censored) | E1 36.2±5.0; E2 23.5±26.3 (1 not_detected) | 1.31±0.07 / 10.30±0.75 / 0.128±0.005 |
| S4 | 584 (all) | 0.040±0.002 [0.039,0.043] | 0.067 | E0 3.0±1.9 [0,5]; E1 4.6±0.6 [4,5] | E0 5.8±2.7 [4,10]; E1 4.0±0.0 | 1.32±0.05 / 10.35±0.46 / 0.129±0.004 |
| S5 | 584–624 | 0.456±0.021 [0.444,0.481] | 0.456 | no events (gap scenario) | – | 1.31±0.06 / 10.40±0.27 / 0.130±0.006 |
| S6 | 606–624 | 0.461±0.009 [0.454,0.473] | 0.485 | drift 39.0±3.7 [35,42]; bump 59.0±4.2 [53,65] | drift 39.0±3.7; bump 47.0±6.2 [39,55] | 1.30±0.05 / 10.28±0.39 / 0.128±0.005 |
| S7 | 584 (all) | 0.414±0.013 [0.398,0.431] | 0.414 | bump 3.6±1.1 [2,5] | 2.4±1.5 [0,4] | 2.66±0.10 / 18.30±0.53 / 0.169±0.003 |
| S8 | 584 (all) | 0.473±0.008 [0.465,0.479] | 0.473 | bump 6.4±3.7 [0,9] | 8.4±2.6 [7,13] | 5.05±0.12 / 41.78±0.85 / 0.268±0.013 |
| FLAT | 584 (all) | 0.037±0.005 [0.029,0.041] | 0.037 | no events | – | 1.32±0.05 / 10.40±0.27 / 0.130±0.004 |

Reading: S2-E1-step `settle_censored` ×5 is correct, not a bug — the step is persistent to end of series, so the settling search has no end boundary (baseline 0.001289 ≈ point mass; the p_raw stays above tol forever). S4 burst latency is the healthy detector (0–5 ticks); the high-latency events (S2/S3/S6) are the reference-lag / stale-ESS cases below.

### 3. FLAT control (D8/D12/D13)
`flat_control` block, base K=11 chain: band [0.0012, 0.005], point_mass 0.001288, max_outside_fraction 0.02.
| seed | n_valid | frac in band | outside fraction | FPR | violation |
|---|---|---|---|---|---|
| 1 | 1289 | 0.9015 | 0.0985 | 0.0396 | true |
| 2 | 1289 | 0.9022 | 0.0978 | 0.0287 | true |
| 3 | 1289 | 0.8875 | 0.1125 | 0.0396 | true |
| 4 | 1289 | 0.8960 | 0.1040 | 0.0357 | true |
| 5 | 1289 | 0.8782 | 0.1218 | 0.0411 | true |

**`flat_band_violation: true`, `n_seeds_violating: 5/5`** — flagged and reported, never tuned away. The K=11 synthetic chain puts ~89–90 % of valid ticks inside the band (vs 73–77 % at K=3) but 8.5–12 % outside: residual factor-AR(1) noise strikes. Sensitivities: white noise FLAT FPR 0.0017 (0.2 % of ticks > 0.2, i.e. near the chance level — white noise is the honest flat control) vs factor 0.0369; K=3 FLAT FPR 0.126, band fraction 0.734.

### 4. ESS-gate diagnostics (D14) — `ess` block of the profile + CSV
Per scenario/seed/metric: `ess_gated_cycles/cycles`, ESS min/median, scored-tick count, stale-model hours. Aggregate over seeds, base K=11 chain (cpu column shown; mem similar, rx/tx near-clean):
| scenario | scored ticks (mean) | cpu ESS-gated fraction | cpu ESS median | stale hours | longest stale |
|---|---|---|---|---|---|
| S1 | 714 | 0.449 | 42.0 | 45.2 h | 5.9 h |
| S2 | 888 | 0.313 | 195.9 | 33.4 h | 33.4 h |
| S3 | 858 | 0.334 | 54.3 | 33.8 h | 5.5 h |
| S4 | 1289 | 0.000 | 240.8 | 0 | 0 |
| S5 | 927 | 0.284 | 56.8 | 28.6 h | 5.2 h |
| S6 | 728 | 0.438 | 42.8 | 44.3 h | 6.9 h |
| S7 | 1207 | 0.064 | 123.9 | 6.8 h | 2.9 h |
| S8 | 1289 | 0.000 | 418.8 | 0 | 0 |
| FLAT | 1289 | 0.000 | 303.9 | 0 | 0 |

S1 seed 1 reproduces the A1b3b measurement exactly: 732/1872 scored, 47.7 % of scored `p_raw` > 0.2, first valid k+1 = 618. The gate rejects strongly seasonal windows (S1/S6 diurnal: ESS median ≈ 42–43, ~44 % of cycles gated, 45 h of stale model) while accepting flat (FLAT/S8) and slow-structure (S2/S4) signals; S2's 33 h longest stale = the whole displayed drift day, which is exactly where the step/drift latency numbers come from.

Sensitivities (analysis-only, `dataclasses.replace` on the lab `RefConfig`; `reference.yaml` untouched):
- **(a) `ess_gate_off` (floor 0)** on S1/S2/S6/S7/S8: all 5 scenarios score **1289** ticks (the 583-tick warm-up still applies — the gate never scores *more* ticks than an ungated run; it only decides *which* ticks are scored). S1 FPR 0.470→0.425, S6 0.461→0.394, S2 0.038 (unchanged FPR but p_raw>0.2 0.089→0.246: the ticks that were unscored under the gate are now scored, and the served reference chasing its own drift/seasonal residual crosses the threshold there). **Mechanism (F2 correction):** with the gate on, a gated cycle serves **no model** — production `scan.py:1320-1332` returns `None` below the ESS floor and `driver.py:1081-1085` rejects a prior-cycle model as stale — so the affected ticks are **uncomputable/unscored** (the pod is skipped when mandatory CPU is unavailable), *not* scored with a stale forecast that strikes. The persisted posterior (the Markov `p_raw` state) carries over across the skipped cycles and scoring resumes at the next accepted refit, but no model is served and no strikes are added during the gated interval. Because the gate-on and gate-off FPR values have **different scored populations**, the aggregate comparison does not by itself establish that the gate does not improve detection; a matched-tick analysis is required for that claim.
- **(b) S1 SNR sweep** (diurnal amplitude/noise, all components scaled by one factor; gate on/off):

| SNR | gate | scored ticks | p_raw>0.2 | FPR | cpu ESS median | gated fraction |
|---|---|---|---|---|---|---|
| 0.5 | on | 1289 | 0.053 | 0.053 | 198 | 0.000 |
| 1.0 | on | 1276 | 0.145 | 0.145 | 101.6 | 0.010 |
| 2.0 | on | 1017 | 0.384 | 0.384 | 58.2 | 0.213 |
| 4.0 | on | 758 | 0.472 | 0.472 | 45.4 | 0.415 |
| 6.7 | on | 714 | 0.470 | 0.470 | 42.0 | 0.449 |
| 0.5–6.7 | off | 1289 | 0.053–0.429 | = same | – | 0 |

The gate's acceptance threshold sits between SNR ≈ 1 and ≈ 2 for the S1 shape (the present reference stops accepting the diurnal window once the seasonality/noise ratio exceeds ~1.5); at the S1 design SNR 6.7 it rejects ~45 % of cycles. With the gate off the same scenarios score the same 1289 valid ticks (the warm-up is identical) and FPR tracks SNR monotonically (0.053 at SNR 0.5 → 0.429 at 6.7) — the high FPR at high SNR with the gate off is the gate-free reference chasing its own seasonal residual. **Caveat (F2):** the gate-on/gate-off FPR values at each SNR compare different scored populations (gate-on leaves gated ticks unscored; gate-off scores every tick after warm-up), so this sweep establishes that the *ungated* reference degrades with SNR and that the gate converts those ticks into ~45 h of **unscored, model-unavailable** intervals at SNR 6.7 (zero at SNR 0.5) — it does not by itself establish a detection-quality ranking of gate on vs off; that requires a matched-tick analysis.

- **White noise (over-fitting-noise hypothesis)**: S1/S3/FLAT with `noise_kind=white` vs factor-AR(1): S1 FPR 0.455 vs 0.470, S3 0.456 vs 0.467, FLAT 0.0017 vs 0.0369. White noise barely moves the seasonal FPRs (the high gate-on FPR is dominated by the reference's own seasonal residual, not the noise law — and the gated ticks stay unscored either way) and makes FLAT cleaner — consistent with the hypothesis that the *noise law*, not the reference, is what makes flat data misbehave at K=11.

### 5. Caption regression (`results/part1-caption-regression.json`, K=3 faithful chain, ESS gate on; 20 targets)
| id | quoted (doc) | generate.py | faithful | gate-off | status |
|---|---|---|---|---|---|
| S1.corr_ref_obs | 0.97 | 0.9709 | 0.9796 | 0.971 | changed (0.005 tol) |
| S1.resid_sd | 1.6 | 1.568 | 1.61 | 1.565 | reproduced |
| S1.corr_seasonal_true | 0.99 | 0.9976 | 0.9968 | 0.9976 | changed |
| S1.strike_fraction | 0.05 | 0.0532 | 0.0486 | 0.0515 | reproduced |
| S1.median_p | 0.5 | 0.5208 | 0.5158 | 0.5193 | reproduced |
| S2.p_step_plus_2h | 0.03 | 0.0260 | 0.0088 | 0.0088 | changed |
| S2.p_step_plus_12h | 0.04 | 0.0365 | – | 0.0035 | not_derivable (ESS gate: no model at the probe block) |
| S2.p_step_plus_36h | 0.7 | 0.684 | – | 0.9491 | not_derivable (gate) |
| S3.p_calm_spike | 0.002 | 0.00174 | – | 0.00175 | not_derivable (gate) |
| S3.p_noisy_spike | 0.31 | 0.3108 | 0.3281 | 0.3281 | changed |
| S4.struck_burst1 | 14 | 14 | 14 | 14 | reproduced |
| S4.struck_burst2 | 14 | 14 | 14 | 14 | reproduced |
| S4.median_p_burst1 | 0.002 | 0.00174 | 0.00175 | 0.00175 | reproduced |
| S4.median_p_burst2 | 0.018 | 0.0182 | 0.0132 | 0.0132 | changed (0.0005 tol) |
| S4.strike_fraction_burst1 | 0.78 | 0.7593 | 0.7593 | 0.7593 | recomputed |
| S4.strike_fraction_burst2 | 0.78 | 0.6852 | 0.6852 | 0.6852 | recomputed |
| S4.background_median_p | 0.44 | 0.4826 | 0.4974 | 0.4974 | changed |
| S5.net_median_p | 0.49 | 0.4882 | 0.5296 | 0.5296 | changed |
| S6.struck_burst | 14 | 14 | – | 14 | not_derivable (gate) |
| S6.p_min_burst | 0.002 | 0.00174 | – | 0.00175 | not_derivable (gate) |

Summary: 6 reproduced / 7 changed / 2 recomputed / 5 not_derivable. The 5 `not_derivable` are all the ESS gate: the K=3 faithful chain has no model at the probe blocks (cpu ESS < 36 on the seasonal windows), so `p` is NaN there; with the gate off every value exists (e.g. S2 +12 h: 0.0035 vs generate.py 0.0365; S6 struck: 14 = quoted). `S4.median_p_burst2` and `S4.strike_fraction_burst2` both diverge from the doc's single 0.78: generate.py itself gives 0.6852 for burst 2, so the doc's "about 0.78 in both" is not what its own simulator produces — a caption-vs-simulator discrepancy, reported not tuned. R-A1 §5 re-derived values (0.0365/0.684, 0.0017/0.311, 0.0017/0.0156) are in the `ra1_value` column; R-A1's "0.0156" is generate.py's printed MINIMUM, kept as `generate_py_min` (independently verified: burst2 p_min = 0.00174, p_median = 0.01823).

### 6. Wall times
scenarios 56.3 s (180 runs, 4 workers; budget 40 min), captions 4.5 s. No seeds dropped.

### 7. Deviations
- The 6 on-disk module files from the aborted attempt were kept after review (all reproduce the D14 measurement; gap handling in `captions.py` matches `encode_raw` semantics: one `GapSpan` per NaN block, open interval, edge samples kept ⇒ exactly one `bad_gap` block per NaN block, asserted in `test_harness_captions`).
- One fix applied to on-disk code: `captions.py` learned-S(j) snapshot now takes the last *built* cycle with `t0 ≤ target` (the cycle in force at the target block) instead of requiring an exact `t0` match (which can miss the in-force cycle when a gated cycle sits between them).
- `evaluate.py`: the old single `evaluate_reference` was split into `run_checked` (PodRun) + `evaluate_reference` (EvalResult) so `profile.execute` can run `ess_diagnostics` on the same pod without a second `run_pod`.
- `aggregate.py`: `_stats` renamed `seed_stats` (exported) — pure rename, no behaviour change.
- `first_valid_k_plus_1` is 584 only when the ESS gate never fires (S2/S4/S7/S8/FLAT); on seasonal scenarios it is 594–624 — the gate delays the first scored tick. Recorded per seed in the JSON (acceptance criterion 2 "expected 584" holds wherever the gate is silent; the delayed values are the D14 measurement, not a deviation).
- `git_head` in the profile JSON is `013c570` (HEAD at run time; Commit 2 is this stage's commit).

## Review fixes (RV-A1 F2–F4; F1 adjudicated by S as D16 — no action)

Applied 2026-11-09. These edits do not change any chain law, threshold, ESS floor, or reference
behaviour; they correct the recorded narrative, make two tests non-vacuous, and fix the figure
to stop hiding valid observations. The 9 `figures/part1-scenario-*.png` are regenerated from the
existing `scripts/run_part1.py --stage scenarios` (the scenario figures share that stage; there is
no figure-only path) and `results/part1-profile.json` is confirmed unchanged in its scientific
content (only `git_head` and per-run wall times move).

- **F2 (ESS narrative):** corrected §4 to say the gate-off scenarios score **1289** ticks, not
  1872 (the 583-tick warm-up still applies; the gate never scores *more* ticks than an ungated run
  — it decides *which* ticks are scored). Gated cycles serve **no model** (production
  `scan.py:1320-1332` returns `None` below the ESS floor; `driver.py:1081-1085` rejects a
  prior-cycle model as stale), so the affected ticks are **uncomputable/unscored**, not scored with
  a stale forecast that strikes. Distinguished posterior carry-over (the Markov `p_raw` state
  persists across skipped cycles; scoring resumes at the next accepted refit) from stale-forecast
  strikes. Qualified the causal/detection claims: the gate-on vs gate-off FPR values at each SNR
  compare different scored populations, so the sweep does not by itself rank gate on vs off — a
  matched-tick analysis is required for that claim. Marked the R-A1 "not on the per-tick scoring
  path" ESS claim superseded (one note added at R-A1 §2.1, lines 26–27). The faithful gate
  implementation and the production floor are unchanged.
- **F3 (plotting):** `figure.py` now plots the **independently raw-derived block observations**
  (via `scenario.blocks()`) in row 0, so valid observations are shown even where no reference model
  is served. Forecast/residual/p remain gaps where unavailable. Model-unavailable intervals are
  shaded in a distinct colour (orange) with a legend entry, separate from the grey true-input gaps.
  Scoring/fidelity masks are unchanged (the harness is untouched). Added a behavioural plot test
  (`test_row0_observed_stays_finite_through_model_gaps`) on S1 seed 1 (finite raw cpu observation
  on all 576 displayed blocks, model absent on 413 of them).
- **F4 (tests):** replaced the vacuous `assert cfg.scenarios["FLAT"] is spec0 or True` in
  `test_harness_profile.py` with a real isolation assertion (every non-S1 scenario spec, plus the
  timeline and sampling, is unchanged vs `hcfg.scn`). Added a numerical caption expectation in
  `test_harness_captions.py` anchoring the 5 reproduced targets and 2 recomputed strike fractions
  within the declared tolerances.

## Stage 3 — S4-real replay, real flat control, Part-1 note (Commit 3, 44a1f99)

Applied 2026-11-10. New files: `src/refstudy/harness/real.py` (+ `PodReal`, `slice_raw`,
`window_mask`, `first_scored_k`, `p_raw_by_tick`, `common_tick_rows`, `log_correlation`,
`episode_verdict`, `fleet_verdict`, `flat_pod_summary`, `flat_summary`, `run_pod_real`,
`load_manifest`, bounded-ProcessPool plumbing), `src/refstudy/plotting/realfig.py`,
`tests/test_harness_real.py` (28 tests), `markdown/part1-limitation-profile.md` (120 lines).
Extended: `config/harness.yaml` (`real{…}`, `outputs.s4real_json/real_flat_json`,
`flat_control.point_mass_tol`), `harness/config.py` (`RealCfg`, `FlatControl.point_mass_tol`,
`_parse_real`, `_utc`), `harness/profile_config.py` (2 new output paths),
`scripts/run_part1.py` (`--stage real`, `--flat-only`, `run_real` + helpers).

### 1. Commands + outputs

```
$ .venv/bin/python scripts/run_part1.py --config config/harness.yaml --stage real
real: pod b4xkt wall 2.33s; projected total 23.3s vs budget 3600s
real: 10 pods replayed (10.1s wall incl. pool)
s4real: verdict=partial written …/results/part1-s4real.json
real flat written …/results/part1-real-flat.json (11.2s stage wall)
```

Preflight: git_head at run time `35fba07`; manifest
`08e54c1dde4ef56740a5febb9daaa6e0685d64a98ca49e4469cc13dd082d044a`; full flat window
2026-10-30T08:45:47.911Z → 2026-11-09T04:29:32.132Z; `restricted_window_used: false`
(projected 23.3 s ≪ 60 min budget). FINAL data, no resampling, no replays (the 11-08
restart is not replayed; the 11-06 window predates it, so as-seen detector state there was
continuous — no hybrid replay needed).

### 2. S4-real replay (window 2026-11-06 00:30–03:00Z; episode 01:15–02:25Z, 15 ticks)

**Fleet verdict: partial — 2 of 10 pods reproduce the recorded episode.**
(`pods_reproducing_episode: 2`, `pods_over_alpha_in_window: 2`; rule per card 3.1:
reproduced iff ≥7 pods with ≥8 of 15 ticks lab p_raw>0.5; not_reproduced iff no pod ever
≥0.2 in the window; else partial.)

| pod | lab >0.5 in episode | lab >0.2 in window | recorded >0.2 in window | r(log10) | lab max | recorded max |
|---|---|---|---|---|---|---|
| m7pr8 | 10/15 | 12 | 13 | 0.972 | 0.9895 | 0.9895 |
| vlsl8 | 14/15 | 16 | 16 | 1.000 | 0.9895 | 0.9895 |
| 2vwwd | 0/15 | 0 | 12 | −0.447 | 0.0037 | 0.9895 |
| 7gjdg | 0/15 | 0 | 12 | −0.302 | 0.0013 | 0.9895 |
| b4xkt | 0/15 | 0 | 12 | −0.384 | 0.0033 | 0.9895 |
| c5bdh | 0/15 | 0 | 14 | −0.407 | 0.0014 | 0.9895 |
| hcfj7 | 0/15 | 0 | 12 | 0.412 | 0.0021 | 0.9895 |
| mjnlq | 0/15 | 0 | 12 | 0.000 | 0.0013 | 0.9895 |
| qsv2m | 0/15 | 0 | 13 | 0.189 | 0.0023 | 0.9895 |
| rzpzm | 0/15 | 0 | 13 | 0.227 | 0.0037 | 0.9895 |

**Surprising result (reported, not tuned).** The recorded P3 store shows the burst on
**all 10 pods near-identically** — cross-pod std collapses to 0.0000–0.0001 at peak
(01:40–02:00, all pods 0.9893–0.9895) — so the fleet-synchrony is a detector-side
(stateful Markov posterior) property, not derivable per-pod from the metrics. The lab
reproduces the recorded envelope tick-by-tick on exactly 2 pods (m7pr8 payments-api-v1,
vlsl8 checkout-api-v2), including the 02:05–02:25 tail decay (0.77→0.05); the other 8
pods sit at the point mass 0.0013 across the whole window (lab max 0.0013–0.0037, 0 ticks
≥0.2). Raw-metric check (throwaway probes, deleted): no fleet-wide raw excursion in the
burst window — per-block cpu/rx means within base p5–p95 for every pod; m7pr8 shows a
mild cpu block extreme (20.1 vs base p95 18.6), vlsl8's cpu blocks fail the block-
validity policy over the window. Recorded quiet baseline in-window is 0.058–0.116
(per-pod median) vs lab point-mass 0.001288 — the quiet floors differ ~40×. All 10
isolated recorded spikes (>0.5, 0.50–0.93, 11-06 03:35 → 11-08 23:00) are
0.0018–0.0026 in the lab. JSON carries the 15×10 `episode_table` and the 10-row
`isolated_spikes` (lab value at the same pod/tick).

### 3. Real flat control (2026-10-30 → 2026-11-09, all 10 pods, FINAL data)

Pooled: **fraction p_raw > 0.2 = 0.0134**, in-band [0.0012, 0.005] = **0.9771**,
at-point-mass (tol 1e-9) 0.5062; p50 0.001288, p99 0.687, max 0.9895; 22 450 valid
ticks. Per pod: 2245 valid / 2248 scored ticks, first scored tick k+1 = 581,
wall 2.3–2.4 s; per-pod >0.2 fraction 0.0098–0.0236 (vlsl8 0.0236, m7pr8 0.0165 — the
two S4-real pods carry their excursion ticks), in-band 0.9653–0.9849.

### 4. Note + gates

`markdown/part1-limitation-profile.md` (120 lines): setup/yardstick; profile table
(S1–S8, FLAT × FPR/latency/settling/MAE, mean±sd); the two failure modes (reference lag
S2/S6; noise-law contamination S3 pulse pair, S4 bump pair); over-fitting-noise verdict
(white vs structured: S1 0.455 vs 0.470, S3 0.456 vs 0.467, FLAT 0.0017 vs 0.037); S5
gap handling (cold-cycle guard modelled, `min_point_fraction` window gate not — rx is the
permanent cold-cycle case); S7/S8 structural limit; FLAT control (K=11 0.037 FPR /
0.893 in-band, violation 5/5; K=3 0.126/0.734; white 0.0017); caption table (6/7/2/5;
recomputed S4 strike fractions 0.7593/0.6852 vs doc 0.78); **ESS-gate section with the
F2-corrected wording** (gated cycles serve no model, ticks unscored; gate-off scenarios
score 1289 ticks not 1872; S1 714 scored / 44.9% gated / 45.2 h stale; gate-on vs
gate-off FPR compares different scored populations — no ranking without matched-tick
analysis); S4-real verdict (partial 2/10, with the table + raw-metric interpretation);
real flat control; limits; reproduction commands.

Gates: `pytest tests/test_harness_*.py tests/test_plotting_*.py -q` → 166 passed, 0
skipped (28 new `test_harness_real` + 9 new `test_harness_config` missing-key
parametrizations `real.*` ×8 + `flat_control.point_mass_tol`); `ruff check` clean on
`src/refstudy/harness src/refstudy/plotting scripts/run_part1.py tests/test_harness_*.py
tests/test_plotting_*.py`; `ruff format --check` clean; `grep -rn "solo_mode|sys.path"`
over harness+plotting empty; `git diff --check` clean.

### 5. Wall times

pod-1 serial 2.33 s; projected total 23.3 s vs 3600 s budget (restricted window NOT used);
10-pod pool (≤4 workers) 10.1 s; stage wall 11.2 s.

### 6. Deviations

- `flat_control.point_mass_tol: 1.0e-9` added (measurement detail: exact-float
  point-mass equality holds only for quantized record sizes; recorded in the JSON, not a
  tuned threshold).
- Verdict applied at fleet level per the card 3.1 rule sentence ("≥fleet_min_pods pods
  …"); `episode_verdict` still reports the per-pod counts.
- `results/part1-s4real.json` `git_head` is `35fba07` (HEAD at run time; Commit 3
  `44a1f99` is this stage's commit). `results/part1-profile.json` (Commit 2) still carries
  `git_head 5d657f8` — not re-run (stage-3 does not touch scenario code).
- `episode_table` (15×10) and `isolated_spikes` (10 rows) are extras beyond the card
  minimum, kept for the note's evidence.
- The 2/10-pod burst reproduction is the surprising result of this stage; it is reported
  in the note and here, with the raw-metric cross-check; nothing was tuned.
- Commit path list includes `tests/test_harness_config.py` (9 new missing-key
  parametrizations for the new `real.*` / `point_mass_tol` keys) in addition to the
  card-named paths.
