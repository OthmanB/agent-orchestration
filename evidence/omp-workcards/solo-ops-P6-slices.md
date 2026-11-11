# SOLO-OPS-P6 slices (companion of [solo-ops-P6.md](solo-ops-P6.md); E reads the master card + ONE slice)

Rules for every slice: production repo `/Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector`, `cd analyser`; `PY=/tmp/solo-p3-venv/bin/python`, `export PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared`. Edit ONLY the listed files; follow surrounding style, no reformatting, no new dependency, `logging` not `print`, type hints. After the edits: the slice's new tests, then the three baseline suites (`test_solo_state.py test_solo_window_store.py test_solo_mode_config.py`, 170 before S1) and — when `driver.py` is touched — `test_solo_driver.py` (~55 s). Commit = `git add <listed files only>` then `git commit -m "<msg>"` (local; no push, no `-A`, no trailers). Append commands/exit codes/counts/numbers to `/Users/obenomar/Work/langGraph/appthrust/agent-orchestration/evidence/E-reference-model-study/E-P6.md`. Order: S1 → S2 → S3 → S4 → S5 → (S6 optional) → P6-repin (lab). E never runs live cluster work, docker, or the lab.

## S1 — required `persistence.retention` block + load-time validation (5 files; commit 1)
Files: `analyser/solo_mode/config.py`, `analyser/config/detector-common.yaml`, `deploy/k8s/solo-card6/configmap.yaml`, `analyser/tests/unit/test_solo_mode_config.py`, `markdown/2026-10-09-solo-mode-config-schema.md`.
1. `config.py`: module constant next to `SQLITE_SYNCHRONOUS_MODES`: `_RETENTION_KEYS = frozenset({"raw_points_ttl","scored_ticks_ttl","lookback_margin","safety_factor","sweep_interval","sweep_batch_rows","sweep_batch_pause_ms"})`. In §19 after the `depth_seconds` check (`:930-941`), before `# ── 20. logging` (`:943`), using in-scope `Dt_seconds`, `tick_seconds`, `depth_seconds` (names verified):
   `retention = _require_key(persistence, "retention")`; non-dict ⇒ `ConfigurationError("…'solo_mode.persistence.retention' must be a mapping.")`; `unknown = sorted(set(retention) - _RETENTION_KEYS)` ⇒ error naming `unknown` and the allowed set. Durations: `_parse_duration_seconds(_require_key(retention, K), "solo_mode.persistence.retention."+K)` for `raw_points_ttl`, `scored_ticks_ttl`, `lookback_margin`, `sweep_interval`; `safety = _require_number_gt(retention, "safety_factor", 1.0)`; `_require_positive_int` for `sweep_batch_rows`, `sweep_batch_pause_ms`. Cross-rules (message states the numbers and the formula):
   - `lookback_s = Dt_seconds + margin_s + tick_seconds`; `raw_ttl_s >= safety * lookback_s` else error (min TTL printed);
   - `ring_ticks = max(1, depth_seconds // tick_seconds)`; `scored_ttl_s >= 2 * ring_ticks * tick_seconds` else error;
   - `tick_seconds <= interval_s <= min(raw_ttl_s, scored_ttl_s)` else error.
   No defaults anywhere. `build_solo_mode_config` needs no change (`persistence=dict(...)` copies the block).
2. Both YAMLs, directly after `scored_tick_history` (detector-common: 4-space indent under `persistence:`, quoted durations like `depth: "1d"`; ConfigMap: 8-space indent, unquoted like `depth: 1d`), identical values, one comment per key: `retention: {raw_points_ttl: 7d, scored_ticks_ttl: 7d, lookback_margin: 12h, safety_factor: 2.5, sweep_interval: 1h, sweep_batch_rows: 2000, sweep_batch_pause_ms: 10}` written block-style. Comments: raw TTL is a backstop (`slide_drop` already trims in-scope streams to `Dt+T`); `lookback_margin` = raw history the reference may read beyond `window.Dt` (cand-B max adaptive boxcar 12 h); scored TTL ≥ 2× ring; pause lets a waiting writer in. ConfigMap header comment (top of file) gains one line: solo-ops P6 `persistence.retention.*` — the P6 image's config validation refuses to START without the block, old images ignore it.
3. Doc: two table rows in `markdown/2026-10-09-solo-mode-config-schema.md` after `:88`: `persistence.retention` (7 required keys, unknown rejected) and the three cross-rules with the deployed numbers (540,750 s / 172,800 s).
Tests (`test_solo_mode_config.py`): add the 7 keys to `_valid_solo()` (`:163` area, `persistence`). New: (i) parametrized over each of the 7 keys: delete ⇒ `ConfigurationError` `match=<key>`; and deleting the `retention` block ⇒ matches `retention`; (ii) wrong types/ranges: durations `0`, `"7w"`, `7`, `True`, `"0d"`; `safety_factor` `1.0`, `True`, `"2.5"`; rows/pause `0`, `-1`, `True`, `1.5`; (iii) unknown key `raw_points_ttl_typo` rejected, message names it; (iv) boundaries with `_valid_solo` (Dt 2d, T 300, margin 12h, factor 2.5): `raw_points_ttl "540750s"` passes, `"540749s"` rejected (message contains `540750`); `scored_ticks_ttl "172800s"` passes, `"172799s"` rejected; with `scored_tick_history.depth "2d"` the floor is `345600s`; interval `"299s"` rejected, interval above `min(ttl)` rejected; (v) shipped values: parse the repo ConfigMap (`os.path.join(ANALYSER_DIR, "..", "deploy", "k8s", "solo-card6", "configmap.yaml")`, `yaml.safe_load(cm["data"]["detector-common.yaml"])`), `validate_solo_mode_config` passes on its `solo_mode` block, and its `persistence.retention` equals `DEV_COMMON_YAML`'s and the 7 literal values above.
Acceptance: 170 + new tests green; `git diff --stat` = the 5 files. Commit: `feat(solo): required persistence.retention config with load-time TTL validation (SOLO-OPS P6-S1)`.

## S2 — `solo_scored_ticks` table + writer on BOTH tick paths (4 files; commit 2)
Files: `analyser/solo_mode/state.py`, `analyser/solo_mode/driver.py`, `analyser/tests/unit/test_solo_state.py`, `analyser/tests/unit/test_solo_driver.py`.
1. `state.py`: add `import`s only if missing (`Sequence`). Module constants `_SCORED_TICKS_DDL` (exact DDL of master card D4, incl. `WITHOUT ROWID`, comment: `p_raw` is the per-metric `m["p"]`, not the pod-level `p_raw`; `gate_fired` is the no-fresh-model gate, unrelated to `solo_pod_scored_history.gate_pass`) and `_METRIC_TICK_UPSERT` (`INSERT INTO solo_scored_ticks (pod_key, metric_name, tick_epoch, p_raw, ess, gate_fired, stale_hours, provenance) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(pod_key, metric_name, tick_epoch) DO UPDATE SET p_raw=excluded.p_raw, ess=excluded.ess, gate_fired=excluded.gate_fired, stale_hours=excluded.stale_hours, provenance=excluded.provenance`).
2. `__init__` (`:66-70`): last line `self._migrate_scored_ticks()`. Method: under the lock, `exists = SELECT 1 FROM sqlite_master WHERE type='table' AND name='solo_scored_ticks'`; if exists return; `upgrade = SELECT 1 FROM solo_pod_scored_history LIMIT 1` row present; execute DDL + commit; `(logger.warning if upgrade else logger.info)("solo_scored_ticks migration: created table in database %s; no backfill — per-metric history starts at the first tick persisted after this migration", self.db_path)`. DDL is NOT added to `_init_schema`.
3. Module-level pure function (after `_dumps`):
```python
def metric_tick_rows(metrics: dict, model_t0: dict, tick_epoch: float) -> list:
    """(metric_name, p_raw, ess, gate_fired, stale_hours, provenance) per metric; D1-D3 of solo-ops-P6."""
    rows = []
    for name, m in metrics.items():
        p, reason, age = m.get("p"), str(m.get("reason") or ""), m.get("model_age_seconds")
        scored = p is not None
        if age is None and name in model_t0:
            age = float(tick_epoch) - float(model_t0[name])
        rows.append((name, float(p) if scored else None,
                     float(m["ess"]) if scored and m.get("ess") is not None else None,
                     1 if (not scored and reason == "model stale") else 0,
                     max(0.0, float(age)) / 3600.0 if age is not None else None,
                     f"model:{m.get('model_method', '')}" if scored else f"none:{reason}"))
    return rows
```
4. Methods: `get_metric_model_t0s(pod_key) -> dict` (`SELECT metric_name, t0 FROM solo_metric_model WHERE pod_key = ?`, under the lock); `read_metric_ticks(pod_key, metric_name, start_epoch, end_epoch) -> list[dict]` (`[start, end)`, ordered by `tick_epoch`, keys = the 8 columns, `gate_fired` as bool); private `_insert_metric_ticks(pod_key, tick_epoch, metric_ticks)` = `executemany(_METRIC_TICK_UPSERT, [(pod_key, name, float(tick_epoch), p, ess, gate, stale, prov) for (name, p, ess, gate, stale, prov) in metric_ticks])` (caller holds the lock and the open transaction).
5. `record_skipped_tick` (`:583`) and `complete_scored_tick` (`:626`): new **required keyword-only** `metric_ticks: Sequence[tuple]`; call `_insert_metric_ticks` before the final `commit()` (`complete_scored_tick`: after the calibration upsert, inside the existing `try`); `record_skipped_tick` gets the same `try … except BaseException: self._conn.rollback(); raise` it lacks today (an exception must not leave an open write transaction). Docstrings: one paragraph each stating the rows are atomic with the tick.
6. `driver.py`: `:113` → `from solo_mode.state import SoloStateStore, metric_tick_rows`. Immediately after `metrics_out = outcome["metrics"]` (`:1490`): `metric_ticks = metric_tick_rows(_public_metrics(metrics_out), state_store.get_metric_model_t0s(pod_key), tick_end)`; add `metric_ticks=metric_ticks,` to the two `record_skipped_tick(` calls (`:1507`, `:1534`) and to `complete_scored_tick(` (`:1906`). No other driver edit.
Tests, `test_solo_state.py`: `_base_complete_kwargs` (`:655`) gains `metric_ticks=()`; every direct `complete_scored_tick(`/`record_skipped_tick(` call that does not use it (grep; ~10 at HEAD, e.g. `:496 :519 :558 :582 :852 :880 :918 :931 :948 :1132`) gets `metric_ticks=()`. New:
- (a) `metric_tick_rows`: scored+eligible (`model:stl_lite`, `stale_hours = age/3600`); scored+ineligible (`reason "window fill…"` still `model:`); `model stale` with persisted t0 (`gate_fired 1`, `stale_hours (tick−t0)/3600`, `none:model stale`); `model not built` (`0`, NULL, `none:model not built`); `no window data` with a model (`0`, age from t0); negative age clamps to 0.
- (b) round trip + upsert idempotence (same key twice ⇒ 1 row, updated).
- (c) atomicity: bad row `("cpu", .1, 40., None, None, "model:x")` (`gate_fired` None ⇒ `IntegrityError`) on `complete_scored_tick` leaves `has_scored_tick` False, markov absent, 0 metric rows; same on `record_skipped_tick` (marker not advanced); the connection stays usable (next write succeeds).
- (d) migration: file DB → `append_scored_tick` row → close → `DROP TABLE solo_scored_ticks` via plain `sqlite3` → reopen under `caplog` ⇒ table exists, exactly ONE WARNING containing `solo_scored_ticks migration`, 0 rows, `sqlite_master.sql` contains `WITHOUT ROWID`; reopen again ⇒ no new record; fresh DB ⇒ no WARNING.
- (e) restart survival (file DB): ticks over 3 d, 2 pods × 3 metrics, `close()`, new `SoloStateStore` ⇒ `read_metric_ticks` equals what was written.
- (f) disk: 2 pods × 2016 ticks × 11 real metric names (85-char pod keys `ml-components/rtx-4000-test/pipelineml-tester-workload-checkout-api-v1-5d9c8f7b6d-0000N`) through `complete_scored_tick` on a file DB (`details={}`, `depth_ticks=10`): `PRAGMA page_count × page_size / 44,352 rows ≤ 260` (scratch simulation 208 B/row; a rowid table = 358).
Tests, `test_solo_driver.py` (fixture `_seeded(db)`, `_drive`, `_rc`; pattern of `test_solo_throughput.py`: ticks 1-2 are the "no eligible metric" skip, tick 3 is scored):
- (g) drive 3 ticks from `t0` ⇒ 33 rows. cpu: `p_raw` and `ess` not NULL, `gate_fired 0`, `provenance` starts `model:`, `stale_hours == (tick−t0)/3600`. The other 10: `p_raw/ess/stale` NULL, `gate_fired 0`, `none:model not built`. Skip-path (ticks 1-2) and scored-path (tick 3) rows both present.
- (h) gated: `_drive(rt, t0 + dt + T)` (cpu model aged out ⇒ mandatory skip) ⇒ cpu row `gate_fired 1`, `none:model stale`, `p_raw/ess` NULL, `stale_hours ≈ (dt+T)/3600`.
- (i) restart: after (g) `drv._reset_solo_runtime_for_tests()` then `SoloStateStore(db)` ⇒ the same 33 rows (file DB).
Acceptance: baseline suites + `test_solo_driver.py` green; (f) passes; run `/tmp/solo-p6-e/insert_cost.py` (not committed; copy the method of `/tmp/solo-p6-plan/wr_cost.py` but call the real `complete_scored_tick` with `metric_ticks=()` vs 11 rows, 10 pods ×2016 and 1000 pods ×60 preloaded ticks, 3 reps, medians) ⇒ added ≤ 1.0 ms/pod-tick at both sizes, ratio ≤ 3×; record the numbers. Commit: `feat(solo): per-metric solo_scored_ticks written on scored and skipped ticks (SOLO-OPS P6-S2)`.

## S3 — batched TTL sweep primitives + policy (5 files; commit 3; needs S1+S2)
Files: `analyser/solo_mode/window_store.py`, `analyser/solo_mode/state.py`, new `analyser/solo_mode/retention.py`, `analyser/tests/unit/test_solo_window_store.py`, new `analyser/tests/unit/test_solo_retention.py`.
1. `window_store.py` (`import time` if missing; module level, after `open_solo_connection`):
```python
_SWEEPABLE = {"solo_window_points": "ts_epoch", "solo_scored_ticks": "tick_epoch"}  # table -> its time column


def sweep_expired_rows(lock, conn, table, cutoff_epoch, batch_rows, pause_s, sleep=time.sleep) -> int:
    """Delete rows with <ts> < cutoff_epoch stream by stream (pod_key, metric_name), at most batch_rows per
    statement+commit. The lock is held per statement only, never across sleep; returns rows deleted."""
    col = _SWEEPABLE.get(table)
    if col is None:
        raise ValueError(f"table {table!r} is not sweepable")
    q_pod = f"SELECT pod_key FROM {table} WHERE pod_key > ? ORDER BY pod_key LIMIT 1"
    q_met = f"SELECT metric_name FROM {table} WHERE pod_key = ? AND metric_name > ? ORDER BY metric_name LIMIT 1"
    q_del = (f"DELETE FROM {table} WHERE pod_key = ? AND metric_name = ? AND {col} IN (SELECT {col} FROM {table} "
             f"WHERE pod_key = ? AND metric_name = ? AND {col} < ? ORDER BY {col} LIMIT ?)")
    deleted, pod = 0, ""
    while True:
        with lock:
            row = conn.execute(q_pod, (pod,)).fetchone()
        if row is None:
            return deleted
        pod, metric = row[0], ""
        while True:
            with lock:
                row = conn.execute(q_met, (pod, metric)).fetchone()
            if row is None:
                break
            metric = row[0]
            while True:
                with lock:
                    try:
                        n = max(0, conn.execute(q_del, (pod, metric, pod, metric, float(cutoff_epoch), int(batch_rows))).rowcount)
                        conn.commit()
                    except BaseException:
                        conn.rollback()
                        raise
                deleted += n
                if n:
                    sleep(pause_s)
                if n < batch_rows:
                    break
```
   `SoloWindowStore.sweep_expired(self, cutoff_epoch, batch_rows, pause_s, sleep=time.sleep) -> int` = `sweep_expired_rows(self._lock, self._conn, "solo_window_points", …)`. Do NOT touch `_merge_episodes` or `slide_drop`. (Why this shape: M2 — index seeks only, no table scan, no long lock; a global `WHERE ts < ? LIMIT` delete would scan the table under the write lock.)
2. `state.py`: `import time`; `from solo_mode.window_store import open_solo_connection, resolve_db_path, sweep_expired_rows`; method `sweep_expired_scored_ticks(self, cutoff_epoch, batch_rows, pause_s, sleep=time.sleep) -> int` (same, table `"solo_scored_ticks"`).
3. `retention.py` (module docstring: SOLO-OPS P6; lazy `from solo_mode.config import _parse_duration_seconds` inside the function — no import cycle): `@dataclass(frozen=True) RetentionPolicy(raw_points_ttl_s:int, scored_ticks_ttl_s:int, sweep_interval_s:int, batch_rows:int, batch_pause_s:float)`; `retention_policy(solo_cfg)` reads `solo_cfg["persistence"]["retention"]` (`batch_pause_s = sweep_batch_pause_ms / 1000.0`); `next_sweep_epoch(now_epoch, tick_seconds, interval_seconds)`: `half = T/2; k = math.ceil((now + interval − half)/T); return k*T + half` (mid-tick, ≥ now+interval); `sweep_once(stores, policy, now_epoch, *, sleep=time.sleep) -> dict`: for `("raw_points", stores.window.sweep_expired, raw ttl)` then `("scored_ticks", stores.state.sweep_expired_scored_ticks, scored ttl)` call `fn(now_epoch − ttl, policy.batch_rows, policy.batch_pause_s, sleep)` each in its own `try`; on failure `logger.exception` and remember the first exception; always attempt both; `logger.info("solo retention sweep: %s", counts)`; re-raise the remembered exception after both ran; return `{"raw_points": n, "scored_ticks": m}`.
Tests (`test_solo_window_store.py` additions + `test_solo_retention.py`; file DBs):
- (a) only `ts < cutoff` die: stream A 5 expired + 5 live, B all live, C all expired; a row at exactly `cutoff` survives; other streams untouched; returned count exact; second run 0; no `sleep` call when nothing expired.
- (b) batch boundaries with `batch_rows=3`: expired counts 0,1,2,3,4,6,7 in separate streams ⇒ all gone, `sleep` (recorder) called `ceil(n/3)` times per stream.
- (c) lock free during the pause: from inside the `sleep` callback (i) a second thread calls `window.count(...)` and `join(1.0)` finishes, (ii) a second `sqlite3.connect(db, timeout=0.2)` inserts a row successfully.
- (d) unknown table ⇒ `ValueError`; (e) the same cases on `solo_scored_ticks` via `SoloStateStore.sweep_expired_scored_ticks`.
- (f) `retention_policy` from the dev config (missing key ⇒ `KeyError`, no default); `next_sweep_epoch(1_000_000.0, 300, 3600) == 1_003_950.0`; property over 200 random nows: `result >= now+interval` and `result % 300 == 150`.
- (g) `sweep_once(now=1_000_000)`: rows at `now−7d` kept, `now−7d−1` deleted, both tables, counts returned; one table's sweep patched to raise ⇒ the other still ran and the exception propagated.
- (h) **concurrency bound**: window+state stores on one file, 150 k expired rows (30 streams × 5,000, direct `executemany`) + live rows; a thread commits an 11-row `complete_scored_tick` every ~20 ms recording latency while `sweep_once` runs (`batch_rows=2000`, `pause=10 ms`); assert deleted count exact, ≥ 5 writes completed meanwhile, **max write latency < 0.5 s** (measured 7 ms at 1.17 M rows; no-pause control 194 ms), no `OperationalError`.
- (i) restart + sweep: rows written, stores reopened, `sweep_once` ⇒ only expired rows gone.
Acceptance: all green; (h) numbers (max/p99 ms, writes, rows) recorded. Commit: `feat(solo): batched TTL sweep primitives and retention policy (SOLO-OPS P6-S3)`.

## S4 — `SoloRetention` thread wiring (2 files; commit 4; needs S2+S3)
Files: `analyser/solo_mode/driver.py`, `analyser/tests/unit/test_solo_driver.py`.
`start_solo_runtime` (`driver.py:2185`): after the `SoloRuntime` thread starts (`:2217-2218`), before `_STARTED.add`:
```python
    from solo_mode import retention as _retention
    policy = _retention.retention_policy(solo_cfg)

    def _retention_loop() -> None:
        while True:
            now = time.time()
            time.sleep(max(0.0, _retention.next_sweep_epoch(now, T, policy.sweep_interval_s) - now))
            try:
                _retention.sweep_once(get_solo_stores(rt_config), policy, time.time())
            except Exception:
                logger.exception("solo retention sweep failed; retrying next interval.")

    threading.Thread(target=_retention_loop, name="SoloRetention", daemon=True).start()
```
plus one `logger.info("solo retention thread started (interval=%ds, batch=%d rows, pause=%.0f ms).", …)`. No change to `run_solo_runtime_step` (the sweep is never on the tick thread). Test: monkeypatch `drv.threading.Thread` with a recorder (`target, name, daemon` kept, `start()` records, nothing runs): `drv.start_solo_runtime(rt)` is True, started names `["SoloRuntime", "SoloRetention"]`, both `daemon=True`, a second call returns False and starts nothing (autouse fixture resets `_STARTED`). Acceptance: full fast list of the master card green vs the pre-edit baseline (record counts). Commit: `feat(solo): SoloRetention sweep thread started with the solo runtime (SOLO-OPS P6-S4)`.

## S5 — docs (1 file; commit 5)
`markdown/2026-10-09-solo-mode-runtime-cutover.md`: dated addendum `### SOLO-OPS-P6 addendum (2026-11-10): retention + scored-tick durability` (≤ 35 lines) inserted before `## Deviations from a naive reading of the spec` (`:940`): config keys + the 3 load-time rules with deployed numbers; why the raw TTL is a backstop (F1); table columns and the D1-D3 definitions in code terms (incl. limits: proxy for the ESS gate, failing ESS NULL, `provenance` grammar, no backfill); sweep design (own thread, mid-tick, per-stream seeks, ≤ batch per statement, pause outside lock, measured max writer wait 7 ms vs 194 ms without pause); study queries (`SELECT SUM(gate_fired)*300/3600.0 FROM solo_scored_ticks WHERE pod_key=? AND metric_name=? AND tick_epoch>=?` = stale hours; longest run via the `tick_epoch − row_number()*300` island trick); the disk table of the master card and the PVC finding; out-of-scope + the two reopen triggers. Commit: `docs(solo): SOLO-OPS P6 retention and scored-ticks addendum`.

## S6 — OPTIONAL, non-blocking: drop the redundant `idx_solo_window_points_key` (2 files; commit 6)
Files: `analyser/solo_mode/window_store.py`, `analyser/tests/unit/test_solo_window_store.py`. Skip if anything is unclear; P6 is complete without it.
`_init_schema` (`window_store.py:155-160`): remove the `CREATE INDEX IF NOT EXISTS idx_solo_window_points_key …` statement; new `_drop_redundant_index()` called after `_migrate_identity_columns()` in `_init_schema` (`:161`): if `sqlite_master` has `type='index' AND name='idx_solo_window_points_key'` ⇒ `DROP INDEX idx_solo_window_points_key`, commit, `logger.warning("solo_window_points migration: dropped idx_solo_window_points_key (identical to the PRIMARY KEY autoindex); pages move to the free list, the file shrinks only after an offline VACUUM")`. Never `VACUUM`, never `auto_vacuum`. Evidence already on scratch (M1; re-run `/tmp/solo-p6-plan/idx_check.py` + `idx_check2.py`): sizes bit-identical, plans identical, DROP 51 ms on 1.17 M rows. Tests: pre-existing DB with the explicit index ⇒ open drops it (one WARNING, idempotent on re-open, fresh DB never has it); for the five query shapes (`merge_select`, `read_window`, `slide_drop`, `max_ts`, `count` SQL copied from `window_store.py`) `EXPLAIN QUERY PLAN` on a FRESH connection mentions `sqlite_autoindex_solo_window_points_1` and not `idx_solo_window_points_key`; `count/read_window/max_ts/slide_drop` results identical before/after on a seeded stream. Commit: `perf(solo): drop redundant idx_solo_window_points_key (SOLO-OPS P6-S6, optional)`.

## P6-repin — LAB slice (named; after the LAST production commit of P6; lab repo only, production read-only)
Lab `/Users/obenomar/Work/langGraph/appthrust/pipelineml-model-exploratory-work` (`main`, local), `cd reference-model-study`, `PY=.venv/bin/python`. Files (7): `config/reference.yaml`, `tests/test_reference_config.py`, `../markdown/reference-port.md`, `src/refstudy/reference/chain.py`, `tests/parity/prod_runner.py`, `tests/parity/test_p3_chain.py`, `results/a1a-parity.json` (regenerated). Not touched: `used_files` (still 9), `scan.py` pin, anything in production.
0. Preconditions (record in `E-reference-model-study/E-P6-repin.md`): `P6=$(git -C <prod> rev-parse HEAD)` is the last P6 commit; `git -C <prod> status --porcelain -- <the 9 used_files>` empty; `git -C <prod> diff 5bcc7f9..HEAD -- analyser/solo_mode/driver.py` contains ONLY: the import line, the `metric_ticks = …` block after `outcome`, three `metric_ticks=` kwargs, the `SoloRetention` block in `start_solo_runtime` — any hunk in scoring math ⇒ STOP and escalate; `git show HEAD:reference-model-study/results/a1a-parity.json > /tmp/solo-p6-repin/pre.json`.
   Hazard seen 2026-11-10: the lab working tree already shows ` M reference-model-study/results/a1a-parity.json` (a peer's parity run) plus peers' untracked files. The baseline is ALWAYS `git show HEAD:…` (never the working copy); regenerate the JSON in this slice; `git add` only the 7 listed files.
1. Edit: `config/reference.yaml:87` `expected_production_head: <full 40-char P6>`; `tests/test_reference_config.py:78` same literal; `../markdown/reference-port.md:3` `5bcc7f9` → `<P6 short>`; refresh the `driver.py` line-range comments that cite the shifted chain: `chain.py:15,354,496`, `prod_runner.py:13,152`, `test_p3_chain.py:4`, `reference-port.md:15` (`driver.py:1486-1605` → start 1486 unchanged, new end = `1605 + (new line of "candidate = bool(p_simes >= alpha_fuse)" − 1642)`; `driver.py:1509` in `chain.py:496` → new line of the first `float(markov_prev["p_posterior"]) if markov_prev else 0.0`); citations below line 1486 stay.
2. Run: `$PY -m pytest -m "not parity" -q` (same pass count as before); `$PY scripts/run_parity.py --config config/reference.yaml --stage 1`; `… --stage 2` (~2 min). All exit 0.
3. Compare: load `/tmp/solo-p6-repin/pre.json` and the new `results/a1a-parity.json`, drop `provenance` and every `wall_seconds`; remainder must be EQUAL (P0-P4b numbers bit-identical); the new `provenance.head.production == P6`, `blob_ids` changed only for `config.py`, `driver.py`, `configmap.yaml`.
4. Commit (explicit add of the 7 files): `chore(refstudy): re-pin parity to production <P6 short> after SOLO-OPS P6`. Write `E-P6-repin.md` (commands, exit codes, diff summary).
5. Campaign-log line for S to append to `CAMPAIGN-CONTEXT.md` (decisions block; orchestration commits wait for the operator): `- **D-P6-repin (<date>):** production pin moved 5bcc7f9 -> <P6 short> after SOLO-OPS P6 (commits <S1..S5[,S6]>); parity.used_files unchanged (9; P6 touched config.py, driver.py, configmap.yaml); parity stage 1+2 green, a1a-parity.json differs only in provenance/wall_seconds; driver.py line-range comments updated. Any further production commit (incl. the deploy digest-pin) needs another re-pin.`
Acceptance: steps 2-3 as stated; `git status` clean for the 7 files. Hazard: the operator's later `docs(deploy): repin solo-card6 image …` commit moves production HEAD again ⇒ parity red until the next re-pin (cheap, same steps).
