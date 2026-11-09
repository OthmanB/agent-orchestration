# RV Review — SOLO-OPS-P2

- Date: 2026-11-06
- Reviewer: RV-P2
- Disposition: **rejected** (advisory; Supervisor decides)
- Reviewed product file: `pipelineml-anomaly-detector/analyser/dashboard_assets/index.html`; line references below refer to the reviewed working-tree version.
- No product/repository files modified by RV. Only this requested evidence, screenshots, and `/tmp/solo-ops-p2-rv/` review helpers were written. No cluster/SSH/kubectl operations, mutations to the API, commits, or changes to the user's port-forward.

## Checks performed

### 1. Inputs, diff scope, and keep-list — PASS

Read the reviewer template, the complete P2 workcard including its must-not-touch list and RV checklist, vision §3-P2, R-P2, E-P2, and report §9 (lines 562–601). Reviewed the full `git diff -- analyser/dashboard_assets/index.html` and the surrounding implementations, not only the added hunks.

`git status --short` and `git diff --numstat` showed the P2 edit only in `analyser/dashboard_assets/index.html` (observed +576/−45). The other tracked modifications were the declared pre-existing `AGENTS.md` and separately reviewed P1 `deploy/k8s/solo-card6/configmap.yaml`; the declared untracked orchestration/report items were also present. No other P2 must-not-touch file appeared in the diff. In particular, `shared_selectors.js`, backend/scoring files, tests, other bundle pages, Dockerfile, and the protected pair were not changed by this UI diff.

Counted literal HTML IDs independently: exactly one each of `baseline-page-link`, `timeseries-chart`, `chart-legend`, `chart-point-count`, `maintenance-form`, `export-button`, `purge-button`, `open-history-page-link`, `solo-metric-chart`, `solo-pt-chart`, `solo-cdf-chart`, `solo-prob-chart`, and new `solo-pdf-chart`. The static bundle contract tests also passed.

### 2. Syntax and specified regression tests — PASS

All commands ran from `pipelineml-anomaly-detector/analyser/`:

| Command | Result |
|---|---|
| `/tmp/solo-ops-p2/check_syntax.sh` | Exit 0; `SYNTAX_OK` |
| `.venv_test/bin/python -m pytest tests/integration/test_dashboard_overview.py tests/integration/test_dashboard_system_health.py tests/unit/test_static_bundle_contract.py -q` | Exit 0; **10 passed in 6.88 s** (3 integration + 7 static bundle tests) |
| `.venv_test/bin/python /tmp/solo-ops-p2-rv/smoke.py` | Exit 0; **44/44 checks passed**, 24.29 s |

Copied E's smoke to `/tmp/solo-ops-p2-rv/smoke.py`, changing its `BASE` constant from port 8090 to **8092**; did not edit E's script. Started my own named background service with `python3 /tmp/solo-dash-dev/static_proxy.py --port 8092`. It served working-tree assets and GET-proxied `/api/*` to the user's existing forward. **Stopped only my own 8092 proxy after the review.**

Independent smoke reproduced marker `F(r) = 0.8464912280701754` on the non-default memory metric, the matching `0.8465` annotation, five titled solo charts, PDF histogram/red line, six Guide pages, timeline 288-point count, and event-history wording. Three automatic pod-list refreshes occurred over 17.0 s without selection/metric changes or a hidden solo panel. This smoke does **not** check decision contents, null data, invalid timestamps, or empty→populated recovery; those omissions explain the findings below despite 44/44 passing.

### 3. Item-by-item workcard review

| Item | Result and source checks |
|---|---|
| 1 — CDF marker/PDF | Exact lookup and linear interpolation work for valid inputs (`1568–1603`). No `y:[1.0]` remains. Marker and annotation share `cdfAtLatest` (`2632–2657`). PDF is on the left at desktop, uses `histnorm:'probability density'`, auto-bins without a fixed bin count, and has the residual line. Both CDF unavailable paths and both metric-unavailable lists include PDF (`2515–2524`, `2607–2616`). **Null handling fails; finding 4.** |
| 2 — Disabled surfaces/Maintenance | `.is-disabled` uses opacity/cursor, not pointer-event suppression. `applySoloSurfaceMode` sets/removes class, `aria-disabled`, and tooltip (`1485–1500`); baseline click guard and generic tab guard are bound once. Both controls stay visible. Maintenance clarifies the process's event-history store and retains its failure string (`1407–1415`). Gate cases and non-solo integration behavior pass; see §5. |
| 3 — Axes/formulas | All five solo layouts have the requested titles and `automargin:true`; all three solo time-chart call sites explicitly pass `type:'date'` (`2467–2470`, `2568–2572`, `2595–2598`, `2681–2687`). Four formula lines occur under the preserved prose (`948–973`). Residual, strike-window, Simes→Markov→isotonic, and two-norm text trace to report §9. Decision prose correctly uses `≥`, unlike the old report wording. **The reused shared timeline is an exception to the literal “every time chart passes date/every titled axis automargin” checklist: its pre-existing layout at `1726–1732` still omits explicit `type:'date'` and automargin; Chromium inferred date correctly, and I saw no title overlap.** The workcard's five-chart axis table is satisfied. |
| 4 — Timeline/counter | New timeline uses already-fetched `/solo` history and its thresholds; network-driven rendering is inside `stillCurrent()` (`2222–2237`). Solo `/timeseries` call and dead solo URL qualification are removed. Both purge lists include PDF and timeline and zero the counter. The return-based success counters work on both paths, but **decision classification, null probability, empty recovery, and timestamp validation fail; findings 1–3 and 5.** |
| 5 — Guide | Six buttons/pages, first page active, eight-row chain table. Static inline content; no fetch. `setupGuideMenu` has one initialization call at DOMContentLoaded (`1340–1358`, `3093`), not in refresh. Each menu button activates exactly one page. Native button focus + Enter changed to `guide-observed` in Chromium. No trivial keyboard blocker observed. **Residual Guide wording invents an incorrect ordinary-ECDF interpretation; finding 7.** |
| 6 — Labels | Three trace-name branches remain driven by persisted `row.details.probability_label`, not gate outcome (`2418–2427`). Independently exercised raw/mixed/calibrated branches: all return the exact requested new names; raw trace is `Raw Markov posterior p_raw`. **The surrounding prose still equates raw with calibrating; finding 6.** |

No new fetch call, dependency, CDN change, hard-coded threshold, histogram bin count, or runtime tunable was introduced. Display-only numeric examples are traceable to report §9 as allowed by the workcard.

### 4. Ownership, refresh, chart lifecycle, external path, and edge cases

Read **all of `loadTimeseries`**, `2792–2841`, including both success and catch. Its only remaining caller is the external detail task at `2988`; `soloActive` returns at `2983` first. Thus the removed solo-qualified URL block really is dead after this cutover. The external URL remains bare-name with `refresh_ts`, and ownership checks protect success and failure. Catch purges the prior plot, produces the empty state/counter 0, and rethrows; a page-local simulated fetch failure confirmed this. The catch uses literal `0` rather than assigning the return value, but that is semantically equivalent for `renderTimeseries([], {})`.

`sameIdentitySilent` is preserved (`2935–2940`): genuine selection changes clear; silent same-identity ticks keep the solo surfaces and invalidate the previous request nonce **before** awaiting live data. Existing detail-token/selection guards remain. New payload-driven PDF/timeline renders are downstream of the nonce/key guard (`2177–2179`, `2222–2237`); the existing metric-change handler still renders from the owned cached payload. `soloRenderChart`, `soloChartUnavailable`, and `soloPurgeChart` are unchanged. Both whole-surface purge sites include `solo-pdf-chart` and `timeseries-chart` (`2250`, `2733–2741`). Refresh does not rebuild tabs, Guide, or the page body.

Additional real-Chromium probes used `/tmp/solo-ops-p2-rv/review_browser.py`, `contracts.py`, `recovery.py`, and `empty_transition.py`. These mutate only the local browser page or substitute its fetch helper; they do not change upstream data:

- Empty `history`: counter 0, empty message, old Plotly data removed — PASS. Re-populating materializes a new SVG — PASS, **but leaves the empty-message paragraph in the DOM/innerText** — finding 2.
- `p_published:null`: decision helper returns `undecided`, but plotted y becomes **0**, not a gap — finding 3.
- Missing thresholds `{}`: helper returns `unknown` and absent threshold fields do not add lines — PASS. Null threshold values are coerced to zero by the helper/shared renderer; they are not equivalent to valid numeric thresholds. Decision helper's threshold shape mismatch breaks valid live data — finding 1.
- CDF exact point → 0.25; interpolation between `[-1,.25]` and `[1,.75]` at 0 → 0.5; `n<2` and Infinity → null — PASS.
- `latest_recorded_residual:null`: no marker, `F(r) n/a` annotation — PASS. A present record with `residual:null` fabricates a residual-0 marker and PDF line — finding 4.
- `residuals` absent: PDF unavailable notice — PASS. Short pairs with missing second element are filtered by the implementation; null sample values are instead included as zero — finding 4. Auto-binning has no fixed bin count.
- External point `{t:'not-a-date', prob:.5}` counts as **1** despite no valid timestamp; finite-but-out-of-Date-range solo epoch throws `RangeError: Invalid time value` — finding 5. Infinity is rejected by the new solo epoch filter, but null is coerced to epoch zero.
- Label branches raw/mixed/calibrated all exercised — PASS.
- Additional 17 s refresh test at **nonzero window.scrollY = 1450**, with the second/non-default pod selected, retained pod, metric, window scroll, and pod-list scroll (the latter was 0 because the live list fit) — PASS.
- Refresh while Guide is hidden/revealed: observed the already accepted no-resize limitation: at a 900 px viewport, solo chart plot widths were 700 inside 796 px containers immediately after returning from a hidden refresh. All SVGs existed. Not a new finding: workcard explicitly accepts healing on the next 5 s tick.
- No page-level JavaScript errors during the normal live screenshot run.
- Cross-panel time alignment, prompted by the screenshot ticks: ran `/tmp/solo-ops-p2-rv/timezone.py` in Chromium contexts explicitly set to `Asia/Tokyo` and `UTC`. The same history tick differed by **9 hours** between timeline and pod-level chart in Tokyo, but by 0 in UTC — finding 8. The scratch proxy was restarted only for this focused check and stopped again afterward.

### 5. Gate cases and non-solo behavior — PASS

Exercised `refreshSoloSurfaceMode` with page-local row substitutions and restored them afterward:

| State | Observed `aria-disabled` |
|---|---|
| No selection, empty pod list | Removed/enabled |
| No selection, mixed solo + external rows | Removed/enabled |
| No selection, all-solo nonempty list | `true` |
| External selection, even with all-solo list stub | Removed/enabled |
| Selection cleared back to all-solo list | `true` |

Normal live pre-selection smoke checks also verified the visible controls and blocked Lineage click. The specified non-solo system-health integration tests passed, including clicking `#tab-lineage` and showing `#lineage-table`; neither Baseline nor Lineage is incorrectly disabled for that stub.

### 6. Pre-existing unit-environment failures — sampled claim verified

Did not repeat E's 61-file census or claim independent verification of the exact 29-failure count. Cheap independent samples reproduced all three named missing-module categories, without stashing/checking out anything:

1. `.venv_test/bin/python -m pytest tests/unit/test_dashboard_api_routes.py::test_build_bayesian_debug_payload_uses_shared_prediction_diagnostics tests/unit/test_solo_dashboard_routes.py::test_solo_dashboard_browser_inputs_smoke -q` → **2 failed in 1.55 s**, exit 1.
   - First failure: `dashboard_routes.py:4604` imports `data_fetcher`, then shared Prometheus code imports missing **`tabulate`**.
   - Second failure: fresh subprocess fails importing `solo_mode.config` at helper line 79 with missing **`shared`**.
2. `.venv_test/bin/python -m pytest tests/unit/test_solo_exporter.py::test_solo_tick_locks_to_block_end -q` → **1 failed in 0.71 s**, exit 1. Scoring fails with repeated `exporter.py:2035 ... No module named 'hickle'` before the test's has-scored-tick assertion.

Searched the named failing test files/helper for `index.html`/`dashboard_assets` and read the failing test/fixture paths. No failing path reads the HTML bundle; the API test file has a **configuration string** `static_bundle_path: 'dashboard_assets'`, not an HTML read. Thus E's blanket “no dashboard_assets references” wording is imprecise, but these observed failures are independent of the HTML change and do not require a source rollback to establish that. The static bundle test that actually protects the bundle passed 7/7. No environment packages or product code were altered to make tests pass.

### 7. Visual review — requested sizes inspected, no new layout finding

Saved **15 PNG screenshots** under `evidence/E-solo-dashboard-ops/rv-p2-shots/` and **read the images**, not only DOM assertions:

- `dashboard-{1440,900}.png`: full selected-solo dashboard, second pod and non-default memory metric. Both layouts are populated; narrow summary grids stack rather than overlap. Baseline and Lineage remain visible and gray.
- `observed-{1440,900}.png`: blue observed series/yellow reference, readable metric-unit y title, time x title, formula and legend. Long memory-metric title is not clipped at these widths.
- `pertick-{1440,900}.png`: blue p and green dashed tilde_p visible. Long vertical surprise-norm title fits; formula wraps above the plot without colliding with ticks or legend.
- `cdf-pdf-{1440,900}.png`: at 1440 the two 612 px plots are side-by-side, PDF left; at 900 they stack as two 796 px plots. Histogram and red line render; CDF red cross lies on the purple curve, with annotation `F(r) = 0.7167` for this second pod. Axis titles and annotation are readable; no clipped title or empty chart. Body widths were exactly viewport widths (1440/900), not horizontally overflowing.
- `podlevel-{1440,900}.png`: calibrated published green markers, dotted raw series and red gate crosses render. Long anomaly-norm y title fits. At 900 the legend wraps to a second line inside the panel, without overlap.
- `timeline-{1440,900}.png`: line and both threshold lines render, counter 288, no steady-state empty message. **All markers are gray**, matching the independently observed all-`unknown` decisions (finding 1), not the expected undecided/warning markers.
- The timeline and pod-level screenshots show the same probability events at different clock hours (e.g. timeline around 06:00 vs pod-level around 15:00). This is a real timezone mismatch, not different history samples; the focused two-timezone probe confirmed it — finding 8.
- `guide-{1440,900}.png`: desktop vertical menu and full eight-row table; at 900 the menu stacks above the table. Text/table wrap within the card, no clipped columns or empty content. Guide grids measured `200px 1042px` and `818px`, respectively.
- `empty-to-populated-900.png`: populated single-point synthetic recovery. The stale paragraph from finding 2 is **clipped below the fixed plot region in this screenshot**, not visibly overlaid on the plotted point; its persistence was confirmed by DOM and rendered `innerText` after 300 ms. Do not interpret this screenshot as proof of a visible text overlap.

This is local working-tree proxy evidence, **not deployed-image proof**. The Supervisor still owns the deployed-image acceptance gate.

## Findings

### 1. **blocker** — Every valid solo timeline decision is `unknown`: threshold-key mismatch

- **File/lines:** `analyser/dashboard_assets/index.html:2497`, with `2483–2487` and `1549–1552`.
- **Issue:** `soloRenderTimeline` adapts `{normal, anomaly}` to `{normal_threshold, anomaly_threshold}` for the shared plotter, then passes that adapted object to `soloDecisionFromProbability`, which reads `.normal` and `.anomaly`. Both reads are undefined, so every finite probability becomes `unknown`. The decision timeline is materially wrong even though its curve, threshold lines and point count pass E's smoke.
- **Independent evidence:** On the second live pod, thresholds were `{normal:0.2, anomaly:0.8}` and all **288** actual decisions were `unknown`; all **288** expected decisions from the live probabilities were `undecided`. Synthetic `.1/.8` values also became `unknown` through the adapter, while direct raw-shape calls return normal/anomaly. Screenshots show gray markers throughout.
- **Recommended fix:** Use one consistent threshold shape for both consumers (e.g. pass `thresholdsRaw` to the existing helper, or make the helper accept the adapted/backend shape). Preserve `≥ anomaly` / `≤ normal`. Make missing/null/invalid threshold and non-finite probability behavior match `dashboard_routes.py:456–483`, including avoiding `Number(null) === 0`. Add page-local coverage for normal, both boundaries, undecided, missing p and missing thresholds; the current smoke's “both threshold lines exist” assertion is insufficient.

### 2. **should-fix** — Empty→populated recovery retains the “No timeseries data available” paragraph

- **File/lines:** `analyser/dashboard_assets/index.html:1447–1453` and `1748`.
- **Issue:** The empty path appends a plain `<p>` after purging. The success path calls `Plotly.react` but never removes that paragraph. Purging fixes SVG ownership, not placeholder cleanup. The stale message survives both shared-renderer callers and violates the intended empty-state/counter contract at the DOM/text level.
- **Independent evidence:** `soloRenderTimeline({history:[]})` followed by one valid history row produced counter **1**, a fresh SVG, and `paragraphs: ['No timeseries data available']`. After 300 ms the paragraph remained `display:block` and in `innerText`. In the requested screenshot it lies below/clipped by the fixed plot box; this is not claimed as a visible overlay at 900 px.
- **Recommended fix:** Remove the owned empty-state placeholder before a successful render, without wiping the live Plotly DOM on ordinary refreshes. Check both empty→populated and populated→empty transitions for absence/presence of the message as well as SVG and counter.

### 3. **should-fix** — Missing published probability is plotted as a real zero

- **File/lines:** `analyser/dashboard_assets/index.html:2496` feeding `1632–1635`.
- **Issue:** The newly reused shared renderer executes `Number(point?.probability ?? point?.prob)`. A solo point with `prob:null` therefore becomes **0**, even though its decision is intentionally undecided. It paints missing evidence as the calmest possible probability and can introduce false drops/connecting segments. The generic coercion predates P2, but feeding nullable solo history into it is new.
- **Independent evidence:** Synthetic history probabilities `[null, .1, .8]` rendered y values **`[0, .1, .8]`**, with first decision `undecided`.
- **Recommended fix:** Preserve null/undefined as a Plotly gap before numeric conversion; keep only actual finite numeric probabilities. Keep the timestamp-based counter semantics required by the workcard, but do not fabricate probability zero for a missing value.

### 4. **should-fix** — Null residual/CDF inputs and PDF samples are converted to fabricated zeros

- **File/lines:** `analyser/dashboard_assets/index.html:1568–1572`, `2633–2638`, `2697–2699`, `2713–2718`.
- **Issue:** Numeric coercion happens before null checks. `soloCdfAt(points, null)` evaluates F(0), a present latest-record object with `residual:null` paints a cross/line at zero, and a residual sample `[timestamp,null]` enters the PDF as zero. This contradicts item 1's explicit null/non-finite → no marker/n/a requirement and changes the plotted residual distribution.
- **Independent evidence:** For CDF `[[-1,.25],[1,.75]]`, null x returned **0.5**. A latest record with null residual produced cross `{x:[0], y:[.5]}` and PDF vertical line x=0. Samples `[[1,null],[2,1],[3]]` produced PDF inputs **`[0,1]`**. An entirely null latest record is correctly omitted; that narrower happy edge does not cover a null field.
- **Recommended fix:** Reject null/undefined residuals and CDF coordinates before `Number(...)`; include only valid pair second-values in the PDF. Drive annotation and marker from the same validated value, retaining n/a when invalid.

### 5. **should-fix** — Counter still accepts invalid timestamps; finite solo epochs can throw

- **File/lines:** `analyser/dashboard_assets/index.html:1612–1615` and `2490–2495`.
- **Issue:** Shared filtering tests only truthiness of `point.t`, so the new return-based counter is not necessarily a count of renderable timestamps. The solo mapper accepts anything coercible to a finite Number, including null→0, and calls `toISOString()` without verifying that the Date is representable. A finite out-of-range epoch throws and routes the entire diagnostics render through its unavailable catch.
- **Independent evidence:** An external response with `{t:'not-a-date',prob:.5}` and `{t:null,prob:.2}` left the counter at **1**, though neither timestamp is renderable. `soloRenderTimeline({history:[{tick_epoch:1e20,p_published:.1}]})` raised **`RangeError: Invalid time value`**. Infinity is correctly rejected.
- **Recommended fix:** Validate actual timestamp/Date finiteness before sorting, counting or calling `toISOString`, and reject missing epochs before coercion. Preserve the external response/URL contract; just make the post-filter count truthful and skip unrenderable rows rather than failing the whole solo surface.

### 6. **should-fix** — Item 6 prose still says every raw tick is “calibrating”

- **File/line:** `analyser/dashboard_assets/index.html:972`.
- **Issue:** The trace names were correctly migrated, but the prose still says “amber ticks are published raw (calibrating)”. Item 6 explicitly requires updating the prose to the same new terms because raw also means no healthy/calibrated mapper, not necessarily an active calibration lifecycle. Operators still receive the old interpretation immediately above the corrected labels.
- **Recommended fix:** Use the workcard's neutral raw/no-calibrated-mapper terminology in this paragraph while retaining the per-tick label, marker-color and independent gate-cross explanations. Do not infer calibration state from the raw label.

### 7. **should-fix** — Guide contradicts its mid-rank CDF definition

- **File/line:** `analyser/dashboard_assets/index.html:1159`.
- **Issue:** New Guide text defines F(r) as “the share of persisted residuals at or below r”, i.e. an ordinary empirical count CDF. The preceding formula correctly says **mid-rank, strictly inside (0,1)**; the backend explicitly differs on ties and endpoints (`solo_mode/noise.py:692–717`). At the largest persisted residual, the ordinary at-or-below share is 1 but the persisted mid-rank value is below 1. This extra explanation is not report §9's canonical text and recreates the precise endpoint confusion this package is meant to remove.
- **Recommended fix:** Remove the ordinary-count interpretation and retain the accurate empirical mid-rank description/strict-interior semantics; describe PDF y as density and CDF y as F(r). No new closed-form count formula is needed.

### 8. **should-fix** — The same solo tick is shifted by the browser timezone between panels

- **File/lines:** `analyser/dashboard_assets/index.html:2495` compared with `2415` (also existing numeric time inputs in the metric charts).
- **Issue:** The new timeline sends UTC ISO strings to Plotly, while the other solo time charts send epoch milliseconds. In a non-UTC browser, this Plotly version converts the numeric dates using the browser's local clock but reads the ISO-string dates on their UTC clock. Consequently two panels backed by the identical `/solo` history put the same event at different displayed hours. The screenshot comparison exposed this even though E's smoke only checks `xaxis.type === 'date'`.
- **Independent evidence:** For the same first `tick_epoch = 1793864100`, timeline input was `2026-11-05T07:35:00.000Z`, with axis linear value `1793864100000`. In an explicit `Asia/Tokyo` Chromium context, pod-level input `1793864100000` converted to axis linear value `1793896500000`: **+9 hours**. An explicit UTC context gave equal linear values (delta 0). The existing screenshots show the offset as well.
- **Recommended fix:** Normalize the solo time-chart inputs to one declared time convention so corresponding ticks align across timeline, pod-level, per-tick and observed panels, without changing the external API contract. If using numeric values in the reused timeline renderer, ensure its axis explicitly remains `type:'date'` rather than auto-inferring a linear epoch axis. Include at least one non-UTC browser context in the local alignment check. The new mapper follows the workcard's ISO suggestion; this finding is advisory feedback on its integration with the existing charts, not a claim that E ignored that suggestion.

## Disposition rationale

The edit respects the one-file scope, preserves the request-ownership/refresh design, passes the required regression suite and E's smoke independently, and renders without new title overlap or clipped panels at 1440/900 px. It is nevertheless not ready for acceptance: the actual live decision timeline is wrong for every point because of a threshold-shape mismatch; corresponding chart events also have inconsistent clock times in non-UTC browsers. Focused edge checks expose missing-data and counter/placeholder failures that the happy-path smoke does not cover. The remaining prose findings are explicit workcard/scientific-correctness issues, not style preferences. Recommend correcting the eight findings and extending the scratch/browser acceptance to cover them before the Supervisor's deployed-image gate. The independent sampled unit failures are environment/import problems, not evidence against this HTML diff.
