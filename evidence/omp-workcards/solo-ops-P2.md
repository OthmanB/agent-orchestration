# Workcard: SOLO-OPS-P2 — solo dashboard UI batch (6 items, one file)

- Parent: [vision §3-P2/§5/§6](../solo-mode-plans/solo-dashboard-operations-vision-2026-11-06.md) (2026-11-06), [supervisor prompt](../solo-mode-plans/solo-dashboard-operations-supervisor-prompt-2026-11-06.md), report `pipelineml-anomaly-detector/markdown/2026-11-06-solo-dashboard-operations-report.md` (Issues 3–10; **§9 lines 562-601 = canonical text** for formulas/Guide), [R-P2](../E-solo-dashboard-ops/R-P2.md)
- Date: 2026-11-06 · Status: draft (P output; Supervisor accepts)
- Repo `/Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector`, branch `feature/cnn2dlstm-bayesian-statistical-detector-v2`. `index.html` re-checked: 2603 lines / 115297 B, unchanged since R-P2 — R's line numbers below are current unless marked **(fixed)**.

## Where P differs from R-P2 / the report (all source-verified)

1. **Solo branch shape (fixed):** it is two independent calls, `loadTimeseries(...)` at `index.html:2452-2454` and `renderSoloDiagnostics(...)` at `:2458-2460` — not `Promise.all` at 2471-2474.
2. **Decision rule (fixed):** `_decision_from_probability` is `dashboard_routes.py:456-483` (R cited 549-561 = `_resolve_operator_thresholds`). It is `p ≥ anomaly → anomaly`, `p ≤ normal → normal`, else `undecided`; thresholds missing → `unknown`. Report §9 writes `> 0.8`; **use the code (`≥`).**
3. **Disabled style:** R suggested `pointer-events:none` + `title`. That suppresses the `title` tooltip. Use `cursor:not-allowed; opacity:.45` + `aria-disabled` + JS click guards.
4. **Pre-selection gate needs no `shared_selectors.js` change:** `onPodsLoaded(selectorState.pods)` already passes the rows (`shared_selectors.js:896`; index.html's callback ignores them at `:2591`), it first fires from the initial `refreshPods()` inside `init` (`:937`) before any pod is selected, and `window.dashboardSelector.getPods()` exists (`:946`). Live check: all 10 `/api/dashboard/pods` rows carry `active_model_family: "solo_statistical"`.
5. **`soloRenderChart` merges layout shallowly** (`Object.assign(baseLayout, layout)`, `:1756`) and purges before each react (`:1748`). Any `xaxis` you pass **replaces** `{type:'date'}`: time charts MUST pass `xaxis:{type:'date', title:'Time'}` or Plotly shows raw epoch-ms. Also set `automargin:true` on titled axes (base `margin.l` is a fixed 56).
6. **Timeline design:** R proposed a new trace builder. P chooses less code: map `/solo` history to the point shape the existing `renderTimeseries` already consumes and reuse it (hover shows `Confidence n/a / Freshness unavailable / Fallback unknown` — truthful: `/solo` rows carry none of them).
7. R-P2 §9's `static_proxy.py --repo …` flag does not exist; the verified call is `python3 /tmp/solo-dash-dev/static_proxy.py --port 8090` (assets default to the repo bundle, `/api/*` GET-proxied to `127.0.0.1:8080`).
8. R-P2 §8 omits `tests/integration/test_dashboard_system_health.py` — it clicks `#tab-lineage` on a non-solo stub and expects `#lineage-table` visible, so the Lineage tab must stay enabled for non-solo rows.

## Objective / non-goals

Objective: the six display fixes of vision §3-P2 (CDF marker + PDF; grayed dead surfaces; axis titles + formulas; solo timeline + honest counter; Guide tab; Raw-vs-Published labels).
Non-goals: any API/route/request-set/fetch change; external-pod `/timeseries` contract; scoring, thresholds, `analyser/solo_mode/**`; any new gate/counter/auth/logging; MathJax/KaTeX/new dependency; the Plotly CDN; new test files.

## Scope and budget

**One file:** `analyser/dashboard_assets/index.html`. Estimate +350–450 lines (+15–20 KB) over ~25 edit sites (CSS ~50, Guide markup ~110, JS ~200). **`shared_selectors.js`: not touched** (finding 4).
**E must NOT touch:** `analyser/solo_mode/**`, `dashboard_routes.py`, `exporter.py`, `config_loader.py`, any YAML/ConfigMap/`deploy/**`, `shared_selectors.js`, `baseline.html`, `history.html`, `analyser/tests/**` (no test pins the changed surfaces), `markdown/**` (the report/vision are the record), tester source, the protected `ml-components` pair, Dockerfile. Do not rename/remove `#baseline-page-link`, `#timeseries-chart`, `#chart-legend`, `#chart-point-count`, `#maintenance-form`, `#export-button`, `#purge-button`, `#open-history-page-link`, the four solo chart ids, or the four bundle files (`test_static_bundle_contract.py`, `test_dashboard_overview.py`). E does not commit, build, or deploy.

## Items (symbols/anchors; code is E's)

**1. CDF marker + PDF** — `soloRenderCdfChart` (`:2157-2217`; hard-coded `y:[1.0]` at `:2190`). Markup `:854-858`.
- Helper `soloCdfAt(points, x)`: exact element of `residual_cdf.points` (the live latest residual is an exact element) → its `y`; else linear interpolation between bracketing neighbours (points are ascending by value); else `null`. `null`/non-finite/`n<2` → no marker, annotation says `F(r) n/a`. Same value drives marker `y` and annotation text (`… · F(r) = 0.0956`).
- PDF: new `<div id="solo-pdf-chart">` LEFT of `#solo-cdf-chart`, both inside a new `<div class="chart-grid-2">` in the same card; CSS `.chart-grid-2{display:grid;grid-template-columns:1fr 1fr;gap:12px}`, `.chart-grid-2>div{min-width:0}`, plus `grid-template-columns:1fr` in the existing `@media (max-width:1024px)` block (`:642-658`). Render via `soloRenderChart('solo-pdf-chart', …)`: `type:'histogram'`, `x` = finite `residual_cdf.residuals[i][1]`, `histnorm:'probability density'`, Plotly auto-binning (no hard-coded bin count), latest residual as a red vertical `shapes` line. h3 → "Residual PDF (left) and CDF (right) — current model".
- Wherever the CDF div is made unavailable the PDF div must be too: the two early returns in `soloRenderCdfChart` (`:2159-2171`), the lists in `soloRenderMetricCharts` (`:2078`, `:2084`). Add `'solo-pdf-chart'` to the purge lists in `soloShowUnavailable` (`:1858`) and `clearSoloSurface` (`:2224-2227`).

**2. Grayed surfaces + Maintenance line**
- New CSS `.is-disabled{opacity:.45;cursor:not-allowed}`. Targets: `#baseline-page-link` (`:671`), `#tab-lineage` (`:677`). Never `hidden`/`display:none` (Playwright asserts the link visible). Keep System/Health and Maintenance enabled.
- `applySoloSurfaceMode(isSolo)`: toggle the class, `aria-disabled="true"` (remove when false) and `title` ("Not applicable in solo mode — no baseline artifacts" / "… no model lineage"; remove title when false). Click guards bound once at `DOMContentLoaded`: the link `preventDefault()`s when `aria-disabled`; the `setupTabs` click handler (`:1094`) returns early for `aria-disabled="true"` tabs.
- **Gate (resolved by P):** `refreshSoloSurfaceMode()` = `currentSelection ? isSoloSelection(currentSelection) : (pods.length > 0 && pods.every(row => isSoloSelection({row})))`, `pods = window.dashboardSelector.getPods()`. Solo marker = `active_model_family === 'solo_statistical'` (`isSoloSelection`, `:1652-1668`, also accepts `model_availability === 'solo_statistical_available'` and `runtime_reason === 'SOLO_WARMING'`). Call it: first line of the `onPodsLoaded` callback (`:2591` — disabled on first paint, before any selection), after `currentSelection = selection` (`:2382`), after `currentSelection = null` in the no-selection branch (`:2373`) and in `onSelectionCleared` (`:2580`). Re-evaluated every refresh → self-healing. Empty list or any non-solo row → enabled (never disable a surface that may work).
- Maintenance: `updateMaintenanceTab` (`:1168`) appends ` | Export/delete act on this process's event-history store (not model or scoring state)`; keep the failure string.

**3. Axis titles + formulas** (call sites `:2071`, `:2131`, `:2154`, `:2216`; string-title convention `:1338-1340`)

| Chart | xaxis | yaxis |
| --- | --- | --- |
| Observed `solo-metric-chart` | `{type:'date', title:'Time'}` | `{title:`${metricName} (metric units)`}` |
| Per-tick `solo-pt-chart` | `{type:'date', title:'Time'}` | `{range:[0,1], title:'p-value [0,1] (surprise-norm: small = surprising)'}` |
| CDF `solo-cdf-chart` | `{type:'linear', title:'residual (observed − expected), metric units'}` | `{range:[0,1], title:'F(r)'}` |
| PDF `solo-pdf-chart` | same as CDF | `{title:'density'}` |
| Pod-level `solo-prob-chart` | `{type:'date', title:'Time'}` | `{range:[0,1], title:'P(anomaly) [0,1] (anomaly-norm: small = normal)'}` |

One `<p class="formula">` per panel under its existing prose (keep the prose; new CSS: monospace, small, muted). Plain Unicode/`<sub>`, no math library. Anchors: observed `#solo-metric-note` (`:844`); per-tick `.chart-subtitle` (`:850`); CDF/PDF `#solo-cdf-note` (`:856`); pod-level `<p class="muted">` (`:862`). Text (report §9):
- Observed: `r = observed − model_forecast` (residual; 0 = as expected).
- Per-tick: `p = P(r_healthy ≥ |r|)` · `n_k = #{ last W ticks : p < α }` · `tilde_p = P(N ≥ n_k | N ~ Binomial(W, α))` = 1 if `n_k = 0` (W = 4, α = 0.05 here). **Two norms, stated here:** surprise-norm (p-value): small = surprising; calm ⇒ `p` ~ Uniform(0,1) (hops between 0 and 1) and `tilde_p` ≈ 1; not the anomaly-norm of the pod-level probability (calm ⇒ ≈ 0).
- CDF/PDF: `F(r)` = empirical mid-rank CDF of the model's N persisted residuals, strictly inside (0, 1) (`solo_mode/noise.py:692-717`, `diagnostics.py:527-538`; do not write a closed form — tie handling differs from a naive count formula); PDF = density of the same N residuals; marker at `y = F(latest residual)`. `r = observed − expected`.
- Pod-level: `p_simes = min_k (K/k)·p_(k)` over the metrics' `tilde_p` → evidence → two-state Markov posterior (prior π = 0.01, mean sojourn 6 ticks) = `p_raw`; `p_published = isotonic(p_raw)`. Anomaly-norm: `P(anomaly)`, calm ⇒ ≈ 0.
No formula line on the timeline panel (shared with external pods); the Guide explains it. No tunable value in code: thresholds only from the payload.

**4. Solo timeline + honest counter** (`#timeseries-panel` `:795-818`)
- `renderTimeseries` (`:1216`) **returns the number of points plotted** (`sorted.length`; 0 on the empty/Plotly-unavailable paths). `loadTimeseries` (`:2315-2320`) and the solo path set `#chart-point-count` from that return (also in `loadTimeseries`' catch at `:2307`) — counter and "No timeseries data available" can never disagree. `renderTimeseriesMessage` (`:1189`) also `Plotly.purge`s the div before wiping `innerHTML` (otherwise the next react skips re-materialising the SVG — the C-GEO failure at `:1697-1706`; needed for empty→populated).
- New `soloRenderTimeline(payload)`, called in `renderSoloDiagnostics`' `.then` right after `soloRenderPodLevelChart(payload)` (`:1844`), i.e. inside the existing `stillCurrent()` guard (`:1786-1788`). Rows = `payload.history` with finite `tick_epoch`; point = `{t: new Date(tick_epoch*1000).toISOString(), prob: p_published, decision}`; `decision` derived exactly as finding 2 from `payload.tick.details.thresholds` (`{normal, anomaly}`; live 0.2/0.8, `driver.py:1764-1766`), thresholds passed as `{normal_threshold, anomaly_threshold}`; null `p_published` → `undecided`. Call `renderTimeseries(points, thresholds)`; set `#chart-point-count` from its return and `#chart-last-updated` to `new Date().toLocaleTimeString()`. No new fetch.
- Solo branch of `loadSelectedPodDetails` (`:2452-2454`): **delete the `loadTimeseries(...)` call** (it races the solo render and its 0-point `/timeseries` response overwrites a good chart). Then the solo-qualification block in `loadTimeseries` (`:2292-2295`) is unreachable → delete it (clean cutover); the external path is otherwise unchanged. Add `'timeseries-chart'` to the purge lists of `clearSoloSurface` and `soloShowUnavailable` and set `#chart-point-count` to `0` there (otherwise a previous solo pod's timeline survives a 404/new selection — the CARD-4C stale-paint class). `#chart-legend` stays as is (visible; test asserts it).

**5. Guide tab** — static, inline, no fetch, always visible (no extra gate)
- `<button class="tab" data-tab="tab-content-guide" id="tab-guide">Guide</button>` appended after Maintenance (`:679`); `<section id="tab-content-guide" class="tab-content">` after `:977`. `setupTabs` is generic → no JS for the tab itself.
- Inside: `.guide-layout{display:grid;grid-template-columns:200px 1fr;gap:16px}` (+ 1fr in the 1024 px media block), `<nav class="guide-menu">` of `<button type="button" data-guide="…">` (new CSS; do NOT reuse `.tab` pill styling), one `<div class="guide-page" id="guide-…">` per page, `.guide-page{display:none}` / `.active{display:block}`. `setupGuideMenu()` (~15 lines, copy of the `setupTabs` pattern) bound once beside `setupTabs()` in `DOMContentLoaded` (`:2570`); the refresh loop never touches it.
- Pages (first = default active) and each page's four parts — what it shows / formula / norm / "calm looks like". Text only from report §9 (table `:571-580`, norms `:582-591`, per-panel `:593-601`); invent no numbers; no hard-coded config values beyond those in §9.

| Page (`data-guide`) | "A calm value looks like" |
| --- | --- |
| The scoring chain (`chain`: the 8-row §9 table + two-norms paragraph) | `p_published ≈ 0` **and** `tilde_p ≈ 1` at the same moment — different instruments, not two dials of one gauge |
| Observed vs Reference (`observed`) | observed wanders around the reference; no lasting gap |
| Per-Tick p and tilde_p (`pertick`) | `p` hops anywhere in 0–1 tick to tick (uniform when healthy — not a defect); `tilde_p` sits at 1.0 with rare short dips |
| Residual PDF and CDF (`resid`) | red marker inside the bulk of the PDF; `F(r)` near the middle, not near 0 or 1 |
| Pod-Level Probability (`podlevel`) | `p_raw` small (at/below the prior); `p_published` under the normal threshold; no red ✕ gate markers |
| Probability and Decision Timeline (`timeline`) | `p_published` line under the dashed normal-threshold line; markers all "normal" |

**6. Raw-vs-Published labels** — `soloRenderPodLevelChart` (`:2013-2072`) + prose `:862`. Keep the 3-way, data-driven ternary on `probability_label` counts (`:2028-2031`), new wording: `'Published p — raw (no calibrated mapper)'` / `'Published p — calibrated: mapper(p_raw)'` / `'Published p — raw + calibrated ticks'`; raw curve (`:2045`) → `'Raw Markov posterior p_raw'` (drop "(calibrating)": a later package makes raw also mean "no healthy mapper"). Update the prose to the same terms; keep the marker-colour and ✕-gate explanation.

## Preserved invariants (2026-10-17 refresh fix + CARD-4C/6G; vision §5)

- `shared_selectors.js` untouched: pod-list in-place refresh, selection and scroll survive; manual refresh/search/filters unchanged.
- `sameIdentitySilent` logic (`:2413-2418`): silent same-identity tick does NOT call `clearSoloSurface`, still bumps `soloRequestNonce` before the live await; detail token/`owned()` guards unchanged. New solo renders only inside `stillCurrent()`.
- Chart lifecycle: keep `soloRenderChart`/`soloChartUnavailable`/`soloPurgeChart` as they are (PDF goes through them); timeline uses existing `renderTimeseries` → `Plotly.react` on `#timeseries-chart`. New chart ids in every purge list.
- Refresh loop (`refreshDashboardView`, 5 s) never re-renders page body, tabs or Guide; Guide handlers bound once.
- No API/route/request-set/fetch change; external `/timeseries` contract and external-pod rendering unchanged. YAML-first: no threshold, bin count or tunable literal in JS (display strings only).

## E acceptance (no cluster access; live API is the user's 127.0.0.1:8080 forward, read-only)

From `analyser/`; helper `/tmp/solo-ops-p2/check_syntax.sh` (P-verified: extracts the single inline `<script>` and runs `node --check` on it and `shared_selectors.js`).
1. `/tmp/solo-ops-p2/check_syntax.sh` → `SYNTAX_OK`.
2. `.venv_test/bin/python -m pytest tests/unit -v` → no new failure (nothing here reads `index.html`; any failure must be shown unrelated; do not "fix" product code).
3. `.venv_test/bin/python -m pytest tests/integration/test_dashboard_overview.py tests/integration/test_dashboard_system_health.py -v` (Chromium) → pass.
4. Smoke: start `python3 /tmp/solo-dash-dev/static_proxy.py --port 8090` as a named background service (kill after); E writes `/tmp/solo-ops-p2/smoke.py` (headless Playwright from `.venv_test/bin/python`, http://127.0.0.1:8090/dashboard/) asserting:
   - BEFORE selecting any pod: `#baseline-page-link` and `#tab-lineage` have `aria-disabled="true"`, are still visible, clicking Lineage does not activate `#tab-content-lineage`.
   - Select a solo pod, then a non-default metric. `solo-cdf-chart` trace "Latest recorded residual": `y[0]` equals `soloCdfAt` of the payload's points at `latest_recorded_residual.residual` (|Δ| < 1e-9; live ≈ 0.0956) and is `< 1.0`; annotation shows the same value.
   - The five solo charts (`solo-metric-chart`, `solo-pt-chart`, `solo-cdf-chart`, `solo-pdf-chart`, `solo-prob-chart`) have non-empty `_fullLayout.xaxis.title.text` and `yaxis.title.text`; 4 non-empty `.formula` in `#solo-panel`; time charts still show date ticks (x type `date`).
   - `#solo-pdf-chart` has a histogram trace and its bounding box is left of `#solo-cdf-chart`.
   - Raw-vs-Published trace names contain "Raw Markov posterior" and "Published p".
   - Guide: click `#tab-guide`; 6 menu buttons; the first page ("The scoring chain") active; clicking each menu button leaves exactly one `.guide-page.active`, and it changes.
   - Timeline: `#timeseries-chart` has the probability trace + threshold lines; `#chart-point-count` equals the number of finite-`tick_epoch` `/solo` history rows (288 live) equals the probability trace length; "No timeseries data available" absent.
   - Maintenance status text contains "event-history".
   - ≥ 3 automatic refresh ticks (≥ 16 s, no manual refresh/reload): selected pod and metric unchanged, `#pod-list.scrollTop` and `window.scrollY` unchanged, `#solo-panel` never gains `hidden`.
5. `git diff --stat` shows only `analyser/dashboard_assets/index.html`.
6. Write `agent-orchestration/evidence/E-solo-dashboard-ops/E-P2.md`: commands, exit codes, smoke output, and limits (local smoke is not deployed-image proof; chart label overlap is eyeballed by RV/S in a real browser).

## RV checklist

- [ ] Diff = `index.html` only; none of the "must not touch" files; element ids in the keep-list intact
- [ ] Marker `y = F(latest)` and annotation share one value; no `y:[1.0]` left
- [ ] Baseline link/Lineage tab are grayed + `aria-disabled` + tooltip, visible, click-guarded; gate works before selection; non-solo rows keep both enabled
- [ ] Every time chart passes `type:'date'`; every titled axis `automargin`; five charts titled; four formula lines match report §9 (decision uses `≥`)
- [ ] Solo timeline built from `/solo` inside `stillCurrent()`; `loadTimeseries` gone from the solo branch and its dead solo-URL block removed; `#timeseries-chart` in both purge lists; counter from the render return (both paths)
- [ ] Guide handlers bound once, no fetch; 6 pages; text traceable to §9
- [ ] Raw-vs-Published names data-driven from `probability_label`
- [ ] No thresholds/bin counts/tunables hard-coded; no new dependency; refresh invariants above intact

## Gate / dependents

E report: `/Users/obenomar/Work/langGraph/appthrust/agent-orchestration/evidence/E-solo-dashboard-ops/E-P2.md`. Gate: `/Users/obenomar/Work/langGraph/appthrust/agent-orchestration/evidence/solo-mode-gates/SOLO-OPS-P2.md` (≤ 200 lines; record commit, workflow run, image digest, protected-pair before/after, real-browser acceptance numbers).
Unlocks: supervisor commit → `docker-build.yml` (`no_cache=false`) → digest pin → solo-only `set image` (+ P1 ConfigMap in the same rollout) → S's real-browser acceptance on `127.0.0.1:8080/dashboard/` (vision §3-P2 list). P3 starts only after that proof.

## Known limitations (accepted, do not fix here)

Baseline round-trip from `baseline.html`/`history.html` stays reachable by URL (no mode source there); timeline hover shows n/a fields; `/solo` (7.4 MB) is refetched every 5 s (unchanged); `#solo-identity-line` triple slash; no `Plotly.Plots.resize` on tab activation (a chart refreshed while the Dashboard tab is hidden heals on the next 5 s tick, as with the existing tabs).

## Open points P resolved

- **Pre-selection gate** = "non-empty pod list, every row solo" else the selection: derivable from rows already delivered to `onPodsLoaded`, no API change; `every` (not `some`) so a surface that could work is never disabled. [INFERENCE] a solo deployment configures no model families (`config_loader.py:733-751`), so all its rows are solo; live: 10/10 rows `solo_statistical`.
- **Disabled mechanism**: `aria-disabled` + guards, not `pointer-events:none` (tooltip must work).
- **Timeline reuse** of `renderTimeseries` + counter from its return, which also fixes the external path's "Points: N + no data" (vision: counter never raw length).
- **`renderTimeseriesMessage` purge** added because the solo timeline switches empty ↔ populated.
- **Guide always visible** (static, wording scoped to solo panels) — avoids a third gate.
- **Formula `≥`** from code, not report `>`.
- **No docs/tests edited:** repo has no changelog; the only candidate doc is `markdown/2026-10-09-solo-mode-export-dashboard.md` — left out by the one-file scope; Supervisor may add a short addendum card.
