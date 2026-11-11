# E Completion — SOLO-REFM / A1b

- Date: 2026-11-09. Executor: `RefmEA1bS1`. Card: `evidence/omp-workcards/refm-A1b.md` (incl. S AMENDMENT, within-block dither, binding).
- Lab: `/Users/obenomar/Work/langGraph/appthrust/pipelineml-model-exploratory-work/reference-model-study`.

## Stage 1 — machinery + S1–S4, S6, FLAT (Commit 1)

### 1. Changed files
- `config/scenarios.yaml` — every tunable (timeline, sampling incl. `within_block{mode: dither, half_width: 0.3}`, signals, noise, S1/S2/S3/S4/S6/FLAT).
- `src/refstudy/scenarios/{__init__,config,spec,noise,components,raw,truth,registry}.py` — config loader, per-scenario schema, latent noise + RNG stream layout, structure/events, raw encoder, ground truth, registry.
- `tests/test_scenarios_{config,noise,raw,core}.py`.

### 2. Commands run / results
- Preflight (1.0): `git status --short` = ` M results/a1a-parity.json`, `?? scripts/build_gold_fixture.py` (others' files, untouched); `git log --oneline -3` = `76f4d1c`, `d0e6163`, `2519ee4`; `from refstudy.reference import build_blocks, load_reference_config` → ok.
- `.venv/bin/python -m pytest tests/test_scenarios_*.py -o addopts="" -q` → **108 passed in 1.95 s** (0 skipped, 0 failed).
- `.venv/bin/ruff check src/refstudy/scenarios tests/test_scenarios_*.py` → All checks passed (`ruff format` applied to the same paths).
- `git diff --check` → clean. `grep -rn 'solo_mode\|sys.path' src/refstudy/scenarios` → empty (exit 1).

### 3. Measured (seed 1, regular grid, default YAML)
| scenario | non-emitted blocks | `len(raw[cpu][0])` | events (kind, onset, end) | quiet_mask(0) True | sha256(raw) 2 calls | gen / blocks wall |
|---|---|---|---|---|---|---|
| S1 | 0 | 37441 | – | 1872/1872 | equal (`28aea024…`) | 0.005 s / 0.06 s |
| S2 | 0 | 37441 | drift 1332→None, step 1440→None | 1332/1872 | equal | same |
| S3 | 0 | 37441 | noise_switch 1584→None (regime), pulse 1440→1446, pulse 1776→1782 | 1860/1872 | equal | same |
| S4 | 0 | 37441 | bump 1536→1554, bump 1752→1770 | 1836/1872 | equal | same |
| S6 | 0 | 37441 | drift 1584→None, bump 1728→1746 | 1584/1872 | equal | same |
| FLAT | 0 | 37441 | – | 1872/1872 | equal | same |

`build_blocks(...).value` equals `target` to max rel. 4.4e-16 on all scenarios/signals (both dither mode default and staircase asserted in tests). display_start 1296; origin = 2026-11-01T12:00:00Z (multiple of 1800).

Noise statistics, `latent_noise`, n = 20000 (factor_ar1; φ .5, weights .1/.7/.2; seeds 0–5): variance 0.97–1.03 (all within ±5 %), lag-1 autocorr 0.491–0.512 (within ±0.03 of φ), pairwise corr 0.793–0.809 (target 0.8 ±0.05). `white` (seeds 0–5): variance 0.975–1.017, |lag-1| ≤ 0.017, |pairwise corr| ≤ 0.015. Tests assert seeds 0,1,2.
S3 sd ratio after/before switch (seed 1): cpu 2.865, mem 2.801, rx_bytes 0.917 (asserted 3 ±20 %, 3 ±20 %, 1 ±20 %). FLAT seed 1: mean cpu 24.94 / mem 511.8 / rx 1.497, sd 1.490 / 11.67 / 0.1525.
Dither: mean within-block relative sd of the raw 20 values ≈ 0.167 (U(−0.3,0.3) ⇒ 0.173); staircase mode within-block sd < 1e-9 (tests). Jitter (S1, mean gap 16 s, ms-rounded): all blocks emitted; mean counter block/target ratio 1.0667/1.0668 (16/15 = 1.0667), gauge 1.0000.
Wall time of the whole stage-1 pytest run: 1.95 s.

### 4. Deviations from the card (all recorded)
1. **Counter/gauge law**: `is_counter_metric(name, kind)` returns False for `kind="continuous"` (kind wins), which would make cpu/rx gauges. The registry therefore calls `is_counter_metric(canonical)` (name rule, `_total`/`_seconds` ⇒ counter), exactly as `reference/pipeline.py:79` does for non-rare entries. Result: cpu & rx counters, memory gauge (test `test_cpu_and_rx_are_cumulative_counters_and_memory_is_a_gauge`). The card's `is_counter_metric(name, kind)` wording is not usable as written.
2. `encode_raw` gains a `dither_rng` keyword (S AMENDMENT needs its own RNG stream); stream layout (`noise.spawn_streams`): common, group₀…, eps₀…, jitter, dither. Dither is mean-preserving per block over the block's own in-range samples (gauge sample at `k=20n`, beyond block n−1, is dithered but excluded from re-centring); validated `0 ≤ 2·half_width < 1`.
3. Extra module `src/refstudy/scenarios/spec.py` (component/event/gap schema and validation) added to keep `config.py` small; within the owned directory. Gap-rule parsing (`gaps{signals,period_seconds,duration_seconds,offset_seconds}`) and periodic gap generation are implemented now (the card places S5 in stage 2) and covered by `test_gap_rule_drives_truth_gaps_and_uncomputable_blocks` (78 gaps ⇒ 468 uncomputable rx blocks, codes ∈ {empty, bad_gap}, cpu/mem all emitted); the S5 YAML entry itself is NOT added (stage 2).
4. Module length: `config.py` 217 and `registry.py` 203 lines after `ruff format` (card: ≤ 200).
5. `raw`/`target`/`clean` dicts are keyed by metric SHORT name; `blocks(ref_cfg)` by CANONICAL name (as the card's text says); `Scenario.names` maps short→canonical.
6. `get_scenario(..., ref_cfg=…)`: when `scn_cfg` is None and `ref_cfg` is given, the default YAML is re-validated against that `ref_cfg`.
7. Event ids are generated (`<scenario>-E<i>-<kind>`), not read from YAML. `ScenariosConfig.timeline.origin` (epoch seconds) is derived from `start_utc`.
8. **YAML values changed from the card: none.** Added key `sampling.within_block` per S AMENDMENT; S3 `rx_bytes` key written as `rx_bytes` (card's `rx` shorthand).
9. Staircase mode retained as a config/test sensitivity only (S AMENDMENT).

### 5. Not done
Stage 2 (S5, S7, S8, tx, `test_scenarios_gaps/structural`, `markdown/scenarios.md`) is out of this assignment. Commit hash: see below.

Commit 1: `26acad5` `feat(refstudy): add raw-first scenario generator core (S1-S4, S6, FLAT) with ground truth` (13 files, only owned paths).

## Stage 2 — gaps, structural scenarios, jitter, tx (Commit 2)

Executor `RefmEA1bS2`, 2026-11-09.

### 1. Changed files
- `config/scenarios.yaml` — S5, S7, S8 appended after FLAT (so `list_scenarios()[:6]` of Stage 1 tests stays valid; order S1 S2 S3 S4 S6 FLAT S5 S7 S8); header comment updated.
- `tests/test_scenarios_gaps.py` (6 test functions, 7 cases), `tests/test_scenarios_structural.py` (15 cases), `markdown/scenarios.md` (47 lines).
- `src/refstudy/scenarios/`: NOT modified (Stage 1 already contained gap parsing/generation and tx support).

### 2. Commands / results
- `.venv/bin/python -m pytest tests/test_scenarios_*.py -o addopts="" -q` → **130 passed in 2.45 s** (0 skipped). New files alone: 22 passed.
- `.venv/bin/ruff check src/refstudy/scenarios tests/test_scenarios_*.py` → All checks passed; `ruff format --check` → 14 files already formatted.
- `grep -rn "solo_mode\|sys.path" src/refstudy/scenarios` → empty (exit 1).

### 3. Acceptance-2 table (seed 1, regular grid, 9 scenarios; two `get_scenario` calls)
| scenario | non-emitted (cpu/mem/rx) | `len(raw[cpu][0])` | events (kind, onset, end) | gaps | quiet_mask(0) True | sha256 equal |
|---|---|---|---|---|---|---|
| S1 | 0/0/0 | 37441 | – | 0 | 1872 | yes |
| S2 | 0/0/0 | 37441 | drift 1332→None, step 1440→None | 0 | 1332 | yes |
| S3 | 0/0/0 | 37441 | noise_switch 1584→None, pulse 1440→1446, pulse 1776→1782 | 0 | 1860 | yes |
| S4 | 0/0/0 | 37441 | bump 1536→1554, bump 1752→1770 | 0 | 1836 | yes |
| S6 | 0/0/0 | 37441 | drift 1584→None, bump 1728→1746 | 0 | 1584 | yes |
| FLAT | 0/0/0 | 37441 | – | 0 | 1872 | yes |
| S5 | 0/0/**468** | 37441 | – | 78 (6 blocks each; 390 `empty` + 78 `bad_gap`) | 1872 | yes |
| S7 | 0/0/0 | 37441 | bump 1536→1554 | 0 | 1854 | yes |
| S8 | 0/0/0 | 37441 | bump 1536→1554 | 0 | 1854 | yes |

Wall time of the 9-scenario check incl. 18 generations + blocks: ~4 s wall (process start included).

### 4. Measured
- S5 jitter (seed 1): rx non-emitted = 468 gap blocks ∪ 77 post-gap blocks (`empty` 468 + `bad_gap` 77); the 78th gap ends exactly at the horizon so its `last+1` lies outside `[0,n)`; cpu/mem all emitted. Gap removes 78×119 = 9282 rx samples; both edge samples are kept.
- S7/S8 jitter: all 3 signals all blocks `emitted`; counter block/target ratio within ±3 % of 16/15, gauge within ±3 % of 1 (asserted); mean raw gap 16 ± 0.05 s.
- Hann FFT (4.5 d event-free `clean` prefix, 8× zero padding): S7 peaks at 86400/21600/25200 s and S8 at 86400/10800/9000 s, each within 2 bins on cpu, mem, rx (asserted). S8 sub-daily/daily variance ratio on `clean` components: cpu 3.78, mem 5.56, rx 3.78 (≥ 3 asserted).
- `tx_bytes.enabled: true` with groups `[[0,1,2]]` → `ValueError` naming `noise.groups`; with `[[0,1,2,3]]` → 4 raw series (37441 samples, strictly increasing counter), blocks == target (rtol 1e-9).

### 5. Deviations
1. S5/S7/S8 appended at the end of the YAML (after FLAT), not between S4 and S6: Stage 1 tests assert `list_scenarios()[:6]`.
2. Card says S7/S8 each carry "the S4 bump @240": implemented as a single bump (cpu 25, mem 180, rx 1.0, 18 blocks) at display block 240 (onset 1536).
3. YAML values: S5 cpu/rx daily sine 3.0/0.3 (card shorthand `cpu [[86400,3,0]] rx [[86400,0.3,0]]`); no other value changed. No `src` change.
Commit 2: see below.

Commit 2: `a3f3cfa` `feat(refstudy): add counter-gap, multi-seasonal and sub-daily scenarios (S5, S7, S8)` (4 files: YAML, 2 tests, markdown/scenarios.md).

## Stage 3 — production-shaped 11-metric set (tx_bytes + 7 quiet rare counts), Commit 3

Executor `RefmEA1b3`, 2026-11-09. Card `evidence/omp-workcards/refm-A1b3.md` (D12).

### 1. Changed files
- `config/scenarios.yaml`: `signals.<s>.mirror` (tx_bytes `enabled: true, mirror: rx_bytes`), `noise.groups [[0,1,2,3]]`, new `rare_counts{enabled, packets_per_sample 40.0, names, coupling{rx_packets: rx_bytes, tx_packets: tx_bytes}}`.
- `src/refstudy/scenarios/{config,noise,raw,registry}.py` (spec/components/truth untouched): `mirror` + `RareCountsCfg` parsing/validation (names must equal reference.yaml's 7 rare shorts); `spawn_streams(..., n_counts)` appends the Poisson streams LAST; `make_stamps` / `encode_counts` in raw.py; `Scenario.rare_signals`, `Scenario.chain_raw()`; mirrored signals copy components/events/noise_switch in the registry and in `GroundTruth.Event.signals/params.amplitudes` (tx_bytes now listed on rx events).
- Tests: new `tests/test_scenarios_counts.py` (a–f of the card + legacy-byte test); adjusted `test_scenarios_{config,core,structural}.py` for 4 signals/mirror/rare_counts. `markdown/scenarios.md` §appended.
- Design: mirror = per-signal YAML key (smaller diff than per-scenario `mirror:` blocks); `tx_bytes` still rejects own components/events.

### 2. Commands / results
- `.venv/bin/python -m pytest tests/test_scenarios_*.py -o addopts="" -q` → **165 passed** (0 skipped); `ruff check src/refstudy/scenarios tests/test_scenarios_*.py` clean; `git diff --check` clean.
- Stage-1 bytes: with `tx_bytes.enabled:false`, groups `[[0,1,2]]`, `rare_counts.enabled:false`, S1 seed 1 `sha256(raw)` = `28aea024a5d81ec48ef3a436d0b41a45826526d7d42d56b34576a679a3dd8427` = the stage-1 value (asserted). Enabling tx (new eps stream) leaves cpu/mem/rx latent noise and targets bit-identical (asserted) but moves the later-indexed dither child ⇒ cpu/mem/rx raw dither draws differ from stage 1 when tx is ON (inherent to adding a 4th eps stream before jitter/dither; documented stream order). `rare_counts.enabled:false` ⇒ continuous raw bit-identical to enabled:true (asserted, regular+jitter, S1/S4/S5).
- 9-scenario seed 1, 11 series each, `len(raw[rx_packets][0])`=37441 everywhere; blocks (`agg` mean for continuous, `sum`+rare law for rare): all `emitted` for S1,S2,S3,S4,S6,FLAT,S7,S8; S5: only rx_bytes non-emitted (1404 emitted, 390 `empty`, 78 `bad_gap` = block law); tx/packets/errors/oom all emitted.
- FLAT: packets increment mean/40 = within 3 % (asserted), `sum` blocks ≈ 800 (±3 %); errors/dropped/oom ≡ 0.0.
- S4: burst-block packet sum > 1.4× quiet-block mean for rx and tx, within 15 % of 800·target/level (asserted).

### 3. FLAT K=11 chain through `run_pod(get_scenario('FLAT',seed,n_ticks=N).chain_raw(), cfg)` (include_rare_count true; first scored k+1 = 584; every scored tick has 11 eligible)
REPORTED AS MEASURED, nothing tuned. p_raw over scored ticks:

| N | seed | n scored | median | max | frac > 0.2 | frac in [0.0012, 0.005] |
|---|---|---|---|---|---|---|
| 700 (card smoke) | 1 | 117 | 0.01139 | 0.9895 | 0.2735 | 0.4274 |
| 700 | 2 | 117 | 0.00722 | 0.9895 | 0.2308 | 0.4786 |
| 700 | 3 | 117 | 0.00297 | 0.9895 | 0.2051 | 0.6325 |
| 1872 (full horizon) | 1 | 1289 | 0.03982 | 0.9895 | 0.3499 | 0.3708 |
| 1872 | 2 | 1289 | 0.02017 | 0.9895 | 0.3095 | 0.3972 |
| 1872 | 3 | 1289 | 0.00826 | 0.9895 | 0.2894 | 0.4616 |

**Surprising: the K=11 FLAT control is NOT clean (27–35 % of ticks > 0.2, far above production fixture 0/599 and above the K=3 smoke FPR 0.116).** Diagnosis (diagnostic runs only, not committed, not a tuning of the delivered code): `rx_packets`/`tx_packets` take their Poisson rate from the NOISY block target (card formula `packets_per_sample·target_block/level`; noise sd = 10 % of level, AR(1)), so per-block packet counts are overdispersed (increment var/mean 1.4 vs 1 for pure Poisson) and the production NB rare-count law (α=β=1 prior) gives per-tick `p_tx_packets` as low as 2e-3 → `tilde_p` 6e-6, Simes/S_pod fire. Diagnostic, same seeds with the packets rate held CONSTANT at 40 (pure Poisson, same streams; no structure coupling):

| N | seed | median | max | frac > 0.2 | frac in band |
|---|---|---|---|---|---|
| 700 | 1 | 0.00129 | 0.5308 | 0.0171 | 0.8718 |
| 700 | 2 | 0.00140 | 0.5006 | 0.0171 | 0.8632 |
| 700 | 3 | 0.00132 | 0.9893 | 0.1197 | 0.7692 |
| 1872 | 1 | 0.00129 | 0.9894 | 0.0396 | 0.9015 |
| 1872 | 2 | 0.00129 | 0.9895 | 0.0287 | 0.9022 |
| 1872 | 3 | 0.00129 | 0.9895 | 0.0396 | 0.8875 |

So the delivered K=11 chain result is dominated by the noise coupling of packets to the noisy byte target (a reading of the card's "target block value"). Decision for S/main: keep (card-literal, delivered), or couple packets to the structure (`clean`) rather than the noisy `target` (one-line change in `registry.py`; clean coupling still raises packets in S4 bursts). Not done here: no scope to change the card's formula.

### 4. Downstream impact (NOT touched: outside OWNS)
`tests/test_harness_evaluate.py` and `tests/test_plotting_figure.py` now fail at collection: `harness.yaml` `plot.colors` has no `tx_bytes` (`required config key missing: plot.colors.tx_bytes`, `harness/config.py:163`); and `run_pod({names[s]: raw[s] for s in signals})` there lacks the 7 rare series (must use `Scenario.chain_raw()`, A1c). `Scenario.signals` is now 4 long (cpu, mem, rx_bytes, tx_bytes); `Scenario.names` also holds the 7 rare shorts.

Commit 3: `76451a6` `feat(refstudy): add production-shaped 11-metric set (tx + quiet rare counts) to scenarios` (10 files, only owned paths).

## Stage 3b — packet counts coupled to the noise-free signal (D13)

Executor `RefmEA1b3b`, 2026-11-09. S decision D13.

- Change: `registry.py` packets rate = `packets_per_sample · max(clean[sig], 0) / level[sig]` (was `target`). Updated `config/scenarios.yaml` comment, `markdown/scenarios.md`, `tests/test_scenarios_counts.py` (FLAT increment var/mean within 15 % of 1; S4 burst ratio now from `clean`, burst > 1.4× quiet still asserted; new test: quiet-stretch packet block sums uncorrelated (|r| < 0.25) with the block noise `target − clean`). Determinism and `rare_counts.enabled:false` equivalence tests unchanged and passing.
- `pytest tests/test_scenarios_*.py` → 166 passed; ruff check/format clean on owned paths.
- K=11 chain `run_pod(get_scenario(name, seed, n_ticks=N).chain_raw(), cfg)` (include_rare_count true), `p_raw` over scored ticks, REPORTED AS MEASURED, nothing tuned:

| scenario | N | seed | n scored | median | max | frac > 0.2 | frac in [0.0012, 0.005] |
|---|---|---|---|---|---|---|---|
| FLAT | 700 | 1 | 117 | 0.00129 | 0.5308 | 0.0171 | 0.8718 |
| FLAT | 700 | 2 | 117 | 0.00140 | 0.5006 | 0.0171 | 0.8632 |
| FLAT | 700 | 3 | 117 | 0.00132 | 0.9893 | 0.1197 | 0.7692 |
| FLAT | 1872 | 1 | 1289 | 0.00129 | 0.9894 | 0.0396 | 0.9015 |
| FLAT | 1872 | 2 | 1289 | 0.00129 | 0.9895 | 0.0287 | 0.9022 |
| FLAT | 1872 | 3 | 1289 | 0.00129 | 0.9895 | 0.0396 | 0.8875 |
| S1 | 700 | 1 | 83 | 0.00129 | 0.5340 | 0.0241 | 0.8795 |
| S1 | 1872 | 1 | 732 | 0.07590 | 0.9895 | 0.4768 | 0.4426 |

FLAT equals the earlier constant-rate-40 diagnostic exactly (FLAT's `clean` is constant). S1 N=1872 differs strongly from N=700 (47.7 % of scored ticks > 0.2): S1 has structured signals/seasonality in the later part; reported, not investigated or tuned.
