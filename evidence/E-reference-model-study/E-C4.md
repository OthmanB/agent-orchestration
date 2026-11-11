# C4 — quantile-band plots, calibration/coverage, width-vs-horizon, honesty-vs-cost (Executor evidence)

One section per workcard slice. This leaf (E) owns **S1**: the library part of
Stage 1 of card `refm-C4.md` — `config/refcompare_bands.yaml`,
`src/refstudy/refcompare/{bands,coverage}.py`,
`tests/test_refcompare_{bands,coverage}.py`.  The plotting figures and the runs
on real shards are a LATER slice (needs C2 shards); S1 delivers the pure
library functions, their YAML (required keys) and tests on synthetic quantile
arrays only.  All paths relative to `reference-model-study/` (lab repo
`pipelineml-model-exploratory-work`).

**File-scope deviation (recorded, no gate touched):** the card names a separate
`calibration.py`; the dispatch fixed the owned files to `bands.py` + `coverage.py`
(no `calibration.py`, no `plots.py`, no `run_c4.py`, no `bands_config.py`). The
YAML loader therefore lives inside `bands.py` (alongside the band builders), and
`coverage.py` carries the calibration/PIT/width/skew functions. Because the
loader and the two builders share one module, `bands.py` (317 lines) and
`coverage.py` (301 lines) exceed the card's ~200-line/module guideline. All
behavioural acceptance criteria below are met.

---

## S1 — library + tests (card Stage 1, steps 1.0–1.3)

### 1.0 Preflight

```
$ git log --oneline -3
03734c2 feat(refstudy): add Phase C side-by-side profile, masking probe and flat-control library (C3 slice 1b)
d313f42 feat(refstudy): add Phase C evaluation config and per-unit evaluation (C3 slice 1a)
c74e59e data(refstudy): record B2 CUDA remeasurement (regular-grid input, batched variant), sustainable-pods table and figures
```

C3 Commit 1 / 1b (`d313f42`, `03734c2`) are HEAD ancestors. C1 `TimesFmProvider.
block_bands`, the C1 pipeline and the A1c plotting import cleanly:

```
$ .venv/bin/python -c "from refstudy.refcompare import evaluate, pipeline; \
from refstudy.plotting import QuantileBand, build_figure; \
from refstudy.refcompare import bands, coverage; print('imports ok')"
imports ok
```

```
$ df -h /
Filesystem   Size   Used   Avail Use% Mounted on
/dev/disk3s1s1  461G   419G    43G   91% /
```

(The card's `build_figure`-on-`get_scenario('S4',1,n_ticks=900)` with a synthetic
cpu band and the tx_bytes check is a plotting-slice item; S1 does not build figures.
`build_figure(bands=…)` is consumed by the LATER figures slice, which owns the plot
scripts. The band objects it will consume are what S1 produces and tests.)

### 1.1 `config/refcompare_bands.yaml` + `bands.py` (stub provider, KNOWN quantiles)

`load_bands_config(path, ref_cfg, rc_cfg, run_cfg=None)` is YAML-first; every
required key names itself in the `ValueError`. The loader cross-checks, against
the passed-in C1 configs, that: the report horizons equal `refcompare.yaml
cycle.diag_blocks` (`15min/30min/60min` = 3/6/12, card D-1); the interval pairs
are `hand_off.levels` (the 25–75 `interp_pair` is allowed to be off-grid, since
`QuantileBand.at` interpolates it, card D-2); `signals.table` is the 4 continuous
in `reference.yaml` order; the scope scenarios (when `run_cfg` is given) and the
sweep contexts are run-matrix / refcompare values.

`tests/test_refcompare_bands.py` builds a `TimesFmProvider` stub whose block
``b`` of cycle ``c`` carries per-level values ``10c + 0.5b + (1..9)`` (strictly
increasing in level ⇒ non-crossing, known exactly). It asserts:
- `served_band` row/tick alignment: block `k` ↔ `block_bands[c, k − e_c]` of the
  covering cycle (checked at ticks 25/31/40/90);
- NaN before the first cycle's served range, finite on the first served 6;
- non-crossing + `levels == DECILE_LEVELS`;
- off-grid ticks rejected (`+1.0`, `+0.5` offsets raise `ValueError`);
- `horizon_band` has exactly one tick per cycle at the end of block `e_c + b`,
  and one tick per row at `block_bands[c, b]`; `b` outside `[0, 13)` rejected;
- `QuantileBand.at(0.25) == mean(0.2 row, 0.3 row)` (the `interp` pair), NaN
  rows stay NaN, `at(0.95)` outside `[0.1, 0.9]` raises.

26 parametrised "missing key names itself" cases cover every YAML key.

### 1.2 `coverage.py` (Gaussian + deliberately overconfident stubs, synthetic arrays)

`tests/test_refcompare_coverage.py` (all on synthetic quantile arrays, no model
weights; `N_TICKS = 2000`, `plan_cycles` first_n0 = 240 ⇒ 97 cycles):
- **Calibrated Gaussian** (band σ = obs σ): for all 5 pairs (10–90, 20–80,
  30–70, 40–60 and the 25–75 interp pair) the empirical coverage is within ±3 SE
  of nominal; the below/above miss split is ≈ ½; the PIT histogram passes a
  chi-square against the uniform 1/10 bins (9 dof, p = 0.995);
- **Deliberately overconfident** (band σ = σ/2, i.e. twice too small): the
  80 %-pair undercovers beyond 3 SE of 0.8 (≈0.59 in theory), and PIT mass
  shifts into the extreme bins (obs < q10 / obs > q90);
- **Raw-native index alignment**: a stub whose step-`h` quantile equals the
  observed grid value at `step_grid_index(counter, e_c, per_block, h)` gives
  coverage 1.0 / 0 miss / all-mass in PIT bin 0 for BOTH the counter and the
  gauge branch (the `step_grid_index` ±1 counter offset is load-bearing);
- `width_curve` median relative width on a hand array (incl. NaN-obs dropped);
- `noise_law_widths` `w_stl`/`w_rec`/`ratio` on hand `ReferenceRun`s (a gated
  tick on one side is skipped; a short record ⇒ `n=0`, `None`);
- `skew` sign on an exponential (right-skewed) and its negation, ≈0 on a sine,
  guards on constant / <3 values; `pre_event_mask`; `pit_hist` strictly-below
  counts; `observed_raw_grid` counter + gauge via C1 `to_grid`.

**rx shape is judged empirically (card D-2 wording):** `coverage_*` reports the
miss split and PIT against the observed distribution; `skew` reports the residual
skew separately. No Gaussian assumption is made anywhere — the overconfident and
oracle tests are distribution-agnostic by construction (the oracle is exact, the
Gaussian test asserts coverage/PIT, not shape).

### 1.3 (plots) — deferred to the figures slice, per dispatch

The dispatch's S1 file list contains no `plots.py` / `test_*.py` plot tests; the
matplotlib figures and their Agg tests (`c4-bands-*`, `c4-width-vs-horizon`,
`c4-reliability`, dashed `w_stl`) are the LATER slice that needs C2 shards and
the plot scripts. S1 ships the pure library only.

### 1.4 (E smoke, real weights, ≤5 min) — NOT run in this slice

Step 1.4 requires the C2 stage-2 `throwaway/c2-smoke` shards and the
`min_served`/small-offset overrides to run `coverage_raw` + `horizon_band` + one
figure end-to-end with real weights. That is explicitly the later figures slice
(needs C2 shards). No GPU, no CPU model run was executed here. No coverage
numbers are printed in this section.

### Gates

```
$ .venv/bin/python -m pytest tests/test_refcompare_*.py -q        # C1/C2/C3/C4 refcompare suites
======================= 262 passed in 108.22s ========================   # 0 skipped, 0 failed
$ .venv/bin/python -m pytest tests/test_refcompare_bands.py tests/test_refcompare_coverage.py -q
49 passed in 1.4s
$ .venv/bin/ruff check src/refstudy/refcompare/bands.py src/refstudy/refcompare/coverage.py \
    tests/test_refcompare_bands.py tests/test_refcompare_coverage.py
All checks passed!
$ grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare   # (empty)
$ grep -rn "print(" src/refstudy/refcompare   # (empty)
$ git diff --check   # clean
```

No change under `plotting/`, `harness/`, `reference/` — `git status --short` at
commit time lists exactly the 5 owned paths.

### Commit

```
$ git log --oneline -1
9955703 feat(refstudy): add quantile-band and coverage calibration library (C4 slice 1)
```

(5 files, 1156 insertions: `config/refcompare_bands.yaml`, `bands.py`,
`coverage.py`, the two test files.)

---

## Fix C4a — RV-C F7 + F8 (dispatch 2026-11-10, AUTONOMY WINDOW)

Owns the same 5 S1 paths plus the evidence note. RV-C findings: **F7**
served-only coverage cannot establish the three diagnostic horizons
(`coverage_block` always consumed `served_band`; `coverage_raw`'s block
selector picked offsets 6–11, so b=3/12-only probes yielded **0 samples**) and
**F8** the width normalisation returned the median of per-cycle ratios, not
the declared `median(width) / |median(obs)|`, and dropped the absolute width.

### F7 — explicit per-(cycle, horizon) evaluation

- `coverage_block(provider, obs_blocks, mask, pairs, *, horizon=None)` and
  `coverage_raw(q_raw, obs_grid, cycles, counter, mask_blocks, pairs,
  per_block, *, horizon=None)`: `horizon=b` evaluates the q10–q90 band AND the
  q25–q75 interpolated band against that `(cycle, b)`'s own observed block /
  raw indices and masks, counting **ALL** eligible (cycle, horizon) pairs —
  not only the latest-serving forecast.  Block case: cycle `c`'s band row
  `block_bands[c, b]` is judged against observed block `e_c + b`; raw case:
  the `per_block` steps of block `b` (h = b·PB + s) against
  `step_grid_index(counter, e_c, PB, h)`.  Out-of-horizon offsets and
  `b ∈ [0, H)`/`[0, H//PB)` bounds raise `ValueError`.
- The pooled served-band function still works but every result now carries a
  `band` field: `pooled_served_30_55min` (constant
  `refstudy.refcompare.bands.POOLED_SERVED_LABEL`) or `f"horizon_b{b}"`, so
  the pooled 30–55 min result can never be reported as 30-min coverage.
  Each pair entry also carries `interp` (True for the 25–75 interpolated
  band, False for the four stored-decile pairs, card D-2).
- `config/refcompare_bands.yaml`: `horizons_min` comment updated — 3/6/12 are
  the per-horizon evaluation offsets; the pooled band is a separate, labelled
  calibration.  No new YAML key (the horizons were already required and
  cross-checked against `cycle.diag_blocks`).

### F8 — width statistics

`width_curve` (median-of-per-cycle-ratios, no absolute width) is replaced by
`width_statistics(bands, obs) -> list[dict]` (one entry per offset `b`),
emitting the three distinct quantities over the finite cycles:
`median_width` (absolute `median(width[:, b])`), `ratio_median_level`
(the declared card statistic `median(width[:, b]) / |median(obs[:, b])|`),
and `sensitivity_median_of_ratios` (the old median-of-per-cycle-ratios, kept
only under a distinctly different name).  A zero median observed level is
handled explicitly: `ratio_median_level = None` + `zero_median_level = True`
(the sensitivity is `None` too — per-cycle width/0 is not finite).  NaN obs
are dropped per offset.

### Tests (synthetic arrays only; deterministic; no model weights)

- **Gaussian calibrated / overconfident tests kept** (`test_gaussian_
  calibrated_coverage`, `test_gaussian_overconfident_undercovers` unchanged
  apart from the new `band == pooled_served_30_55min` assertion); raw-native
  oracle test now also asserts the pooled label.
- **Per-horizon, nonstationary, distinguishable**: a drift + 47→59-block
  oscillation observed level with band centres LAGGED by `b` blocks and fixed
  half-width 10 (cycle-c and offset-b dependent coverage).  At b = 3/6/12:
  `n` == independent hand count of eligible cycles (330/330/329 on the 2000-
  tick plan), 80 %-pair AND 25–75-interp-pair coverage each equal an
  independent hand count from `block_bands` + the observed series (no call
  into the coverage functions), measured coverages ≈ 0.936 / 0.339 / 0.204 —
  three distinct, non-degenerate values; `interp` flag False/True as
  declared; raw-native per-horizon: exact oracle gives coverage 1.0 with
  `n == #eligible cycles × PB` for counter AND gauge; bad offsets (13, −1,
  13.0, True) raise; pooled vs horizon-b=6 coexist on the same data with
  different `n` and different coverage.
- **Width behavioural test** on the review's example: widths `[10, 20]` over
  observed levels `[1, 100]` → `median_width = 15`,
  `ratio_median_level = 15 / 50.5 = 0.297029702970297` (the card's declared
  statistic), `sensitivity_median_of_ratios = median(10/1, 20/100) = 5.1` —
  the two statistics distinguished, not enshrined.  Plus a two-offset case:
  zero median level → `ratio_median_level is None` + `zero_median_level is
  True`; NaN-obs cycle dropped; shape guard raises.

### Gates

```
$ .venv/bin/python -m pytest tests/test_refcompare_bands.py tests/test_refcompare_coverage.py
58 passed in 1.15s                                  # 0 skipped
$ .venv/bin/python -m pytest tests/test_refcompare_*.py
(all refcompare suites) 292 passed in 179.2s        # 0 skipped, 0 failed
$ .venv/bin/ruff check src/refstudy/refcompare/bands.py src/refstudy/refcompare/coverage.py \
    tests/test_refcompare_bands.py tests/test_refcompare_coverage.py
All checks passed!
$ grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare   # (empty)
$ grep -rn "print(" src/refstudy/refcompare                  # (empty)
$ git diff --check                                       # clean
```

Commit (4 files, 417 insertions, 44 deletions):

```
$ git log --oneline -1
594664b fix(refstudy): per-horizon band coverage and width statistics (RV-C F7 F8)
```

Note: `width_curve` was removed (no in-repo consumers other than the replaced
test; `scripts/` had none).  Stage-2 (`run_c4` consumer, a later slice) should
call `coverage_block(..., horizon=b)` / `coverage_raw(..., horizon=b)` with
`b` from `BandsConfig.horizons_min` and `width_statistics` for card D-4;
the returned `band` label is the reporting key.

---

## S1b — plot figure functions + tests + CPU smoke (card Stage 1, steps 1.3–1.5)

Owns `src/refstudy/refcompare/plots.py` and
`tests/test_refcompare_plots.py` (the C4 slice-1b dispatch; the dispatch
replaces the card's `calibration.py`/`refcompare_cal.yaml` names with the
committed `bands.py` + `coverage.py` + `refcompare_bands.yaml` — this slice
follows the code on disk).  NOT owned (later slice, stage 2): `run_c4.py`,
the C3-band `c4-bands-*` figures (those reuse
`refstudy.plotting.build_figure(..., bands=)`), the tables, the real-shard
figures, the note.

`plots.py` (4 figure builders, Agg `Figure` + `FigureCanvasAgg` only, no
pyplot state; D-A vocabulary only — "Decisive-normal boundary" /
"Decisive-anomaly boundary" / "undecidable"; thresholds always passed in):

- `plot_horizons(bands, obs_blocks, *, T, origin, horizons_min, min_height_px, dpi, title)`:
  card D-5 `c4-horizons-*` — one column per plotted signal (cpu/mem/rx_bytes),
  one row per report horizon (15/30/60 min); row `m` plots the observed block
  series (the full pod block grid) with the `horizon_band` at
  `b = horizons_min[m]`: outer 10-90 / inner 25-75 filled bands + dotted
  median.  `bands[s][b]` per (signal, horizon).
- `plot_real_bands(bands, blocks, p_raw, *, fans, alpha_threshold,
  delta_threshold, grid_seconds, min_height_px, dpi, title)`: card D-5
  `c4-bands-realflat-*` (own Agg figure, not `build_figure`) — row 0 per
  signal: blocks + served band; one row per fan cycle label (`fans[s][label]`
  = `[steps, 9]` unscaled raw-native quantiles ahead of the fit end, one step
  per grid point); bottom p_raw strip (log-y): trace, undecidable band
  shaded, both boundary lines with the exact labels and the three-class
  legend.
- `plot_width(curves, stl_widths, *, block_minutes, min_height_px, dpi, title)`:
  card D-5 `c4-width-vs-horizon` — `ratio_median_level` (the declared card
  statistic of `width_statistics`) vs minutes ahead (`b * block_minutes`),
  one curve per (scenario, signal); the per-scenario `w_stl` medians drawn
  dashed; zero-median-level offsets skipped.
- `plot_reliability(coverage, *, min_height_px, dpi, title)`: card D-5
  `c4-reliability` — nominal vs empirical coverage per signal (the
  `coverage_block`/`coverage_raw` result at one horizon, card D-2 pairs incl.
  the 25-75 interp pair), drawn against the nominal diagonal.

All four enforce `min_height_px` at `dpi` (`_height_px` raises on a figure
shorter than the card `plots.min_height_px`); the unknown-signal, missing-key
and shape guards raise `ValueError` naming the offender.  The `BandLevels`
frozen dataclass carries the card D-2 overlay levels (outer 0.1/0.9, inner
0.25/0.75 interp, median 0.5).

### 1.3 Tests (Agg, tiny inputs, no model weights)

`tests/test_refcompare_plots.py` — 7 deterministic tests on a known-quantile
stub provider (`q[c, h, i] = 10c + 0.1h + i`, non-crossing) and a 40-block
pod grid:

- `plot_horizons`: the PNG is written (non-empty file); pixel height > 800;
  exactly one filled quantile band per panel (the two
  `FillBetweenPolyCollection` of outer+inner, each spanning the
  one-tick-per-cycle band axis); the three horizon row titles
  `15 min (b=3)` / `30 min (b=6)` / `60 min (b=12)` all present; unknown
  signal and missing horizon `b` rejected.
- `plot_real_bands`: PNG written; height > 800; the three top-row band
  panels each carry the two-band fill; the fan row (`raw-native fan:
  first`) present; the log-y p_raw strip present with the exact D-A
  vocabulary — "Decisive-normal boundary (0.2)" and
  "Decisive-anomaly boundary (0.8)" as strip texts, the
  `undecidable [0.2, 0.8]` legend patch, and the three-class legend — and
  NO "false-positive" wording anywhere in the figure (checked over every
  title/text/axis label/legend text); bad fan shape `[4, 8]` and
  `alpha >= delta` rejected.
- `plot_width`: PNG written; height > 800; the per-scenario dashed `w_stl`
  reference lines present (2, with the passed-in medians); the 6 scenario x
  signal curves drawn; zero-median-level offsets produce NO curve; unknown
  signal rejected.
- `plot_reliability`: PNG written; height > 800; the legend is
  `nominal` + one line per signal with its `n`; 5 pairs per signal
  (0.1-0.9 … 0.25-0.75, nominal x-values 0.8/0.6/0.4/0.2/0.5); a
  non-positive `n` rejected.

### 1.4 E smoke (real weights, CPU, the C2 stage-2 smoke shards)

`throwaway/c4_s1b_smoke.py` (gitignored; `throwaway/c2-smoke/shards`,
`syn:S1:1:240:multi`, real TimesFM-3 weights on device cpu): the test-only
`min_served=0` override for the 3-cycle smoke shards; the C3 step-1.4
`hcfg_common` offset does not apply — it only moves the `evaluate_records`
p_raw warmup, and the band builders / coverage functions consume the shard
forecasts and the pod blocks only.  `coverage_raw` + `horizon_band` + one
figure end-to-end; the three coverage numbers printed (NOT asserted):

```
$ .venv/bin/python throwaway/c4_s1b_smoke.py
shard syn:S1:1:240:multi: C=3 H=260 K=9 ctx=240 first_n0=588 n_ticks=1872 wall_s=0.7
     cpu: raw-native b=6 n=60 cov=0.867 | block pooled n=19 cov=1.000 | block b=6 n=3 cov=1.000 | pit=[0.133..., 0.167..., 0.15, 0.133..., 0.083..., 0.183..., 0.083..., 0.067..., 0.0, 0.0]
     mem: raw-native b=6 n=60 cov=0.833 | block pooled n=19 cov=1.000 | block b=6 n=3 cov=1.000 | pit=[0.067..., 0.167..., 0.133..., 0.083..., 0.083..., 0.05, 0.1, 0.117..., 0.1, 0.1]
rx_bytes: raw-native b=6 n=60 cov=0.850 | block pooled n=19 cov=0.947 | block b=6 n=3 cov=1.000 | pit=[0.15, 0.117..., 0.133..., 0.1, 0.167..., 0.083..., 0.067..., 0.067..., 0.117..., 0.0]
HEADLINE cpu 30-min 80% coverage: raw-native=0.867 (n=60) | pooled served-band=1.000 (n=19) | horizon b=6=1.000 (n=3)
figure: .../throwaway/c4_s1b_smoke_horizons.png 283528 bytes, height 1530 px, total wall_s=1.3
smoke ok
```

(The tiny 3-cycle smoke plan: the per-horizon b=6 population is 3 cycles —
one eligible (cycle, horizon) pair each — so `n=3` and the coverage 1.000
here is a sample-size artefact of the smoke, not a calibration claim; the
raw-native b=6 population is 3 cycles x 20 steps = 60.  The pooled
served-band offsets 6..11 give `n=19` on the served blocks.  E judges the
headline on the full 2 d scope in stage 2.)

### Gates

```
$ .venv/bin/python -m pytest tests/test_refcompare_plots.py -q
7 passed in 2.3s                                            # 0 skipped, 0 failed
$ .venv/bin/python -m pytest tests/test_refcompare_*.py -q  # ALL refcompare suites
303 passed in 182.8s                                        # 0 skipped, 0 failed
$ .venv/bin/ruff check src/refstudy/refcompare/plots.py tests/test_refcompare_plots.py
All checks passed!
$ grep -rniE 'print\(|solo_mode|sys\.path' src/refstudy/refcompare   # (empty)
$ git diff --check                                           # clean
```

Commit:

```
$ git log --oneline -1
1252182 feat(refstudy): add Phase C calibration and band figure functions (C4 slice 1b)
```

(2 files: `src/refstudy/refcompare/plots.py`,
`tests/test_refcompare_plots.py`; the smoke script and its PNG stay
gitignored under `throwaway/`.)


---

## Stage 2.1 — `--stage tables` on the 118-shard store (card Step 2.1, dispatch C4-S2a)

Owns `scripts/run_c4.py`, the `inputs.c3_profile` / `inputs.c3_real_flat` keys
added to `config/refcompare_bands.yaml` (+ the two new "missing key names
itself" cases in `tests/test_refcompare_bands.py`), `tests/test_refcompare_run_c4.py`
and the two results files.  `run_c4 --stage tables` verifies every scope shard
digest (C3 `evaluate.verify_shard`, P3), then builds the card D-2/D-3/D-4
tables for the YAML scope (FLAT/S1/S3/S4/S7 × seeds 1–3 × {uni, multi} at
2 d = 11520 pts; the sweep (1 d = 5760, 1 h = 240) seed 1 on FLAT/S1; real
b4xkt/m7pr8 × {uni, multi}) — 42 scope units out of the 118 frozen shards
(RV-C2), copied `class_join` from C3 stage 2 (`results/c3-profile.json`,
`results/c3-real-flat.json`, both committed in `9277c0d`; a missing key stops
the stage).  `--stage figures`/`all` are rejected with a clear "LATER slice"
error (card D-5 figures land next).

### Preflight

```
$ git log --oneline -2
7fc2709 feat(refstudy): add candidate-B measurement library, candb config and measure tests (CB 4.1)
9277c0d data(refstudy): record Phase C accuracy profile, masking probe and real flat control

$ .venv/bin/python scripts/run_c4.py --config config/refcompare_bands.yaml --stage tables --max-minutes 18
...
03:16:08 | INFO | __main__ - tables: 42 units -> results/c4-calibration.json / results/c4-calibration.csv
         (stage wall 238.7 s; 0 absent cells)
03:16:08 | INFO | __main__ - stage(s) tables done in 240.8 s     (exit 0)
```

Verify: `42/42` scope shards ok, `digest_rtol 1e-06` (the eval-config `profile.
digest_rtol`), every context/forecast digest rebuilt past-only — the run
recorded `verify: {all_ok: true, n_shards: 42, rtol: 1e-06}` in the JSON.
`results/c4-calibration.json` carries `c3_sha256` (c3-profile
`303332ea2a09d48a…`, c3-real-flat `e3f2154ec6bef54e…`), the C3 `git_head`
(`1252182…` for both files) and this run's `git_head` `7fc2709…`.

### Headline 30-min (b = 6) coverage — the `0.1–0.9` pair (nominal 0.8),
`all_quiet`, seed-mean ± nothing shown (per-seed in the JSON), per signal/mode

```
raw-native (model vs raw grid - Q2 proper):
scn/mode            cpu        mem   rx_bytes    tx_bytes
FLAT/uni           0.798      0.798      0.793      0.791
FLAT/multi         0.798      0.803      0.795      0.795
S1/uni             0.814      0.803      0.817      0.817
S1/multi           0.807      0.798      0.804      0.802
S3/uni             0.797      0.799      0.809      0.807
S3/multi           0.792      0.792      0.805      0.803
S4/uni             0.805      0.799      0.800      0.795
S4/multi           0.804      0.803      0.798      0.797
S7/uni             0.812      0.801      0.812      0.812
S7/multi           0.806      0.798      0.806      0.804

block hand-off (model vs detector block - what the chain sees):
scn/mode            cpu        mem   rx_bytes    tx_bytes
FLAT/uni           1.000      1.000      0.994      0.984
FLAT/multi         1.000      1.000      0.994      0.981
S1/uni             0.997      1.000      0.980      0.975
S1/multi           1.000      1.000      0.977      0.975
S3/uni             0.980      1.000      0.984      0.973
S3/multi           0.975      1.000      0.987      0.978
S4/uni             1.000      1.000      0.994      0.987
S4/multi           1.000      1.000      0.994      0.984
S7/uni             0.976      1.000      0.965      0.959
S7/multi           0.981      1.000      0.975      0.969
```

Raw-native is well calibrated at the 80 %-pair on every scenario × mode
(0.79–0.82, ≈ the 0.8 nominal; FLAT uni per pair: 0.8→0.798, 0.6→0.599,
0.4→0.401, 0.2→0.204, interp 0.5→0.501 — the full five-pair curve lands on
its nominal diagonal).  The block hand-off is *conservative* (the p50-block
forecast plus the comonotone mean-of-quantiles band, C1 D-4 upper bound).
The pooled served-band result is carried separately under
`band="pooled_served_30_55min"` (RV-C F7) and is NOT reported above as a
30-min value.

### Width / honesty-vs-cost (card D-4)

Width curves `b = 0…12` are in the JSON per unit/signal/resolution
(`width_statistics`: absolute `median_width`, `ratio_median_level`, per-cycle
sensitivity).  FLAT seed-mean at b = 6:

```
signal      resolution  median_width      ratio_median_level
cpu         raw         11.87            0.475
cpu         block       11.87            0.474
mem         raw/block   238.6 / 238.6    0.466
rx_bytes    raw/block   0.7735 / 0.7734  0.517
tx_bytes    raw/block   0.7771 / 0.7771  0.517
```

Honesty table (FLAT, gate off; gate on identical on FLAT since nothing gates
there, seed-mean; `n` = matched ticks):

```
signal      n     w_stl        w_rec        w_rec/w_stl  band_w(b=6)  band_wider
cpu       757    4.14±0.15    3.99±0.20    0.962        11.85        True (2.8×)
mem       757   32.9±1.2     31.0±1.3      0.944       238.6         True (7.3×)
rx_bytes  757   0.409±0.025  0.399±0.021   0.978        0.774        True (1.9×)
tx_bytes  757   0.411±0.017  0.397±0.019   0.966        0.777        True (1.9×)
```

`band_wider=True` on all 24 FLAT (signal × mode × gate) cells: the 30-min
band is 1.9–7.3× the STL-lite noise-law interval — the honest price.
S1 shows where the as-deployed ESS gate restricts: w_stl gate-on has
n = 408/442/456/460 (cpu/mem/rx/tx) vs 757 gate-off, w_stl ≈ unchanged.

**S3 before/after the noise-switch (block 1584, card D-4):**
cpu band b6 width 12.15 → 16.45 (ratio 1.354) vs STL record width
4.01 → 5.60 (ratio 1.397) — the band widens IN STEP with the STL record
(regime-aware, matching ratio).  mem band 238.6 → 249.9 (1.047) vs STL
32.90 → 43.65 (1.327) — the band does NOT widen as much as the record there.

**rx residual skew** (card D-2, the rx shape judged empirically): FLAT
uni −0.114 / multi −0.099; S1 uni −0.069 / multi −0.138; S4 multi +1.334
(burst regime).  Miss splits agree with the shape (S4 rx raw b6:
miss_below 0.197 / miss_above 0.209, PIT near-uniform on FLAT:
[0.109, 0.095, 0.097, 0.102, 0.091, 0.103, 0.105, 0.099, 0.102, 0.096]).

### D-6 three-class join (copied verbatim from C3 stage 2; observed
co-variation only, no causal claim — E judges)

```
unit            cpu-block-b6-cov  undecided_occ  decisive_occ  frac_normal  fresh-model-noise>0.8
FLAT/uni         0.995            0.0119          0.0026       0.9854       mean 2.0/755 ticks
FLAT/multi       0.992            0.0137          0.0031       0.9832       mean 2.3
S3/uni           0.909            0.0612          0.3814       0.5607       mean 280.3
S3/multi         0.914            0.0576          0.3732       0.5691       mean 274.3
real b4xkt/uni   0.011 (n=190)    frac_undecided 0.0000, frac_decisive 0.0000, frac_normal 1.0000
real b4xkt/multi 0.011 (n=190)    (same)
real m7pr8/uni   0.016 (n=190)    (same)
```

The synthetic S3 co-varies as expected (low band coverage ⇔ high
decisive-anomaly occupancy, the mechanism count dominated by
`fresh-model noise` >0.8: 280/755).  **Surprise (reported, not tuned):**
on the REAL flat pods the CPU *block* band is badly miscalibrated, while
the CPU *raw-native* coverage stays near-nominal and mem/rx/tx block
coverage over-covers.  The chain still calls both pods `calm` (C3 fleet)
because it scores on its empirical residual record, not the model band (P2)
— the miscalibrated band is exactly the calibration/honesty diagnostic the
card exists to surface.

> **SUPERSEDED (RV-Phase-E F11, 2026-11-11):** the numbers quoted in the
> stage-2 paragraph above — CPU block "80 %-pair coverage 0.011–0.016" and
> "CPU raw-native coverage 0.598" — mixed interval pairs / stale values and
> are superseded by the final `results/c4-calibration.json` + note numbers:
> CPU block b6 10-90 coverage **0.021 (b4xkt) / 0.016 (m7pr8)** (20-80 pair
> 0.011 / 0.016), miss split 0.56 below / 0.42 above; CPU **raw-native near
> nominal (0.795 uni / 0.788 multi on b4xkt; 0.799 / 0.798 on m7pr8)**;
> mem/rx/tx block b6 0.984–0.995 (over-cover).  See the "Flat / real
> observations" section of `markdown/part2-calibration.md` (corrected 2026-11-11).

### Acceptance cell check + wall

`cell_check.acceptance_cells_met = true`, `missing = []` — every scope entry
× 4 signals × 3 horizons (b3/b6/b12) × 5 pairs × {raw, block} × {pre_event,
all_quiet} is present (FLAT/S1/real have no anomaly events ⇒ pre_event ≡
all_quiet, identical `n` and coverage, verified per cell; S1/S3/S4/S7 differ
by the guard).  No absent cells to report.

Wall: verify 42 shards + 42 units in **238.7 s stage / 240.8 s total**
(per-unit 4.4–4.9 s, single bounded process, shared machine; `--max-minutes`
guard, exit 5 resumable).  `results/c4-calibration.json` 7.5 MB (+ 13 440-line
`.csv`, long form unit × signal × resolution × segment × band × pair).

### Gates

```
$ .venv/bin/python -m pytest tests/test_refcompare_*.py -q
324 passed in 193.0 s, 0 skipped, 0 failed   # S1b baseline 303 + 2 new bands missing-key cases + 19 run_c4 helper tests
$ .venv/bin/python -m pytest tests/test_refcompare_run_c4.py tests/test_refcompare_bands.py -q
59 passed in 12.4 s        # 19 run_c4 helpers + 40 bands (incl. the 2 new missing-key cases)
$ .venv/bin/ruff check scripts/run_c4.py tests/test_refcompare_run_c4.py \
    src/refstudy/refcompare/bands.py tests/test_refcompare_bands.py
All checks passed!
$ grep -rniE 'print\(|solo_mode|sys\.path' src/refstudy/refcompare scripts/run_c4.py   # (empty)
$ git diff --check   # clean
```

Deviations: (1) `run_c4.py` imports the C1 `tfm_pipeline._last_ts` /
`_pod_grid` privates with `# noqa: SLF001` (the script reuses the C3
plumbing pattern rather than duplicating the grid rebuild); (2) the
`class_join` profile block is scoped to the YAML scope keys (FLAT/S1/S3/S4/S7
main + FLAT/S1 sweep contexts); (3) real-pod rows use `n_blocks = 1728`
(6.0 d slice) — the real offsets differ from the synthetic common offset
(1117 vs 1118, both recorded in the JSON).

Commit:

```
$ git log --oneline -1
536e6e2 data(refstudy): record Phase C calibration tables (C4 stage 2.1)
```

(7 files, owned paths only: `scripts/run_c4.py`, `config/refcompare_bands.yaml`,
`tests/test_refcompare_run_c4.py`, `tests/test_refcompare_bands.py`,
`src/refstudy/refcompare/bands.py`, `results/c4-calibration.json`,
`results/c4-calibration.csv`; the concurrent cand-B files and the dirty
`results/a1a-parity.json` were left unstaged.)

## Stage 2.2-2.3 — `--stage figures` + calibration note (card Steps 2.2–2.3, dispatch C4-S2b)

Owns `scripts/run_c4.py` (new figures stage), `src/refstudy/refcompare/plots.py`
(new optional `fan_t0` on `plot_real_bands`; `plot_reliability` parsing split
into the public `draw_reliability(ax, coverage)` so the two-panel figure can
share it), the two test files, the 13 figure PNGs and
`markdown/part2-calibration.md` (99 lines, D-A vocabulary, fixed card order).

### `--stage figures` run (single bounded process, no STL re-runs)

```
$ .venv/bin/python scripts/run_c4.py --config config/refcompare_bands.yaml --stage figures
...
04:53:14 | INFO | verify: 11/11 figure-scope shards ok in 12.5 s
04:53:18 | INFO | figure S1-uni in 2.2 s        ... figure horizons-S4-multi in 2.5 s
04:53:32 | INFO | figure realflat-b4xkt in 2.3 s  ... figure realflat-m7pr8 in 2.3 s
04:55:45 | INFO | figures: 15 PNGs in .../reference-model-study/figures (stage wall 37.9 s)
04:55:45 | INFO | stage(s) figures done in 39.8 s   (exit 0 — every PNG passed the
            in-script floor: >= 30000 bytes and height > 800 px, from the YAML)
```

Scope: the 11 card D-5 units (S1/S3/S4 × {uni, multi}, seed 1, main ctx; real
b4xkt/m7pr8 × {uni, multi}) plus FLAT:1:uni, which is used only as the
width-curve and reliability-panel input (it is NOT a D-5 figure; the figure
loop skips it, guard `unit.scenario in FIGURES_SCENARIOS`). Rebuild is the
same `_run_pod` as the tables stage (providers from the C2 shards, records
→ `evaluate_records` for the DB three-class p_raw strip); origin is always
`pod.ticks[0] - T` (what `served_band` validates against). Stage verifies all
11 shards via `ev.verify_shard` (rtol from the eval config) and exits 1 if
`results/c4-calibration.json` is absent; `--max-minutes` exit 5 unchanged.

### Figure list (15 PNGs, 150 dpi; sizes / pixel heights, PIL-checked)

```
name                        bytes   WxH
c4-bands-S1-uni.png        655 KB  1980x1410
c4-bands-S1-multi.png      652 KB  1980x1410
c4-bands-S3-uni.png        720 KB  1980x1410
c4-bands-S3-multi.png      720 KB  1980x1410
c4-bands-S4-uni.png        568 KB  1980x1410
c4-bands-S4-multi.png      576 KB  1980x1410
c4-horizons-S1-multi.png   525 KB  1980x1530
c4-horizons-S3-multi.png   501 KB  1980x1530
c4-horizons-S4-multi.png   361 KB  1980x1530
c4-bands-realflat-b4xkt.png 271 KB  1980x1800
c4-bands-realflat-m7pr8.png 270 KB  1980x1800
c4-width.png                 74 KB  1050x845
c4-reliability.png          117 KB  1860x845
```

Visual descriptions (raster sanity: every file non-blank, 4–42 % non-white
content; strip/label content guaranteed by the unit tests on the same code
paths — `plots._p_raw_strip` and `plotting/figure.py` `build_figure`):
- **bands** (`c4-bands-*-{uni,multi}`): 3 signal columns × 2 d served-band
  rows + raw rows, shaded outer/inner band, dotted median, observed series,
  and the bottom p_raw strip (log-y) with the shaded undecidable band, both
  D-A boundary lines labelled "Decisive-normal boundary (0.2)" and
  "Decisive-anomaly boundary (0.8)" and the three-class legend. On
  `c4-bands-S4-multi.png` band + observed are present on all three signal
  columns (cpu, mem, rx_bytes).
- **horizons** (`c4-horizons-*-multi`): 3 signal columns × rows 15/30/60 min
  (b3/b6/b12), one block per cycle, outer/inner band + median + observed
  block series; band visibly widens with horizon.
- **realflat** (`c4-bands-realflat-*`): last 2 d of the block series with the
  served band; raw-native 65-min fans (unscaled provider `_q`, all 13
  horizon blocks = 260 steps) for the first/middle/last model cycle; bottom
  p_raw strip = the tfm-multi row from `results/c3-real-flat.json` (612
  finite of 1728; None → gap on the log-y axis) with both boundary lines.
  **RV-Phase-E F5 (2026-11-11):** the three fan cycles have DISTINCT
  epochs, so each fan row now carries its OWN local minutes-ahead 0–65
  x-axis (NOT shared with the multiday block/served-band + p_raw strip axis)
  and states its own origin in the row title (epoch of the fan's first
  plotted step, indexed by the cycles counter/gauge step law). The figure is
  drawn ONCE per pod from the uni shard (the multi unit targets the same
  file name; the earlier run overwrote the uni figure with the multi one).
  Regenerated from the existing shards (no re-run); the two committed PNGs
  are now 1980×1800, 466 / 469 kB.
- **width** (`c4-width.png`): ratio_median_level vs b = 0…12 for real flat
  (b4xkt, ≈0.002), S1 (0.48–0.52) and S3-pre (0.50–0.53; S3 masked to cycles
  before the noise-switch block 1584), block level; dashed lines = gate-off
  cpu w_stl per curve (real 2.677 / S1 4.153 / S3 4.190).
- **reliability** (`c4-reliability.png`): two panels (raw-native | block
  hand-off) of nominal vs empirical 0.1–0.9 coverage per signal, FLAT uni
  b6, all_quiet, via the shared `draw_reliability`.

### Note (`markdown/part2-calibration.md`, 106 lines after the 2026-11-11
RV-Phase-E F3/F11 corrections; 99 at stage-2 time)

Fixed card order: setup + the two resolutions (raw-native / block hand-off,
C1 D-4 comonotone upper bound); coverage tables at 15/30/60 min per
signal/mode, raw-native and block (seed-mean over seeds 1–3, 10–90 pair,
all_quiet); rx asymmetry/PIT (miss-below/above seed-mean, PIT ≈ 0.100 all
bins, `rx_skew` per unit); width vs horizon (no horizon effect on synthetic;
real flat ~100× tighter relative noise law); honesty-vs-cost table
(w_stl/w_rec/ratio/band-b6/band_wider, FLAT 4 signals + S1 + S3 cpu;
S3 widening 1.327 band vs 1.397 STL, matching direction; S1 gate-on n=420
vs gate-off n=757, w_stl unchanged); D-6 join table copied from the C3
profile (dec_occ/und_occ + >0.8 mechanism means, tfm-uni rows; gate-on post
for S1; real pods all-zero n=612); flat/real observations with the CPU-block
surprise stated as measured (raw near-nominal + block 0.011–0.021 + no
>0.8 tick — observed co-variation only, NO causal claim); figure list.

### Numbers recomputed from `results/c4-calibration.json` at note time
(verification sample; every other note number came from the same JSON)

```
1. FLAT:1:uni cpu raw b6 0.1-0.9 all_quiet, seed-mean(seeds 1-3) = 0.798
   (note: "raw-native ... 0.798" row; D-6 table cov column)
2. real:b4xkt:uni cpu block b6 0.1-0.9 coverage = 0.021053 (n=190),
   0.2-0.8 = 0.010526, miss split 0.5632/0.4158
   (note: "CPU block is badly miscalibrated ... 0.021 (b4xkt, n=190) / 0.016
   (m7pr8); 20-80 pair 0.011 / 0.016; misses split 0.56 / 0.42")
3. S3:1:multi noise_switch_split cpu: band b6 median 11.718 -> 15.553
   (ratio 1.327), stl record 4.010 -> 5.600 (ratio 1.397)
4. S3:1:multi honesty stl-gate-off cpu: w_stl 4.190, w_rec 4.594,
   ratio 1.096, band b6 12.392, band_over_stl 2.957, band_wider true
```

### Gates

```
$ .venv/bin/python -m pytest tests/test_refcompare_run_c4.py tests/test_refcompare_plots.py -q
34 passed in 23.3 s, 0 skipped        # per dispatch: only the two C4 test files
   (new: test_stage_figures_refuses_an_empty_shard_store,
   test_stage_figures_refuses_a_missing_calibration_json,
   test_stage_parser_rejects_unknown_stage, test_figures_scope_is_card_d5_units,
   test_shard_path_names_the_unit, test_figure_floor_flags_small_and_short_pngs,
   test_s3_regime_block_is_the_noise_switch_onset;
   plots: test_draw_reliability_shares_the_parsing,
   test_plot_real_bands_fan_t0_anchors_the_fan_axis;
   removed: test_stage_figures_rejected_with_clear_error)
$ .venv/bin/ruff check scripts/run_c4.py src/refstudy/refcompare/plots.py \
    tests/test_refcompare_run_c4.py tests/test_refcompare_plots.py
All checks passed!
$ git diff --check   # clean
```

Deviations: (1) the stage log says "15 PNGs" = `n_done + 2`, where `n_done`
counts FIGURE GENERATIONS (6 bands + 3 horizons + 4 real-flat — the real-flat
figure is built for BOTH the uni and multi units of each pod, each written to
the same `c4-bands-realflat-{pod}.png`, so the multi build overwrites the uni
build — + width + reliability = 15 builds) while the on-disk file count is 13
unique PNGs; the committed on-disk real-flat figures are the multi-mode builds
(the p_raw strip is the tfm-multi row, so band overlay and strip share one
reference). (2) `draw_reliability` was factored out of `plot_reliability`
(shared parsing) so the two-panel figure cannot drift from the library's
single-panel one; `plot_reliability` itself is unchanged in behaviour;
(3) real-flat p_raw strip is the last-1440-tick
window of the tfm-multi row, matching the 2 d display window.

Commit:

```
$ git log --oneline -1
4bc2bd5 data(refstudy): record Phase C quantile-band figures and calibration note (C4 stage 2.2-2.3)
```

(18 files, owned paths only: `scripts/run_c4.py`,
`src/refstudy/refcompare/plots.py`, `tests/test_refcompare_run_c4.py`,
`tests/test_refcompare_plots.py`, the 13 `figures/c4-*.png`,
`markdown/part2-calibration.md`; the dirty `results/a1a-parity.json` and the
concurrent cand-B `markdown/part2-accuracy-profile.md` were left unstaged.)

---

## RV-Phase-E F5/F3/F11 correction (2026-11-11)

Scope: the real-flat figure fans (F5), the calibration-note factual
corrections (F3/F11 text), and the stage-2 supersession note above. Lab files:
`scripts/run_c4.py`, `src/refstudy/refcompare/plots.py`,
`tests/test_refcompare_{plots,run_c4}.py`, `figures/c4-bands-realflat-{b4xkt,
m7pr8}.png`, `markdown/part2-calibration.md`, `markdown/candb-profile.md`
(F12 nit: 15 five-minute blocks = 1.25 h). No shard was modified; no result
JSON changed; the fix regenerates ONLY the two real-flat figures from the
existing C2 shards (one bounded run, `--stage` figures logic reused via
`_run_pod` + `verify_shard` on the uni shards, ~14 s wall, no model
inference).

**F5 (real-flat fan time axes).** Root causes and fixes:

1. *Wrong epoch + shared axis.* The stage-2 `plot_real_bands` drew all three
   fans at the FIRST cycle's `fit_end + cadence` on the multiday strip's
   shared x-axis (the committed figure showed nine near-vertical fan marks
   compressed at one early timestamp). Now each fan row carries its OWN local
   minutes-ahead 0–65 x-axis (`grid_seconds`-scaled, `set_xlim(0, 65)`,
   integer minor ticks), NOT shared with the block/served-band + p_raw strip
   axis, and states its OWN origin in the row title
   (`raw-native fan: {first|middle|last} (origin {YYYY-MM-DD HH:MM:SS} UTC)`).
   The origin is the epoch of the fan's first plotted grid step, indexed by
   the `cycles.step_grid_index` counter/gauge law (`run_c4._fan_origin_epoch`):
   counter step 0 ends `fit_end + 15 s`, gauge step 0 is `fit_end` itself, so
   cpu/rx (counters) and mem (gauge) differ by one 15 s step — passed to the
   plotter as a per-signal `fan_cycles` label→epoch map (a single shared
   `fan_t0` cannot express three distinct cycle timestamps, let alone the
   per-signal step-law offset).
2. *Fan extent bug.* The committed `REAL_FAN_STEPS = 13 * 5 = 65` steps
   covered only 16 min, not the card's "65-min fan = all 13 horizon blocks"
   (`per_block × horizon_blocks = 20 × 13 = 260 steps = 65 min` at the 15 s
   cadence). Now derived from `refcompare.yaml` (`rc.per_block × rc.cycle.
   horizon_blocks`); the YAML key `cycle.horizon_blocks: 13` is the single
   source of the 13.
3. *uni-overwritten-by-multi.* `stage_figures` built the real-flat figure for
   BOTH the uni and multi units of each pod into the SAME file
   `c4-bands-realflat-{pod}.png`; the multi unit (later in the scope loop)
   overwrote the uni build — deviation (1) above recorded that the committed
   figure was the multi build. Fix: `unit.mode == 'multi'` guard in the
   figure loop — the figure is drawn ONCE, from the uni-mode shard (the p_raw
   strip is the tfm-multi row of `results/c3-real-flat.json`, carried by both
   shards, so nothing is lost).
4. *Tests.* `test_plot_real_bands_fans_own_local_axes_and_distinct_origins`
   asserts the fan extents (data span 0–64.75 min for the 260-step fan, view
   clamped to 0–65), the per-row local axis (not shared with the p_raw strip),
   and DISTINCT origins per signal column (the counter/gauge law makes the
   same cycle's cpu origin 15 s after the mem origin); the old
   `test_plot_real_bands_fan_t0_anchors_the_fan_axis` is removed (the shared
   `fan_t0` axis no longer exists). `test_fan_origin_epoch_counter_and_gauge_
   law` pins the origin law (first/middle/last distinct; gauge = counter − 1
   cadence step).

**Opened figure description (`c4-bands-realflat-b4xkt.png`, 1980×1800,
466 367 B; `c4-bands-realflat-m7pr8.png` identical layout, 469 151 B).**
The vision side-channel was unavailable (Bedrock HTTP 404, model EOL), so the
description is from the figure's own axes objects (what the raster contains),
re-read after regeneration from the existing b4xkt/m7pr8 uni shards:

- 13 axes: top row = 3 signal columns (cpu/mem/rx_bytes) of the last ~2.2 d
  of observed blocks with the served band (date axis, 2026-11-07 02:06 →
  2026-11-09 06:48 UTC); middle = 9 fan rows (3 cycles × 3 signals); bottom =
  the full-width tfm-multi p_raw strip (log-y, both D-A boundary lines +
  three-class legend).
- Each fan row: local x-axis "min ahead of fit_end", xlim (0.0, 65.0),
  integer ticks; the fan data span 0.0–64.8 min (all 13 horizon blocks),
  i.e. the fan now fills the row instead of being a spike at one timestamp.
- Row titles carry DISTINCT origins: first = 2026-11-05 04:55:15 (cpu/rx) /
  04:55:00 (mem), middle = 2026-11-07 04:25:15 / 04:25:00, last =
  2026-11-09 03:25:15 / 03:25:00 UTC — the 15 s cpu/rx-vs-mem offset is the
  counter/gauge step law, provenance included per fan.
- The p_raw strip stays on the multiday date axis (2026-11-07 → 2026-11-09),
  decoupled from the fan rows.

**F3/F11 (note text, `markdown/part2-calibration.md`).** Replaced by the
measured values (recomputed from `results/c4-calibration.json`): synthetic
raw-native seed-mean 0.791–0.826 over the reported main horizons (individual
main units 0.780–0.833), NOT "0.79–0.82 for every unit"; block bands
seed-mean 0.940–1.000 (individual 0.915–1.000); real memory raw-native
under-covers (b4xkt/m7pr8 b6: uni 0.714/0.691, multi 0.723/0.731); "both
modes identical on cpu" removed (b4xkt raw cpu uni 0.795000 vs multi
0.787632); width ratios labelled "selected seed-1 examples" with the
across-synthetic-main-units gate-off ranges (residual/noise-law
0.738–1.324, band/noise-law 1.356–7.647); the PIT statement's aggregation is
named (mean over the 10 bins, all synthetic main units, raw b6 ≈ 0.100;
individual synthetic bins 0.070–0.128). Note is now 106 lines (was 99).

**Gates (2026-11-11):**

```
$ .venv/bin/python -m pytest tests/test_refcompare_plots.py tests/test_refcompare_run_c4.py -q
35 passed, 0 skipped
$ .venv/bin/ruff check scripts/run_c4.py src/refstudy/refcompare/plots.py \
    tests/test_refcompare_run_c4.py tests/test_refcompare_plots.py
All checks passed!
$ git diff --check   # clean
```
