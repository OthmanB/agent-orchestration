# C1 — TimesFM-3 `ReferenceProvider` (Executor evidence)

One section per workcard stage. This leaf (E) owns **S1a**: `config/refcompare.yaml`,
`src/refstudy/refcompare/{__init__,config,grid,cycles}.py`,
`tests/test_refcompare_{config,grid,cycles}.py`.  S1b (hand-off, store) and S2
(provider, pipeline, variants, smoke) are separate slices; their sections are
added as they land.  All paths relative to
`reference-model-study/` (lab repo
`pipelineml-model-exploratory-work`).

---

## S1a — config, regular-grid resampler, cycle planner

### 1.0 Preflight (record all)

Repo state at start (lab repo, branch `main`):

```
$ git status --short
# (clean before this slice)

$ git log --oneline -6
a2c4584 fix(refstudy): strictly increasing batch calibration counts and fail-closed hygiene probes (B2 fix A)
7194c9c chore(refstudy): record B2 CUDA refresh measurements
194938f data(refstudy): record Part-1 limitation profile, figures and caption regression
b375742 feat(refstudy): add refresh-study runner, batching wrapper and figures
013c570 fix(refstudy): adapt harness to the 11-metric production-shaped chain
d41c91f fix(refstudy): couple scenario packet counts to the noise-free signal (pure Poisson)
```

HEAD ⊇ `7bbe268` and the A1b3 commit `76451a6` (both verified `git merge-base
--is-ancestor` ⇒ yes).  A sibling executor landed `a2c4584` (B2 fix) on
disjoint files during this slice; it does not touch any C1 path.

```
$ .venv/bin/python -c "from refstudy.reference import run_pod, score_pod, build_blocks, \
ReferenceRun, check_no_leakage, RareCountProvider; \
from refstudy.harness import evaluate_records, load_harness_config; \
from refstudy.scenarios import get_scenario; ...; print(...)"
SIGNATURE: (observed: 'Mapping[str, BlockSeries]', runs: 'Mapping[str, ReferenceRun | RareCountRun]',
            ticks: 'Sequence[float] | np.ndarray', cfg: 'RefConfig', *,
            forced_gaps: 'Mapping[str, Mapping[float, str]] | None' = None,
            scored_cells: 'Mapping[str, Mapping[float, BlockCell | None]] | None' = None)
            -> 'list[TickRecord]'
REFRUN_FIELDS: ['forecast', 'model_t0', 'fit_end', 'ess', 'rec_lo', 'rec_hi', 'rec_ts', 'rec_val']
CHAIN_RAW(sorted): ['container_cpu_usage_seconds_total',
 'container_memory_working_set_bytes', 'container_network_receive_bytes_total',
 'container_network_receive_errors_total', 'container_network_receive_packets_dropped_total',
 'container_network_receive_packets_total', 'container_network_transmit_bytes_total',
 'container_network_transmit_errors_total', 'container_network_transmit_packets_dropped_total',
 'container_network_transmit_packets_total', 'container_oom_events_total']
INCLUDE_RARE: True  ENTRIES: 11
```

All 11 canonical names, `include_rare_count=True`, 11 entries — preflight passes.

```
$ df -h / | tail -1
/dev/disk3s1s1  461G  418G   43G  91% /
```

### Files owned by S1a

- `config/refcompare.yaml` (all tunables + provenance comments)
- `src/refstudy/refcompare/__init__.py` (exports the S1a API)
- `src/refstudy/refcompare/config.py` (frozen `RefCompareConfig`, `load_refcompare_config`)
- `src/refstudy/refcompare/grid.py` (`to_grid`, `pod_origin`, `real_slice`)
- `src/refstudy/refcompare/cycles.py` (`Cycle`, `plan_cycles`, `min_first_n0`,
  `first_valid_tick`, `context`, `step_grid_index`, `digest`)
- `tests/test_refcompare_config.py`, `tests/test_refcompare_grid.py`,
  `tests/test_refcompare_cycles.py`

### 1.1 config validation (test: `test_refcompare_config.py`)

Every required key is named in its `ValueError`; bool-as-number rejected;
`ctx > max_context` rejected; non-integer `T/cadence` rejected;
`max_gap_seconds != reference.validity.counter_max_gap_seconds` rejected;
levels not 9-ascending rejected; `horizon_blocks` must exceed `max(diag_blocks)`
and be `>= 13` (the shipped config has `horizon_blocks=13`, `diag={3,6,12}` ⇒
max diag 12; the card's `horizon_blocks>max(diag)≥13` was read as the two
self-consistent constraints `horizon > max(diag)` and `horizon >= 13` because a
literal `max(diag) ≥ 13` would reject the shipped YAML).  `reference_quantile_index`
must equal `architecture.median_index` and `levels[median_index] == 0.5`.

### 1.2 grid (test: `test_refcompare_grid.py`)

- Regular grid ⇒ identity: counter increments == `diff` of the cumulative; gauge
  unchanged.
- Jittered 10–34 s gaps, constant rate 2/s ⇒ every grid increment == 30.0 and
  block sums telescope to `C(right)−C(left)` (20×30 = 600 per 300 s block).
- 40 s gap ⇒ NaN exactly on the grid points/increments whose bracket spans it
  (35.0 s admitted: `gap > max_gap` only).
- Counter reset ⇒ NaN on the increments whose span crosses the reset interval.
- Points outside the raw range ⇒ NaN.
- `real_slice` keeps `ts >= last_ts − days·86400` for ALL entries and returns one
  shared `origin` = `floor(first_ts/T)·T`.

### 1.3 cycles (test: `test_refcompare_cycles.py`)

`min_first_n0` (context in grid POINTS, converted to blocks internally):

```
min_first_n0(240) = 24      (1 h = 12 blocks)
min_first_n0(5760) = 300    (1 d = 288 blocks)
min_first_n0(11520) = 588   (2 d = 576 blocks)
```

`plan_cycles(origin, 1872, T=300, dt=1800, first_n0=588)` (the shared 2 d first
cycle) ⇒ **215 cycles**, `n0 = 588…1872`, every `t0 % 1800 == 0`,
`fit_end = t0 − 2100`, served ticks `k+1 ∈ [n0, n0+6)`.

`first_valid_tick(ctx_pts, ref_cfg, origin)` (dt-aligned origin, card D-5/D-6):

```
ctx 240    -> k+1 = 554
ctx 5760   -> k+1 = 830
ctx 11520  -> k+1 = 1118
```

Derived, not retyped: `gate = (Dt−dt)/T − noise.min_fit_blocks = 570 − 48 = 522`,
`k+1 = n0 + gate + 6 + 2` (record lags newest served blocks by one cycle ⇒ `+6`;
two ring-fill ticks ⇒ `+2`).

Origin shifted by `300·j s` (`j = 1…5`): every `t0 % 1800 == 0`, first scored
tick `1118 + (6 − j) % 6` (i.e. 1119…1123), 214 cycles each (the aligned case has
215; a shifted origin starts one block later and drops the trailing unaligned
cycle).  `context(grid, cycle, ctx_pts, counter)` equals the hand-sliced window
for counter AND gauge and is byte-identical when raw after `fit_end` is deleted
(truncation invariance).  `digest` = `(sum, sumsq, n_nan)` over finite values.

### 1.4 Gates (literal)

```
$ .venv/bin/python -m pytest tests/test_refcompare_config.py \
    tests/test_refcompare_grid.py tests/test_refcompare_cycles.py -q
......................................                                   [100%]
```
(38 passed, 0 skipped.)

```
$ .venv/bin/ruff check src/refstudy/refcompare \
    tests/test_refcompare_config.py tests/test_refcompare_grid.py \
    tests/test_refcompare_cycles.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare
# (empty, exit 1)

$ git diff --check
# (clean)
```

### Commit

```
feat(refstudy): add refcompare config, regular-grid resampler and cycle planner (C1 slice 1a)
```

Commit hash: `5d657f8` (lab repo `main`, 8 files, +1147 lines; owned paths only).

### Deviations / notes

- **`first_valid_tick` semantics**: returns `k+1` (card D-6 "first scored
  `k+1 = n0+528+2`"), not 0-based `k`.  Card's 554/830/1118 reproduced exactly.
- **`min_first_n0`/`first_valid_tick` take context in grid POINTS** (matching
  `input.contexts` values), converting to blocks internally via `per_block=20`.
  The YAML key `shared_first_cycle_context_blocks: 576` is in blocks (== 2 d);
  S1b/S2 callers that pass it to these functions should convert `·20` first.
- **Card D-6 cycle count**: "215 cycles per 1872-tick run" is for the dt-aligned
  (j=0) shared-2d plan, reproduced here.  A shifted real-pod origin gives 214
  (card's "190–191 cycles per 1728-tick slice" refers to a 1728-tick real slice,
  a different horizon).
- **`context`/`step_grid_index` alignment**: fit_end is block `e = n0−7` = grid
  index `20e`.  counter context last idx `20e` (increment ending AT fit_end);
  gauge last idx `20e−1` (samples `ts < fit_end`).  Block `b` = steps
  `[20b, 20b+20)` for both.

---

## S1b — hand-off aggregation (`handoff.py`) and resumable shard store (`store.py`)

### Files owned by S1b

- `src/refstudy/refcompare/handoff.py` (`counter_scale`, `block_aggregate`)
- `src/refstudy/refcompare/store.py` (`Shard`, `write_shard_atomic`,
  `read_shard`, `cycles_done`, `META_VERSION`)
- `src/refstudy/refcompare/__init__.py` (extended exports; S1a API unchanged)
- `tests/test_refcompare_handoff.py`, `tests/test_refcompare_store.py`

Repo state at start: `5d657f8` (S1a) + sibling `933925d` (A1c review fixes,
disjoint `plotting`/`harness`/`tests/test_*` paths); working tree clean except
the sibling's pre-commit `plotting/figure.py` edit, which never touches a C1
path and was never staged by this slice.

### `handoff.py`

- `block_aggregate(q[H,9], per_block, n_blocks, scale) -> [n_blocks,9]`:
  `scale * mean(q[per_block*b : per_block*b+per_block], axis=0)` per block
  (mean-of-quantiles, C1 D-4).  Validates `q.ndim == 2`, 9 columns,
  `H >= per_block * n_blocks`, positive `per_block`/`n_blocks`, finite
  `scale` — all raise `ValueError` with the offending value named.
- `counter_scale(blocks, grid, cycle, ctx_blocks, per_block,
  block_offset=0) -> float`: `s_c = sum(v_b)/sum(g_b)` over the context's
  detector blocks `b ∈ [e−ctx_blocks, e−1]` (the blocks FINALIZED by data
  `<= fit_end`, since counter block `b` closes at `T*(b+1)` and
  `fit_end = g_{20e}`), with `g_b = mean(grid[20b+1 : 20b+21])` — exactly the
  context's grid steps `[20(e−ctx_blocks)+1, 20e]`.  `block_offset` lets a
  caller pass a detector array cut to start at a non-zero block (the
  truncation-invariance test case).  NaN detector blocks / NaN grid steps are
  skipped (`nanmean` + finite mask); raises on `ctx_blocks`/`per_block`/
  `block_offset` < 0, context starting before block 0, too-short detector or
  grid arrays, no finite detector block, and a non-positive grid-increment
  sum.

### `store.py`

- `Shard(unit_id, names[str,V], t0[float64,C], q[float32,C,V,H,9],
  digest[float64,C,V,3], meta)` — frozen dataclass; `__post_init__` refuses
  non-float32 `q` (bit-exactness, no widening), non-float64 digest, wrong
  shapes/dtypes, non-all-finite `q` or digest, and `meta` without
  `kind=1, version=META_VERSION(=1)`.
- `write_shard_atomic(path, shard)`: `np.savez_compressed` to
  `<path>.tmp.npz` (the `.npz` suffix is load-bearing: `np.savez` silently
  appends it to any other basename), `flush` + `fsync`, then `os.replace`;
  any failure removes the tmp file and re-raises, so the destination is never
  left partial.
- `read_shard(path, *, expect_meta=None)`: reloads, re-validates via
  `Shard`, and raises `ValueError` when the stored `meta` differs from
  `expect_meta`.
- `cycles_done(path)`: counts the leading cycles whose digest row
  `[V,3]` is all-finite (a cycle C2 digests only after its forecast is
  final).

### Gates (literal, post-commit)

```
$ .venv/bin/python -m pytest tests/test_refcompare_config.py \
    tests/test_refcompare_grid.py tests/test_refcompare_cycles.py \
    tests/test_refcompare_handoff.py tests/test_refcompare_store.py -q
.......................................................                  [100%]
```
(55 passed, 0 skipped: S1a's 38 + 17 hand-off + store tests.)

```
$ .venv/bin/ruff check src/refstudy/refcompare \
    tests/test_refcompare_config.py tests/test_refcompare_grid.py \
    tests/test_refcompare_cycles.py tests/test_refcompare_handoff.py \
    tests/test_refcompare_store.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare
# (empty, exit 1)

$ git diff --check
# (clean)
```

### Commit

```
feat(refstudy): add refcompare hand-off aggregation and resumable shard store (C1 slice 1b)
```

Commit hash: `002170d` (lab repo `main`, 5 files, +727/−4; owned paths only,
explicit `git add`, never `-A`).

### Deviations / notes

- **Context block range for `counter_scale`**: the detector counter block
  `b` is right-closed `(left, right]` (the `build_blocks` law) and FINALIZES
  at `right`; with `fit_end = g_{20e}` the last finalized block is
  `e−1`, so the context spans `b ∈ [e−ctx_blocks, e−1]` and the grid
  increments used are steps `[20(e−ctx_blocks)+1, 20e]` — i.e. the SAME grid
  points the model context ends on (the counter context's last point,
  S1a fact 4).  This is the only way `s_c` stays strictly context-side
  (leakage-free): block `e`'s own increments end AFTER `fit_end`.  The
  workcard's "blocks of the cycle's own context" is read as "detector blocks
  whose value was computed from data ≤ `fit_end`".
- **`s_c` on real data ≈ 16.4/15, not 16/15**: the card's step-1.3 value
  `16/15` was reproduced verbatim on a hand-built constant-rate 16 s series
  (detector value 32.0/sample interval vs grid increments 30.0/step); the
  campaign D2 real-data mean interval 16.4 s gives `s_c ≈ 16.4/15`
  (separate test, `rel=1e-9`).
- **`Shard` is strict about dtypes**: `q` MUST arrive float32 (the contract:
  "float32 kept so the forecasts are exact") — no silent downcast, so a
  caller passing a float64 model output gets a `ValueError` at
  construction.  `meta` must be a dict carrying `kind=1` and
  `version=1`; `read_shard(expect_meta=…)` enforces exact equality for C2's
  unit-key checks.
- **Partial-shard fixture**: `write_shard_atomic` refuses non-finite digests
  (a shard is only ever written fully digested), so the
  `cycles_done` partial-fill tests model C2's crash-mid-fill state by
  hand-writing the `.npz` with a NaN digest row — the on-disk shape C2's
  resume will actually see.
- **tmp filename is `<path>.tmp.npz`**, not `<path>.tmp`: `np.savez*`
  appends `.npz` to a basename lacking it, which would write a different
  file than the one `os.replace` moves.

---

## S2a — `TimesFmProvider`: the production `ReferenceRun` from the per-cycle quantile forecasts

### Files owned by S2a

- `src/refstudy/refcompare/provider.py` (`TimesFmProvider`)
- `src/refstudy/refcompare/__init__.py` (export `TimesFmProvider`; S1a/S1b API unchanged)
- `tests/test_refcompare_provider.py` (12 tests)

Repo state at start: `002170d` (S1b) + sibling `933925d` (A1c review fixes,
disjoint paths).  A sibling executor (B2 fixB: `src/refstudy/compute/podgen.py`,
`config/refresh_study.yaml`, `tests/test_compute_podgen.py`) works concurrently
on disjoint files and was never staged by this slice.

### `provider.py`

`TimesFmProvider(ref_cfg, rc_cfg, *, counter, cycles, q[C, 260, 9], scale[C],
min_served=None).run(blocks, ticks) -> ReferenceRun` with `.cycles`, `.scale`
and `block_bands() -> [C, 13, 9]` (all workcard 2.1 contract lines).

* **forecast (D-3/D-4)**: cycle `c` serves tick indices
  `k in [n0_c - 1, n0_c + 5)` and the forecast is
  `s_c * mean(q_c[20b : 20b+20, 4])` with `b = k - e_c` via `block_aggregate`
  (median index 4 from `rc_cfg.hand_off`); `model_t0[k] = t0_c`,
  `fit_end[k] = t0_c - T - dt`.
* **record (D-5)**: the residual log of the SERVED blocks grows with EVERY
  cycle (`obs[n] - F_c[n - e_c]`); an unobserved (NaN) block adds no entry;
  the residual of cycle `j` is USABLE from cycle `j + 2` (its newest served
  block ends AT `fe_{j+2}` — the `check_no_leakage` equality case); the record
  served at cycle `c` is the last `min(570, usable)` log entries = the
  production window `[fe_c - 570*T, fe_c)`.  (SUPERSEDED by FIX C1b / RV-C F3:
  the lower index comes from the TIMESTAMP cutoff `fit_end - 570*T`, not a
  finite-entry count — see § Fix C1b.)
* **gate (D-5, derived)**: `has_model` only while
  `usable >= min_served`, `min_served = (Dt - dt)/T - noise.min_fit_blocks`
  (= 522) unless overridden (smoke-only argument, like `cold_start_t0`).
* **ess (D-8)**: `bartlett_ess` (A1a, `noise.bartlett_max_lag`) of the finite
  detector block values of the production window `[fe_c - 570*T, fe_c)`
  (clipped at the pod origin for early cycles); INFORMATIONAL ONLY — the
  provider never reads `noise.min_effective_samples`, so the floor cannot gate
  any field.

NaN conventions: where no model serves a tick, `forecast/model_t0/fit_end/ess`
are NaN and `rec_lo/rec_hi` are `-1`.  `q` must be all-finite (the NaN policy
is grid-side, D8); `scale` finite and > 0; `blocks.T == grid.tick_seconds`.

### Tests (behaviour, no real model)

Synthetic quantile arrays: the workcard 2.1 stub `q = mean(context blocks)
+ per-cycle offset + per-block ramp` (all 9 levels equal); observed blocks are
constant-rate detector blocks (a real `build_blocks`-shaped series).

* the returned `ReferenceRun` passes `check_no_leakage`; a `fit_end + T` or
  `rec_ts + 2T` wrapper raises;
* forecast at tick `k` equals the hand-off of the RIGHT cycle's block offset
  (`k in [n0_c - 1, n0_c + 5)`, `b = k - e_c`, `s_c = 1.5` scale check);
  `t0` an absolute multiple of `dt`;
* record rule D-5 with `min_served=12` (first model `k+1 = 42`): record =
  last `min(570, usable)` entries, `rec_ts` ascending from block 23,
  `rec_val = obs - F` of the SERVING cycle;
* derived gate (`min_served=None`): first model `k+1 = 552` carrying the
  522-entry COLD record; the 570-block window fills at cycle 96 (`k in
  [599, 605)`); D-6's first scored `k+1 = 554` (552 + 2 ring-fill ticks, a
  pod-chain property);
* ticks before the first model: `has_model=False`, NaN / `-1` conventions;
* `ess` invariance: `noise.min_effective_samples` 0 vs `10**6` (`RefConfig`
  `dataclasses.replace`) gives bit-identical `forecast/model_t0/fit_end/ess`
  and all `rec_*` (no gate);
* `ess[k]` equals the hand-computed `bartlett_ess` of the window;
* a NaN observed block adds no record entry (log 6C-1 vs 6C) and the forecast
  is unchanged;
* the produced run feeds the UNCHANGED `refstudy.reference.score_pod` on a
  tiny 3-continuous + rare-count-free chain (`include_rare_count=false` via
  `dataclasses.replace`, as the harness's `_chain_cfg` does): synthetic oracle
  forecast (= the true clean block value: cpu 3.0/increment, mem 1000.0,
  rx_bytes 5.0/increment on a regular 15 s grid) ⇒ `score_pod` returns
  125 `TickRecord`s; every scored tick has a finite `p_raw`, metric `p = 1.0`
  (zero residual against the all-zero record) and zero metric residual; the
  posterior settles to the quiet-floor point mass `0.001288171…` (< the 0.2
  threshold).  Measured first scored `k+1 = 44` (first model `k+1 = 42` + 2
  ring-fill ticks, `min_served=12`).

### Gates (literal, post-commit)

```
$ .venv/bin/python -m pytest tests/test_refcompare_*.py -q
...................................................................      [100%]
```
(67 passed, 0 skipped: S1a 38 + S1b 17 + S2a 12.)

```
$ .venv/bin/ruff check src/refstudy/refcompare tests/test_refcompare_*.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare
# (empty, exit 1)

$ git diff --check
# (clean)
```

### Commit

```
feat(refstudy): add TimesFM reference provider returning the production ReferenceRun (C1 slice 2a)
```

### Deviations / notes

- **First-model tick vs first-scored tick**: the D-5 gate makes `has_model`
  true at `k+1 = 552` (derived) / `42` (`min_served=12`); D-6's "first scored
  `k+1 = 554`" includes the 2 ring-fill ticks of the pod chain (eligibility
  after `min_strikes_to_score = 3` scored `p`s), which the provider does not
  see — the two notions are asserted separately (`test_derived_gate_…`,
  `test_score_pod_on_oracle_forecast`).
- **Record served at the GATE cycle is the COLD record** (522 entries), not
  empty: at cycle 88 `usable = 522 = min_served`, so the record is the whole
  usable log so far (blocks 23…544).  The card's "record sizes 6(i-1) then the
  570-block window" is read as the GROWTH of usable entries, of which the
  served record is the last `min(570, usable)`.
- **`e = n0 - 7`**, not `n0 - 1`: the fit-end block index of cycle `n0` is
  `e = n0 - 7` (`fit_end = t0 - T - dt = origin + T*(n0 - 7)`), as S1a's
  `Cycle` already encodes; served blocks are `n in [n0 - 1, n0 + 5)` =
  offsets `b in [6, 12)`.
- **The residual log grows with every cycle, not only model-serving cycles**:
  `q` holds the forecast of ALL C cycles, so the served-block residuals
  `obs - F_c` exist for warm-up cycles too; the gate only controls
  `has_model`/record SLOP, mirroring production (the persisted record already
  contains the cold-window residuals when the first model appears).
- **Oracle-chain K=3 chain**: built as the harness does
  (`dataclasses.replace` of `RefConfig.metrics` with
  `include_rare_count=false` and the 3 continuous entries cpu/mem/rx_bytes);
  `build_blocks` on the regular raw grid gives exactly the constant-rate
  block values (3.0 / 1000.0 / 5.0) that the oracle `q` forecasts, so all
  metric residuals are 0 and `p = 1.0`.

---

## S2b — pod pipeline (`pipeline.py`), paired variants (`variants.py`), CPU smoke

### Files owned by S2b

- `src/refstudy/refcompare/pipeline.py` (`build_providers`, `run_pod_timesfm`)
- `src/refstudy/refcompare/variants.py` (`make_variant`, `variant_name`,
  `VARIANT_BASES`, `VARIANT_KEEPS`)
- `src/refstudy/refcompare/__init__.py` (extended exports; S1a/S1b/S2a API
  unchanged)
- `tests/test_refcompare_pipeline.py` (6 tests),
  `tests/test_refcompare_variants.py` (7 tests)
- `scripts/smoke_refcompare.py` (CPU smoke, real weights)
- `results/c1-smoke-cpu.json` (small, tracked)
- `markdown/refcompare.md` (52 lines)

Repo state at start: `bf894d7` (S2a).  A sibling executor (B2 fixB) landed
`6b99fb3` (`compute/podgen.py` etc.) during this slice; disjoint paths, never
staged by this slice.  Two sibling-modified files were in the tree at start
(`results/a1a-parity.json`, later `src/refstudy/compute/config.py`) — NOT in
the S2b commit.

### `pipeline.py`

`build_providers(raw, cfg, rc_cfg, *, forecasts, first_n0, ctx_pts,
min_served=None, max_cycles=None)`: raw for ALL 11 canonical entries ⇒
`pod_origin`, `plan_cycles`; `C == len(plan)` (or `== max_cycles` with the
plan truncated to its first `max_cycles` cycles, smoke/test-only) and
`H == horizon_blocks * per_block == 260` validated (shape errors raise,
offender named); per continuous metric: `to_grid` (D-2), detector
`build_blocks`, `counter_scale` per cycle (D-4; gauges `s_c = 1`), one
`TimesFmProvider`.  `ctx_pts` must be one of the refcompare context values
(240 / 5760 / 11520).

`run_pod_timesfm(…same args…) -> PodRun`: the `run_pod` mirror —
`build_blocks` for all 11, UNCHANGED `RareCountProvider` for the 7 rare-count
series, one `TimesFmProvider` per continuous metric, UNCHANGED `score_pod`.
The pod block grid is extended to `n0_last + 5` blocks (the provider's
residual-log tail beyond `n_ticks`; the extra blocks are unobserved NaNs and
the chain only reads `k < n_ticks`).

### Tests (no real model; deterministic oracle + FLAT scenarios)

- **Oracle pipeline** (`test_run_pod_timesfm_oracle_residuals_and_rare_counts`):
  constant-rate regular raw grid (cpu 3.75, mem 1000.0, rx/tx 1.875; 7
  zero-rate rare counters); the oracle fills every served-block forecast with
  the observed block value ⇒ every scored continuous residual is EXACTLY 0,
  `p = 1.0`; the 7 rare-count `runs` are field-for-field identical to
  `run_pod`'s (the rare-count part is the same code); blocks identical on the
  chain's domain; `check_no_leakage` ok.  First model `k+1 = 606`
  (derived: `first_n0=588` + gate cycle 3, `min_served=12`); 1267 model ticks;
  first SCORED tick `k+1 = 606` (before it the mandatory cpu has no model; at
  it the already-eligible rare-count metrics carry the ring, so no 2-tick
  lag at the pod level when the continuous first model lands exactly on a
  ring-ready tick).
- **`build_providers` validation**: `C=8` vs plan 215 raises; `C=9` vs
  `max_cycles=8` raises; `H=240` raises; 2-D forecast raises;
  `max_cycles=216 > plan` raises; missing forecast / missing raw raise.
- **`max_cycles` truncation**: the FIRST 8 cycles of the plan; 30 model ticks
  (cycles 3..7); nothing served past `n0_8 + 5`.
- **`variants.py`**: `S4@cpu` has the two bumps with `signals == (("cpu",
  25.0),)` and the base onsets; every other signal's `target` equals
  `S4@none`'s bit-for-bit; `S4@rx_bytes` bumps rx AND tx (A1b3 mirror) and
  nothing else; `S6@cpu` keeps the drift (`drift, bump`); `S6@none` drift
  only; `make_variant` rejects non-base names, `keep ∉ {cpu, mem, rx_bytes,
  None}`, duplicate registration; paired sha256: every series the kept bump
  does not touch equals `S4@none`'s byte-for-byte (cpu variant: mem/rx/tx +
  7 rare; mem variant: cpu/rx/tx + 7 rare; between the two variants: rx/tx +
  rare equal).

### Gates (literal)

```
$ .venv/bin/python -m pytest tests/test_refcompare_*.py -q
........................................................................ [ 90%]
........                                                                 [100%]
```
(80 passed, 0 skipped: S1a 38 + S1b 17 + S2a 12 + S2b 13.)

```
$ .venv/bin/ruff check src/refstudy/refcompare scripts/smoke_refcompare.py \
    tests/test_refcompare_*.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare
# (empty, exit 1)

$ git diff --check
# (clean)
```

### CPU smoke (S2.3, real weights, device `cpu` only)

```
$ .venv/bin/python scripts/smoke_refcompare.py \
    --config config/refcompare.yaml --out results/c1-smoke-cpu.json
smoke results/c1-smoke-cpu.json -> ok (8.8 s)
```
(`--device mps|mlx` is refused: the C1 S2b smoke is CPU-only; C2 is the
CUDA run.)  FLAT seed 1, 700 ticks, K=11; ctx 240: 8 cycles (`first_n0=24`),
ctx 5760: 2 cycles (`first_n0=300`), H=260; per cycle one multivariate
(V=4) + 4 univariate calls.  JSON (excerpt):

```
overall ok, wall 8.8 s, load 1.51 s
ctx_240:  shapes (4,260,9) / (260,9), finite T/T, non-crossing T,
          uni_vs_multi_max_abs_diff_q50 = 57.09,
          digests_equal_after_float32_round_trip = true
ctx_5760: shapes (4,260,9) / (260,9), finite T/T, non-crossing T,
          uni_vs_multi_max_abs_diff_q50 = 17.59, digests equal
nan_probe: finite, median within 8.51 of last valid level 23.79
          (20 trailing + 1 interior NaN; D8 fill on the real wheel)
pipeline: 700 records, 11 metrics, check_no_leakage ok,
          first_model k+1 = 42, first/last scored k+1 = 44 / 71, 28 scored
ms/call: 50 calls, 100.1 / 100.8 (median) / 440.9
```
Measured first scored `k+1` with the real model: **44** (= first model 42 +
the 2 ring-fill ticks of `min_strikes_to_score=3`, D-6).

### Deviations / notes

- **First scored tick is NOT first_model + 2 in the oracle test**: the pod
  scores as soon as some metric is eligible; with K=11 the quiet rare-count
  metrics (NB, `k=0 ⇒ p=1.0`) become eligible two ticks after their first
  cycle-0 model, earlier than the continuous gate.  The continuous first
  model still lands on `k+1 = 606` and its p scores on that same tick because
  the ring is already ready.  The S2a "+2" rule (first model + 2 ring-fill)
  is a property of a chain where the metric itself is the first to become
  eligible (K=3, cold continuous-only start).
- **Oracle `q` fills the whole horizon with the observed constant** (all 9
  levels, all 13 blocks): the provider's `q` must be all-finite (S2a D8),
  and the tail blocks past `n_ticks` are unobserved NaNs anyway, so the
  filler can never leak into a scored residual.
- **`ctx_5760` capped at 2 cycles in the smoke** (card: "ctx 5760 (2 cycles)");
  `max_cycles` is the smoke-only argument for that.
- **Pod block grid extended to `n0_last + 5`**: the provider's residual log
  reaches those blocks; they are NaN (unobserved) and never scored.  `run_pod`
  (STL path) builds `n_ticks` blocks only, so the two pipelines' block series
  are compared on the chain's domain `k < n_ticks`.

## Fix C1a — RV-C F1: causal per-cycle context and counter scale from raw samples up to `fit_end`

RV-C F1 (blocker): the 15 s grid was built ONCE from the complete raw series,
so a grid point at/before `fit_end` could interpolate against a raw sample
AFTER `fit_end` — the context (and, on a jittered counter, the `counter_scale`)
leaked the future raw.  The fix shares ONE causal construction across the
runner, the provider `counter_scale` and the evaluator; the fixed pod grid
(`origin` / `cadence`) and the D8 NaN policy are preserved.

### Change
- `grid.to_grid(..., ts_cut=None)`: when set, truncates the RAW SOURCE to
  `ts <= ts_cut` (via `searchsorted(side="right")`) before resampling; a grid
  value is NaN wherever no PAST-ONLY bracket exists.  Output is invariant to
  any raw sample after the cut.
- `cycles.causal_grid(raw, cycle, *, origin, cadence, per_block, counter,
  max_gap)`: returns EXACTLY the `[0, context_hi)` window the context and
  `counter_scale` read — counter `hi = 20e + 1` (the increment ending at
  `fit_end`), gauge `hi = 20e` (samples before `fit_end`) — built past-only
  (`ts_cut = cycle.fit_end`).
- `cycles.causal_context(...)`: the SHARED construction — `context(causal_grid(...))`.
- `runner.UnitBuild` gains `raw` (the model's data source), `cadence`,
  `per_block`, `max_gap` and a `.context(cycle, name, ctx_pts)` method that
  delegates to `causal_context`.  All three model-context call sites
  (`_write_shard`, `_run_unit`, `_probe`) now use `build.context(...)`.
- `pipeline.build_providers`: the counter branch feeds `counter_scale` the
  `causal_grid` (the detector `build_blocks` are intrinsically causal — block
  `b` uses only `left < ts <= right`, all `<= fit_end` — so only the grid side
  leaked).
- `evaluate.verify_shard` / `tfm_pod`: `_shard_frame` now returns the
  CANONICAL-KEYED sliced raw (the model's data source, sliced by `real_slice`
  on `real.days`, exactly as `build_unit`) instead of the full grids;
  `_check_frame` rebuilds every context via the SHARED `causal_context`.

### b4xkt real-data, first cycle (c=0, n0=589, e=582, `fit_end`=1793854500, ctx=11520)
Old (full-series) → New (causal) context digests `(sum, sumsq, n_nan)` — the
new values match RV-C's recorded expected values exactly:

| metric | kind | old | new |
|---|---|---|---|
| cpu | counter | `(172773.7901574422, 2591215.376214618, 0)` | `(172758.79532256053, 2590990.531141489, 1)` |
| mem | gauge | `(2932938581822.462, 7.46732141892491e+20, 0)` | IDENTICAL |
| rx_bytes | counter | `(61852876.41723047, 343286436723.7129, 0)` | `(61847669.08691032, 343259320434.6497, 1)` |
| tx_bytes | counter | `(40010219.89246969, 143641490472.38077, 0)` | `(40006851.722232014, 143630145901.6308, 1)` |

Each counter gains exactly ONE past-only NaN at the fit-end increment (the
bracketing raw sample is after `fit_end`); the gauge (mem) is unchanged.  `test_real_unit_causal_context_is_past_only`
asserts `build.context(...) == context(to_grid(raw[ts<=fit_end]))` bit-exactly
and `n_diff vs full == 3` (cpu/rx/tx).

### Synthetic digest identity
On a regular 15 s grid every grid point at/before `fit_end` interpolates
against raw partners all at/before `fit_end`, so the causal context is
**BIT-IDENTICAL to the old full-series context** (860/860 context digests for
the S1/S2/FLAT/S4 seed-1 units).  `test_synthetic_causal_context_is_digest_identical`
asserts `causal == old` bit-exactly on 3 synthetic units (S1/S2 240, S4 11520),
plus: the NaN count matches the committed shard digests exactly (860/860), and
sum/sumsq are within 4 ULPs of the committed shard — a PRE-EXISTING
cross-platform accumulation artefact (the committed shards were produced on
the x86 CUDA host; the old full-grid code on this ARM Mac is likewise 1–4 ULP
off in sumsq), NOT introduced by the fix.

### Tests added
- `tests/test_refcompare_cycles.py`:
  - `test_causal_context_counter_jittered_truncation_invariant` — jittered
    counter extending past `fit_end`: causal == truncated-rebuild (bit-exact),
    != full-series (one past-only-NaN vs finite at the fit-end increment).
  - `test_causal_context_gauge_straddling_bracket` — a raw bracket straddling
    `fit_end`: causal last context point NaN, full-series finite; truncation
    invariant holds.
  - `test_causal_context_regresses_full_series_construction` — the regression
    guard: FAILS if the construction reverts to slicing the full grid.
  - `test_causal_grid_window_matches_context_hi` — `causal_grid` returns
    exactly `[0, context_hi)` (counter `20e+1`, gauge `20e`), past-only.
- `tests/test_refcompare_handoff.py`:
  - `test_counter_scale_causal_grid_is_past_only` — the causal `counter_scale`
    is invariant to appending raw after `fit_end` (a pure function of the raw
    past `fit_end`), and the causal grid == the truncated past-only resample.
- `tests/test_refcompare_runner.py`:
  - `test_real_unit_causal_context_is_past_only` (b4xkt first cycle, above).
  - `test_synthetic_causal_context_is_digest_identical` (above).
  - `test_shard_digests_equal_c1_digests` now rebuilds via `build.context`
    (the SHARED causal context) rather than the full grid.

The 20 committed REAL shards are now stale by design (they hold the leaked
full-series contexts) and correctly fail `verify_shard` under the new causal
code; the Supervisor regenerates them.

### Gates (literal)
```text
.venv/bin/python -m pytest tests/test_refcompare_*.py -q -p no:cacheprovider
269 passed, 0 skipped
.venv/bin/ruff check --no-cache src/refstudy/refcompare tests/test_refcompare_{grid,cycles,handoff,pipeline,runner}.py
All checks passed!
grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare   # (empty, exit 1)
git diff --check                                            # (clean)
```

---

## Fix C1b — RV-C F2, F3, F9: pipeline leak check, time-window residual record, policy provenance

Three RV-C findings, in disjoint owned files: `src/refstudy/refcompare/{provider,
pipeline,runner}.py` (+ `run_config.py`), `tests/test_refcompare_{provider,
pipeline,runner}.py`.  No chain-law/threshold change; no shard/manifest
regeneration (S regenerates the real units and re-writes the manifest — the
committed C2 store + `results/c2-run-manifest.json` are untouched by this fix
and stay readable: every new key is additive).

### F2 — pipeline applies the leakage checker (`pipeline.py`)

`run_pod_timesfm` now calls the UNCHANGED `check_no_leakage` on EVERY
CONTINUOUS `ReferenceRun` BEFORE `score_pod` (a real `ValueError` naming the
offending tick/record entry — not the provider's `assert`, which is dead under
`-O`, and not left to C3's outer `tfm_pod` wrapper that direct pipeline callers
do not go through).  Module + function docstrings document the guard.

### F3 — residual record cut at the TIMESTAMP cutoff, not a finite count (`provider.py`)

`TimesFmProvider.run`: the record served at cycle `c` is the usable entries
(the c+2 upper bound `[0, usable)`) whose block-start timestamp lies in the
production window `[fit_end − 570·T, fit_end)`.  The LOWER index is now
`searchsorted(log_ts, origin + (i_e − 570)·T, "left")` (with `i_e` the
fit-end block index) instead of `usable − 570`.  One unobserved block inside a
full active window therefore yields a 569-entry record, never a 570-entry
record reaching 300 s past the cutoff (the RV-C probe: one missing served
block ⇒ old code returned an entry 300 s too old).  An empty window (all 570
window blocks unobserved) withholds the model for the cycle (`rec_lo/rec_hi =
-1`) like a gated cycle.  The mistaken equivalence statement ("the last 570
usable entries = the production window") is corrected in the provider
docstring, the test-module docstring and the record-rule test docstring.

### F9 — effective input policy recorded in manifest + shard meta (`runner.py`, `run_config.py`)

New `POLICY_VERSION = "causal-fit-end-v1"` and `input_policy(cfg, ref_cfg,
rc_cfg, *, settings=None, git_head=None)` returning a JSON-plain dict with:
grid cadence, `tick_seconds`, `per_block`, `max_gap_seconds`, the
interpolation/NaN policy (`input.missing.policy` = "nan"), the
`counter_scale_estimator`, the CAUSAL-BOUNDARY policy (after FIX C1a `a7133a3`:
per-cycle contexts AND counter scale built past-only from raw samples
`ts <= fit_end` via `cycles.causal_grid`/`causal_context`), the
timestamp-cutoff record-window statement (RV-C F3), the config sha256 of
`refcompare.yaml` / `refcompare_run.yaml` / `reference.yaml` /
`scenarios.yaml`, the model `revision` + weights `sha256` from
`config/timesfm3.yaml`, the code `git rev-parse HEAD` of the study repo
(`"unknown"` when git is unavailable), and the `policy_version` string.
`RunConfig` gains a `run_yaml` field (the `refcompare_run.yaml` path, so the
digest is taken of the ACTUAL loaded file, not a re-resolved default).
`run_slice` computes the policy once per process, writes it to the manifest as
the run-level `input_policy` key, and threads it into `_write_shard` so every
shard's `meta` carries `meta["policy"]` (an isolated shard stays bound to the
policy that produced it; the manifest is the full record).  `settings` /
`git_head` are injectable (tests); defaults load the study's
`config/timesfm3.yaml` and run `git rev-parse HEAD`.  A missing one of the
four hashed configs raises (no silent default).

### Tests added (behaviour, deterministic)

- `test_refcompare_pipeline.py`:
  - `test_run_pod_timesfm_checks_no_leakage_on_every_continuous_run` — a spy
    on the module-level checker counts exactly the 4 continuous `ReferenceRun`s
    checked before the chain scores (the clean oracle still returns its
    `PodRun`, so the guard is a pass, not a skip);
  - `test_run_pod_timesfm_raises_on_leaking_run` — monkeypatching
    `TimesFmProvider.run` to return every finite `fit_end` shifted by `+T`
    makes the pipeline raise a real `ValueError` matching `leakage` (NOT an
    `AssertionError`); the un-patched clean run passes the same guard.
- `test_refcompare_provider.py`:
  - `test_record_window_cuts_at_timestamp_cutoff_inside_full_window` — one
    missing served block inside a full active window (block 400): at c=96 and
    c=99 every returned record timestamp is inside the D-5 window
    `[fe − 570·T, fe)`; the record holds exactly `i_e − lo_blk − 1` entries
    (the missing block excluded); the old count-based `lo` starts one entry
    (300 s) too early and is asserted to be exactly one slot before the
    timestamp-cutoff `lo`;
  - `test_record_window_withholds_model_on_empty_window` — blocks observed up
    to 1000 then all NaN on a 1600-tick plan: the gate (522) first holds at
    c=88 (522-entry cold record), the window still holds the in-window tail
    until c=258 (6 entries, starting exactly at the cutoff block 995), and
    from c=259 the empty window withholds the model (`rec_lo/rec_hi = -1`,
    `has_model` False).
- `test_refcompare_runner.py`:
  - `test_input_policy_records_the_effective_input_policy` — the `input_policy`
    dict carries `policy_version`, cadence/`per_block`/`max_gap`/NaN policy,
    the causal-boundary statement (`ts <= fit_end`), the four config sha256s
    (equal to the file digests), the `timesfm3.yaml` model revision + weights
    sha256, and the git head;
  - `test_smoke_run_writes_input_policy_to_manifest_and_shard_meta` — a smoke
    run writes `doc["input_policy"]` to the manifest AND the SAME dict to each
    shard's `meta["policy"]`; the pre-F9 meta keys are all still present
    (additive, readers stay compatible).

### Gates (literal)

```text
# every refcompare test file EXCEPT tests/test_refcompare_coverage.py — that
# file was mid-edit by a CONCURRENT executor (C4 fix, band_label/width_curve)
# at run time and its module no longer imports (its OWN WIP, not this fix).
.venv/bin/python -m pytest tests/test_refcompare_bands.py ... tests/test_refcompare_variants.py -p no:cacheprovider
272 passed, 0 failed, 0 skipped
.venv/bin/ruff check --no-cache src/refstudy/refcompare/{provider,pipeline,runner,run_config}.py tests/test_refcompare_{provider,pipeline,runner,run_config}.py scripts/run_refcompare.py
All checks passed!
grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare   # (empty, exit 1)
git diff --check                                            # (clean)
```

F3/F9 probe evidence (independent of the repo tests, `throwaway/f3_probe.py`
during the run; the behaviour is now pinned by the tests above): with one
missing block inside a full window, c=99 (n0=618, e=611, usable=587) serves a
569-entry record whose oldest block start sits EXACTLY on the cutoff
(block 41, `0 s` vs `[fe − 570·T, fe)`), while the old count-based lower index
would have started at block 40 (300 s too old, `lo_old = 17` vs new `lo = 18`).

### Notes

- The committed C2 manifest + 118 shards are NOT regenerated or modified here
  (S regenerates the real units and re-writes the manifest after the F1
  regeneration; the F9 keys attach to the NEW write).  `verify_store` and
  `read_shard` ignore unknown manifest/meta keys, so the pre-fix store keeps
  working unchanged.
- `input_policy` hashes the four YAML files BY PATH (the study dir), not by
  in-memory config, so a YAML edit between load and run is still auditable
  from the recorded digests.
- No `config/refcompare*.yaml` key was needed for F9: the provenance is
  DERIVED from the configs the run already loads (their digests, the
  `timesfm3.yaml` model identity, the git head) — nothing new is configurable.
