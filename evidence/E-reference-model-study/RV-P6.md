# RV Review — SOLO-OPS-P6

- Date: 2026-11-11
- Advisory disposition: **rejected** — **1 blocker**, 5 should-fix findings, 0 nits. The Supervisor decides action.
- Reviewed production range: `5bcc7f9..7e4014e6874e81c0934c2dbb7670b7eea207bc18` (all six commits).
- Production and lab were read-only; only this review artifact was written. No cluster, Docker, deployment, network, or dashboard-route test was used.
- Production paths below are relative to `pipelineml-anomaly-detector/`; evidence paths are relative to `agent-orchestration/`.

## Per-item dispositions (assignment items 1–10)

| Item | Disposition | Result |
|---|---|---|
| 1. Master RV checklist | rejected | Six checklist rows evaluated separately below; writer/retry durability fails F1. |
| 2. D1–D3 vs code/card/addendum | accepted_with_findings | Field mapping follows the prescribed implementation; the addendum overstates snapshot-age and gate-attribution guarantees (F3). |
| 3. Transactions, rollback, locks, retry upsert | rejected | Atomic transactions and rollback are sound; a delayed skipped-tick retry erases an original gated observation (F1). |
| 4. Sweep and scheduling/thread | accepted_with_findings | Finite-backlog batching works; empty keys are skipped (F2), scheduling claims need qualification (F5). |
| 5. Config | accepted | Required keys, boolean rejection, exact bounds, shipped YAML equality, and header warning checked. |
| 6. S6 index and downgrade | accepted | Equivalent PK autoindex remains; no runtime named-index dependency; migration/result/plan tests pass. |
| 7. Disk/PVC and numerical claims | accepted_with_findings | Recomputed budgets and independently reproduced performance bounds; documentation omits post-S6 capacity (F6). |
| 8. Test quality and flake risk | accepted_with_findings | Substantial behavioral coverage, but the lock-free-pause assertion is ineffective (F4); latency gate is host-sensitive. |
| 9. Allowed hunks and unrelated paths | accepted | Exactly the allowed production files/hunks; protected modules unchanged; unrelated paths absent from all six commits. |
| 10. Role provenance and reproduced evidence | accepted | Content-only check: no D15-type deviation visible; 293 tests reproduced. Commit content cannot establish the actual execution model's identity. |

### Master card RV checklist, item by item (`solo-ops-P6.md:70-75`)

| Card line | Disposition | Specific check |
|---|---|---|
| 70 | accepted | Commit-by-commit file lists match S1–S6; no dependency change. Driver diff has only import, metric-row block, three kwargs, retention thread. `scan.py`, root `analyser/exporter.py`, root `analyser/api_layer.py`, and `_merge_episodes` unchanged. |
| 71 | accepted | Seven required retention keys; unknown-key rejection; cross-rule boundary tests; both YAMLs match; ConfigMap line 12 contains the promised new-image/old-image warning. |
| 72 | rejected | Both tick paths use the required kwarg and one transaction; rollback, `WITHOUT ROWID`, and no secondary index verified. Retry durability and prose caveats fail F1/F3. |
| 73 | accepted_with_findings | Per-stream seeks, bounded deletes, per-statement locks, external pauses, daemon, cutoff/batch tests, and concurrency pass. F2/F4/F5 qualify completeness. |
| 74 | accepted_with_findings | Insert/disk bounds reproduced; PVC limitation disclosed. E-P6 reports the pre-S6 summary but not the requested complete pre/post-S6 disk table (F6). |
| 75 | accepted | Nine used files retained; re-pin recorded. Independently compared parity JSON bodies and provenance; stage execution evidence is the peer's, not an RV rerun. |

### Slice dispositions

S1 `43b31b4`: **accepted**; S2 `52197c3`: **rejected** (F1); S3 `a29efbf`: **accepted_with_findings** (F2/F5); S4 `9266dbf`: **accepted_with_findings** (F5); S5 `5e435a0`: **accepted_with_findings** (F3/F5/F6); S6 `7e4014e`: **accepted**.

## Findings

### F1 — blocker — A delayed skipped-tick retry overwrites durable gate history

- Locations: `analyser/solo_mode/state.py:74-76`; `analyser/solo_mode/driver.py:1472-1476,1494-1495`; supporting test `analyser/tests/unit/test_solo_state.py:1279-1292`.
- The skip dedupe marker remembers only the latest advanced tick. After another tick advances that marker, replaying the older skipped tick re-scores it. The unconditional upsert replaces all five measurement fields, including `gate_fired` and provenance. Individual store locks serialize SQL, not the request's dedupe/score/write sequence; overlapping requests also have a check-then-write race.
- Independently reproduced with real `_seeded`/`_drive` helpers and persisted CPU snapshots: process tick `1699999200` against a stale snapshot; publish the fresh snapshot; process `t0+T`; replay `t0`. Original CPU row: `gate_fired=True`, `p_raw=NULL`, `stale_hours=0.5`, `none:model stale`. After replay: `gate_fired=False`, `p_raw=0.7739463601532568`, `stale_hours=0`, `model:stl_lite`. Both requests completed normally.
- Thus `SUM(gate_fired)` loses a real observed stale tick, contrary to D4's “retried/deduped ticks write nothing new.” This extends a pre-existing latest-only skip-marker weakness into the new sole durable per-metric history. The new upsert test actually expects a gated row to become ungated; it proves uniqueness, not retry immutability.
- Concrete fix: persist/reuse a per-(pod,tick) processed outcome for the retained history horizon and serialize/recheck dedupe through tick completion, so already-processed ticks never reach the measurement upsert. Preserve original committed measurements; an uncommitted failed transaction remains retryable. Add deterministic delayed-skip-retry and overlapping-request regressions. Merely making `gate_fired` sticky would not preserve the original observation or other tick state.

### F2 — should-fix — Empty-string seek sentinels omit valid stored streams

- Location: `analyser/solo_mode/window_store.py:117-127` (shared by both table sweeps).
- `pod_key > ''` excludes pod key `''`; each pod's `metric_name > ''` excludes metric name `''`. Both schemas allow these values and store APIs do not reject them. Ordinary production pod keys/canonical metrics are nonempty, so this is not a demonstrated deployed-stream leak.
- Independent in-memory probe seeded six expired streams, including `('', 'cpu')`, `('pod', '')`, mixed-case ASCII, and Unicode. Sweep deleted four and left exactly the two empty-key streams. This is omission, not a collation-order loop.
- Concrete fix: use a first-seek query without a lower bound, then strict `>` seeks thereafter (for both key levels). Add empty-pod/empty-metric, Unicode, and mixed-case cases on both table wrappers; retain index seeks rather than a table scan.

### F3 — should-fix — D1/D2 documentation promises more than these fields establish

- Locations: `markdown/2026-10-09-solo-mode-runtime-cutover.md:946`; `analyser/solo_mode/state.py:85-93`; master card `evidence/omp-workcards/solo-ops-P6.md:28-29` also needs clarification.
- Code prioritizes scoring-snapshot `model_age_seconds`; only absent age falls back to the separately queried persisted model t0. Therefore a scored row is not necessarily the age of the newest model persisted when rows are assembled. Async publication may interleave between scoring and the fallback query. Probe: age 1200 seconds plus newly persisted t0 equal to the tick produces `stale_hours=1/3`, not zero; future fallback t0 clamps to zero, even with `gate_fired=1`.
- The addendum omits the card's counter-representation/policy `model stale` false positives (`driver.py:846,1074`). Build lag and an ESS rejection can have the same `none:model stale` provenance and age; those fields do not guarantee separation or exact cause attribution.
- Concrete fix: document “scoring-snapshot age when present; otherwise age from a post-score persisted-t0 lookup; clamp at zero; NULL when neither age source exists.” List both freshness and policy/build-lag proxy limitations, remove guaranteed separability, and distinguish age-on-a-row from aggregate `SUM(gate_fired)*T/3600`. Add an age-precedence/publication-interleaving regression if stronger snapshot consistency is intended.

### F4 — should-fix — The lock-free-pause test's join assertion is vacuous

- Location: `analyser/tests/unit/test_solo_window_store.py:721-724,738-740`.
- `Thread.join(timeout)` returns `None` whether the worker completed or timed out. The reader-result assertion is after the entire sweep returns, when a mistakenly retained lock may already have been released. The second-connection write proves no SQLite write transaction remains, but not release of this store's Python RLock.
- Concrete fix: call `join(1.0)`, then assert `not t.is_alive()` and the expected reader result inside `pause_hook`, before returning to the sweep. An Event signaled by the reader is another deterministic completion assertion. Keep the independent-connection write assertion too.

### F5 — should-fix — Scheduling documentation overstates cadence and non-overlap

- Locations: `analyser/solo_mode/retention.py:18-20,83-95`; `analyser/solo_mode/driver.py:2234-2237`; `markdown/2026-10-09-solo-mode-runtime-cutover.md:948`.
- Implemented `ceil((now+interval)/T)*T+T/2` meets the card's explicit sample `1003950` and the tested lower-bound/midpoint properties. It deliberately is not the card formula or the first eligible midpoint. At `now=150,T=300,interval=3600`, it returns 4050, not 3750; an instantaneous sweep repeatedly started at midpoints has a 3900-second (65-minute) cadence, not exactly one hour.
- A midpoint start cannot guarantee that all batches/pauses never cross a scoring boundary. A large backlog, ordinary wake delay, or a wall-clock jump can invalidate that claim. No deadline/boundary avoidance exists inside the sweep.
- Concrete fix: describe a minimum interval plus conservative midpoint rounding, not exact hourly cadence/first-midpoint/non-overlap. Record the formula deviation in the card/gate and add a repeated-midpoint/rounding-upper-bound test (the current exact sample plus seeded properties pin only part of the intended contract). If strict non-overlap is required, obtain a revised workcard before changing implementation scope.

### F6 — should-fix — Disk guidance was not refreshed after optional S6 landed

- Locations: `markdown/2026-10-09-solo-mode-runtime-cutover.md:952`; `evidence/E-reference-model-study/E-P6.md:618-629,652-671`; master budget `evidence/omp-workcards/solo-ops-P6.md:49-55`.
- Addendum still gives only the pre-S6 76-pod/70-GB figures and says 1000 pods “needs ≥70 GB regardless.” The card's post-S6 model is approximately 52 GB/1000 pods and 103 pods/5 GiB. Seventy GB can be a conservative provisioning recommendation, not the post-S6 minimum. E-P6 gives a summary rather than the requested full budget table.
- Concrete fix: include pre- and post-S6 columns in the addendum/evidence, label capacity as an active-stream projection with WAL/free-space/headroom exclusions, and distinguish allocated file size from reusable freed index pages. Preserve the operator sizing warning; do not imply index drop shrinks the existing file.

## Independent execution and numerical evidence

All production commands used cwd `analyser/`, `/tmp/solo-p3-venv/bin/python`, and `PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared`.

```text
python -m pytest tests/unit/test_solo_driver.py tests/unit/test_solo_state.py \
  tests/unit/test_solo_window_store.py tests/unit/test_solo_mode_config.py \
  tests/unit/test_solo_retention.py -q
EXIT 0: 293 passed in 60.55s.
Breakdown: driver 57; state 44; window 43; config 142; retention 7.
Four non-driver suites = 236; total = 57 + 236 = 293.

python -m pytest \
  tests/unit/test_solo_state.py::test_p6_scored_ticks_disk_budget_bytes_per_row \
  tests/unit/test_solo_retention.py::test_sweep_concurrent_writer_latency_bound -q -s
EXIT 0: 2 passed in 7.46s.
p6-disk: 44352 rows, page_size=4096, page_count=2245, 207.3 B/row.
p6-conc: max 7.4 ms, p99 4.5 ms, median 0.2 ms, 232 writes,
         300000 rows deleted (150000 raw + 150000 scored).
```

- Reused inspected scratch benchmark `/tmp/solo-p6-e/insert_cost.py` via its `run()` function on NEW RV scratch SQLite paths, not E's files: EXIT 0. Ten pods ×2016: 221760 rows, WITH median 0.152 ms, WITHOUT 0.041 ms, added **0.111 ms**. Thousand pods ×60: 660000 rows, WITH 0.155 ms, WITHOUT 0.041 ms, added **0.114 ms**; unrounded ratio **1.0253**. Both ≤1 ms and ratio ≤3. This reproduces the bounds, not identical wall timings.
- E's reported added-time ratio recomputes as `0.169/0.158=1.06962`. Printed `0.215−0.056=0.159` differs by 0.001 ms from E's 0.158; independently rounded medians can explain that, not a failed bound.
- Recomputed from the card/E numbers: `2.5*(172800+43200+300)=540750 s`; `2*288*300=172800 s`; `7*86400/300*11=22176 rows/pod-week`; `205*22176=4546080 B=4.54608 MB`; `2245*4096/44352=207.33045 B/row`; `1−205/358=42.7374%` byte saving.
- Pre-S6 per-pod estimate: `61.6+3.7+4.54608=69.84608 MB`; table fraction `4.54608/69.84608=6.5087%`. Post-S6: `43.7+3.7+4.54608=51.94608 MB`.

| Pods | Scored 7d GB | Total pre-S6 GB | Total post-S6 GB |
|---:|---:|---:|---:|
| 10 | 0.04546 | 0.69846 | 0.51946 |
| 100 | 0.45461 | 6.98461 | 5.19461 |
| 1000 | 4.54608 | 69.84608 | 51.94608 |

- `5 GiB=5.36870912 GB`: projected capacity 76.8649 pods pre-S6 / 103.3516 post-S6, before operational headroom. These are arithmetic projections of the card's observed raw footprint, not new live/PVC measurements. Raw history remains the binding term; 5 GiB is not a 1000-pod volume.

## Technical checks and limits

- **D1/D3:** `state.py:85-93` implements exactly `p is None and reason == 'model stale'`; pre-first-model alone is not gated. p is per-metric, ESS is NULL for any unscored metric, provenance uses the model/none prefixes. Age fallback, nonnegative clamp, and absent-model NULL exercised by units and independent probes. A gated metric need not imply the whole pod was skipped.
- **Atomicity:** `state.py:699-730,897-1017` holds one store RLock through markov/ring/calibration/metric writes and the single commit. `_insert_metric_ticks` has no commit. All write-path exceptions roll back. No P6 path commits metric rows separately or leaves its failed write transaction open.
- Additional populated-state probe: write tick 100 with ring depth 1, then tick 200 with a valid metric row followed by a NOT NULL-invalid row. Observed verbatim `IntegrityError NOT NULL constraint failed: solo_scored_ticks.gate_fired`; old ring restored, markov tick and calibration updated_at remained 100, no tick-200 metric row, `in_transaction=False`. Skip-path valid-then-invalid probe likewise left zero metric rows, no marker, and `in_transaction=False`.
- **Sweep:** both keys/time columns use default SQLite BINARY collation; WHERE `>` and ORDER BY agree. Mixed-case/Unicode order is safe. DELETE's IN subquery has a unique timestamp within each (pod,metric), so affected rows ≤batch; Python SQLite rowcount is the direct DELETE count, not the subselect count. Passed 0/1/B−1/B/B+1/3B boundary, exact-cutoff, idempotence, and pause-count cases exercise this behavior.
- Every SELECT/DELETE is separately locked; DELETE+commit/rollback completes before the pause. A full B-row batch correctly performs another delete, eventually observing zero for a finite backlog; it does not repeat the same rows. [INFERENCE] Unbounded concurrent reinsertion of expired rows can keep the inner loop alive indefinitely; there is no snapshot/work budget. Ordinary fresh scored writes are above the fixed cutoff, and the tested finite backlog drained completely.
- **Schedule/thread:** conservative midpoint rounding is acceptable for the stated low-frequency/minimum-interval objective, subject to F5's contract clarification. The seeded 200-case test plus exact sample pins midpoint and `>=now+interval`, not earliest-slot or repeat cadence. `SoloRetention` is a separate daemon; both tables are attempted on ordinary failure, then the error is logged and the next interval retried. Behavioral thread-target testing supplements the wiring test.
- [INFERENCE] Scheduling/cutoffs use `time.time()`, while `sleep` is a relative wait: a wall-time jump during sleep does not recompute the pending wake. Forward jumps advance the next cutoff, backward jumps delay expiry; the wake can cease to be mid-tick. The following iteration realigns from current wall time. Restart forgets schedule state and waits a full interval plus rounding before its first sweep; no startup catch-up occurs.
- **Config:** independently exercised raw TTL 540750 accepted / 540749 rejected, scored TTL 172800 /172799, sweep 300 /299 and 604800 /604801, boolean rows/pause/safety rejection, NaN/infinity safety rejection, and batch rows/pause=1 acceptance. Errors came from the real validator. Seven-key missing/unknown/type/YAML equality cases passed in the 142-test config suite. Positive integer helper excludes bool and floats; finite numeric helper excludes bool and non-finite values.
- **S6:** all query shapes still have the same PK prefix/time ordering, including inclusive/exclusive read ranges, exact lookup, known-provenance filtering, and new sweep seeks. No runtime `INDEXED BY` dependency found. Fresh-connection plan and before/after result/migration tests passed. The E scratch “after DROP” cached plan names are not independent proof; its fresh-connection follow-up and the tests address that cache issue.
- **Test discipline:** real SQLite/file restart, real scoring paths, constraint-induced rollback, seeded data/randomness, and actual invariants dominate the new tests. Thread wiring alone is an echo test, but the companion invokes the target and checks error isolation. Gated-driver restart is covered at store level plus the driver write/read path, rather than a separate gated-driver-reset test. The latency test's 500 ms limit is ~67.6× this run's 7.4 ms maximum; generous locally, not deterministic on a machine descheduled >500 ms. Keep the specified bound on a controlled runner and retain structural lock/transaction tests; do not weaken it to conceal a failure. F4 needs repair regardless.

## Scope, parity, provenance, and operator handoff

- Inspected all six commits' file lists and full production-code diff. Exactly 14 allowed files changed. The requested `git diff 5bcc7f9..HEAD -- analyser/solo_mode/{driver.py,scan.py,exporter.py,api_layer.py}` showed only allowed driver hunks. Since exporter/API actually live at analyser root, also compared those real paths: empty diff, as for `solo_mode/scan.py`. `_merge_episodes` and `slide_drop` have no changed body.
- Observed unrelated tree state remained ` M AGENTS.md`, `?? analyser/agent-orchestration/`, `?? markdown/2026-11-06-solo-dashboard-operations-report.md`; none appears in any of the six commits. No new dependency or scoring-math hunk.
- **Role provenance:** commit content/messages show the six prescribed slices, no substituted implementation path or D15-type deviation. They have the same normal author/committer and no model identity/trailers. Therefore actual execution-role model identity is not independently inferable from commits; no stronger provenance claim is made.
- **Parity:** read `E-P6-repin.md:37-52,60-67`: peer reports 762 non-parity tests before/after, stage 1 and 2 exit 0, lab commit `3f97c8e5574fc16bc5ec4467f2f0c37bf18cc001`. RV did not rerun lab suites. RV independently parsed `/tmp/solo-p6-repin/pre.json` and regenerated `results/a1a-parity.json`: equal after removing provenance and all `*wall_seconds`; nine blob keys unchanged; only config.py/driver.py/configmap.yaml blobs differ; production pin is full `7e4014e…`, shared head unchanged. Campaign-log insertion is the Supervisor's, not RV's edit.
- **Deployment requires operator action:** build/publish the P6 image, update its deployment digest, apply the retention-bearing ConfigMap, roll/restart, and size the PVC for actual pod/raw-history load plus WAL/headroom. Code alone has not deployed anything. A new image with old ConfigMap fails validation. Schema creation/index drop are automatic on DB open, not a manual SQL migration; 10 pods do not imply a mandatory PVC resize, while 1000 do. No live VACUUM is part of this change.
- **Rollback [INFERENCE from inspected old/new code]:** restore the previous image/digest; the new retention keys may remain because old images ignore them. The extra scored table is additive and can remain. Old window-store initialization recreates the redundant index (startup I/O/space cost); old code neither writes the new history nor runs its TTL sweep. New code on an old DB creates the table and drops the redundant index automatically. Neither image rollback nor index recreation restores TTL-deleted rows, and there is no history backfill. Preserve/restore a suitable DB backup if deleted data must be recovered. A later deployment-pin production commit requires another lab re-pin.

## Disposition rationale

The six commits largely implement the prescribed design and reproduce its numerical gates, but passing 293 tests does not protect the core durable-history invariant: an already-observed gated tick can be rewritten by a legitimate delayed retry. F1 requires a Supervisor decision/fix before promotion; the other five findings are bounded correctness/test/documentation repairs, not style preferences. No production or lab fix was made by RV.
