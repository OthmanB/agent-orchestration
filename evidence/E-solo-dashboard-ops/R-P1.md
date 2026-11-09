# R-P1 — freshness window (`data_flow_health`, config-only): current-source + live facts

Date: 2026-11-06 (windows ~05:07–05:19 and ~05:22–05:28 UTC). Scope: read-only. Repository
`pipelineml-anomaly-detector`, branch `feature/cnn2dlstm-bayesian-statistical-detector-v2`.
Cluster facts via `ssh rtx-4000-test … kubectl --context kind-rtx-4000-cluster -n rtx-4000-test`;
API facts via `http://127.0.0.1:8080/api/dashboard/...` (live solo exporter).
Artifacts (same dir): `R-P1-sampler.py`, `R-P1-pods-samples.jsonl` (74 samples × 10 pods,
05:07:05→05:19:15 UTC, 10 s grid), `R-P1-publish.jsonl`, `R-P1-publish2.jsonl`,
`R-P1b-tscount.py`, `R-P1b-tscount.jsonl` (22 probes × 10 pods, 05:22:35→05:27:50 UTC, 15 s grid).

## 0. CONTRADICTIONS against the binding documents (read before planning)

**C1 — per-pod publish cadence is ~300 s, not 60–190 s.** Report §1 ("a given pod's new data
lands roughly every 60–190s, not every 30s") is wrong. Measured 20 consecutive per-pod publish
intervals: min 300 s, median 301 s, p95 303 s, max 303 s. All ten pods publish **exactly one
result per 300 s scoring tick**, in three stable phase groups (+19.5 s / +49.5 s / +81 s after the
tick boundary: 3 / 5 / 2 pods). [LIVE]
Consequence: vision P1 option A's arithmetic (`3–5 × 30 s = 90–150 s`, vision §P1) would leave
every pod red ~50 % of the time (measured at a 150 s window: 47–55 % fresh). The window must
exceed one tick.

**C2 — the UI-green window is `stale_age_multiplier × 30 s`, not `degraded_age_multiplier × 30 s`.**
Report §1 line 34 ("fresh if age ≤ 1.0 × 30s") understates the live green window (it is 60 s).
`_data_freshness_payload` maps **fresh *and* degraded** to `state="fresh"` / `FLOW_ACTIVE`
(dashboard_routes.py:2681-2686). So raising `degraded_age_multiplier` alone — the report's
fix-list row #1 (report §Consolidated fix list) and vision P1 option A — is a **no-op for
Indicator B, the pipeline status and the chart**, and if raised above the still-2.0
`stale_age_multiplier` the exporter **fails its startup validation** (config_loader.py:469-473).
`degraded` only surfaces in two
places: the chart-point tooltip (`point.freshness_state`) and `drift_status`, and as a
pass-through for `scoring_eligibility` (degraded → scoreable).

**C3 — a multiplier-only change cannot move the window past 300 s.** `exporter.ttl_seconds: 300`
purges the snapshot `_store` entry (`now - updated_at > ttl` → `_invalidate_pod_eligibility(
keep_point_history=False)`, exporter.py:1253-1291), then the inventory row
(`discovered_at + ttl`, exporter.py:1297-1303, which also pops `_point_history` directly), and in
solo mode `_solo_cleanup_stale` repeats it (`age > ttl` → invalidate with
`keep_point_history=False`, exporter.py:2833/2904 → 1866/1908-1909). Effective green window =
`min(stale_multiplier × 30, ttl_seconds)`. Observed max entry age is 303 s vs TTL 300 s — every
pod's entry sits **on the purge boundary each cycle**.

**C4 — `last_seen_data_age_seconds` is NOT the freshness clock.** `_resolve_last_seen_payload`
takes the newest of (snapshot `updated_at`, inventory `discovered_at`, error timestamp), and
`discovered_at` is stamped only on (re)registration — the inventory row expires on its own 300 s
TTL and is re-registered, so the reported age silently resets mid-cycle while the snapshot keeps
ageing: e.g. 05:14:25 UTC b4xkt read `age=4.0 s` while `data_freshness_state` was still `stale`
(snapshot `updated_at` = 05:10:19.5). Measured offset of the shadow timestamp from the pod's true
publish: −60 s, −31 s, +61 s, +91 s, +121 s (stable per pod). This divergence hit
**123/740 pod-samples (16.6 %; 6–18 samples per pod)**. Sizing the window from
`last_seen_data_age_seconds` understates the real age by up to 40 s and hides the purge cycle.
Reliable observables: `data_freshness_state` and the publish instants
(`/api/dashboard/pods/<pod>/timeseries`, last point `t` = publish wall clock).

## 1. Freshness semantics (current source)

| fact | anchor |
|---|---|
| age = `now - snapshot.updated_at`; `age > cadence·stale` → `stale`; else `age > cadence·degraded` → `degraded`; else `fresh` (strict `>`, so age == threshold is still fresh/degraded) | dashboard_routes.py:2280-2310 (2304-2310) |
| cadence = `exporter.refresh_interval_seconds` (30) exposed as `effective_cadence_seconds` | exporter.py:3985 (also 3903); [LIVE] `/api/dashboard/system` → `effective_cadence_seconds: 30` |
| `degraded`/`fresh` → `{state: fresh, reason: FLOW_ACTIVE}`; `stale` → `{stale, AGE_EXCEEDED_FRESHNESS}`; entry `None` → `stale` with `FLOW_TIMESTAMP_UNAVAILABLE` (inventory `scored`) / `FLOW_NOT_FLOWING` / `FLOW_SIGNAL_UNAVAILABLE` | dashboard_routes.py:2651-2694 |
| pipeline: `fresh`+inventory `scored` → `active`; `stale`+`AGE_EXCEEDED_FRESHNESS` → `stale`; else `unknown` | dashboard_routes.py:2705-2735 |
| `scoring_eligibility`: freshness `stale` → `"stale"`, `unavailable` → `"offline"`, `degraded` → falls through to `scoreable`/`unscoreable` | dashboard_routes.py:2356-2401 |
| validation: both multipliers finite and > 0; `stale > degraded` else `ConfigurationError`; **no upper bound** | config_loader.py:128-139, 463-473 |
| values are read at process start (`build_config`) — a ConfigMap edit needs a solo pod restart | config_loader.py / exporter.py:632 |

Consumers of the two multipliers (all recompute the same tri-state per request):
1. `/api/dashboard/pods` → `data_freshness_state`, `indicator_b_state` (indicator B label
   `fresh`→"Recent data available" else "No recent data", dashboard_routes.py:2767-2772; UI dot
   `shared_selectors.js:316,329-334`, legend/filter `index.html:736-744`).
2. `pipeline_status.state` → pod-detail overall pill turns **critical** on `stale`
   (`index.html:1383-1400`, `pipeline-flow-status`).
3. `scoring_eligibility.state` (dashboard_routes.py:2356; surfaced in `/pods`, `/current`,
   `/overview`, `/pods/<pod>/solo-diagnostics` at 4246-4248).
4. `/overview` per-pod aggregation (dashboard_routes.py:4277-4279) and `/current`
   `data_freshness` + `drift_status` (dashboard_routes.py:807, 3991-4021).
5. Chart-point `freshness_state` per point (dashboard_routes.py:3227-3231) → hover "Freshness:
   fresh|degraded|stale" (`index.html:1255,1292`); marker colour is decision-based, not freshness.
6. NOT affected: the health-panel `health-freshness` chip (`index.html:1116-1120`) is
   `shared_state_freshness`, derived from cadence/ttl (`_derive_shared_state_freshness`,
   exporter.py:588-600), not from these
   multipliers; `hide-stale-pods` uses `pod_families_config` + drift, not freshness.

## 2. Repo ConfigMap vs live ConfigMap — AGREE

| key | repo `deploy/k8s/solo-card6/configmap.yaml` | live `cm pipelineml-anomaly-detector-solo-config` `.data.detector-common.yaml` |
|---|---|---|
| `dashboard.data_flow_health.degraded_age_multiplier` | `1.0` (line 169) | `1.0` (line 150) |
| `dashboard.data_flow_health.stale_age_multiplier` | `2.0` (line 170) | `2.0` (line 150) |
| `exporter.refresh_interval_seconds` | `30` (line 95) | `30` (line 77) |
| `exporter.ttl_seconds` | `300` (line 96) | `300` (line 78) |

So live green window = 2.0 × 30 = **60 s** against a 301–303 s publish cadence → the observed
flicker.

## 3. Live measurement (74 samples/pod, 10 s grid, 05:07:05–05:19:15 UTC)

Method: sample `/api/dashboard/pods`, reconstruct `age(t) = t - last_publish`. Publish instants
were taken from the exact `updated_at`/`timeseries` timestamps (`R-P1-publish.jsonl`) and the
`fresh`-run starts. **Validation: the reconstructed age with the *current* 30/60 s thresholds
reproduces the reported `data_freshness_state` on 740/740 pod-samples (100 %)** — the model of
"one publish per 300 s tick, phase-stable" is confirmed, and C4 (last_seen drift) never affects
the state.

| pod (suffix) | phase after tick boundary | publishes observed | gap (s) | max sampled age (s) | fresh % now (60 s) |
|---|---|---|---|---|---|
| b4xkt | +19.5 s | 05:05:17.9 → 05:10:19.5 → 05:15:20 | 302 | 298.2 | 16.2 |
| mjnlq | +19.5 s | same wave | 302 | 298.2 | 16.2 |
| rzpzm | +19.5 s | same wave | 302 | 298.2 | 16.2 |
| hcfj7 | +49.9 s | 05:05:48 → 05:10:49.9 → 05:15:50.5 | 301 | 297.2 | 16.2 |
| vlsl8 | +50.0 s | same wave | 302 | 297.2 | 16.2 |
| 2vwwd | +50.2 s | same wave | 302 | 297.2 | 16.2 |
| 7gjdg | +50.4 s | same wave | 302 | 297.2 | 16.2 |
| c5bdh | +50.8 s | same wave | 302 | 297.2 | 16.2 |
| m7pr8 | +81.1 s | 05:06:18.5 → 05:11:21.1 → 05:16:21 | 303 | 297.2 | 18.9 |
| qsv2m | +81.2 s | same wave | 303 | 297.2 | 18.9 |

Fleet intervals: n=20, min 300.0, median 301.0, p95 303.0, max **303.0** s.
Max age reached just before a reset: **303 s** (raw `last_seen_data_age_seconds` maximum was only
266.5 s — see C4; do not use it as the bound).

Per-sample fresh fraction (replay of the reconstructed ages, all 10 pods):

| W = multiplier × 30 s | 60 (now) | 90 | 150 | 270 (9.0) | 300 (10.0) | 330 (11.0) | 390 (13.0) | 450 (15.0) |
|---|---|---|---|---|---|---|---|---|
| fleet mean | 16.7 % | 27.0 % | 51.0 % | 91.9 % | 100 %* | 100 % | 100 % | 100 % |

\* W=300 is knife-edge: the *true* age reaches 303 s, i.e. ~3 s of red per cycle that a 10 s grid
cannot resolve. Anything ≤ 300 s is unsafe.

## 4. Recommendation (ONE value pair, arithmetic shown)

**`dashboard.data_flow_health.degraded_age_multiplier: 11.0`** (11.0 × 30 s = **330 s**)
**`dashboard.data_flow_health.stale_age_multiplier: 13.0`** (13.0 × 30 s = **390 s**)
**plus `exporter.ttl_seconds: 900`** (mandatory, see §5).

Arithmetic against the measured worst case (max gap = 303 s):
- 330 s = 303 + 27 s → a healthy pod never even enters the degraded band (27 s = 0.9 poll periods
  of jitter headroom).
- 390 s = 303 + 87 s ≈ worst gap + 2 poll periods (60 s) + 27 s slack → no red flash even if a
  publish slips by two poll cycles.
- Validation: 0 < 11.0 < 13.0 ✓ (config_loader.py:463-473); no upper bound ✓.
- Semantics preserved: one missed tick (gap ≈ 600 s) → 330–390 s = degraded (green),
  > 390 s = stale (red) for ~210 s, which is the intended "one tick late is not an alarm,
  two ticks is".
- `ttl_seconds = 900 ≥ 390 (stale window) + 300 (one full tick) + 30 (poll) = 720` ✓.

**Acceptance (vision P1: each pod fresh ≥ 90 % of the time under flat load): satisfied with
margin — 100 % of samples for all ten pods** (74/74 each; time-weighted 390/303 → capped at
100 %), versus 16.2–18.9 % today and 91.9 % at the minimum acceptable 9.0 (which is knife-edge:
0.9 × 303 = 272.7 s of a 303 s cycle, no jitter headroom).
Minimum compliant value: `stale ≥ 303/30 = 10.1`. Cheaper alternative if a 360 s window is
preferred: `degraded 11.0 / stale 12.0` (still 100 % sampled, 57 s headroom).

## 5. What makes a multipliers-only ConfigMap change insufficient

1. **TTL cap (hard blocker for any window > 300 s).** Snapshot entries, inventory rows and
   `_point_history` are purged at `ttl_seconds = 300` (exporter.py:1278-1291, 1297-1303,
   `_solo_cleanup_stale` 2833/2904). With `stale_multiplier = 13.0` but ttl 300, a pod would
   still flip to `stale` with reason `FLOW_TIMESTAMP_UNAVAILABLE` at 300 s — the fix would look
   "implemented but ineffective". `exporter.ttl_seconds` is in the *same* ConfigMap
   (`detector-common.yaml`), so this stays a config-only package, but it **must** be in it.
2. **The same TTLs empty the pod-level timeline (report Issue 8) — and the empty window is long.**
   [SOURCE] `/timeseries` reads the in-memory ring only and has **no WAL fallback** (`get_chart_history`,
   exporter.py:3845-3862 → `[]` when the deque is absent). The ring is wiped by three TTL/scope purges
   (exporter.py:1278-1291 store TTL, 1297-1303 inventory TTL, 2904 `_solo_cleanup_stale`) and
   refilled by the solo cold restore (`read_scored_history` → deque rebuild, exporter.py:2540-2560)
   or one live append per tick (2461-2468). [LIVE] probe of all 10 pods every 15 s, 05:22:35→05:27:50Z
   (22 probes, `R-P1b-tscount.jsonl`): **every pod went 60 → 0 → 60 once per cycle**, zero-window
   **30–150 s measured (180–210 s censored at the window edges)**; **94/220 pod-samples (42.7 %)
   showed an empty timeline**; one pod came back with **1 point** (live append, cold restore not yet
   run). The zero-set rotates (05:15:04Z: 6/10; 05:23:16Z: 4/10; over 05:22–05:27: 10/10 at some
   point), and the solo pod itself read 0 points at 05:16Z and 60 at 05:23Z. So the panel is not
   "empty because data is fresh" and not a missing/retryable read — the deque is genuinely absent
   ~40 % of the time. Raising ttl to 900 makes the wipe happen every 3 cycles instead of every 1:
   the store-TTL path (1278-1291) then never fires for a publishing pod (max age 303 < 900) and
   `_solo_cleanup_stale` (2904) likewise, so **only the inventory path (1297-1303) remains** —
   `discovered_at` is still stamped solely on (re)registration, so rows still expire every 900 s and
   the cold restore then repopulates 60 points. Empty-panel fraction should therefore drop ~3×
   (≈14 %), **not to zero**. P1 reduces Issue 8's episodes; it does not eliminate them — only a
   `/solo`-backed render (R-P2's recommendation) or a code change removes them. Note that the code
   change is not free-standing: see item 4, it must also key the inventory purge on the publish
   time, and is inert under `ttl 300`.
3. **Non-TTL wipers exist in `_solo_cleanup_stale`** (exporter.py:2872-2904): besides `age > ttl`,
   the pod is marked stale — and its ring wiped — when the store entry is gone, or when
   `not calibrated and pod_key in self._solo_canonical_children.values()` (2878-2889, "fraction-only
   (raw) pods … NOT stale here"). Our ten pods publish raw (`p_published == p_raw`), so they hit only
   the TTL clauses today; if P3 ever gives them a canonical child, the blanking stops being purely
   TTL-driven and the ttl raise would no longer bound it.
4. **The code one-liner only works together with the ttl raise.** The inventory purge tests
   `now - discovered_at > ttl` (exporter.py:1297-1300). Stamping `discovered_at` on publish makes
   that age range `0 … ~303 s` (publish → next publish), so:
   - **`ttl 900` alone** → rows still expire at 900 s → 1 wipe per 3 cycles (the ~14 % residual
     above);
   - **stamp-on-publish alone, `ttl 300`** → the age exceeds 300 only in the ~3 s before the next
     publish, so wipes fall from 1/cycle to ≈1 per 10 cycles (a 30 s poll grid rarely lands in that
     window) — reduced, not removed;
   - **both** → the inventory row never expires for a live pod, so the ring is never wiped
     (Issue 8 eliminated). The minimal form has **two no-op traps**, both verified against the row
     shapes:
     1. the inventory entry **never carries `updated_at`** (created with `discovered_at` only,
        exporter.py:2439-2460; the publish-path update touches status/probability/calibration only,
        2420-2436) → `max(v.get("updated_at"), v.get("discovered_at"))` *inside the inventory loop*
        silently degenerates to `discovered_at`;
     2. `_store` is keyed by an **8-tuple** `(namespace, workload, "solo", pod_full_name, cluster,
        pod_family, match_mode, method)` (2360-2368), not by the inventory's `"ns/cl/pod"` string →
        `self._store.get(k, {})` also returns `{}` and does nothing.
     Correct form, reusing the existing resolver (2911-2921):
     `age_ref = max(float(v.get("discovered_at", 0.0)),
     float((self._solo_entry_for(k) or {}).get("updated_at", 0.0)))`.
     Mode safety in the shared purge: an **external** inventory key is the bare pod name
     (3052-3061, `_inventory[pod_full_name]`), so `_solo_entry_for` returns `None` on its `split("/")`
     yielding < 3 parts, and `age_ref` falls back to `discovered_at`. That is a **double** guard: even a
     hypothetical 3-part external key could not match, because the resolver also requires
     `key[2] == "solo"` (2918-2920) while external `_store` rows carry `phase` in that slot (3361-3364).
     So external TTL semantics are bit-identical and no mode branch is needed.
     No ghost risk: a dead pod never reaches the publish-path update, so its `discovered_at` freezes
     at its last publish and the row still expires at `ttl` — the ghost warning at 2744-2746 concerns
     the gated/restore creation branch (2739-2752), which does not publish and must not re-stamp.
5. **No "blank less often" effect for restore-gated pods.** `_solo_restore_unavailable` refreshes an
   *existing* row's `status`/`unavailable_reason` but never its `discovered_at` (docstring "the row's
   age is never refreshed with now", exporter.py:2735-2739); `discovered_at: now_epoch` appears only
   in the creation branch for a row that does not exist yet (2748-2750). So the purge clock of a
   publishing pod is set at first registration and is not touched afterwards — the per-pod
   differences in empty *duration* (30 s … 210 s) reflect refill latency, not `discovered_at`
   bookkeeping.
6. **Purge race is live today:** max entry age 303 s vs ttl 300 s. A slower poll or a missed tick
   purges the entry *and* the chart history, so indicator B shows `stale` and eligibility
   `offline` even though the detector is healthy. ttl 900 removes the race; the multipliers alone
   cannot.
7. **Other behaviour that changes with the same knobs** (expect this in review): chart-point
   tooltip `freshness_state`, `/current` `drift_status`, and `scoring_eligibility` all use the same
   pair; `hide-stale-pods` filtering uses `pod_families_config` (untouched). The health panel chip
   is *not* driven by the multipliers but **is driven by `ttl_seconds`**:
   `_derive_shared_state_freshness` returns `fresh` for age ≤ refresh (30 s), `degraded` for
   age ≤ ttl, else `stale` (exporter.py:588-600) — raising ttl to 900 widens that chip's
   `degraded` band from 300 s to 900 s. [LIVE] the chip already reads `degraded`/"no recent data"
   whenever the ~90 s solo scan leaves `last_poll_at` older than 30 s (observed at 05:06:19Z, then
   `fresh` at 05:21:25Z), so the widened band makes it *less* likely to show `stale`, not more.
8. **Restart required, and the blast radius is one pod.** The ConfigMap is mounted as a directory
   at `/config` (`CONFIG_FILE=/config`, `deploy/k8s/solo-card6/deployment.yaml:74-79, 106-108`);
   there is no config watcher (no reload-on-change code in `analyser/*.py`; `cache_manager.py:70`
   "does NOT reload during server runtime"), so a rollout is mandatory.
   [LIVE] `rtx-4000-test` holds exactly **one** deployment, `pipelineml-anomaly-detector-solo`
   (1/1, pod `…-66769bc7cf-47rv2`), and it is the only workload mounting this ConfigMap — so the
   rollout touches only our detector. Do **not** restart the tester `ml-components` pods (they are
   the observed workload) and do not widen the restart beyond this deployment.
9. No pod shows data arriving slower than 5 min under flat load (max 303 s), so a config-only fix
   is sufficient *for the freshness window*; the only structural addition needed is the ttl raise.
