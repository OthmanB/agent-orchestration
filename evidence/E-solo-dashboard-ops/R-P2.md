# R-P2 — UI batch (six vision items): current-source + live anchors

R-P2-ui-source, 2026-11-06. Repo `pipelineml-anomaly-detector`, branch
`feature/cnn2dlstm-bayesian-statistical-detector-v2`. The working tree is **byte-identical to what the pod serves**
(index.html 115297 B, shared_selectors.js 34192 B: `curl -sI` Content-Length [LIVE] == `wc -c` [SOURCE]).
Tags: **[LIVE]** = observed on `http://127.0.0.1:8080` (curl / real Chromium via the OMP `browser` helper);
**[SOURCE f:l]** = repo file:line; **[INFER]** = my reading.

## 0. Corrections / additions to the established facts

**C1 — Issue 6 reproduces NOW; the mechanism is a per-pod cyclic TTL pop of the in-memory chart ring (NOT a store
failure, NOT a presentation bug).** 05:10Z `/timeseries` returned **60 points**
(first 00:15:00 prob 0.2354448465377041; last 05:10:19 prob 0.1679755553291581; `decision` normal/undecided;
`freshness.state` stale); at 05:16Z **0 points on 6 consecutive probes**, with and without `namespace/cluster`
[LIVE]. The open dashboard then showed `#timeseries-chart` = "No timeseries data available",
`#chart-point-count` = "0", `#chart-last-updated` = "2:15:12 PM", while `/solo` still had 288 ticks and
`solo-prob-chart` rendered [LIVE]. Same-tick values: first **0.2354 vs 0.22503628121605632** (differ), last
**0.1679755553291581 vs 0.1679755553291581** (identical) [LIVE] → **two independent stores [SOURCE]:**
`/timeseries` reads the in-memory `_point_history` deque [exporter.py:3824-3883; solo writer keyed
`ns//cl//pod` exporter.py:2459-2468, external writer keyed by full name exporter.py:3431-3435], `/solo` reads the
WAL-backed solo history - hence the differing first-tick value and the identical last tick.
The ring is popped **per pod-key** by three purges, each with `keep_point_history=False`: store TTL
[exporter.py:1258-1291], inventory TTL (`self._point_history.pop(k, None)`) [exporter.py:1293-1300], and
`_solo_cleanup_stale` [exporter.py:2845-2904]; the code says it outright - "filter the in-memory chart history;
the durable WAL is never touched" [exporter.py:2899-2901]. It repopulates when that pod is scored again, so the
empty window is **per-pod and cyclic**: live 05:23:16Z, **4/10** pods at 0 (rzpzm, hcfj7, vlsl8, 2vwwd) and 6/10 at
exactly **60** spanning `00:25:00Z -> 05:23Z`, a *different* set than the 05:15:04Z sample (6/10 empty) [LIVE,
corroborating R-P1-freshness §5.2]; the solo pod itself was 0 at 05:16Z and 60 at 05:23Z [LIVE]. Retrying does not
help (6/6 zero probes). **So the external `/timeseries` path is not a reliable source for a solo timeline** - the
client-side `/solo` render (§4) bypasses the wiper entirely. (The WAL-backed cold restore does rebuild the deque, but only
on re-entry - `state_store.read_scored_history` + `setdefault(deque)` with tick dedupe, exporter.py:2544-2562 - never on
read: `get_chart_history` returns `[]` for an absent deque, exporter.py:3848-3850.)

**C2 — the residual CDF is per METRIC, not per tick:** `reference_models[<metric>].residual_cdf` =
`{semantics, n_residuals, points, residuals}`; `tick.details.residual_cdf` does **not** exist [LIVE key dumps].
`points` = `[[residual_value, cdf_value], …]` sorted by value (**570**); `residuals` = `[[ts, residual], …]` raw
samples (**570**); `n_residuals` = 570 = `points.length` [LIVE]. The code states the semantics itself
[SOURCE analyser/solo_mode/diagnostics.py:527-541]; mid-rank ECDF `(below+0.5)/N` [SOURCE analyser/solo_mode/noise.py:692-717].
`latest_recorded_residual` = `{block_start, residual, expected, observed, model_t0}` from the model's LAST persisted
residual [SOURCE diagnostics.py:545-563]; live `{block_start:1793938072.0, residual:-1.3002623,
expected:16.513230822497, observed:15.21295824996882, model_t0:1793941200.0}` [LIVE].

**C3 — marker bug, exact numbers:** `y: [1.0]` hard-coded [SOURCE index.html:2190]; true
`cdf(latest.residual)` = **0.09561443680791193**, and the latest residual is an **exact element of `points`**
(nearest-point distance 0.0) [LIVE] → an exact lookup suffices today; linear interpolation is only the general
fallback (right-continuous step, `F(r-) = (below+0.5)/N`).

**C4 — no "dashboard mode" exists anywhere.** `/api/dashboard/system` keys: `analysis_errors_total, backend_mode,
client_refresh_interval_seconds, configured_scope, contract_failure_count, contracts, dashboard_refresh,
degraded_dimensions, event_history, exporter_snapshot, freshness_dimensions, history_purge_available, history_store,
maintenance_indicators, tier2_active`; `/api/dashboard/pods` rows have `active_model_family, alert_state,
analysis_state, data_freshness, …` and **no mode/flag** [LIVE]. Client-side solo is per-selection:
`isSoloSelection` [SOURCE index.html:1652-1666]; payload `mode:"solo"` arrives only after a selection
[SOURCE index.html:2464-2480]. Any "hide dead surfaces in solo" gate must ride the selection (adding a field = API change).

**C5 —** `/solo` payload is **7,374,932 B / 288 history rows**, re-fetched on the **5 s** refresh tick
[LIVE + SOURCE index.html:1066-1075]. New panels must reuse it, not add fetches.

**C6 — retraction of a mid-investigation note:** "the solo panel stays hidden" was a mid-refresh snapshot;
`#solo-panel` is visible and populated in steady state [LIVE]; `soloRenderSummaryBadges` unhides it on the first good
payload [SOURCE index.html:1871-1875].

---

## 1. CDF panel → PDF (left) + CDF (right), marker on the curve

**Current code** `soloRenderCdfChart` [SOURCE index.html:2157-2217], called with `model =
payload.reference_models[soloCurrentMetric]` from `soloRenderMetricCharts` [2074-2094]:
`points = model.residual_cdf.points` [2173]; CDF trace `'Residual CDF'` = `x: pts.map(p=>p[0])`, `y: pts.map(p=>p[1])`
[2175-2183]; `latest = model.latest_recorded_residual` [2186]; marker `x:[latest.residual], y:[1.0]` [2186-2194];
annotation "latest residual/expected/observed/cdf at marker" [2195-2204]; render
`soloRenderChart('solo-cdf-chart', traces, { xaxis:{type:'linear'}, annotations })` [2216]. No axis titles.

**Marker fix shape:** compute `cdfAtLatest = exact(points, latest.residual) ?? lerp(points, latest.residual)`
(exact if a point is within eps; else bracket neighbours; guard `n<2` and a null/NaN `latest`); use it for the marker
`y` **and** the annotation text, and render "n/a" rather than a fabricated 0 when absent.

**PDF with NO API change** — both sources are already in the payload: **(a)** `residual_cdf.residuals` = 570
`[ts, residual]` samples → client-side histogram/KDE (the code exposes them for exactly this); **(b)** finite
differences of `points` (same distribution, noisier tails, no extra structure). **Recommend (a)**.

**Container / subplot:** the card is `<h3>Residual CDF (current model)</h3>` + `<p class="muted" id="solo-cdf-note">`
+ `<div id="solo-cdf-chart">` [SOURCE index.html:854-858]; `.card` [142], `.chart-wrap` [461].
**Existing 2-column precedents:** `.panel-grid` [402], `.baseline-grid` (`1fr 1fr`) [476], `.status-grid` [528], all
collapsed to `1fr` in `@media (max-width:1024px)` [642-658]. **No Plotly subplot pattern exists** — zero
`xaxis2`/`yaxis2`/`grid` uses in the file [grep], and `soloRenderChart` [1717-1759] only merges `{height:450}` while
`soloChartUnavailable` resets `style.minHeight` on purge [1692-1715], so a 2-axis single div would fight the C-GEO
invariants. **Minimal shape:** wrap two sibling divs in a new `.chart-grid-2 { display:grid; grid-template-columns:1fr 1fr;
gap:12px }` (+ the 1024 px collapse), add `<div id="solo-pdf-chart">` left of `#solo-cdf-chart`, one extra
`soloRenderChart('solo-pdf-chart', …)` call in `soloRenderCdfChart` (it already has `model`), and add the new id to the
purge lists [SOURCE index.html:1858, 2078, 2084, 2224-2227].

---

## 2. Solo-applicable surfaces (Baseline View, Lineage, Maintenance line)

**Baseline View** `<a id="baseline-page-link" class="header-link" href="/dashboard/baseline.html">` [SOURCE index.html:671]
in `.header-links` [62-74], `.header-link` [68]; live class `header-link`, `display:block` [LIVE]. It is the only
Baseline entry point on the Dashboard page. `baseline.html` [72-79] and `history.html` [176] have their own nav but
**no mode source** (`history.html` fetches only `/api/history*` [561-765]; `baseline.html` fetches
`/api/dashboard/pods/<pod>/baseline` [1425]) → the link *in index.html* can be grayed; the round-trip from those pages
cannot (known limitation).

**Lineage tab** `<button class="tab" data-tab="tab-content-lineage" id="tab-lineage">` [SOURCE index.html:677] +
`<section id="tab-content-lineage">` [899-921]. Switching is generic (`setupTabs` binds `.tab` once, toggles `active` on
`data-tab` [1092-1111]); CSS `.tab-content{display:none}` / `.active{display:block}` [127-133]. Live tab set
`[tab-dashboard, tab-lineage, tab-system-health, tab-maintenance]` [LIVE]. For a solo pod `loadLineage` is never called
(the solo branch returns before the non-solo `Promise.all` [2464-2480]) so the tab keeps the placeholder
"Select a pod in the Dashboard tab first." [911-913] — empty by construction.

**Disabled-link shape:** none exists today [grep `disabled|aria-disabled` in index.html → form buttons only]. Existing
idioms: `.tooltip-container`/`.tooltip-dot`/`.tooltip-text` [550-595, used 797] and `.muted` [167]. Minimal: class
`is-disabled` (new 2 lines: `opacity:.45; pointer-events:none`) + `aria-disabled="true"` + `title`. **Never**
`hidden`/`display:none` — the Playwright test asserts visibility (§8).

**Gate point:** `isSoloSelection(selection)` is sync and available at the top of `loadSelectedPodDetails`
[1652-1666, 2371]; one `applySoloSurfaceMode(isSolo)` there toggles the class on `#baseline-page-link` and `#tab-lineage`,
and re-runs every refresh tick → self-healing, no API change.

**Maintenance line** `<p id="maintenance-status">` [SOURCE index.html:956] written by `updateMaintenanceTab`
[1165-1173] as `Backend Mode … | TMin Mode … | Queue …`; live: `Backend Mode: greptime_sql | TMin Mode: fixed | Queue: 10`
[LIVE]. It never mentions retention, although `/system` already returns
`maintenance_indicators{history_export_available, history_purge_available}` [LIVE]. Report §9 fix table: Issue 7 =
"leave as-is; clarify it targets the event-history store" → wording-only edit in `updateMaintenanceTab` (same response).

---

## 3. Axis titles + Section-9 formulas on the four solo charts

Layout objects are exactly the 3rd argument at each call site [SOURCE]: `{ yaxis:{range:[0,1]} }` for pod-level [2071];
`{ annotations }` for observed [2131]; `{ yaxis:{range:[0,1]} }` for per-tick [2154];
`{ xaxis:{type:'linear'}, annotations }` for CDF [2216]. **None has `xaxis.title`/`yaxis.title`** [LIVE layout dump];
`soloRenderChart`'s base layout adds only `{height:450}` + annotation defaults [1733-1741] → the four call sites are the
exact change points. **Follow the existing string-title convention:** `xaxis:{title:'Time'}`,
`yaxis:{title:'Probability', range:[0,1]}` [SOURCE index.html:1340-1344].

**Labels, verbatim from report §9:** residual x = "residual (metric units)", y = "F(r)"; per-tick y = "residual-tail p"
and "strike-tail p (tilde_p)"; pod-level y = "published probability P(anomaly)" (+ "raw Markov posterior P(anomaly)");
observed/reference y = "metric units"; time charts x = "Time".

**Prose subtitle anchors** (formula line goes beneath each): observed `#solo-metric-note` [843-845]; per-tick
`.chart-subtitle` [849-851] (no id); CDF `#solo-cdf-note` [855-857]; pod-level plain `<p class="muted">` [861-863] (no id).
Add one `<p class="formula">` per panel (new 3-line CSS, monospace) with §9 strings: `r = observed − model_forecast`,
`p = P(r_healthy ≥ |r|)`, `tilde_p = P(N ≥ n_k | N ~ Binomial(4, 0.05))`, `p_simes = min_k (K/k)·p_(k)`,
`p_published = isotonic(p_raw)`; and state the two norms on the per-tick panel (anomaly-norm ⇒ calm ≈ 0; surprise-norm ⇒
`p` uniform, `tilde_p` ≈ 1) — that is the §9 operator-confusion crux.

**Math rendering:** Plotly 2.27.0 comes from `https://cdn.plot.ly/plotly-2.27.0.min.js` [SOURCE index.html:660], the
bundle's only external asset, no local copy. **No MathJax/KaTeX** anywhere in the repo/bundle [grep; only pandas-internal
`use_mathjax` strings in `.venv_test`]. Internet is reachable today [LIVE, CDN 200] but not guaranteed → **plain
Unicode/HTML (`−`, `≥`, `<sub>`) is the safe default**; KaTeX would add an external dependency.

---

## 4. Probability and Decision Timeline (Issue 8)

**Call path:** `refreshDashboardView` [1066-1075] → `dashboardSelector.refreshPods()` → `onPodsLoaded` [2590-2595] →
`loadSelectedPodDetails(selection,{silent:true})` [2371] → solo branch `Promise.all([loadTimeseries(selection,myToken),
renderSoloDiagnostics(selection)])` [2471-2474] → `renderTimeseries(points, thresholds)` [2316] → `#timeseries-chart`;
counter [2317-2321]; empty state `renderTimeseriesMessage` [1189-1198].

**Markup:** `#timeseries-panel` [795], tooltip heading [796-800], `#chart-last-updated`/`#chart-refresh-cadence`/
`#chart-point-count` [802-807], `#timeseries-chart` [808], static HTML legend `#chart-legend` [809-816] (external-mode
wording: "Composite Anomaly Probability", "Warning/Critical Threshold").

**Route** `get_pod_timeseries` [SOURCE dashboard_routes.py:3095-3163] validates `window_hours` [3101], calls
`exporter.get_chart_history(pod, limit, namespace=…, cluster=…)` **only when both are not None** [3145-3152]; payload
`{pod_name, window_hours, thresholds:{probability:[min,max]}, points:[{t, prob, family, confidence, decision,
freshness, fallback_state,…}], presentation:{…}}` [LIVE]; cap `max_timeseries_points: 60`
[SOURCE config/detector-common.yaml:169]; currently 0 points for the solo pod (C1).

**`/solo` history row** — the whole per-tick record available client-side [LIVE, 288 rows]:
`{tick_epoch (float, 300 s), p_published, p_raw, candidate (bool), gate_pass (bool), drift_stale, details_status,
details}` — **no `decision`, no family/confidence**. Thresholds: `payload.tick.details.thresholds = {anomaly:0.8,
normal:0.2}` [LIVE] (same on both sampled ticks); decision is derivable exactly as `_decision_from_probability`
[dashboard_routes.py:549-561] and the client's `decisionMarkerColor` [1202-1214].
**No per-point freshness exists in `/solo` rows** — and `_data_freshness_payload` [dashboard_routes.py:2655-2694]
returns `{"state":"fresh","reason":"FLOW_ACTIVE"}` for **both** `fresh` and `degraded`
(`if freshness_state in {"fresh","degraded"}: …`), so the external renderer's tooltip `point.freshness` can only ever
say "fresh" (consequence verified independently; the same mapping is R-P1-freshness's finding, and their reading is that
the "degraded" wording at index.html:1255/1292 comes from `drift_status`, not the classifier). Hence a client-side solo
timeline should hover `p_raw`/`p_published`/`candidate`/`gate_pass`/`drift_stale` and may omit a freshness field entirely.

**Recommend CLIENT-SIDE, from the already-fetched `/solo` payload** (also the report's named Issue-8 fix: "drive the
panel from the 288-tick `/solo` history in solo mode; counter counts only renderable (valid-`t`) points"):
1. In the solo branch [2471-2474] drop `loadTimeseries`, keep `renderSoloDiagnostics` → removes the race where the
   0-point `/timeseries` response overwrites a good solo render (today both write the same two DOM nodes; slower wins).
2. Add `soloRenderTimeline(payload)` after `soloRenderPodLevelChart` [1843-1846], inside the existing `stillCurrent()`
   guard [1785-1789] → inherits the CARD-4C staleness protection.
3. Same trace shape as `renderTimeseries` (published line + 0.2/0.8 lines + one marker trace per decision class) with
   `x = tick_epoch*1000`, `y = p_published`, lines at `thresholds.normal`/`thresholds.anomaly`.
4. Set `#chart-point-count` from `history.filter(r => Number.isFinite(Number(r.tick_epoch)))` (288 today), set
   `#chart-last-updated` too (only `loadTimeseries` writes it today), and swap/hide the static legend text.
**Why not a server-side solo branch:** it would move the external route's data source (vision forbids contract/request
changes); the integration stub `get_chart_history(self, pod_name, limit=30)` [conftest.py:250] takes no namespace/cluster
kwargs, so any extra kwarg breaks the suite; and the 60-point cap + empty ring stay (C1).
**Do not add a retry/backoff:** the 0-point answer is the ring mid-cycle for that pod (three TTL purges, C1) and was
stable across 6 consecutive probes - a retry loop re-reads the same deque and hides nothing. In the solo branch the route
is not called at all, which is the whole point.

**Sizing evidence (R-P1-freshness §5.2: 10 pods x 22 probes @15 s, 05:22:35-05:27:50Z):** every pod shows exactly one
`60 -> 0 -> 60` cycle; zero windows are **30-150 s** long and **94/220 pod-samples (42.7 %)** are empty; one pod came back
at `n=1` (live append before the cold restore) - that is the "Points: 1, no curve" flavour. The cold restore IS WAL-backed
but runs only on re-entry [exporter.py:2544-2562, `state_store.read_scored_history` + `setdefault(deque)` with tick
dedupe], never on read: `get_chart_history` returns `[]` for an absent deque with no fallback [exporter.py:3848-3850].
Consequence for RV acceptance: with `ttl=900` the cycle persists at ~1/3 the frequency (empty fraction **≈14 %, not
zero**), so a config change reduces but never eliminates blanking. Under that ttl the **only remaining trigger is the
inventory purge** `self._point_history.pop(k, None)` [exporter.py:1303]: the store entry's `updated_at` is re-stamped on
every publish [exporter.py:2374] so the store-TTL purge [exporter.py:1259] cannot fire, and `_solo_cleanup_stale`'s age
test reads that same stamp [exporter.py:2878], while `discovered_at` is set only when a row is **created** and never
refreshed in place - the publish path takes the existing-row `update({...})` branch [exporter.py:2412-2430] and a gated
pod only updates `status`/`unavailable_reason` on its existing row [exporter.py:2736-2748; its docstring spells it out:
"the row's age is never refreshed with now", 2727-2728]; the creation-only stamps are
[exporter.py:2447] (first publish) and [exporter.py:2750] (gated bookkeeping row for a pod with no row yet).

**Accurate triage of the code-side fix (do not ship it as a standalone one-liner):** `ttl=900` alone leaves ~14 %; the
change that removes it *together with* `ttl=900` is to make the inventory purge [exporter.py:1297-1303] compare against
the newest of the row's `discovered_at` **and the store row's `updated_at`** - i.e. `self._store.get(k, {}).get("updated_at")`
- so a live pod never trips it while a dead pod (whose `_store` row is gone) still expires at `ttl`. With `ttl=300` the
same change barely helps, because the solo tick interval is itself ~300 s (live: 60 `_point_history` points spanning
`00:25Z -> 05:23Z`, ≈5.3 min apart; max observed age 303 s), so the purge fires just before each next tick either way.
**Trap (two ways to write a silent no-op):** an inventory row carries no `updated_at` (only `discovered_at`
[exporter.py:2447, 2750]), and `_store` is keyed by an **8-tuple** `(namespace, workload, "solo", pod, cluster, family,
match_mode, method)` [exporter.py:2360-2368], not by the inventory's `"ns/cl/pod"` string - so neither
`max(v.get("updated_at"), v.get("discovered_at"))` nor `self._store.get(k, {})` reads anything. Reuse the existing
resolver `_solo_entry_for(k)` [exporter.py:2911-2921], which rebuilds the 5-part match: `age_ref = max(discovered_at,
(_solo_entry_for(k) or {}).get("updated_at", 0.0))`. That is safe in the **shared** `_poll_once` purge with no mode
branch: external inventory rows are keyed by the bare `pod_full_name` with `discovered_at: now` [exporter.py:3051-3057],
so `_solo_entry_for(k)` returns `None` on **two** independent guards - the `<3 parts` split check and the `key[2]=="solo"`
filter [exporter.py:2914-2920], since external `_store` rows carry `phase`, not the literal `"solo"` [exporter.py:3361-3364]
- so `age_ref` falls back to `discovered_at` and external TTL semantics stay bit-identical. Refreshing `discovered_at` in the publish-path update [2412-2430] has the same effect but
overloads an audit field, and must never be done in the gated/restore path [2739-2750] - a gated pod does not publish, so
re-stamping there would keep its bookkeeping row alive forever, which is the ghost the comment at 2744-2746 warns about. Either way this is a P1/config-side change, not part of P2 - the `/solo` render below bypasses all of it.
Caveat, so this is not oversold: the lost-calibration clause in `_solo_cleanup_stale`
[exporter.py:2878-2893] bypasses age entirely for a pod that still owns canonical children, so no age-keyed change
covers a mapper-eligibility flip (P3 territory); our pod publishes raw (`p_published == p_raw` [LIVE]), i.e. the
fraction-only case the code explicitly excludes from that clause.

**Counter/validity code to change:** `renderTimeseries` filters `point && point.t` [1224-1226] but the counter uses raw
`points.length` [2317-2321], and `renderTimeseriesMessage` never resets it [1189-1198] → "Points: N + no data" (the solo
path above fixes it; the external path keeps its behaviour). **Adjacent:** `renderTimeseriesMessage` wipes `innerHTML`
without `Plotly.purge`; live check showed the div still owning a Plotly `data` array while displaying "No timeseries data
available" [LIVE].
---

## 5. Guide tab (solo-only) + static-asset serving

**Tab structure:** `<div class="tabs">` with four `<button class="tab" data-tab="tab-content-X">` [SOURCE index.html:675-680]
followed by sibling `<section id="tab-content-X" class="tab-content">` inside `<main class="page">`: dashboard [682-897],
lineage [899-921], system-health [923-951], maintenance [953-977]. CSS `.tabs` [98], `.tab` [105], `.tab-content`/`.active`
[127-133]. `setupTabs()` is generic over `querySelectorAll('.tab')` + `data-tab` [1092-1111] → **a new tab needs zero JS**.
No vertical-menu layout exists: the only multi-column idioms are `.panel-grid` [402], `.baseline-grid` [476],
`.status-grid` [528], collapsed to `1fr` at `@media (max-width:1024px)` [642-658]. → one new rule
`.guide-layout{display:grid;grid-template-columns:200px 1fr;gap:16px}` (+ that media query), a
`<nav class="guide-menu">` of `<button data-guide="…">`, one `.guide-page` div per panel toggled `.active` (copy the
`setupTabs` pattern, ~15 lines). Do not reuse `.tab` (pill styling) for the vertical menu.

**Serving:** `create_static_dashboard_blueprint(bundle_path)` [SOURCE analyser/detector_dashboard.py:33-47] mounts the
**whole directory** — one rule `/<path:filename>` → `send_from_directory`, plus `/` and `/dashboard/` → index.html.
**No allow-list.** `validate_bundle_path` [16-31] raises `ConfigurationError` unless the 4 files
`{index.html, history.html, baseline.html, shared_selectors.js}` exist → **adding** an asset is free;
removing/renaming one bricks startup. Image: `WORKDIR /app/analyser` [analyser/Dockerfile:72] + `COPY analyser .` [:75]
→ any new file under `analyser/dashboard_assets/` ships with no Dockerfile change.

**Recommend: inline in index.html** as `<section id="tab-content-guide">` with one `.guide-page` per panel + a "Scoring
chain" overview (§9 content). The tab machinery is already inline and generic; a separate file needs a `fetch()` plus a
not-found/offline state the codebase has no pattern for; content is static so it cannot touch the refresh loop (§7).

**Sibling-repo precedent (structure only, do not copy text):** `pipelineml-tester/src/pipelineml_tester/tier_c/templates/about.html`
— `{% extends "base.html" %}`, one `<div class="card alert">` per h2 section, `class="muted"`/`<code>` fragments, `<table>`s;
nav in `tier_c/templates/base.html:24-27` as `<a data-nav-key="about" href="/tier-c/about">` with `aria-current="page"`.
It is server-rendered Jinja with its own route (not reusable), but its IA (one short page per concept, tables, explicit
"what this does NOT show") is the right model.

---

## 6. Raw-vs-Published panel names

`soloRenderPodLevelChart` [SOURCE index.html:2013-2072]: published curve uses a 3-way name ternary [2029-2032]
(`'Published p (raw — calibrating)'` when 0 calibrated ticks, `'Published p (calibrated)'` when all — today's live name,
`'Published p (raw + calibrated ticks)'` when mixed), per-tick marker colors from `row.details.probability_label` [2026-2027];
raw curve `name:'Raw Markov posterior p (calibrating)'` [2045]; gate markers `name:'Simes gate rejected null (anomalous)'`
[2066]. Live trace names [LIVE]: `["Published p (calibrated)", "Raw Markov posterior p (calibrating)", "Simes gate rejected
null (anomalous)"]`. Relabel sites = those strings + the prose paragraph [862]. Note `CHART_LEGEND_LABELS.probabilitySeries`
= "Composite Anomaly Probability" [1007-1011] belongs to the *timeseries* legend — a different string.

---

## 7. Refresh invariants a Guide tab / timeline swap must not break

- `refreshDashboardView` [1066-1075] = `updateSystemHealth()` + `dashboardSelector.refreshPods()`; it never re-renders the
  page body, never touches tab sections, never re-runs `setupTabs` → a static Guide tab is immune; bind its handlers once
  at `DOMContentLoaded` [2566-2600].
- `refreshPods` (shared_selectors.js, bf93e06) re-renders the pod list **in place**, preserving selection and scroll; never
  recreate the list/detail containers from elsewhere.
- `onPodsLoaded` [2590-2595] → `loadSelectedPodDetails(selection,{silent:true})`: silent mode must not clear the solo
  surface (`clearSoloSurface` is for selection change / Baseline click) and must bump the request nonce [2371-2422]. New
  renders must live inside `renderSoloDiagnostics`' `stillCurrent()` guard [1785-1789] so a slow pod-A response cannot paint
  pod B (the CARD-4C class).
- Charts update via `Plotly.react` on an existing div [1755] (no innerHTML rebuild) → zoom/scroll survive. **No
  `Plotly.Plots.resize` call exists** [grep: 0] → a chart rendered while its tab is `display:none` lays out at zero width
  and self-heals only on the next 5 s react; call `Plotly.Plots.resize(div)` on tab activation (also the correct fix for
  any new hidden-then-shown chart).

---

## 8. Tests / verification surface

**No JS test harness** (no node/eslint/jest config); JS is exercised only through Playwright, and `node --check` on an
extracted `<script>` (scratch, /tmp) covers syntax. `index.html` is **2603 lines / 115297 B, all app JS inline** in one
`<script>` starting at line 980 and running to ~2601, after the two `<script src>` tags (Plotly CDN + shared_selectors.js)
at 660-661. New UI code belongs at the end of that inline script, beside the solo renderers (2074-2275).

1. `tests/unit/test_static_bundle_contract.py` — the 4 bundle files must exist (**never remove/rename** one); asserts
   `baseline.html` contains ids (`residual-series-chart`, `training-overlay-chart`, `cdn.plot.ly/plotly-2.27.0.min.js`, …)
   and that `/dashboard/` redirects and serves `shared_selectors.js`. Nothing about index.html content.
2. `tests/integration/test_dashboard_overview.py` (Playwright, real Chromium, serving the **repo** `dashboard_assets`
   [conftest.py:263-276]): `#baseline-page-link` **to_be_visible**; `#timeseries-chart`, `#chart-legend` visible;
   `#chart-point-count` **not** "0"; `#chart-refresh-cadence` contains "config"; clicks `#tab-maintenance`; asserts
   `#export-button`/`#purge-button` texts and `#open-history-page-link`. → graying the Baseline link must keep it rendered
   (`opacity`/`pointer-events`); do not remove/rename the legend block or Maintenance card.
3. `tests/integration/test_canonical_route_contracts.py:39` pins `max_timeseries_points == 60` + the `/timeseries` contract.
4. `tests/unit/test_solo_dashboard_routes.py` FAKE exporter takes `(pod_name, limit, namespace, cluster)`; the integration
   stub [conftest.py:250] takes `(pod_name, limit=30)` → new server-side kwargs break the stub, not the fake.

**Nothing pins** the tab list/count, `#maintenance-status` text, counter semantics, the four solo chart ids, or CDF
internals → Guide tab, relabeling, axis titles/formulas, marker fix and PDF panel need **no test edits**; changing
`#chart-point-count` for solo is safe (the integration stub pod is non-solo).

**Run** (verified here: pytest 9.0.1, playwright 1.9.0, `analyser/.venv_test`):
```
cd /Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector/analyser
.venv_test/bin/python -m pytest tests/unit -v
.venv_test/bin/python -m pytest tests/integration/test_dashboard_overview.py -v   # needs Chromium
```

---

## 9. Local run for E/RV (validated)

Post-deploy, RV's cheapest check is the pod itself: `http://127.0.0.1:8080/dashboard/` serves exactly the repo bytes (C5).
Pre-deploy, the validated recipe is a ~30-line scratch server under `/tmp` serving `analyser/dashboard_assets` as document
root and reverse-proxying `/api/*` → the live solo API:
```
python3 /tmp/solo-dash-dev/static_proxy.py \
  --repo /Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector/analyser --port 8090
# → http://127.0.0.1:8090/dashboard/
```
Exercised here [LIVE]: index 200 (115297 B), `/api/dashboard/system` 200 via the proxy, family+pod rows render, all four
solo charts render, Plotly loads from the CDN. Keep it under `/tmp` (not the repo); it answers `HEAD`, maps `/<file>` and
`/dashboard/<file>` to the bundle, and 404s unknown paths. Plain `python3 -m http.server` is **not** enough (no `/api`
proxy). Browser driving: the OMP `browser` helper runs real Chromium against that URL (`browser.tab('dashdev')`) and
produced every [LIVE] DOM fact here — e.g. `document.getElementById('solo-cdf-chart').layout` to assert the marker `y`
equals the annotation cdf, or `#chart-point-count` text after a solo selection. Nothing else needed: Playwright 1.9.0 with
chromium-1208/-1223, headless shell, firefox, webkit is installed in `analyser/.venv_test`.

---

## Noticed, not in scope (recorded, not proposed)

1. `renderTimeseriesMessage` [1189-1198] wipes `innerHTML` without `Plotly.purge`; live-confirmed stale Plotly `data` +
   geometry survive behind the empty message — the pattern `soloPurgeChart` [1670-1690] exists to prevent.
2. `#solo-identity-line` renders `ml-components///pipelineml-tester-…` (empty cluster → triple slash) [LIVE]; cosmetic.
3. No `Plotly.Plots.resize` call → charts in a hidden tab lay out at zero width until the next react.
4. `updateMaintenanceTab` [1165-1173] ignores `maintenance_indicators.history_purge_available` returned by `/system`.
5. `/solo` is 7.37 MB per 5 s tick (≈1.5 MB/s sustained), refetched whole though one metric is drawn.
6. `#chart-legend` static labels [809-816] duplicate the Plotly legend and use external-mode wording.
7. `history.html`/`baseline.html` have no mode source → the Baseline surface stays reachable by direct URL from them.
8. `analyser/.venv_test` lives inside the source tree (pollutes repo-wide greps).
