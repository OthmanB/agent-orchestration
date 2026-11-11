# E-DB — D-B three-class re-expression of the Part-1 profile (executor)

Commit base: lab `main` @ `1d01aed` (clean preflight; baseline `pytest tests -q` green, 328 s wall).

## 1.1 (commit `7c78f0b` — `refactor(refstudy): add D-A three-class scoring config and metrics (DB 1.1)`)

Owned files (5): `config/harness.yaml`, `src/refstudy/harness/config.py`,
`src/refstudy/harness/metrics.py`, `tests/test_harness_config.py`, `tests/test_harness_metrics.py`.

### What landed
- **YAML**: `scoring.decisive_threshold: 0.8`, `scoring.p_raw_quantiles: [0.05,0.25,0.5,0.75,0.95,0.99]`
  (required, increasing, keys `q{round(100*l):02d}`), `mechanism.post_gate_lookback_cycles: 2`,
  `mechanism.lookback_sensitivity_cycles: [1,4]`, `outputs.mechanism_table: markdown/part1-mechanism-table.md`.
  `scoring.alpha_threshold: 0.2` kept (now commented as the decisive-normal boundary).
- **config.py**: `ScoringCfg.decisive_threshold, p_raw_quantiles`; NEW `MechanismCfg(post_gate_lookback_cycles,
  lookback_sensitivity_cycles)`; `HarnessConfig.mechanism`; every key via `require`; `ValueError` when
  `alpha >= delta` or `delta >= 1`; quantile list validated (non-empty, increasing, in (0,1), no 2-decimal
  q-key collision).
- **metrics.py**: NEW `ClassCounts(n, normal, undecided, decisive, at_alpha, at_decisive)`,
  `class_counts(p, sel, α, δ)` (NaN excluded; ties on 0.2/0.8 ⇒ undecided, flagged by `at_*`);
  NEW `Occupancy(rate, n, count)` + `occupancy(p, sel, α, δ, *, decisive)` (band = undecided incl. `at_alpha`);
  `detection(..., thr, *, inclusive=False)` (strict default = old semantics; `inclusive` = `>=`);
  `false_positive_rate`/`Fpr` deleted.
- **Tests**: ties 0.2/0.8 → undecided, 0.8+ε → decisive, NaN/warm-up/non-quiet excluded, old FPR guard
  cases (guard end+3 excluded / end+4 counted, persistent event, NaN-rate) kept as occupancy tests;
  config: new keys in the missing/mistyped/invalid parametrize lists (δ=0.2, δ=1.0, non-increasing
  quantiles, [0.051,0.052] key collision, lookback 0).

### Gate
```
$ .venv/bin/python -m pytest tests/test_harness_config.py tests/test_harness_metrics.py -q
111 passed
$ .venv/bin/ruff check src/refstudy/harness/config.py src/refstudy/harness/metrics.py \
    tests/test_harness_config.py tests/test_harness_metrics.py
All checks passed!
```

### Broader suite (expected red until slices 1.3–1.6 — their files, untouched)
`pytest tests -q` → 26 failures/errors, all
`AttributeError: module 'refstudy.harness.metrics' has no attribute 'false_positive_rate'` raised from
`harness/evaluate.py:179` (slice 1.3 owns that call), in:
`tests/test_harness_evaluate.py` (6 failed + 7 error), `tests/test_plotting_figure.py` (9 error),
`tests/test_refcompare_evaluate.py` (4 failed). No other test files fail; 0 skipped.

### Deviations / notes
- `results/a1a-parity.json` shows `wall_seconds` churn in `git status` after the full-suite runs
  (the parity test rewrites it each run — pre-existing test side effect, not this slice's code).
  Left unstaged; not part of this commit.
- `outputs.mechanism_table` is in the YAML now; its parse into `Outputs` lands in slice 1.4
  (`harness/profile_config.py` is that slice's file), so it is NOT in the `test_missing_key_is_named`
  harness list (deleting it would not make `load_harness_config` raise).

## 1.2 (commit `25752fc` — `feat(refstudy): add decisive-anomaly mechanism classification (DB 1.2)`)

Owned files (2): NEW `src/refstudy/harness/mechanism.py`, NEW `tests/test_harness_mechanism.py`.

### What landed
- **mechanism.py**: `MECHANISMS = ("injected-anomaly", "post-gate", "fresh-model noise")`;
  `lookback_ticks(grid, cycles)` (L = `cycles * round(dt_seconds/tick_seconds)`, exact-integer
  enforced; ValueError otherwise); `no_model_mask(records, names, warmup_offset)` — D-B records-only
  rule: `k + 1 >= warmup_offset` AND some listed metric's `MetricTick.reason ∈ {"model not built",
  "model stale"}` (works for TimesFM rows; ValueError on missing metric / bad args);
  `classify_decisive(p_raw, valid, quiet, no_model, delta, lookback_ticks) -> int8[n]` (−1 none,
  0 injected, 1 post-gate, 2 fresh-model noise) — maximal run of `valid & p_raw > delta`, `e0` =
  first tick, whole episode inherits one class: injected if `¬quiet[e0]` or any episode tick
  `¬quiet`; post-gate else if `no_model[max(0, e0−L) : e0]` has any True (e0 excluded); fresh else;
  `mechanism_block(...)` → `{"lookback_ticks": L, "counts": {3 names}, "runs": [[k0, length, name]],
  "sensitivity": {str(Li): counts}}` (sensitivity re-classifies at each `lookbacks`; sum invariant
  `sum(counts) == decisive ticks` enforced, ValueError otherwise).
- **Tests** (19): hand arrays — injected precedence over post-gate; episode inheritance from `e0`;
  `no_model` at `e0−L` counts (post-gate) vs `e0−L−1` does not (fresh); `no_model` at `e0` itself
  does not count; L=0 window `[e0,e0)`; episode split by an invalid tick (both halves inherit);
  episode starting inside an anomaly span (injected) + late tick inside a span; p == delta not
  decisive, NaN excluded; `mechanism_block` counts/runs/sensitivity at L=6 vs L=24 boundary;
  sum invariant; `no_model_mask` reason filter + warm-up boundary (offset 11: tick 10 counted,
  tick 3 not) + non no-model reason ignored + unlisted metric ignored + missing-metric/bad-arg
  ValueError; `lookback_ticks` from the study grid (L=12; sensitivities 6, 24); and the workcard
  on_cycle equality: on `get_scenario('S1', 1, n_ticks=900)` the cpu `no_model` mask from
  `pod.records` equals exactly the union of `[t0, t0+dt)` (tick-end times) of the
  `StlLiteProvider.run(on_cycle=…)` cycles with `reason != "built"`, both restricted to
  `k + 1 >= warmup_tick_end_offset` (bit-exact `bool((mask == expected).all())`; the re-run also
  serves the identical forecast). Extended on S1 seed 2 across ALL continuous metrics of the K=11
  and K=3 chains (same equality per metric).

### Gate
```
$ .venv/bin/python -m pytest tests/test_harness_mechanism.py -q
19 passed in ~1.7 s          # 0 skipped
$ .venv/bin/ruff check src/refstudy/harness/mechanism.py tests/test_harness_mechanism.py
All checks passed!
$ git diff --check
(clean)
```

### Broader suite (unchanged from 1.1 — expected red until slices 1.3–1.6)
`pytest tests -q` → the SAME 26 failures/errors as after 1.1 (all
`AttributeError: … no attribute 'false_positive_rate'` from `harness/evaluate.py:179`):
`test_harness_evaluate.py` (6 failed + 7 error), `test_plotting_figure.py` (9 error),
`test_refcompare_evaluate.py` (4 failed) — slices 1.3/1.4/1.6 own those. No new failures;
0 skipped. `results/a1a-parity.json` wall-seconds churn again left unstaged.

### Deviations / notes
- The workcard names `classify_decisive(p_raw, valid, quiet, no_model, delta, lookback_ticks)`;
  implemented exactly in that positional order (`quiet` is required — real pods pass all-True).
- `mechanism_block` also accepts `lookbacks=tuple[int,...]` (ticks) for the per-run sensitivity
  the workcard's per-run `mechanism{…sensitivity{…}}` shape requires; slice 1.3 wires it.
- `no_model_mask` is records-only and provider-agnostic as specified; it inspects the canonical
  names passed in, so slice 1.5's `PodReal.mechanism` can reuse it unchanged on real pods
  (`quiet` all-True per the workcard).

## 1.3 (commit `dd9c255` — `refactor(refstudy): re-express harness quantities in D-A three-class units (DB 1.3)`)

Owned files (5): `src/refstudy/harness/evaluate.py`, `src/refstudy/harness/aggregate.py`,
`src/refstudy/harness/__init__.py` (docstring), `tests/test_harness_evaluate.py`,
`tests/test_harness_aggregate.py`. No `EvalResult` field change; clean cutover (no alias of
`fpr` / `alpha_threshold` / `detection` / `median` / `frac_gt_thr` — all deleted, no legacy keys).

### What landed
- **evaluate.py** — new per-seed `quantities`:
  - `classes{valid,quiet}` = `{n, normal, undecided, decisive, at_alpha, at_decisive}`
    (`M.class_counts`); sum invariant `normal + undecided + decisive == n` holds by construction.
  - `undecided_occupancy{rate,n,count}` (quiet ticks, `0.2 <= p <= 0.8` incl. both edges) and
    `decisive_occupancy{...}` (quiet ticks, `p > 0.8`) — both `M.occupancy` views of
    `classes.quiet` (`undecided`/`decisive` fields exactly).
  - `p_raw_summary{ n_valid, q05, q25, q50, q75, q95, q99, max, frac_normal, frac_undecided,
    frac_decisive, frac_in_flat_band }` (`np.quantile` at every `scoring.p_raw_quantiles` level;
    all `None` when no valid tick; `frac_in_flat_band` = share in `[band_lo, band_hi]`).
  - `thresholds{decisive_normal_below, decisive_anomaly_above}` replaces the old
    `alpha_threshold` key.
  - `events[i]`: `detection` renamed to `leave_normal` (first valid `p >= alpha`,
    `M.detection(..., inclusive=True)`), NEW `decisive` (first valid `p > delta`, strict);
    `{status, j_star, latency, horizon}` each; window `[onset, next onset)` and censoring
    unchanged; `settling` unchanged, still keyed to `leave_normal.j_star`.
  - NEW `mechanism` block via `harness/mechanism.py`: `no_model_mask` over the served
    **continuous** canonical names (D-B rule: "∃ served continuous metric c"), L from
    `post_gate_lookback_cycles`, sensitivity lookbacks from `lookback_sensitivity_cycles`;
    `mechanism_block` returns `{lookback_ticks, counts, runs, sensitivity}` and enforces the
    sum invariant `sum(counts) == decisive ticks` (ValueError otherwise).
- **aggregate.py** — `aggregate_seeds`: `events[i].latency` → `latency_leave_normal` and
  NEW `latency_decisive`, each `{n, mean, sd, min, max, n_censored}`; NEW
  `undecided_occupancy` / `decisive_occupancy` (seed stats of the quiet-tick rates),
  `class_fraction{normal,undecided,decisive}` (seed stats of `p_raw_summary.frac_*`),
  `mechanism_counts{3 names}`; `p_raw_summary` now aggregates ALL keys (incl. `n_valid`);
  `fpr` deleted. `profile_rows`: CSV quantities renamed `latency` → `latency_leave_normal`,
  NEW `latency_decisive`, `fpr` → `undecided_occupancy`, NEW `decisive_occupancy`,
  `class_fraction` (per class), `p_raw_quantile` (per q05..q99 level), `mechanism_count`
  (per D-B class); `settle` / `fidelity_*` rows unchanged.
- **__init__.py** — docstring re-expressed in D-A three-class units.
- **Tests** — the 13 reds in `test_harness_evaluate.py` fixed (all were
  `AttributeError: ...false_positive_rate` from `evaluate.py`), plus new:
  - class-sum invariant `normal + undecided + decisive == n` for both `valid` and `quiet`
    selections + occupancies == views of `classes.quiet` (counts and rates);
  - `at_alpha` / `at_decisive` edge counting: hand-built single-signal scenario
    (`Scenario`/`GroundTruth`/`TickRecord` directly, no chain run) with p ticks
    {0.1, 0.2, 0.2, 0.8, 0.8, 0.8+ε, 0.1} — `at_alpha == 2`, `at_decisive == 2`, both
    boundary ticks in `undecided`; `leave_normal` fires at the first `== 0.2` (inclusive),
    `decisive` only at `0.8 + ε`; second hand scenario: crossing to exactly 0.8 →
    `leave_normal` detected, `decisive` censored;
  - decisive-latency censoring: S4 seed 1 — event E0 (onset 564) has
    `leave_normal.status == detected`, `decisive.status == censored` (p crosses 0.2 but
    never exceeds 0.8 before E1's window); E1: `decisive.j_star > leave_normal.j_star`;
  - mechanism sum invariant `sum(counts) == classes.valid.decisive` (S4 seed 1: 19,
    FLAT: 0, S3: asserted) + `mechanism.runs`/`counts` pinned for S4 seed 1
    (`[[785,13,injected-anomaly],[860,6,fresh-model noise]]`, counts 13/0/6) and all
    sensitivity cells;
  - `p_raw_summary` key set + value checks vs `np.quantile` of `p_raw[valid]`;
  - `thresholds` block present, old `alpha_threshold`/`fpr` keys absent; strict-JSON round-trip.
  - `test_harness_aggregate.py`: `_fake` per-seed payloads carry both latency blocks,
    classes, both occupancies, `p_raw_summary` (all keys) and `mechanism`; asserts
    `latency_leave_normal` / `latency_decisive` stats + `n_censored` each; mechanism-count
    aggregation (mean/invariant 13+0+6); `class_fraction` keys; CSV row key-set exactly
    `latency_leave_normal`, `latency_decisive`, `settle`, both occupancies, 3
    `class_fraction`s, 6 `p_raw_quantile`s, 3 `mechanism_count`s, 3 `fidelity_*`s; old
    `fpr`/`latency` keys asserted absent.

### Gate
```
$ .venv/bin/python -m pytest tests/test_harness_config.py tests/test_harness_metrics.py \
    tests/test_harness_mechanism.py tests/test_harness_evaluate.py tests/test_harness_aggregate.py -q
153 passed in ~7 s          # 0 skipped
$ .venv/bin/ruff check src/refstudy/harness/evaluate.py src/refstudy/harness/aggregate.py \
    src/refstudy/harness/__init__.py tests/test_harness_evaluate.py tests/test_harness_aggregate.py
All checks passed!
$ git diff --check
(clean)
```

### Planner-probe cross-check (mechanism wiring, seeds 1–5 summed, S1 base)
Reproduced exactly (workcard "Expected"): S1 → injected-anomaly 0 / post-gate **1570** /
fresh-model noise **7** (per seed 1–5: 318/324/312/312/304 post; 2/0/5/0/0 fresh;
`sum(counts) == decisive ticks` held on every seed). Sensitivity sums: L=6 → 0/1570/7,
L=24 → 0/1571/6 (only S7 moves at other lookbacks per the workcard; not re-probed here).

### Broader suite (expected red until slices 1.4–1.6 — their files, untouched by this slice)
`pytest tests -q` → 14 failures, all in slice 1.4/1.6-owned files, none in owned files:
- `tests/test_plotting_figure.py` — 8 failed (`KeyError: 'fpr'` / old `events[i]["detection"]`
  reads in `src/refstudy/plotting/figure.py`) → slice 1.4.
- `tests/test_refcompare_evaluate.py` — 2 failed (assert `'fpr' in quantities`) → slice 1.6
  (`refcompare/evaluate.py` consumers).
- `tests/test_refcompare_sidebyside.py` — 4 failed (`KeyError: 'mechanism'` —
  `refcompare/sidebyside.py` builds its own per-seed payloads without the new `mechanism`
  key and reads `agg["fpr"]` / `e["detection"]`) → slice 1.6.
Also stale until 1.4: `harness/profile.py` (`flat_summary` reads `s["median"]`/`q["fpr"]`,
`snr_summary` reads `frac_gt_thr`/`fpr_mean`), `scripts/run_part1.py` (SCHEMA_VERSION 1→2,
CSV column set), `harness/real.py` (slice 1.5). `test_harness_profile.py` currently passes
only because its fixtures predate the key cutover; it goes red once `profile.py` is exercised
in slice 1.4. 0 skipped; `results/a1a-parity.json` wall-seconds churn left unstaged
(pre-existing test side effect, same as 1.1/1.2).

### Deviations / notes
- Commit `a04e4f5` was amended to `dd9c255` (local-only, same slice): `_mechanism_block` now
  inspects the served **continuous** metric names only, matching the D-B rule verbatim
  ("∃ served continuous metric c"). No numeric change (S4 seed 1 pinned counts 13/0/6 and
  S1 seeds 1–5 sum 1570/7 reproduced identically before/after — rare-count runs never carry
  the no-model reasons, so the masks are equal on these scenarios).
- `served_continuous` is `tuple(scenario.names[s] for s in signals)` where `signals` = the
  continuous shorts the chain actually served (K=3 chains drop tx_bytes) — so the K=3
  sensitivity runs inspect exactly 3 metrics.
- `aggregate_seeds` aggregates `p_raw_summary.n_valid` as a plain seed-statistic (n = number
  of seeds with a value, mean over the n_valid counts); it is JSON-only, not a CSV row.

## 1.4 (commit `48f8050` — `refactor(refstudy): D-A three-class legends, profile summaries and mechanism table (DB 1.4)`)

Owned files (5): `src/refstudy/plotting/figure.py`, `src/refstudy/harness/profile.py`,
`src/refstudy/harness/profile_config.py`, `tests/test_plotting_figure.py`,
`tests/test_harness_profile.py`. Clean cutover: no alias of old keys
(`fpr`/`median`/`frac_gt_thr`/`fpr_mean`/`frac_gt_thr_mean`/`settings.alpha_threshold`
all deleted; `hcfg.scoring.alpha_threshold` is the kept config field, not a quantity key).

### What landed
- **figure.py** — three-class vocabulary, thresholds from `hcfg.scoring` (no literals):
  - `annotation(scenario, result, hcfg)` (new `hcfg` param): line 1
    `<S> seed <n> | undecided-band occupancy <rate> (c/n quiet) | decisive-anomaly <rate>
    (c/n quiet) | first scored k+1 = …`; one event line
    `<id> @k=<onset>: leave-normal <lat|censored (horizon H)> | decisive <lat|censored> |
    settle <…>` (reads `ev["leave_normal"]`/`ev["decisive"]`, no old `detection`);
    NEW mechanism line `p_raw>0.8 by mechanism: injected-anomaly a | post-gate b |
    fresh-model noise c` (0.8 from `hcfg.scoring.decisive_threshold`, counts from
    `q["mechanism"]["counts"]`); fidelity MAE line unchanged; no `FPR` text.
  - p_raw strip: dotted lines labelled ` Decisive-normal boundary (0.2)` (red, left) and
    ` Decisive-anomaly boundary (0.8)` (blue, right); undecidable band
    `[0.2, 0.8]` shaded (tab:orange, alpha 0.15, via new `_log_frac` helper =
    `log(v/lo)/log(hi/lo)` on the log y-scale); strip legend `decisively normal (<0.2)` /
    `undecidable [0.2, 0.8]` / `decisively anomalous (>0.8)` (values from `hcfg.scoring`).
    Row-0 legend now passed as `handles=`/`labels=` (matplotlib keyword form).
- **profile.py** — `SCHEMA_VERSION` 1→2; `flat_summary` rows re-expressed
  (`median`→`q50`, NEW `frac_normal`/`undecided_occupancy`/`decisive_occupancy`/`calm`
  (= `frac_normal >= 1 - flat.max_outside_fraction`, D-A iv; `flat_band_violation`
  unchanged); `snr_summary` rows re-expressed (`frac_gt_thr_mean`/`fpr_mean` →
  `frac_normal_mean`/`undecided_occupancy_mean`/`decisive_occupancy_mean`, ESS/stale
  blocks unchanged); `settings.alpha_threshold` → `settings.thresholds
  {decisive_normal_below, decisive_anomaly_above}`; NEW `mechanism_table(profile)->str`
  (header + one line per base scenario in `hcfg.scn` order, THEN the `<scn>/gate-off`
  (ess_off) / `<scn>/white` / `<scn>/k3` sensitivity lines grouped by scenario; columns
  scenario, valid ticks, >0.8, injected-anomaly, post-gate, fresh-model noise, all
  summed over the seeds of the cell via `_sum_per_seed`).
- **profile_config.py** — `Outputs.mechanism_table` (required, from
  `outputs.mechanism_table` via `require`; YAML key already present from 1.1).
- **Tests** — `test_plotting_figure.py`: both boundaries drawn (values from `hcfg`),
  boundary label texts present, undecidable band shaded with y-extent == the two
  boundaries on the log scale, three-class legend labels; `annotation` rewritten to
  assert line 1 / event lines / mechanism line against the result quantities
  (mechanism counts sum to `classes.valid.decisive`; no `FPR`); figure-text test
  asserts no `FPR` / `threshold 0.2`. `test_harness_profile.py`: `flat_summary`
  fixtures in D-A keys (q50/q99/max + occupancies + `frac_normal` + `calm` incl.
  the not-calm and no-valid-tick branches); `snr_summary` fixtures re-expressed
  (asserts new keys present, old `fpr_mean`/`frac_gt_thr_mean` absent); NEW
  `test_mechanism_table_sums_over_seeds_and_orders_cells` (base block then variant
  block, exact line content, per-seed summation, cell presence/absence); CSV
  round-trip uses `latency_leave_normal` / `undecided_occupancy` quantities.

### Gate
```
$ .venv/bin/python -m pytest tests/test_harness_config.py tests/test_harness_metrics.py \
    tests/test_harness_mechanism.py tests/test_harness_evaluate.py tests/test_harness_aggregate.py \
    tests/test_plotting_figure.py tests/test_harness_profile.py 2>&1 | tail -1
173 passed in 13.84s          # 0 skipped
$ .venv/bin/ruff check src/refstudy/plotting/figure.py src/refstudy/harness/profile.py \
    src/refstudy/harness/profile_config.py tests/test_plotting_figure.py tests/test_harness_profile.py
All checks passed!
$ git diff --check
(clean)
```

### Broader suite (expected red until slices 1.5–1.6 — their files, untouched by this slice)
`pytest tests -q` (full, ~330 s wall) → **6 failed, all in slice 1.6-owned files,
none in owned files** (0 skipped):
- `tests/test_refcompare_evaluate.py` — 2 failed (`assert "fpr" in result.quantities`,
  `multi.quantities["fpr"] == uni.quantities["fpr"]`) → slice 1.6 (`refcompare/evaluate.py`
  + the consumer tests).
- `tests/test_refcompare_sidebyside.py` — 4 failed (`KeyError: 'mechanism'` from
  `refcompare/sidebyside.py:94` → `aggregate_seeds`: it builds its own per-seed payloads
  without the new `mechanism` key and reads `e["detection"]`) → slice 1.6.
Same 6 reds as recorded after slice 1.3 (no NEW reds introduced). `test_harness_real.py`,
`test_refcompare_flat.py`, `test_refcompare_leakage.py` all still pass (their re-expression
is slice 1.5). `results/a1a-parity.json` wall-seconds churn left unstaged (pre-existing
test side effect, same as 1.1/1.2/1.3).

### Deviations / notes
- `annotation` gained a `hcfg` parameter (the card's "thresholds come from `hcfg`, no
  literals" requirement); both call sites updated (the `fig.text` call in `build_figure`
  and the test). No other `annotation` callers exist.
- `mechanism_table` is a pure function of the built `profile` dict (reads
  `profile["scenarios"]` + `profile["sensitivity"]`); `run_part1.py` writing it to
  `outputs.mechanism_table` lands in slice 1.5. `ess_off` variant lines are labelled
  `<scn>/gate-off` (the card's `gate-off` tag) and only emitted for scenarios the ESS
  gate-off sensitivity ran (S1, S2, S6, S7, S8); `white` runs S1, S3, FLAT; `k3` runs all 9.
- The p_raw strip band uses `axvspan(x[0], x[-1], ymin=_log_frac(α), ymax=_log_frac(δ))`
  where `x` is the tick-end datetime axis (already converted), so no `_dt` re-wrap.

## 1.5 (commit `d233b45` — `refactor(refstudy): re-express S4-real and real flat control in D-A three-class units (DB 1.5)`)

Owned files (4): `src/refstudy/harness/real.py`, `src/refstudy/plotting/realfig.py`,
`scripts/run_part1.py`, `tests/test_harness_real.py`. Clean cutover: no alias of old keys
(`lab_over_0p2` / `recorded_over_0p2` / `lab_frac_gt_0p2` / `recorded_frac_gt_0p2` /
`frac_gt_0p2` / `window_ticks_over_alpha` / `pods_over_alpha_in_window` / `alpha_threshold`
all deleted; `grep -rnE "window_ticks_over_alpha|pods_over_alpha_in_window|frac_gt_0p2|lab_over_0p2|recorded_over_0p2|frac_gt_0p2" src scripts tests` empty).
No threshold literals remain in `real.py` / `run_part1.py` / `realfig.py` (grep for `0\.2` /
`0\.8` returns only quantile levels, line widths, colors and layout fractions); α/δ come
from `hcfg.scoring`. No stage of `run_part1.py` was re-run against the real results
(slice-2 re-run is a later dispatch); verification is unit tests + `--help` / import smoke.

### What landed
- **real.py** —
  - `episode_verdict(lab_p, lab_ticks, episode, window, cfg, alpha)`: `window_ticks_over_alpha`
    → `window_ticks_not_normal` (window ticks with lab p_raw ≥ α, unscored/NaN not counted);
    `episode_ticks_over_threshold` (0.5, `cfg.episode_p_threshold`) unchanged.
  - `fleet_verdict(per_pod, cfg, thresholds)`: `pods_over_alpha_in_window` →
    `pods_leaving_normal_in_window`; reported `alpha_threshold: 0.2` → `thresholds`
    `{decisive_normal_below, decisive_anomaly_above}` (passed in, not a literal); verdict
    logic unchanged (reproduced / not_reproduced / partial).
  - `flat_pod_summary(p, hcfg)`: `frac_gt_0p2` (p > 0.2) split into the D-A three classes
    `frac_normal` (p < α), `undecided_occupancy` (α ≤ p ≤ δ, both edges inclusive),
    `decisive_occupancy` (p > δ), plus NEW `calm` = `frac_normal >= 1 -
    flat_control.max_outside_fraction` (D-A iv); quantiles / `frac_in_band` /
    `frac_at_point_mass` unchanged; empty input → all new keys `None`.
  - NEW `class_counts_of(p, alpha, delta) -> {n, normal, undecided, decisive}` (finite
    values; empty/all-NaN → all zeros; boundaries → undecided).
  - NEW `PodReal.records: tuple[TickRecord, ...] = ()` + `PodReal.mechanism(hcfg)` and NEW
    `pod_mechanism_block(p_raw, records, hcfg)`: the per-real-pod D-B `mechanism` block
    (reuses `harness/mechanism.py`: `no_model_mask` over the continuous canonical names of
    `hcfg.ref_real.metrics.entries`, L = `lookback_ticks(hcfg.ref_real.grid,
    post_gate_lookback_cycles)`, sensitivity at `lookback_sensitivity_cycles`; real pods
    pass `quiet` = all True per the card). `run_pod_real` now keeps `tuple(run.records)`.
- **realfig.py** — both figures take `alpha_threshold` / `delta_threshold` as REQUIRED
  keyword args (no literal defaults; both draw the two dotted boundary lines from them).
  Fleet panels: title now `"<sfx> | lab <frac_normal>/<frac_undecided>/<frac_decisive>
  n=<n> <normal>/<undecided>/<decisive> (u<%> d<%>) | rec n=… (u% d%) | r=…"`, reading
  `lab_classes` / `recorded_classes` / `lab_frac_*` from the per-pod rows. Flat panels:
  title now `"<sfx> | scored … | p50 … | normal … | band … | decisive … | calm|NOT calm"`
  (class counts/fractions from `flat_pod_summary`).
- **run_part1.py** —
  - `run_scenarios`: after `profile.run_profile`, writes `outputs.mechanism_table` from
    `profile.mechanism_table(profile)` (single write site; `run_profile` itself does not
    write it).
  - S4-real record: `schema_version` 1 → 2; NEW top-level `thresholds
    {decisive_normal_below, decisive_anomaly_above}`; per-pod: `lab_over_0p2` /
    `recorded_over_0p2` / `lab_frac_gt_0p2` / `recorded_frac_gt_0p2` deleted; NEW
    `lab_classes` / `recorded_classes` (via `class_counts_of`) and `lab_frac_normal` /
    `lab_frac_undecided` / `lab_frac_decisive` (None when no finite lab values); NEW
    `mechanism` block (`pr.mechanism(hcfg)`); `episode_verdict` / `fleet_verdict` called
    with α / `record["thresholds"]`. `lab_over_0p5` / `recorded_over_0p5` and the episode
    threshold (0.5) are unchanged per the card.
  - Real-flat record: `schema_version` 1 → 2; NEW top-level `thresholds`; per-pod rows
    carry the new `flat_pod_summary` keys (`frac_normal` / `undecided_occupancy` /
    `decisive_occupancy` / `calm`).
  - Both figure calls pass `alpha_threshold=hcfg.scoring.alpha_threshold` /
    `delta_threshold=hcfg.scoring.decisive_threshold`.
- **tests/test_harness_real.py** — re-expressed + extended (45 tests): new
  `TestClassCountsOf` (partition, boundaries → undecided, empty/NaN → zeros);
  `episode_verdict` tests now assert `window_ticks_not_normal` (inclusive at α, 0 when all
  below); `fleet_verdict` tests use `window_ticks_not_normal` rows and assert the reported
  `thresholds` block; `flat_pod_summary` tests assert the new class fractions + `calm`
  (calm iff frac_normal ≥ 0.98; boundary p == δ → undecided not decisive; empty → all
  None); NEW `TestPodMechanism` on hand-built `TickRecord` arrays (single continuous
  'cpu' metric; L = 12): no decisive → zero counts; post-gate when a no-model tick sits at
  e0−1 (in `[e0−L, e0)`); fresh-model noise with no no-model tick; no-model at e0−15
  (outside the lookback) → fresh; p == δ not decisive; `PodReal.mechanism(hcfg)` ==
  `pod_mechanism_block(...)`; sensitivity cells at 6 and 24 ticks present;
  NEW `TestRealfigSmoke`: fleet figure titles carry the class fractions and both boundary
  hlines sit exactly at α / δ (no literal defaults); flat figure title shows `calm` +
  class fractions. Window-slicing / common-tick / log-correlation / p_raw_by_tick tests
  unchanged (kept as regression coverage).

### Gate
```
$ .venv/bin/python -m pytest tests/test_harness_real.py tests/test_harness_profile.py \
    tests/test_plotting_figure.py -v
collected 65 items
tests/test_harness_real.py ............... [ 69%]
tests/test_harness_profile.py ... [ 83%]
tests/test_plotting_figure.py ... [100%]
65 passed in 3.26s          # 0 skipped
$ .venv/bin/ruff check src/refstudy/harness/real.py src/refstudy/plotting/realfig.py \
    scripts/run_part1.py tests/test_harness_real.py
All checks passed!
$ git diff --check
(clean)
```

### Smoke (no real-results re-run)
- `.venv/bin/python scripts/run_part1.py --help` OK (usage + stages unchanged).
- Import smoke: `refstudy.harness.real` and `refstudy.plotting.realfig` import;
  `build_fleet_figure` / `build_flat_figure` signatures require `alpha_threshold` /
  `delta_threshold` (no defaults, verified via `inspect.signature`);
  `scripts/run_part1.py` exec-imports cleanly (`run_scenarios` / `run_real` defined).
- `grep -rnE "0\.2|0\.8"` over the three owned source files: no threshold literals
  (only quantile levels `0.25`, line widths `0.8`, color `"0.4"`, layout fractions).

### Broader suite (remaining reds belong to slice 1.6 — their files, untouched by this slice)
`pytest tests -q` (full, ~480 s wall; machine loaded by a concurrent cand-B run) →
**6 failed, all in slice 1.6-owned files, none in owned files; 0 skipped** — identical to
the 6 reds recorded after slice 1.4:
- `tests/test_refcompare_evaluate.py` — 2 failed (`assert "fpr" in result.quantities`;
  `KeyError: 'fpr'` from `refcompare/evaluate.py` consumers) → slice 1.6.
- `tests/test_refcompare_sidebyside.py` — 4 failed (`KeyError: 'mechanism'` from
  `refcompare/sidebyside.py:94` → `aggregate_seeds`: it builds its own per-seed payloads
  without the new `mechanism` key and reads `e["detection"]`) → slice 1.6.
No NEW reds introduced by this slice. `test_harness_real.py`, `test_harness_profile.py`,
`test_plotting_figure.py`, `test_refcompare_flat.py`, `test_refcompare_leakage.py` all
pass. `results/a1a-parity.json` wall-seconds churn left unstaged (pre-existing test side
effect, same as 1.1–1.4).

### Deviations / notes
- `PodReal.mechanism(hcfg)` is a method (not a property): it needs the harness config for
  the decisive threshold / lookbacks / ref_real grid + continuous metric names. The card's
  "`PodReal.mechanism`" is satisfied; `run_part1.py` calls `pr.mechanism(hcfg)` and the
  tests exercise both the method and `pod_mechanism_block` directly.
- The per-pod `mechanism` block lands in `results/part1-s4real.json` (`pods.<sfx>.mechanism`),
  mirroring the synthetic per-seed `mechanism` key of the profile (workcard "decisive-
  episode counts per the card table"). The real-flat JSON keeps the card's `flat_pod_summary`
  shape (`frac_normal` / `undecided_occupancy` / `decisive_occupancy` / `calm`) without a
  per-pod mechanism block (the card's flat row renames are the three fractions + `calm`).
- `run_pod_real` now carries the full `TickRecord` tuple in the pickled `PodReal`
  (process-pool results). This is the mechanism's recorded input (reasons / `model_t0` /
  `ess` per metric); it slightly increases the pickled payload of each pod result. No
  numeric change to `p_raw` / ticks / wall (the chain run is untouched).
- `flat_pod_summary.calm` uses the D-A iv rule (`frac_normal >= 1 -
  max_outside_fraction`, i.e. ≥ 0.98 with the current YAML), matching
  `harness/profile.py flat_summary` from slice 1.4; the prior `frac_gt_0p2` was p > 0.2
  (the re-label, not a pure relabel — flagged in the card).

## 1.6 (commit `7ea2966` — `refactor(refstudy): cut over C3 consumers to D-A three-class keys (DB 1.6)`)

Owned files (6): `src/refstudy/refcompare/sidebyside.py`,
`src/refstudy/refcompare/flat.py`, `tests/test_refcompare_evaluate.py`,
`tests/test_refcompare_flat.py`, `tests/test_refcompare_leakage.py`,
`tests/test_refcompare_sidebyside.py`. Mechanical cutover of the committed C3
consumers to the new keys only (no new content; C3 slice 1c adds the three-class
columns/verdicts later). +165 / −76.

### What landed
- **sidebyside.py** — clean cutover, no alias:
  - `_seed_list`: per-seed payload `"fpr": quantities["fpr"]` → `"undecided_occupancy"`
    + `"decisive_occupancy"` (both carried from `EvalResult.quantities`).
  - `deltas`: per-event `"latency"` → `"latency_leave_normal"` + NEW
    `"latency_decisive"` (each `{tfm_mean, stl_mean, delta, n_censored{tfm,stl}}`); the
    aggregate `"fpr"` diff block → `"undecided_occupancy"` + `"decisive_occupancy"`
    (absolute diffs of the two seed-mean rates). Docstrings re-expressed.
  - `s3_pulse_rows`: `e["detection"]` → `ev_block["leave_normal"]` (the row's
    `latency`/`status`) + NEW `decisive_latency`/`decisive_status` from
    `ev_block["decisive"]` (the card's "S3 pulse rows add the latency to
    decisive-anomaly"). Docstring re-expressed.
  - `s7s8_advantage`: `"fpr"` block → `"undecided_occupancy"` + `"decisive_occupancy"`
    (`tfm_mean` / `stl_mean` of the two seed-mean rates).
  - `profile_rows` (flat CSV): single `"fpr","rate"` row → one row each for
    `"undecided_occupancy"` / `"decisive_occupancy"`; `"detection"` row →
    `"latency_leave_normal"` + `"latency_decisive"` rows (per event); `p_raw` rows now
    iterate the D-A quantile keys (q05…q99, max, frac_*) of `aggregate.p_raw_summary`.
    Docstring re-expressed.
- **flat.py** — `p_raw_summary` key set: `median` → `q50` (value unchanged, `np.median`);
  `frac_gt_threshold` REMOVED (the gate regex `frac_gt_thr` matches the substring; the
  workcard's "`frac_gt_thr` removed"). `frac_gt_calm_p` kept (C3's own D-4 yardstick,
  matches no gate token; the full three-class key set `{frac_normal,
  frac_undecided, frac_decisive, n_decisive, frac_lt_calm_p}` lands in C3 1c). The D-4
  `verdict` is unchanged — it computes `(v > threshold).sum()` inline, so removing the
  summary key is a no-op for the verdict logic. Docstrings re-expressed.
- **tests** — hand-built `EvalResult.quantities` payloads rebuilt to the post-1.3 schema
  so the real consumers exercise it:
  - `test_refcompare_sidebyside.py`: `_event` now carries `leave_normal` + `decisive`
    (not `detection`); `mk` payload drops `alpha_threshold`/`fpr`/`median`/`frac_gt_thr`
    and adds `thresholds`, `classes{valid,quiet}`, `undecided_occupancy`,
    `decisive_occupancy`, the full `p_raw_summary` (q05…q99/max/frac_*) and
    `mechanism` block (all the keys `aggregate_seeds` now reads); the `fpr=` kwarg →
    `und_rate=`. Deltas asserts on `latency_leave_normal` /
    `undecided_occupancy` / `decisive_occupancy`; S3 row asserts `decisive_latency`;
    CSV-row asserts on the new quantity keys.
  - `test_refcompare_evaluate.py`: `"fpr" in quantities` → `undecided_occupancy` +
    `decisive_occupancy in`; uni/multi identity on the two occupancies.
  - `test_refcompare_flat.py`: `s["median"]` → `s["q50"]` + `"median" not in s`; the
    `_mk` payload `fpr` → `undecided_occupancy`/`decisive_occupancy`.
  - `test_refcompare_leakage.py`: the `_mk` event block `detection` → `leave_normal`
    + `decisive` (with `j_star`/`horizon`), `fpr` → the two occupancies. (`leakage.py`
    itself never reads `quantities`, so this is payload-shape only.)

### Gate
```
$ .venv/bin/python -m pytest tests/test_refcompare_evaluate.py tests/test_refcompare_flat.py \
    tests/test_refcompare_leakage.py tests/test_refcompare_sidebyside.py -q
34 passed, 0 skipped
$ .venv/bin/python -m pytest tests -q
... all dots, no s/F/E ...  exit 0          # 0 skipped
$ .venv/bin/ruff check src/refstudy/refcompare/sidebyside.py src/refstudy/refcompare/flat.py \
    tests/test_refcompare_evaluate.py tests/test_refcompare_flat.py \
    tests/test_refcompare_leakage.py tests/test_refcompare_sidebyside.py
All checks passed!
$ .venv/bin/ruff check src tests scripts
All checks passed!
$ git diff --check            # clean
```

### Gate grep (the card's command)
`grep -rniE "fpr|false.?positive|frac_gt_thr|frac_gt_0p2|over_0p2|over_alpha|\"detection\""
src scripts tests config` over the 6 owned files: **EMPTY** (exit 1). Over the whole tree it
is NOT empty, but every remaining hit is in a slice 1.1–1.4 file already committed by this
campaign, in one of two shapes, both legitimate:
- docstring/comment prose describing the re-label ("the re-label of the former FPR",
  `# … the old "detection"") — `harness/__init__.py:4`, `harness/evaluate.py:102,266`,
  `harness/metrics.py:101`; and
- negative cutover assertions that VERIFY the old keys are gone — `tests/test_harness_
  aggregate.py:119,134,196`, `test_harness_evaluate.py:168,180`, `test_harness_profile.py:221`,
  `test_plotting_figure.py:7,188,219,224,227,228,232`.
No live old-key reader remains anywhere in `src`/`scripts`/`tests`/`config`.

### Notes
- `results/a1a-parity.json` re-churned on the full-suite run (the parity test rewrites it
  each run — pre-existing test side effect, same as 1.1–1.5). Verified numerically: all 60
  differing leaf paths are `wall_seconds.*`; zero non-wall (numeric comparison) values
  changed. Restored to HEAD per the gate instruction; not part of this commit.
- The C3 consumers had NO `results/` / `figures/` artifacts to regenerate (the stage-2 C3
  run is a later dispatch); verification here is the unit tests + the gate grep. No
  chain law / threshold / `reference/` / `scenarios/` touched.
- The whole-tree grep will stay non-empty by design (the 1.1–1.4 explanatory comments and
  the "old-key absent" test assertions are intentional and correct); this slice's
  obligation — the 6 named files grep-clean and the full suite green — is met.



## Stage 2 (PASS — all gates green; mechanism defect found & fixed in 1.2's `classify_decisive`)

**Outcome: committed after one in-scope defect fix.** `compare` PASSES (180/180 digests
equal; every pre-existing number identical under the D-A rename map). The
workcard's expected D-B mechanism counts initially failed 6/9; the root cause was a
genuine slice-1.2 defect in `mechanism.py::classify_decisive` (interior-episode end
off-by-one), fixed in place + regression-tested; after the fix + re-run,
`check-mechanism` passes 9/9 and the S7 lookback sensitivity matches the card
exactly. No workaround (no threshold / law / scenario / reference change); the
defect fix is a 1.2-owned-file repair, recorded below as a deviation.

Base: lab main @ `3f3ac04` at run start (HEAD now `7ea2966` + D-F commits
`60628d1`/`b2a8165`/`3f3ac04` — all in D-F's owned `b2-*` paths, untouched here).
Preflight: `results/a1a-parity.json` already dirty at start (pre-existing
parity-test wall-seconds side effect, as 1.1–1.6); `refcompare/grid.py` received an
RV-C modification mid-run (another executor; not mine, not staged).

### 2.0 — baselines from the commit before slice 1.1 (`P = 7c78f0b^ = 1d01aed`)
```
$ P=$(git rev-parse 7c78f0b^)            # 1d01aed40bf24284acef76ea9a49ffc7d861da6d
$ git worktree add /tmp/refm-db-base $P
$ cp scripts/verify_part1_cutover.py /tmp/refm-db-base/reference-model-study/scripts/
$ cd /tmp/refm-db-base/reference-model-study
$ PYTHONPATH=$PWD/src $STUDY/.venv/bin/python scripts/verify_part1_cutover.py \
      digest --config config/harness.yaml --out /tmp/refm-db-old-digest.json
# digest: 180 digests written /tmp/refm-db-old-digest.json   (real 0m46.334s)
$ git worktree remove /tmp/refm-db-base      # (--force: only the copied script untracked)
```
Old baseline results extracted via `git show $P:reference-model-study/results/
part1-{profile.json,profile.csv,s4real.json,real-flat.json}` → `/tmp/refm-db-old-results/`.

### 2.1 — NEW `scripts/verify_part1_cutover.py`
Subcommands: `digest` (sha256 of float64 `p_raw` bytes, all 180 `plan_runs` specs,
keyed by `spec.label`), `compare OLD_JSON NEW_JSON OLD_DIGEST NEW_DIGEST`,
`check-mechanism PROFILE` (the expected-count gate). Rename map: `detection`→
`leave_normal` (status/j_star/latency/horizon); shared blocks
(`settling`, `fidelity*`, `first_valid_k_plus_1`, `ess`, `frac_in_flat_band`, q99,
max) walk-compare; `median`→`q50` (rel 1e-12); `fpr`→`undecided_occupancy` with the
re-label identities `fpr.count == undecided.count + decisive.count − at_alpha`,
`fpr.n == classes.quiet.n`, `frac_gt_thr·n_valid == undecided + decisive − at_alpha`
over valid, via exact integer count recovery (no float sums); aggregate `latency`→
`latency_leave_normal`; flat rows `fpr`/`median`→`undecided_occupancy`/`q50`;
`snr_summary` `fpr_mean`/`frac_gt_thr_mean` recomputed from the new per-seed class
counts; S4-real `lab_over_0p2`/`recorded_over_0p2`/`*_frac_gt_0p2`/
`window_ticks_over_alpha`/`pods_over_alpha_in_window`; real-flat `frac_gt_0p2`→
undecided+decisive share (+ class-partition check). Excluded / gate-per-card:
`timing`, `git_head`, `config_sha256.harness`; `config_sha256.reference` and
`s4real.projected_total_seconds` are REPORTED, not gate-checked (they move with
concurrent lab work / wall time); `config_sha256.scenarios` IS gate-checked and is
equal. ruff clean; `digest` verified reproducible (180/180 on both commits, 46.3 s
old / 46.1 s new).

### 2.2 — re-run (wall times on this shared machine)
```
$ .venv/bin/python scripts/run_part1.py --config config/harness.yaml --stage scenarios
# real 0m56.404s (profile wall 55.6 s) → results/part1-profile.{json,csv},
#   figures/part1-scenario-{1..8,flat}.png (9), markdown/part1-mechanism-table.md
$ .venv/bin/python scripts/run_part1.py --config config/harness.yaml --stage real
# real 0m12.307s (10 pods, 10.2 s in pool) → results/part1-{s4real,real-flat}.json,
#   figures/part1-{s4real,real-flat}.png; s4real verdict=partial
# `--stage captions` NOT re-run (results/part1-caption-regression.json untouched)
```
Figure + text-check chain runs: ~2.6 s per build; two proof/sensitivity
re-derivations: ~49 s each (9 base scenarios × 5 seeds, single chain pass, shared
p_raw).

### compare — PASS
```
$ .venv/bin/python scripts/verify_part1_cutover.py compare \
      /tmp/refm-db-old-results/part1-profile.json results/part1-profile.json \
      /tmp/refm-db-old-digest.json /tmp/refm-db-new-digest.json
digests: 180/180 equal (label sets match)
reported (non-gate) items (3):
  config_sha256.harness old=44e186b18427… new=c89a972b2fe0… (expected: YAML changed by D-A)
  config_sha256.reference old=0356d2c0e3bd… new=534f8d83d148… (concurrent CB work 482e3ea
    added the lab-only `baseline.continuous.seasonal.trend.method: boxcar` key to
    config/reference.yaml; bit-for-bit legacy behaviour — proven harmless by the
    180/180 digest equality)
  s4real.projected_total_seconds old=23.2734 new=22.7800 (wall time; not gate-checked)
compare: all pre-existing numbers equal under the D-A rename map; class-sum and re-label
invariants hold
PASS   (exit 0)
```
`at_alpha` / `at_decisive`: 0 across all 180 per-seed blocks (both `valid` and
`quiet`) — the card's "0 valid ticks with p==0.2 or p==0.8" holds (probed on FLAT,
S1, S3, S4, S7 individually; sum over all blocks = 0). `git diff --check` clean on
all owned paths.

### check-mechanism — first run FAIL 6/9 → defect fixed → **PASS 9/9**

First run (before the fix):
```
scn   committed(inj,post,fresh) card expected    status
FLAT  (0, 0, 55)               (0, 0, 55)       OK
S1    (0, 1570, 7)             (0, 1570, 7)     OK
S2    (209, 0, 21)             (195, 0, 35)     MISMATCH
S3    (676, 1161, 14)          (2, 1826, 23)    MISMATCH
S4    (148, 0, 70)             (137, 0, 81)     MISMATCH
S5    (0, 1957, 22)            (0, 1957, 22)    OK
S6    (669, 974, 13)           (402, 1239, 15)  MISMATCH
S7    (132, 473, 1587)         (64, 473, 1655)  MISMATCH
S8    (123, 0, 2278)           (85, 0, 2316)    MISMATCH
check-mechanism: 6/9 base scenarios MISMATCH   (exit 1)
```

#### Root cause (definitive; same inputs, two classifiers)
`mechanism.py::classify_decisive` built interior episodes as
`runs = [(starts[i], starts[i+1] - 1), ...] + [(starts[-1], idx[-1] + 1)]` — the
end of run *i* was `start_{i+1} - 1` (one past the next run's first decisive
tick… i.e. it spanned the inter-run gap) instead of this run's own last decisive
tick + 1. When the gap is ≥ 2 non-decisive ticks, the extended slice
`quiet[s:e]` includes the gap; any non-quiet gap tick (an anomaly span incl. guard
over the gap) made the whole all-quiet run classify as `injected-anomaly` (or,
via the lookback window, `post-gate`). The card's own episode definition —
"maximal run of consecutive ticks with `valid ∧ p_raw > δ`" — excludes the gap,
so the committed code violated the spec. Concrete (S2 seed 1): run
`[100–104]`-shaped interior runs with a non-quiet tick in the 5-tick gap were
class-0 instead of class-2; the gap tick itself was also (wrongly) classed.
Proof on one chain pass per spec (identical `p_raw`/`valid`/`quiet`/`no_model`,
only the episode-end computation differs), summed over seeds 1–5:

```
scn   card            committed [status]  correct-boundary [status]
S1    (0, 1570, 7)    (0, 1570, 7)  [OK ]  (0, 1570, 7)  [OK ]
S2    (195, 0, 35)    (209, 0, 21)  [X  ]  (195, 0, 35)  [OK ]
S3    (2, 1826, 23)   (676, 1161, 14)[X  ] (2, 1826, 23) [OK ]
S4    (137, 0, 81)    (148, 0, 70)  [X  ]  (137, 0, 81)  [OK ]
S6    (402, 1239, 15) (669, 974, 13) [X  ]  (402, 1239, 15) [OK ]
FLAT  (0, 0, 55)      (0, 0, 55)    [OK ]  (0, 0, 55)    [OK ]
S5    (0, 1957, 22)   (0, 1957, 22) [OK ]  (0, 1957, 22) [OK ]
S7    (64, 473, 1655) (132, 473, 1587)[X ] (64, 473, 1655)[OK ]
S8    (85, 0, 2316)   (123, 0, 2278) [X  ]  (85, 0, 2316) [OK ]
```
i.e. the committed numbers reproduce the profile JSON exactly (the defect is the
whole 6/9 failure), and the correct-boundary rule matches the card on **all 9**.
Sensitivity (same re-derivation at L = 6/12/24 ticks): S7 moves —
post 332 / 473 / 676 — as the card states; **S1 also moves, slightly** —
post/fresh 1570 / 7 at L = 6 and L = 12 but **1571 / 6 at L = 24** (seed 1:
318 / 2 → 319 / 1; that cell is stored in the profile's S1 sensitivity block,
as the 1.3 cross-check above already reported). The earlier "only S7 moves …
every other scenario is lookback-invariant" was therefore an overstatement:
two scenarios (S1, S7) are lookback-sensitive in the stored base cells.

#### Fix applied (1.2-owned file; recorded deviation)
- `src/refstudy/harness/mechanism.py::classify_decisive`: the `runs` list is now
  the maximal consecutive decisive runs as `(k0, k1)` with `k1` EXCLUSIVE = the
  run's own last decisive tick + 1 (the next run's `start - 1` is not used as an
  end). The rest of the function — `quiet[s]` / `quiet[s:e].all()` injected test,
  `no_model[max(0, s-L):s]` post-gate test, the `out[s:e]` fill, the int8/`_NONE=-1`
  return, and `mechanism_block`'s sum-invariant — is unchanged. The sensitivity
  lookbacks re-run the same function, so one fix corrects base + sensitivity.
  (`_runs_of`, used for the per-run `runs` list, was already correct.)
- `tests/test_harness_mechanism.py`: NEW
  `test_interior_episode_end_does_not_span_the_gap` — two interior decisive runs
  `[100,105)` and `[110,115)` with a non-quiet tick at 105 (gap 105–109, ≥ 2
  non-decisive ticks); asserts both runs are `fresh-model noise` (2) and the gap
  tick stays unclassed (−1). Hand-verified to FAIL on the old boundary logic
  (run 1 → class 0, gap tick → class 0).
- Rationale for in-place fix vs. hand-back: the file is this card's slice-1.2
  deliverable ("NEW `harness/mechanism.py` + `tests/test_harness_mechanism.py`"),
  not in the concurrently-owned D-F set (`src/refstudy/compute/*`,
  `scripts/plot_refresh.py`, `tests/test_compute_*`, `figures/b2-*`,
  `results/b2-*`); stage 2's 2.3 cannot commit a mechanism table that carries a
  proven spec-violating classifier; and the fix is spec-compliance, not a
  threshold/law/scenario/reference workaround. `mechanism.py` + its test are
  added to the 2.3 commit and flagged in the commit message.

After the fix + 2.2 re-run:
```
$ .venv/bin/python scripts/verify_part1_cutover.py check-mechanism results/part1-profile.json
scn   committed(inj,post,fresh) card expected    status
FLAT  (0, 0, 55)               (0, 0, 55)       OK
S1    (0, 1570, 7)             (0, 1570, 7)     OK
S2    (195, 0, 35)             (195, 0, 35)     OK
S3    (2, 1826, 23)            (2, 1826, 23)    OK
S4    (137, 0, 81)             (137, 0, 81)     OK
S5    (0, 1957, 22)            (0, 1957, 22)    OK
S6    (402, 1239, 15)          (402, 1239, 15)  OK
S7    (64, 473, 1655)          (64, 473, 1655)  OK
S8    (85, 0, 2316)            (85, 0, 2316)    OK
check-mechanism: all 9 base scenarios match the card's expected counts   (exit 0)
```
S7 sensitivity in the regenerated profile: L=6 post 332, L=12 (main) 473,
L=24 676 — card match. (The sensitivity dict stores only the configured cycles
[1, 4] → L=6/24; L=12 is the main `counts`.)

### Headline three-class numbers per scenario (seeds 1–5 summed; p_raw-gated)
| scn | n_valid | normal | undecided | decisive | und-band occ (quiet) | decisive occ (quiet) |
|---|---:|---:|---:|---:|---:|---:|
| FLAT | 6445 | 6207 | 183 | 55 | 183 | 55 |
| S1 | 3570 | 1893 | 100 | 1577 | 100 | 1577 |
| S2 | 4442 | 4046 | 166 | 230 | 106 | 35 |
| S3 | 4289 | 2303 | 135 | 1851 | 131 | 1849 |
| S4 | 6445 | 6014 | 213 | 218 | 178 | 81 |
| S5 | 4634 | 2524 | 131 | 1979 | 131 | 1979 |
| S6 | 3642 | 1878 | 108 | 1656 | 92 | 1254 |
| S7 | 6036 | 3538 | 306 | 2192 | 290 | 2128 |
| S8 | 6445 | 3396 | 648 | 2401 | 640 | 2334 |

### Mechanism table (regenerated, card-gated base rows)
```
| scenario | valid ticks | >0.8 | injected-anomaly | post-gate | fresh-model noise |
|---|---:|---:|---:|---:|---:|
| S1 | 3570 | 1577 | 0 | 1570 | 7 |
| S2 | 4442 | 230 | 195 | 0 | 35 |
| S3 | 4289 | 1851 | 2 | 1826 | 23 |
| S4 | 6445 | 218 | 137 | 0 | 81 |
| S6 | 3642 | 1656 | 402 | 1239 | 15 |
| FLAT | 6445 | 55 | 0 | 0 | 55 |
| S5 | 4634 | 1979 | 0 | 1957 | 22 |
| S7 | 6036 | 2192 | 64 | 473 | 1655 |
| S8 | 6445 | 2401 | 85 | 0 | 2316 |
```
(Plus the variant lines — `S1/gate-off`, `S1/white`, `S1/k3`, `S2/gate-off`,
`S2/k3`, `S3/white`, `S3/k3`, `S4/k3`, `S6/gate-off`, `S6/k3`, `FLAT/white`,
`FLAT/k3`, `S5/k3`, `S7/gate-off`, `S7/k3`, `S8/gate-off`, `S8/k3` — 9 base + 17
variant = 27 lines in `markdown/part1-mechanism-table.md`; only the 9 base rows
are card-gated.)

### Figures (11 regenerated; programmatic text audit — vision backend was down)
Built S3 seed 1 (most annotation lines) + S1 seed 1 + FLAT seed 1 via
`build_figure` and inspected the actual text artists (bounding boxes, labels,
hlines, overlap test over all text artists):
- annotation box (fig.text, inside figure bounds, **0 overlapping text pairs** in
  each of the 3 audited figures): line 1 `S3 seed 1 | undecided-band occupancy
  0.0358 (31/867 quiet) | decisive-anomaly 0.4141 (359/867 quiet) | first scored
  k+1 = 618`; event lines `S3-E1-pulse @k=1440: leave-normal latency 41 | decisive
  latency 126 | settle 35` and `S3-E2-pulse @k=1776: leave-normal censored
  (horizon 96) | decisive censored (horizon 96) | settle not_detected`; mechanism
  line `p_raw>0.8 by mechanism: injected-anomaly 0 | post-gate 353 | fresh-model
  noise 6` (corrected split); fidelity MAE line present.
- p_raw strip: dotted hlines at exactly y = 0.2 and y = 0.8, labels
  ` Decisive-normal boundary (0.2)` (red) and ` Decisive-anomaly boundary (0.8)`
  (blue); undecidable band shaded between; strip legend `decisively normal
  (<0.2)` / `undecidable [0.2, 0.8]` / `decisively anomalous (>0.8)`.
- No `FPR` text anywhere (annotation, axis labels, legends) in any audited figure.
  `part1-s4real.png` / `part1-real-flat.png` regenerated (1980×1650); their titles
  carry the D-A class counts/fractions per slice 1.5.

### Gates
```
$ .venv/bin/python -m pytest tests -q                # full suite: exit 0, 0 skipped
$ .venv/bin/ruff check src tests scripts            # All checks passed!
$ git diff --check                                   # clean
```
`results/a1a-parity.json` wall-seconds churn (pre-existing side effect, as
1.1–1.6) and the RV-C `refcompare/grid.py` modification (another executor) are
NOT mine, NOT staged, excluded from the commit.

### 2.3 — commit `496255c`
`data(refstudy): re-express Part-1 profile, S4-real and real flat control in D-A
three-class units`, plus the 1.2 `classify_decisive` episode-boundary fix
(`src/refstudy/harness/mechanism.py` + `tests/test_harness_mechanism.py`, recorded
deviation, see Root cause above). Staged EXACTLY:
`results/part1-{profile.json,profile.csv,s4real.json,real-flat.json}`,
`figures/part1-scenario-{1,2,3,4,5,6,7,8,flat}.png`, `figures/part1-{s4real,
real-flat}.png`, `markdown/part1-mechanism-table.md`,
`scripts/verify_part1_cutover.py`, `src/refstudy/harness/mechanism.py`,
`tests/test_harness_mechanism.py`. Not staged: `results/a1a-parity.json`,
`src/refstudy/refcompare/grid.py`, any `b2-*` (D-F owned).

## Fix (RV-DB F1–F4, 2026-11-10)

Findings from `RV-DB.md` (review of stages 1–2, baseline `7c78f0b^ = 1d01aed`).
All four applied in the lab; one commit (message `fix(refstudy): per-tick
injected rule, onset in lookback, figure labels and corrected sensitivity
prose (RV-DB F1-F4)`). No chain-law / threshold / `reference/` / `scenarios/`
change; `scripts/run_part1.py` needed no change.

### F1 — per-tick injected rule + run splitting
- `mechanism.py::classify_decisive`: tick k of a decisive episode (onset e0) is
  `injected-anomaly` iff `not quiet[k]` or `not quiet[e0]` (the card's per-tick
  rule) — no longer "any episode tick not quiet ⇒ whole episode injected".
  Post-gate / fresh remain episode-inherited.
- `mechanism.py::mechanism_block`: exported `runs` now SPLIT at every class
  change inside a decisive episode (a quiet prefix + injected tail exports as
  two runs); `counts` / sensitivity / sum-invariant unchanged in shape.
  Dead helper `_runs_of` deleted.
- `tests/test_harness_mechanism.py`: NEW `test_quiet_prefix_before_injection`
  (three consecutive decisive ticks, quiet `[True, True, False]`, no model
  outage → first two ticks fresh-model noise, third injected; also asserts the
  exported run split) and NEW `test_episode_late_tick_inside_span_is_injected_per_tick`
  (the previously asserted whole-episode injection is now asserted per tick);
  `test_injected_precedence_wins_over_post_gate` re-expressed to the per-tick
  rule.

### F2 — onset tick INCLUDED in the no-model lookback
- `classify_decisive`: window is `no_model[max(0, e0-L) .. e0]` inclusive
  (`lo:s+1`, was `lo:s`); docstrings updated.
- `tests/test_harness_mechanism.py`: `test_no_model_at_e0_itself_counts`
  (replaces the old exclusion-demanding test), L=0 boundary test updated to
  `[e0, e0]`, NEW card probe `test_onset_at_tick_1_with_no_model_onset_is_post_gate`
  (decisive onset at tick 1, `no_model[1]=True` → post-gate).

### F3 — corrected sensitivity prose (above)
- E-DB stage-2 §"only S7 moves" corrected: S1 post/fresh = 1570/7 at L = 6 and
  12 but **1571/6 at L = 24** (seed 1: 318/2 → 319/1). The stored sensitivity
  cells are kept verbatim (verified below, they already carried the change).

### F4 — real figures: shared legend + both boundary labels, unobscured
- `realfig.py`: NEW shared three-class legend + BOTH exact boundary labels
  (`Decisive-normal boundary (0.2)` lower-left, `Decisive-anomaly boundary
  (0.8)` upper-right) on every panel of `build_fleet_figure` AND
  `build_flat_figure`; the shared legend is drawn on a dedicated invisible
  axes in its OWN top gridspec row (overlap impossible by construction; a
  floating figure-legend was probed first and rejected — it dipped into the
  top-row panels' labels at 10 pods).
- `figure.py` (scenario figures): the `Decisive-normal boundary (0.2)` label
  moved from the strip's upper-left (where it overlaid the strip legend) to the
  upper-right, clear of the legend; the 0.8 label already sat there and stays.
- Tests assert RENDERED visibility/non-overlap, not just text presence:
  `test_plotting_figure.py::test_strip_boundaries_and_legend_do_not_overlap`
  (artist bbox non-intersection of both labels vs the strip legend and each
  other), `test_harness_real.py`: both fleet/flat title tests extended with
  exact-label + legend assertions and NEW
  `test_fleet_figure_labels_and_legend_do_not_overlap` /
  `test_flat_figure_labels_and_legend_do_not_overlap` (bbox checks).
- Regenerated `figures/part1-{scenario-1..8,flat,s4real,real-flat}.png`
  (11). The 3 key images (scenario-1, scenario-4, s4real) were checked: both
  labels + legend present and non-intersecting (bbox check on the figure
  artists + an independent pixel-ink check of the saved PNGs: legend row has
  ink, clean gap band below it, strip ink in the scenario figures). The
  vision-model image endpoint was down (Bedrock 404) during this run, so the
  check is bbox/pixel-based, not visual.

### Re-run + cutover (baseline worktree of `7c78f0b^ = 1d01aed`, removed after)
```
$ git worktree add /tmp/refm-db-base2 7c78f0b^   # committed verifier copied in
$ (baseline, PYTHONPATH=$PWD/src) scripts/verify_part1_cutover.py digest --out /tmp/refm-db-evidence2/old-digest.json
digest: 180 digests written (wall ~55 s)
$ scripts/verify_part1_cutover.py digest --config config/harness.yaml --out /tmp/refm-db-evidence2/new-digest.json
digest: 180 digests written (wall ~54 s)
$ scripts/run_part1.py --config config/harness.yaml --stage scenarios   # 56.8 s, 4 workers
$ scripts/run_part1.py --config config/harness.yaml --stage real        # 12.5 s, verdict=partial
$ scripts/verify_part1_cutover.py compare /tmp/refm-db-evidence2/old/part1-profile.json \
      results/part1-profile.json /tmp/refm-db-evidence2/old-digest.json /tmp/refm-db-evidence2/new-digest.json
digests: 180/180 equal (label sets match)
reported (non-gate) items (3):
  config_sha256.harness old=44e186b18427… new=c89a972b2fe0… (expected: YAML changed by D-A)
  config_sha256.reference old=0356d2c0e3bd… new=534f8d83d148… (concurrent CB work; reported, not gate-checked)
  s4real.projected_total_seconds old=23.2734 new=22.1184 (wall time; not gate-checked)
compare: all pre-existing numbers equal under the D-A rename map; class-sum and re-label invariants hold
PASS
$ scripts/verify_part1_cutover.py check-mechanism results/part1-profile.json
check-mechanism: all 9 base scenarios match the card's expected counts   (exit 0)
$ git worktree remove --force /tmp/refm-db-base2
```

### Mechanism counts vs the committed table (before/after; the 2.3 commit)
F1/F2 are REPORTED, not forced: the classifier now follows the card's
per-tick rule + inclusive onset. **All 9 base rows and the s4real per-pod
mechanism blocks are UNCHANGED** (0 valid ticks flip — verified per seed on all
180 runs' decisive ticks). The only stored mechanism-count changes:

| cell (seeds 1–5) | committed (inj/post/fresh) | after F1/F2 | Δ |
|---|---|---|---|
| base FLAT/S1/S2/S3/S4/S5/S6/S7/S8 | unchanged (all 9) | unchanged | 0 |
| S3/k3 | 20 / 115 / 338 | 20 / **125** / **328** | +10 post, −10 fresh (seeds 4, 5: an episode onset that sits on a `no_model` tick now reads post-gate) |
| S6/k3 | 75 / 12 / 97 | 75 / **17** / **92** | +5 post, −5 fresh (seed 3) |

Run-list splits inside those cells: S3/k3 seed 4 runs[1709] & runs[1847]
`fresh-model noise → post-gate`; seed 5 runs[1709] likewise; S6/k3 seed 3
runs[1553] `fresh-model noise → post-gate`. Sensitivity cells at L=6/24 moved
by the same onset flips (e.g. S3 seed 4 L=6: post 15→19, fresh 58→54; S3 seed
5 L=6: 31→37 / 50→44; S6 seed 3 L=24: 8→13 / 30→25). **S1/S7 base and their
stored sensitivity cells are unchanged by F1/F2** — the F3 cells (S1 L=24
1571/6, seed 1 319/1; S7 332/473/676) were already stored and remain verbatim.
`results/part1-profile.csv`: only the two `k3,S3` / `k3,S6` `mechanism_count`
row-groups move (post-gate 23→25 / 2.4→3.4 mean; fresh-model noise 67.6→65.6 /
19.4→18.4 mean). `markdown/part1-mechanism-table.md`: only the S3/k3 and S6/k3
rows move, base rows untouched. `part1-s4real.json` / `part1-real-flat.json`:
no mechanism-class changes (real pods are all-quiet ⇒ the F1 rule is a no-op
there; only gate-excluded `wall_s`/`git_head` churn).

### Gates (fix run)
```
$ .venv/bin/python -m pytest tests/test_harness_*.py tests/test_plotting_*.py -q
243 passed in 22.53s            # 0 skipped (was 238; +5 new tests)
$ .venv/bin/ruff check src/refstudy/harness src/refstudy/plotting \
    tests/test_harness_mechanism.py tests/test_harness_real.py tests/test_plotting_figure.py \
    tests/test_plotting_bands.py scripts/run_part1.py scripts/verify_part1_cutover.py
All checks passed!
$ git diff --check
(clean)
```
Stage 3 (limitation-profile note) was completed in the Stage 3 section below
(commit `1d7571a`). `results/a1a-parity.json` wall-seconds churn (pre-existing
test side effect) and the concurrent C1 `refcompare/*` changes stay unstaged.

## Stage 3 (commit `1d7571a` — `docs(refstudy): rewrite Part-1 limitation profile note in D-A three-class vocabulary`)

Owns `markdown/part1-limitation-profile.md` ONLY (120 lines, measured numbers
only; grep `fpr|false.?positive|warning|p_raw ?0\.2` hits only inside the one
re-label sentence). Content per the card: setup (0.2/0.8, three classes, p_raw
yardstick, former-"FPR" relabel with the not-pure-relabel caveat), §1 table per
scenario (und-band occupancy, decisive occupancy on quiet ticks, latency to
leave-normal / to decisive, settle, MAE), §2 failure modes, §3 over-fitting
verdict, §4 S5 gaps, §5 S7/S8 corrected (multi-seasonal structure, NOT 3×/5×
scale — per `config/scenarios.yaml`), §6 FLAT control + real flat (calm =
frac_normal ≥ 1 − max_outside_fraction), §7 caption regression (unchanged),
§8 S4-real verdict in three-class terms, §9 ESS gate (gated cycles serve NO
model, ticks unscored; gate-off scores all 1289 ticks; different scored
populations), §10 mechanism table = `markdown/part1-mechanism-table.md` base
rows + L=6/12/24 sensitivity incl. S1's small shift, §11 limits (p_raw
yardstick, calibration invisible, single cadence).

### Recomputed from the committed JSONs (5 numbers, stated in the note)
1. **S1 not-pure-relabel split, seeds 1–5 (per-seed `classes`, profile JSON):**
   old count (valid ticks p>0.2) = 1677 = undecided 100 + decisive 1577
   (per seed: 349/337/342/327/322; undecided 29/13/25/15/18; decisive
   320/324/317/312/304) ⇒ 1577/1677 = **94.0 %** of the old S1 count was
   decisive-anomaly; at_alpha = 0 so the exact identity holds.
2. **S1 seed-1 L=24 sensitivity cell (per-seed `mechanism.sensitivity`):**
   post-gate 318→319, fresh 2→1 (L=6: 318/2; L=12 base: 318/2; L=24:
   319/1); seed-summed 1570/7 at L=6/12 vs 1571/6 at L=24 — the small S1
   shift reported alongside S7's 332/473/676.
3. **Real-flat pooled class counts, from per-pod `n_valid` × fractions:**
   22150 normal / 89 undecided / 211 decisive of 22450 = 0.986637 / 0.003964 /
   0.009399 — exactly matching the stored pooled block;
   `calm = 0.986637 ≥ 0.98` = true (D-A iv).
4. **vlsl8 S4-real lab classes, from the raw `lab_p_raw` array (31 window
   ticks):** 15 normal / 5 undecided / 11 decisive = stored `lab_classes`;
   m7pr8 19/4/8 likewise; recorded decisive = 8–11 ticks on ALL 10 pods.
   Pre-episode recorded quiet floor 0.0013–0.0037 across the 10 pods
   (matches the lab 0.0013–0.0037).
5. **Gate-off decisive occupancy (ess_off aggregate means):** S1 0.396 (714
   scored on / 1289 off), S6 0.355; S2 decisive fraction of valid 0.052 on /
   0.188 off — the three-class gate-on vs gate-off comparison, different
   scored populations, no ranking without matched-tick analysis.

Also re-verified from the JSON: all 9 base-row mechanism counts (summed over
per-seed `mechanism.counts`), S7 sensitivity sums 64/332/1796, 64/473/1655,
64/676/1452, white-variant decisive occ (S1 0.438, S3 0.434, FLAT 0.000),
K=3 FLAT occ (und 0.078, dec 0.049), FLAT per-seed calm = false 5/5 (frac
normal 0.959–0.971 < 0.98; per-seed `calm` field) vs white FLAT calm true 5/5,
FLAT outside-band 0.098–0.122 (per-seed `outside_fraction`), real-flat
per-pod frac_normal 0.9764–0.9902 (vlsl8 the only non-calm pod), S3/S6
decisive latencies (S3 E1 151.8±38.5, S6 bump censored 5/5).

### Campaign-log lines (one per base scenario; S copies verbatim)
- S1: 1577 ticks > 0.8 — 1570 post-gate / 7 fresh-model noise: the strong diurnal shape trips the ESS gate (~45 % of cycles), so p_raw stays high in the quiet ticks right after each scoring resumption (a gated cycle within the 12-tick lookback of the episode onset); 94 % of the old "FPR" here was decisive, i.e. this is mostly carry-over decisive-anomaly, not noise.
- S2: 230 ticks > 0.8 — 195 injected-anomaly / 35 fresh-model noise: decisive ticks sit inside the injected mem-drift span (195) or in the post-onset fresh-model stretch; 0 post-gate.
- S3: 1851 ticks > 0.8 — 2 injected / 1826 post-gate / 23 fresh: only 2 ticks are inside the injected pulses; the rest are decisive quiet-tick runs that start within 12 ticks of a gated (no-model) cycle — the gated-seasonal carry-over, inherited by the whole episode.
- S4: 218 ticks > 0.8 — 137 injected-anomaly / 81 fresh-model noise: the two 18-tick bursts are decisively detected (137 inside the spans); the 81 fresh are post-bump reference-chasing excursions outside the spans; 0 post-gate.
- S5: 1979 ticks > 0.8 — 1957 post-gate / 22 fresh: with rx permanently in the cold-cycle case (gap, unscored), the other 9 metrics score ~44 % of cycles gated on the seasonal windows; the decisive quiet-tick runs resume right after gating; 0 injected (no anomaly spans).
- S6: 1656 ticks > 0.8 — 402 injected-anomaly / 1239 post-gate / 15 fresh: the injected mem-drift + burst carry 402; the diurnal+drift gating drives 1239 post-gate; a tiny 15 fresh residual.
- S7: 2192 ticks > 0.8 — 64 injected / 473 post-gate / 1655 fresh-model noise: the multi-seasonal structure (6 h + 7 h sines) is NOT resolved by the 570-block reference; the residual "fresh-model noise" is reference MISFIT to the unlearnable sub-daily periods, not stochastic noise; 64 decisive ticks inside the injected S4 bump.
- S8: 2401 ticks > 0.8 — 85 injected / 2316 fresh-model noise: same misfit mechanism, worse (3 h + 2.5 h periods, dominant amplitude); 85 decisive inside the injected bump; 0 post-gate (gate silent: ESS median 418.8).
- FLAT: 55 ticks > 0.8 — all 55 fresh-model noise: the quiet-state floor of the factor-AR(1) noise law at K=11 (0 % cycles gated, no anomaly spans); these are the 6-tick Markov-sojourn decisive runs at the point-mass reference.
