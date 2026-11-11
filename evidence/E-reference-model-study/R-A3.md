# R Evidence - R-A3 (raw-cadence data packaging research)
- Date: 2026-11-09 (probes run 2026-11-09T02:00-03:10Z)
- Environment: host `rtx-4000-test` (user `michel`), context `kind-rtx-4000-cluster`, single node
  `rtx-4000-cluster-control-plane`; data namespace `ml-components`, store namespace `ml-monitoring`
  (greptimedb-monitoring), cross-check namespace `istio-system` (prometheus).
- Access used: `ssh rtx-4000-test` with `export PATH=$HOME/.local/bin:$PATH` (BatchMode, no 2FA banner).
- Nothing was modified: every cluster interaction was `kubectl get/exec` + HTTP `SELECT` reads, or a
  `kubectl port-forward` that was started and killed again. Scratch under `/tmp/refm-ra3/` created and deleted.

## 1. Context verification

OBSERVED - environment matches CAMPAIGN-CONTEXT.md:
- 10 live tester pods in `ml-components`, names as listed there (3 x checkout-api-v1, 2 x checkout-api-v2,
  3 x checkout-worker-v1, 2 x payments-api-v1; last segment b4xkt mjnlq rzpzm / hcfj7 vlsl8 /
  2vwwd 7gjdg c5bdh / m7pr8 qsv2m).
- Solo detector runs in ns `rtx-4000-test`, pod `pipelineml-anomaly-detector-solo-64676d88bf-5jqgv`,
  started 2026-11-08T11:03:30Z, **0 restarts**, 15 h old.
- `ml-monitoring` has greptimedb-monitoring frontend (1) + datanode (2) + meta (1) + flownode (1).
- Supervisor forward `127.0.0.1:18086` is alive: `GET /dashboard/` -> 200 (182 KB).
- Divergence from my expectations (not a blocker): the detector's config key is `solo_mode`, not `solo`;
  the live frontend pod name is `greptimedb-monitoring-frontend-5dc56cf7f6-5mmd7` (older notes said
  `...-5d5c6f7f6-5mmd7`, which no longer exists).

## 2. Source facts (what the solo detector consumes)

### 2.1 Metric list - LIVE authoritative config
OBSERVED from the running cluster: `kubectl -n rtx-4000-test get cm pipelineml-anomaly-detector-solo-config
-o jsonpath='{.data}'` -> key `detector-common.yaml` -> top-level key **`solo_mode`** (the pod also mounts
this at `/app/analyser/config/detector-common.yaml`; there is no `/app/config/`).

`solo_mode.metrics` = **11 entries, all `contract: mandatory`** (observed verbatim):

| # | metric | kind | series_selector |
|---|--------|------|-----------------|
| 1 | `container_cpu_usage_seconds_total` | continuous | container=`workload`, name=`nonempty` |
| 2 | `container_memory_working_set_bytes` | continuous | container=`workload`, name=`nonempty` |
| 3 | `container_oom_events_total` | rare_count | container=`workload`, name=`nonempty` |
| 4 | `container_network_receive_bytes_total` | continuous | container=`""`, name=`nonempty` |
| 5 | `container_network_receive_packets_total` | rare_count | container=`""`, name=`nonempty` |
| 6 | `container_network_receive_errors_total` | rare_count | container=`""`, name=`nonempty` |
| 7 | `container_network_receive_packets_dropped_total` | rare_count | container=`""`, name=`nonempty` |
| 8 | `container_network_transmit_bytes_total` | continuous | container=`""`, name=`nonempty` |
| 9 | `container_network_transmit_errors_total` | rare_count | container=`""`, name=`nonempty` |
| 10 | `container_network_transmit_packets_total` | rare_count | container=`""`, name=`nonempty` |
| 11 | `container_network_transmit_packets_dropped_total` | rare_count | container=`""`, name=`nonempty` |

So the split is **4 continuous + 7 rare_count**, not "3 + 11": the three signals R-A3 must package are
entries 1, 2 and 4 (rx), and entry 8 (tx bytes) is a fourth continuous signal available at the same cost.
`container_oom_events_total` is rare_count, not continuous.
Source mirror of the same list: `pipelineml-anomaly-detector/deploy/k8s/solo-card6/configmap.yaml:214-284`.

### 2.2 Mandatory set / degraded rule
OBSERVED: `solo_mode.degraded.mandatory_metrics = [container_cpu_usage_seconds_total]` (single metric;
`warn_on_degraded: true`, `telemetry_fraction_computable: true`). All 11 series are `contract: mandatory`
for *model* purposes, but the degraded-fraction gate only hard-requires CPU.
Repo mirror: `deploy/k8s/solo-card6/configmap.yaml:305-310` region; source constant
`analyser/solo_mode/config.py` (`CANONICAL_METRIC_NAMES`, 11 names).

### 2.3 Cadence, tick, window (live values)
OBSERVED `solo_mode.window`: `Dt: 2d`, `dt: 30m`, **`sampling_cadence: 16s`**, `min_cycles_per_period: 2`,
`enforce_dt_less_than_Dt: true`.
OBSERVED `solo_mode.undersampling: {boxcar: {mode: jumping, over: duration, value: 5m}, auto: {enabled: true,
max_boxcar_multiple: 4, max_steps: 5}, min_effective_samples: 36}`.
OBSERVED `solo_mode.validity`: `min_point_fraction: 0.95`, `counter_block_min_fraction: 0.9`,
**`counter_max_gap: 35s`**, `wasserstein_split_half: true`, `warn_threshold: 0.75`.

- **tick = 300 s**, *derived* not configured: `config.py:277-300` `_derive_tick_seconds()` ->
  `tick_seconds = _parse_duration_seconds(boxcar.value)` = 300; validated at `config.py:473-490`
  (`dt % tick_seconds == 0`, `blocks_in_window = Dt_seconds // tick_seconds` = 576).
- `counter_max_gap` must be < tick: `config.py:879-883`.
- `sampling_cadence: 16s` is a *declared* cadence used by the fetcher/scoper
  (`analyser/data_fetcher.py:613` default `"15s"`, overridden to 16s by config); the data is **never
  resampled** - raw timestamps are kept.

### 2.4 Where the samples come from (and the exact query)
SOURCE `analyser/data_fetcher.py:215-219` -- the detector issues one SQL per (pod, metric) against the
GreptimeDB HTTP SQL endpoint:

```sql
SELECT greptime_timestamp AS ts, greptime_value AS val, container AS container, name AS name
FROM "<metric>"
WHERE greptime_timestamp >= '<tmin>' AND greptime_timestamp <= '<tmax>'
  AND pod = '<pod>' [AND cluster = '<cluster>'] [AND namespace = '<namespace>']
  AND container = '<selector.container>' AND name <> ''
ORDER BY greptime_timestamp
```
(`where` built at `data_fetcher.py:309-321`; selector clause at `data_fetcher.py:196-215`;
`ORDER BY` at `data_fetcher.py:219`.)

### 2.5 5-minute block construction (the law to reimplement)
SOURCE `analyser/solo_mode/scan.py:459` `_tick_aligned_blocks(..., tick_seconds, window_start, window_end,
aggregation, counter, max_gap_seconds, min_coverage)`; callers `driver.py:1138-1141` (3-block read) and
`driver.py:1226-1229` (full fit window).

Grid: block `j` = `[window_start + j*T, window_start + (j+1)*T)`, `T = 300`,
`j in [0, floor((window_end-window_start)/T))` (docstring `scan.py:466-480`).

- **Gauges (cpu, memory, rx/tx bytes are counters; gauges = non-counter metrics such as memory):
  value = arithmetic mean of every sample whose ts falls in the block** - `scan.py:529-530`
  (`sums[j] += v; counts[j] += 1`) and `scan.py:763-766` (`value = sums[j]/counts[j]`; `counts[j]==0`
  -> block is a gap, no coercion).
- **Counters:**
  - pair `(ts_prev, ts)` with `gap = ts - ts_prev`; `gap <= 0` or `gap > max_gap(35 s)` ->
    **that block is invalidated for that identity** (`scan.py:571-605`, reason `bad_gap`).
  - increment `= v - v_prev`, or `= v` when `v < v_prev` (counter reset), `scan.py:576-590`.
  - block index `j = int(math.ceil((ts - window_start)/T)) - 1`, kept only if `0 <= j < span_blocks`
    and `left < ts <= right` -> **right-closed `(left, right]` attribution on the LATER sample**
    (`scan.py:571,575`). A sample exactly at a block start belongs to the previous block.
  - emit only if **`n_inc >= 2`** and
    **`coverage = (last_stamp - max(left, first_prev)) / T >= counter_block_min_fraction (0.9)`**
    (`scan.py:631-655`, emission `scan.py:683-697`).
  - **block value = `sum(increments) / n_inc` (mean increment) for `continuous`** and `sum` for
    `rare_count` (`scan.py:694-697`).
- **"block not aligned" / degraded** = the counter emission gate above fired: observed 43-47 of 288
  ticks/day rejected for rx/tx bytes and 0 of 288 for cpu/memory (gauges have no coverage law).
  Cause: the trailing sample sat > 30 s before the tick boundary (spacing here is 16.4 s mean with
  10-34 s jitter), so `coverage < 0.9`.

### 2.6 Units - important correction
OBSERVED (measured against the detector's own output): **the block builder applies no unit conversion.**
A block value is the mean of raw samples (gauge) or the mean increment per sample interval (counter):
- cpu: block value ~`16.7` for a pod using ~1 core at 16.4 s spacing (seconds per *sample interval*,
  not "CPU %" - `%` would be `mean_increment / mean_dt * 100`);
- memory: block value ~`2.55e8` bytes (not MiB);
- rx bytes: block value ~`32921` (bytes per sample interval ~ 2007 B/s, not "MiB/s").
So the campaign's "CPU %, memory MiB, network MiB/s" wording is scenario framing only; **package raw
values and the detector's unit-free z-scoring is preserved**. Do not divide/convert in the lab.

### 2.7 Parity source (source of truth for rebuilt block values)
OBSERVED `GET http://127.0.0.1:18086/api/dashboard/pods/<pod>/solo?namespace=ml-components`
-> 200, **7,378,534 B, 1.95 s**. Route source: `analyser/dashboard_routes.py:3251-3255`
(`/api/dashboard/pods/<pod>/solo`, handler `get_pod_solo_diagnostics`).
Body (7.38 MB, abridged):
```json
{"tick": 1794192900.0, "window_ready": true, "cluster": "", "details_status": "ok",
 "history": [{"tick_epoch": 1794192900.0, "p_raw": ..., "p_published": ..., "label": "calibrated",
   "metrics": {"container_cpu_usage_seconds_total": {
       "observed": 16.707738333351117, "forecast": ..., "residual": ...,
       "block_attribution": {"block_start": 1794192600.0, "coverage_fraction": 0.996,
         "first_prev": 1794192589.63, "last_stamp": 1794192882.449,
         "max_pair_gap": 31.276, "n_increments": 18, "reason": "emitted"}}, ...},
   }, ...],
 "pods": [...], "reference_ticks": ..., "meta_filename": ..., "table_rows": ..., "row_count": ...}
```
VERIFIED: for tick 1794192900 (2026-11-09T02:55:00Z), cpu `observed` = 16.707738333 and my
reconstruction from the raw Greptime rows (same window, same laws) = 16.707738333, **diff 0.00e+00**.
`history` spans 288 ticks (1 day) per pod, so the lab can parity-check 288 x 3 values per pod.
For rx bytes the checker must expect `block_attribution: null` with reason `block not aligned` on ~15 %
of ticks (see 2.5) - `observed` and `residual` are then `null`/NaN and must not be compared.

## 3. Environment state (where the raw 15 s samples live)

### 3.1 Store inventory
| store | ns | holds the 10 pods at raw cadence? | retention | how it is fed |
|---|---|---|---|---|
| **GreptimeDB** `greptimedb-monitoring-frontend` svc :4000 (HTTP SQL/PromQL), :4001 gRPC, :4002 MySQL | ml-monitoring | **YES - this is the detector's own source** | **no TTL** (table option `ttl` empty) = full history since 2026-10-01 | Vector DaemonSet (`vector-system`) scrapes kubelet to the GreptimeDB Prometheus **remote_write** receiver |
| Prometheus `prometheus-5b89cd67dd-8x5p5` :9090 | istio-system | yes (same cAdvisor values), **15 s scrape** | `storage.tsdb.retention.time = 15d`; `emptyDir` (lost on restart, restarted 8x) | own cAdvisor/node-exporter/kube-state-metrics scrape jobs |
| kube-state-metrics | monitoring | metadata only (`kube_pod_container_status_restarts_total` etc.) - also landed in Greptime | same as Prometheus | Prometheus scrape -> remote_write |
| kubelet :10250 `/metrics/cadvisor` | node | source of truth, per-node, not a queryable history | none | vector + prometheus scrape it |

OBSERVED GreptimeDB physical table: `SHOW CREATE TABLE container_cpu_usage_seconds_total` ->
`ENGINE=metric`, `PRIMARY KEY (cluster, container, endpoint, id, image, instance, job, metrics_path,
name, namespace, node, pod, service)`, column `greptime_timestamp TIMESTAMP(3)`, `greptime_value DOUBLE`,
`TIME INDEX (greptime_timestamp)`. No `ttl` in `information_schema.tables` -> **no TTL**.
OBSERVED `SELECT MIN/MAX/COUNT` on that table: `t0 2026-10-01T08:29:19Z`, `t1 2026-11-09T03:02:11Z`,
**25,818,189 rows** (~38.8 days of history retained).

### 3.2 Label set that identifies one pod series
OBSERVED (full row of `container_cpu_usage_seconds_total`): `cluster=kind-michel-cluster`,
`container=workload`, `cpu=total`, `endpoint=https://172.18.0.2:10250/metrics/cadvisor`, `id=<cgroup path>`,
`image=ghcr.io/appthrust/pipelineml-tester/workload:sha-0d6bff8`, `instance=172.18.0.2:10250`,
`job=cadvisor`, `metrics_path=/metrics/cadvisor`, `name=<container-id hex>`, `namespace=ml-components`,
`node=rtx-4000-cluster-control-plane`, `pod=<pod name>`, `service=kubelet`.
- `name` = the **container id**, i.e. the identity that changes on every restart (CARD-6D3 episodes).
- `name` is **required** (`name <> ''`) to avoid double counting: OBSERVED the same pod+timestamp appears
  for 3 different series in a 1 h window - `container=workload image=...workload:sha-...` (221 rows),
  `container='' image=registry.k8s.io/pause:3.10` (220 rows), `container='' image=''` (218 rows, pod-level
  cgroup aggregate). Without `container`+`name` filters you read ~3x the samples.
- For cpu/memory the app series is `container='workload'`; for network metrics the detector's selector is
  `container=''` (netns series, whose `name` is the pause-container id and therefore changes only when the
  pod sandbox is recreated - observed 5 distinct pause ids per pod over 37 days vs 31-42 app ids).

### 3.3 How much flat load is really available
OBSERVED all 10 pods restarted (last container start) at **2026-10-30T08:45:26-37Z** and have run since
(pod age 37 d, created 2026-10-02T19:02Z). Verified per pod that the flat window contains **exactly one
identity** (`count(DISTINCT name)=1`, `count(DISTINCT instance)=1`, `count(DISTINCT node)=1`) for all three
signals -> **no counter resets inside the window**.
- **Clean flat-load window: 2026-10-30T08:45:47Z -> now = 234.25 h = 9.76 days per pod** (all 10 pods).
- Samples per pod-signal in that window (OBSERVED): cpu 51,413-51,638; memory 51,413-51,638;
  rx bytes 51,484-51,644. Total **1,546,091 rows for 10 pods x 3 signals**.
- Sample spacing inside the window (OBSERVED, payments-api-v1-m7pr8, full 234 h): median 15.9-16.4 s,
  min 10.0 s, max 34.3 s, **0 gaps > 45 s**, no duplicate timestamps, no NaN values.
- Full retention (37.3 d) per pod-signal: 196,814-197,203 rows, 17 gaps > 45 s, max gap 336 s (sparse,
  distributed, no stale markers) - includes the pre-2026-10-30 restart era, i.e. **not a single identity**.

### 3.4 Prometheus cross-check
OBSERVED `/api/v1/query` at `time=2026-10-20` -> empty; at `2026-10-26`, `10-29`, `10-31`, `11-02` ->
data. So Prometheus covers **~2026-10-26 -> now (14 d, the 15 d retention minus its 9-day-old restart)**,
which **includes the 2026-11-06 burst**. Its scrape interval is 15 s (`/etc/prometheus/prometheus.yml`
`scrape_interval: 15s`), and its `query_range` with `step=15` works over the tunnel (verified: matrix
response). It is a valid *independent parity* store (different ingestion path, same cAdvisor source).

## 4. Extraction route (proven, repeatable, read-only)

### 4.1 The route
Prefer the GreptimeDB HTTP SQL endpoint reached through a **port-forward of the Service** (stable name,
no `exec` per query, no writes):

```bash
# one-time, on the Mac (keep alive):          # one-time, on the host:
ssh -N -L 14000:127.0.0.1:14000 rtx-4000-test      # (start via ssh:)
                                                   ssh rtx-4000-test 'export PATH=$HOME/.local/bin:$PATH; \
                                                     nohup kubectl -n ml-monitoring port-forward \
                                                     --address 127.0.0.1 svc/greptimedb-monitoring-frontend \
                                                     14000:4000 >/tmp/gt_fwd.log 2>&1 &'
# then, from the Mac, one query == one bounded GET:
curl -sS -G "http://127.0.0.1:14000/v1/sql" \
     --data-urlencode "db=public" \
     --data-urlencode "sql=SELECT pod, count(*) AS n FROM \"container_cpu_usage_seconds_total\" \
       WHERE greptime_timestamp >= '2026-11-08 00:00:00' AND namespace = 'ml-components' GROUP BY pod"
```
OBSERVED both this route (local endpoint answers in ~2 s incl. tunnel) and the alternative
`kubectl -n ml-monitoring exec <frontend-pod> -- curl -s -G http://127.0.0.1:4000/v1/sql ...` work.
The exec variant needs the live frontend pod name (changes with releases) -> prefer the Service forward.

Response envelope (OBSERVED):
```json
{"output":[{"records":{"schema":{"column_schemas":[{"name":"ts","data_type":"TimestampMillisecond"},
 {"name":"val","data_type":"Float64"}]},"rows":[[1794182406391, 9186.23],[...]],"total_rows":N}}],
 "execution_time_ms":11}
```
Parse `output[0].records.schema.column_schemas[*].name` -> positional dicts; `ts` is epoch **ms**.

### 4.2 Measured cost and size (real extraction, since deleted)
OBSERVED 1 pod (`...checkout-api-v1-55d59c5477-b4xkt`) x 3 signals x full 234 h:
| metric | rows | JSON bytes | CSV bytes (iso,epoch,value) | wall |
|---|---|---|---|---|
| cpu | 51,582 | 2.10 MB | 2.62 MB | 1.0 s |
| memory | 51,582 | 2.01 MB | 2.53 MB | 1.2 s |
| rx bytes | 51,639 | 2.00 MB | 2.51 MB | 1.0 s |
Response body per query 1.43-1.54 MB; `execution_time_ms` 11-40 ms server side.
**Extrapolation for 10 pods x 3 signals over the whole flat window: 1.55 M rows -> ~61 MB JSON or
~77 MB CSV (~49 B/row).** Adding tx bytes (4th continuous) -> ~103 MB CSV. No point/size limit was hit:
a 196,814-row response (full 37 d, one signal) also succeeded (~6 MB). Disk (40 GiB free) is not a constraint.

### 4.3 Timestamp reality (do not assume a 15 s grid)
OBSERVED: **0 of 660 samples fall on a 15 s boundary**; spacing is 10.0-34.3 s with mean 16.37 s and
median 16.02 s; ~40 % of intervals are < 14.9 s (catch-up bursts after a slow scrape). No duplicates,
no NaN, **no gaps > 45 s inside the flat window**. Cause [INFERENCE]: the timestamp kept is the kubelet's
own Prometheus-format timestamp (`endpoint=https://172.18.0.2:10250/metrics/cadvisor`,
`job=cadvisor`), produced by the kubelet's housekeeping loop under a CPU-saturated node (load ~20), so it
drifts and occasionally double-fires; vector's 15 s interval is only the outer bound.
**Consequence for A3: store raw (ts, value) pairs - never resample to a 15 s/16 s grid if you want
bit-exact parity with the detector's `observed`.**

### 4.4 Burst (S4) - the decisive finding
OBSERVED (p3 tick store, `evidence/E-solo-dashboard-ops/p3-ticks.jsonl`, 9,916 rows, keys
`pod,tick_epoch,p_raw,p_published,label,calibration_state,normal_threshold,anomaly_threshold`):
the burst is **15 consecutive ticks, 2026-11-06T01:15:00Z -> 02:25:00Z** (step 300 s), all **10 pods
present at each of the 15 ticks** (109 rows above p_raw>0.5 incl. 5+4 partial tails), median
`p_raw = 0.98949`, **min 0.5139 / max 0.98952** - i.e. nearly identical across pods. Neighbouring ticks
01:05/01:10 and 02:30 are at p_raw ~0.001-0.06. Ten isolated single-pod spikes >0.5 exist elsewhere
(2026-11-06T03:35, 03:40, 23:20, 23:25, 23:30; 11-07T09:15, 18:10; 11-08T02:35, 22:55, 23:00).

OBSERVED raw samples for that window (3 h extracted, 660-670 rows, 43 s of 5-min blocks computed with the
detector's own laws): cpu block values 14.7-18.8, memory 255.7-255.8 MB, rx bytes ~5.4-5.6 KB/s - **flat,
no excursion, no gap, no reset**. Also: 11-metric scan over 00:30-02:30 shows every rare_count at 0 and
rx/tx byte ratios 0.93-1.07; detector logs at 01:15-02:25 UTC contain only `request-context - INFO`
lines (no WARN/ERROR, no `tier 2 fallback`, no `guard`).
**Conclusion: the burst has NO raw-series counterpart.** The raw 15 s samples for the window DO still
exist (2026-11-06 is inside the 9.76 d flat window and inside Prometheus' 14 d), so extraction is
feasible - but re-running the detector on them cannot reproduce the burst. `p_raw` was ~0.99 for all 10
pods simultaneously while their series were normal -> the event is detector-side (fleet-wide, identical
p-value), not a metric excursion. **S4 must be built as an injected/marker event (as the Part-1 spec
already says), with the p3 `p_raw`/`p_published` series as the only ground truth.**

### 4.5 Pod identity stability
OBSERVED restart counts (kubectl): b4xkt 40, mjnlq 41, rzpzm 31, hcfj7 31, vlsl8 30, 2vwwd 30, 7gjdg 30,
c5bdh 30, m7pr8 30, qsv2m 30; last restart 2026-10-30T08:45:26-37Z for all ten; **no renames** (pod
created 2026-10-02T19:02, name stable for 37 d). Per-pod container-id episodes over the full 37 d:
31-42 app ids (cpu/memory) and 5 pause ids (rx/tx). Earlier resets cluster on 2026-10-02 -> 2026-10-30
(incl. a run of resets 2026-10-30T04:38-08:43), then none. Detector pod itself restarted 0 times but was
recreated 2026-11-08T11:03Z (its in-memory window store was rebuilt from Greptime).

## 5. Unresolved conditions
1. `container_memory_working_set_bytes` is declared `kind: continuous` in the live config, so it takes the
   **counter** path (increments) - yet the observed block values are plain means (255.7 MB) and the
   detector's `observed` equals the mean of the raw samples. Verified numerically on one tick only.
   The Planner should have A3 assert the path per metric (compare `observed` against both laws on the
   288-tick history) rather than guess. Not resolvable from source alone here without reading the whole
   driver branch (`driver.py:1120-1200` vs `1210-1270`).
2. The 2026-11-06 burst's *cause* (detector-side) is out of R-A3 scope; only its absence from the raw
   series is established.
3. GreptimeDB window functions (`lag(...) OVER`) failed through the HTTP SQL endpoint in my probe (parse
   error), so per-pod gap statistics were computed client-side instead (cheap: 51 k rows/query).
4. Weights/data sizes on local disk were not an issue (77 MB for the full package), so no further
   capacity check was needed.

## 6. Commands run (condensed; all read-only)
```bash
ssh rtx-4000-test 'export PATH=$HOME/.local/bin:$PATH; kubectl config current-context; kubectl get ns -o name'
ssh ... 'kubectl -n ml-components get pods -o wide'
ssh ... 'kubectl -n ml-components get pods --no-headers -o custom-columns="NAME:.metadata.name,
   RESTARTS:.status.containerStatuses[0].restartCount,STARTED:.status.containerStatuses[0].state.running.startedAt"'
ssh ... 'kubectl -n rtx-4000-test get cm pipelineml-anomaly-detector-solo-config -o jsonpath="{.data}"' | python -c yaml  # <- live solo_mode
ssh ... 'kubectl -n ml-components exec pipelineml-anomaly-detector-7579bd8777-lklm5 -- sh -c
   "find / -maxdepth 5 -name *detector*common*; cat /proc/1/cmdline"'      # -> /app/analyser/config/detector-common.yaml
ssh ... 'kubectl -n ml-monitoring exec <frontend> -- curl -s -G http://127.0.0.1:4000/v1/sql -d db=public -d sql=...'
ssh -N -L 14000:127.0.0.1:14000 rtx-4000-test   # + remote: kubectl port-forward svc/greptimedb-monitoring-frontend 14000:4000
curl -sS -G 'http://127.0.0.1:14000/v1/sql' -d db=public -d 'sql=SHOW CREATE TABLE "container_cpu_usage_seconds_total"'
curl -sS -G 'http://127.0.0.1:14000/v1/sql' -d db=public -d 'sql=SELECT MIN(greptime_timestamp),MAX(greptime_timestamp),count(*) FROM "container_cpu_usage_seconds_total"'
curl -sS -G 'http://127.0.0.1:14000/v1/sql' -d db=public -d 'sql=SELECT pod,count(*),min(greptime_timestamp),max(greptime_timestamp) FROM "<metric>" WHERE ... GROUP BY pod'
ssh ... 'kubectl -n istio-system port-forward pod/prometheus-5b89cd67dd-8x5p5 19090:9090 &  curl /api/v1/query?time=...  curl /api/v1/status/flags'
curl -s -o /dev/null -w '%{http_code} %{size_download}' 'http://127.0.0.1:18086/api/dashboard/pods/<pod>/solo?namespace=ml-components'
```
Files read (source facts): `analyser/data_fetcher.py:196-219,300-321,613`, `analyser/solo_mode/scan.py:459-500,
507-540,570-700,763-766`, `analyser/solo_mode/config.py:120,277-300,473-490,879-883`, `analyser/solo_mode/driver.py:26,
1138-1141,1226-1229,1429`, `analyser/dashboard_routes.py:3251-3255`,
`deploy/k8s/solo-card6/configmap.yaml:90-400`, `evidence/E-solo-dashboard-ops/p3-ticks.jsonl`.

## 7. Recommended extraction recipe (hand this to E for `scripts/package_flat_load.py`)

```python
# constants (verified 2026-11-09)
SQL_BASE = "http://127.0.0.1:14000/v1/sql"        # ssh -N -L 14000:127.0.0.1:14000 rtx-4000-test
DB = "public"; NS = "ml-components"; CLUSTER = ""  # keep empty: no cluster filter, as the detector does
WINDOW_START = "2026-10-30 08:45:47.911"           # last container restart of all 10 pods (UTC)
METRICS = [  # (table, container selector, kind) - exactly the detector's selectors
  ("container_cpu_usage_seconds_total",   "workload", "continuous"),
  ("container_memory_working_set_bytes",  "workload", "continuous"),
  ("container_network_receive_bytes_total","",        "continuous"),
  ("container_network_transmit_bytes_total","",       "continuous"),   # optional 4th
]
PODS = [ ... 10 exact pod names ... ]
SQL = ('SELECT greptime_timestamp AS ts, greptime_value AS val, container AS container, name AS name '
       'FROM "{metric}" WHERE greptime_timestamp >= \'{t0}\' AND greptime_timestamp <= \'{t1}\' '
       "AND pod = '{pod}' AND namespace = '{ns}' AND container = '{cont}' AND name <> '' "
       'ORDER BY greptime_timestamp')     # data_fetcher.py:215-219, byte-for-byte
# per (pod, metric): one GET with params {"db": DB, "sql": SQL}; parse output[0].records
#   -> column_schemas gives names; ts is epoch MILLISECONDS; write ONE csv per (pod, metric)
#   columns: ts_epoch_ms, value, container, name   (identity needed for episode/reset checks)
# validation per file (hard fails): 50_000 <= rows <= 53_000; ts strictly increasing; 5 < min dt;
#   max dt < 60 s; count(distinct name) == 1 (else the window straddles a restart -> exclude);
#   warm-up: skip the first 6 samples after WINDOW_START (container start transient)
# then: build 5-min blocks with the laws of §2.5 and parity-check 288 ticks/pod against
#   GET http://127.0.0.1:18086/api/dashboard/pods/<pod>/solo?namespace=ml-components
#   -> history[i].metrics[<metric>].observed  (must match to <1e-9 when reason == "emitted")
```
Hard rules for E: sequential queries (no parallel fan-out, the node is CPU-saturated), one bounded
time-window per query (no unbounded `SELECT *`), never write to Greptime, never restart anything,
delete the port-forwards when done. Budget: ~40 s and ~40 MB of HTTP for 10 pods x 3 signals.

## Recommendations for the Planner
1. Package from **GreptimeDB** (the detector's own source) via the Service forward on `:14000/v1/sql`;
   use Prometheus (istio-system) only as an independent parity/coverage cross-check.
2. Use the **exact** detector series predicate `container=<selector> AND name <> ''`; without it every
   pod-signal is duplicated ~3x (workload / pause / pod-level cgroup series).
3. Available clean flat load is **9.76 days (234.25 h), 2026-10-30T08:45:47Z -> 2026-11-09T03:00Z**, single
   container identity per pod per signal, zero gaps > 45 s. That is ~10x the 2-day fit window - ample.
4. Package **4 continuous signals** (cpu, memory, rx bytes, tx bytes), not 3: tx bytes is free and is the
   detector's 4th continuous metric; keep the 7 rare_count metrics out unless the lab needs them (~+40 MB).
5. Store **raw (ts, value)** pairs with the identity columns; do **not** resample to 15/16 s - there is no
   regular grid (10-34 s jitter) and resampling breaks bit-exact parity with the detector.
6. No unit conversion: block values are means of raw samples / means of increments (cpu ~16.7 s per
   sample interval, memory in bytes, rx in bytes per interval). Keep the detector's unit-free z-scoring.
7. Reproduce the block laws exactly (§2.5): gauges `[left,right)` mean; counters right-closed `(left,right]`,
   `gap > 35 s` invalidates the block, `n_inc >= 2`, `coverage >= 0.9`, value = mean increment.
8. Use `/api/dashboard/pods/<pod>/solo?namespace=ml-components` (7.4 MB, 288 ticks) as the parity oracle;
   expect `block not aligned` for ~15 % of rx/tx ticks (that is normal, not a bug).
9. **S4 burst cannot be reproduced from the series**: 15 fleet-wide ticks (2026-11-06T01:15-02:25Z) with
   p_raw ~0.99 on all 10 pods while cpu/memory/rx were flat. Build S4 as an injected/marker event; carry
   the p3 `p_raw`/`p_published` (10 pods x 15 ticks) as the only observable truth.
10. Size budget: 1.55 M rows, ~61 MB JSON / ~77 MB CSV for 10 pods x 3 signals for the whole window
    (+26 MB for tx bytes). Fits trivially in 40 GiB; still write gzipped CSV/parquet to keep the repo light.
11. Record in the MANIFEST: window start/end, per-file row counts, per-pod container id, Greptime table
    timestamps, and the parity max-abs-diff obtained.
12. Keep queries sequential and bounded (measured 1.0-1.2 s and 1.4-1.5 MB per pod-metric query) - the host
    runs the tester workload at load ~20; do not batch 10 pods in parallel.

## Open questions that need an operator decision
- None blocking. One clarification would help: the live `solo_mode` marks `container_memory_working_set_bytes`
  as `kind: continuous`, while the observed block values are plain sample means; A3 should be told to
  verify per-metric which law the detector applied (both are reproducible from the same raw data).
