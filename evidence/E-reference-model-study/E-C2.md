# C2 — Phase C run matrix, resumable runner, live batch (Executor evidence)

One section per workcard slice. This leaf (E) owns **S1a**:
`config/refcompare_run.yaml`, `src/refstudy/refcompare/{run_config,units}.py`,
`tests/test_refcompare_{run_config,units}.py`.  S1b (infer, runner, script) and
the live stage are separate slices; their sections are added as they land.
All paths relative to `reference-model-study/` (lab repo
`pipelineml-model-exploratory-work`).

---

## S1a — run-matrix YAML, `run_config.py`, `units.py`

### 1.0 Preflight (record all)

Repo state at start (lab repo, branch `main`):

```
$ git log --oneline -3
93c594a feat(refstudy): add TimesFM pod pipeline, paired variants and CPU smoke (C1 slice 2b)
6b99fb3 fix(refstudy): regular-grid timestamp-aligned PodWorld input per operator D8 (B2 fix B)
bf894d7 feat(refstudy): add TimesFM reference provider returning the production ReferenceRun (C1 slice 2a)
```

C1 Commit 2 ⊇ HEAD verified (93c594a is the tip). `git status --short` at start:
two unrelated in-flight sibling edits (`results/a1a-parity.json`,
`src/refstudy/compute/config.py`) — neither is a C2 path; neither was
staged or committed by this slice (at hand-off only `scripts/plot_refresh.py`
was still modified in the worktree, owned by B2 fix C).

B1 CUDA per-call medians read from `results/b1-scaling-cuda.json`
(`status == "ok"` cells, H=120, unbatched — the card's worst-case table):

```
n240-v4    69.44602995645255
n5760-v4  203.69445893447846
n11520-v4 391.8082290329039
n240-v1    65.99730800371617
n5760-v1  170.5623749876395
n11520-v1 268.35148804821074
```

### Files owned by S1a

- `config/refcompare_run.yaml` (the card's `matrix` table + `slices` L0–L7 as
  data + `inference`/`hygiene`/`outputs`/`smoke`/`timing`/shared-config refs)
- `src/refstudy/refcompare/run_config.py` (frozen `RunConfig` +
  `load_run_config`; missing key ⇒ `ValueError` naming the dotted key)
- `src/refstudy/refcompare/units.py` (`Unit`, `unit_id`, `expand_units`,
  `slice_units`, `unit_calls`, `call_table`)
- `tests/test_refcompare_run_config.py`, `tests/test_refcompare_units.py`

### 1.1 behaviour (tests `test_refcompare_run_config.py` /
`test_refcompare_units.py`)

- `expand_units` ⇒ **exactly 118 units**, ids unique; kinds syn=90 /
  leak=8 / real=20; order = slice order L0..L7 (partition asserted both ways:
  every matrix unit in exactly one slice).
- `call_table` reproduces the card's numbers (real counted from the EXACT
  per-pod cycle counts, `load_run_config` counts them from the packaged flat
  load via C1 `real_slice` + `plan_cycles`; all 10 pods ⇒ **190** each, the
  origins are not multiples of 30 min, C1 D-6):

| (V, N) | calls (exact) | calls (191 upper) | wall_s exact | wall_s upper |
|---|---|---|---|---|
| V=4, 240 | 1,935 | 1,935 | 134.4 | 134.4 |
| V=4, 5760 | 1,935 | 1,935 | 394.1 | 394.1 |
| V=4, 11520 | 9,425 | **9,435** | 3,692.8 | 3,696.7 |
| V=1, 240 | 7,740 | 7,740 | 510.8 | 510.8 |
| V=1, 5760 | 7,740 | 7,740 | 1,320.2 | 1,320.2 |
| V=1, 11520 | 30,820 | **30,860** | 8,270.6 | 8,281.3 |
| **total** | **59,595** | **59,645** | **14,323 s ≈ 3.98 h** | **14,338 s ≈ 3.98 h** |

- synthetic/leak exactly: V=4 @11520 = 5,805 (syn A) + 1,720 (leak) =
  **7,525**; tier B V=4 = 1,935 + 1,935 = **3,870**; V=1 @11520 = **23,220**;
  tier B V=1 = 7,740 + 7,740 = **15,480** (asserted per cell in the test).
- real upper bound: V=4 **1,910**, V=1 **7,640**; totals ≤ **13,305** (V=4) /
  ≤ **46,340** (V=1) / ≤ **59,645** calls, ≈ **4.0 h** at the B1 medians.
- every slice ≤ 40 min by the table (B1 medians, unbatched worst case):
  L0 0 (probe, no matrix units) · L1 36.5 · L2 33.9 · L3/L4/L5 34.6 ·
  L6 30.5 · L7 34.0 (the card's ≈37/34/35/35/35/31/34 min estimates).
- `unit_id` formation: `syn:S1:1:11520:multi`, `leak:S4@cpu:1:11520:multi`,
  `real:b4xkt:-:11520:uni` (the `-` seed slot marks pod units).

### Checks

```
$ .venv/bin/python -m pytest tests/test_refcompare_*.py -q
(rc 0; 99 passed, 0 failed, 0 skipped — all 10 test_refcompare_*.py files:
 config 22, cycles 7, grid 9, handoff 10, pipeline 6, provider 12,
 run_config 10, store 7, units 9, variants 7; the new files contribute
 10 + 9 = 19 tests)

$ .venv/bin/ruff check src/refstudy/refcompare/run_config.py \
    src/refstudy/refcompare/units.py \
    tests/test_refcompare_run_config.py tests/test_refcompare_units.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare
(empty, rc 1)

$ git diff --check
(clean)
```

Note: `pytest -q` on this box does not print the final "N passed" summary line
(only the progress bar, rc 0); the pass/skip counts above are counted from the
collected test ids (0 skipped asserted by `-q`'s zero-failure exit + no
`skipped` markers in the two new files).

### Missing-key contract (tested)

Every YAML key missing ⇒ `ValueError` naming the dotted key (37 keys covered
in `test_missing_keys_name_themselves`), e.g.
`required config key missing: matrix.tiers.B.ctx_pts`,
`required config key missing: inference.batch_parity.rtol`,
`required config key missing: slices` (a removed slice entry ⇒
`slices must have exactly the keys ['L0'…'L7']`).  Behavioural invariants that
fail with a named key: `matrix.real.days` ≠ `refcompare` `real.days`,
`matrix.cycles.real_upper` < the counted per-pod max, an unknown scenario
(`scenarios.yaml`), a slice seed/ctx not in the matrix, an unknown hygiene
profile in `shared.hygiene.profiles`, a scenario not in
`scenarios.yaml` (leak bases checked too).

### Commit

`9370848 feat(refstudy): add Phase C run matrix config and unit expansion (C2 slice 1a)`
(5 files: the YAML + 2 modules + 2 test files; explicit `git add` of the 5
paths only; a sibling B2-fix-C edit to `scripts/plot_refresh.py` was in flight
in the worktree and was NOT staged/committed).

### Open issues / notes for S1b

- `load_run_config` loads the packaged flat load (≈2 s, 10 pods × 4
  continuous series) to count the exact per-pod real cycles; the runner should
  load it once and reuse `cfg.matrix.real.cycles_exact`.
- `Unit` carries no pod/scenario series accessor: S1b's runner builds the
  series (`get_scenario`/`make_variant` for syn/leak, `load_flat_series` +
  `real_slice` for real) from `Unit.kind/scenario/seed` + `rc_cfg` per the
  card P4; the 4 continuous entries are `matrix.continuous_metrics`.
- Slice order is `cfg.slice_names` (L0..L7); `slice_units` re-derives the
  matrix each call — S1b should call `expand_units` once and group.

---

## S1b — `infer.py`, `runner.py`, `run_refcompare.py`

### Files owned by S1b

- `src/refstudy/refcompare/infer.py` (110 lines)
- `src/refstudy/refcompare/runner.py` (896 lines)
- `scripts/run_refcompare.py` (204 lines)
- `tests/test_refcompare_infer.py` (191 lines, 10 tests)
- `tests/test_refcompare_runner.py` (638 lines, 21 tests)

### 1.2 behaviour

**`infer.py` — batched forecast plumbing**

- `forecast_contexts(forecaster, contexts, horizon, batch)`: chunks the
  contexts so each chunk is a set of cycles of ONE unit (a shape change or
  `len(chunk) >= batch` starts a new chunk; a multi chunk of B cycles is B
  items of `(4, N)`, a uni chunk is 4B items of `(N,)` — never mixes V/N);
  sets `forecaster.config.per_core_batch_size = len(chunk)` per chunk; one
  `predict_batch(items, horizon, return_quantiles=True)` call per chunk;
  returns the float32 quantile arrays in input order (`(H, 9)` uni /
  `(V, H, 9)` multi).
- `batch_parity(forecaster, contexts, horizon, B)`: `max(|a-b|/|b|)` over the
  B=1 vs B=B legs (absolute diff where `|b| == 0`); `B < 1` raises;
  `B == 1` returns 0.0.  Drives the L0 probe.

**`runner.py` — resumable slice runner (contract in the module docstring)**

- `build_unit(u, ...)`: the 4 continuous entries of `Scenario.chain_raw()`
  (syn; leak names resolved through C1 `make_variant`, `None` when
  `keep == "none"`, must be in `VARIANT_KEEPS` else `ValueError`); real via
  packaged flat load + C1 `real_slice` + `to_grid` (operator D8).  Shared
  first cycle `n0 = 588` for EVERY context (C1 D-6, not per-unit
  `min_first_n0(ctx_pts)`) ⇒ `plan_cycles(origin, n_ticks, T, dt, 588)`;
  syn/leak = 215 cycles, real `b4xkt` = 190 (= `cfg.matrix.real.cycles_exact`).
- `run_slice(cfg, slice_name, forecaster_call, ...) -> int`:
  - **resume**: a unit's complete cycles come from the shard's digested rows
    (C1 `cycles_done`); only `[done, planned)` are forecast; a fully-complete
    unit logs `"<uid>: 0 cycles to run (N cycles already complete)"` and is
    not re-forecast;
  - **shard write**: `_write_shard` reassembles the stored float32 rows
    (uni rows arrive 4-per-cycle, multi one `(4, H, 9)`-per-cycle, both to
    `q[cycles, 4, H, 9]` float32), stores the C1 `digest` of each row and the
    CONTEXT digests in the shard `meta` (card P4), and re-writes atomically
    (C1 `write_shard_atomic`) — so a rerun reproduces the shard of an
    uninterrupted run bit-for-bit;
  - **hygiene** (B1 gate, `compute.hygiene.snapshot/check`): runs before the
    first unit and, with `hygiene.per_unit`, before every unit; a persisted
    violation aborts with **2**, an `ac:`-prefixed violation (AC-enforcing
    profiles) with **3**; the smoke run skips the gate (`profile=None`
    allowed iff `smoke=True`);
  - **L0 slice** = the hygiene gate + the batch-parity probe on
    `syn:S1:1:240:multi` (first 16 planned cycles); records
    `decisions.probe` and `decisions.batch_cycles_effective` (1 if parity
    max-rel > `inference.batch_parity.rtol` else `inference.batch_cycles`),
    no shard; later slices read it via `_batch_effective(doc, cfg)`;
  - **deadline**: at a chunk boundary, if `clock() >= deadline`, the running
    chunk's completed cycles are flushed (only if `c > done`), the unit is
    recorded `deadline`, later units `deadline` ("not started (slice deadline
    reached in an earlier unit)"), and `run_slice` returns **5** (resumable);
  - **error**: an unknown per-unit exception is recorded `error` and the slice
    continues with the next unit; build errors the same.
- `smoke_units(cfg)`: one unit per kind — `syn S1:1:240:multi`,
  `syn S1:1:240:uni`, `leak S4@cpu:1:240:multi`, `real b4xkt:-:240:multi` —
  capped at `smoke.max_cycles` (3).
- `verify_store(cfg, out_dir)`: checks the 118 MATRIX units against the
  manifest (the manifest's own `cycles_planned` per entry); missing entries
  are "missing manifest entry" problems, a `deadline` entry's partial shard
  must have exactly the recorded cycles + matching sha, other statuses must
  match the shard.  Returns `units`, `ok`, `all_ok`, `problems`.

**`run_refcompare.py` — live-batch / local CLI**

- Args: `--config --device cpu|mps|mlx|cuda --slice L0..L7 --smoke
  --dry-run --verify-store --max-minutes N --out-dir D`.
- **Refusal (exit 4)** per the rule of `scripts/run_scaling.py`: any
  `--device mps|mlx|cuda` or any non-smoke run without `REFM_LIVE=1`;
  `--dry-run` / `--verify-store` / `--device cpu --smoke` are always allowed.
- The run YAML is NOT the refcompare config: load it via
  `load_yaml(run_yaml)["refcompare_config"]` → `load_refcompare_config(...)`,
  then `load_run_config(args.config, ref_cfg, rc_cfg)`.
- The forecaster is loaded once per process in `forecaster_call`
  (`configure_hf_home` + `load_device(settings, device,
  shared.devices[device])`; `shared = load_shared(cfg.shared)`); the runner
  itself never loads weights.
- `--dry-run` prints the unit/call/wall table via loguru (no model).
- `--verify-store` runs no model; exit 0 iff `all_ok` else 1.
- `--out-dir D` redirects the whole run: manifest `D/c2-run-manifest.json`
  + shards `D/shards/*.npz` (shard name = `unit_id` with `:`→`_` + `.npz`).

### Tests (stub forecaster)

31 new deterministic seeded tests (10 in `test_refcompare_infer.py`, 21 in
`test_refcompare_runner.py`).  A stub forecaster (a seeded linear ramp per
variade, `nan_to_num(nan=0.0)`) keeps the grid leading-NaN/real-data
deterministic + finite.  Key assertions:

- chunking keeps cycles-of-one-unit and never mixes V/N; `per_core_batch_size`
  set per chunk; output order + shapes preserved;
- `batch_parity` B=1 == B=B ⇒ 0.0; `B < 1` raises;
- L0 probe writes `decisions.batch_cycles_effective`; later slices read it;
- **resume**: an uninterrupted run and a run that was interrupted mid-unit
  (then re-run) produce **byte-identical** shards and equal manifest
  `shard_sha256`; the re-run forecasts only the missing cycles (A forecasts 21
  items; B first `state == [(2, (4, 240))]`, B re-run forecasts 19);
- crash-in-writer (monkeypatch `write_shard_atomic` to raise): one chunk per
  unit is recorded, no partial `.npz`/`.tmp.npz` on disk, rc 1; a later
  `run_slice` after the patch is undone succeeds;
- shard digests: `meta.context_digest[c][v] == digest(context(...))` (card P4)
  and `digest[c][v] == digest(q[c][v])` (the stored float32 row);
- deadline (scripted `FakeClock` hitting 2400 s after chunk 1): the unit is
  recorded `deadline`, later units `deadline`, rc 5;
- hygiene abort → rc 2, AC-lost → rc 3; `verify_store` ok=2 after a smoke run
  (only the two tier-B `syn S1:1:240` units are matrix units; the 116 others
  are "missing manifest entry"), a corrupted shard byte is caught by
  sha256, a cycle-count mismatch is named;
- CLI subprocess tests run the real script (`.venv/bin/python
  scripts/run_refcompare.py …`, cwd = study dir, `REFM_LIVE` removed from env):
  `--device cuda` refused → 4, non-smoke without `REFM_LIVE` → 4, `--dry-run`
  prints the card table, `--verify-store` without a manifest → 1.

### Checks

```
$ .venv/bin/python -m pytest tests/test_refcompare_*.py -q
(rc 0; 130 passed, 0 failed, 0 skipped — all 12 test_refcompare_*.py files:
 config 22, cycles 7, grid 9, handoff 10, infer 10, pipeline 6, provider 12,
 run_config 10, runner 21, store 7, units 9, variants 7; the new files
 contribute 10 + 21 = 31 tests, 99 (S1a) + 31 = 130)

$ .venv/bin/ruff check src/refstudy/refcompare/infer.py \
    src/refstudy/refcompare/runner.py scripts/run_refcompare.py \
    tests/test_refcompare_infer.py tests/test_refcompare_runner.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare
(empty, rc 1)

$ git diff --check
(clean)

$ git check-ignore -v artifacts/refcompare/x.npz
.gitignore:44:reference-model-study/artifacts/*   (acceptance: shards are
  under artifacts/, git-ignored; the non-commercial TimesFM weights are never
  committed)

$ .venv/bin/python scripts/run_refcompare.py --config config/refcompare_run.yaml \
    --dry-run   (no model; printed table equals the S1a / card numbers)
118 units;  (4,11520) 9,425/9,435 · (1,11520) 30,820/30,860
V=4 TOTAL 13,295/13,305 · V=1 TOTAL 46,300/46,340 · ALL TOTAL 59,595/59,645
every slice ≤ 40 min (L0 0 · L1 36.5 · L2 33.9 · L3/L4/L5 34.6 · L6 30.5 ·
L7 34.0)
```

Note: `pytest -q` on this box prints only the progress bar + rc 0 (no final
"130 passed" line); the pass/skip counts are counted from `--collect-only -q`
(130 ids) + the zero-failure rc, matching S1a's convention.

### Commit

`1863de3 feat(refstudy): add Phase C resumable inference runner and live-batch CLI (C2 slice 1b)`
(5 files: `infer.py`, `runner.py`, `run_refcompare.py`, `test_refcompare_infer.py`,
`test_refcompare_runner.py`; explicit `git add` of the 5 paths only; a sibling
B2-fix-C edit to `scripts/plot_refresh.py` was in flight in the worktree and was
NOT staged/committed.)

---

## Stage 2 — CPU smoke (real TimesFM-3 weights, local, no live batch)

D17: the SUPERVISOR runs the live GPU batches; this stage only proves the
runner end-to-end on the local CPU with the real weights, in `throwaway/`
(git-ignored), well under the 5-min budget.

### 1. First run (4 smoke units, 3 cycles each)

```
$ .venv/bin/python scripts/run_refcompare.py --config config/refcompare_run.yaml \
      --device cpu --smoke --out-dir throwaway/c2-smoke
(rc 0; total wall ≈ 7 s)
TimesFM-3 loaded on cpu in 1.5 s          (weights from artifacts/timesfm3)

manifest (c2-run-manifest.json) — all 4 units `ok`, 3 cycles, batch_eff=8:
  syn:S1:1:240:multi    wall_s 0.227  ms/cycle 75.57
  syn:S1:1:240:uni      wall_s 0.222  ms/cycle 74.11
  leak:S4@cpu:1:240:multi wall_s 0.223 ms/cycle 74.26
  real:b4xkt:-:240:multi  wall_s 0.224  ms/cycle 74.66
  slice: status ok · device cpu · n_units 4 · wall_s 2.503 · batch_effective 8
```

### 2. Shards read back with C1 `read_shard`

All 4 shards: `q (3, 4, 260, 9) float32`, `digest (3, 4, 3)`, meta
`kind=1 version=1 mode∈{multi,uni} ctx_pts=240 n_cycles_planned=3`,
`meta.context_digest` present (3×4×3), all `q` values finite.  (H = 260 =
240 context + 20 horizon, per the card's expected `(3, 4, 260, 9)`.)

### 3. Resume proof (same command, second run)

```
$ .venv/bin/python scripts/run_refcompare.py --config config/refcompare_run.yaml \
      --device cpu --smoke --out-dir throwaway/c2-smoke
(rc 0)
  syn:S1:1:240:multi: 0 cycles to run (3 cycles already complete)
  syn:S1:1:240:uni:   0 cycles to run (3 cycles already complete)
  leak:S4@cpu:1:240:multi: 0 cycles to run (3 cycles already complete)
  real:b4xkt:-:240:multi:  0 cycles to run (3 cycles already complete)
```

All 4 shards are **byte-identical** (sha256 before == after the re-run) — a
rerun recomputes nothing and reproduces the shard of the uninterrupted run.

### 4. Dry-run table check

`--dry-run` (no model) prints the card's table exactly: 118 units,
59,595 exact / 59,645 upper calls, V=4 13,305 / V=1 46,340,
(4,11520) 9,435 / (1,11520) 30,860, every slice ≤ 40 min — matching S1a's
`call_table`.

### Commit

No commit 2: the Stage 2 smoke ran clean on the first attempt, no
code/doc adjustments were forced (the planned
`chore(refstudy): add Phase C runner smoke checks` commit is not needed).
