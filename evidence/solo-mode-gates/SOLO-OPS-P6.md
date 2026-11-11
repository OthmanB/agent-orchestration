# SOLO-OPS-P6 — SQLite-only retention + per-metric scored-tick durability

Date 2026-11-11 · Status: **promoted (local; not deployed)** · S model `anthropic/claude-sonnet-5-5` · executors: configured execution role (Qwen); reviewer: configured review role.

## 1 Context
Decision D-D (amended 2026-11-10: SQLite-only, Prometheus scrape leg deferred), D-S2 (parity-evidence freeze), D-S6; operator defaults Q1-Q7 accepted (TTL 7 d, `safety_factor` 2.5, `lookback_margin` 12 h, `WITHOUT ROWID`, `gate_fired` = no-fresh-model proxy, PVC sizing = operator's). Cards `evidence/omp-workcards/solo-ops-P6.md` (+ "Post-review corrections" at its end) and `solo-ops-P6-slices.md`; R-P6; E-P6 (`evidence/E-reference-model-study/E-P6.md`, `E-P6-repin.md`, `E-P6-repin2.md`); reviews `RV-P6.md`, `RV-P6b.md`. Release message: operator "start with P6" 2026-11-11 (D-S12).

## 2 Decisions
D1-D8 of the card stand, with the corrections of D-S13/D-S14: the per-metric table keeps the FIRST committed observation (`ON CONFLICT DO NOTHING`); `stale_hours` = scoring-snapshot age else post-score persisted-t0 lookup, clamped, NULL when neither; `gate_fired` is a proxy whose causes are not separable; the sweep schedule is a minimum interval (excess over `now+interval` in `[T/2, 1.5T)`, effective cadence interval+T = 3900 s) with no non-overlap guarantee; first seeks have no lower bound (empty keys swept); capacity table has pre- and post-S6 columns.

## 3 Implementation + review (production branch `feature/cnn2dlstm-bayesian-statistical-detector-v2`, local, base `5bcc7f9`)
| slice | commit | files | tests after |
|---|---|---|---|
| S1 required `persistence.retention` + load-time rules | `43b31b4` | config.py, detector-common.yaml, configmap.yaml, test_solo_mode_config.py, config-schema doc | 215 (baseline 170 pre-venv fix) |
| S2 `solo_scored_ticks` + writer on both paths | `52197c3` | state.py, driver.py, 2 test files | 276 |
| S3 batched sweep + policy | `a29efbf` | window_store.py, state.py, retention.py (new), 2 test files | 288 |
| S4 `SoloRetention` thread | `9266dbf` | driver.py, test_solo_driver.py | 290 |
| S5 docs addendum | `5e435a0` | cutover doc | 290 |
| S6 drop redundant index (optional) | `7e4014e` | window_store.py, test | 293 |
| FIX-A (RV F1 blocker) | `163506f` | state.py, 2 test files | 296 |
| FIX-B (F2, F4) | `197a122` | window_store.py, test | 298 |
| FIX-C (F3, F5, F6) | `e30ddb0` | docs, 3 comment-only modules, 2 tests | 300 |
| FIX-D (RV-b R1-R4) | `c6ec9a2` | docs/comments, 1 test fixture | 300 |
Environment correction: the scratch venv lacked `pytz`, `termcolor`, `scikit-learn` (12 driver tests failed identically before any edit); installed into `/tmp/solo-p3-venv` only; baseline became 267.
Reviews: RV-P6 (1 blocker, 5 should-fix; S2 rejected, others accepted/with findings) → all accepted by S, fixed (D-S13); RV-P6b (0 blockers, R1-R4) → fixed in FIX-D (D-S14). RV-P6b independently reproduced **300 passed** (47 state + 45 window + 142 config + 8 retention + 58 driver) and confirmed: only the allowed `driver.py` hunks (import, `metric_ticks` block, 3 kwargs, SoloRetention block; AST-equal after the comment-only fixes), `scan.py`/`exporter.py`/`api_layer.py`/`_merge_episodes` byte-identical, no unrelated path in any commit.

## 4 Commits
Production HEAD before `5bcc7f9`, after `c6ec9a22b7cf5da42be082f70e2a36a8f207c0d0` (10 local commits). No push, no deploy, no ConfigMap apply, no VACUUM. Unrelated dirty paths (` M AGENTS.md`, untracked `analyser/agent-orchestration/`, the 2026-11-06 report) never staged.

## 5 Acceptance numbers
- Config: 7 keys required, unknown key rejected, exact boundaries 540,750 s / 172,800 s (+ min-TTL message), `True` rejected, ConfigMap YAML equals detector-common (tests green).
- Insert cost (real `complete_scored_tick`, 11 rows): **+0.158 ms/pod-tick (10 pods), +0.169 ms (1000 pods)**; bound 1.0 ms, ratio 1.07 <= 3.
- Concurrency (150 k expired rows per table, 11-row tick every ~20 ms, batch 2000, pause 10 ms): **max 7.3 ms, p99 5.2 ms, median 0.5 ms, 247 writes, 300,000 rows deleted exactly, no OperationalError**; bound 0.5 s (no-pause control in the card: 194 ms).
- Disk: **207.3 B/row** (bound 260; rowid table 358); per pod-week 22,176 rows x 205 B = 4.546 MB.
- Capacity (active-stream projection, excludes WAL/free space/headroom): 5 GiB PVC holds ~76.9 pods before S6, ~103.4 after; 1000 pods ~69.8 / ~51.9 GB. The 2-day raw window, not P6, is the binding term; the new table is ~6.5 % (pre-S6) / ~8.75 % (post-S6) of the per-pod footprint.
- Migration: pre-P6 file DB gets the table with ONE warning and no backfill; fresh DB INFO only; restart survival (store and driver level) green; delayed-skip-retry regression green (negative control on old SQL fails with all five fields changed).

## 6 Parity (lab `reference-model-study`)
`used_files` unchanged (9); P6 touches `config.py`, `driver.py`, `configmap.yaml`. Pin moved `5bcc7f9` -> `7e4014e` (lab `3f97c8e`, superseded) -> **`c6ec9a2` (lab `ed249a4`, final)**; parity stage 1 + 2 green, `a1a-parity.json` body EQUAL to the pre-P6 baseline once `provenance` and every `wall_seconds` are dropped; `blob_ids` changed only for the touched pinned files. Campaign-log line: D-P6-repin2 (`E-P6-repin2.md`). Recorded discrepancy: the first repin reported "762 passed" for the lab's non-parity suite; the final repin and a collection run both give **1430**; the 762 is unreproducible and superseded. Any further production commit (incl. the deploy digest-pin) needs another re-pin.

## 7 Deviations / accepted debt
1. `next_sweep_epoch`: the slices file's formula contradicted the card's own sample value; the sample-consistent form was implemented and documented (D-S13/F5).
2. Accepted debt (pre-existing, outside P6): a replayed old tick can still rewrite `solo_pod_markov` (markov time may regress), insert/upsert `solo_pod_scored_history` and upsert `solo_pod_calibration`; the per-metric table is immune (first observation wins), so it can disagree with later pod-level details by design.
3. `gate_fired` is a no-fresh-model proxy; exact ESS attribution needs a `build_one` hook (parked).
4. Lab stash `stash@{0}` holds the cancelled `e30ddb0` repin attempt; left for the operator (not deleted without authorisation).

## 8 Operator steps (nothing deployed)
Image: build/push through the GitHub workflow after the operator pushes the branch (no local image builds). ConfigMap: apply `deploy/k8s/solo-card6/configmap.yaml` BEFORE or WITH the new image — the P6 image refuses to start without `persistence.retention`; old images ignore it. PVC: size per the capacity table. After deploy S/operator runs the live restart smoke (not done here). Rollback: redeploy the previous image + previous ConfigMap; the new table stays in the file, is ignored by the old image; the dropped `idx_solo_window_points_key` is recreated by the old image's `CREATE INDEX IF NOT EXISTS`; no VACUUM was run.
