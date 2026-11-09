# RV Review — SOLO-OPS-P2, revision 1

- Date: 2026-11-06
- Reviewer: RV-P2
- Disposition: **accepted_with_findings** (advisory; Supervisor decides)
- Remaining findings: **0 blockers, 1 should-fix**. The original live-decision blocker is resolved; the revision's null-threshold-line acceptance is not fully met.
- Scope: read-only re-review of `analyser/dashboard_assets/index.html`, against `solo-ops-P2-rev1.md`, the original workcard/review, and E-P2's Revision 1 report. No product files edited, commits, cluster/SSH/kubectl operations, or API mutations.

## Checks performed

### Commands and independent execution

All Python commands below ran from `pipelineml-anomaly-detector/analyser/`.

| Check | Result |
|---|---|
| `/tmp/solo-ops-p2/check_syntax.sh` | Exit 0, **SYNTAX_OK** |
| `.venv_test/bin/python -m pytest tests/integration/test_dashboard_overview.py tests/integration/test_dashboard_system_health.py tests/unit/test_static_bundle_contract.py -q` | Exit 0, **10 passed in 8.59 s** |
| `.venv_test/bin/python /tmp/solo-ops-p2-rv/smoke-rev1.py` | Exit 0, **64/64 checks passed**, 33.86 s |
| `.venv_test/bin/python /tmp/solo-ops-p2-rv/rev1_checks.py` | Exit 0; independent live/synthetic edge probes, external renderer parity, loader success/failure/staleness, and all-four-chart timezone checks. Results below; the null-threshold probe exposes the remaining defect. |

Copied E's updated `/tmp/solo-ops-p2/smoke.py` to my own `smoke-rev1.py`, changing only port **8090 → 8092**. E's script was not edited. Started `python3 /tmp/solo-dash-dev/static_proxy.py --port 8092` as named service `rv-p2-rev1-proxy-8092`, then **stopped that service after all probes**. Ports 8090/8091 and the user's 8080 forward were not managed or modified. All proxy/API requests were GET-only.

The extended smoke retains the earlier chart/Guide/gate/refresh checks and now exercises revision cases. It passed the non-default memory metric, marker/annotation equality (`F(r) = 0.5464912280701755`, annotation `0.5465`), 288 timeline points, correct live decisions, six Guide pages, and four automatic refreshes over 17.2 s without selection/metric/scroll changes or solo-panel hiding. However, its check named “null-threshold” passes **`{}`**, not `{normal:null, anomaly:null}` through `soloRenderTimeline`; therefore 64/64 is not proof that explicit null thresholds are handled end-to-end.

### Re-verification of all eight original findings

Current product-file line numbers are used below.

| Original finding | Independent result |
|---|---|
| **1. Decision threshold-key mismatch** | **Live blocker fixed; threshold-line subcase still open.** `soloRenderTimeline` now passes `thresholdsRaw` to the decision helper (`2603`), separately adapting plot thresholds. My second live pod yielded **288 actual undecided decisions = 288 expected**, with **0 gray markers**. Helper calls for `.1,.2,.5,.8,.9` returned `normal,normal,undecided,anomaly,anomaly`; null/undefined/NaN/Infinity probability returned undecided. Missing/null/empty/non-finite/reversed thresholds returned unknown. But the plot-threshold adapter at `2573` still converts null/empty thresholds to zero; see finding 1 below. |
| **2. Stale empty-state paragraph** | **Fixed.** `renderTimeseriesMessage` tags its owned paragraph (`1449`); successful render removes only that node (`1684–1692`). Through the actual solo caller: empty history produced message + counter **0**; repopulating three rows produced **0 paragraphs**, no empty-message text in `innerText`, a fresh SVG and counter **3**. No ordinary-refresh Plotly DOM wipe was introduced. |
| **3. Null probability rendered as zero** | **Fixed for the shared renderer/new timeline.** `[null,.1,.8]` rendered y **`[null,.1,.8]`**, decisions **`[undecided,normal,anomaly]`**, counter **3**. The null guard precedes numeric conversion (`1695–1704`). Also verified external-path gap behavior, below. |
| **4. Null residual/CDF/PDF values** | **Fixed for the reported null/undefined/non-finite cases.** `soloCdfAt(points,null/undefined)` returned null; exact lookup returned .25, interpolation .5, null-coordinate entries were skipped. A latest record with `residual:null` produced **no CDF marker**, annotation **`F(r) n/a`**, **0 PDF lines**; `[[1,null],[2,1],[3]]` produced PDF samples **`[1]`**. Guards precede conversion in helper/marker/PDF builders (`1584–1631`, `2743–2752`, `2813–2817`, `2834–2838`). |
| **5. Invalid timestamp count/throw** | **Fixed for the reported cases.** `dateMs`/`isValidTimeValue` validate representable dates (`1639–1656`); shared filtering/sorting uses them (`1665–1668`). Solo null/missing/out-of-range/non-finite/unparseable epochs were skipped without throwing: mixed bad rows plus one valid epoch yielded counter **1**, x **`[1700000000000]`**. External ISO points mixed with invalid text/null/1e20 timestamps yielded counter **2** for two valid timestamps. |
| **6. Raw prose = calibrating** | **Fixed in the requested Pod-Level panel and Guide scope.** Paragraph `972` now says published raw means no healthy calibrated mapper; it retains color/gate explanations and contains no “calibrating.” Guide contains no equivalent raw=calibration-in-progress wording. The pre-existing live-summary suffix at `2990` remains outside this revision's explicit panel/Guide scope, as E disclosed; not promoted into a new finding. |
| **7. Ordinary-count CDF explanation** | **Fixed.** Guide `1159` now describes the empirical mid-rank CDF, strict interior and tie distinction, with PDF y=density; it no longer says “at or below.” No closed-form count formula was introduced. |
| **8. Cross-panel timezone mismatch** | **Fixed across all four time charts, not only timeline/pod-level.** Solo timeline now feeds epoch-ms numbers (`2601`) and shared layout explicitly sets date (`1809`). Re-ran an expanded independent timezone probe in `Asia/Tokyo` and `UTC`, checking live axis conversion and a synthetic common tick through the real timeline, pod-level, per-tick and observed builders. All four input types were numeric, all four axes date, and all four displayed linear positions were exactly equal in each context. Details below. |

### Timezone probe: all four solo time charts

For the common tick `1793865900000` ms, my synthetic payload went through **all four actual builders**, not merely a comparison of raw inputs:

| Browser context | Timeline displayed linear x | Pod-level | Per-tick | Observed |
|---|---:|---:|---:|---:|
| Asia/Tokyo | 1793898300000 | 1793898300000 | 1793898300000 | 1793898300000 |
| UTC | 1793865900000 | 1793865900000 | 1793865900000 | 1793865900000 |

The existing numeric-date convention remains browser-local; the revision correctly makes corresponding solo panels agree. A live common-anchor axis conversion also matched across all four. No claim is made that the revision changes every chart to a new global UTC convention; that was not the workcard's selected fix.

### Shared external-path regression review

Read `renderTimeseriesMessage`, `renderTimeseries`, and **all of `loadTimeseries` (`2916–2965`)**, including both catch and ownership rejection.

For a concrete before/after reference, extracted the original `renderTimeseries` function from **`git show HEAD:analyser/dashboard_assets/index.html`** into `/tmp/solo-ops-p2-rv/baseline_render.js`, renaming only its function declaration. Executed original and revised functions in the same real Chromium page, purging between them, with unsorted external ISO-string points and valid thresholds.

- **Valid external ISO behavior preserved:** sorted x strings, y values, all trace definitions, marker colors, model-family/confidence/freshness/fallback customdata, hover template, threshold traces, resolved date-axis type/range, y range and hover mode were **identical** in the reference/revised snapshots. Example sorted y was `[.1,.5,.8]`; x range was `2026-11-05 23:52:46.3089` → `2026-11-06 02:07:13.6911` for both. Explicitly repeated ISO parity in **Tokyo and UTC**, including `Z` and `+00:00` strings: identical in each context. This is renderer/axis parity, not a claimed deployed external-pod screenshot comparison.
- **External URL/contract preserved:** a page-local `fetchJSON` substitute recorded exactly `/api/dashboard/pods/external-review/timeseries?refresh_ts=…`, with no namespace/cluster appended. `loadTimeseries` plotted the three ISO points and set counter **3** from the renderer return.
- **External null probability now a gap:** two valid ISO timestamps, one with null probability, rendered y **`[null,.5]`**, counter **2**. This change is **acceptable and intentional display behavior**: missing probability is not evidence of a real zero; no API payload/route contract is changed, and timestamp-based count semantics remain intact. It is not a regression to undo.
- **External invalid dates/null thresholds:** invalid timestamp strings/null/out-of-range values were excluded, and direct external `{normal_threshold:null,anomaly_threshold:null}` drew **0** threshold lines. The remaining null-line bug is specifically the solo adapter, not the shared renderer's guard.
- **External fetch failure:** simulated owning failure was rethrown; chart purged, message displayed, counter **0**, no Plotly data left.
- **External stale response:** deferred success with an intervening detail-token increment did not repaint the cleared chart or change counter 0. Existing ownership guards remain effective.

### Regression scan and scope

Scanned the full current HTML diff and its surrounding changed functions. Current scope remains only `index.html` among P2 files (observed cumulative **+708/−53**); other status entries are the declared pre-existing `AGENTS.md` and untracked orchestration/report items. P1's ConfigMap no longer appears in the working-tree diff. The small line-count discrepancy with E's +716 report is recorded, not treated as a product defect.

Recounted the keep-list IDs: exactly one each, including new PDF. No new fetch call or Plotly CDN reference was added. Reviewed the retained `stillCurrent()` guard (`2258–2260`, `2307`), silent-same-identity nonce path (`3059–3064`), both whole-surface PDF/timeline purge lists (`2331`, `2857–2865`), sole external `loadTimeseries` caller (`3112`), and one-time Guide initialization (`3217`). No new lifecycle/request-set/Guide-binding regression found. Normal regressions remain covered by the 10 required tests and all 44 retained smoke assertions. Did not rerun the unrelated full unit-suite environment failures from the first review; this narrow revision does not touch their dependencies or source.

## Numbered findings

### 1. **should-fix** — Solo plot-threshold adapter still converts explicit null/empty thresholds into zero lines

- **File/lines:** `analyser/dashboard_assets/index.html:2573–2576`.
- **Issue:** `finiteNumber = value => Number.isFinite(Number(value)) ? Number(value) : null` still accepts `null` and `''` as **0**. The revised shared renderer correctly rejects null/empty thresholds before conversion (`1760–1767`), but the solo adapter has already destroyed that missing-value information before passing the threshold object to it. The decision helper correctly says unknown while the plot invents decision gates at zero. This misses revision workcard item 1's explicit end-to-end requirement.
- **Independent reproduction:** Call `soloRenderTimeline` with one valid history row and `tick.details.thresholds = {normal:null,anomaly:null}`. Result: decision **unknown**, but traces **Warning Threshold y=[0,0]** and **Critical Threshold y=[0,0]**. `{normal:null,anomaly:.8}` and `{normal:'',anomaly:.8}` similarly paint a fabricated warning line at 0. Missing `{}` correctly draws none; valid `.2/.8` draws the expected lines. Thus this is not a live all-valid-threshold failure and does not reopen the original 288-point decision blocker.
- **Recommended fix:** Reject null/undefined/empty values in the solo adapter **before** `Number(...)`, or pass raw threshold fields through to the now-validating shared renderer. Keep valid numeric zero legal. Extend the smoke to invoke `soloRenderTimeline` with explicit null/empty threshold fields and assert the missing line is absent; the present `{}`-only test does not cover this regression.

## Disposition rationale

The original live decision bug and seven other reported behaviors have been independently rechecked, with the substantive fixes confirmed; all specified tests and the expanded smoke pass. External valid-ISO rendering is unchanged in direct original-vs-revised Chromium comparisons, and external null-as-gap is the correct missing-data display behavior. One should-fix remains in the solo threshold adapter, making revision acceptance incomplete for explicit null/empty thresholds despite the passing smoke. Recommend the small adapter correction and targeted smoke extension before closing the acceptance checklist. Findings remain advisory; deployed-image proof is still the Supervisor's gate.
