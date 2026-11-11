# E-A1a — Executor evidence (SOLO-REFM / A1a)

## Slice 1 (S1.1 + S1.2): config + block law port

Date: 2026-11-09 · Executor: RefmEA1aSl1 · Lab HEAD before commit: `6d3c6e0`
(commit under `reference-model-study/`).

### Files (all under `reference-model-study/`)

| Path | Notes |
| --- | --- |
| `config/reference.yaml` | pre-existing untracked file from the failed attempt; reviewed against the card's YAML section (line 34) and the live ConfigMap `deploy/k8s/solo-card6/configmap.yaml` — all mirrored values match (`solo_mode.grid/window`, `validity`, `baseline`, `noise`, `undersampling.min_effective_samples`, `strikes`, `fusion`, `degraded.mandatory_metrics`, `metrics[*]` names/kinds); kept with provenance comments on every mirrored key; `constants.*` provenance re-verified in pinned source (`scan.py:527` `+1e-9`, `scan.py:1302` `anchor = 0.0`, shared `bayesian/common.py:16` `1e-12`, shared `bayesian/short_term.py:191` `_LLR_SAFE_LIMIT = 700.0`) |
| `src/refstudy/reference/__init__.py` | minimal, no exports (later slices add) |
| `src/refstudy/reference/config.py` | 13 frozen dataclasses + `load_reference_config(path) -> RefConfig`; every key via `require` (list helpers for `degraded.mandatory_metrics`, `metrics.entries`, `parity.used_files`); bool-for-number rejected; enum checks on `method`/`model`/`semantics` |
| `src/refstudy/reference/blocks.py` | `BlockSeries`, `BlockCell`, `is_counter_metric`, `build_blocks`, `block_cell` — literal port of `prod:scan.py:459-767` (`_tick_aligned_blocks`) + `prod:scan.py:808-820` (`is_counter_metric`) + `prod:driver.py:1109-1264` (scored-block read semantics, CARD-6B2b) |
| `tests/test_reference_config.py` | every missing key named in the error (51-key parametrize); bool-for-number; mistyped; enum; entries validation |
| `tests/test_reference_blocks.py` | S1.2 hand-computed cases |

### Gates (all from the study dir, `.venv` py3.12 / numpy 2.5.4 / scipy 1.18.1)

1. `.venv/bin/python -m pytest tests/test_reference_config.py tests/test_reference_blocks.py -q`
   → `95 passed in 0.18s` (72 + 23 tests; parametrize-expanded 51+15+… cases)
   Full study suite `pytest -q`: 213 passed, 0 failed, 0 skipped.
2. `.venv/bin/ruff check src/refstudy/reference tests/test_reference_config.py tests/test_reference_blocks.py`
   → `All checks passed!`
3. `grep -rniE 'solo_mode|sys\.path|import analyser' src/refstudy/reference` → empty (exit 1)
4. `git diff --check` → clean (also `--staged` before commit)

### Vectorisation decision (card D-4 / fact 3)

Plain Python loop chosen, NOT `np.bincount(weights=)`:
- `np.floor`/`np.ceil` verified bit-identical to C `math.floor`/`math.ceil` on
  float64 over 200 k random values in the lab venv (0 mismatches; incl.
  `2**53±1`, boundary quotients), so the vectorised form *would* reproduce the
  production per-block sums exactly — but the loop mirrors the production op
  order 1:1 (pair-by-pair Python-float accumulation, D-4) and cannot drift.
- The card explicitly allows the loop ("correctness first"); no fallback
  was needed, it was the primary choice, documented in the module docstring.

### Fidelity cross-check against production (in-process, not a deliverable)

Production `_tick_aligned_blocks` imported under a throwaway script
(`solo_mode.scan` from the pinned DET repo) and compared to the port:

- 8 hand cases (dense chain sum/mean, reset law, 36 s bad pair, coverage
  0.89 vs 0.9, cross-block bad pair, gauge/counter boundary sample, empty
  block, single increment): value, `n_increments`, `first_prev`,
  `last_stamp`, `coverage_fraction`, `max_pair_gap` all equal (max|Δ| = 0.0).
- Fuzz `build_blocks` vs production: 4000 random series (0–120 points,
  ms-rounded stamps, resets, duplicate stamps, both laws, both aggs,
  origins 0/30.5/123, 1–4 blocks): **max|Δ| = 0.0 on every emitted value
  and every attribution field, 0 verdict mismatches**.
- Fuzz `block_cell` vs the production scored read
  (`driver.py` window `[tick−3T, tick]`, `end_inclusive` per law): 3000
  random ticks/series (cutoff for counters, drop_last 0–3 for gauges):
  bit-exact on all emitted cells (37 fully-truncated → `None`, 1080
  not-emitted cells → NaN + verdict code, all matching).

### Behavioural notes (recorded as data, all intentional)

- `is_counter_metric(name, kind)`: `kind` wins when given (`rare_count`
  always counter per fact 3); `kind=None` → production name heuristic
  (suffixes `_total`/`_seconds`, lower-cased).
- Timestamps accepted non-decreasing (duplicate stamps → degenerate pair
  `gap = 0` → `bad_gap`), exactly as production, which has no monotonicity
  precondition.
- `block_cell` returns `None` when the truncated window has no points
  (production `no window data` / `no complete block`); else always a
  `BlockCell` (NaN value + verdict code when not emitted).
- Counter `block_cell` REQUIRES `cutoff_ts` (the as-seen window edge,
  fact-7 replay); `drop_last` is gauge-only and clamped to the number of
  points (YAML `p4.max_drop_last` bounds it in real replay).
- Block with no points at all = `empty`; slot with 0/1 admitted increments
  = `few_increments`; a bad pair marks `bad_gap` even when other pairs in
  the block are admitted (production "INVALIDATES this block").

### Commit

`b588eb6` — `feat(refstudy): add reference config and block law port (A1a slice 1)`
(6 files, explicit `git add`, no A2/A3 paths, no trailers; verified via
`git show --stat` at commit time).

### Deviations

1. Loop instead of `np.bincount` (documented above; card-sanctioned,
   bit-exactness proven by fuzz against production).
2. No other deviations from the card's S1.1/S1.2 contract.

Open issues: none. Slice 2 (noise law / STL-lite / provider, S1.3–S1.5)
NOT started, per dispatch.

---

## Stage 1 (rest): noise law, STL-lite provider, parity harness P0–P2b

Date: 2026-11-09 · Executor: RefmEA1aS1b (S-approved session fallback) · Commit **`21bd3e7`**
`feat(refstudy): add STL-lite provider and noise law with parity P0-P2b (A1a stage 1)`
(17 files under `reference-model-study/`, explicit `git add`, `git diff --cached --check` clean; no B1/A2/A3 path staged).

### Files
`src/refstudy/reference/{noise_law,stl_lite,provider}.py` + `__init__.py` (exports `BlockSeries, build_blocks, block_cell, StlLiteProvider, ReferenceRun, ReferenceProvider, check_no_leakage, load_reference_config`); tests `tests/test_reference_{noise_law,stl_lite,provider}.py`; `tests/parity/{conftest,prod_import,_record}.py` + `test_p{0_config,1_cdf,2_residuals,2a_blocks,2b_build}.py`; `scripts/run_parity.py`; `results/a1a-parity.json`.

### Gates (from `reference-model-study/`, `.venv` py3.12.15 / numpy 2.5.4 / scipy 1.18.1)
| Gate | Result |
| --- | --- |
| `pytest -m "not parity"` excluding B1's in-flight `tests/test_compute_*` | **207 passed, 8 deselected, 0 skipped**, 10.3 s |
| `pytest -m "not parity"` whole tree | 4 FAILED, all in B1's `tests/test_compute_scaling.py` (`test_start_violation_aborts…`, `test_start_without_ac_aborts_immediately`, `test_polluted_flag_after_retries`, `test_ac_loss_mid_run_exits_3…`) — not my files, B1 in flight; not touched |
| `pytest -m parity` (P0,P1,P2,P2a,P2b) | **8 passed, 0 skipped**; via `scripts/run_parity.py --config config/reference.yaml --stage 1`: wall **2.8 s** |
| `ruff check src tests scripts` | `All checks passed!` (my files also `ruff format`ed; B1 files untouched) |
| `git diff --check` | clean (also `--cached`) |
| `grep -rniE 'solo_mode\|sys\.path\|import analyser' src/refstudy/reference` | empty. NB whole-`src/` grep (Acceptance 1) also matches **A3's** `src/refstudy/data/package.py:645,691` (`solo_mode_config` dict key) and `src/refstudy/data/oracle.py:11` (docstring citing `solo_mode/scan.py::_tick_aligned_blocks`) — A3-owned, not mine, not touched |
| `grep -rl 'solo_mode' tests \| grep -v '^tests/parity/'` | empty |
| Negative `parity.production_root` check | ran with a **temporary copy** of the YAML (`/tmp/reference-badroot.yaml`, `production_root: /nonexistent/production`, passed via `run_parity.py --config`; committed YAML never edited): `prod_import.ProductionImportError: parity.production_root is not a directory: /nonexistent/production` on every parity test (errors, not skips); `run_parity.py` exit code **1**; `results/a1a-parity.json` byte-identical before/after (`cmp`). Copy deleted. |

### Parity table (straight from `results/a1a-parity.json`; in-process, tolerance 0)
Provenance: production head `5bcc7f9128d55e38d3c09838b3af0699edc4973b`, shared `942b8807f63e614fe3542ed2ba1268046291bfeb` (== pins); recorded `git status --porcelain`: production `[" M AGENTS.md", "?? analyser/agent-orchestration/", "?? markdown/2026-11-06-solo-dashboard-operations-report.md"]`, shared `[" M AGENTS.md"]`; 8 used-file blob ids recorded, all used files clean; python 3.12.15 / numpy 2.5.4 / scipy 1.18.1.

| Test | Scenario | max\|Δ\| | Counts |
| --- | --- | --- | --- |
| P0 | 29 mirrored YAML keys + metrics `(name,kind)` list vs production `solo_mode` (tick 300) | mismatches `[]` | 29 keys; `constants.*` (gauge_epsilon, phase_anchor, posterior_clamp, llr_limit) all `true` vs pinned source text |
| P1 | `mid_rank_cdf` + `two_sided_surprise` (+ fast `two_sided_p`) vs production, N∈{570,570 tie-heavy,852 heavy-tail,852 tie-heavy} | **0.0** (cdf, p, p_fast) | 11 740 / 11 800 / 12 586 / 12 643 probes each (1 740–2 643 fixed + 10 000 random) |
| P2 | lab `rolling_one_step_residuals` vs production `…_incremental` vs `…_oracle` (912 blocks, bins ≥40 dropped for first 400) | **0.0** (ts and residuals, both) | 864 residuals, equal lengths; 40 forecasts hit the empty-bin trend-only fallback |
| P2a | `build_blocks` vs `scan._tick_aligned_blocks(meta_sink=)`, 48 seeded series (origins 0 and 1794096000; counter/gauge × mean/sum) with empty block, 36–45 s gaps ≥100 s inside block, boundary samples, one reset, `ts=boundary−5e-10` | **0.0** (value, n_inc, first_prev, last_stamp, coverage, max_pair_gap) | 1656 emitted blocks, 0 emitted-set/verdict-prefix mismatches; counter codes `emitted 736, bad_gap 144, empty 40, low_coverage 32, few_increments 8` |
| P2b gauge | 27 cycles of production `build_one` vs lab `StlLiteProvider` (injected fully-empty block 13) | **0.0** on fit window, F state, R state, residual ts/values, 6 served forecasts/cycle; `ess` rel **0.0** | cold cycles [0,1,2] (first + guard-forced), 24 steady; record sizes 521,521,522,528,…,570,570 |
| P2b counter (cpu-like, 1 reset) | same, injected 40 s gap with later stamp ≥100 s in block 13 | **0.0** (same quantities) | same cycle pattern |
| P2b ESS gate | random-walk first window | production `build_one → None`; lab `ess_gate` (ESS 3.84 < 36), no tick has a model | — |

Wall times (JSON `wall_seconds`): P1 0.72 s, P2 0.11 s, P2a 0.03 s, P2b gauge 0.21 s, counter 0.33 s.

### Notes / deviations (all data)
1. **Lab residual cycle rule** is a direct port of `scan.py:1296-1499` + guard geometry (`pfs == pt0−T−Dt`, `pfe == pt0−T−dt`, displacement a whole number of `dt`, every prior-window block emitted); the F/R `population` sum/bin *isclose* checks and the forget-inverse probe are NOT modelled (they only trip on corrupted state, which the lab never produces).
2. **`forget` leaves emptied bins as zero entries** in `bin_sums/bin_counts`, exactly like production (parity compares dicts key-for-key, so this is part of the bit-exactness); unit test compares after dropping zero entries.
3. P2b first-cycle choice: `first_t0 = ceil((origin+T+Dt)/dt)*dt` ⇒ fit window `[origin+1500, origin+172500)` (570 blocks), as card.
4. Negative check done with a temp config copy instead of editing `config/reference.yaml` (equivalent, safer: no restore step). `REFSTUDY_PARITY_CONFIG` env var is how `run_parity.py --config` reaches the tests.
5. `StlLiteProvider.run` also takes an `on_cycle` callback (`CycleReport`: fit window, F/R snapshots, record) used by P2b; `cold_start_t0` is implemented and unit-tested.
6. `bincount` question: unchanged from slice 1 — loop port, P2a 0.0.
7. Test fix recorded: `test_p_within_bounds_random` needed a 1-ulp slack on the `1/N` floor (`0.004999999999999947 < 1/200`) — production float arithmetic, not a port defect (lab == production bitwise per P1).

### Open issues
- Whole-`src/` Acceptance-1 grep hits A3's `src/refstudy/data/package.py` (`solo_mode_config`) — outside this leaf's ownership; Main/A3 decide.
- B1's `tests/test_compute_scaling.py` has 4 failing tests at time of run (B1 in flight).
- Stage 2 (rare-count, chain, pipeline, P3, gold fixture, P4/P4b, doc) NOT started, per dispatch.

---

## Stage 2a — rare-count law, scoring chain, pod pipeline, parity P3 (S2.1 + S2.2)

Commit `2519ee4` — `feat(refstudy): add rare-count law, scoring chain, pod pipeline and parity P3 (A1a stage 2a)` (16 owned paths; explicit `git add`; `git diff --check` clean). NOT done (later slice): S2.3 gold fixture + P4/P4b real data, S2.4 `markdown/reference-port.md`.

### Gates
| Gate | Result |
| --- | --- |
| `.venv/bin/python -m pytest -m "not parity" --ignore-glob='tests/test_compute_*'` | **251 passed**, 10 deselected, 0 skipped, 12.0 s |
| `.venv/bin/python -m pytest -m parity tests/parity` (P0, P1, P2, P2a, P2b ×4, P3) | **10 passed**, 0 skipped, 17.9 s (`run_parity.py --stage 2`: P3 alone 15.6 s of which production 14.8 s, lab 0.72 s) |
| `.venv/bin/ruff check src tests/parity tests/test_reference_*.py scripts/run_parity.py` | clean (`ruff format --check`: only stage-1 `blocks.py:183`, `test_reference_blocks.py:65` differ — untouched) |
| `grep -rniE 'solo_mode\|sys\.path\|import analyser' src/refstudy/reference` | empty (rc 1) |
| `grep -rl solo_mode tests \| grep -v '^tests/parity/'` | empty |
| `git diff --check` | clean |

### Parity table (from `results/a1a-parity.json`; in-process, tolerance 0; provenance heads == pins, now 9 used files incl. `driver.py`)
| Test | Scenario | max\|Δ\| | Counts |
| --- | --- | --- | --- |
| P0, P1, P2, P2a, P2b gauge/counter/ESS-gate | unchanged from stage 1 | **0.0** | as stage 1 |
| **P2b rare_count** | production `build_one(kind="rare_count")` vs `RareCountProvider` (agg `sum` blocks), 27 cycles, injected invalid block 13 | **0.0** on `post_alpha, post_beta, post_rate, total_count, ess, fit_window` | `n_blocks` 569 while the invalid block is in the window, then 570; 0 `None` snapshots; the 6 served ticks/cycle carry the same posterior |
| **P3** (seeded synthetic pod, 11 metrics, 1296 ticks, 14 256 metric-ticks) | lab `run_pod` vs production real `build_one` + `_publish_and_recorrelate` per cycle + real `_score_all_metrics` + `driver.py:1486-1605` transcription per tick | **0.0** for `observed, forecast, residual, p, tilde_p, p_simes, k_eff, S_pod, p_raw, degraded_fraction`; `ess` rel **0.0**; `n_k`, `eligible`, `model_t0`, skip reasons, eligible lists: 0 mismatches | **713 scored** ticks in both (identical set); eligible size ∈ {3, 11} (3 ticks at K=3: the three all-network gaps); `p_simes<α` on **32** ticks (min 6.9e-5); `k_eff` 1.533…1.813 (713 non-trivial); rx/tx_bytes: 71 steady cycles then **48 guard-cold cycles** (indices 72…119, right after the first gap block enters the prior window), cpu/mem 119 steady; wall: lab 0.72 s, production 14.8 s |

### What was built
- `rare_count.py`: `rare_count_fit/surprise` (literal; `k=0⇒1.0`, half-even `round`, NB/Poisson `logsf`, no padding), `RareCountProvider.run/cycle` (refit from scratch every dt cycle on `max(0,round(block_sum))` of the EMITTED fit-window blocks; `ess=n_blocks`; no model if no emitted block), `RareCountRun`, `RareCycleReport`.
- `chain.py`: `strike_count, beta_binomial_tail, metric_is_eligible, simes_p, k_eff, s_pod, ell_of, signed_evidence, markov_matrix, update_posterior, compute_pod_correlation`, `MetricTick`, `TickRecord`, `score_pod`.
- `pipeline.py`: `run_pod(raw, cfg, *, provider, forced_gaps, observed_cells, cold_start_t0) -> PodRun{ticks, records, blocks, runs}`.
- Tests: `test_reference_{rare_count,chain,pipeline}.py` (card S2.1 list: ring k=3/4 with None gaps, `tilde_p` 0/1/4 within 1e-15, Simes K=4 → 0.742 vs K=2 → 0.371, p floor 1/N, quiet fixed point 0.0012881712904713476 ±1e-15 after 250 ticks, p_prev=π, skip keeps posterior, mandatory-metric skip, NB `k=0⇒1.0`, `include_rare_count=false`, `forced_gaps`, chain invariance on a re-wrapped STL-lite `ReferenceRun`, positive branch `p_simes<α` bounded by `rising`).
- P3 files: `tests/parity/{synth_series,prod_runner,test_p3_chain}.py`; P2b extended.

### Deviations from the card (all data / decisions)
1. **`p3.n_ticks` 1008 → 1296** (`config/reference.yaml`, test updated): with the first t0 at tick 582 and ring fill 3, 1008 ticks give only 425 scored ticks; ≥600 (acceptance) needs ≥1184 ticks; 1296 gives 713.
2. **`parity.used_files` + `analyser/solo_mode/driver.py`** (9 files; `Production` gains `.driver`; `test_reference_config` count 8→9): P3 calls the real `driver._score_all_metrics`.
3. **Literal production quirk ported**: a skipped tick before any scored tick persists `p_posterior = 0.0` (`driver.py:1509`), so the first scored tick after warm-up skips has `p_prev = 0.0`, NOT π; π is used only when no tick preceded (unit-tested both ways; P3 confirms against production).
4. `score_pod` has one extra kw-only argument `scored_cells` (carrier of `run_pod(observed_cells=…)`); `MetricTick`/`TickRecord` use `None` (never NaN) for absent quantities so records compare with `==`. `eligible` is a tuple in config order. Unscored-block reasons mapped to production's: `block not aligned` (another block of the 3-block read window is emitted), `no window data` (gauge, no sample), else `no complete block`.
5. Persisted-correlation rule in `score_pod`: for each continuous metric the latest built model's record (also across stale ticks) feeds `compute_pod_correlation`, mirroring `_publish_and_recorrelate` re-derivation per publication (P3 cold cycles exercise stale-record carry-over: 0.0).
6. P3 scenario: shared stamps; network counters get the three gap edits (two samples deleted + third moved to a 37/40.5/44 s pair; later stamp ≥107 s in blocks 1000/1070/1140); cpu +50 % step blocks 1200–1219; rx reset once; shared AR(1) block latent so continuous residuals correlate. Gaps are late ⇒ steady cycles first, guard-cold afterwards.
7. `scripts/run_parity.py` stage 2 lists only `test_p3_chain.py` now (P4 file does not exist yet; S2.3 appends it); table notes include `n_scored`.
8. Ruff-format applied only to new/touched-by-me files (touching `test_p2b_build.py` reformatted two of its stage-1 statements; no semantic change).

### Open issues
- Stage-1 `blocks.py:183` / `test_reference_blocks.py:65` are `ruff format`-dirty (lint clean); left alone.
- P3's production side is a transcription of `driver.py:1486-1605`; its shared-transcription risk is anchored only by P4 (real oracle, S2.3).
- B1's `test_compute_*` excluded from the gate as instructed.

---

## Stage 2b — gold fixture, real-data parity P4/P4b, reference-port doc (S2.3 + S2.4)

Executor RefmEA1aS2b · Lab commit **`ca0fd63`** `feat(refstudy): add gold fixture, real-data parity P4/P4b and reference-port doc (A1a stage 2b)` (7 paths, explicit `git add`, `git diff --check` clean): `scripts/build_gold_fixture.py`, `scripts/run_parity.py` (stage 2 now lists `test_p4_real.py`; compact P4/P4b rows), `tests/fixtures/gold_live_b4xkt.json.gz` (502 054 B, deterministic gzip, sha256 `2e1a4ef7…7d35`), `tests/test_reference_gold_fixture.py`, `tests/parity/test_p4_real.py`, `results/a1a-parity.json` (1.6 MB: verbatim mismatch rows), `markdown/reference-port.md` (70 lines). No `src/` change.

### Gates
| Gate | Result |
| --- | --- |
| `pytest -m "not parity"` (whole tree incl. B1/other leaves) | **452 passed**, 31 deselected, 0 skipped, 18.6 s |
| `pytest -m parity` (31 tests: P0,P1,P2,P2a,P2b×4,P3,P4×10 + summary,P4b×10) | **all passed**, 0 skipped, wall 2 m 06 s |
| `scripts/run_parity.py --stage 2` | P3 + P4 + P4b, ~100 s (P4 alone: 78.6 s for 10 pods, 6.9–9.0 s/pod; budget 15 min / 2 min per pod) |
| `ruff check src tests scripts` | All checks passed (owned files `ruff format`ed) |
| negative `parity.production_root=/nonexistent/production` (temp YAML copy, `--stage 1`) | rc **1** (tests error, never skip); `results/a1a-parity.json` byte-identical before/after (`cmp`) |
| Acceptance 1 | `grep -rniE 'solo_mode\|sys\.path\|import analyser' src/` still hits **A3's** `src/refstudy/data/{oracle.py:11,package.py:645,691}` (docstring/dict key, A3-owned, not touched); `src/refstudy/reference` clean; `grep -rl solo_mode tests \| grep -v '^tests/parity/'` empty |
| Acceptance 5 | Stage-2 commit message differs from the card's "Commit 2" text (this is the dispatched 2b commit; stage 2a was `2519ee4`); no A2/A3 path staged |

### Gold (`test_reference_gold_fixture`, 14 tests, no production, no A3 package)
Live b4xkt last tick (1794198600): blocks rebuilt from `raw_series` == `observed_series` **exactly** for cpu, mem, rx, tx (570 blocks each) incl. counter attribution `n_increments, first_prev, last_stamp, coverage_fraction, max_pair_gap` (equality); F loaded sequentially from `observed_series` → oracle `forecast` and all 570 `baseline_series` rel ≤1e-12; `two_sided_p(sorted(residual_cdf), residual) == oracle p` exactly. (Fixture keeps `block_attribution` only for counters: the gauge reference model has none.)

### P4 — 10 pods, as-seen observed-cell replay
Comparable ticks: **287 of 288** per pod: the last oracle tick 1794198600 lies beyond the packaged raw (`raw_last_ts` 1794198564 < tick; the oracle `last_stamp` 1794198587.8 is not in the package) → no lab tick exists; recorded under `not_comparable`. Replay (fact 7): all 27 148 scored metric-ticks reproduced (**unexplained 0**): counters via `block_cell(cutoff_ts=oracle last_stamp)` (`observed` + `n_increments` + 4 attributions), gauges via smallest `drop_last≤3`. Lag statistics: final data == oracle on 26 470 (97.5 %), lag-explained 678 (counters: 587 with exactly 1 dropped sample, 0→23 976 exact; gauges: 91 with drop_last=1, 2 494 with 0); 4 422 `p None` oracle ticks → `forced_gaps` (4 111 `block not aligned`, 311 `model stale`); of the 4 414 whose final-data cell IS emitted, dropping the last 1–3 samples reproduces "not emitted" for 4 137 (the remaining 277 ≈ the `model stale` race, not data-explainable).

Strict quantities (all comparable ticks, all pods): `observed` 27 148/27 148 equal (0.0), `model_t0` exact, `forecast` rel max **1.05e-15**, `residual` max **1.05e-15**, `ess` rel **2.2e-15**; p-family: `p` abs max 9.7e-14, `tilde_p` 2.8e-17, `n_k`/`eligible` exact, `p_simes` 1.1e-16, `k_eff` rel ≤1.2e-14 (after the prefix), `p_raw == history.p_raw` abs ≤4e-19 (after prefix), `p_raw == p_posterior_raw` (oracle self-check) exact.

**ROOT CAUSE found — NOT in the card's predeclared replay list (Main must rule on this).** The literal replay (as-seen cells + `forced_gaps`, steady cycle machine) FAILS the pass rule after the prefix on all 10 pods (`as_seen` variant kept verbatim in `P4/<pod>.as_seen`; e.g. b4xkt first mismatch tick idx 78: cpu `p` lab 0.5824561403508772 vs oracle 0.5938697318007663; per-pod first mismatch idx 78, k_eff mismatches idx 78…286). Diagnosis: oracle `p` is always a multiple of 1/(2N); the implied record size is **570 until idx 77, then 522 at idx 78 on every one of the 10 pods and on every continuous metric, then 528, 534, … 570 (+6/cycle)** — a **pod-wide cold rebuild of the persisted residual record in the middle of cycle t0=1794135600 (between ticks idx 77 and 78)** with an unchanged `model_t0` (same-cycle rebuild; forecast unchanged ⇒ strict quantities unaffected) — i.e. detector state loss/restart, not a port defect. Hypotheses tried: (a) lab cold at the oracle's first `model_t0` (card variant) → worse (933–1235 mismatches); (b) cold at t0=1794135600 for whole cycle (`cold_start_t0`) → only idx 77 mismatched (4 `p`, 1 `k_eff` per pod: the oracle still scored idx 77 with the PRE-restart record) → (c) **hybrid**: steady run before the restart tick, cold-rebuilt run (cold at that t0) from it (`_hybrid` in the test; `ReferenceRun` log concatenation, no `src/` change).
Restart detection is oracle-only arithmetic (`_find_restart`): first tick whose continuous `p` is a multiple of 1/(2·522) but not of 1/(2·570) (522 = 570 − `min_fit_blocks`), giving idx 78 / t0 1794135600 for all 10 pods; no lab output is used to find it. With it: **0 mismatches after the 48-tick prefix on all 10 pods** (table below). I consider this an environment-event replay of the same class as `forced_gaps` (not a tolerance change), but the card did not list it: **the literal card pass rule is met only with this additional replay**; the un-replayed `as_seen` numbers are recorded and fail.

| pod | comparable | forced gaps | replay unexpl. | strict mism. | p-family after prefix (restart replay) | p-family in prefix (sum over quantities) | w/o restart replay: p-family after prefix | cold@first-t0 variant; wall s |
|---|---|---|---|---|---|---|---|---|
| b4xkt | 287 | 425 | 0 | 0 | **0** | 0 | 1003 (first idx 78) | -; 7.1 |
| mjnlq | 287 | 403 | 0 | 0 | **0** | 51 | 785 (first idx 0) | 933 after / 288 prefix; 9.0 |
| rzpzm | 287 | 451 | 0 | 0 | **0** | 7 | 1012 (first idx 0) | 1161 / 249; 9.0 |
| hcfj7 | 287 | 390 | 0 | 0 | **0** | 0 | 1080 (first idx 78) | -; 7.1 |
| vlsl8 | 287 | 711 | 0 | 0 | **0** | 0 | 724 (first idx 78) | -; 6.9 |
| 2vwwd | 287 | 362 | 0 | 0 | **0** | 0 | 1010 (first idx 78) | -; 7.2 |
| 7gjdg | 287 | 407 | 0 | 0 | **0** | 44 | 1088 (first idx 1) | 1142 / 264; 9.0 |
| c5bdh | 287 | 469 | 0 | 0 | **0** | 10 | 1021 (first idx 0) | 1101 / 264; 9.0 |
| m7pr8 | 287 | 405 | 0 | 0 | **0** | 13 | 1121 (first idx 0) | 1235 / 319; 9.0 |
| qsv2m | 287 | 399 | 0 | 0 | **0** | 0 | 1001 (first idx 78) | -; 7.2 |

Prefix content (allowed ≤48 ticks): `eligible/tilde_p/n_k` at idx 0–2 (ring fill from pre-window ticks: the lab computes ticks before the oracle window from final data and has no as-seen gaps there), `p_simes`/`k_eff` at idx 0–2, and the `p_raw` posterior-memory tail (≤ idx 21, max |Δ| 4.4e-4 on mjnlq at idx 0). The card's cold-start variant (`cold_start_t0 = oracle first model_t0`, reported for pods with a non-empty prefix) does NOT improve (it wrongly cold-starts the first cycle); kept as data.

### P4b (report-only; final-data lab `p_raw` vs recorded P3 store)
Per pod common ticks 862–1006; equal (abs ≤1e-12): 329–514; mismatching 439–677 in 12–19 intervals; burst window 2026-11-06 01:15–02:25Z: 15 mismatching ticks (9 on vlsl8); outside the burst: Δ ≤1e-9 on 103–156, ≤1e-6 on 136–216, ≤1e-3 on 159–281, ≤1e-2 on 7–22, >1e-2 on 13–42 per pod (max 0.93); threshold-0.2 crossings: p3≥0.2>lab on 4–20 ticks per pod, lab≥0.2>p3 on **0** ticks anywhere. Not interpreted here (A1c); these are final-data lab runs from the 2026-10-30 data start (no ingest-lag replay, no restart replay, lab record state from t=0 not from the live detector's history).

### Facts 1–9 on the live data
Held: facts 1, 2 (record 522→570 observed on the live oracle after the restart), 3 (blocks 0.0 incl. attribution, gold), 5 (rare-count metrics required: all 11 metrics compared, K=2…11), 6 (gold exact), 7 (lag replay exact, 0 unexplained over 27 148 metric-ticks), 4/8/9 exercised through P3/P4. New: the restart/cold-rebuild event above (not in facts 1–9); the oracle's newest tick can lie beyond the packaged raw (1/288 not comparable).

### Deviations from the card
1. P4 pass uses the extra restart replay (hybrid run) — see above; literal variant recorded and failing.
2. `build_gold_fixture.py`: the gauge `reference_models` entry has no `block_attribution`; kept only where present.
3. `test_p4_real.py` is 661 lines (ruff-formatted); P4/P4b per-pod results are cached (`functools.cache`) and written under `P4/<pod>`, `P4b/<pod>`, summary `P4`.
4. `results/a1a-parity.json` is 1.6 MB (verbatim mismatch rows capped at 100 per quantity/pod for the failing as-seen variant).
5. Commit message: the dispatched stage-2b message (card's "Commit 2" text names stage 2 as a whole).

### Open issues
- Main decision: accept restart replay as part of the P4 pass rule (recommended: it is oracle-derived and fully explains 100 % of the post-prefix mismatches) or declare P4 failed.
- A3 `src/refstudy/data/{oracle,package}.py` still trips the whole-`src/` Acceptance-1 grep (A3's).
- Final-tick oracle/raw misalignment: the packaged raw ends 36 s before the newest oracle tick (A3 package timing).
