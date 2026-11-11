# E Evidence — A3: package the real flat load (read-only extraction)

- Executor: RefmEA3. Date: 2026-11-09 (run 13:28–13:42 local / 04:28–04:42 UTC).
- Workcard: `omp-workcards/refm-A3.md`. Lab: `pipelineml-model-exploratory-work` (branch `main`).
- Route ports: **14010** (card decision 3). The stale R-A3 14000 tunnel was already killed by S at
  12:2x (supervisor note) — preflight confirmed 14000 empty; all card lines "leave 14000 untouched"
  therefore trivially satisfied; nothing touched.
- All cluster interaction was read-only (HTTP `SELECT` via port-forward + `kubectl get`); no writes,
  no restarts; port-forwards killed by recorded PID only.

## Step 1 — Preflight (literal outputs)

```
$ git -C $LAB status --short          -> (empty)
$ df -h / | tail -1                   -> /dev/disk3s1s1  461G  422G   40G  92% /   (>=5 Gi OK)
$ curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18086/dashboard/  -> 200
$ lsof -nP -iTCP:14010 -sTCP:LISTEN   -> (empty, rc=1)
$ ssh rtx-4000-test "ss -ltn | grep -c ':14010 '" -> 0
$ lsof -nP -iTCP:14000 -sTCP:LISTEN   -> (empty, rc=1)   # stale tunnel already dead
```
Port 14010 free on Mac and host ⇒ used 14010 exactly as written; no YAML endpoint change.

## Step 2 — Code + tests

- Files: `config/data_packaging.yaml`, `src/refstudy/data/{__init__,greptime,package,oracle,loader}.py`,
  `scripts/package_flat_load.py`, `tests/test_data_{greptime,package,oracle,loader}.py`.
- `$PY -m pytest tests/test_data_*.py` → green at commit time (the ingest-lag tests D1/D2 add
  2 to `test_data_oracle` → final 12); `.venv/bin/ruff check src tests scripts` → **All checks
  passed**.
- Commit 1 (see Deviations D6 for the rebase; final hash `b1707f7`):
  `feat(refstudy): add flat-load packaging library, loader and parity-oracle checks`
  — 11 files, all owned paths.

## Step 3 — Live-config snapshot (decision 8)

```
$ ssh rtx-4000-test 'export PATH=$HOME/.local/bin:$PATH; kubectl --context kind-rtx-4000-cluster \
    -n rtx-4000-test get cm pipelineml-anomaly-detector-solo-config \
    -o jsonpath="{.data.detector-common\.yaml}"' > throwaway/solo-config.yaml
$ grep -c '^solo_mode:' throwaway/solo-config.yaml   -> 1
```
Script-side `verify_solo_config` passed: YAML (table, kind, container) == live `solo_mode.metrics`
(11 entries, order-matching). Snapshot: `window {Dt: 2d, dt: 30m, sampling_cadence: 16s}`,
`validity {min_point_fraction: 0.95, counter_block_min_fraction: 0.9, counter_max_gap: 35s}`,
`degraded.mandatory_metrics [container_cpu_usage_seconds_total]`,
`undersampling.boxcar {mode: jumping, over: duration, value: 5m}`.

## Step 4 — Route (recorded PIDs)

```
# host (remote shell PID of the kubectl port-forward):
$ ssh rtx-4000-test 'export PATH=$HOME/.local/bin:$PATH; nohup kubectl --context \
    kind-rtx-4000-cluster -n ml-monitoring port-forward --address 127.0.0.1 \
    svc/greptimedb-monitoring-frontend 14010:4000 >/tmp/refm-a3-fwd.log 2>&1 </dev/null & echo $!'
KUBECTL_PID=2018993
$ ssh rtx-4000-test "ss -ltn | grep ':14010 '" -> LISTEN ... 127.0.0.1:14010
   log: "Forwarding from 127.0.0.1:14010 -> 4000"
# Mac ssh tunnel:
$ ssh -f -N -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
    -L 14010:127.0.0.1:14010 rtx-4000-test
$ lsof -nP -iTCP:14010 -sTCP:LISTEN -> ssh  PID 69074   (Mac ssh PID = 69074)
# Smoke:
$ curl -sS -G http://127.0.0.1:14010/v1/sql --data-urlencode db=public \
    --data-urlencode "sql=SELECT 1"
{"output":[{"records":{"schema":{"column_schemas":[{"name":"Int64(1)","data_type":"Int64"}]},
 "rows":[[1]],"total_rows":1}}],"execution_time_ms":3}
```

## Step 5 — Run

```
$ PYTHONUNBUFFERED=1 .venv/bin/python scripts/package_flat_load.py \
      --config config/data_packaging.yaml 2>&1 | tee throwaway/a3-package.log
EXIT_CODE=0   (successful run wall ≈ 151 s; full log: throwaway/a3-package.log, 282 lines)
```
- Window: `[2026-10-30T08:45:47.911Z .. 2026-11-09T04:29:32.132Z]` = **235.73 h**
  (end = now − end_lag_s 300; late-ingest guard applied).
- **Oracle first** (decision 6): 10 × 7.4 MB docs, each `history_len 288`, ticks 300 s-aligned,
  `fetched_utc 2026-11-09T04:34:56Z` in manifest. Script warned per pod that the ring's last tick
  (`1794198600.0` = 04:30:00Z) sits past `end` — spot-check tick eligibility enforces
  `tick <= end` and `tick - 335 s >= start` (decision 6), so only fully-covered ticks were drawn.
- **Raw (per-file validation, right after each fetch)**: 110/110 files ok. Per-metric (10 pods):
  | metric | rows/pod | dt min–max (s) | mean dt |
  |---|---|---|---|
  | cpu, mem | 51,730–51,955 | 10.001–34.770 | 16.365 |
  | rx_bytes, tx_bytes | 51,798–51,962 | 10.000–35.542 | 16.358 |
  | oom + 6 rare_count | (same windows, identity `n_name=1` in every file) | — | — |
  All within `rows_per_hour [150,300] × 235.73 h = [35,360, 70,719]`; `min_dt ≥ 5 s`,
  `max_dt < 60 s` (60 s = PACKAGING bound, never hit); first/last samples inside
  `edge_slack_s 300`. **CORRECTION (review F6):** `n_dt_gt_counter_max_gap` (35 s = counter
  INVALIDATION law, NOT the packaging bound) is 0 in 102 files but **1 in each of the eight
  `mjnlq` network files** (rx/tx bytes/packets/errors/dropped) — the gap
  `1794162138.037` → `1794162173.579` = **35.542 s**. The earlier "0 in all 110 files" claim was
  wrong; the manifest `files[].n_dt_gt_counter_max_gap` field had the correct values all along.
  The data stay as they are (no discard/resample). Single identity per file
  (`n_name = n_container = 1` — re-proven post-hoc by `scripts/verify_identity.py`, see Review-fix).
- **Grouped-count cross-check**: `cross-check <metric> ok: N pods all rows == Greptime count`
  for all 11 metrics (10 pods each; netns tables report 15 pods in the cluster, our 10 all match).
- **Greptime table min/max**: all 11 tables `1790843359338 .. 1794199016364 ms`
  (2026-10-01T08:29:19Z .. 2026-11-09T04:36:56Z) — full retention, no TTL, as R-A3 §3.1.
- **P3 copy**: `p3 copy ok: 9916 rows -> p3-ticks.jsonl.gz` (= source line count, 9916 at planning).
- **Spot-check** (seed 42, 3 ticks/pod, `rel_tol 1e-9`, 4 continuous metrics, decision 5 laws):
  `max rel diff cpu 0.000e+00 / mem 0.000e+00 / rx_bytes 0.000e+00 / tx_bytes 0.000e+00`.
  Per-metric classification over 10 pods × 3 ticks (30 comparisons each):
  | metric | exact | lag-explained | unexplained |
  |---|---|---|---|
  | cpu (counter) | 28 | 2 | 0 |
  | mem (gauge) | 28 | 2 | 0 |
  | rx_bytes (counter) | 29 | 1 | 0 |
  | tx_bytes (counter) | 29 | 1 | 0 |
  Lag-explained entries (in-block samples held back at scoring time, all = 1):
  b4xkt cpu & mem @ tick 1794122100, mjnlq rx/tx @ 1794134100, mjnlq cpu & mem @ 1794180300.
  For every counter comparison `n_increments`, `first_prev`, `last_stamp` matched
  `block_attribution` (±1e-3 s) by construction of the check.
- **Manifest written last** (`data/packaged/MANIFEST-flat-load.json`), `validation.hard_checks_passed: true`,
  `warmup_rows_skipped: 0`.

## Step 6 — Teardown (literal outputs)

```
$ kill 69074                              # Mac ssh tunnel PID (recorded)
$ ssh rtx-4000-test 'kill 2018993 2>/dev/null; rm -f /tmp/refm-a3-fwd.log; echo remote-killed'
remote-killed
$ lsof -nP -iTCP:14010 -sTCP:LISTEN       -> (empty)
$ pgrep -fl '[s]sh .*-L 14010'            -> (empty, rc=1)
$ ssh rtx-4000-test "pgrep -af '[k]ubectl.*14010:4000'" -> (empty, rc=1)
$ ssh rtx-4000-test "ls /tmp/refm-a3-fwd.log" -> No such file or directory
$ curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18086/dashboard/  -> 200   # supervisor loop untouched
$ lsof -nP -iTCP:14000 -sTCP:LISTEN       -> (empty)   # stale 14000 tunnel untouched (already dead at preflight)
```

## Step 7 — Independent re-check (throwaway/a3-recheck.py, via `load_flat_series`, not committed)

```
files checked: 110
dt stats (s): median=15.910 mean=16.360 min=10.000 max=35.542
samples on a 15 s grid: 340 / 5705839
dt samples: 5705729
sha ok: hcfj7.tx_errors c397772227dd4404...
sha ok: mjnlq.tx_errors 77262387896357dc...
sha ok: vlsl8.rx_dropped 8f1065e1c6f21ca8...
RECHECK_OK
```
Per pair: `len(ts) == manifest rows`, `np.diff(ts) > 0`, burst-window row count (370–396/file)
within band `rows_per_hour.max × 1.75 h = 525` and equal to `manifest.files[].flag_rows`.

## Step 8 — Doc + commit 2

- `markdown/data-packaging.md` (75 lines ≤ 80-line budget; all required sections present:
  contents/paths, loader usage, irregular cadence, units, burst, metric path, ingest lag,
  warm-up, re-extract procedure).
- Commit 2 `6d3c6e0`: `data(refstudy): package real flat load, parity oracle and manifest`
  — exactly `markdown/data-packaging.md` + `reference-model-study/data/packaged/MANIFEST-flat-load.json`.
- `git diff --check` clean before commit.

## Acceptance — observed

1. `ls data/raw/flat-load/*.csv.gz | wc -l` = **110** = `len(manifest.files)`; every sha256
   (110 flat + 10 oracle) equals `shasum -a 256` ("all 120 shas match"); script exit 0,
   `hard_checks_passed: true`; every file `rows == greptime_count`, `n_name == 1`, `n_container == 1`,
   `warmup_rows_skipped == 0`. ✅
2. 10 files `data/raw/oracle/<suffix>.solo.json.gz`, each `history_len 288`, ticks 300 s-aligned,
   `fetched_utc` recorded; `data/raw/p3/p3-ticks.jsonl.gz` rows = 9916 = source line count. ✅
3. `spot_check` in manifest: all 30 comparisons per metric within `rel_tol` (max rel diff 0.0),
   `n_increments/first_prev/last_stamp` included; mem gauge-mean matches (28 exact + 2 lag-explained,
   0 unexplained), counter-law value for mem reported per entry, null-`block_attribution` counts
   recorded (cpu 0, mem 2880, rx 437, tx 466 of 2880); **mem follows the gauge path explicitly
   (`mem_follows_gauge_path: true`)**. ✅
4. `flags[0]` = `burst-2026-11-06` / `recorded burst (detector-side; no metric excursion)`;
   all 110 files hold 370–396 burst-window rows ≤ 525 band. ✅
5. `git check-ignore -v` on one flat-load, one oracle, the p3 file → each prints
   `.gitignore:38:reference-model-study/data/raw/*`. Manifest: plain `git check-ignore` rc=**1**
   (NOT ignored) and `git add` succeeds — functionally as the card requires; note `check-ignore -v`
   itself exits 0 whenever it prints a matching (negation) rule, so the card's literal `rc=1` is
   only observable without `-v` (see D7). `git status --short` lists no `data/raw` path;
   `git ls-files | grep -c MANIFEST-flat-load` = **1**. ✅
6. Step-6 outputs all empty; 18086 = 200. ✅
7. `pytest tests/test_data_*.py tests/test_common_config.py` → **45 passed, 0 skipped**;
   `ruff check src tests scripts` clean; two commits, `git show --stat` only owned paths;
   `git diff --check` clean. ✅

`du -sh data/raw/*`: `40M data/raw/flat-load`, `21M data/raw/oracle`, `156K data/raw/p3` (61M total,
raw + gzipped; flat-load alone 41.3 MB / 5.706 M rows).

## Decisions 4–5 on live data — held

- **Decision 4 (oracle path)**: `history[i].details.metrics[<metric>]` with keys
  `observed/forecast/residual/kind/eligible/block_attribution` — used and confirmed on all 10 live
  docs; top-level `tick`/`window_ready` are dicts as stated.
- **Decision 5 (metric paths)**: `is_counter_metric` suffix-based ⇒ cpu/rx_bytes/tx_bytes counters,
  **mem GAUGE** (settles R-A3 §5.1). Live: mem `block_attribution` null on all 2880/2880
  pod-ticks; cpu emitted 2880/2880; rx_bytes null 437/2880 (15.2 %) and tx_bytes null 466/2880
  (16.2 %) — the "block not aligned" population R-A3 §2.5 expected (~15 %). Counter spot-check
  blocks reproduced `observed`, `n_increments`, `first_prev`, `last_stamp` exactly (rel diff 0.0).

## Deviations

- **D1 — ingest-lag amendment (approved by S, from planner RefmPA1a):** spot-check would fail ~99 %
  of the time against a strict "full raw window == observed" check: the detector scores `observed`
  without the newest 1–3 raw samples on ~17 % of ticks. Implemented exactly as S approved: a
  mismatch is classified **lag-explained** only if the counter block replayed on raw truncated at
  `block_attribution.last_stamp` (mem: in-block mean minus the last 1 sample) reproduces
  `observed` (+ `n_increments/first_prev/last_stamp` ±1e-3 s) within `rel_tol`; any **unexplained**
  mismatch still fails the run (no manifest). Manifest records `counts_per_metric`
  (exact / lag-explained / unexplained) and per-entry lag magnitude (`trailing_samples_held_back`,
  in-block count; observed = 1 for all 6 lag entries). `rel_tol` (1e-9) was NOT loosened. Live
  result: 0 unexplained. **QUALIFICATION (review F6/F3):** the "ingest lag" wording is a STATISTIC
  of the oracle comparison — the ~6 lag cases out of 120 spot-check comparisons are compatible with
  a held-back tail (and, for counters, proven against the detector's own recorded cutoff). It is
  NOT a proven cause for the ~15–16 % null `block_attribution` network population (437/466 of 2880
  pod-ticks), which is a different population that never enters this comparison. For GAUGES the
  match is weaker: the dropped-sample count is searched, not independently observed, so the review
  fix relabels the gauge class to `lag-compatible` (counts unchanged; see Review-fix).
- **D2 — decision-6 tick restriction implemented in `spot_check`** (`t0_s`/`t1_s` args): the oracle
  ring's last tick exceeded `end` on every pod, so eligibility additionally requires
  `tick <= end` and `tick - 300 - 35 >= start` (drawn ticks: 3/pod among fully-covered ticks).
- **D3 — two log-format bugs in `scripts/package_flat_load.py`** (self-inflicted, pre-data):
  first run died with `IndexError: Replacement index 7 out of range` at the per-file log line
  (8 placeholders / 7 args); second run same class of bug in the same line. Fixed the format
  strings (`raw {} {} ok: {} rows, dt {:.3f}..{:.3f}s (mean {:.2f}), file {}`); third run completed.
  No threshold was changed; no data was fetched between the failures and the fix except the
  aborted first two fetch attempts (read-only, harmless).
- **D4 — held-back magnitude correction:** the first manifest recorded `trailing_samples_held_back`
  as the total number of raw samples past `last_stamp` in the *whole* window (4692/1130/3956/3956),
  which is not the lag magnitude. Recomputed as the **in-block** sample count
  `(last_stamp, tick]` = 1 for all four counter entries; manifest `oracle.spot_check` patched in
  place (deterministic re-run: same seed 42, same window, same on-disk files; only the 4
  `trailing_samples_held_back` values changed, verified by diff).
- **D5 — no port change needed:** 14000 was already free at preflight (S killed the stale tunnel
  12:2x); 14010 used as written; no YAML `source.endpoint` change.
- **D6 — commit hygiene:** late fixes (D1/D2/D3/D4 code in `oracle.py`/script/tests) were folded
  into commit 1 via `git rebase -i` (edit commit 1 → amend → continue); final hashes
  **commit 1 = `b1707f7`**, **commit 2 = `6d3c6e0`** (commit 2 amended once more to carry the
  final 75-line doc). A sibling leaf's commit
  (`eb49314` TimesFM-3 MPS/MLX smoke, A2-owned paths) landed between mine and was replayed
  untouched; my two commits contain only owned paths (`git show --name-only` verified).
- **D7 — acceptance 5 literal vs functional:** `git check-ignore -v <manifest>` exits 0 and prints
  the `!...MANIFEST*.json` negation rule (that is how `-v` reports a matched-but-ignored=false rule);
  plain `git check-ignore <manifest>` exits **1** and `git add` of the manifest succeeds — i.e. the
  manifest is NOT ignored, as the card requires. The card's "`rc=1`" is therefore satisfied by the
  non-`-v` form.
- **D8 — R-A3 cause correction (recorded, no code change; qualified per review F6):** R-A3 §2.5
  attributed null `block_attribution` on rx/tx ticks to "trailing sample > 30 s before tick
  boundary". The live spot-check shows the per-tick discrepancy mechanism in the COMPARED ticks is
  compatible with ingest lag (latest 1–3 raw samples not yet in the detector window store at
  scoring time); truncating raw at `block_attribution.last_stamp` reproduces `observed` exactly for
  the counter cases. **Qualification:** this is a statistic of the oracle comparison (6 lag cases /
  120 compared ticks, 4 proven by the recorded cutoff, 2 gauge-compatibility only), NOT a proven
  cause for the ~15–16 % null `block_attribution` network population, which is a different
  population and is never compared here. Noted in `markdown/data-packaging.md`.

## Review-fix (RV-A2-A3 findings F1–F7; executor RefmEA3fix, 2026-11-09)

Applied per finding (details in the commit `fix(refstudy): harden A3 packaging per review
(identity, NaN, read-only SQL, YAML, docs)`):

- **F1 (blocker) — FIXED.** `Series` now carries the REAL distinct identity sets
  (`containers`/`names` frozensets, `n_name`/`n_container` properties); `fetch_series` no longer
  reduces to `next(iter(...))`; `validate_series` raises `ValueError` naming
  `<pod>/<metric> [n_name]` / `[n_container]` when either cardinality != 1; `write_series`
  re-proves single identity before writing. Tests: `test_fetch_validate_rejects_two_names`
  (two non-empty names, alternating), `test_fetch_validate_rejects_two_containers` (two
  containers, alternating rows), `test_fetch_validate_single_identity_passes_and_writes_uniform`,
  `test_write_series_rejects_multi_identity` — all green.
- **F1 (existing export re-verified) — PASSED.** `scripts/verify_identity.py` (YAML-driven,
  reuses `GreptimeClient`): for every one of the 110 pod×metric pairs, read-only
  `SELECT count(DISTINCT name) AS n_name, count(DISTINCT container) AS n_container, count(*) AS n`
  with EXACTLY the manifest's packaging predicate and window. Run once via the documented route
  (host `kubectl port-forward` svc/greptimedb-monitoring-frontend 14010:4000, PID 2202293; Mac
  `ssh -L 14010`, PID 2551; sequential; both killed by recorded PID). Pre-check: all 110 flat +
  10 oracle sha256 still match the manifest (files byte-unchanged). Result, literal tail of
  `throwaway/a3-verify-identity.log`:

```text
2026-11-09 15:19:10.483 | INFO | assert_files_unchanged:71 - file integrity ok: 110 flat + 10 oracle sha256 match the manifest
...
2026-11-09 15:19:20.383 | INFO | main:121 - identity qsv2m tx_dropped: n_name=1 n_container=1 n=51897 manifest_rows=51897 ok
2026-11-09 15:19:20.486 | INFO | main:163 - identity check PASSED: 110/110 pairs all_single; recorded in manifest oracle.identity_check (no data re-fetched)
EXIT_CODE=0
```

  All 110 pairs: `n_name=1 n_container=1` and `n == manifest rows` (spot-checked first/last rows
  above; every per-pair line in the log is `ok`). No data file was re-fetched; the 120 sha256
  values in the manifest are unchanged. Recorded in the manifest as a new
  `oracle.identity_check` block: `checked_utc 2026-11-09T06:19:20Z`, `all_single: true`,
  `n_pairs: 110`, per-file `n_name/n_container/n/manifest_rows/ok`. Teardown (PID-only):
  `kill 2551`; `ssh rtx-4000-test 'kill 2202293; rm -f /tmp/refm-a3-verify-fwd.log'` →
  `lsof -nP -iTCP:14010 -sTCP:LISTEN` empty (rc=1), `pgrep -fl '[s]sh .*-L 14010'` empty (rc=1),
  host `pgrep -af '[k]ubectl.*14010:4000'` empty (rc=1), host log removed,
  `curl 18086/dashboard/` → **200** (supervisor loop untouched), 14000 still empty.
- **F2 — FIXED.** `oracle.py`: non-finite `observed` → `SpotCheckError` (fail closed) via
  `_finite`; `_rel_diff` returns `+inf` (never NaN/0) for non-finite operands;
  `_counter_reproduces` rejects non-finite mine/observed and non-finite
  `n_increments`/`first_prev`/`last_stamp`; gauge branch checks reproduced value finiteness and
  the searched mean finiteness. Tests: NaN and Infinity observed on the counter law, NaN observed
  on the gauge law, NaN `last_stamp` attribution (fails UNEXPLAINED, never silently truncates),
  plus `_rel_diff` fail-closed unit test — all green.
- **F3 — FIXED (relabel only, heuristic unchanged).** Gauge class renamed
  `lag-explained` → `lag-compatible` (code, manifest key, tests, docs): the dropped-sample count
  is searched, not independently observed, so it records an ambiguity, not proven parity/cause.
  The counter replay keeps `lag-explained` — it replays at the oracle's RECORDED
  `last_stamp` with value + `n_increments` + `first_prev` + `last_stamp`, which the docstring and
  docs now state explicitly as the stronger, independent-cutoff form. Manifest
  `oracle.spot_check` regenerated from the saved data only (deterministic, seed 42, same window):
  counts verified UNCHANGED — cpu 28/2/0, mem 28/2/0 (now under `lag-compatible`), rx 29/1/0,
  tx 29/1/0; max rel diff 0.0; all 120 data-file sha256 asserted unchanged before writing;
  `git diff` on the manifest shows only the 3 label lines. New test
  `test_spot_check_gauge_wrong_boundary_is_not_exact`: an independently computed wrong-boundary
  gauge oracle (all-but-newest mean, no lag evidence) is NOT classed `exact` (it lands in
  `lag-compatible`; 2 of 3 mem comparisons stay exact).
- **F4 — FIXED.** `GreptimeClient.query` now runs `_assert_single_select` BEFORE opening the URL:
  first word must be `SELECT`; any `;` rejected; embedded DELETE/INSERT/UPDATE/DROP/ALTER/CREATE/
  TRUNCATE/COPY rejected (comment tricks included). Clear `GreptimeError` messages. Doc states the
  guarantee honestly: "client refuses non-SELECT; not a database permission". Tests: a captured
  `urlopen` asserting the opener is NOT called for `DELETE FROM "synthetic_table"`; 13
  parametrized forbidden forms; a legitimate SELECT reaches the transport (dead-port error proves
  it passed the gate).
- **F5 — FIXED.** YAML: `spot_check.max_lag_samples: 3` added; `spot_check.law` now REQUIRED for
  every continuous metric, value in {gauge, counter}, no `.get(...)` fallback anywhere in
  `oracle.py`/`package.py`/script. The hardcoded `35.0` eligibility bound in `spot_check` and the
  script's ring warning now use `validation.counter_max_gap_s`; the `(1,2,3)` lag search uses
  `max_lag_samples`. Tests: missing `spot_check.law.cpu` names the key; mistyped law value
  rejected; law for a non-continuous metric rejected; `max_lag_samples` missing names the key;
  non-default `counter_max_gap_s` (34.0) loads and is used; a 14 s bound makes the synthetic
  payload UNEXPLAINED (proves the bound is the configured value, not a constant); a configured
  gauge law on the counter-suffixed cpu table is honoured (no suffix fallback).
- **F6/F7 — FIXED.** `markdown/data-packaging.md` and this file now say there IS one >35 s gap in
  each of the eight `mjnlq` network files (35.542 s, `1794162138.037`→`1794162173.579`;
  `n_dt_gt_counter_max_gap = 1` in exactly those 8 files, 0 in the other 102), distinguish the
  60 s packaging bound from the 35 s counter-invalidation law, keep the data as-is, qualify the
  "~17 % ingest lag" wording as a statistic of the oracle comparison (not a proven cause for the
  null-attribution population), and use the correct log line count (282, not 148).
  `E-A2-live.md`: `eb49314` named as the final live commit (`97de27d` kept only as the
  explicitly historical pre-rebase hash); time labels now consistently local +0900 with the
  manifest refresh `2026-11-09T04:31:58+00:00` = 13:31:58 local.

### Gates (literal)

```text
$ .venv/bin/python -m pytest tests/test_data_*.py tests/test_common_config.py -q -o addopts=""
77 passed in 7.31s          # 0 skipped (was 45 at original delivery; +32 new tests)
$ .venv/bin/ruff check src/refstudy/data scripts/package_flat_load.py scripts/verify_identity.py \
      tests/test_data_greptime.py tests/test_data_package.py tests/test_data_oracle.py \
      tests/test_data_loader.py
All checks passed!
$ git diff --check          -> (clean)
$ git status --short        -> only A3-owned paths modified + scripts/verify_identity.py untracked->committed;
                               sibling leaves' untracked files (config/reference.yaml,
                               src/refstudy/reference/, tests/test_reference_*.py) untouched
```

Commit: **`d93d228`** `fix(refstudy): harden A3 packaging per review (identity, NaN, read-only
SQL, YAML, docs)` — 11 files, all owned paths (`git show --stat`: the 10 modified owned files +
new `scripts/verify_identity.py`). No push; explicit `git add <paths>` only.

Deviations from the fix list: none material. (a) `markdown/data-packaging.md` grew from 75 to
96 lines to carry the required F4/F5/F6 corrections + the F1 post-hoc identity proof; the original
"≤80 lines" was a size target for the first draft, and every added line maps to a required
finding. (b) The `spot_check` gauge per-entry field keeps the name `gauge_samples_held_back`
(only the class value changed, `lag-compatible`), keeping the regenerated manifest diff to the
3 label lines.
