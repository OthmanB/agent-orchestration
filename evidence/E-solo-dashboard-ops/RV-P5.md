# RV Review — SOLO-OPS-P5

- Date: 2026-11-07
- Reviewer: RV-P5
- Disposition: **accepted_with_findings** (advisory; Supervisor owns acceptance/waivers)
- Reviewed baseline: HEAD `01f6c50` per assignment; uncommitted P5 in `analyser/dashboard_assets/index.html`.
- **No blocker findings; five should-fix findings below.** The prescribed smoke passes, but it does not establish every requested acceptance condition.
- Read-only repository review: no repository file modified/staged/committed by RV. Only this orchestration evidence, screenshots, and `/tmp/solo-ops-p5-rv/` scratch were written. No cluster/SSH/kubectl/docker/gh, live GPU work, or service-management changes. Scratch proxies 8097 and 8098 were stopped after use; existing forwards/services were left alone.

## Inputs read

Read the reviewer mandate, full P5 card including its long contract lines and RV checklist, P5 prompt, R-P5, E-P5, full P4 card, and operations report §9 (562–601). Also read the relevant current source in `driver.py`, `diagnostics.py`, `scan.py`, `fusion.py`, `exporter.py`, `dashboard_routes.py`, `core_orchestration.py`, deployed config, and the P3 addendum in `markdown/2026-10-09-solo-mode-runtime-cutover.md:568–600`. Current source, not the superseded R-P5 proposals, governed this review.

## Checks performed and commands

Repository below means `/Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector`; test commands ran from its `analyser/` directory.

### 1. Scope, keep-list, syntax, and source comparison

- Ran `git diff -- analyser/dashboard_assets/index.html && git status --short` once at review start. P5 diff: **176 insertions / 33 deletions, index.html only**. Status also showed the declared out-of-scope user changes: `M AGENTS.md`, untracked `analyser/agent-orchestration/`, and the operations report under `markdown/`.
- Ran `git diff --stat -- analyser/dashboard_routes.py analyser/solo_mode analyser/exporter.py analyser/tests analyser/dashboard_assets/vendor deploy` through a Python subprocess: **empty**. Backend/tests/vendor/deploy were not changed by P5.
- Programmatically compared HEAD and current HTML: exactly **one inline `<script>`**, all 23 checked keep-list IDs present exactly once (eight badges, analysis badge, five solo charts, timeline/legend/counter, Baseline/Lineage, Maintenance/export/purge/history). `data-tex` sequence is **byte-identical to HEAD**, not merely count-equivalent.
- Exhaustive regex check for `Asia/|America/|Europe/|JST|PST|UTC[+-][0-9]` in current HTML: **no matches**. The `analysis_state` accesses are code/comments, not Guide prose.
- Non-solo analysis-state branch is **not literally byte-identical**: E substituted the shared `analysisBadge` local for repeated `getElementById` calls and attached it as `else if` after the solo branch. After normalizing only that binding/branch attachment, its text is identical to HEAD. Independent runtime fixtures preserved ready/ok, degraded/warn, error/critical, other/neutral. This behavior-preserving deviation is not a finding.
- `/tmp/solo-ops-p2/check_syntax.sh` → **SYNTAX_OK**, exit 0.
- Refresh identity/nonce/ownership logic and formula refresh behavior were not changed by the diff; badge handlers are installed only by the single DOMContentLoaded call at `index.html:3412–3416`.

### 2. Requested test suites and independent copied smoke

Commands actually run:

```sh
./.venv_test/bin/python -m pytest tests/integration/test_dashboard_overview.py tests/integration/test_dashboard_system_health.py tests/unit/test_static_bundle_contract.py -q
sh /tmp/solo-ops-p2/check_syntax.sh
env PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared /tmp/solo-p3-venv/bin/python -m pytest tests/unit/test_dashboard_api_routes.py tests/integration/test_canonical_route_contracts.py -q -p no:cacheprovider
python3 /tmp/solo-dash-dev/static_proxy.py --port 8097
```

- Frontend/bundle suite: **10 passed**, 7.62 s, exit 0. Syntax: exit 0.
- Backend contract suite: **80 passed, 1 failed**, 1.60 s, exit 1. Only failure: the declared existing `test_build_bayesian_debug_payload_uses_shared_prediction_diagnostics`, `dashboard_routes.py:4597`, `ModuleNotFoundError: No module named 'mlflow'`. No other failure.
- **Never ran `tests/unit/test_solo_dashboard_routes.py`.** No full suite, build, deploy, or live mutation was run.
- Copied `/tmp/solo-ops-p5/smoke.py` to `/tmp/solo-ops-p5-rv/smoke.py`; changed **only BASE from port 8090 to 8097**. Programmatic equality check after reverting that one string: true.
- Ran `analyser/.venv_test/bin/python /tmp/solo-ops-p5-rv/run_smoke.py`: **154/154 passed**, exit 0, 105.61 s. The runner executes the copied smoke unchanged, except it redirects Page/Locator screenshot destinations at runtime into `rv-p5-shots/` so E/P4 evidence is not overwritten.
- Diffed the P4 portion against `/tmp/solo-ops-p4/smoke.py`. The count change and time-title exception are present, plus strengthened banned-token checks. **The claim that every other P4 axis guard remains intact is false**: y-title shortness and all original punctuation guards were removed (finding 5). The numeric pass total therefore is not a complete proof of unchanged P4 assertions.

### 3. A — level logic, real pods, and adverse scenarios

- Inspected `soloAnalysisLevel` at `index.html:1375–1392` and its use at `:3167–3188`. Only the three contracted payload fields are read. Error beats a finite score; raw/calibrated both use ok; unknown label with a score is neutral. Null payload and empty object do not throw. Raw probability suffix is exactly `(raw - no verified calibration mapper)`.
- Independent real-page fixtures: probability **null / undefined / 'x' / NaN / ±Infinity → degraded**, **0 → healthy - raw**, uppercase ERROR with a calibrated zero score → error. **Empty string → healthy - raw**: finding 1.
- Independently fetched `/api/dashboard/pods`, then **each of the ten** identity-qualified `/api/dashboard/live/<family>/<pod>?namespace=…&cluster=…` endpoints through 8097. **10/10 healthy - raw / ok**, all fresh at this observation. Copied smoke also selected two pods through the UI and checked stability after refresh.
- Aborted the owning `/live` GET in a browser-only route: analysis badge became **error / badge critical**. The resulting failed-fetch console messages were intentional probe output, not production errors.

**Source-grounded adverse-case analysis:** these are hypothetical failure scenarios, not faults injected into the live detector.

| Scenario | What actually happens / what remains visible |
| --- | --- |
| A score becomes old while no new score arrives | [INFERENCE, source-derived] Existing probability/label keep the analysis badge green. `_pod_freshness_from_snapshot` and `_data_freshness_payload` separately turn Indicator B into No recent data, and Pipeline Status into stale/critical. Current deployed multipliers are 11/13 × 30 s, so B turns stale after **390 s** from the snapshot update; TTL is **900 s** (`configmap.yaml:97–98,170–174`). After TTL cleanup on the next exporter poll, a retained identity has null probability → degraded; a removed identity can instead produce a GET refusal → the fetch-error badge. |
| Mandatory raw tail is missing, or its model is stale/not built, while a previous score still exists | [INFERENCE, source-derived] Exporter preflight **defers** the tick (`exporter.py:1630–1663`), or catch-up returns for no valid model (`:1683–1690`), without immediately clearing the last score. Both analysis and B can stay green during the freshness allowance; then B goes red while analysis still describes the last score, until expiry. `/solo` mandatory ready is historical scored-tick presence (`diagnostics.py:692–737`), not proof that this tick scored. |
| A mature mandatory metric is uncomputable and the driver actually skips | `driver.py:1492–1520` records the skip and returns no scored result. **This need not wait for TTL:** `core_orchestration.py:207–213` returns an error envelope and exporter `:2068–2103` clears current eligibility immediately. `/live` then has null probability → degraded, plus runtime not_running / Pipeline critical / B stale. The card's universal “skip → wait for entry expiry” explanation is incomplete. |
| Runtime request/error failure | Exporter clears the entry and puts the error on inventory/error_store. `_solo_analysis_state` checks only entry.error_message, not inventory/error_store (`dashboard_routes.py:2138–2145`). Thus the normal failure path yields API unknown + null probability and **P5 degraded, not error**. This is finding 2; other panels do still expose the failure. |
| `/live` network/HTTP failure | Owning fetch-failure path `index.html:3342–3354` explicitly paints error; independently exercised. Old charts can remain, but are not silently accompanied by a healthy analysis badge. |
| Non-mandatory metrics missing; drift warning; or high anomaly probability | These intentionally do not demote analysis-path health. Computable/drift and the distinct Decision/Alert/Indicator A surfaces remain visible. This is the agreed contract, not a hidden anomaly classifier. |

**Judgment on staleness:** keeping freshness out of the level is acceptable as the card's deliberate separation of instruments, not a newly proposed health check. However green means **the last published scoring path**, not a present-tense guarantee that scoring is currently working. The Guide should say that explicitly and direct the reader to B/Pipeline Status; it currently says “scoring works.” The runtime-error mismatch in finding 2 is separate and is not cured by accepting the stale-data design. No live stale pod was observed during this review.

### 4. B — badge wall, source accuracy, refresh, geometry

- Copied smoke checked all eight names/variants, warming/ready/no-data/mixed-window fixtures, raw/calibrated, gate states, computable 1/0.5/absent, drift, exact tooltip text, and Guide repetition. **All passed.** All badge IDs and initial/writer/reset-map names agree.
- All eight tooltips are **siblings**, not badge children. Independent 17 s observation saw **four live responses**, the same eight tooltip and wrapper node identities, no duplicated/replaced tooltip nodes. Separate nonzero-scroll refresh check retained math node identity too.
- Source accuracy: window is raw fit-window row completeness, not calibration (`diagnostics.py:206–214,307–321`); mandatory is historical scored-row presence (`:692–737`); gate state differs from verified publication (`driver.py:1655–1684,1726–1729,1794–1827`); oldest scored metric-model age is max age (`:1835–1839`); drift is split-half residual Wasserstein distance vs persisted reference threshold and record-only (`scan.py:245–275,1534–1667`; `driver.py:1621–1635`); computable direction is computable/expected (`:1607–1611`); Keff is the residual-correlation participation ratio, clamped to [1,K] (`fusion.py:130–153`). No materially false tooltip sentence was found within those definitions. The historical nature of mandatory is important in the adverse cases above.
- Independently hovered **all eight** and keyboard-focused all eight at **1440/1200/900/800 px**. All tips visible and inside their nearest outer card; no measured movement of the observed-chart panel. Body horizontal overflow: **0**. Normal badge row at rest does not overflow.
- Caveats not detected by E's smoke: shown tips can increase row scrollWidth by **24 px** (and 13 px for Keff at 800), and first/last tooltips clip above the **viewport** when their badge is near its top. Finding 3 distinguishes viewport clipping from card containment; card containment itself passed.
- Scoped display:none/display:block CSS is outside the literal “no CSS change” instruction, but is narrowly display-local and keeps hidden popups out of the scrolling overflow area. No separate style-preference finding is raised.

### 5. C — timezone truth, fractional offsets, DST, and Plotly baseline

- Real Chromium contexts, current offset/title observed:

| Context | `timeAxisTitle()` |
| --- | --- |
| Asia/Tokyo | `Time (Asia/Tokyo, UTC+9)` |
| America/New_York | `Time (America/New_York, UTC-5)` |
| Asia/Calcutta | `Time (Asia/Calcutta, UTC+5:30)` |
| UTC | `Time (UTC, UTC+0)` |
| Australia/Lord_Howe | `Time (Australia/Lord_Howe, UTC+11)` |
| Asia/Kathmandu | `Time (Asia/Katmandu, UTC+5:45)` — Chromium's resolved IANA alias |
| America/St_Johns | `Time (America/St_Johns, UTC-3:30)` |

- All four time axes equal the helper in each context; three solo chart axes retain automargin:true. Shared timeline's pre-existing automargin:false is unchanged. CDF/PDF remain residual r. No source zone literal.
- Tested actual first-point **SVG tick text**, not just titles, using `2026-11-07T12:34:00+00:00` and equivalent numeric `1794054840000`: ISO displays **12:34 UTC in every context**, numeric displays **21:34 Tokyo / 07:34 New York / 18:04 Calcutta / 12:34 UTC / 23:34 Lord Howe / 18:19 Kathmandu / 09:04 St Johns**. Labels are truthful for these inputs.
- Date fixtures in real timezone contexts: Lord Howe July **UTC+10:30**, November **UTC+11**; St Johns July **UTC-2:30**, November **UTC-3:30**. Negative fractional formatting is correct.
- Titles fit horizontally at 900 px (e.g. timeline Tokyo x=373.67–560.33; New York x=347.78–586.22). **But the expanded timeline title intersects its date tick at 900 px, unlike HEAD**: finding 4.
- Known limitation retained: displayed offset is for now, not every point across a DST transition. No per-point DST change requested or made.
- Independent HEAD snapshot: `git show HEAD:analyser/dashboard_assets/index.html` materialized under `/tmp/solo-ops-p5-rv/head-assets/`, plus existing `shared_selectors.js` and `vendor/`; served with `env DASH_ASSETS=/tmp/solo-ops-p5-rv/head-assets python3 /tmp/solo-dash-dev/static_proxy.py --port 8098`. No stash/checkout or worktree alteration.
- `analyser/.venv_test/bin/python /tmp/solo-ops-p5-rv/run_head_smoke.py`: **103/103 P4 checks pass**, exit 0, **one** `_redrawFromAutoMarginCount` pageerror, **zero** console errors, 49.15 s. P5 full copied smoke likewise reports **one** identical pageerror and **zero** console errors. The error therefore reproduces on HEAD without P5.
- Separate matched **60.00 s** HEAD/P5 refresh + metric/pod/tab-switch observation: **0/0 pageerrors**, no action failures. The probe's final console arrays also contain two messages from its deliberate later `/live` abort (mutable arrays persisted after that step); those are not 60 s spontaneous errors. No evidence of increased error frequency/visibility from P5 in these observations; this is not a statistical guarantee. The pre-existing race is not a P5 finding and was not suppressed/fixed.

### 6. D — Guide content and preserved P2/P4 behavior

- **Seven** menu buttons/pages, chain default and status not default; exactly one active page on every menu switch. Status has the required four-row level table and eight tooltip-identical blocks. Dormancy paragraph identical in chain/pod-level. Visible-text banned-token sweep clean on all seven pages.
- **28 data-tex nodes / 12 strings / four panel formulas**, 28/28 rendered, zero KaTeX error nodes; original TeX sequence unchanged. No new threshold numbers, “removing outliers,” or invented calibration constants.
- Calibration explanation traced to `fusion.py:500–532,616–644` and `driver.py:1676–1729,1794–1827`: empirical healthy-reference exceedance mapping, first-half isotonic fit, held-out gate AND spread guard, verified mapper never demoted. The cadence sentence is correctly restricted to a **verified** mapper; without one source evaluates each valid-window tick, not once/288.
- Independent smoke re-established marker on interpolated CDF, PDF left of CDF, **288 timeline points and matching counter**, grayed Baseline/Lineage, Guide switching, rendered math, and both KaTeX abort modes. Offline fallbacks nonempty/readable, charts still present, no page exceptions, no overflow at 1440/900.
- Copied smoke's scroll check started at zero. RV supplemented it at 900 px with **pod-list.scrollTop=39 and window.scrollY=1450**, non-default memory metric: **six pod-list responses over 17 s**, every sampled selection/scroll identical, same tooltip/math nodes. Thus the requested nonzero-scroll case was actually exercised, not inferred from the zero-scroll smoke.

### 7. Visual evidence actually read

Saved under [`rv-p5-shots/`](rv-p5-shots/). Read the images, including:

- `wall-1440.png`, `wall-900.png`, first/last `tip-0-*` / `tip-7-*` at 1440/900/800, plus `smoke-p5-shots-tip-first-1440.png` and `tip-viewport-{0,7}-{1440,900}.png`.
- `smoke-p5-shots-guide-status-{1440,900}.png`, `guide-status-900.png`, `smoke-p5-shots-guide-chain-dormancy-1440.png`, `chain-dormancy-900.png`.
- `smoke-p5-shots-axis-tokyo.png`, `smoke-p5-shots-axis-new_york.png`, `axis-Tokyo-900.png`, `axis-New_York-900.png`, and paired `timeline-axis-{HEAD,P5}-900.png`.
- `smoke-p4-shots-offline-guide-chain.png`.

Judgment: green mandatory/gate/published and neutral partial-window are calm and legible. Only computable<1 and an actual drift flag were amber in the observed wall states; raw alone was never amber there. Guide text/math/fallbacks are readable at both widths, tooltip white-on-dark contrast is good when onscreen. The screenshots reveal the tooltip viewport clipping and narrow timeline-title collision below. Existing amber raw chart markers and existing Pipeline Overall degraded/write-errors-unknown are unchanged, not P5 badge logic regressions.

## Numbered findings

1. **should-fix — Empty probability can falsely produce a healthy level.** `analyser/dashboard_assets/index.html:1380–1383`. `Number('')` is 0, so `soloAnalysisLevel({probability:'', probability_label:'raw'})` returns healthy - raw / ok; only null/undefined are explicitly excluded. This was independently executed. It is a malformed-payload edge, **not an observed live incident**, but it is specifically in the requested adversarial checks and violates the intent that an absent score is never healthy. **Fix:** reject empty/blank probability before numeric conversion (or require an actual finite number, matching the API's numeric payload), preserve valid 0, and add the empty/NaN/Infinity fixtures to E's smoke.

2. **should-fix — Real runtime errors are not represented by the new red error level.** `analyser/dashboard_assets/index.html:1377–1383,3171–3173,1242`; source chain `analyser/exporter.py:2055–2065,2092–2103` and `analyser/dashboard_routes.py:2138–2145,2585–2592,4303`. The normal error path deletes the score entry and records error on inventory/error_store, but the API analysis helper checks only the now-absent entry. Independently calling the real helpers with solo inventory status:error produced **analysis_state unknown + runtime_status not_running**; P5 maps null score to **degraded**, not error. Other panels do show not_running/critical, so this is not a hidden green incident, but the new Guide's “pod reports an error → red” promise and the operator's four-level requirement are not fulfilled by the ordinary source path. **Fix:** Supervisor should explicitly amend the three-input display contract to honor the existing runtime not_running/error fact before presenting a healthy/degraded level, using the existing `/live` payload and leaving backend APIs unchanged. Keep freshness separate if that decision stands. Also qualify Guide “scoring works” as last-published-score readiness and tell readers where freshness/current flow is shown; do not imply immediate detection of every mandatory-tail loss.

3. **should-fix — Tooltips fit the outer card, but can be unreadable above the viewport and still overflow the badge row while shown.** `analyser/dashboard_assets/index.html:1314–1335` plus tooltip placement at `:575–578`. With the badge at viewport y=80, first-tooltip top is **−53.875 px**, last-tooltip top **−36.25 px**, at 1440/900/800. This is real clipped text in `tip-viewport-0-900.png` and `tip-viewport-7-1440.png`, not just a rect assertion. At 900 the model-age hover also adds **24 px** to row scrollWidth; Keff adds 24 at 1440 and 13 at 800 (body itself does not overflow). **Fix:** fit against viewport as well as the card, choose a below-badge placement when above-space is insufficient, and constrain shown popup horizontal extent to the row's usable bounds without clipping its text. Exercise hover/focus near the viewport top and assert both viewport containment and shown-row overflow, rather than checking the hidden/resting row only. This remains display-local; no new service/API surface is needed.

4. **should-fix — Adaptive timeline title collides with a date tick at 900 px.** `analyser/dashboard_assets/index.html:1997–2002`. The new wider title retained the fixed bottom margin 42. Paired HEAD/P5 browser measurement on identical 900 px Tokyo pages: title y=613.875–630.875, date tick `00:00 / Nov 7, 2026` y=589.875–620.475. P5 title x=373.672–560.328 intersects that tick x=506.623–580.857; HEAD's short Time title x=449.781–484.219 does **not**. The paired screenshots visibly confirm the collision. **Fix:** give the shared timeline sufficient bottom margin/title standoff or equivalent date-axis layout space for its two-line date ticks, preserving existing date behavior and the three solo charts' automargin. Add a rendered tick/title nonintersection check, not only title-vs-viewport width.

5. **should-fix — P4 assertion preservation claim is overstated.** `/tmp/solo-ops-p5/smoke.py:333–340` versus `/tmp/solo-ops-p4/smoke.py:323–326`; also E-P5's “all y titles and CDF/PDF ... keep strict checks” statement. E removed `all(len(t.split()) <= 2 for t in got)` and the punctuation-ban predicate for the entire pair, then restored only x-title shortness. The original y-title shortness and original CDF/PDF x/y punctuation guards are no longer asserted. This exceeds the two authorized deltas even though exact current titles happen to pass. **Fix:** restore those predicates for every y title and for both CDF/PDF x titles; relax only the three intended time x titles. Correct E's evidence claim. RV's supplemental strict checks pass on the current page, so this is a test-quality/evidence defect, not a demonstrated current y-title rendering defect.

## Disposition rationale and evidence limitations

The core display-local cutover, calm/raw green state, eight accurate badge explanations, timezone truth, Guide expansion, and preserved P2/P4 math/chart/refresh behavior are established independently. No backend/scoring/config scope change or live-observation interference was found. The known mlflow environment failure and Plotly race are independently accounted for, not treated as new regressions. Acceptance is **with findings**, not a clean rubber stamp: the ordinary runtime-error path, blank-score edge, tooltip viewport geometry, timeline date/title collision, and overstated test preservation should be resolved or explicitly waived by S before recording a clean P5 gate.

Detailed scratch evidence: `/tmp/solo-ops-p5-rv/{static-checks.txt,probe-results.json,supplement-results.json,head-smoke-errors.json,tooltip-viewport.json,axis-geometry.json}`. Commands also run: `analyser/.venv_test/bin/python /tmp/solo-ops-p5-rv/{probe.py,supplement.py,remaining_zones.py,tooltip_viewport.py,axis_geometry.py}` and the direct `dashboard_routes` helper check described above. The initial broad probe exited 1 on its first Lord Howe chart-readiness timeout after completing the other sections and four zones; only the remaining timezone step was resumed, with settled selector readiness, and all three remaining contexts passed. No completed section was represented as having passed merely because the process later failed. Proof is local proxy + read-only live payloads, **not the deployed P5 image**. The 60 s race comparison is a bounded observation, not a frequency guarantee.
