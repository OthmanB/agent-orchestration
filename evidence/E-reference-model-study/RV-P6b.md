# RV re-review — SOLO-OPS-P6 fixes A/B/C

- Date: 2026-11-11. Advisory disposition: **accepted_with_findings**; **0 blockers, 3 should-fix, 1 nit**. The Supervisor decides action.
- Independently verified production HEAD: **`e30ddb07194d6f60e4116d1d7899e83f03f45b0d`**.
- Reviewed `163506f56eea6aa6204441f609ef9a79aad074fc`, `197a122f549b0a25c0099b12bb3c2898c746a7e8`, `e30ddb07194d6f60e4116d1d7899e83f03f45b0d` against RV-P6 F1–F6, master-card corrections :83–88, D-S13, and E-P6 FIX-A/B/C.
- Production/lab source was read-only; only this artifact was written. No network, cluster, Docker, deployment, or dashboard-route test. Lab repin/parity is the concurrent executor's separate assignment, not claimed here.
- Production references below are relative to `pipelineml-anomaly-detector/`; evidence references are relative to `agent-orchestration/`.

## Per-finding dispositions

| Finding | Disposition | Independent judgment |
|---|---|---|
| F1 | **closed_with_residual** | SQL now preserves each retained key's first observation. Real delayed-retry regression passes. Pre-existing pod-state replay debt remains, explicitly accepted by S; see exact consequences below. |
| F2 | **closed_with_residual** | Both implementations sweep actual empty pod AND metric keys and terminate in independent probes. Committed scored-table test never seeds an empty metric (R1); “never a table scan” is literally false but no full scan occurs (R2). |
| F3 | **closed** | Snapshot-age precedence, post-score fallback/publication caveat, clamp/NULL, proxy ambiguity and row-age versus gate-duration distinction now match code. |
| F4 | **closed** | Reader liveness AND result asserted inside pause, before sweep resumes; independent-connection write retained. Recorded negative control fails at the intended assertion. |
| F5 | **closed_with_residual** | Minimum cadence and lack of boundary-exclusion guarantee corrected; implementation unchanged. New docstring still gives a false rounding upper bound (R3). |
| F6 | **closed_with_residual** | Pre/post-S6 capacity and free-list/not-file-shrink caveat corrected. Required full evidence budget matrix still absent and 6.5% needs a pre-S6 qualifier (R4). |

## Independent execution

Command, cwd `analyser/` (cache/bytecode writes disabled):
```text
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared \
 /tmp/solo-p3-venv/bin/python -m pytest -p no:cacheprovider \
 tests/unit/test_solo_state.py tests/unit/test_solo_window_store.py \
 tests/unit/test_solo_mode_config.py tests/unit/test_solo_retention.py \
 tests/unit/test_solo_driver.py -q
pytest: 300 passed in 102.86s (0:01:42)
```
Completed normally; raw output `artifact://4704`. Actual breakdown: **47 state + 45 window + 142 config + 8 retention = 242; + 58 driver = 300**. The sequence is 293 original → 296 FIX-A → 298 FIX-B → **300 FIX-C**, not 298 at final HEAD.

## F1: caller contract, regression, transactions, accepted debt

- Exhaustive production caller search found only the two skip branches (`driver.py:1513,1541`) and one scored branch (`:1914`); both state methods call the one SQL writer (`state.py:762,1059`, `_METRIC_TICK_INSERT` :77–81). No production correction/backfill API needs replacement semantics. `driver.py:1441–1484` already intends deduplication of processed ticks, not refreshed answers for the same timestamp.
- A skipped tick CAN later have genuine data/a fresh model and score on a delayed replay; this does **not** make replacement correct under S's revised observation-history contract. The original missing-data/ESS-proxy/gated observation remains unchanged, including NULL p/ESS, original age and provenance. Thus gate totals count the original observation, not an eventually rescored historical truth; the per-metric record can disagree with the later pod response/details. An ESS-proxy row later contradicted by successful scoring remains the first observation deliberately. If eventual corrected history were required, this policy would be wrong, but neither current caller contract nor the amended card requires that.
- Driver regression `test_solo_driver.py:5316–5413` really reaches delayed replay: stale-boundary mandatory skip; real `build_one` fresh snapshot publication; a subsequent scored tick advances the marker; old tick returns a non-deduplicated scored result; original complete CPU row/count compared. It does not merely reinsert identical tuples. E-P6 :861–888's recorded old-SQL control fails at that final comparison with **all five fields changed** (gate, p, ESS, age, provenance): convincing causal negative control. This review ran the current regression within the 58-driver suite, not the historical control again.
- `state.py:738–769,947–1067`: same lock, transaction, single commit, and whole-transaction rollback. Targeted PK conflict handling does not ignore NOT NULL errors. Current rollback tests, including failed-first-write retry, pass. No new transaction/rollback issue found; SQL conflict resolution also protects per-metric rows when requests overlap, without fixing driver check-then-write races.
- D-S13's accepted-debt sentence is **accurate but non-exhaustive**. A replay still skipped rewrites only `solo_pod_markov`: posterior, tick_epoch, strikes_json, last_advanced_tick and last_outcome (:742–751). A replay now scored also inserts/upserts `solo_pod_scored_history` with p_raw/p_published, gate_pass, candidate, drift_stale, details_json (:973–1007), then count-prunes it; originally skipped ticks had no ring row, so this is an insertion, not replacement of an original skipped row. It also upserts **solo_pod_calibration**, including state/mapper/tau/updated_at, mapper_healthy and last_fit_attempt_epoch (:1025–1053); existing provenance_json is carried unless a new adoption supplies provenance. Markov time can regress to the replayed epoch and posterior/strike progression uses current state. Recommend naming calibration as well in the accepted-debt record; none of these pre-existing writes is made harmless by DO NOTHING on the metric table.

## F2/F4: plans, progress and negative control

Independent in-memory probes used real store schemas/wrappers, six streams including `('', '')`, `('', 'cpu')`, `('pod', '')`, mixed case and Unicode; each had times 99,100,101, cutoff=100 and batch=1. **Both tables deleted 6, retained 12 (all >=100), second sweep 0**; empty metric coverage here is real, unlike R1's committed fixture.

`EXPLAIN QUERY PLAN` results (first pod / subsequent pod / first metric / subsequent metric):
```text
raw: SCAN solo_window_points USING COVERING INDEX sqlite_autoindex_solo_window_points_1
     SEARCH ... USING COVERING INDEX ... (pod_key>?)
     SEARCH ... USING COVERING INDEX ... (pod_key=?)
     SEARCH ... USING COVERING INDEX ... (pod_key=? AND metric_name>?)
scored: SCAN solo_scored_ticks
        SEARCH ... USING PRIMARY KEY (pod_key>?)
        SEARCH ... USING PRIMARY KEY (pod_key=?)
        SEARCH ... USING PRIMARY KEY (pod_key=? AND metric_name>?)
```
Both first-pod VDBEs: `Integer 1; OpenRead; Rewind; Column; ResultRow; DecrJumpZero ... Halt` before `Next`. Raw uses its covering PK autoindex; WITHOUT ROWID scored uses its PK-organized table B-tree. **No full-table traversal or sort**: bounded first-entry positioning, then strict indexed seeks. NOT NULL keys make None an unambiguous initial sentinel; key order strictly advances, deletes reduce each finite expired backlog, and exhausting a deleted pod still seeks strictly beyond its saved key. Unbounded concurrent insertion of expired rows remains the previously disclosed non-snapshot-sweep limitation.

F4 at `test_solo_window_store.py:723–748`: the liveness/result checks precede the independent write and return from the pause. E-P6 :991–1007 records held-lock control failing specifically at `assert not t.is_alive()`. Its `EXIT=0 (pytest exit 1)` is a wrapper-status quirk, not a passing pytest control; the actual failure is recorded. No need to mutate production to repeat it.

Probe failure retained verbatim: initial scratch INSERT used a nonexistent raw column, exit 1: `sqlite3.OperationalError: table solo_window_points has no column named episode_id`. Read actual schema :198–207, corrected only the in-memory probe; subsequent probe exit 0. This was reviewer probe construction, not a product failure.

## F3/F5/F6: meaningful pins, arithmetic and scope

- Independently parsed committed old/new modules and stripped module/class/function docstrings before `ast.dump(..., include_attributes=False)`: **driver/state/retention all equal, 197a122 → e30ddb0**. Driver also AST-equal **7e4014e → HEAD**. Only driver diff after 7e4014e is the 11-line comment at :2229–2239; no executable hunk.
- Age pin `test_solo_state.py:1231–1275` calls production `metric_tick_rows` with snapshot age 1200 conflicting with persisted t0==tick, plus absent-age fallback, future t0 and neither-source cases. Meaningful precedence oracle, not implementation echo; it simulates the interleaving's resulting inputs, not actual asynchronous publication.
- Schedule pin `test_solo_retention.py:128–159` uses seeded random input bounds and midpoint congruence plus two fixed repeated-midpoint cadence checks. It calls production scheduling and does not simply repeat its ceil expression; would reject earliest-eligible-midpoint cadence. The tested `<1.5*T` bound is correct; the docstring's `<=T` claim is not (R3).
- Recomputed from master-card :47–55: 7×86400/300×11=**22,176 rows/pod-week**; ×205=**4.54608 MB**; 5 GiB=5.36870912 decimal GB. Totals include raw+3.7 MB other+4.54608 MB scored per pod:

| Pods | Scored 7d GB | Raw pre/post GB | Other GB | Total pre/post GB |
|---:|---:|---:|---:|---:|
| 10 | 0.0454608 | 0.616 / 0.437 | 0.037 | 0.6984608 / 0.5194608 |
| 100 | 0.454608 | 6.16 / 4.37 | 0.37 | 6.984608 / 5.194608 |
| 1000 | 4.54608 | 61.6 / 43.7 | 3.7 | 69.84608 / 51.94608 |

Projected 5-GiB capacities **76.8649 pre / 103.3516 post**; scored fraction **6.5087% pre / 8.7515% post**. Addendum's ~70/~52 GB and ~76/~103 pods are sound rounded projections, not allocated-file measurements; its free-list/WAL/headroom caveats are appropriate. Card's rounded 52.1 differs from recomputed 51.946, not a new implementation measurement.
- Independently byte-compared git objects vs **5bcc7f9**: `analyser/solo_mode/scan.py`, actual root `analyser/exporter.py`, actual root `analyser/api_layer.py` identical; extracted complete `_merge_episodes` source bytes also identical. Three fix commit path lists are exactly 3,2,6 prescribed files; no AGENTS.md, analyser/agent-orchestration/, dashboard report, dependency or unrelated path committed/staged into those commits.

## Residual/new findings (concrete fixes; advisory)

1. **R1 — should-fix — missing scored empty-metric regression:** `analyser/tests/unit/test_solo_window_store.py:874` passes `metric=''` to `_seed_state`, but :762–780 ignores that argument and emits canonical metrics only. :883–898 checks only a canonical metric. Fix: seed actual empty-metric rows through metric_ticks (or direct fixture SQL), assert their presence before sweep, then exact expired/live counts for that key; correct E-P6 :967–976's coverage claim. Product behavior independently works, but this named acceptance coverage is absent.
2. **R2 — nit — inaccurate plan comment/evidence:** `analyser/solo_mode/window_store.py:120–121` and `evidence/E-reference-model-study/E-P6.md:957–958` say both first seeks are index seeks, “never a table scan.” Actual first-pod EQP includes SCAN, including scored's table B-tree. Fix wording to “bounded first-entry PK-B-tree traversal (LIMIT 1), indexed range seeks thereafter; no full scan,” and record the real plans. Do not add an index or alter correct queries merely to change EQP terminology.
3. **R3 — should-fix — false schedule upper bound:** `analyser/solo_mode/retention.py:95–97` says up to one tick later than now+interval. With now=1,T=300,interval=3600, observed result=4050, excess=449>300; true excess is `[T/2,1.5*T)`. Fix docstring to that bound and “conservative following-boundary midpoint,” not earliest midpoint at/after the minimum; align driver :2231–2232/addendum :948 wording if retaining “next.” No algorithm change requested.
4. **R4 — should-fix — incomplete budget evidence and unlabeled percentage:** `evidence/E-reference-model-study/E-P6.md:1120–1133` still supplies prose, not the full pre/post-S6 budget table requested by card :47–55 and RV-P6 F6. `markdown/2026-10-09-solo-mode-runtime-cutover.md:952` still calls scored rows ~6.5% without saying pre-S6 (post-S6 ~8.75%). Fix: add the complete 10/100/1000 pre/post table to E-P6, including raw/other/total/PVC ratios, and label the percentage pre-S6 or give both. The matrix above independently supplies the component arithmetic; capacity headline itself is corrected.

No remaining blocker to the **amended** P6 observation-history contract was found. Remaining issues are regression coverage and factual documentation/evidence gaps, not scoring-math changes or an unaccepted replay-policy redesign.
