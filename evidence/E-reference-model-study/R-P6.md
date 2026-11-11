# R-P6 — retention + durability (D-D): production research evidence

Researcher R, 2026-11-10. Read-only on production (HEAD `5bcc7f9`), lab, and the cluster. Labels: **OBSERVED**
(command output), **SOURCE** (file:line), **INFERENCE** (my reading/estimate). Nothing was edited; no repo or
cluster write. Live objects: pod `pipelineml-anomaly-detector-solo-64676d88bf-5jqgv` (ns `rtx-4000-test`,
IP 10.244.0.41), DB `/app/cache/solo_mode_state.sqlite`.

## 1. `solo_window_points`: schema, writers/readers, live size, real lookback

**Schema** (SOURCE `solo_mode/window_store.py:143-162`): `(pod_key TEXT, metric_name TEXT, ts_epoch REAL,
value REAL, container TEXT, name TEXT, provenance TEXT NOT NULL DEFAULT 'unknown')`,
`PRIMARY KEY (pod_key, metric_name, ts_epoch)`, plus `idx_solo_window_points_key ON solo_window_points
(pod_key, metric_name, ts_epoch)`.

**FINDING 1.1 (redundant index = 178 MB + ~2x insert amplification).** OBSERVED `dbstat`:
`solo_window_points` 1,167,821 rows / 259,056,616 B; `sqlite_autoindex_solo_window_points_1` 178,343,936 B;
`idx_solo_window_points_key` 178,343,936 B — bit-identical sizes because the explicit index covers exactly the
PK triple. The explicit index is fully redundant (every query filters `pod_key`+`metric_name`). Dropping it
(SOURCE `DROP INDEX IF EXISTS`, logged like `state.py:312-350`) reclaims 178 MB of pages and removes one index
maintenance per inserted row. File size only shrinks after `VACUUM` (`auto_vacuum=0`, OBSERVED).

**Writers** (all through one upsert path `_merge_episodes`, SOURCE `window_store.py:249-323`):
`bootstrap` / `append_tail` / `gap_repair` (SOURCE `window_store.py:404-433`) and `slide_drop`
(SOURCE `window_store.py:429-443`, `DELETE ... WHERE pod_key=? AND metric_name=? AND ts_epoch<?`).
Callers: `scan.run_ingest_tick` (SOURCE `scan.py:1926-1962`) every `T`=300 s, and `scan.run_build_cycle`
every `dt`=1800 s (SOURCE `scan.py:2619-2690`) which owns the trim.

**Readers**: `read_window` (SOURCE `window_store.py:445-473`), `read_window_drop` / `missing_spans`
(SOURCE `window_store.py:390-415`), the scorer `_score_continuous` / `_score_rare_count` (SOURCE
`driver.py:1195-1275`), diagnostics and the dashboard routes.

**Hot-path read cost (FINDING 1.2, pre-existing).** `_merge_episodes` runs `SELECT ts_epoch, value, container, name,
provenance FROM solo_window_points WHERE pod_key=? AND metric_name=?` with **no ts bound** (SOURCE
`window_store.py:277-281`), so the full stored stream is materialised into Python on every merge: OBSERVED ~10,600
rows per (pod, metric) ⇒ ~1.17 M rows re-read and re-dicted every 5 minutes at 110 streams (~337 M rows/day)
before anything is written. P6 must add **O(small)** work here, never another O(window) scan.

**Live size** (OBSERVED `ls -la`, 2026-11-10T00:05): `solo_mode_state.sqlite` 793,931,776 B (757 MiB),
`-wal` 9,331,832 B, `-shm` 32,768 B. OBSERVED `PRAGMA`: `page_size` 4096, `page_count` 193,831,
`freelist_count` 36,977 (144 MiB free), `auto_vacuum` 0.
OBSERVED `dbstat` per table: `solo_window_points` 259,056,616 B / 1,167,821 rows; the two indexes 178,343,936 B
each; `solo_pod_scored_history` 2,880 rows / 24,756,224 B (8.6 kB/row — it stores `details_json`);
`solo_metric_model` 110 rows / 12,288,000 B; `solo_pod_calibration` 20 / 45,056 B; `solo_pod_correlation`
20 / 12,288 B; `solo_pod_markov` 10 / 20,480 B; `solo_pod_registry` 28 / 4,096 B. PVC: 5 GiB `standard`
(SOURCE `deploy/k8s/solo-card6/state-pvc.yaml`).

**Live window content** (OBSERVED, read-only `mode=ro`): 10 distinct `pod_key`s, 116,880–117,236 rows per pod
(11 metrics × ~10,600), global ts span 173,419–173,429 s = **2.007 d**. Registry holds **28** `pod_key`s, 10 with
window data; window rows whose `pod_key` is absent from `solo_pod_registry` = **0**.

**Real lookback requirement.** Trim cutoff = `fit_start − headroom` with `t0=floor(now/dt)*dt`,
`b=t0−T`, `fit_start=b−Dt` (SOURCE `scan.py:1976-1979`; trim SOURCE `scan.py:2684-2687`) ⇒ the window holds
`Dt + T` = 2 d + 300 s, exactly the observed 2.007 d. Cand-B raises the requirement: vision
“`Dt` = 2 d + max adaptive boxcar ≤ 12 h + scoring tail” (SOURCE
`evidence/solo-mode-plans/solo-adaptive-smoothing-stl-vision-2026-11-10.md:199`; boxcar grid 30 m…12 h at
SOURCE `:157`) ⇒ **2 d 12 h + tail ≈ 2.51 d** of raw points, i.e. ~13,500 rows per stream when `window.Dt`
is raised. That is a **config-only** change (`slide_drop` follows `Dt`), no code change.
**Verdict on D-D's “one week = ~3x headroom”**: today 7 d / 2.007 d = **3.49x**; under cand-B 7 / 2.51 = **2.79x**
— so a 1-week TTL is only 2.8x once cand-B lands; say so in the gate.

**Concurrency / lock model** (SOURCE `window_store.py:73-107`): ONE connection per store object, built by
`open_solo_connection` with `check_same_thread=False`, `timeout`=`persistence.sqlite.timeout_seconds` (30 s),
`row_factory=Row`, `PRAGMA journal_mode=WAL`, `PRAGMA synchronous=NORMAL`. Window and state stores each own a
connection to the SAME file (SOURCE `driver.get_solo_stores`, `driver.py:176-189`), each behind its own
`threading.RLock`; every mutation commits immediately. Threads: `SoloRuntime` daemon (ingest/refit,
`driver.py:2189-2217`), `PipelineMLExporter` daemon (scoring + publication, `exporter.py:940-941`), a 4-worker
`ThreadPoolExecutor` for build jobs (`scan.py:79`), Flask request threads for read-only routes. WAL is active on
the live file (OBSERVED `-wal` 9.3 MB, `-shm` present). **INFERENCE**: a batched `DELETE` is correctness-safe
(WAL, 30 s busy timeout, per-store RLock) but serialises against the tick — SQLite allows one writer — so
`LIMIT` ≤ 2000 with a commit per batch keeps each lock in the ms range; never start a sweep on a tick boundary.

**Migration precedent to copy.** (a) additive column: `_migrate_scored_history` / `_migrate_pod_calibration` do
`PRAGMA table_info(...)` presence check → `ALTER TABLE ... ADD COLUMN ... NOT NULL DEFAULT <v>` →
`logger.info("... migration: added column ...")` (SOURCE `state.py:312-355`, `:145-158`). (b) a NEW table needs
no ALTER: `state.py:_init_schema` is one `executescript` of `CREATE TABLE IF NOT EXISTS ...; CREATE INDEX IF NOT
EXISTS ...` (SOURCE `state.py:76-208`; window-side example `window_store.py:139-162`). (c) Never add an explicit
index on a column set equal to the PK — that is exactly the redundancy in 1.1.

## 2. Where the per-tick values live, and what “gate-fired” / “stale hours” mean in code

All five D-D columns exist **already, at score time**, in one dict: `driver._score_all_metrics` builds
`metrics_out[name]` with `kind, contract, eligible, reason, p, tilde_p, residual, observed, forecast, ess,
model_t0, model_age_seconds` (SOURCE `driver.py:1294-1313`, `:1334-1356`; `eligible` reasons `:1385-1390`), stashed
verbatim as `details["metrics"] = _public_metrics(metrics_out)` (SOURCE `driver.py:1880`) and written in ONE
transaction by `state_store.complete_scored_tick(..., details=details, ...)` (SOURCE `driver.py:1872-1913`;
writer `state.py:626-770`). `_public_metrics` strips only `_`-prefixed keys and `unready` (SOURCE
`driver.py:1962-1969`). **INFERENCE: the per-metric rows can be derived inside `complete_scored_tick` (state.py
is NOT parity-pinned) with ZERO driver change.**

Mapping (verified against code, not guessed):

| D-D column / gauge | code fact |
|---|---|
| `p_raw` / `solo_p_raw` | `m["p"]` = the metric's raw surprise probability this tick (SOURCE `driver.py:1334`, set from `res["p"]` at `:1329`) |
| `ess` / `solo_ess_value` | `m["ess"]` = `float(model_used["ess"])` — ESS of the model that actually scored, `None` when no model scored (SOURCE `driver.py:1347-1349`) |
| gate-fired / `solo_ess_gated` | `m["p"] is None` with `m["reason"]`. The ESS gate itself is in `build_one`: `ess < min_effective_samples` → metric skipped, **no model persisted** (SOURCE `scan.py:1321-1333`); at score time it therefore surfaces as `reason="model not built"` (SOURCE `driver.py` `_scorable`: `model is None -> "model not built"`, also `"model stale"`, `"no window data"`), and `unready` is defined as exactly that triple (SOURCE `driver.py:1315-1317`). There is **no persisted per-metric gate flag today**: `run_build_cycle`'s summary records only `skipped[...] = "fetch-failed" | "pool-backpressure"` (SOURCE `scan.py:2575`, `:2748`, `:2750`). |
| `stale_hours` / `solo_model_stale_hours` | `m["model_age_seconds"] = tick_end − model_t0` (SOURCE `driver.py:1351-1352`) ⇒ `stale_hours = model_age_seconds/3600`. Distinct from `drift_stale` (the D14 RECORD-ONLY soft flag, SOURCE `driver.py:2120-2140`, `state.py:145-152`) — do not conflate them. |
| `provenance` (tick) | the per-tick calibration provenance already passed as `provenance=gate_provenance` (SOURCE `driver.py:1913`), stored in `solo_pod_calibration.provenance_json`. On a gated metric there is no calibration provenance — use the metric's `reason` string (that is the honest provenance of a missing value). The window store also uses the token `provenance` for raw identity (`unknown|physical|unselected`, SOURCE `window_store.py:216-230`) — **name collision risk**: name the new column `metric_reason` or document it. |

**Ring and “depth ≥ 2x ring”.** The scored-tick ring is `scored_tick_history.depth`; deployed `depth: 1d`
(OBSERVED live ConfigMap) ⇒ **288 ticks** at T=300 s; validated `depth >= fusion.calibration.gate.window` (SOURCE
`config.py:931-941`), trimmed per pod in the same transaction as the insert (SOURCE `state.py:748-760`). OBSERVED
`solo_pod_scored_history` = 2,880 rows = 288 × 10 pods ⇒ the ring is **pod-level, not per metric**. So “depth ≥ 2x
ring” = the new table's retention must cover **≥ 576 ticks = 2 d** per (pod, metric); 1 week = 2,016 ticks = **7x
ring** (satisfied). Validate `persistence.scored_ticks.ttl_seconds >= 2 * scored_tick_history.depth_seconds`.

## 3. Prometheus exposition today — and the fact that nothing scrapes it

**Code.** `prometheus_client` is optional: every metric is built as `Gauge(...) if Gauge is not None else None`,
registered in `EXPORTER_OBSERVABILITY_METRICS`, with `set_*` helpers that no-op when the client is absent (SOURCE
`exporter.py:223-355`). Canonical gauge `pipelineml_detector_anomaly_probability` labels
`pod, pod_family, model_family, mode, degraded` (SOURCE `exporter.py:311-343`), published **only for
`probability_label == "calibrated"`** ticks and removed (never zeroed) when a pod goes raw/ambiguous (SOURCE
`exporter.py:2274-2330`, cleanup `:1817-1860`); `solo_mode_degraded_fraction` (`pod, pod_family`) at SOURCE
`exporter.py:2335-2336`.
**Route.** `/metrics` is the ONLY metrics exposure: `@app.route("/metrics")` returning OpenMetrics, registered
only when `endpoints.metrics.enabled` (SOURCE `api_layer.py:220-222`), same Flask app and same container port 8080
(SOURCE `deploy/k8s/solo-card6/deployment.yaml:75`; probes only `/health` `:92-104`; single service port SOURCE
`service.yaml`). Deployed `metrics.enabled: true`, `api.enabled: false` (OBSERVED live ConfigMap ≡ repo
`configmap.yaml:91-95`) ⇒ **`/metrics` on 8080 already IS the dedicated, API-less metrics route**; no second port,
no separate app. OBSERVED live body via the operator port-forward (`127.0.0.1:18086/metrics`): 15 lines —
`# HELP`/`# TYPE` for the canonical gauge with **zero samples** (no pod is calibrated), 10
`solo_mode_degraded_fraction` lines, `# EOF`.

**Scrape path (OBSERVED — the blocker for D-D's durability claim).** In-cluster Prometheus (`istio-system`) keeps
pods/services only with the `prometheus.io/scrape=true` annotation, at `scrape_interval: 5m`; the solo pod carries
**only** `kubectl.kubernetes.io/restartedAt` and `service.yaml` no annotations, so the OBSERVED 5 active targets
are flagger/kube-state-metrics/istiod and **10.244.0.41 (the solo pod) is absent**. OBSERVED `api/v1/query`:
`pipelineml_detector_anomaly_probability` → `[]` and `solo_mode_degraded_fraction` → `[]` — nothing has ever
stored these metrics. `ServiceMonitor`/`PodMonitor` do not exist (CRD absent: *the server doesn't have a resource
type*). Vector scrapes only cadvisor / kubelet / kube-state-metrics / flagger and remote-writes to GreptimeDB; the
detector is not a Vector source. Durability split (OBSERVED): Prometheus `storage-volume` is an **emptyDir** with
no PVC and `storage.tsdb.retention: 0s` ⇒ **ephemeral**; GreptimeDB has two 100 Gi `standard` PVCs
(`ml-monitoring`) ⇒ the only durable store.
**INFERENCE:** an exposure nobody scrapes is not an archive. D-D's “durable archive = existing Prometheus/
Greptime” needs a scrape leg that does not exist: either the `prometheus.io/scrape: "true"` + `port: "8080"` +
`path: /metrics` annotations on the solo pod template (repo-editable, 5-minute interval, still ephemeral) or a
Vector `prometheus_scrape` source → GreptimeDB (cluster config, Supervisor/D17, outside the P6 code card).

**Cardinality.** 4 gauges × 11 metrics × N pods = **44N series**: 440 at 10 pods, 4,400 at 100, 44,000 at 1,000,
vs 10 today. Keep the labels to `(pod, pod_family, metric)` — never a reason string.

## 4. Config schema to extend (YAML-first, fail-fast, no silent defaults)

`validate_solo_mode_config` is an ordered, hand-written validator: `_require_key` → `_require_non_empty_string` /
`_require_one_of` / `_require_positive_int` / `_require_str_list` / `_positive_float`, raising
`ConfigurationError` (OBSERVED probe: a missing top-level key raises `ConfigurationError`; a wrong type raises
`TypeError`/`ConfigurationError`). Numbered sections run 1..21: `persistence` is **§19** (SOURCE
`config.py:909-941`), `logging` §20 (SOURCE `config.py:942`) — the new blocks go between them. Durations:
`_parse_duration_seconds` (`30m`, `12h`, `2d`; SOURCE `config.py:150-172`). `build_solo_mode_config` copies the
block into the frozen `SoloModeConfig` (SOURCE `config.py:1011`, fields `:1051`) behind the dual-access view
(`cfg["x"]` == `cfg.x`).
**CONSTRAINT (verified):** the validator does **NOT** reject unknown keys (no `_no_unknown`/set-difference sweep
anywhere in `config.py`). A typo'd or absent block therefore fails silently unless P6 adds explicit
`_require_key(...)` + validation for every new key — the card must require fail-fast on each key, and a test that
a missing key raises `ConfigurationError` (and that an unknown/typo'd key is rejected, which is a new behaviour:
implement an explicit allowed-key set for the two new blocks only).
**Deployed vs repo:** OBSERVED byte-identical — `diff` of the live ConfigMap
`pipelineml-anomaly-detector-solo-config[detector-common.yaml]` (370 lines) against the repo slice of
`deploy/k8s/solo-card6/configmap.yaml` → **IDENTICAL**. So editing the repo ConfigMap is the whole deployment
change (image repin aside). Relevant values today (OBSERVED): `persistence.sqlite.path
/app/cache/solo_mode_state.sqlite`, `journal_mode WAL`, `synchronous NORMAL`, `timeout_seconds 30`,
`scored_tick_history.depth 1d`, `window.Dt 2d`, `window.dt 30m`, `tick_seconds 300` (derived),
`scope.cluster rtx-4000-test`, universe 14 pods / 10 in scope, `undersampling.min_effective_samples 60`.
**Precedent for shipping values (P3):** new keys go into the repo ConfigMap in the same commit as the validator,
the values are pinned by a test in `tests/unit/test_solo_mode_config.py`, and the deployed image is repinned
separately by the deploy commit (R-P3 §Q5, `E-P3.md`).

## 5. Tests to extend, how to run, and the parity-pin hazard

Existing solo suites (OBSERVED `ls analyser/tests/unit`): `test_solo_{window_store,state,mode_config,driver,scan,
exporter,diagnostics,dashboard_routes}.py` plus subprocess helpers `_solo_{exporter,diagnostics}_subprocess.py`.
Run (VERIFIED here): `cd analyser; PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared
/tmp/solo-p3-venv/bin/python -m pytest tests/unit/test_solo_state.py tests/unit/test_solo_window_store.py
tests/unit/test_solo_mode_config.py` → **170 tests collected** (venv Python 3.10.22, pre-existing). Add for P6:
schema+insert+TTL-sweep in `test_solo_state.py` (precedent
`test_scored_history_and_calibration_schema_migrate_with_logged_alter`), no-redundant-index, gauge publication and
removal in `test_solo_exporter.py` (it already asserts the `/metrics` text), fail-fast keys in
`test_solo_mode_config.py`.

**PARITY HAZARD (must be planned, not discovered).** `reference-model-study/config/reference.yaml:83-99` pins
`expected_production_head: 5bcc7f9128d55e38d3c09838b3af0699edc4973b` (today's HEAD, OBSERVED) and `used_files` =
`noise.py, baseline.py, **scan.py**, fusion.py, **driver.py**, **config.py**, shared/bayesian/*.py,
**deploy/k8s/solo-card6/configmap.yaml**`; `tests/parity/prod_import.py:124` also requires a clean
`git status --porcelain` for each and fails loudly (never skips) ⇒ `window_store.py` and `state.py` are **free**,
`scan.py`/`driver.py`/`config.py`/ConfigMap are **pinned**. P6 cannot avoid `config.py` (new keys), the ConfigMap
(new values) and `driver.py` (call site) ⇒ **the P6 commit breaks A1a/A1c parity until the lab repins**
(`expected_production_head` + `used_files`, `results/a1a-parity.json`); `test_reference_config.py:80` asserts
`len(used_files) == 9`. The card must carry the repin as an explicit step or the gate records parity red-by-design
with a named follow-up.

## 6. Risks and the recommended minimal design

**Write amplification.** New inserts are 11 metrics × N pods **per scored tick** = 31,680 rows/day at 10 pods
(OBSERVED 288 ticks/day/pod). At ~130 B/row (8 narrow columns) ≈ 4 MB/day, ~29 MB per 7-day TTL at 10 pods — noise
next to the 757 MiB file and the ~1.17 M rows/TICK already read on the ingest path (§1). At 100 pods ~290 MB; at
1,000 pods **~2.9 GB against a 5 GiB PVC** ⇒ TTL or a row cap must scale with pod count (INFERENCE; state it).
**File growth.** Deletes only populate `freelist` (144 MiB already free, `auto_vacuum=0`). Dropping the redundant
index (§1.1) frees 178 MB of pages but the file stays 757 MB without `VACUUM` (needs ~2x free space on the PVC,
must not run on the tick thread). Do **not** propose `auto_vacuum=INCREMENTAL` on the live file (full rewrite).
**Sweep vs tick.** SQLite has one writer: an unbounded `DELETE` on a 1.17 M-row table holds the write lock for
seconds and stalls ingest. Use `LIMIT` batches (≤ 2000, commit per batch), per (pod, metric) so
`(pod_key, metric_name, ts_epoch)` is used, at most hourly and never on a `dt` boundary.
**Label cardinality.** 44N series — `(pod, pod_family, metric)` only, never a reason string.

**Recommended minimal design (researcher's call unless §7 says otherwise).**
1. `solo_scored_ticks` in `state.py:_init_schema` (unpinned), narrow, PK-first, **no extra index**:
   `(pod_key TEXT NOT NULL, metric_name TEXT NOT NULL, tick_epoch REAL NOT NULL, p_raw REAL, ess REAL,
   gate_fired INTEGER NOT NULL, stale_hours REAL, metric_reason TEXT, PRIMARY KEY (pod_key, metric_name,
   tick_epoch))`. `WITHOUT ROWID` is ~30 % smaller (INFERENCE) but deviates from every existing table — skip.
2. Writer: loop over `details["metrics"]` inside `complete_scored_tick` (same transaction as the ring; SOURCE
   `state.py:626-770`): `gate_fired = 1 when m["p"] is None`, `metric_reason = m["reason"]`,
   `stale_hours = m["model_age_seconds"]/3600` else NULL, tick `provenance` from `gate_provenance`. **No
   `details_json` copy** — that column is what makes `solo_pod_scored_history` 8.6 kB/row.
3. Sweep: new `analyser/solo_mode/retention.py` (new file, no parity impact), `sweep(store, table, ttl_seconds,
   batch=2000, now)`, called from the `SoloRuntime` loop hourly after the ingest leg; also sweeps pod_keys absent
   from `solo_pod_registry` (the 28-vs-10 skew in §1).
4. Gauges: 4 gauges in `exporter.py` beside the existing ones (`Gauge or None`, added to
   `EXPORTER_OBSERVABILITY_METRICS`), set per metric in `_poll_solo_once` right after `set_solo_degraded_fraction`
   (SOURCE `exporter.py:2335-2336`) guarded by `details_status == "available"`; `ess`/`stale_hours` skipped when
   `None`, `solo_ess_gated` always 0/1; removed via `_solo_clear_pod_children` / family-removal paths (SOURCE
   `exporter.py:1817-1860`).
5. Route: none — `/metrics` on 8080 already is the dedicated metrics route (§3); a second path/port would need a
   probe/service change for zero benefit.
6. Config: `persistence.scored_ticks.{enabled, ttl, sweep_interval, batch_rows}` and
   `persistence.raw_points.{enabled, ttl}` + cross-validation `ttl >= 2 * scored_tick_history.depth`, all
   `_require_key` fail-fast; repo ConfigMap carries the values; the operator repins the image.

## 7. What the operator must decide vs what the researcher settles

**Operator.** (a) TTL default — 1 week is given, but confirm it stands *after* cand-B raises the raw lookback to
2.5 d (headroom drops 3.5x → 2.8x) and confirm the pod-count scaling rule (shorter TTL or a row cap above ~100
pods, otherwise the 5 GiB PVC is the limit). (b) Whether the archive leg is Prometheus-only (ephemeral today,
5-minute scrape, needs a repo annotation) or Vector→GreptimeDB (durable 200 Gi, needs cluster config by D17).
(c) Whether P6 may `DROP INDEX idx_solo_window_points_key` + optional offline `VACUUM` on the live PVC
(reclaims 178 MB now; touches a live schema). (d) Whether P6 lands before A1c/later parity work given the pin
break (§5), or the repin rides in the same commit.
**Researcher (settled — state in the card).** Gauge names exactly as D-D wrote them (`solo_p_raw`,
`solo_ess_value`, `solo_ess_gated`, `solo_model_stale_hours`, labels `pod, pod_family, metric`) — lowercase, no
`pipelineml_detector_` prefix, since D-D is the spec the dashboards will query; route = the existing `/metrics`;
`gate_fired` = `p is None` + the reason string; `stale_hours` = `model_age_seconds/3600` (never confounded with
`drift_stale`); sweep hourly, batch 2000, per (pod, metric); narrow table, PK-only index; new module
`solo_mode/retention.py` so `window_store.py`/`state.py` stay the only store files touched and the pinned-file
delta stays minimal (3 small call sites).

## 8. Open items not settleable read-only

* Prometheus keeps data on an emptyDir, retention unlimited ⇒ an operator restart wipes it; the true span is unreadable.
* `solo_pod_registry` holds 28 keys vs 10 pods with window data; their `last_seen` ages were not inspected (matters only to whether the sweep prunes registry rows).
* Whether the dashboards already query `solo_p_raw`-style names (`PATCH-dashboard-threshold-labels`, a peer's work, not read here); if so, the literal names are mandatory.
