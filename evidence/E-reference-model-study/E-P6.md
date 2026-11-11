# E-P6 — SOLO-REFM P6 executor evidence (SQLite-only retention + per-metric scored-tick durability)

Repo `/Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector`, branch `feature/cnn2dlstm-bayesian-statistical-detector-v2`.
Env: `cd analyser`, `PY=/tmp/solo-p3-venv/bin/python`, `PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared`.

## S1 — required `persistence.retention` block + load-time validation (commit 1)

Commit: `43b31b46b93e80422eb15167671c06681c2bc9b3`
`feat(solo): required persistence.retention config with load-time TTL validation (SOLO-OPS P6-S1)`
HEAD before: `5bcc7f9` · 5 files, 282 insertions, 0 deletions. No push, local only.

### Baseline (pre-edit, HEAD 5bcc7f9)

```
$ PY -m pytest tests/unit/test_solo_state.py tests/unit/test_solo_window_store.py tests/unit/test_solo_mode_config.py -q -x
→ 170 passed in 4.87s · EXIT=0
```

### Post-edit

```
$ PY -m pytest tests/unit/test_solo_mode_config.py -q
→ 142 passed in 3.29s · EXIT=0   (was 97 before S1; +45 new P6 tests)

$ PY -m pytest tests/unit/test_solo_state.py tests/unit/test_solo_window_store.py tests/unit/test_solo_mode_config.py -q
→ 215 passed in 3.94s · EXIT=0   (170 baseline + 45 new, all green)
```

New tests in `test_solo_mode_config.py` (all 45 pass):
- `test_p6_retention_block_missing_rejected` (block delete ⇒ match `retention`);
- `test_p6_retention_each_key_required` parametrized over all 7 keys (delete ⇒ `ConfigurationError` match `<key>`);
- `test_p6_retention_non_mapping_rejected`;
- `test_p6_retention_bad_duration` × 4 duration keys × {`0`, `"7w"`, `7`, `True`, `"0d"`} (20);
- `test_p6_retention_bad_safety_factor` × {`1.0`, `True`, `"2.5"`};
- `test_p6_retention_bad_positive_int` × 2 keys × {`0`, `-1`, `True`, `1.5`};
- `test_p6_retention_unknown_key_rejected` (`raw_points_ttl_typo` named in message);
- boundaries: `raw_points_ttl` `"540750s"` passes / `"540749s"` rejected (message contains `540750`); `scored_ticks_ttl` `"172800s"` passes / `"172799s"` rejected; with `scored_tick_history.depth "2d"` floor `345600s` passes / `345599s` rejected; `sweep_interval` `"299s"` rejected, `"300s"` (= tick) passes, `"8d"` (> min TTL) rejected;
- `test_p6_shipped_configmap_retention_matches_dev`: repo ConfigMap's embedded `detector-common.yaml` parses, `validate_solo_mode_config` passes on its `solo_mode` block, and its `persistence.retention` equals `DEV_COMMON_YAML`'s and the 7 literal shipped values (`7d`/`7d`/`12h`/`2.5`/`1h`/`2000`/`10`).

### Other unit tests that build a solo config from detector-common.yaml / the ConfigMap

```
$ grep -rn "detector-common\|solo-card6" tests/unit
→ consumers: test_split_config_loader.py, test_solo_driver.py, test_solo_exporter.py,
   test_solo_scan.py, test_solo_diagnostics.py, test_solo_scenarios.py (+ dashboard/exporter
   subprocess helpers; test_solo_dashboard_routes.py NOT run per card)
```

```
$ PY -m pytest tests/unit/test_split_config_loader.py tests/unit/test_solo_exporter.py tests/unit/test_solo_scan.py tests/unit/test_solo_diagnostics.py -q
→ 23 failed, 86 passed in 27.55s · EXIT=0
→ identical result on the PRE-EDIT tree (git stash: same 23 failed, 86 passed) —
  all 23 are pre-existing `ModuleNotFoundError: No module named 'termcolor'` in a
  subprocess helper (helper runs system python3.10, not the P3 venv). NOT caused by S1.

$ PY -m pytest tests/unit/test_solo_driver.py -q
→ 12 failed, 40 passed in 79.18s
→ identical on the PRE-EDIT tree (git stash: same 12 failed, 40 passed, same test names) —
  pre-existing `ModuleNotFoundError: No module named 'sklearn'` (×11) / `'pytz'` (×1),
  not installed in the P3 venv. NOT caused by S1.

$ PY -m pytest tests/unit/test_solo_scenarios.py -q
→ collection ERROR `ModuleNotFoundError: No module named 'pytz'` (pre-existing, same module).
```

Cross-check: dev `detector-common.yaml` solo block with `enabled=true` passes the real
`load_split_config` + `validate_split_config` end-to-end (scratch, exit 0). Shipped cross-rule
messages verified verbatim:
- `raw_points_ttl` 540749s → `'solo_mode.persistence.retention.raw_points_ttl' (540749s) must be >= safety_factor * (window.Dt + lookback_margin + tick_seconds): 2.5 * (172800s + 43200s + 300s) = 540750s.`
- `scored_ticks_ttl` 172799s → `... (172799s) must be >= 2 * ring_ticks * tick_seconds (172800s): 2 * 288 * 300s, where ring_ticks = max(1, scored_tick_history.depth // tick_seconds).`
- `sweep_interval` 299s / 8d → `... must satisfy tick_seconds (300s) <= sweep_interval <= min(raw_points_ttl, scored_ticks_ttl) (604800s).`

### Pre-commit checks

```
$ git diff --check            # clean (exit 0, no output)
$ git diff --stat -- <the 5 slice files>
 analyser/config/detector-common.yaml           |  24 ++++
 analyser/solo_mode/config.py                   |  76 ++++++++++++
 analyser/tests/unit/test_solo_mode_config.py   | 155 +++++++++++++++++++++++++
 deploy/k8s/solo-card6/configmap.yaml           |  25 ++++
 markdown/2026-10-09-solo-mode-config-schema.md |   2 +
 5 files changed, 282 insertions(+)
$ git add <the 5 slice files> && git commit -m "feat(solo): required persistence.retention config with load-time TTL validation (SOLO-OPS P6-S1)"
[feature/cnn2dlstm-bayesian-statistical-detector-v2 43b31b4] 5 files changed, 282 insertions(+)
$ git show --stat HEAD   # commit = exactly the 5 files (282 insertions, 0 deletions)
```

Unrelated tree state (` M AGENTS.md`, untracked `analyser/agent-orchestration/`,
`markdown/2026-11-06-solo-dashboard-operations-report.md`) NOT staged. No push, no trailers.

### Parity consequence (per master card)

P6 touched 3 of 9 pinned `used_files`: `solo_mode/config.py` (this commit), `driver.py` and
`deploy/k8s/solo-card6/configmap.yaml` (later slices). The lab parity suite is red-by-design
until P6-repin; the lab also transcribes `driver.py:1486-1605` — S1 inserts no driver lines,
but the config.py/configmap.yaml blob ids change here and P6-repin must re-record them.

## Environment correction (S, 2026-11-11, after S1)
The S1 executor found 12 `test_solo_driver.py` failures identical on the pre-edit tree: the scratch venv `/tmp/solo-p3-venv` lacked `pytz`, `termcolor`, `scikit-learn` (declared dependencies of `shared`/analyser, not P6 defects). S installed them into the scratch venv only (`uv pip install --python /tmp/solo-p3-venv/bin/python pytz termcolor scikit-learn`; no repo change). **New baseline after S1 = 267 passed** (`test_solo_driver.py` 52 + the three baseline suites 215), `0 failed`, 81.7 s. Later slices compare against this number.

## S2 — `solo_scored_ticks` table + writer on BOTH tick paths (commit 2)

Commit: `52197c3919d7776324476c4983ca2729797b8ab5`
`feat(solo): per-metric solo_scored_ticks written on scored and skipped ticks (SOLO-OPS P6-S2)`
HEAD before: `43b31b4` · 4 files, 721 insertions, 23 deletions. No push, local only.

### Production code

- **`state.py`**:
  - `Sequence` added to the `typing` import.
  - Module constant `_SCORED_TICKS_DDL` — exact D4 DDL, `WITHOUT ROWID`,
    no secondary index; comment states `p_raw` is the per-metric `m["p"]`
    (not the pod-level `p_raw`) and `gate_fired` is the no-fresh-model gate
    (unrelated to `solo_pod_scored_history.gate_pass`).
  - Module constant `_METRIC_TICK_UPSERT` — `INSERT … ON CONFLICT
    (pod_key, metric_name, tick_epoch) DO UPDATE` over all 5 non-key columns.
  - Module-level pure function `metric_tick_rows(metrics, model_t0,
    tick_epoch)` (D1-D3): returns one `(name, p_raw, ess, gate_fired,
    stale_hours, provenance)` tuple per metric; `gate_fired=1` iff unscored
    AND `reason == "model stale"`; `stale_hours` = `(tick − model_t0[name])/3600`
    when the model age is absent but a persisted t0 exists, else
    `model_age_seconds/3600`, clamped `>= 0`, NULL when no model row.
  - `__init__` last line `self._migrate_scored_ticks()`; new
    `_migrate_scored_ticks()` (existence check; `upgrade` probe on
    `solo_pod_scored_history`; DDL + commit; `logger.warning` when a
    database with history is upgraded, `logger.info` on a fresh one; no
    backfill; DDL is NOT in `_init_schema`).
  - New methods: `get_metric_model_t0s(pod_key)` (PK-prefix SELECT under
    the lock), `read_metric_ticks(pod_key, metric_name, start, end)`
    (`[start, end)`, ordered, 8 column keys, `gate_fired` as bool), private
    `_insert_metric_ticks(pod_key, tick_epoch, metric_ticks)` (executemany
    upsert; caller holds the lock + open transaction; no commit here).
  - `record_skipped_tick`: new required keyword-only `metric_ticks:
    Sequence[tuple]`; wraps the markov write + `_insert_metric_ticks` in a
    `try … except BaseException: self._conn.rollback(); raise` (the rollback
    it previously lacked); docstring notes the rows are atomic with the tick.
  - `complete_scored_tick`: new required keyword-only `metric_ticks:
    Sequence[tuple]`; `_insert_metric_ticks` called after the calibration
    upsert, inside the existing `try` (before the final `commit()`);
    docstring gained step 4 + a paragraph stating the rows are atomic with
    the tick.
- **`driver.py`**: `import metric_tick_rows` (`:113`); ONE
  `metric_ticks = metric_tick_rows(_public_metrics(metrics_out),
  state_store.get_metric_model_t0s(pod_key), tick_end)` line immediately
  after `metrics_out = outcome["metrics"]`; `metric_ticks=metric_ticks,`
  added to the two `record_skipped_tick(` calls and the one
  `complete_scored_tick(` call. No other driver edit (no scoring-math
  hunk).

### Test changes

- **`test_solo_state.py`**: `_base_complete_kwargs` gains
  `metric_ticks=()`; every direct `complete_scored_tick(`/`record_skipped_tick(`
  call that did not use it (10 at HEAD: the skip test, the 4-arg loop,
  depth-requires-positive, same-tick-upsert, drift-flag, drift-default,
  provenance ×3, schema-idempotent) gained `metric_ticks=()`. New P6 tests:
  - (a) `test_p6_metric_tick_rows_scored_and_unscored` — scored+eligible
    (`model:stl_lite`, `stale_hours = age/3600`), scored+ineligible
    (`window fill…` still `model:`), `model stale` + persisted t0
    (`gate_fired 1`, `(tick−t0)/3600`, `none:model stale`),
    `model not built` (`0`, NULL age, `none:model not built`),
    `no window data` with a model (`0`, age from t0), negative age clamps
    to 0.
  - (b) `test_p6_metric_ticks_roundtrip_and_upsert_idempotence` —
    round-trip through both tick paths + `[start, end)` boundary; same key
    twice ⇒ 1 row, updated (no duplicate).
  - (c) `test_p6_metric_ticks_bad_row_rolls_back_whole_tick` — bad row
    (`gate_fired None` ⇒ `IntegrityError`) on `complete_scored_tick`
    leaves `has_scored_tick` False / markov None / 0 metric rows; same on
    `record_skipped_tick` (marker not advanced); connection stays usable
    (next write succeeds).
  - (d) `test_p6_scored_ticks_migration_logs_and_is_idempotent` — file DB
    + `append_scored_tick` → close → `DROP TABLE` (plain `sqlite3`) → reopen
    under `caplog` ⇒ table exists, exactly ONE WARNING containing
    `solo_scored_ticks migration`, 0 rows, `sqlite_master.sql` has
    `WITHOUT ROWID`, ring row survived; re-open ⇒ no new record; fresh DB ⇒
    INFO only, no WARNING.
  - (e) `test_p6_metric_ticks_survive_restart` — 2 pods × 3 metrics, 4
    ticks each spanning 3 d, `close()`, new `SoloStateStore` ⇒
    `read_metric_ticks` equals what was written.
  - (f) `test_p6_scored_ticks_disk_budget_bytes_per_row` — 2 pods × 2016
    ticks × 11 real metric names (85-char pod keys) through
    `complete_scored_tick` (`details={}`, `depth_ticks=10`) on a file DB;
    `PRAGMA page_count × page_size / 44,352` rows.
- **`test_solo_driver.py`** (pattern of `test_solo_throughput.py`;
  `_seeded`/`_drive`/`_rc`): ticks 1-2 are the "no eligible metric" skip,
  tick 3 is scored.
  - (g) `test_p6_metric_rows_on_skipped_and_scored_ticks` — 3 ticks from
    `t0` ⇒ 33 rows; cpu `p_raw`/`ess` not NULL, `gate_fired 0`,
    `provenance` starts `model:`, `stale_hours == (tick−t0)/3600`; the other
    10 `p_raw`/`ess`/`stale` NULL, `gate_fired 0`, `none:model not built`;
    skip-path (ticks 1-2) and scored-path (tick 3) rows both present.
  - (h) `test_p6_metric_rows_on_gated_mandatory_skip` —
    `_drive(rt, t0 + dt + T)` (cpu model aged out ⇒ mandatory skip) ⇒ cpu
    row `gate_fired 1`, `none:model stale`, `p_raw`/`ess` NULL,
    `stale_hours == (dt+T)/3600`; the other 10 still `none:model not
    built`.
  - (i) `test_p6_metric_rows_survive_restart` — after (g)
    `drv._reset_solo_runtime_for_tests()` then a fresh `SoloStateStore(db)`
    ⇒ the same 33 rows (file DB).

### Test results

Baseline before S2 = **267 passed** (`test_solo_driver.py` 52 + the three
baseline suites 215), `0 failed` (env correction above).

```
# three baseline suites (test_solo_state.py 38->44 = +6 new P6 tests)
$ PY -m pytest tests/unit/test_solo_state.py tests/unit/test_solo_window_store.py tests/unit/test_solo_mode_config.py -q
→ 221 passed in 5.01s · EXIT=0   (215 baseline + 6 new, all green)

# full driver suite (52 -> 55 = +3 new P6 driver tests g/h/i)
$ PY -m pytest tests/unit/test_solo_driver.py -q
→ 55 passed in 81.42s · EXIT=0   (52 baseline + 3 new, all green)

TOTAL after S2 = 276 passed (267 baseline + 9 new: 6 state + 3 driver), 0 failed.
```

Targeted run of the three new P6 driver tests alone: `3 passed in 1.82s`.
Targeted run of `test_solo_state.py`: `44 passed in 1.89s`.

### Insert-cost (scratch `/tmp/solo-p6-e/insert_cost.py`, NOT committed)

Method of `/tmp/solo-p6-plan/wr_cost.py`, but the target is the REAL
`SoloStateStore.complete_scored_tick` (one scored-tick commit: markov +
ring + calibration) with `metric_ticks=()` vs 11 real metric rows, in the
tick's existing transaction. Preload: 10 pods × 2016 and 1000 pods × 60
ticks; 3 reps, medians.

```
10 pods x 2016 preloaded ticks (221,760 metric rows; preload 6816 ms):
  tick txn WITH 11 metric rows median 0.215 ms (max 0.34 ms)
  vs WITHOUT 0.056 ms  =>  ADDED 0.158 ms/pod-tick
1000 pods x 60 preloaded ticks (660,000 metric rows; preload 19278 ms):
  tick txn WITH 11 metric rows median 0.229 ms (max 500.06 ms)
  vs WITHOUT 0.060 ms  =>  ADDED 0.169 ms/pod-tick
bounds: 10-pod added 0.158 ms (<= 1.0 ms OK),
        1000-pod added 0.169 ms (<= 1.0 ms OK),
        ratio 1.07 (<= 3.0 OK)
```

Card bound ≤ 1.0 ms/pod-tick at both sizes and 1000-pod ≤ 3× the 10-pod
figure — MET (0.158 / 0.169 ms; ratio 1.07). (Master-card scratch M3
reference: +0.111 ms / +0.115 ms; this re-measurement on the real
`complete_scored_tick` path is marginally higher because the "without" arm
still does the full markov + ring + calibration transaction.)

### Disk budget (test f)

```
p6-disk: 44352 rows, page_size=4096, page_count=2245, 207.3 B/row (bound 260)
```

207.3 B/row ≤ 260 (WITHOUT ROWID; a rowid table measured 358 B/row on the
same shape). Pass.

### Pre-commit checks

```
$ git diff --check            # clean (exit 0, no output)
$ git diff --stat -- <the 4 slice files>
 analyser/solo_mode/driver.py            |  11 +-
 analyser/solo_mode/state.py             | 238 +++++++++++++++++++--
 analyser/tests/unit/test_solo_driver.py | 134 ++++++++++++
 analyser/tests/unit/test_solo_state.py  | 361 ++++++++++++++++++++++++++++++++
 4 files changed, 721 insertions(+), 23 deletions(-)
$ git add <the 4 slice files> && git commit -m "feat(solo): per-metric solo_scored_ticks written on scored and skipped ticks (SOLO-OPS P6-S2)"
[feature/cnn2dlstm-bayesian-statistical-detector-v2 52197c3] 4 files changed, 721 insertions(+), 23 deletions(-)
```

Unrelated tree state (` M AGENTS.md`, untracked `analyser/agent-orchestration/`,
`markdown/2026-11-06-solo-dashboard-operations-report.md`) NOT staged. No push, no trailers.

### `driver.py` hunk summary since the P6 base (5bcc7f9)

```
$ git diff 5bcc7f9..HEAD -- analyser/solo_mode/driver.py
@@ -110,7  +110,7 @@  import: from solo_mode.state import SoloStateStore, metric_tick_rows
@@ -1488,6 +1488,12 @@ handle_solo_request: metric_ticks = metric_tick_rows(...) after metrics_out
@@ -1516,6 +1522,7  @@ handle_solo_request: metric_ticks=metric_ticks, (first record_skipped_tick)
@@ -1543,6 +1550,7  @@ handle_solo_request: metric_ticks=metric_ticks, (second record_skipped_tick)
@@ -1922,6 +1930,7  @@ handle_solo_request: metric_ticks=metric_ticks, (complete_scored_tick)
 analyser/solo_mode/driver.py | 11 ++++++++++- (10 insertions, 1 deletion)
```

Exactly the 5 permitted hunks: the import line, the `metric_ticks = …`
line, and the three `metric_ticks=` kwargs. No scoring-math hunk.

### Parity consequence (per master card)

`driver.py` is now one of the P6-touched pinned `used_files` (alongside
`config.py` from S1; `configmap.yaml` from S1). Its blob id changes here;
the lab transcribes `driver.py:1486-1605` (this slice inserts lines inside
that range — persistence only, no scoring math). P6-repin must re-record
the `driver.py` blob id and refresh the line-range comments. Parity
stays red-by-design until P6-repin.

## S3 — batched TTL sweep primitives + policy (commit 3)

Commit: `a29efbfdb5e4eb8ab0a7e7ef6258bd883b002f91`
`feat(solo): batched TTL sweep primitives and retention policy (SOLO-OPS P6-S3)`
HEAD before: `52197c3` · 5 files, 756 insertions, 2 deletions. No push, local only.
`retention.py` and `test_solo_retention.py` are NEW files; the other three
are edited. `scan.py` and `driver.py` are UNTOUCHED by this slice
(`git diff 52197c3..HEAD -- analyser/solo_mode/scan.py analyser/solo_mode/driver.py` is EMPTY).

### Production code

- **`window_store.py`**: `import time` added; module-level
  `_SWEEPABLE = {"solo_window_points": "ts_epoch", "solo_scored_ticks":
  "tick_epoch"}` and `sweep_expired_rows(lock, conn, table, cutoff_epoch,
  batch_rows, pause_s, sleep=time.sleep) -> int` — the batched per-stream
  TTL delete (index seeks only, no table scan, no long lock; the lock is
  held per statement only, NEVER across `sleep`; a `pause_s` sleep happens
  after every non-empty batch so a waiting writer can commit). Unknown
  table ⇒ `ValueError`. `SoloWindowStore.sweep_expired(...)` is the thin
  wrapper over `solo_window_points`. `_merge_episodes` and `slide_drop`
  are BYTE-IDENTICAL (untouched).
- **`state.py`**: `import time` added; `from solo_mode.window_store import
  open_solo_connection, resolve_db_path, sweep_expired_rows`; new
  `SoloStateStore.sweep_expired_scored_ticks(...)` = the same primitive on
  `solo_scored_ticks`. No other state edit.
- **`retention.py` (NEW)**: module docstring (SOLO-OPS P6); the frozen
  dataclass `RetentionPolicy(raw_points_ttl_s, scored_ticks_ttl_s,
  sweep_interval_s, batch_rows, batch_pause_s)`; `retention_policy(solo_cfg)`
  re-parses the validated `persistence.retention` block via a LAZY
  `from solo_mode.config import _parse_duration_seconds` (no import cycle;
  a missing key is a `KeyError`, no default); `next_sweep_epoch(now, T,
  interval)` returns the next MID-TICK sweep wake-time
  (`k*T + T/2` where `k = ceil((now + interval)/T)`, always
  `>= now + interval`); `sweep_once(stores, policy, now, *, sleep)` deletes
  the expired rows from BOTH tables in one pass, each in its OWN
  `try/except` (one table's exception is `logger.exception`'d and does NOT
  skip the other; the first exception is re-raised AFTER both ran; returns
  `{"raw_points": n, "scored_ticks": m}`).

> NOTE on `next_sweep_epoch`: the S3 card's item-3 formula
> (`k = ceil((now + interval − half)/T); return k*T + half`) as literally
> written yields `1_003_650.0` for the card's own test value
> `next_sweep_epoch(1_000_000.0, 300, 3600)`, but the card's test (f)
> asserts `== 1_003_950.0` (which is `k = ceil((now + interval)/T)`). The
> implemented function matches the AUTHORITATIVE test value
> `1_003_950.0` and satisfies the 200-random-now property
> (`result >= now + interval` AND `result % 300 == 150`). This is a
> mid-tick scheduling detail that does NOT affect any P6 correctness
> property (the sweep still wakes mid-tick, one full interval out).

### Test changes

- **`test_solo_window_store.py`** (5 new tests, 35 → 40):
  - (a) `test_p6_sweep_only_rows_below_cutoff` — stream A 5 expired + 5
    live, B all live, C all expired; a row at EXACTLY the cutoff survives
    (strict `<`); other streams untouched; returned count exact; second
    run deletes 0; no `sleep` call when nothing expired.
  - (b) `test_p6_sweep_batch_boundaries_and_pause_count` — `batch_rows=3`
    with expired counts 0,1,2,3,4,6,7 in separate streams: all gone, the
    recorder sees exactly `ceil(n/3)` sleeps per stream.
  - (c) `test_p6_sweep_lock_free_during_pause` — from inside the `sleep`
    callback: (i) a second thread's `window.count(...)` `join(1.0)`
    finishes (the lock is free), (ii) a second `sqlite3.connect(db,
    timeout=0.2)` inserts a row successfully.
  - (d) `test_p6_sweep_unknown_table_rejected` — unknown table ⇒
    `ValueError` (two table names).
  - (e) `test_p6_sweep_scored_ticks_same_cases` — the same cases on
    `solo_scored_ticks` through `SoloStateStore.sweep_expired_scored_ticks`
    (exact boundary, count, second-run 0).
- **`test_solo_retention.py` (NEW, 7 tests)**:
  - (f) `test_retention_policy_from_dev_config` — dev `detector-common.yaml`
    yields the exact 7-value policy; missing `raw_points_ttl` /
    `sweep_batch_pause_ms` ⇒ `KeyError` (no default).
  - (f) `test_next_sweep_epoch_exact_and_property` —
    `next_sweep_epoch(1_000_000.0, 300, 3600) == 1_003_950.0`; 200 random
    nows: `result >= now + interval` AND `result % 300 == 150` (mid-tick).
  - (g) `test_sweep_once_exact_ttl_boundary_both_tables` — rows at
    `now − 7d` KEPT, `now − 7d − 1` DELETED, both tables, counts exact.
  - (g) `test_sweep_once_isolates_per_table_failure` — the raw sweep is
    patched to raise ⇒ the scored sweep STILL ran (its expired rows
    deleted, connection usable), and the exception propagated.
  - (g) `test_sweep_once_isolates_scored_table_failure` — mirror: the
    scored sweep raises ⇒ the raw sweep STILL ran, exception propagated.
  - (h) `test_sweep_concurrent_writer_latency_bound` — the concurrency
    bound (see numbers below).
  - (i) `test_restart_then_sweep_deletes_only_expired` — rows written,
    stores closed + reopened, `sweep_once` ⇒ only expired rows gone.

### Test results

Baseline before S3 = **276 passed** (`test_solo_driver.py` 55 + the three
baseline suites 221), `0 failed` (S2).

```
# the four baseline + new suites (test_solo_window_store.py 35 -> 40 = +5 new P6;
# test_solo_retention.py NEW = 7; test_solo_state.py 44 unchanged; test_solo_mode_config.py 142 unchanged)
$ PY -m pytest tests/unit/test_solo_state.py tests/unit/test_solo_window_store.py tests/unit/test_solo_mode_config.py tests/unit/test_solo_retention.py -q
→ 233 passed in 11.17s · EXIT=0   (221 baseline + 12 new: 5 window + 7 retention, all green)

# driver suite (UNTOUCHED by this slice, run once at the end per the card)
$ PY -m pytest tests/unit/test_solo_driver.py -q
→ 55 passed in 51.37s · EXIT=0   (unchanged; 0 new)

TOTAL after S3 = 288 passed (276 baseline + 12 new: 5 window + 7 retention), 0 failed.
```

### Concurrency bound (h) — numbers

`test_sweep_concurrent_writer_latency_bound`: window + state stores on ONE
file DB; **150 k expired rows on EACH table** (30 streams × 5,000, direct
`executemany`) + 30 live raw points; a writer thread commits an 11-row
`complete_scored_tick` every ~20 ms (the REAL `complete_scored_tick` path,
8 rotating pods, ticks at 902,000+) recording the wall latency of each
commit while `sweep_once` runs with the DEV policy (`batch_rows=2000`,
`pause=10 ms`). Bound: max write latency `< 0.5 s`, `>= 5` writes completed,
exact deleted count, no `OperationalError`.

```
p6-conc: max 7.3 ms, p99 5.2 ms, median 0.5 ms, writes 247,
        deleted 300000 rows (150000 window + 150000 scored)
```

max 7.3 ms `<< 0.5 s` (the card's reference measurement was 7 ms at 1.17 M
rows with a no-pause control of 194 ms; here the pause is 10 ms and the
write latencies stay in the low single-digit ms range). 247 writes
`>= 5`. Deleted count is EXACT (150,000 + 150,000; every live + writer
row at the cutoff or newer survives; 0 rows remain below the cutoff on
either table). PASS.

### Pre-commit checks

```
$ git diff --check            # clean (exit 0, no output)
$ git add <the 5 slice files>   # retention.py + test_solo_retention.py are NEW
$ git diff --cached --stat
 analyser/solo_mode/retention.py               | 123 ++++++++
 analyser/solo_mode/state.py                   |  15 +-
 analyser/solo_mode/window_store.py            |  54 ++++
 analyser/tests/unit/test_solo_retention.py    | 390 ++++++++++++++++++++++++++
 analyser/tests/unit/test_solo_window_store.py | 176 +++++++++++-
 5 files changed, 756 insertions(+), 2 deletions(-)
$ git commit -m "feat(solo): batched TTL sweep primitives and retention policy (SOLO-OPS P6-S3)"
[feature/cnn2dlstm-bayesian-statistical-detector-v2 a29efbf] 5 files changed, 756 insertions(+), 2 deletions(-)
$ git rev-parse HEAD
a29efbfdb5e4eb8ab0a7e7ef6258bd883b002f91
$ git diff 52197c3..HEAD -- analyser/solo_mode/scan.py analyser/solo_mode/driver.py
(empty — scan.py and driver.py are UNTOUCHED by this slice)
```

Unrelated tree state (` M AGENTS.md`, untracked `analyser/agent-orchestration/`,
`markdown/2026-11-06-solo-dashboard-operations-report.md`) NOT staged. No push, no trailers.

### Parity consequence (per master card)

NONE of S3's 5 files (`window_store.py`, `state.py`, NEW `retention.py`,
`test_solo_window_store.py`, NEW `test_solo_retention.py`) is in the 9
pinned `used_files` (noise.py, baseline.py, scan.py, fusion.py,
driver.py, config.py, shared/bayesian/short_term.py,
shared/bayesian/common.py, configmap.yaml) — so NO pinned blob id changes
here and P6-repin re-records nothing for S3. `driver.py` and `scan.py`
remain byte-identical to the P6 base (`5bcc7f9`) — P6-repin's
`git diff 5bcc7f9..HEAD -- analyser/solo_mode/driver.py` check is
UNCHANGED by S3. Parity stays red-by-design until P6-repin.

## S4 — `SoloRetention` thread wiring (commit 4)

Commit: `9266dbf7ad6c174f34113eaf5088de75082fd7bb`
`feat(solo): SoloRetention sweep thread started with the solo runtime (SOLO-OPS P6-S4)`
HEAD before: `a29efbf` · 2 files, 146 insertions, 0 deletions. No push, local only.

### Production code (`driver.py`, `start_solo_runtime` only)

After the `SoloRuntime` thread `.start()` and BEFORE `_STARTED.add`, the
card's block verbatim (all names verified at HEAD — no adaptation
needed): `from solo_mode import retention as _retention`;
`policy = _retention.retention_policy(solo_cfg)`; the nested
`_retention_loop()` (wall-clock `time.time()` now;
`time.sleep(max(0.0, _retention.next_sweep_epoch(now, T,
policy.sweep_interval_s) - now))`; then
`_retention.sweep_once(get_solo_stores(rt_config), policy,
time.time())` with `except Exception: logger.exception("solo retention
sweep failed; retrying next interval.")`);
`threading.Thread(target=_retention_loop, name="SoloRetention",
daemon=True).start()`; plus the one required
`logger.info("solo retention thread started (interval=%ds, batch=%d
rows, pause=%.0f ms).", policy.sweep_interval_s, policy.batch_rows,
policy.batch_pause_s * 1000.0)`. `run_solo_runtime_step` UNCHANGED —
the sweep is never on the tick thread. `_STARTED.add` now happens AFTER
both threads are started.

### Test changes (`test_solo_driver.py`, +2 tests; imports `time` and
`from solo_mode import retention as _retention`)

- **`test_p6_solo_retention_thread_wired_with_runtime`** — monkeypatches
  `drv.threading.Thread` with a recorder (`FakeThread` keeps
  `(target, name, daemon)`; `start()` only records into a shared list,
  NOTHING runs). `drv.start_solo_runtime(rt)` returns `True`; started
  names in order `["SoloRuntime", "SoloRetention"]`; both
  `daemon is True`; the two targets are the driver's `_loop` and
  `_retention_loop` closures; a SECOND call returns `False` and starts
  nothing (record count stays 2). The autouse fixture
  `_clean_solo_runtime` resets `_STARTED` (and the store singletons)
  around every test, so the first call is a genuine start.
- **`test_p6_solo_retention_loop_single_iteration_and_error_isolation`**
  — takes the recorded `SoloRetention` target and drives it for exactly
  the iterations under test: fake `time.sleep` (recorded) returns 0 on
  the first two wakes and raises a private sentinel
  (`_P6BreakLoop`) on the third wake to break the infinite loop;
  `_retention.sweep_once` monkeypatched with a recorder: iteration 2's
  sweep raises `RuntimeError`. Asserts: exactly 3 wakes + 2 sweeps
  (the RAISING sweep was caught, the next wake still happened — the loop
  does not end on failure); iteration 1 got
  `drv.get_solo_stores(rt)` (the runtime's singleton pair, identity),
  the policy `== _retention.retention_policy(cfg)` (parsed from the
  YAML retention block), and a `time.time()`-like now inside
  `[before, after]` of the call; the failing sweep was logged exactly
  once via `logger.exception` on `solo_mode.driver` (ERROR,
  `exc_info` is the RuntimeError with the injected message, message
  starts with `solo retention sweep failed`).

### Test results

Baseline before S4 = **288 passed** (`test_solo_driver.py` 55 + the four
suites below 233), `0 failed` (S3).

```
# targeted: the two new S4 tests alone
$ PY -m pytest tests/unit/test_solo_driver.py -q -k "p6_solo_retention"
→ 2 passed in 0.87s · EXIT=0

# driver suite (55 -> 57 = +2 new S4 tests)
$ PY -m pytest tests/unit/test_solo_driver.py -q
→ 57 passed in 55.89s · EXIT=0

# the other four gate suites (UNTOUCHED by this slice)
$ PY -m pytest tests/unit/test_solo_state.py tests/unit/test_solo_window_store.py \
    tests/unit/test_solo_mode_config.py tests/unit/test_solo_retention.py -q
→ 233 passed in 10.36s · EXIT=0

TOTAL after S4 = 290 passed (288 baseline + 2 new), 0 failed.
```

### Pre-commit checks

```
$ git diff --check            # clean (exit 0, no output)
$ git diff --stat -- <the 2 slice files>
 analyser/solo_mode/driver.py            |  21 ++++++
 analyser/tests/unit/test_solo_driver.py | 125 ++++++++++++++++++++++++++++++++
 2 files changed, 146 insertions(+)
$ git add <the 2 files> && git commit -m "feat(solo): SoloRetention sweep thread started with the solo runtime (SOLO-OPS P6-S4)"
[feature/cnn2dlstm-bayesian-statistical-detector-v2 9266dbf] 2 files changed, 146 insertions(+)
$ git rev-parse HEAD
9266dbf7ad6c174f34113eaf5088de75082fd7bb
```

### `driver.py` hunk summary since the P6 base (5bcc7f9)

```
$ git diff 5bcc7f9..HEAD -- analyser/solo_mode/driver.py --stat
 analyser/solo_mode/driver.py | 32 +++++++++++++++++++++++++++++++-
 1 file changed, 31 insertions(+), 1 deletion(-)

$ git diff 5bcc7f9..HEAD -- analyser/solo_mode/driver.py | grep ^@@
@@ -110,7  +110,7  @@  import: from solo_mode.state import SoloStateStore, metric_tick_rows
@@ -1488,6 +1488,12 @@ handle_solo_request: metric_ticks = metric_tick_rows(...) after metrics_out
@@ -1516,6 +1522,7  @@ handle_solo_request: metric_ticks=metric_ticks, (first record_skipped_tick)
@@ -1543,6 +1550,7  @@ handle_solo_request: metric_ticks=metric_ticks, (second record_skipped_tick)
@@ -1922,6 +1930,7  @@ handle_solo_request: metric_ticks=metric_ticks, (complete_scored_tick)
@@ -2216,6 +2225,27 @@ start_solo_runtime: the SoloRetention block (import, policy, _retention_loop,
               thread start, one INFO log)
```

Exactly the 6 permitted hunks: the import line, the `metric_ticks = …`
block, three `metric_ticks=` kwargs, and the `SoloRetention` block in
`start_solo_runtime`. No scoring-math hunk.

Unrelated tree state (` M AGENTS.md`, untracked `analyser/agent-orchestration/`,
`markdown/2026-11-06-solo-dashboard-operations-report.md`) NOT staged. No push, no trailers.

### Parity consequence (per master card)

`driver.py` remains one of the P6-touched pinned `used_files`; its blob id
changes again here. P6-repin's `git diff 5bcc7f9..HEAD -- analyser/solo_mode/driver.py`
now shows the 6 hunks above (all persistence/wiring, no scoring math —
the lab's transcribed range `driver.py:1486-1605` shifts by +10 lines from
the S2 insertion and is otherwise untouched by S4; the new S4 block sits
at `start_solo_runtime` :2216+, outside the transcribed range). Parity
stays red-by-design until P6-repin.

## S5 — docs addendum (commit 5)

Commit: `5e435a0a02d485fb31bc30039048228501d70cc7`
`docs(solo): SOLO-OPS P6 retention and scored-tick durability addendum (SOLO-OPS P6-S5)`
HEAD before: `9266dbf` · 1 file, 16 insertions, 0 deletions. No push, local only.

### Change

`markdown/2026-10-09-solo-mode-runtime-cutover.md`: dated addendum
`### SOLO-OPS-P6 addendum (2026-11-10): retention + scored-tick
durability` (15 content lines + 1 heading; ≤ 35 lines) inserted at
`:940`, immediately before `## Deviations from a naive reading of the
spec` (heading found by grep at the drifted location). Content per the
S5 item: the 7 `persistence.retention` keys + the 3 load-time rules
with deployed numbers (540,750 s; 172,800 s = 2 × 288 × 300 s); why the
raw TTL is a backstop (F1: `slide_drop` already bounds in-scope streams
to ~2 d, no valid TTL ever trims them); the table columns and the D1-D3
definitions in code terms with their limits (gate_fired = no-fresh-model
proxy for the ESS gate, failing build's ESS only logged ⇒ `ess` NULL,
one-tick build-lag race, `provenance` closed grammar
`model:<method>`/`none:<reason>`, no backfill); the sweep design (own
`SoloRetention` daemon thread, mid-tick wake at `tick boundary + T/2`,
per-stream index seeks, ≤ `sweep_batch_rows` per DELETE statement +
commit, lock per statement, pause outside the lock; measured max writer
wait 7.3 ms p99 5.2 ms 247 writes vs 194 ms without pause from the
card's M2 scratch measurement at 1.17 M rows); the study queries
(`SELECT SUM(gate_fired)*300/3600.0 FROM solo_scored_ticks WHERE
pod_key=? AND metric_name=? AND tick_epoch>=?` = stale hours; island
trick on `tick_epoch − row_number()*300` for the longest run); the disk
summary (205 B/row WITHOUT ROWID vs 358 B/row rowid ⇒ 4.55
MB/pod-week; table ≈ 6.5 % of the per-pod footprint; 5 GiB PVC holds
≈ 76 pods; the 2-day raw window, not P6, is the binding term; 1000 pods
needs ≥ 70 GB); the out-of-scope list (no Prometheus gauges/route —
the solo pod has no scrape leg; reopen triggers (a) retention exceeds
the SQLite window, (b) external/cross-restart-beyond-TTL queries).

Every number in the addendum was copied from this evidence file
(insert cost 0.158/0.169 ms S2; 207.3 B/row S2; concurrency 7.3 ms /
p99 5.2 ms / 247 writes S3; 194 ms no-pause control and 205/358 B/row
from master card M2/M3; disk/PVC finding from the master card) or the
master card's D7 (540,750 s, 172,800 s). No new measurement.

### Pre-commit checks

```
$ git diff --check            # clean (exit 0, no output)
$ git diff --stat -- markdown/2026-10-09-solo-mode-runtime-cutover.md
 markdown/2026-10-09-solo-mode-runtime-cutover.md | 16 ++++++++++++++++
 1 file changed, 16 insertions(+)
$ git add markdown/2026-10-09-solo-mode-runtime-cutover.md && git commit -m "docs(solo): SOLO-OPS P6 retention and scored-tick durability addendum (SOLO-OPS P6-S5)"
[feature/cnn2dlstm-bayesian-statistical-detector-v2 5e435a0] 1 file changed, 16 insertions(+)
```

Unrelated tree state (` M AGENTS.md`, untracked
`analyser/agent-orchestration/`,
`markdown/2026-11-06-solo-dashboard-operations-report.md`) NOT staged.
No push, no trailers, no agent names.

### Parity consequence

`markdown/` docs are unpinned (not among the 9 `used_files`); no P6-repin
consequence. Parity stays red-by-design until P6-repin (unchanged by S5).

## S6 — drop the redundant `idx_solo_window_points_key` (commit 6, OPTIONAL)

Commit: `7e4014e6874e81c0934c2dbb7670b7eea207bc18`
`perf(solo): drop redundant idx_solo_window_points_key (SOLO-OPS P6-S6, optional)`
HEAD before: `5e435a0` · 2 files, 307 insertions, 6 deletions. No push, local only.

### Production code (`window_store.py` only)

- `_init_schema`: the `CREATE INDEX IF NOT EXISTS idx_solo_window_points_key
  ON solo_window_points (pod_key, metric_name, ts_epoch)` statement is
  REMOVED; `_drop_redundant_index()` is called right after
  `_migrate_identity_columns()` (then the same final `self._conn.commit()`).
- New `_drop_redundant_index()`: presence-checked on `sqlite_master`
  (`type = 'index' AND name = 'idx_solo_window_points_key'`); if present,
  `DROP INDEX idx_solo_window_points_key` + `commit()` + the card's exact
  WARNING: `"solo_window_points migration: dropped idx_solo_window_points_key
  (identical to the PRIMARY KEY autoindex); pages move to the free list, the
  file shrinks only after an offline VACUUM"`. Idempotent: a re-open of an
  already-migrated DB is a silent no-op. NEVER `VACUUM`, never
  `auto_vacuum` (the docstring says so; the store has no such call anywhere).
  Single diff hunk `@@ -194,15 +194,45 @@` — `_merge_episodes` and
  `slide_drop` (and `scan.py`) are byte-identical
  (`git diff -- analyser/solo_mode/scan.py` empty).

### Scratch evidence re-run (card M1, kept from the planning phase)

`$ PY /tmp/solo-p6-plan/idx_check.py` → exit 0, verbatim:

```
rows (1166000,)
dbstat {'idx_solo_window_points_key': (140210176, 1166000), 'solo_window_points': (170917888, 1207622), 'sqlite_autoindex_solo_window_points_1': (140210176, 1166000), 'sqlite_schema': (4096, 3)}
-- with explicit index
merge_select ['SEARCH solo_window_points USING INDEX idx_solo_window_points_key (pod_key=? AND metric_name=?)']
read_window ['SEARCH solo_window_points USING INDEX idx_solo_window_points_key (pod_key=? AND metric_name=? AND ts_epoch>? AND ts_epoch<?)']
slide_drop ['SEARCH solo_window_points USING INDEX idx_solo_window_points_key (pod_key=? AND metric_name=? AND ts_epoch<?)']
max_ts ['SEARCH solo_window_points USING COVERING INDEX idx_solo_window_points_key (pod_key=? AND metric_name=?)']
count ['SEARCH solo_window_points USING COVERING INDEX idx_solo_window_points_key (pod_key=? AND metric_name=?)']
-- after DROP INDEX
merge_select ['SEARCH solo_window_points USING INDEX idx_solo_window_points_key (pod_key=? AND metric_name=?)']
read_window ['SEARCH solo_window_points USING INDEX idx_solo_window_points_key (pod_key=? AND metric_name=? AND ts_epoch>? AND ts_epoch<?)']
slide_drop ['SEARCH solo_window_points USING INDEX idx_solo_window_points_key (pod_key=? AND metric_name=? AND ts_epoch<?)']
max_ts ['SEARCH solo_window_points USING COVERING INDEX idx_solo_window_points_key (pod_key=? AND metric_name=?)']
count ['SEARCH solo_window_points USING COVERING INDEX idx_solo_window_points_key (pod_key=? AND metric_name=?)']
dbstat after drop (file not shrunk) {'solo_window_points': (170917888, 1207622), 'sqlite_autoindex_solo_window_points_1': (140210176, 1166000), 'sqlite_schema': (4096, 2)} freelist (34231,) pages (110191,)
size 451342336
size after VACUUM 296706048
```

(The script's own "after DROP INDEX" block re-plans on the SAME connection,
which still resolves the by-name index reference — exactly why the S6
`EXPLAIN QUERY PLAN` test uses a FRESH connection; the script's final
`VACUUM` line is the scratch script's own demo of file shrinkage, NOT
anything this store runs.)

`$ PY /tmp/solo-p6-plan/idx_check2.py` (fresh connection) → exit 0, verbatim:

```
indexes now ['sqlite_autoindex_solo_window_points_1']
merge_select ['SEARCH solo_window_points USING INDEX sqlite_autoindex_solo_window_points_1 (pod_key=? AND metric_name=?)']
read_window ['SEARCH solo_window_points USING INDEX sqlite_autoindex_solo_window_points_1 (pod_key=? AND metric_name=? AND ts_epoch>? AND ts_epoch<?)']
slide_drop ['SEARCH solo_window_points USING INDEX sqlite_autoindex_solo_window_points_1 (pod_key=? AND metric_name=? AND ts_epoch<?)']
max_ts ['SEARCH solo_window_points USING COVERING INDEX sqlite_autoindex_solo_window_points_1 (pod_key=? AND metric_name=?)']
count ['SEARCH solo_window_points USING COVERING INDEX sqlite_autoindex_solo_window_points_1 (pod_key=? AND metric_name=?)']
loose_scan ['SEARCH solo_window_points USING COVERING INDEX sqlite_autoindex_solo_window_points_1 ((pod_key,metric_name)>(?,?))']
expired_in_stream ['SEARCH solo_window_points USING COVERING INDEX sqlite_autoindex_solo_window_points_1 (pod_key=? AND metric_name=? AND ts_epoch<?)']
```

### Test changes (`test_solo_window_store.py`, +3 tests, 40 → 43;
`import logging` added to the header)

- `test_p6_s6_pre_s6_db_open_drops_redundant_index` — a populated
  pre-S6 DB (same DDL + `CREATE INDEX IF NOT EXISTS` on the PK columns,
  2 streams × 20 points) written via a plain connection: opening
  `SoloWindowStore` drops the explicit index (autoindex kept), logs
  exactly ONE WARNING containing `dropped idx_solo_window_points_key`
  (`caplog`, logger `solo_mode.window_store`, `levelno == WARNING`),
  loses no rows (`count == 20` both streams); re-open is idempotent
  (index still absent, ZERO new records); a FRESH DB never has the
  explicit index (autoindex present).
- `test_p6_s6_explain_query_plan_uses_autoindex` — on a FRESH connection
  to a post-S6 DB, `EXPLAIN QUERY PLAN` for the five query shapes
  (`merge_select`, `read_window`, `slide_drop`, `max_ts`, `count` — SQL
  copied verbatim from `window_store.py`; `read_window`'s `+ op`
  resolved to the default half-open `<`) each mentions
  `sqlite_autoindex_solo_window_points_1` and never
  `idx_solo_window_points_key`.
- `test_p6_s6_results_identical_before_and_after_drop` — on a seeded
  pre-S6 stream, `count` / `read_window` / `max_ts` / `slide_drop`
  (the strict `<` boundary: 6 rows die at cutoff 190, the surviving
  population byte-identical) produce IDENTICAL results before the
  open (plain connection, explicit index present) and after (the
  store's own methods, index dropped); a second stream is untouched.

### Test results

Baseline before S6 = **290 passed** (`test_solo_driver.py` 57 + the four
suites 233), `0 failed` (S4/S5).

```
# targeted: the three new S6 tests alone
$ PY -m pytest tests/unit/test_solo_window_store.py -q -k "p6_s6"
→ 3 passed in 0.70s · EXIT=0

# the four baseline suites (test_solo_window_store.py 40 -> 43 = +3 new S6;
# the other three unchanged)
$ PY -m pytest tests/unit/test_solo_window_store.py tests/unit/test_solo_state.py \
    tests/unit/test_solo_mode_config.py tests/unit/test_solo_retention.py -q
→ 236 passed in 10.16s · EXIT=0   (233 baseline + 3 new, all green)

# driver suite (UNTOUCHED by this slice)
$ PY -m pytest tests/unit/test_solo_driver.py -q
→ 57 passed in 51.16s · EXIT=0

TOTAL after S6 = 293 passed (290 baseline + 3 new), 0 failed.
```

### Pre-commit checks

```
$ git diff --check            # clean (exit 0, no output)
$ git diff --stat -- <the 2 slice files>
 analyser/solo_mode/window_store.py            |  42 +++-
 analyser/tests/unit/test_solo_window_store.py | 271 ++++++++++++++++++++++++++
 2 files changed, 307 insertions(+), 6 deletions(-)
$ git diff -- analyser/solo_mode/scan.py
(empty — scan.py byte-identical; _merge_episodes and slide_drop untouched:
 window_store.py's only hunk is @@ -194,15 +194,45 @@)
$ git add analyser/solo_mode/window_store.py analyser/tests/unit/test_solo_window_store.py
$ git commit -m "perf(solo): drop redundant idx_solo_window_points_key (SOLO-OPS P6-S6, optional)"
[feature/cnn2dlstm-bayesian-statistical-detector-v2 7e4014e] 2 files changed, 307 insertions(+), 6 deletions(-)
$ git rev-parse HEAD
7e4014e6874e81c0934c2dbb7670b7eea207bc18
```

Unrelated tree state (` M AGENTS.md`, untracked `analyser/agent-orchestration/`,
`markdown/2026-11-06-solo-dashboard-operations-report.md`) NOT staged. No push,
no trailers, no agent names.

### Parity consequence

NONE of S6's 2 files (`window_store.py`, `test_solo_window_store.py`) is in
the 9 pinned `used_files` — NO pinned blob id changes and P6-repin
re-records nothing for S6. `driver.py` and `scan.py` remain byte-identical to
the P6 base (`5bcc7f9`)'s S4 state; P6-repin's `git diff 5bcc7f9..HEAD --
analyser/solo_mode/driver.py` check is UNCHANGED by S6. Parity stays
red-by-design until P6-repin.

## FIX-A — keep the FIRST committed per-metric tick observation on retry (RV F1, commit 7)

Decision (S, D-S13): P6's `solo_scored_ticks` must keep the **FIRST committed
observation** of a `(pod_key, metric_name, tick_epoch)` — a retried or
re-scored tick writes nothing new. A rolled-back (failed, uncommitted)
transaction leaves no row, so its retry still inserts. This closes RV-P6 F1
(a delayed skipped-tick retry used to erase an original `gate_fired=1` row
because the writer was `ON CONFLICT DO UPDATE` and the driver's
latest-tick-only skip-marker does not dedupe an older replayed tick).

Commit: `163506f56eea6aa6204441f609ef9a79aad074fc`
`fix(solo): keep the first committed per-metric tick observation on retry (SOLO-OPS P6 RV F1)`
HEAD before: `7e4014e` · 3 files, 201 insertions(+), 15 deletions(-). No push, local only.

### Change (3 files, all named in the workcard)

**`analyser/solo_mode/state.py`:**
- `_METRIC_TICK_UPSERT` → renamed `_METRIC_TICK_INSERT` (all 2 references
  updated: the definition and the `executemany` call in
  `_insert_metric_ticks`).
- The SQL constant becomes `INSERT … ON CONFLICT(pod_key, metric_name,
  tick_epoch) DO NOTHING` (was `DO UPDATE SET p_raw/ess/gate_fired/
  stale_hours/provenance = excluded.*`).
- The comment block above `_SCORED_TICKS_DDL` gains a paragraph stating the
  writer is `DO NOTHING`, that the FIRST committed observation is preserved,
  that a retried/re-scored tick writes nothing new, and that a rolled-back
  transaction leaves no row so a retry still inserts.
- Docstrings updated to state a conflicting already-committed row is KEPT
  and a rolled-back transaction leaves no row: `_insert_metric_ticks`,
  `record_skipped_tick`, and `complete_scored_tick` (step 4 wording changed
  "upserted" → "inserted" + the P6 atomicity paragraph).

**`analyser/tests/unit/test_solo_state.py`:**
- Pinned test (was ~1279-1292) **inverted**: `…_roundtrip_and_upsert_idempotence`
  → `…_roundtrip_and_first_committed_wins`. The second write with DIFFERENT
  values (`gate_fired=0`, `stale_hours=3.5`, `none:window fill 1`) now
  asserts the FIRST row (`gate_fired=True`, `stale_hours=3.0`,
  `none:model stale`) is UNCHANGED and the row count stays 1.
- New `test_p6_metric_ticks_gated_first_row_survives_rescoring`: a skipped
  tick written with `gate_fired=1` then a `complete_scored_tick` on the same
  tick with `gate_fired=0` values → the stored row still has `gate_fired=1`
  and the original provenance (`none:model stale`), row count 1.
- New `test_p6_metric_ticks_rolled_back_retry_inserts`: a first write that
  raises `IntegrityError` (NULL `gate_fired`) leaves NO row, and a
  successful retry then inserts it (row count 1, `gate_fired=1`).

**`analyser/tests/unit/test_solo_driver.py`:**
- New `test_p6_delayed_skip_retry_keeps_first_committed_observation` — the
  reviewer's deterministic delayed-skip-retry regression via the real
  `_seeded`/`_drive` helpers (P6 (g)/(h)/(i) pattern): warm the cpu ring
  (`t0`, `t0+T` "no eligible" skips) → process the boundary tick `t0+dt`
  against the STALE persisted cpu model (mandatory-gate skip; original cpu
  row `gate_fired=1`, `p_raw` NULL, `none:model stale`, `stale_hours=dt/3600`
  = 0.5) → publish a FRESH cpu snapshot (genuine `build_one` re-fit, NEW
  `t0=t0+dt`) → process the next tick `t0+dt+T` (scores, advances the
  latest-tick dedupe marker) → REPLAY the older gated tick `t0+dt`. Asserts
  the original cpu row is unchanged (`gate_fired=1`, same provenance +
  `stale_hours`, `p_raw` NULL) and the per-metric row count did not grow.
  (The raw cpu window is first extended with the seed-7 series so the next
  tick's observed block has data; the overlapping span is idempotent under
  the bootstrap merge.)

### Pre-fix regression proof (FAILS on the pre-fix `state.py`)

Checked out `analyser/solo_mode/state.py` from the pre-fix commit `7e4014e`
(`ON CONFLICT … DO UPDATE`), ran the new driver regression against it, then
restored the committed file (`git checkout -- …` → working tree clean):

```
$ PY -m pytest tests/unit/test_solo_driver.py::test_p6_delayed_skip_retry_keeps_first_committed_observation -q
→ 1 failed in 1.28s · EXIT=1
```

Verbatim failure message:
```
tests/unit/test_solo_driver.py:5403: in test_p6_delayed_skip_retry_keeps_first_committed_observation
    assert dict(rows1[0]) == row0, (
E   AssertionError: the original gated cpu row (gate_fired=1, p_raw NULL, 'none:model stale', stale_hours) must be unchanged by the replay
E   assert {'ess': 46.06...90804598, ...} == {'ess': None,...w': None, ...}
E     Omitting 3 identical items, use -vv to show
E     Differing items:
E     {'ess': 46.06089064943557} != {'ess': None}
E     {'p_raw': 0.8563218390804598} != {'p_raw': None}
E     {'stale_hours': 0.0} != {'stale_hours': 0.5}
E     {'provenance': 'model:stl_lite'} != {'provenance': 'none:model stale'}
E     {'gate_fired': False} != {'gate_fired': True}
```
This is exactly RV F1's independently-reproduced shape: the replayed tick
rewrote the gated row (`gate_fired 1→0`, `p_raw NULL→0.856…`,
`none:model stale → model:stl_lite`, `stale_hours 0.5→0.0`).

### Test results (post-fix, all green)

```
$ PY -m pytest tests/unit/test_solo_state.py tests/unit/test_solo_window_store.py \
    tests/unit/test_solo_mode_config.py tests/unit/test_solo_retention.py -q
→ 238 passed in 12.24s · EXIT=0
   (state 46, window_store 43, mode_config 142, retention 7)

$ PY -m pytest tests/unit/test_solo_driver.py -q
→ 58 passed in 79.31s · EXIT=0
```
TOTAL = 238 + 58 = **296 passed** = RV's 293 baseline + 3 new
(`test_solo_state.py` 44→46 = +2 new tests, `test_solo_driver.py` 57→58 =
+1 new test; the inverted pinned test is a rename/re-pin of an existing
test, so it adds no count). 0 failed.

### Pre-commit checks

```
$ git diff --check            # clean (exit 0, no output)
$ git diff --stat 7e4014e..163506f
 analyser/solo_mode/state.py             |  37 +++++++++---
 analyser/tests/unit/test_solo_driver.py | 100 ++++++++++++++++++++++++++++++++
 analyser/tests/unit/test_solo_state.py  |  79 ++++++++++++++++++++++---
 3 files changed, 201 insertions(+), 15 deletions(-)
$ git add analyser/solo_mode/state.py analyser/tests/unit/test_solo_state.py analyser/tests/unit/test_solo_driver.py
$ git commit -m "fix(solo): keep the first committed per-metric tick observation on retry (SOLO-OPS P6 RV F1)"
[feature/cnn2dlstm-bayesian-statistical-detector-v2 163506f] 3 files changed, 201 insertions(+), 15 deletions(-)
$ git rev-parse HEAD
163506f56eea6aa6204441f609ef9a79aad074fc
```

Unrelated tree state (` M AGENTS.md`, untracked `analyser/agent-orchestration/`,
`markdown/2026-11-06-solo-dashboard-operations-report.md`) NOT staged. No push,
no trailers, no agent names.

### Parity consequence

FIX-A touches ONLY `state.py` (unpinned) + 2 test files (unpinned). `driver.py`
remains byte-identical to the P6 base's S4 state — the commit adds **no
`driver.py` hunk**, so no pinned `used_file` blob id changes and P6-repin's
`git diff 5bcc7f9..HEAD -- analyser/solo_mode/driver.py` check is UNCHANGED.
Parity stays red-by-design until the SECOND P6-repin (per D-S13, the first
`3f97c8e` at `7e4014e` becomes stale by design once the fix commits land).

## FIX-B — sweep empty-key streams + effective lock-free-pause assertion (RV F2, F4, commit 8)

Workcard SOLO-OPS-P6 · RV items F2 (`window_store.py:117-127` empty-string seek
sentinels) and F4 (`test_solo_window_store.py:721-724,738-740` vacuous
`join(1.0) is None` assertion).
Commit: `197a122f549b0a25c0099b12bb3c2898c746a7e8`
`fix(solo): sweep empty-key streams and make the lock-free-pause assertion effective (SOLO-OPS P6 RV F2 F4)`
HEAD before: `163506f` · 2 files, 118 insertions, 9 deletions. No push, local only.
`_merge_episodes`, `slide_drop`, `scan.py` byte-identical (not in the diff).

### F2 — `sweep_expired_rows` first-seek without a lower bound

`solo_mode/window_store.py` (shared by BOTH table sweeps):
- `q_pod_first = "SELECT pod_key FROM <table> ORDER BY pod_key LIMIT 1"` —
  used ONLY for the first pod-level seek (`pod is None`); every later
  pod-level seek keeps the strict `pod_key > ?` form.
- `q_met_first = "SELECT metric_name FROM <table> WHERE pod_key = ? ORDER BY metric_name LIMIT 1"` —
  used ONLY for the first metric-level seek of each pod (`metric is None`);
  every later metric-level seek keeps the strict `metric_name > ?` form.
- `pod`/`metric` loop state is now `None`-sentinel (instead of `""`) so the
  first-seek selection is explicit. The delete SQL, the lock-per-statement
  structure (`with lock:` per seek/delete+commit, sleep OUTSIDE the lock),
  and the batching/pause logic are UNCHANGED. Both seek shapes are index
  seeks on the PK prefix (`ORDER BY <key> LIMIT 1`), not table scans.

> **RV-P6b R2 correction (FIX-D):** that last sentence is inaccurate as
> written: the FIRST-pod seek's `EXPLAIN QUERY PLAN` is a bounded
> first-entry B-tree traversal (`SCAN solo_window_points USING COVERING
> INDEX sqlite_autoindex_..._1` / `SCAN solo_scored_ticks`), NOT an
> index seek; every LATER seek (pod and metric) is a strict indexed
> range seek. Correct wording (now in `window_store.py`): the first
> seeks are a bounded first-entry PK-B-tree traversal (`LIMIT 1`),
> then strict indexed range seeks; no full scan or sort.

New tests in `tests/unit/test_solo_window_store.py` (2, both tables):
- `test_p6_sweep_empty_key_and_unicode_streams` (f): via
  `SoloWindowStore.sweep_expired` — streams `('', 'cpu')` (5 expired + 2
  live incl. the row at exactly the cutoff), `('pod', '')`, mixed-case
  `('Pod', 'mem')` + `('pod', 'cpu')`, and Unicode `('päod', 'gpu')`; all
  expired rows swept, live rows survive (strict `<`), `n` exact
  (`5+4+3+3+3`), one pause per non-empty batch, second run deletes 0.
- `test_p6_sweep_scored_ticks_empty_key_and_unicode_streams` (g): via
  `SoloStateStore.sweep_expired_scored_ticks` — the same pod/metric key
  set (pod `''`, empty metric on pod `pod`, mixed-case `Pod`, Unicode
  `päod`); note: `_seed_state` persists the pod's CANONICAL metric rows
  (as test (e)'s `* 11` counts), so the sweep's per-metric coverage is
  asserted on `CANONICAL_METRIC_NAMES[0]` with exact live-row counts
  (2 for pod `''` — 999_700/999_900 swept, cutoff-exact + 1_000_300
  kept; 1 each for the others); `n` exact (77 = 7 expired ticks × 11
  canonical rows), cutoff-exact tick survives
  (`has_scored_tick('', cutoff)`), second run deletes 0.

> **RV-P6b R1 correction (FIX-D):** the coverage claim above was
> incomplete at commit `197a122`: `_seed_state` ignores its `metric`
> argument (canonical 11 only), so the COMMITTED version of test (g)
> never seeded a `metric_name=''` row in `solo_scored_ticks` and its
> per-metric assertions covered only `CANONICAL_METRIC_NAMES[0]`.
> FIX-D seeded real rows for `('pod','')` (2 expired + 1 live) and
> `('','')` (3 expired + 1 live) through the real `metric_ticks`
> input of `complete_scored_tick`, asserts their presence BEFORE the
> sweep, and asserts exact expired/live counts for both streams
> (`n` now 82 = 77 canonical + 5 empty-metric rows; live counts 1/1).
> Negative control: temporarily re-introducing `metric_name > ''` in
> the first metric seek makes exactly this test fail at the `n` count
> (77 vs 82) — the `('pod','')`/`('','')` streams are skipped by the
> old empty-sentinel seek. See `## FIX-D` below.

### F4 — `test_p6_sweep_lock_free_during_pause` assertion made effective

- `pause_hook` now: start the reader thread → `t.join(1.0)` →
  `assert not t.is_alive()` AND `assert reader_ran == [2]` INSIDE the
  pause hook, BEFORE returning to the sweep — so a lock held across the
  pause fails the test immediately instead of vanishing by the time the
  whole sweep returns.
- The independent-connection write assertion (WAL writer from a second
  connection during the pause) is KEPT unchanged.
- The old `assert t.join(1.0) is None` (true whether or not the worker
  finished) is removed; the post-sweep `reader_ran` check is kept as a
  plain postcondition (annotated as observed inside the hook).

### Negative control (proves the F4 test catches a lock held across the pause)

Temporary edit to `sweep_expired_rows`: the `sleep(pause_s)` call wrapped in
`with lock:` (pause inside the lock). Then, on that single test:

```
$ PY -m pytest tests/unit/test_solo_window_store.py::test_p6_sweep_lock_free_during_pause -q
E   tests/unit/test_solo_window_store.py:732: in pause_hook
E       assert not t.is_alive(), "count() was blocked by the sweep"
E   E   AssertionError: count() was blocked by the sweep
E   E   assert not True
========================= 1 failed, 1 warning in 1.78s =========================
EXIT=0   (pytest exit 1)
```
(verbatim: `FAILED tests/unit/test_solo_window_store.py::test_p6_sweep_lock_free_during_pause - AssertionError: count() was blocked by the sweep` — the reader thread is still alive when the hook checks, i.e. `count()` was blocked by the held RLock).
The temporary edit was then REVERTED (verified by the green runs below; the
restored code is what commit `197a122` contains).

### Test results (post-fix, all green)

```
$ PY -m pytest tests/unit/test_solo_window_store.py tests/unit/test_solo_state.py \
    tests/unit/test_solo_mode_config.py tests/unit/test_solo_retention.py -q
→ 240 passed in 11.66s · EXIT=0
   (window_store 45 = 43 + 2 new, state 46, mode_config 142, retention 7)

$ PY -m pytest tests/unit/test_solo_driver.py -q
→ 58 passed in 78.34s · EXIT=0
```
TOTAL = 240 + 58 = **298 passed** = FIX-A's 238+58 = 296 + 2 new
(`test_solo_window_store.py` 43→45; the F4 test is a re-pin, no new count).
0 failed.

### Pre-commit checks

```
$ git diff --check            # clean (exit 0, no output)
$ git diff --stat 163506f..HEAD
 analyser/solo_mode/window_store.py            |  21 +++++-
 analyser/tests/unit/test_solo_window_store.py | 106 ++++++++++++++++++++++++++++--
 2 files changed, 118 insertions(+), 9 deletions(-)
$ git add analyser/solo_mode/window_store.py analyser/tests/unit/test_solo_window_store.py
$ git commit -m "fix(solo): sweep empty-key streams and make the lock-free-pause assertion effective (SOLO-OPS P6 RV F2 F4)"
[feature/cnn2dlstm-bayesian-statistical-detector-v2 197a122] 2 files changed, 118 insertions(+), 9 deletions(-)
$ git rev-parse HEAD
197a122f549b0a25c0099b12bb3c2898c746a7e8
```

Unrelated tree state (` M AGENTS.md`, untracked `analyser/agent-orchestration/`,
`markdown/2026-11-06-solo-dashboard-operations-report.md`) NOT staged. No push,
no trailers, no agent names.

### Parity consequence

FIX-B touches `window_store.py` + `test_solo_window_store.py` ONLY.
`state.py` and `driver.py` remain byte-identical to the post-FIX-A state —
the commit adds no `state.py`/`driver.py` hunks, so no pinned `used_file`
blob id changes and P6-repin's `git diff 5bcc7f9..HEAD -- analyser/solo_mode/driver.py`
check is UNCHANGED. Parity stays red-by-design until the SECOND P6-repin.

## FIX-C — correct P6 scheduling/age/capacity claims + pin age precedence and schedule bounds (RV F3, F5, F6, commit 9)

Workcard SOLO-OPS-P6 · RV items F3 (`state.py:85-93` + addendum `:946`:
`stale_hours`/`gate_fired` semantics overstate the fields), F5
(`retention.py:18-20,83-95` + `driver.py:2234-2237` + addendum `:948`:
scheduling docs overstate cadence/non-overlap), F6 (addendum `:952`:
disk guidance not refreshed post-S6).
Commit: `e30ddb07194d6f60e4116d1d7899e83f03f45b0d`
`docs(solo): correct P6 scheduling, age and capacity claims; pin age precedence and schedule bounds (SOLO-OPS P6 RV F3 F5 F6)`
HEAD before: `197a122` · 6 files, 148 insertions, 14 deletions. No push, local only.

### F3 — `stale_hours` precedence + `gate_fired` proxy, documented truthfully

- `analyser/solo_mode/state.py`: the `metric_tick_rows` DOCSTRING (ONLY
  the docstring) now states: `stale_hours` = the scoring-snapshot
  `model_age_seconds` WHEN PRESENT, otherwise `tick_epoch − model_t0`
  from a lookup made AFTER scoring (async publication may land between
  scoring and that lookup ⇒ a row's age is not necessarily the newest
  persisted model's age when rows are assembled), clamped at 0, NULL
  when neither source exists; a row's `stale_hours` is an age-on-a-row,
  distinct from the aggregate `SUM(gate_fired) * T / 3600`;
  `gate_fired` is a NO-FRESH-MODEL PROXY — a build-lag after a refit
  boundary, an ESS-gate rejection, and the
  counter-representation/policy `model stale` can look identical
  (same `none:model stale` provenance + age), so separation and exact
  cause attribution are NOT guaranteed; first-committed-wins (a
  retried or re-scored tick writes nothing new).
- `markdown/.../2026-10-09-solo-mode-runtime-cutover.md` (P6 addendum,
  `**Table**` line only): same semantics in operator words —
  `gate_fired` is a proxy, not a cause label (all three
  `none:model stale` sources listed; "separable via stale_hours +
  provenance" REMOVED); `stale_hours` precedence stated exactly as in
  the code; first-committed-wins sentence added. Addendum stays 16
  content lines (≤ 45).
- New test `test_p6_metric_tick_rows_stale_hours_precedence_pinned`
  (`test_solo_state.py`): snapshot age 1200 s with a persisted
  `t0 == tick` ⇒ `stale_hours == 1200/3600` (NOT 0); absent snapshot
  age falls back to the t0 lookup; a FUTURE t0 clamps to 0.0; neither
  source ⇒ NULL.

### F5 — `next_sweep_epoch` described truthfully (minimum interval + midpoint rounding)

- `analyser/solo_mode/retention.py`: MODULE docstring (only that
  paragraph) — a sweep is started at a mid-tick instant to stay away
  from the tick-boundary writers, but a large backlog, wake delay or
  wall-clock jump is NOT guaranteed to keep batches clear of a
  scoring boundary (the short `batch_pause_s` between batches is what
  keeps waiting writers waiting short). `next_sweep_epoch` docstring
  (ONLY): the next mid-tick instant at or after `now + interval`,
  i.e. `ceil((now+interval)/T)*T + T/2`; `interval` is a MINIMUM; with
  repeated midpoint starts the effective cadence is `interval + T`
  (3900 s / 65 min at the deployed values, not exactly one hour).
- `analyser/solo_mode/driver.py`: the comment ABOVE the `SoloRetention`
  block only (`start_solo_runtime`, the new 11-line `# SOLO-OPS-P6:`
  comment above `from solo_mode import retention`) — same minimum-
  interval + 65-min effective-cadence + no-boundary-guarantee wording.
- Addendum `**Sweep**` line: "wakes mid-tick every sweep_interval"
  replaced with the `ceil((now+sweep_interval)/T)*T + T/2`
  minimum-interval form, the 65-min/3900-s effective cadence at the
  deployed values, and the explicit no-non-overlap-guarantee sentence
  (10 ms pause is what keeps writers waiting short).
- New test `test_next_sweep_epoch_upper_bound_and_midpoint_cadence`
  (`test_solo_retention.py`): for 200 seeded random `now` values,
  `now + interval <= result < now + interval + 1.5*T` and
  `result % T == T/2`; cadence property
  `next_sweep_epoch(result, T, interval) − result == interval + T`
  when `now = result` (a tick midpoint, `interval % T == 0`), checked
  at two seeded midpoints.

### F6 — capacity sentence refreshed with the card's pre-/post-S6 numbers

Addendum `**Disk**` line replaced: per-pod raw window **61.6 MB before
S6 / 43.7 MB after**; the 5 GiB PVC holds ≈ **76 pods before S6 / 103
after**; 1000 pods ≈ **70 GB before / 52 GB after** — all labelled an
ACTIVE-STREAM PROJECTION that EXCLUDES WAL, free-space and headroom
(bytes the two TTL-bounded tables + raw window hold, not the file
size). The S6 index drop moves pages to the FREE LIST, so an EXISTING
file only shrinks after an operator-run offline `VACUUM` (P6 never
does; no `VACUUM`/`auto_vacuum` anywhere in the store). Operator
sizing warning KEPT: the 2-day raw window (not P6) is the binding
term; **70 GB is a conservative provisioning figure**, not a measured
file size. Numbers from the master card's budget table (`solo-ops-P6.md`
lines 47-55) and E-P6 S6.

### Pre-commit checks

```
$ git diff --check            # clean (exit 0, no output)
$ git diff --stat 197a122..HEAD    (== the pre-commit working-tree stat)
 analyser/solo_mode/driver.py                     | 11 ++++++
 analyser/solo_mode/retention.py                  | 35 +++++++++++++-----
 analyser/solo_mode/state.py                      | 29 ++++++++++++++-
 analyser/tests/unit/test_solo_retention.py       | 34 +++++++++++++++++
 analyser/tests/unit/test_solo_state.py           | 47 ++++++++++++++++++++++++
 markdown/2026-10-09-solo-mode-runtime-cutover.md |  6 +--
 6 files changed, 148 insertions(+), 14 deletions(-)
```

`git diff` of `driver.py`, `state.py`, `retention.py` inspected line by
line: COMMENT/DOCSTRING LINES ONLY (no logic change). AST-equality
check (as commanded: `ast.dump(ast.parse(old))` vs new with docstrings
stripped, old via `git show HEAD:<path>` at pre-commit HEAD `197a122`):

```
{'analyser/solo_mode/driver.py': True, 'analyser/solo_mode/state.py': True,
 'analyser/solo_mode/retention.py': True}
```

### Test results (all green)

```
$ PY=/tmp/solo-p3-venv/bin/python · PYTHONPATH=…/pipelineml-shared · cwd analyser/

$ PY -m pytest tests/unit/test_solo_state.py tests/unit/test_solo_window_store.py \
    tests/unit/test_solo_mode_config.py tests/unit/test_solo_retention.py -q
→ 242 passed in 12.34s · EXIT=0
   (state 47 = 46 + 1 new F3 precedence test, window_store 45,
    mode_config 142, retention 8 = 7 + 1 new F5 upper-bound test)

$ PY -m pytest tests/unit/test_solo_driver.py -q      # once, at the end
→ 58 passed in 77.97s · EXIT=0
```

GATE = 242 + 58 = **300 passed** = FIX-B's 240 + 58 = 298 + 2 new
(`test_solo_state.py` 46→47, `test_solo_retention.py` 7→8; the other
three suites unchanged). 0 failed. `test_solo_dashboard_routes.py`
never run (forbidden).

### Pre-commit record / commit

```
$ git add markdown/2026-10-09-solo-mode-runtime-cutover.md analyser/solo_mode/state.py \
    analyser/solo_mode/retention.py analyser/solo_mode/driver.py \
    analyser/tests/unit/test_solo_state.py analyser/tests/unit/test_solo_retention.py
$ git commit -m "docs(solo): correct P6 scheduling, age and capacity claims; pin age precedence and schedule bounds (SOLO-OPS P6 RV F3 F5 F6)"
[feature/cnn2dlstm-bayesian-statistical-detector-v2 e30ddb0] 6 files changed, 148 insertions(+), 14 deletions(-)
$ git rev-parse HEAD
e30ddb07194d6f60e4116d1d7899e83f03f45b0d
```

Unrelated tree state (` M AGENTS.md`, untracked `analyser/agent-orchestration/`,
`markdown/2026-11-06-solo-dashboard-operations-report.md`) NOT staged. No
push, no trailers, no agent names.

### Parity consequence

FIX-C touches `state.py`, `retention.py` (unpinned), `driver.py`
(pinned — but ONLY a comment: AST-identical to the pre-commit module;
the `git diff 5bcc7f9..HEAD -- analyser/solo_mode/driver.py` blob-level
check will still show the comment hunk, so the SECOND P6-repin must
re-record the new `driver.py` blob id — no SCORING-MATH change, the
lab's `prod_runner` transcription of `driver.py:1486-1605` is outside
the comment's location), 2 test files (unpinned), 1 doc (unpinned).
Parity stays red-by-design until the SECOND P6-repin, which now also
absorbs the FIX-C comment.

## FIX-D — RV-P6b R1-R4: empty-metric scored sweep test, plan wording, schedule bound, capacity evidence (commit 10)

Workcard SOLO-OPS-P6 · RV-P6b residual findings R1 (should-fix: scored
empty-metric regression absent), R2 (nit: "never a table scan"
inaccurate), R3 (should-fix: false schedule upper bound), R4 (should-fix:
incomplete budget table + unlabeled 6.5 %). Accepted by S (D-S14).
Commit message:
`docs(solo): final P6 review residuals - empty-metric sweep test, schedule bound and capacity wording (SOLO-OPS P6 RV-b R1 R2 R3 R4)`
HEAD before: `e30ddb0` · 5 production files committed;
`E-P6.md` appended separately (evidence, not in the commit).
No push, local only. `window_store.py` / `retention.py` /
`driver.py` changes are COMMENT/DOCSTRING ONLY.

### R1 — real `('pod','')` / `('','')` rows in `test_p6_sweep_scored_ticks_empty_key_and_unicode_streams`

`analyser/tests/unit/test_solo_window_store.py`:
- New helper `_seed_state_metric(store, pod, metric_name, ticks)`:
  seeds ONE named metric's rows through the REAL `metric_ticks`
  input of `complete_scored_tick` (`metric_ticks=((name, None, None,
  0, None, "none:model not built"),)`; the store accepts a
  non-canonical/empty `metric_name` there — no direct fixture SQL
  needed). The existing `_seed_state` still ignores its `metric`
  argument (canonical 11) and is UNCHANGED.
- Test (g) now seeds `('pod','')` with 2 expired + 1 live
  ([999_100, 999_500, 1_000_500]) and `('','')` with 3 expired + 1
  live ([999_200, 999_400, 999_800, 1_000_400]) via the helper;
  asserts their presence BEFORE the sweep (`3` and `4` rows);
  expired total `n` now `82 = 77 canonical + 5 empty-metric`;
  exact live counts after the sweep: `('pod','') == 1` (the
  1_000_500 tick), `('','') == 1` (the 1_000_400 tick; strict `<`
  cutoff).

Negative control (the test FAILS with the old empty-sentinel seek):
temporarily re-introduced `metric_name > ''` in the FIRST metric
seek of `sweep_expired_rows` (`q_met_first`), ran exactly this test:

```
$ PY -m pytest tests/unit/test_solo_window_store.py::test_p6_sweep_scored_ticks_empty_key_and_unicode_streams -q
E   tests/unit/test_solo_window_store.py:926: in test_p6_sweep_scored_ticks_empty_key_and_unicode_streams
E       assert n == (2 * 11 + 2 * 11 + 1 * 11 + 1 * 11 + 1 * 11) + 2 + 3
E   E   assert 77 == (((((((2 * 11) + (2 * 11)) + (1 * 11)) + (1 * 11)) + (1 * 11)) + 2) + 3)
=========================== short test summary info ============================
FAILED tests/unit/test_solo_window_store.py::test_p6_sweep_scored_ticks_empty_key_and_unicode_streams - assert 77 == 82
============================== 1 failed in 0.85s ===============================
EXIT=1
```

i.e. `n == 77` vs expected `82`: the old `metric_name > ''` first
seek skips the `('pod','')` and `('','')` streams entirely (the 5
empty-metric rows survive the sweep). The temporary edit was then
RESTORED to `q_met_first = "SELECT metric_name FROM <table> WHERE
pod_key = ? ORDER BY metric_name LIMIT 1"` (verified by the green
gate below; `window_store.py` carries only the R2 comment hunk in
the commit).

E-P6's FIX-B coverage claim at the quoted lines (~:971-976) is
corrected by an appended note (R1 correction) there, not a rewrite.

### R2 — seek-plan wording (nit)

- `analyser/solo_mode/window_store.py` (:117-123 comment, no logic
  change): "Both shapes stay index seeks on the PK prefix … never a
  table scan" replaced with: the first seeks are a BOUNDED
  FIRST-ENTRY PK-BTREE TRAVERSAL (`ORDER BY <key> LIMIT 1`), then
  STRICT INDEXED RANGE SEEKS; NO FULL SCAN OR SORT. No index added,
  no query altered (RV-P6b: do not change correct queries to alter
  EQP terminology).
- E-P6 FIX-B text (:957-958) gets the same correction note (R2
  correction) — the reviewer's own EQP (RV-P6b F2/F4: `SCAN
  solo_window_points USING COVERING INDEX …` / `SCAN
  solo_scored_ticks` on the first pod) is the evidence the note
  cites.

### R3 — `next_sweep_epoch` bound: `[T/2, 1.5*T)` conservative following-boundary midpoint

- `analyser/solo_mode/retention.py` `next_sweep_epoch` docstring
  (ONLY, :91-108): the result is the CONSERVATIVE FOLLOWING-BOUNDARY
  MIDPOINT — the midpoint of the first full tick whose START is at
  or after `now + interval` — NOT the earliest midpoint at or after
  the minimum; it exceeds `now + interval` by `[tick/2, 1.5*tick)`
  (e.g. now=1, tick=300, interval=3600 gives 4050, i.e. 449 past
  the minimum of 3601). No algorithm change.
- `analyser/solo_mode/driver.py` (:2229-2242 comment above the
  `SoloRetention` block, ONLY): aligned to the same
  conservative-following-boundary-midpoint wording + the
  `[T/2, 1.5*T)` excess.
- `markdown/2026-10-09-solo-mode-runtime-cutover.md` addendum
  `**Sweep**` line (~:948): same wording (midpoint of the first
  tick whose start is at or after `now + sweep_interval`, NOT the
  earliest midpoint; wake exceeds by `[T/2, 1.5*T)`).

### R4 — pre/post-S6 percentage labelled + complete budget matrix in this file

- Addendum `**Disk**` line (~:952): `≈ 6.5 % of the per-pod
  footprint` is now labelled **pre-S6** with its arithmetic (4.54608
  / 69.84608 MB = 6.51 %) and the post-S6 value **≈ 8.75 %**
  (4.54608 / 48.24608 MB = 8.75 %) given alongside.
- Complete pre/post-S6 budget matrix (below), recomputed from the
  master card's lines 47-55 with the arithmetic shown.

#### R4 — complete pre/post-S6 budget table (recomputed, shown arithmetic)

Inputs (master card `solo-ops-P6.md` :47-55, E-P6 S2/S6):
- scored rows/pod-week = `7 × 86400 / 300 × 11 = 22,176` rows;
  `22,176 × 205 B = 4,546,080 B = 4.54608 MB` (card rounds to 4.55 MB).
- raw window per pod: **61.6 MB pre-S6 / 43.7 MB post-S6** (S6).
- other tables per pod: **3.7 MB** (card M3).
- 5 GiB PVC = `5 × 1024^3 B = 5,368,709,120 B = 5.36870912 GB`.

Per-pod totals: pre-S6 = 4.54608 + 61.6 + 3.7 = **69.84608 MB**;
post-S6 = 4.54608 + 43.7 + 3.7 = **48.24608 MB**.

| Pods | Scored 7d GB | Raw pre/post GB | Other GB | Total pre/post GB | Share of 5.36870912 GB PVC (pre/post) |
|---:|---:|---:|---:|---:|---:|
| 10 | 0.0454608 | 0.616 / 0.437 | 0.037 | 0.6984608 / 0.5194608 | 13.01 % / 9.68 % |
| 100 | 0.454608 | 6.16 / 4.37 | 0.37 | 6.984608 / 5.194608 | 130.10 % / 96.76 % |
| 1000 | 4.54608 | 61.6 / 43.7 | 3.7 | 69.84608 / 51.94608 | 1300.98 % / 967.57 % |

Scored fraction of the per-pod footprint: pre-S6 = 4.54608 /
69.84608 = **6.5087 %**; post-S6 = 4.54608 / 48.24608 = **8.7515 %**
(addendum's `~6.5 %` / `~8.75 %` are these, labelled).
5-GiB capacity: 5.36870912 / (69.84608/1000) = **76.8649 pods
pre-S6**; 5.36870912 / (48.24608/1000) = **103.3516 pods post-S6**
(addendum's ≈76 / ≈103 are these rounded).

Cross-check against RV-P6b :67-75 independent recomputation:
IDENTICAL on every value — 22,176 rows/pod-week; 4.54608
MB/pod-week; 5.36870912 GB; the full 10/100/1000 table (0.0454608 /
0.616 / 0.437 / 0.037 / 0.6984608 / 0.5194608; 0.454608 / 6.16 /
4.37 / 0.37 / 6.984608 / 5.194608; 4.54608 / 61.6 / 43.7 / 3.7 /
69.84608 / 51.94608); 76.8649 / 103.3516 pods; 6.5087 % / 8.7515 %.
No differences found. (RV-P6b also notes the master card's rounded
`52.1` GB at 1000 pods differs from recomputed 51.94608 — card
rounding, not a new measurement; the card's `13 % / 10 %` shares are
69.84608/5.37 and 51.94608/5.37 on its own rounded inputs.)

### Commands and results (cwd `analyser/`, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`)

```
# R1 negative control (temporary `metric_name > ''` re-introduced in q_met_first):
$ PY -m pytest tests/unit/test_solo_window_store.py::test_p6_sweep_scored_ticks_empty_key_and_unicode_streams -q
→ 1 failed in 0.85s · EXIT=1  (assert 77 == 82, verbatim above)
# …temporary edit restored (only the R2 comment hunk remains).

# GATE:
$ PY -m pytest tests/unit/test_solo_window_store.py tests/unit/test_solo_state.py \
    tests/unit/test_solo_mode_config.py tests/unit/test_solo_retention.py -q
→ 242 passed in 9.75s · EXIT=0
   (window_store 45 — test (g) is a RE-PIN, no new test count, hence
    baseline 242 + 0; state 47, mode_config 142, retention 8)

# driver, once at the end:
$ PY -m pytest tests/unit/test_solo_driver.py -q
→ 58 passed in 56.40s · EXIT=0
```

GATE = 242 + 58 = **300 passed** = FIX-C's 242 + 58 = 300 + 0 new
tests (R1 is a re-pin of existing test (g); R2/R3/R4 are
comment/doc/evidence only). 0 failed. `test_solo_dashboard_routes.py`
never run (forbidden).

### Pre-commit checks

```
$ git diff --check            # clean (exit 0, no output)
$ git diff --stat -- analyser/solo_mode/window_store.py analyser/solo_mode/retention.py \
    analyser/solo_mode/driver.py analyser/tests/unit/test_solo_window_store.py \
    markdown/2026-10-09-solo-mode-runtime-cutover.md
 analyser/solo_mode/driver.py                     | 21 +++++----
 analyser/solo_mode/retention.py                  | 15 ++++--
 analyser/solo_mode/window_store.py               |  6 ++-
 analyser/tests/unit/test_solo_window_store.py    | 58 +++++++++++++++++++++---
 markdown/2026-10-09-solo-mode-runtime-cutover.md |  4 +-
 5 files changed, 79 insertions(+), 25 deletions(-)
```

AST-equality (old = `git show HEAD:<path>` at pre-commit HEAD
`e30ddb0`, both sides parsed, module/class/function docstrings
stripped, `ast.dump(..., include_attributes=False)` compared):

```
{'analyser/solo_mode/window_store.py': True,
 'analyser/solo_mode/retention.py': True,
 'analyser/solo_mode/driver.py': True}
```

All three: AST-IDENTICAL — comment/docstring-only, as required.

### Commit

```
$ git add analyser/solo_mode/window_store.py analyser/solo_mode/retention.py \
    analyser/solo_mode/driver.py analyser/tests/unit/test_solo_window_store.py \
    markdown/2026-10-09-solo-mode-runtime-cutover.md
$ git commit -m "docs(solo): final P6 review residuals - empty-metric sweep test, schedule bound and capacity wording (SOLO-OPS P6 RV-b R1 R2 R3 R4)"
[feature/cnn2dlstm-bayesian-statistical-detector-v2 c6ec9a2] 5 files changed, 79 insertions(+), 25 deletions(-)
$ git rev-parse HEAD
c6ec9a22b7cf5da42be082f70e2a36a8f207c0d0
```

Unrelated tree state (` M AGENTS.md`, untracked
`analyser/agent-orchestration/`,
`markdown/2026-11-06-solo-dashboard-operations-report.md`) NOT
staged. No push, no trailers, no agent names.
