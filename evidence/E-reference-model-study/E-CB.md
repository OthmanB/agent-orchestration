# E-CB — candidate-B executor evidence (CB-1)

Executor E, slice CB-1 of `evidence/omp-workcards/refm-CB.md` (D-S5).
Commit: `482e3ea feat(refstudy): add candidate-B trend primitives, span/trend config keys and boxcar digest fixture (CB 1.0-1.3)`
Lab head before the commit: `25752fc4a859c51d5f5204adff7905e126fae322` (DB 1.2, peer-committed in flight).

## CB-1 (2026-11-10, JST ~11:25)

### 1.0 PREFLIGHT (before touching `src/` or `config/`)

`git status` in owned paths: clean (only the in-flight DB-slice files were dirty:
`results/a1a-parity.json` timing-only rewrite, untracked
`src/refstudy/harness/mechanism.py` + `tests/test_harness_mechanism.py` — not staged by me).

Baseline `.venv/bin/python -m pytest tests -q` (pre-CB tree): green except the in-flight
DB-slice files — see "Full-suite gate" below for the recorded red set.
Pre-existing `results/a1a-parity.json` dirty diff: 60 leaf diffs, ALL `wall_seconds`
(timing); zero `*delta*`/`*mismatch*`/unexplained leaves vs `git show HEAD:…` (checked
with an inline leaf-diff snippet; recorded before starting, no gate loosened).

### 1.0 digest fixture (pre-change, on the unchanged tree)

Created `tests/test_reference_trend.py` with ONLY `digests() -> dict[str,str]` +
`test_boxcar_default_is_bit_exact` + the `__main__` writer (no `trend` imports yet).
Ran on the unchanged tree:

```
$ .venv/bin/python tests/test_reference_trend.py
wrote …/tests/fixtures/candb_boxcar_digests.json (192 digests, head 25752fc4a859c51d5f5204adff7905e126fae322)
```

192 digests = 6 scenarios {S1,S2,S3,S4,S6,FLAT} × 4 continuous signals × 8
`ReferenceRun` fields {forecast, model_t0, fit_end, ess, rec_lo, rec_hi, rec_ts,
rec_val}; key scheme `S1/cpu/forecast`; `blocks = scenario.blocks(cfg)[canon]`,
`ticks = blocks.origin + T*arange(1, n+1)`, `StlLiteProvider(cfg).run(blocks, ticks)`,
sha256 of the float64/int64 array bytes. `generated_at_head` = 25752fc4 (= HEAD at
generation; the provider path is byte-identical to the pre-CB tree — CB-1 executes no
provider hook, which the green digest test below re-confirms after the config/YAML
change lands).

### 1.1 `src/refstudy/reference/trend.py` (numpy only, no cfg/stl_lite imports)

- `boxcar_trailing(values, width, *, inclusive)`: cumsum-based trailing mean.
  Exclusive `d_i = mean(y[max(0,i-W):i])` (strictly older blocks, shrinking head,
  NaN at i=0); inclusive `mean(y[max(0,i-W+1):i+1])`. `width < 1` (and bool) →
  `ValueError`.
- `adaptive_one_step_residuals(values, bins, width, *, min_lag, phase_bins)`:
  `e_i = y_i − (d_i + S_i(bin_i))` for i ≥ min_lag (NaN below); `r_s` accumulated
  only for s ≥ min_lag; `S_i(j) = mean{r_s: m0≤s<i, bin_s=j} − mean{r_s: m0≤s<i}`;
  empty bin / no history ⇒ 0 (legacy empty-bin rule). Vectorised: per-bin cumsum +
  searchsorted prefix sums, no Python loop over i.
- `legacy_one_step_residuals(values, bins, *, min_lag, phase_bins)`: sentinel
  growing-prefix rule (prefix-mean trend, per-bin raw prefix means, empty bin ⇒
  trend only) — the exact one-step residuals of the running STL-lite state.

Bug found and fixed during 1.3 test authoring (recorded, not worked around): the
first `_prefix_bin_sums` version counted blocks `s < min_lag` in the per-bin counts
(their `r` is zeroed but the position was still in the bin's position set), so a bin
with pre-warm-up history was treated as non-empty and `S` was computed from a zeroed
"bin mean". Fixed by restricting the per-bin position sets to `s ≥ start`
(`start=min_lag` for the adaptive path, 0 for legacy). After the fix the explicit-loop
reference test passes at 1e-9.

### 1.2 config keys

`src/refstudy/reference/config.py`:
- `SpanConfig(grid_min_minutes, grid_max_minutes, n_grid, criterion)` (frozen slots)
- `TrendConfig(method, span: SpanConfig | None = None)` (frozen slots)
- `ContinuousBaseline.trend` — new LAST field (grep verified: `ContinuousBaseline(`
  is constructed only at `config.py:228` pre-change; no other constructor unpacks it)
- `parse_trend(cfg, prefix, *, tick_seconds, period_seconds)`:
  `method ∈ {boxcar, adaptive}`; **boxcar with a `span` key → ValueError naming
  `<prefix>.span`**; adaptive requires `span` with all four keys (each missing key
  named via `require` at the full dotted path); `grid_min·60 ≥ tick_seconds`;
  `grid_min < grid_max`; `grid_max·60 ≤ period_seconds/2`; `n_grid ≥ 2` int;
  `criterion ∈ {cv1, ess}`; bool rejected everywhere a number is required.
- `with_trend(cfg, trend) -> RefConfig` (dataclasses.replace chain; original frozen
  untouched).
- `load_reference_config` now parses `baseline.continuous.trend` via `parse_trend`.

`config/reference.yaml` — additive block only (provenance-commented "lab-only study
key, no production counterpart; … vision §3.1 span.method gradient/fallback not
ported — grid only, fallback is structural"):

```yaml
    trend:
      method: boxcar
```
(the adaptive `span` form is shown as a comment; the live adaptive block lives in
`config/candb.yaml` for CB-4).

### 1.3 tests

`tests/test_reference_trend.py` (appended, same file as 1.0):
- `test_adaptive_one_step_residuals_match_explicit_loop` — vs an explicit-loop
  reference of the workcard definitions, `atol=1e-9` (K=400, W=25, m0=48, seeded
  diurnal+noise series)
- `test_adaptive_empty_bin_gives_trend_only` — single-bin ⇒ `e_i = y_i − d_i`
  exactly (1e-12)
- `test_adaptive_min_lag_head_is_nan_and_short_window_all_nan`
- `test_legacy_one_step_residuals_match_stl_lite` — vs
  `stl_lite.rolling_one_step_residuals` at `atol=1e-9` on S1/cpu, S2/mem,
  FLAT/rx_bytes (bins via the literal `phase_of`; scenario origin is not a bin
  boundary, so `i % 48` would be wrong)
- causality: `e_i` (both adaptive and legacy) bit-identical when `y[j>i]` is
  scrambled
- `test_boxcar_trailing_matches_brute_force` — `np.mean` brute force, rtol 1e-12,
  both `inclusive` modes, W ∈ {1, 3, 47, 100, 600}
- validation (width 0 / bool width)
- `test_boxcar_default_is_bit_exact` — the 1.0 fixture guard

`tests/test_reference_trend_config.py`: default = boxcar/no span (both via
`load_reference_config` and `parse_trend` on the YAML dict); adaptive parses all
four keys; every error path with the dotted key named (missing trend block, missing
method, bad method, boxcar+span forbidden naming `<prefix>.span`, adaptive missing
span, span not a mapping, each of the four span keys missing named individually,
all six span value violations, bool-for-number for all five number/str keys);
`with_trend` leaves every other field equal (field-by-field, plus deep
`dataclasses.replace` equality); round-trip boxcar back to the original config.

### Gate results (all at commit time)

```
$ .venv/bin/python -m pytest tests/test_reference_trend.py tests/test_reference_trend_config.py -q
.........................................                                [100%]   # 41 passed, 0 skipped

$ .venv/bin/ruff check src tests scripts
All checks passed!

$ git diff --check            # clean (exit 0)

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/reference
(empty; grep exit 1)

$ .venv/bin/python scripts/run_parity.py --config config/reference.yaml --stage 1
exit 0. Table (verbatim):
section            max|delta|  notes
P0                          0  n_keys=29
P1                          0
P2                          0  n_blocks=912
P2a                         0  n_cases=48
P2b_counter                 0  n_cold=3, n_cycles=27, n_steady=24
P2b_gauge                   0  n_cold=3, n_cycles=27, n_steady=24
P2b_rare_count              0  n_cycles=27
P3                          0  n_scored=713
P4                         22
P4/<10 pods>                -  variant=restart_replay comparable=287
                               replay_unexplained=0 … p_family_after_prefix=0
                               passed=True   (all 10 pods)
P4b/<10 pods>               0.519–0.988   common/match/mismatch/in_burst=intervals
                               per-pod values unchanged vs committed (see below)

(the P4 section value 22 is the max of the 143 committed P4 delta/mismatch
leaves — present identically in the committed `results/a1a-parity.json`; the
leaf-diff below proves the re-run left every one of them unchanged.)

$ .venv/bin/python -m pytest -m parity -q
...............................                                          [100%]   # 31 passed
```

Bit-exactness of the parity re-run vs the committed `results/a1a-parity.json`:
inline leaf-diff snippet compared every leaf; **0** differences in any
`*delta*`/`*mismatch*`/`replay_unexplained`/`strict`/`comparable` leaf (P0–P3
max|Δ| = 0.0 as committed; P4: 0 unexplained after the 48-tick prefix on all 10
pods; P4b per-pod match/mismatch counts unchanged). The only leaf differences were
60 `wall_seconds` timing leaves (e.g. `/P2/wall_seconds 0.1086039999499917 →
0.13452304201200604`, `/P4/pods/2vwwd/wall_seconds 7.352020041095593 →
7.130770124777347`) — the re-run rewrites the file, so it was restored with
`git restore results/a1a-parity.json` after the numeric comparison, per the card.

### Full-suite gate (`pytest -m 'not parity' -q`)

41 new tests green, 0 skipped. The full suite's remaining reds are EXACTLY the
in-flight concurrent DB-slice files and their direct dependents (all fail inside
uncommitted peer files `src/refstudy/harness/evaluate.py` — `occupancy()` gained a
keyword-only `decisive` argument — and `src/refstudy/harness/aggregate.py:82` —
reads a `mechanism` key not yet produced by the committed evaluate path):

```
tests/test_harness_evaluate.py      11 ERROR/FAILED  (harness.metrics false_positive_rate -> occupancy()/decisive)
tests/test_plotting_figure.py        9 ERROR         (same harness.metrics dependency)
tests/test_refcompare_evaluate.py    4 FAILED        (TypeError: occupancy() missing 'decisive')
tests/test_refcompare_sidebyside.py  4 FAILED        (KeyError: 'mechanism' at harness/aggregate.py:82)
```

No other failures; all remaining tests pass. (At preflight the first three files
failed with `AttributeError: harness.metrics has no attribute false_positive_rate`;
the peer's in-flight edits moved the failure signature between my preflight and
gate runs — both are the same in-flight DB slice, none are mine.)

### Commit

```
git add src/refstudy/reference/trend.py src/refstudy/reference/config.py \
        config/reference.yaml tests/test_reference_trend.py \
        tests/test_reference_trend_config.py tests/fixtures/candb_boxcar_digests.json
git commit  →  482e3ea feat(refstudy): add candidate-B trend primitives, span/trend
               config keys and boxcar digest fixture (CB 1.0-1.3)
```

6 files, 962 insertions(+), 2 deletions(-). `git diff --check` clean; no
trailer; nothing pushed; the only foreign paths ever touched were `git restore`
of `results/a1a-parity.json` (parity re-run timing leaves).

### Open issues / notes for CB-2..CB-3

- `parse_trend` span-geometry error messages prefix `config key <prefix>.trend.span:`
  (not the full dotted path) — the missing-key errors use the full dotted path via
  `require`; behaviour matches the card, wording is as recorded in
  `tests/test_reference_trend_config.py`.
- The fixture's `generated_at_head` is 25752fc4 (the DB 1.2 commit), not the
  campaign-start head; the provider path it digests is byte-identical to the
  pre-CB tree (no CB-1 file touches `stl_lite.py`/`provider.py`), so the
  "pre-change" property holds.
- CB-2/3: `legacy_one_step_residuals` already matches
  `rolling_one_step_residuals` to 1e-9, so the CB-3 sentinel-routing test can rely
  on that identity; `adaptive_one_step_residuals` is ready for `select_width`.

## CB-2 (2026-11-10, JST ~12:25)

Commit: `5843a09 feat(refstudy): add candidate-B width selector select_width with cv1/ess criteria and degenerate fallbacks (CB 2)`
Lab head before the commit: `dd9c255` (DB 1.3, peer-committed in flight). 2 files, 585 insertions: `src/refstudy/reference/trend_select.py`, `tests/test_reference_trend_select.py` (both new; no existing file touched — CB-2 does not touch provider or parity-imported code).

### Implementation (`reference/trend_select.py`, numpy only)

- `candidate_widths(span: SpanConfig, tick_seconds: float) -> tuple[int, ...]`:
  `round(geomspace(grid_min·60/T, grid_max·60/T, n_grid))` → unique, sorted,
  ascending ints; `tick_seconds <= 0` / bool and non-ascending spans rejected
  with named `ValueError`s. 30–720 min, n_grid 32, T=300 → 32 geomspace points
  with ONE rounding collision → 31 uniques, first 6, last 144 (pinned in the
  grid test). The `< K` filter is applied inside `select_width` (the card's
  "only those `< K`").
- `Selection(width, criterion, scores, sentinel_score, reason, resid)` —
  frozen slots; `width None` = sentinel (legacy full window); `resid` =
  `adaptive_one_step_residuals` of the chosen finite width (reused verbatim by
  the CB-3 hook), `None` for the sentinel and all degenerate reasons.
- `select_width(values, bins, candidates, *, min_lag, phase_bins, criterion,
  ess_max_lag, const_tol) -> Selection` — pure, inputs not mutated:
  - `cv1` (default for adaptive, the D-S5 operator choice): `mean|e_i|` over the
    common sample `i >= min_lag`; every candidate and the sentinel scored on
    the SAME out-of-sample, leak-free sample.
  - `ess` (vision §2.1, diagnostic only, never a default):
    `bartlett_ess(e[m0:], ess_max_lag)/len(e)`; ties keep the smaller width;
    asserted degenerate in the tests (see below).
  - Sentinel = `legacy_one_step_residuals` (the adaptive formula at W=K is not
    the legacy rule — R-candB §3.1 correction — hence the separate path). A
    challenger must be STRICTLY better; the sentinel wins only if strictly
    better.
  - Degenerate reasons (check order: `short_window` K ≤ min_lag, then
    `nonfinite`, then `no_candidates` (nothing `< K`), then `constant_window`
    `ptp(y) <= const_tol·max(1,|mean y|)` with `const_tol` =
    `constants.gauge_epsilon` (reused 1e-9 literal; R-candB CONTRADICTION-8
    wrong for the lab)) ⇒ `width None`, `scores {}`, `sentinel_score None`,
    `resid None`, no NaN, no ZeroDivisionError.

### Tests (`tests/test_reference_trend_select.py`, 16 tests, seeded, behaviour)

- `test_selector_has_interior_optimum` (card test 6, cv1 half): seeded
  local-level series, the card's literal parameters (random-walk step sd 0.08
  + white sd 1.0, K=570, seed 20261110; the optional diurnal component NOT
  added — with it the one-step MAE optimum is dominated by the 288-block
  period and the grid's lower bound wins; the card authorises "tune series
  params, never the selector"). `cv1` returns `width = 34`, strictly inside
  the grid bounds (6, 144) and inside `12 <= W <= 72`; the sentinel is scored
  strictly worse; the winner is the smallest width tied for the best score
  (tie-break pinned); `resid` has the full-window shape.
- `test_ess_criterion_degenerate_smallest_width` (card test 6, ess half, and
  workcard item (b)): on `get_scenario({S1/cpu, S2/mem, FLAT/cpu}, seed=1)`
  570-block windows at offsets 0/48/96 (9 windows; bins via the literal
  `phase_of`, not `i % 48` — the scenario origin is not a bin boundary),
  `criterion="ess"` selects `candidates[0]` (= 6) on **all 9/9 windows**
  (their ess scores tie for the maximum at the clamp value; the tie keeps the
  smallest width) — the vision objective is degenerate, CONFIRMED, no miss ⇒
  nothing to record as a finding. The assertion is not weakened.
- Degenerate reasons (workcard item (c), R-candB test 7): `short_window`
  (K == min_lag), `nonfinite` (one NaN block), `no_candidates` (candidates
  60/90 on K=50), `constant_window` (three shapes: exact constant 3.14,
  zeros, 1e-12-absolute ramp — all at/below the gauge floor; plus a 1e-6 ramp
  just above the floor asserting `reason == "finite"` so the sentinel is not
  over-triggered). All: `width None`, empty scores, no NaN, no
  ZeroDivisionError.
- (e) `test_scores_match_adaptive_mae_and_sentinel`: every `scores[w]` equals
  `mean|adaptive_one_step_residuals(...)[m0:]|` at atol 1e-12; the sentinel
  score equals the legacy-rule MAE; the `< K` filter: on a K=50 window exactly
  the sub-K candidates are scored, in ascending order.
- Determinism + inputs unchanged (workcard item "bit-identical twice"): two
  calls → equal `width/reason/scores/sentinel_score` and
  `np.array_equal(resid, equal_nan=True)`; `values`/`bins` byte-identical
  after; the `ess` path likewise deterministic.
- Leak-freeness (the candidate FORECAST of a block never reads that block;
  the residual/loss do read the target — see (iii)): (i) tail scramble — the
  last 12 blocks perturbed with seeded
  noise; for EVERY candidate width the residuals `e_j` for `j < K-12` are
  bit-identical before/after, and the legacy residuals likewise; (ii)
  single-block self-exclusion — perturbing ONLY `y[i0]` leaves every
  `e_j` for `j < i0` bit-identical and shifts `e_{i0}` by EXACTLY the
  perturbation (i.e. the forecast `F_{i0}` is invariant to its own block);
  (iii) `test_selection_scores_are_prefix_causal` — for every candidate and
  the sentinel, the candidate FORECAST of block `i` is prefix-causal (reads
  only blocks `< i`), so the residual `e_j = y_j - F_j` on the prefix `y[:401]`
  is bit-identical to the full window for `j <= 400` (it depends on `j`'s own
  target `y_j` and on blocks `< j`, never on blocks at/after `j`).  The width
  is NOT prefix-selected: it is chosen over the whole fitted training window
  and depends on every target in it; leakage safety of the served forecast
  holds at the served tick's fit cutoff, which the scramble checks establish.

### Gate results (all at commit time)

```
$ .venv/bin/python -m pytest tests/test_reference_trend_select.py tests/test_reference_trend.py tests/test_reference_trend_config.py -q
.........................................................                [100%]   # 57 passed (16 new + 41 CB-1), 0 skipped

$ .venv/bin/ruff check src tests scripts
All checks passed!

$ git diff --check            # clean (exit 0)

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/reference
(empty; grep exit 1)
```

Parity (the card's CB-2 gate says "no parity needed" since CB-2 touches no
parity-imported module; re-run anyway as a belt-and-braces check):

```
$ .venv/bin/python scripts/run_parity.py --config config/reference.yaml --stage 1
exit 0. Table (verbatim summary): P0 0 (n_keys=29), P1 0, P2 0 (n_blocks=912),
P2a 0 (n_cases=48), P2b_counter 0, P2b_gauge 0, P2b_rare_count 0, P3 0
(n_scored=713), P4 22 (max of the committed P4 leaves), P4 per-pod
(restart_replay, all 10 pods): comparable=287, replay_unexplained=0,
p_family_after_prefix=0, passed=True; P4b per-pod values 0.519–0.988 with the
committed per-pod match/mismatch/in_burst/intervals counts (identical to the
committed JSON, leaf-diff below).

$ .venv/bin/python -m pytest -m parity -q
...............................                                          [100%]   # 31 passed

Leaf-diff `results/a1a-parity.json` re-run vs `git show HEAD:…` (inline
snippet over every leaf): 60 leaf diffs, ALL `wall_seconds`/timing leaves;
**0** differences in any `*delta*`/`*mismatch*`/`*unexplained*`/`strict`/
`comparable` leaf. The re-run rewrites the file, so it was restored with
`git restore results/a1a-parity.json` afterwards (once after the run_parity
re-write, once after the pytest -m parity re-write; both verified all-timing
before restoring).
```

Full suite (same gate as CB-1): my three test files green, 0 skipped; the
remaining reds are EXACTLY the in-flight concurrent DB-slice files (peer's
uncommitted `harness/`/`plotting/` edits moved the failure signature between
CB-1's and CB-2's runs — same slice, none mine):

```
tests/test_harness_evaluate.py      ERROR/FAILED (occupancy()/decisive in-flight)
tests/test_harness_profile.py        2 FAILED (KeyError 'frac_normal'/'class_fraction', in-flight)
tests/test_plotting_figure.py        4+ FAILED (KeyError 'fpr', in-flight)
tests/test_refcompare_evaluate.py    2+ FAILED (KeyError 'fpr', in-flight)
tests/test_refcompare_sidebyside.py  4 FAILED (KeyError 'mechanism' at harness/aggregate.py, in-flight)
```

(Excluding exactly those five in-flight files, the rest of the suite passes.)

### Commit

```
git add src/refstudy/reference/trend_select.py tests/test_reference_trend_select.py
git commit → 5843a09 feat(refstudy): add candidate-B width selector select_width with
            cv1/ess criteria and degenerate fallbacks (CB 2)
```

2 files, 585 insertions(+). `git diff --check` clean; no trailer; nothing
pushed; the only foreign path ever touched was `git restore` of
`results/a1a-parity.json` (parity re-run timing leaves, verified all-timing
first).

### Open issues / notes for CB-3

- `select_width` returns `reason == "finite"` for every scored window (the
  four degenerate reasons only on degenerate input); the CB-3 hook's
  `sel.width is None` check covers BOTH the sentinel win and the degenerate
  reasons uniformly (both serve `prior.F`).
- `resid` from a finite win is the FULL-window `e` (NaN for `i < min_lag`);
  the CB-3 record rule takes exactly its last `len(new_ts)` entries, as the
  card's record rule specifies.
- The degenerate `constant_window` test pins the gauge floor at BOTH sides
  (1e-12 ramp ⇒ sentinel; 1e-6 ramp ⇒ scored) so a future `const_tol` change
  cannot silently over-trigger the sentinel.
- Determinism of `criterion="ess"` is asserted on the same seeded series
  (bit-identical scores/sentinel across calls), mirroring the cv1 guarantee.

## CB-3 (2026-11-10, JST ~13:40)

Commit: `c8c1b9f feat(refstudy): add candidate-B AdaptiveStlState provider integration and parity re-run (CB 3)`
2 files, 439 insertions(+), 4 deletions(-): `src/refstudy/reference/stl_lite.py` (hooks H1–H7 only), `tests/test_reference_trend_provider.py` (new, 8 tests). Lab head before commit: `48f8050` (DB 1.4, peer-committed in flight — a later commit, `run_part1.py` docstring only, is not mine).

### Implementation (hooks in `reference/stl_lite.py`, EXACT list)

- **H1** imports: `trend`, `trend_select` (`Selection`, `candidate_widths`, `select_width`), `config.TrendConfig`.
- **H2** `CycleReport.trend_width: int | None = None` appended (positional constructors keep working; exercised in test 7).
- **H3** `_Prior.served: AdaptiveStlState | None = None` appended.
- **H4** `AdaptiveStlState` (after `StlLiteState`): `fit(cls, ts, val, width, cfg)`, `forecast(t1)`, `snapshot()` plain dict. `level = mean(val[max(0,K−W):K])` (INCLUSIVE of the last fitted block — `fit_end`); `d_s = mean(val[max(0,s−W):s])` exclusive; `r_s = val_s − d_s` accumulated only for `s ≥ min_lag`; `S(j) = mean{r: bin=j} − mean{r}` over the whole fit window; empty bin / no accumulated residual ⇒ level only. NOTE: `fit` takes ANY width ≥ 1 with a shrinking head when `K < width` (the card's independent recomputation `fit(win[:i])` needs it for early blocks); the provider only ever passes the selected finite width (< K, enforced by `select_width`).
- **H5** `StlLiteProvider.__init__`: stores `cfg.baseline.continuous.trend`; adaptive ⇒ `candidate_widths(span, T)`; unknown method ⇒ `ValueError`.
- **H6** `_cycle`, right after the ESS gate: `sel = self._select(win_ts, win_val)` (None for boxcar; pure function of the window, bins via the literal `phase_of`); at BOTH `log_val.extend(new_r)` sites → `self._adopt(new_r, sel, K)` (returns `sel.resid[K−len(new_r):]` for a finite width, `new_r` otherwise, length assert); after `new_prior = _Prior(…)` ⇒ `new_prior.served = AdaptiveStlState.fit(win_ts, win_val, sel.width, cfg)` iff finite; `trend_width=sel.width` on the built `CycleReport` (None for sentinel/degenerate/boxcar).
- **H7** `run`: `model = prior.served if prior.served is not None else prior.F` for the forecast line. `provider.py`, `pipeline.py`, `harness/ess.py` unedited (they build `StlLiteProvider(cfg)`; the ESS-gate stream is consumed positionally, H2 default keeps parity-imported construction working).

### Tests (`tests/test_reference_trend_provider.py`, adaptive = `with_trend(ref, TrendConfig("adaptive", SpanConfig(30,720,32,"cv1")))`; S1/S2/FLAT cpu seed 1; first 2 days of cycles = 97 cycles, 1158 ticks)

1. `test_sentinel_equals_current` — monkeypatch `stl_lite.select_width` → sentinel (`Selection(width=None)`): every `ReferenceRun` array `array_equal(equal_nan=True)` to the boxcar run on all 3 scenarios; all `trend_width` None. PASSED — sentinel routing is byte-for-byte the legacy path.
2. `test_no_leakage_adaptive` — `check_no_leakage` passes (all 3 scenarios) AND S1/cpu has finite-width cycles (observed: widths 10–12 ≈ 0.9–1.2 h in the first 2 days; S2/FLAT cpu frequently pick the sentinel — expected from R-candB §4.2, not a failure).
3. `test_record_is_causal` — THE RECORD RULE (the card's riskiest assumption): every entry of the first cold built cycle's `record_val` (522 entries, blocks 48..569) AND the last-6 entries of the next steady cycle equal `y_i − AdaptiveStlState.fit(win[:i], W).forecast(ts_i)` at 1e-9 with W from `on_cycle` (observed widths 11, 11; record offsets: cold = `K−522 = 48`, steady = `K−rec.size` via the retained+entered geometry; the last-6 record entries are asserted to be exactly the 6 entered blocks). PASSED at 1e-9 — the "last `len(new_r)` entries of `sel.resid`" rule holds on BOTH geometries; no STOP, no bending.
4. `test_warmup_head_not_poisoned` — level 1000 + N(0,1), K=570, W=24: `e[:48]` NaN, `|e_i| < 10` for i ≥ 48 (max ≈ 3.2), and `fit` on exactly 48 blocks ⇒ `n_resid = 0`, empty bins, forecast = level for every bin (guards R-candB's +252.8 trap; the vision's `d_0 = 0`/shrinking head is NOT implemented).
5. `test_gate_unchanged` — the `(t0, reason, fit_end, ess)` stream of `on_cycle` is IDENTICAL boxcar vs adaptive on S1/S2/FLAT (elementwise; NaN-safe ESS compare), the gated-cycle SETS equal, and `fit_end`/`model_t0`/`ess` ReferenceRun arrays `array_equal(equal_nan=True)` (the guard reads raw blocks ⇒ identical gated set, as the card requires).
6. `test_adaptive_deterministic` — two S2/cpu adaptive runs bit-identical (all 8 arrays, widths, reasons).
7. `test_boxcar_trend_width_is_none` — every boxcar `CycleReport.trend_width is None`; positional `CycleReport(...)` still works.
8. `test_built_cycle_widths_are_valid` — every built cycle's width ∈ {None} ∪ grid ∩ [1, 570); S1/cpu has a finite width; leak-free.

### Parity acceptance (same slice, REQUIRED)

```
$ .venv/bin/python scripts/run_parity.py --config config/reference.yaml --stage 1   → exit 0
P0  (constants), P1 0, P2 0 (n_blocks=912), P2a 0 (n_cases=48), P2b_counter 0
(n_cold=3, n_cycles=27, n_steady=24), P2b_gauge 0, P2b_rare_count 0, P3 0
(n_scored=713), P4 22 (max of the 143 committed P4 leaves), P4/<10 pods>
(restart_replay): comparable=287, replay_unexplained=0, strict=0,
p_family_after_prefix=0, passed=True — all 10 pods; P4b per-pod
0.519–0.988 with the committed per-pod common/match/mismatch/in_burst/intervals.

$ .venv/bin/python scripts/run_parity.py --config config/reference.yaml --stage 2 → exit 0 (same table)

$ .venv/bin/python -m pytest -m parity -q
...............................   [100%]   # 31 passed, 0 skipped
```

Bit-exactness: inline leaf-diff snippet over EVERY leaf of the re-run
`results/a1a-parity.json` vs `git show HEAD:…`: **60** leaf diffs, ALL
`wall_seconds`/timing (load/replay/total/total_wall_seconds) — the same
pre-existing dirty set recorded at CB-1 preflight; **0** differences in any
`*delta*`/`*mismatch*`/`replay_unexplained`/`strict`/`comparable`/`ess`/
`fit_end`/`forced_gaps` leaf. P0–P3 max|Δ| = 0.0; P4 0 unexplained after the
48-tick prefix on all 10 pods (environment-event replay); P4b unchanged.
`results/a1a-parity.json` restored with `git restore` afterwards, per the card.

### Gates at commit time

- `.venv/bin/python -m pytest tests/test_reference_trend.py tests/test_reference_trend_config.py tests/test_reference_trend_select.py tests/test_reference_trend_provider.py tests/test_reference_provider.py tests/test_reference_stl_lite.py tests/test_reference_pipeline.py tests/test_reference_chain.py tests/test_reference_gold_fixture.py -q` → **115 passed, 0 skipped** (41 CB-1 + 16 CB-2 + 8 new + 50 legacy reference tests; the CB-1 boxcar digest test `test_boxcar_default_is_bit_exact` green after the hook change — the boxcar path executes no adaptive numerical work; the dispatch hooks run and return identity/legacy values).
- `.venv/bin/ruff check src tests scripts` → All checks passed!
- `git diff --check` (owned paths) → clean; explicit `git add src/refstudy/reference/stl_lite.py tests/test_reference_trend_provider.py` (no `-A`, no trailer, no push).
- Full non-parity suite: **6 FAILED, all in the peer's in-flight DB/D-B files** — `test_refcompare_evaluate.py` (2, `KeyError: 'fpr'`) and `test_refcompare_sidebyside.py` (4, `KeyError: 'mechanism'` at `harness/aggregate.py:82`), same D-B re-expression root cause as CB-1/CB-2; every other test passes. No other foreign file touched (`scripts/run_part1.py` was already dirty in-flight by the peer when I started — docstring only, NOT staged by me).

### Open issues / notes for CB-4

- S1/cpu cv1 winner ≈ 10–12 blocks (~1 h) in the first 2 days — consistent with R-candB §4.2 (1–1.5 h interior optimum). S2/FLAT cpu frequently take the sentinel (cv1 prefers the full window there, R-candB §4.2 "regresses flat/white by 5–10%") — CB-4's headline will show it.
- `AdaptiveStlState.fit` is O(K) with a Python loop over emitted bins (≤48 bins, ≤570 blocks): negligible vs the 30-min cadence; the selector (CB-2) is the hot part (O(grid·K·L) with L=144).
- `Selection.reason == "finite"` is the only non-degenerate reason; the provider's `sel.width is None` check covers sentinel-win AND all four degenerate reasons uniformly (both serve `prior.F`).
- The `assert self._candidate_widths is not None` / `assert self._trend_cfg.span is not None` in `_select` are unreachable (guarded in `__init__`); they keep the type checker honest without a runtime branch on the boxcar path.

## CB-4.1 (2026-11-11, JST ~02:10)

Commit: `7fc2709 feat(refstudy): add candidate-B measurement library, candb config and measure tests (CB 4.1)` (lab head before: `9277c0d`; 5 files, 1509 insertions: `config/candb.yaml`, `src/refstudy/candb/{__init__,config,measure}.py`, `tests/test_candb_measure.py`).

### `config/candb.yaml` (all keys required)

`harness_config` (pointer, resolved relative to the study dir), the candidate-B `trend` block `{method: adaptive, span: {grid_min_minutes: 30, grid_max_minutes: 720, n_grid: 32, criterion: cv1}}` (parsed by the SAME `parse_trend` as `reference.yaml`, via a `{"candb": {...}}` wrapper so error messages carry the `candb.trend.*` dotted paths of this file), `workers: 4`, `fidelity.drift {scenarios: [S2], signals: [mem, cpu], min_level_move: 5.0}`, `age.stale_hours: 6.0`, `sequencing {scenarios: [S1,S2,FLAT], signals: [cpu, mem], stride_cycles: 12}`, `outputs {profile_json, figures_dir}`. Scenario/signal names are validated against the loaded `ScenariosConfig`.

### `candb/config.py`

`load_candb_config(path, hcfg=None) -> CandbConfig` (frozen slots: `study_dir, hcfg, trend, workers, drift: DriftFidelity, stale_hours, seq_scenarios, seq_signals, stride_cycles, outputs`). Every key via `require` (missing/mistyped -> ValueError naming the dotted key); `trend.method` must be `adaptive` (the B arm) with a span; `workers >= 1`, `min_level_move > 0`, `stale_hours > 0`, `stride_cycles >= 1`; the two name lists are cross-checked against the harness config (unknown scenario/signal -> ValueError listing both).

### `candb/measure.py`

- `forecast_vs_clean(forecast, clean, mask) -> {bias, mae, rmse, n}` on `e = forecast - scenario.clean[sig]` (positive = model above truth); NaN forecast/clean drop out; `n == 0` -> `None` statistics (a finding, not a default); unequal lengths -> ValueError.
- `drift_affected_mask(fit_end, origin, chain, clean, min_level_move)`: S2 selection — a served tick whose model's fit window `[i_s, i_e)` (`W = (Dt-dt)/T = 570` blocks, `i_e = round((fit_end-origin)/T)`) has `|clean[i_e-1] - clean[i_s]| >= min_level_move`; NaN fit_end / `i_s < 0` / below-threshold move -> not affected.
- `model_age_h(fit_end, ticks, stale_hours) -> {p50, p90, max, frac_gt_stale, no_model_fraction, n_model}` (hours, `stale_hours` from `age.stale_hours`).
- `cycle_report(pod, scenario, chain)`: ONE provider re-run per continuous metric with `on_cycle` (forecast equality checked against the evaluated pod, as `harness.ess.ess_diagnostics` — divergent re-run -> ValueError) -> per metric the `harness.ess.metric_ess` block + the width block `{n_built, n_sentinel, sentinel_fraction, hist{width_blocks: count}, median_blocks}` from `CycleReport.trend_width` (built cycles only; `n_sentinel` counts `trend_width is None` = sentinel win + degenerate fallbacks; `None` for the boxcar chain).
- `guard_fractions_equal(a, b)`: the guard equality assertion — every `GUARD_KEYS` entry (`cycles, built_cycles, ess_gated_cycles, ess_gated_fraction, ticks_with_model, stale_ticks`) of every metric must agree A vs B, else ValueError naming metric/key; -> per-metric gated fractions of both arms.
- `arm_candb_block(pod, result, scenario, chain, ccfg)`: the per-run B extras — `fc_vs_clean` per signal over `all` valid-with-model ticks and, on `fidelity.drift.scenarios`, `drift_affected` over `fidelity.drift.signals`; `model_age_h` per signal; `cycle_report`.
- `arm_chain(hcfg, ccfg, *, arm, gate_on, ess_floor)` / `run_arm(scenario, seed, *, arm, gate_on, hcfg, ccfg, ess_floor, n_ticks=None) -> EvalResult`: the per-scenario/seed runner — arm A = the unchanged `hcfg.ref_synth` chain (`trend.method boxcar`), arm B = `with_trend(ref_synth, candb trend)`; gate off = `gate_off_chain(chain, ess_floor)` (the `sensitivity.ess_gate_off.floor` of harness.yaml, same helper as the Part-1 ess_off sensitivity); `get_scenario` -> `run_checked` (leak check included) -> `evaluate_records`. This is the 4.3 worker's per-arm call, extracted here so both arms of one generated scenario share the yardstick.
- `three_class_regressions(a_per_seed, b_per_seed)`: D-A non-regression of B over A on EVERY three-class quantity, per seed: `undecided_occupancy.rate` / `decisive_occupancy.rate` of B <= A; every event `leave_normal.latency` / `decisive.latency` B <= A (censored = `None` -> `+inf`); `p_raw_summary.frac_normal` B >= A; every `q05..q99` mean B <= A. -> `{violations, n_checked, pass}`; a regression is a finding, never a default.
- `decision_readout(profile)`: the MECHANICAL read-out of the vision section-6 rule, labelled as such (the A/B/C recommendation stays with Phase E). `s2_improved[gate][sig]`: per seed `improved = B.mae < A.mae and |B.bias| < |A.bias|` on `drift_affected` (any `n == 0` -> not improved, counted in `n_zero_ticks`); `no_detection_regression`: per scenario/event/seed/gate B latencies <= A (censored = +inf); `occupancy_s2`: undecidable-band occupancy B <= A per seed/gate; `flat`: FLAT `calm` / `flat_band_violation` per arm/seed (the `harness.profile.flat_summary` rules from `settings.flat_control`); `guard_equal`: every `GUARD_KEYS` entry A == B; `verdict` = `regressed` if any of detection/occupancy/FLAT-B/guard fails, else `improved` if S2 improved on every signal at BOTH gates, else `mixed`.

### Tests (`tests/test_candb_measure.py`, 43 tests, 0 skipped)

- config: the committed YAML loads with all documented values; all 23 required keys named when missing (parametrised); 8 value violations named (boxcar method, bad criterion, workers 0, zero thresholds, zero stride, unknown scenario/signal).
- `forecast_vs_clean`: hand arrays (bias/mae/rmse/n exact; negative bias; NaN + masked ticks drop out; `n == 0` -> None statistics; length mismatch -> ValueError).
- `drift_affected_mask`: edge ticks (window spanning the move / not / window start before the series / no model), threshold INCLUSIVE, `min_level_move <= 0` rejected. (fit_end is epoch seconds: `i_e = round((fit_end - origin)/T)` blocks.)
- `model_age_h`: hand-array quantiles, stale fraction, no-model fraction, all-missing degenerate.
- real S2 full-horizon (seed 1, ~2 s per arm): arm A `widths` is None; arm B width blocks sum to `n_built`, every finite width in `[1, 570)`; the ESS-gate block + gated fraction + model availability are IDENTICAL A vs B (`guard_fractions_equal` clean; the whole `metric_ess` dict equal); a divergent re-run forecast raises; `arm_candb_block` schema on both arms.
- `run_arm`: returns the harness `EvalResult` for A/B x gate-on/off on S1 seed 1 (all quantity keys present; arm B serves a DIFFERENT forecast line on S1/cpu — finite-width cycles, R-candB 4.2; gate-off scores >= as many ticks as gate-on).
- `three_class_regressions`: synthetic per-seed cells — clean pass; each violation direction flagged (occupancy up, latency longer, censored-B vs detected-A, frac_normal down, q05 up); censored-A never a regression; seed mismatch rejected.
- `decision_readout` on synthetic profiles: all-pass -> `improved` (flags, per-seed rows, `n_event_checks`); better-mae-worse-bias -> `mixed`; `n == 0` -> finding; detection regression (finite + censored-B cases + censored-A control); occupancy regression; FLAT-band violation by B; guard mismatch (readout flags + the direct `guard_fractions_equal` raise).

### Gates (all at commit time)

```
$ .venv/bin/python -m pytest tests/test_candb_measure.py -q
...........................................                              [100%]   # 43 passed, 0 skipped

$ .venv/bin/ruff check src/refstudy/candb tests/test_candb_measure.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/candb
(empty; grep exit 1)

$ git diff --check            # clean (exit 0)

$ .venv/bin/python -m pytest tests -m 'not parity' -q   # full suite: green
(all tests pass, 0 skipped — including the 43 new tests; the suite is green end-to-end
at this head, no in-flight peer reds)
```

Commit: explicit `git add` of exactly the 5 owned paths; `git diff --check` clean; no trailers; nothing pushed; `results/a1a-parity.json` (pre-existing in-flight timing churn, 60 leaves all `wall_seconds`/`seconds`, 0 non-timing, verified by leaf diff vs `git show HEAD:…`) left untouched by me.

### Notes for CB-4.2 / 4.3 / 4.4

- `run_arm` is the 4.3 per-arm entry point (the card's `RunSpec` runner calls it twice — arm A and arm B — on the same generated scenario; the in-process A/B array assertions there use `pod.runs` + `cycle_report`, not the `EvalResult`).
- S2 at `n_ticks=900` is fully ESS-gated for every cycle (0 built, 0 scored): the 4.3 test at 900 ticks still exercises the schema (all `n == 0` / empty selections are legal findings), while the S2 headline statistics need the full 1872-tick horizon (mem 140 / cpu 148 built cycles, ~886 scored ticks).
- `drift_affected` on S2 is non-trivial on BOTH configured signals (mem: the 40.0 drift ramp+hold spans the fit window over its ramp; cpu: the 12.0 step at display block 144 spans it from onset on) — expect `drift_affected n` > 0 on both; `n == 0` would be a finding per the card, to be confirmed in 4.4.
- `decision_readout` consumes the 4.4 `profile["runs"][scn][arm][gate]["per_seed"]` entries `{"seed", "quantities", "candb"}`; the 4.3 runner must store the `arm_candb_block` dict under `candb` and the harness `block()` per-seed list entries (with the full `quantities`) under `per_seed`.

## CB-4.2 (2026-11-11, JST ~04:15)

Commit: `0b394bd feat(refstudy): add candidate-B sequencing-cost study and tests (CB 4.2)` (lab head before: `7fc2709`; 3 files, 817 insertions: `src/refstudy/candb/sequencing.py` (451), `tests/test_candb_sequencing.py` (347), `src/refstudy/candb/__init__.py` updated to export the study).

### `candb/sequencing.py`

- `local_minima_count(xs)`: strict local-minima count of a 1-D array (interior points strictly below both neighbours).
- `joint_backfit_residuals(y, bins, width, *, min_lag, phase_bins)`: the counterfactual co-fit. ONE causal backfitting pass: the deseasonalised joint residual `r_s = y_s - d_s^{joint}` (the level at `i` = the mean over `s in [max(0, i-W), i)` of the in-window blocks that CARRY a residual, `s >= min_lag`), with `S_i` = centred bin means of `r_s (s < i, >= m0)`, `S_i = 0` on empty bin/history, `F_i = d_i^{joint} + S_i(bin_i)`. O(K*B) via a running S state + prefix one-hot bin counts + moving-window sums (validated against an explicit-loop reference to 1e-9: max diff 1.1e-13).
- `WindowAnalysis` (frozen slots, `to_dict()`); `analyze_window(y, bins, candidates, *, min_lag, phase_bins, ess_max_lag, const_tol)`: `curve_seq` = the `select_width` cv1 scores EXACTLY (the deployed selector, sentinel excluded), `curve_joint` = cv1 of `joint_backfit_residuals[m0:]`; `w_seq`/`w_joint` = argmin (ties -> smaller width); `seq_regret = jcv1[w_seq]/min jcv1 - 1`, `joint_regret = cv1[w_joint]/min cv1 - 1`; local-minima counts; degenerate windows (`ess_gate` / few blocks / constant) return empty curves + `None` widths + the reason.
- `_windows_of_signal` (provider re-run, every `stride`-th cycle, emitted blocks, the gated flag from `rep.reason == "ess_gate"`); `summarize` (p50/p90 per scenario x signal over the finite windows); `study_sequencing(ccfg, hcfg, *, seeds=None)` -> `{scn: {sig: {"windows": [row], "summary": {...}}}, "summary": {"<scn>/<sig>": {...}}}`, every row JSON-safe: `cycle_index, t0, gated, k, curve_seq, curve_joint, w_seq, w_joint, seq_regret, joint_regret, n_local_minima_seq, n_local_minima_joint, reason`.

### Tests (`tests/test_candb_sequencing.py`, 13 tests, 0 skipped)

- joint backfit == the explicit-loop reference for `w in {1, 7, 36, 100, K-1}` (self-consistent `r_s = y_s - d_s^{joint}`); causality (prefix invariance); input non-mutation; validation errors.
- `analyze_window`: `curve_seq` == `select_width` scores verbatim; regrets >= 0 + finite; determinism; all 4 degenerate reasons; local-minima count.
- real S1/cpu seed-1 stride-12 study: row schema; `curve_seq` == an independently recomputed `select_width` on >= 3 windows; determinism; summary shape.

### Gates (all at commit time)

```
$ .venv/bin/python -m pytest tests/test_candb_sequencing.py -q
.............                                                            # 13 passed, 0 skipped

$ .venv/bin/ruff check src/refstudy/candb tests/test_candb_sequencing.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/candb
(empty; grep exit 1)

$ git diff --check            # clean (exit 0)

$ .venv/bin/python -m pytest tests -m 'not parity' -q   # full suite: green
(all tests pass, 0 skipped — including the 13 new tests)
```

Commit: explicit `git add` of exactly the 3 owned paths (the 4.2-only `__init__.py` — no `run.py` import yet); `git diff --check` clean; no trailers; nothing pushed; `results/a1a-parity.json` left untouched.

### Notes for CB-4.3 / 4.4

- Measured S1/cpu seed-1 stride-12 study (18 windows, 9 gated on first-day ESS, finite on all 18): `w_seq` p50 = 7.5 / p90 ~ 10.3 blocks, `w_joint` p50 = 6.0; `seq_regret` p50 ~ 0.034 / p90 ~ 0.22, `joint_regret` p50 ~ 0.0035 / p90 ~ 0.023; local minima: seq p50 = 1 / p90 ~ 2.3 vs joint p50 = 0 / p90 = 0 — co-fit costs little, and the sequential curve is more multimodal (the operator's sequencing concern is visible on S1).
- The full 3-scenario x 2-signal x 5-seed study ~ 120 windows/sig/seed x 32 joint backfits; S1/cpu/seed1 alone ~ 2.3 s single-threaded -> a few minutes in the 4.4 run (bounded pool, no extra parallelism needed).
- `build_profile` (4.3) computes `study_sequencing` inside `stage_runs` unless the caller passes a pre-computed study (the tests pass empty cells for speed).

## CB-4.3 (2026-11-11, JST ~04:40)

Commit: `641753d feat(refstudy): add candidate-B runner, figures and run script (CB 4.3)` (lab head before: `0b394bd`; 6 files, 1728 insertions: `src/refstudy/candb/run.py` (584), `src/refstudy/candb/plots.py` (330), `scripts/run_candb.py` (200), `tests/test_candb_run.py` (343), `tests/test_candb_plots.py` (263), `src/refstudy/candb/__init__.py` updated with the runner exports).

### `candb/run.py`

- `RunSpec(gate, scenario, seed, n_ticks=None)` (`.gate_key` = `gate_on`/`gate_off`, `.label`); `run_specs(specs, candb_path, workers)` = the bounded `ProcessPoolExecutor` with a config-reloading worker initializer (as `harness.profile.run_specs`), order-preserving.
- `run_one(spec, ccfg, hcfg, *, ess_floor)`: BOTH arms of ONE generated scenario (`get_scenario` once, shared by A and B): arm A = the unchanged `ref_synth` chain, arm B = `with_trend(ref_synth, ccfg.trend)`; gate off = `gate_off_chain`. Per arm: `run_checked` -> `evaluate_records` -> the entry `{"seed", "scenario", "quantities", "candb" (= the `arm_candb_block` dict: `fc_vs_clean`/`model_age_h`/`cycle_report`), "ess" (per-seed metric_ess blocks reused from the cycle report)}`. Then the IN-PROCESS guard assertion `assert_guard_and_arrays` (A.`fit_end`/`model_t0`/`ess` arrays `array_equal(equal_nan=True)` per continuous metric + `measure.guard_fractions_equal` on the gated-cycle counts) — a mismatch raises `ValueError("candb guard: {short}.{field} differs between arm A and arm B …")`, which in the worker pool becomes a non-zero exit; on success the guard-check count is recorded in `guard_checks`.
- `width_rows(pod, scenario, chain)`: the arm-B width rows `(t0, reason, trend_width)` per cycle per signal (one provider re-run, forecast equality checked).
- `cell(outs)`: the harness `block()` shape `{"per_seed": [{seed, quantities, candb}], "aggregate" (the harness seed aggregation minus its flat per_seed), "ess": {"per_seed", "aggregate" (harness aggregate_ess)}}`; `headline(runs)`: S2 trend-lag fidelity of B vs A per gate x selection (all / drift_affected) x signal x statistic — A/B mean+-sd over the seeds + the per-seed paired deltas (B - A), `n` reported (`n == 0` is a finding).
- `a_matches_part1(runs, study_dir)` -> `(bool | None, {"status": "true"|"pending", "n_compared", "mismatches"})`: arm A (gate_on) per-seed quantities vs the committed `results/part1-profile.json` schema 2 (`scenarios.{scn}.per_seed`); file absent or any mismatch -> `"pending"` (never faked `true`), with the named diffs.
- `build_profile(outs, ccfg, hcfg, *, timing=None, sequencing=None)` -> the CB-4.4 profile dict: `schema_version: 1`, `git_head`, `config_sha256 {reference, candb, harness, scenarios}`, `settings {flat_control, scoring, trend, seeds, workers, stale_hours, fidelity_drift, sequencing}`, `runs {scn: {A|B: {gate_on, gate_off: cell}}}`, `headline`, `sequencing` (computed via `study_sequencing` when `None`), `decision_readout` (the `measure.decision_readout` mechanical read-out — REQUIRES S2 + FLAT cells present), `assertions {guard_equal: True, fit_end_equal: True, a_matches_part1, a_matches_part1_detail}` (the True values are structural: the in-process guard would otherwise have raised), `timing`.

### `candb/plots.py` + `scripts/run_candb.py`

- `build_s2_trend(data, scenario, hcfg)`: the 2x2 (rows = gate_on/gate_off; col 0 = the S2 mem forecast of arm A vs arm B vs the noise-free `clean`, orange drift-onset vline; col 1 = the pod `p_raw` strip A vs B, log y 1e-3..1, the undecidable band shaded, the 0.2/0.8 boundaries dotted with their EXACT D-A labels "decisively normal (<0.2)" / "undecidable [0.2, 0.8]" / "decisively anomalous (>0.8)" from `hcfg.scoring`, the no-model stretches shaded, 4-patch legend). Missing (arm, gate) key -> KeyError.
- `build_widths(widths, hcfg)`: one panel per scenario x cpu/mem; finite built widths in HOURS (`w * T / 3600`), the sentinel cycles as ONE grey `x` marker line at y = 1.0, gated/few-block cycles skipped; log y 0.3..26.
- `build_sequencing(sequencing, *, tick_seconds)`: one panel per scenario (excluding `summary`) x cpu/mem; the median `curve_seq` (solid, "curve_seq (deployed)") + median `curve_joint` (dashed, "curve_joint (co-fit)") over the finite windows, the median `w_seq`/`w_joint` as axvlines (underscored labels keep them out of the legend; the test counts them by their labels).
- `save_figure(fig, path, dpi)`; `scripts/run_candb.py --config config/candb.yaml --stage runs|figures|all` (default all): `stage_runs` = the full 90-task plan (both gates x every scenario x every seed = 180 arm-runs) in the pool -> `build_profile` (sequencing computed inside) -> `results/candb-profile.json`; `stage_figures` = the three seed-1 figures (`candb-s2-trend.png` both arms x both gates, `candb-widths.png` arm-B S1/S2/FLAT gate-on, `candb-sequencing.png`).

### Tests (`tests/test_candb_run.py` 12 + `tests/test_candb_plots.py` 9 = 21 tests, 0 skipped)

- `test_candb_run.py` (S2 `n_ticks=900` seed 1, serial in-process via `R.run_one` — the same worker body the pool runs; the pool mechanics are the committed `harness.profile` precedent + the 4.4 full run): the arm-entry schema (all keys, `candb.fc_vs_clean = {all, drift_affected}`, `ess.metrics` == the cycle-report ess blocks); S2@900 gate-on is FULLY ESS-gated on the drift signals mem/cpu (0 built, 0 scored, B widths `n_built == 0`; the network signals are out of the drift selection and their gate outcome is a measured value, not asserted); the guard counts equal A vs B; arm A quantities == a direct harness call; at 900 ticks both arms serve no forecast (n == 0 recorded verbatim); a tampered `fit_end` -> `ValueError("candb guard: cpu.fit_end differs")`; the `cell()` shape; `headline` on synthetic runs (the `n == 0` finding; the paired deltas); `a_matches_part1` (file absent -> pending; a mismatched `undecided_occupancy.rate` -> pending with the named diff; equal -> true); `build_profile` full assembly on S2 + FLAT 900-tick tasks (the read-out needs both; schema keys, the block shape, the assertions, verdict in the three classes; headline: gate-on fully gated n == 0 recorded, gate-off n > 0).
- `test_candb_plots.py`: synthetic bundles (per-signal clean/forecast, a p_raw with a decisive episode + warm-up NaNs, a no-model stretch) — the 2x2 figure (4 axes, legends, the drift-onset text, log yscale, the boundary labels, the "undecidable" / "no model" legend patches), the missing-gate KeyError, `build_widths` (6 axes, titles, the 24 finite-width points in hours, the sentinel line with 6 points), the empty-widths case, `build_sequencing` (6 axes, the two curve labels, the 2 vlines) + the empty-windows case; and the REAL S2 seed-1 full 1872-tick bundle (both arms x both gates: the shapes, the arm-invariant no-model mask, the PNG render).

### Gates (all at commit time)

```
$ .venv/bin/python -m pytest tests/test_candb_sequencing.py tests/test_candb_run.py tests/test_candb_plots.py -q
..................................                                       # 34 passed, 0 skipped

$ .venv/bin/ruff check src/refstudy/candb tests/test_candb_sequencing.py tests/test_candb_run.py tests/test_candb_plots.py scripts/run_candb.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/candb scripts/run_candb.py
(empty; grep exit 1)

$ git diff --check            # clean (exit 0)

$ .venv/bin/python -m pytest tests -m 'not parity' -q   # full suite: green
(all tests pass, 0 skipped — including the 34 CB-4.2/4.3 tests; 493 s wall)
```

Commit: explicit `git add` of exactly the 6 owned paths; `git diff --check` clean; no trailers; nothing pushed; `results/a1a-parity.json` and the sibling C4-stage-2 paths left untouched.

### Notes for CB-4.4

- The 4.4 run is `$PY scripts/run_candb.py --config config/candb.yaml` (default `--stage all`): 90 pool tasks = 180 arm-runs (9 scenarios x 5 seeds x 2 arms x 2 gates, workers = `candb.yaml` `workers: 4`), then the 3 seed-1 figures; the profile lands at `results/candb-profile.json`.
- `build_profile`/`decision_readout` REQUIRE S2 + FLAT cells (the read-out's flat control + drift signals); in production every scenario is present, so no library change is needed — the tests pass both.
- S2 @ `n_ticks=900` (the test horizon): gate-ON is fully ESS-gated on mem/cpu (0 built, 0 scored, headline n == 0 recorded as a finding); gate-OFF builds the models (mem/cpu n = 317 all / 319 drift_affected). The 900-tick tests exercise the schema + the guard + the assembly; the headline statistics need the full 1872-tick horizon (mem 140 / cpu 148 built cycles, ~886 scored ticks, per the CB-4.1 note).
- `a_matches_part1` is `"pending"` until `results/part1-profile.json` exists and matches arm A gate-on per-seed quantities; any mismatch is `"pending"` with the named diffs (never a faked `true`).
- Figure data-flow: `stage_figures` re-runs the arm chains on the figure seed (S2 both gates both arms; S1/S2/FLAT arm-B gate-on for the widths; the sequencing study is computed, not read from the profile) — the figures are pure functions of their bundles, so the builders are testable on synthetic data.
- The CB-4.2 study inside `stage_runs` is the full 3-scenario x 2-signal x 5-seed sweep (S1/cpu/seed1 ~ 2.3 s single-threaded in the tests -> a few minutes here; bounded by the pool, no extra parallelism).

## CB-4.4 (2026-11-11, JST ~04:35)

Commit: `cdb74e7 data(refstudy): record candidate-B measurement arm (CB 4.4)` (lab head before: `641753d`; 4 files, 149492 insertions: `results/candb-profile.json`, `figures/candb-s2-trend.png`, `figures/candb-widths.png`, `figures/candb-sequencing.png` — owned paths only).

### Run

```
$ .venv/bin/python scripts/run_candb.py --config config/candb.yaml      # default --stage all
...
2026-11-11 04:31:58 INFO __main__:stage_runs:89 - wrote .../results/candb-profile.json
                     (180 arm-runs, 1399s wall; a_matches_part1=true)
2026-11-11 04:32:41 INFO __main__:stage_figures:149 - wrote .../figures/candb-s2-trend.png
2026-11-11 04:34:25 INFO __main__:stage_figures:160 - wrote .../figures/candb-widths.png
2026-11-11 04:35:34 INFO __main__:stage_figures:166 - wrote .../figures/candb-sequencing.png
2026-11-11 04:35:34 INFO __main__:main:195 - candb all done in 1686s      # exit 0
```

90 pool tasks × both arms = 180 arm-runs (9 scenarios × 5 seeds × 2 arms × 2 gates),
workers 4, CPU. Runs wall 1399 s + sequencing study 70 s (inside `stage_runs`) + 3 figure
re-runs ≈ 4.8 min; **total 1686 s ≈ 28.1 min** (card expectation 20–40 min).
Per-task tail of the run log: last task `gate_off:S8:seed5 wall 1399.2s (90/90)`.

### Profile + assertions (verbatim from `results/candb-profile.json`)

```
assertions: {
  "a_matches_part1": "true",
  "a_matches_part1_detail": {"mismatches": [], "n_compared": 45, "status": "true"},
  "fit_end_equal": true,
  "guard_equal": true
}
timing: {"n_tasks": 90, "runs_wall_s": 1399.36, "sequencing_wall_s": 70.07}
```

- **A-cross-check PASSED and computed now** (the card's "pending" step): arm A gate-on
  per-seed quantities == committed `results/part1-profile.json` (schema 2, D-B re-expression
  `fb8b53a`/`496255c`): 45/45 scenario-seed cells, 0 leaf diffs. Independently re-verified
  while writing 4.5 (inline leaf walk over every per-seed quantity: `n_compared=45,
  diffs=0`).
- Guard fraction A == B per scenario/signal/gate: asserted in-process by the runner
  (a mismatch would have exited non-zero) — `guard_equal: true`; e.g. S2 gate-on
  cpu 148/216 built, 68 gated (0.315) both arms; mem 140/216 built, 76 gated (0.352) both arms.
- `fit_end_equal: true` (A/B `fit_end`/`model_t0`/`ess` arrays `array_equal(equal_nan=True)`
  per metric, asserted in-process).
- Determinism: the run is the deterministic seeded re-run; figure stage re-ran the arm chains
  and matched the committed profile data (the figure bundles are pure functions of the same
  generated scenarios).

### Headline (S2 trend bias/MAE/RMSE, A vs B; mean±sd over seeds; n = scored ticks)

| gate | selection | sig | n | A MAE | B MAE | paired ΔMAE (B−A, per-seed range) |
|---|---|---|---|---|---|---|
| on  | all             | mem | 844  | 5.53 ± 0.34 | 6.38 ± 0.53 | +0.85 (+0.46…+1.65) |
| on  | drift_affected  | mem | 72   | 20.95 ± 3.12 | 12.23 ± 2.23 | −8.72 (−11.03…−5.03) |
| on  | all             | cpu | 892  | 0.97 ± 0.08 | 1.02 ± 0.08 | +0.04 (−0.12…+0.27) |
| on  | drift_affected  | cpu | 24   | 11.99 ± 0.49 | 4.45 ± 1.98 | −7.53 (−10.41…−4.93) |
| off | all             | mem | 1289 | 14.27 ± 0.26 | 6.56 ± 0.35 | −7.71 (−7.97…−7.30) |
| off | drift_affected  | mem | 517  | 29.32 ± 0.41 | 7.58 ± 0.59 | −21.74 (−22.63…−21.05) |
| off | all             | cpu | 1289 | 3.66 ± 0.04 | 1.06 ± 0.07 | −2.60 (−2.67…−2.50) |
| off | drift_affected  | cpu | 421  | 9.72 ± 0.08 | 1.29 ± 0.10 | −8.44 (−8.59…−8.32) |

B strictly improves drift_affected bias/MAE/RMSE on **every seed, both signals, both gates**
(5/5; `decision_readout.s2_improved` `n_zero_ticks = 0`). `all`-tick gate-on: B marginally
worse on mem (+0.85 MAE), flat on cpu; gate-off: B far better everywhere. No `n == 0`
findings on the configured drift signals (gate-on drift n per seed: mem 54–72, cpu 12–24;
gate-off 421/517 per seed).

Other card-required headline elements (all in the profile + 4.5 note): S2 onset latencies
(E0-drift gate-on per seed leave_normal/decisive: A (54,76) (1,68) (30,31) (69,75) (55,56) vs
B (95,96) (1,2) (30,31) (8,9) (28,56); E1-step gate-off A (0,0) all seeds vs B (3,4) all
seeds); S2 undecidable-band occupancy A 0.0283±0.0098 → B 0.0563±0.0086 (gate on, up on all 5
seeds, both gates); **S1 non-regression VIOLATED — finding, reported verbatim, not tuned**:
B regresses A on all 30 three-class checks per gate (undecidable occupancy 0.0280→0.0583
gate-on means; decisive 0.4417→0.4580; decisively-normal 0.5303→0.4836); FLAT calibration:
frac_in_flat_band 0.893 (A) vs 0.814 (B), decisively-anomalous fraction 0.0085 vs 0.0202 —
both arms outside the strict band (committed Part-1 sits outside it too), B widens it ~1.7×;
model age identical A=B (guard unchanged): S2 p50 0.792 h, p90 1.0 h, frac > 6 h = 0.
Stale-model question (R-candB §4.3 "served 28–39 h stale"): **refuted** — no stale model
observed; gated cycles serve no model at all (S2 cpu gate-on 984/1872 ticks no-model), and the
gate-on drift_affected ticks (n 12–72) are where B still strictly improves.

### `decision_readout` (mechanical vision-§6 read-out, as recorded in the profile)

flags: drift_pass = true; detection_pass = false (29/200 event checks — S2-E0-drift seed-1
gate-on 54→95 leave_normal / 76→96 decisive; S2-E1-step gate-off 0→3, 0→4 all 5 seeds;
S3-E1-pulse seed-3 decisive 97→113; S4-E0 seed-5 +1 both quantities both gates;
S6-E1-bump gate-off +3…+6 all seeds); occupancy_pass = false (undecidable band up, all 5
seeds, both gates); flat_pass = false (B outside-band all 5 seeds); guard_pass = true.
**verdict = regressed** — B not adopted by the mechanical rule; the A/B/C recommendation
stays with Phase E (per card, unchanged).

### Figures (3, seed 1)

- `figures/candb-s2-trend.png` (1980×1410): 2×2, rows gate-on/off; col 0 = S2 mem served
  forecast A vs B vs clean with the drift-onset vline — B tracks the drift ramp ~1 h behind
  vs A ~9 h behind (visible in both rows); col 1 = p_raw strip A vs B, log y, undecidable
  band shaded, 0.2/0.8 dotted with the D-A labels, no-model stretches shaded.
- `figures/candb-widths.png` (1980×1890): 3×2 (S1/S2/FLAT × cpu/mem), arm-B selected width
  in hours per cycle, finite widths as points (S2 cpu/mem medians ≈ 9.8 h / 8.8 h, flapping
  across 0.6–12 h; S1 cpu ≈ 0.6 h, mem ≈ 1.9 h), the sentinel cycles as one grey x-line at
  y = 1.0 (S2 cpu 28/148, mem 49/140 cycles; S1 0/122, 0/139).
- `figures/candb-sequencing.png` (1980×1980): 3×2, median curve_seq (deployed) vs
  curve_joint (co-fit) cv1 vs width (h) per scenario×signal, with the median w_seq/w_joint
  vlines; joint curve flatter at the minimum on S1 (the multimodality of the deployed
  sequential curve is concentrated on the diurnal regime).

Figure inspection note (environment, not data): the read-tool vision backend was unavailable
during this run (`Bedrock HTTP 404 — model version EOL`, 4 attempts on the 3 PNGs); the
figures were therefore verified by (a) the 9 committed `test_candb_plots.py` tests, which
pin every axis/legend/label/patch and include the real seed-1 S2 full-horizon bundle render,
and (b) programmatic content checks (dimensions 1980×1410/1980×1890/1980×1980 @150 dpi;
non-blank fraction 0.153 / 0.039 / 0.023 of pixels; 1045/794/1355 distinct colour rows).
The layout facts above come from the pinned `candb/plots.py` builders.

### Gates (all at commit time)

```
$ .venv/bin/python -m pytest tests/test_candb_measure.py tests/test_candb_sequencing.py \
     tests/test_candb_run.py tests/test_candb_plots.py -q
....................................................................  # 77 passed, 0 skipped

$ git diff --check            # clean (exit 0)
```

Commit: explicit `git add` of exactly the 4 owned paths; no trailers; nothing pushed. The
foreign dirty paths in the working tree at commit time (`results/a1a-parity.json` timing
churn, the sibling C4-stage-2 files `scripts/run_c4.py`/`src/refstudy/refcompare/plots.py`/
`tests/test_refcompare_*.py`/`figures/c4-*`) were NOT staged or touched by me.

## CB-4.5 (2026-11-11, JST ~04:55)

Commit: `0d1a3f0 docs(refstudy): candidate-B measurement note (CB 4.5)` (1 file, 120
insertions: `markdown/candb-profile.md` — exactly the 120-line limit, owned path only).

### Note content (all numbers measured, D-A vocabulary only)

Setup (180 arm-runs, config span [30 min, 12 h] × 32 grid points, cv1, guard asserted
identical) → headline table (8 rows above, with bias/MAE/RMSE A vs B, n, and per-seed
paired-delta ranges) → **deviations from the vision text** (ESS objective degenerate:
smallest grid width 6 blocks in 9/9 windows ⇒ cv1 used, ESS diagnostic-only; exclusive trend
vs the vision's inclusive form — no-leakage, ~20 % self-inclusion artefact at W = 6; span
[30 min, 12 h] not "8–12 h"; target: the vision expected S1 unmoved — **measured B moves
S1** (non-regression violated, recorded as a finding); warm-up from `min_fit_blocks` = 48;
sentinel routed to legacy byte-for-byte; `gauge_epsilon` 1e-9 reused, no new key; grid-only,
no span.method gradient/fallback ported) → **stale-model question refuted** (guard
unchanged ⇒ served-model age identical A=B, p50 0.792 h / p90 1.0 h / frac > 6 h = 0 on S2;
R-candB §4.3's "28–39 h stale drift windows" do not occur — gated cycles serve no model at
all; the gate-on drift_affected ticks (n 12–72/seed) still show B strictly improving 5/5, so
the drift gain is NOT only in the gate-off counterfactual) → S1 non-regression finding
(30/30 checks violated both gates; B widths S1 cpu 7.5 / mem 15 blocks, 0 sentinel) → FLAT
calibration verdict (both arms outside the strict band, committed Part-1 included; B widens
outside-band 0.107 → 0.186) → selected-widths section (S2 cpu median 117 blocks ≈ 9.8 h,
sentinel fraction 0.189; mem 106 ≈ 8.8 h, 0.35; width flapping 25–144 blocks) →
sequencing-cost study table (6 scenario×signal cells, w_seq/w_joint p50, seq/joint regret
p50/p90, local-minima counts: S1 seq_regret p50 0.060/0.113, joint p50 0.006/0.023, S1
sequential curve multimodal (1–4 minima) vs joint 0–1; S2/FLAT regret ~0.002–0.005) →
mechanical decision read-out (flags as above, verdict = regressed, A/B/C recommendation
stays with Phase E) → cross-check (`a_matches_part1 = true`, 45/45) → limits (one-step cv1
vs the 0.5–1 h served horizon, cv1 sample includes the cold prefix, width flapping, figures
seed-1).

### Numbers recomputed from the JSON while writing (4, listed for S)

1. `a_matches_part1` re-verified independently by an inline leaf walk of arm A gate-on
   per-seed quantities vs `results/part1-profile.json`: **45/45 cells, 0 diffs** (profile
   says `"true"`).
2. gate-off all mem MAE from the per-seed `candb.fc_vs_clean.all.mem` blocks: A mean
   **14.2712** (sd 0.2615, per-seed 13.978…14.516), B mean **6.5572** (sd 0.3460,
   6.131…7.049) — matches the profile headline 14.27 ± 0.26 / 6.56 ± 0.35.
3. S2 gate-on undecidable-band occupancy from per-seed quantities: A mean **0.028304**
   (sd 0.009784), B mean **0.056342** (sd 0.008570) — matches 0.0283 ± 0.0098 /
   0.0563 ± 0.0086.
4. S2-E0-drift seed-1 gate-on onset from `events`: A leave_normal **54** / decisive **76**,
   B **95** / **96** — matches the decision_readout violations and the note.

### Gates (all at commit time)

```
$ .venv/bin/python -m pytest tests/test_candb_measure.py tests/test_candb_sequencing.py \
     tests/test_candb_run.py tests/test_candb_plots.py -q
....................................................................  # 77 passed, 0 skipped

$ .venv/bin/ruff check markdown/candb-profile.md    # All checks passed!
$ wc -l markdown/candb-profile.md                    # 120
$ grep -niE "fpr|false.?positive|warning" markdown/candb-profile.md
(empty; grep exit 1)
$ git diff --check            # clean (exit 0)
```

Commit: explicit `git add markdown/candb-profile.md`; the two headline-table delta-range
fixes (min…max ordering on the gate-on drift rows) were folded in via `git commit
--amend --no-edit` before any consumer read the commit; no trailers; nothing pushed; no
foreign path staged.

### One-paragraph headline (for S's campaign log)

Candidate B (adaptive-width boxcar trend, span [30 min, 12 h], cv1 selection) was measured
on the full arm: 180 arm-runs (9 scenarios × 5 seeds × 2 arms × 2 gates, CPU, 28.1 min),
with arm A cross-checked exactly against the committed Part-1 profile (45/45 cells,
`a_matches_part1 = true`) and the ESS guard proven identical A vs B (`guard_equal`,
`fit_end_equal` true). The drift gain is real and large: on S2's drift-affected ticks B
cuts MAE from 20.95 → 12.23 (mem, gate on; 29.32 → 7.58 gate off) and 11.99 → 4.45 /
9.72 → 1.29 (cpu), strictly on all 5 seeds, both signals, both gates — and the R-candB
§4.3 "stale model" caveat is refuted (no stale model is ever served: gated cycles carry no
model, and even the gate-on drift ticks improve). But the mechanical vision-§6 decision
rule reads **verdict = regressed**: B regresses the diurnal regime — S1 three-class
non-regression is violated on all 30 checks (undecidable-band occupancy 0.028 → 0.058),
S2 undecidable-band occupancy rises on all 5 seeds, two drift-seed-1 onsets slow by
+41/+20 ticks, and the FLAT outside-band fraction widens 0.107 → 0.186 (both arms were
already outside the strict band in Part-1). Sequencing cost is small (sequential-vs-joint
regret ≤ ~0.27 relative cv1, concentrated on S1 where the deployed curve is multimodal).
Recommendation: B's trend is the right mechanism for drift, but as measured it fails the
no-regression bar — the A/B/C adoption decision stays with Phase E, and the candidate's
cost is a wide, flapping width (S2 median ~9 h with 19–35 % sentinel cycles) that a
diurnal-aware constraint (narrower span or a S1-style width floor) could plausibly repair.
