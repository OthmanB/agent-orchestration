# RV Review — SOLO-OPS-P5 revision 1

- Date: 2026-11-07
- Reviewer: RV-P5
- Disposition: **accepted_with_findings** — advisory; S owns acceptance/waivers.
- **No blockers; two should-fix findings remain**, both concerning tooltip placement/its acceptance evidence. Score/runtime semantics, ordinary initial tooltip placement, the timeline collision, and the original P4 guard defect are fixed.
- Inputs: approved `solo-ops-P5-rev1.md`, E-P5.md Revision 1, current index.html diff, parent contract and RV-P5 round-1 evidence. Same read-only rules: no repository modification/stage/commit, no cluster/SSH/kubectl/docker/gh, no service/forward interference. Only scratch port **8097** was used and it has been stopped.

## Commands and evidence

Repository: `/Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector`; test cwd: its `analyser/`.

```sh
git diff --stat
git diff -- analyser/dashboard_assets/index.html
git status --short
./.venv_test/bin/python -m pytest tests/integration/test_dashboard_overview.py tests/integration/test_dashboard_system_health.py tests/unit/test_static_bundle_contract.py -q
sh /tmp/solo-ops-p2/check_syntax.sh
env PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared /tmp/solo-p3-venv/bin/python -m pytest tests/unit/test_dashboard_api_routes.py tests/integration/test_canonical_route_contracts.py -q -p no:cacheprovider
python3 /tmp/solo-dash-dev/static_proxy.py --port 8097
```

Also executed through the existing `.venv_test/bin/python`:

- `/tmp/solo-ops-p5-rv/run_rev1_smoke.py`
- `/tmp/solo-ops-p5-rv/rev1_probe.py`
- `/tmp/solo-ops-p5-rv/rev1_dst.py`
- `/tmp/solo-ops-p5-rv/rev1_three_line_shot.py` (dedicated screenshot capture)

Programmatic source comparison used Python `difflib`, regexes, and read-only `git show HEAD:analyser/dashboard_assets/index.html` / `git diff --stat -- <protected paths>`. The direct real `dashboard_routes` helper command used `/tmp/solo-p3-venv/bin/python`, the shared PYTHONPATH, `_solo_analysis_state` and `_runtime_liveness_payload` on solo inventory status:error and status:warming.

### Results

| Check | Observed result |
| --- | --- |
| P5 scope | **index.html +243/−34** vs HEAD. Other tree entries are the declared user-owned AGENTS.md / untracked orchestration/report items. Protected backend/solo_mode/exporter/tests/vendor/deploy diff is empty. |
| Syntax | **SYNTAX_OK**, exit 0; one inline script. |
| Frontend/bundle pytest | **10 passed**, 7.02 s, exit 0. |
| Backend contract pytest | **80 passed, 1 failed**, 1.39 s, exit 1; only the known missing-mlflow environment failure in `test_build_bayesian_debug_payload_uses_shared_prediction_diagnostics`. |
| Independent copied E smoke | **162/162 passed**, 137.06 s, exit 0. |
| Independent full tooltip edge matrix | **128/128 placements passed**: 8 badges × 4 widths × top/bottom × hover/focus. |
| Independent time-axis geometry | **36/36 chart/case measurements passed** across 3 zones × 2 widths × (timeline + 3 solo time charts + external ISO + forced three-line external ticks). |
| Live pods | **10/10 healthy - raw / ok**, runtime running. |
| Independent main-page console | **0 pageerrors, 0 console errors** in RV probe. E copied full smoke: 1 previously established Plotly automargin race, 0 console errors, no new pageerror type. |

Never ran `tests/unit/test_solo_dashboard_routes.py`, a full test suite, a build, deploy, or live mutation.

Scratch JSON/text evidence: `/tmp/solo-ops-p5-rv/rev1-probe-results.json`, `rev1-dst.json`, `rev1-static.txt`. Full smoke output was observed as tool artifact `artifact://1518`; pytest output as `artifact://1512` plus the frontend result. Screenshots are in [`rv-p5-rev1-shots/`](rv-p5-rev1-shots/).

## 1. Probability and runtime-level re-review

### Probability fixtures — fixed

Independently called the actual page helper, not a reimplementation:

- `''`, `'  '`, `NaN`, `Infinity`, `-Infinity`, `[]`, `{}`, `true`, null and undefined → **degraded / warn**.
- `0` and `'0.0013'`, with raw label → **healthy - raw / ok**.
- A stale freshness fact with a valid raw score still stays healthy/raw, as explicitly required; no new freshness input was introduced.

Source: `index.html:1428–1437` accepts only finite numbers or nonblank numeric strings. The round-1 blank-score finding is closed.

### Actual runtime field and source agreement — fixed

E correctly uses **`current.runtime_status.state === 'not_running'`**, lowercased, in addition to `analysis_state === 'error'` (`index.html:1414–1426`). It also accepts the card's string-shaped fixture, but the real API field is an object.

Re-read `dashboard_routes.py:2512–2593,4383–4423`. `_runtime_liveness_payload` returns the source domain **running / not_running / unknown**; solo warming/scored inventory is running (`:2549–2561`), inventory error is not_running (`:2585–2592`), and `/live.current.runtime_status` emits that object (`:4398`). It does not emit state:error, so checking only not_running is the minimal appropriate runtime test.

Executed the real Python helpers:

- Solo inventory error → API analysis_state unknown, probability null, runtime object **state:not_running / reason:RUNTIME_STATUS_ERROR**.
- Solo inventory warming → API analysis_state unknown, probability null, runtime object **state:running / reason:SOLO_WARMING**.

Rendered those source-shaped cases in the actual page: error/no score → **error / badge critical**; not_running with a raw score → **error / critical**; warming/running with no score → **degraded / warn**; calm raw → **healthy - raw / badge ok**. Uppercase NOT_RUNNING also wins over a score. There was no unhealthy live pod available to select, and no live failure was injected: the failure-path proof is real producer-helper output plus page fixtures, not a claim of observing a broken deployed pod.

Fetched the actual identity-qualified `/api/dashboard/live/<family>/<pod>?namespace=…&cluster=…` payload of **each of the ten live pods** again, through 8097: all ten healthy/raw and runtime running.

### Guide wording

`index.html:1247–1249` now exactly says:

- Error: **“the pod reports an error, or its scoring runtime is not running, or its live data could not be fetched”**.
- Healthy raw includes **“the last published score … green means the last scoring path published a score, not that scoring is working right now — for freshness see Indicator B and Pipeline Status”**.

These agree with the API-error / runtime-not_running priority and the unchanged owning-fetch exception path. The score-vs-freshness distinction is now explicit. Eight badge tooltip strings remain unchanged and still match their Guide blocks verbatim. The round-1 runtime/wording finding is closed.

## 2. Tooltips — initial geometry fixed; dynamic limitations remain

### Independent full matrix, not E's narrower matrix

For each of the eight badges at **1440, 1200, 900 and 800 px**, RV placed it near the viewport top (**badge top y=70**) and bottom (**y=900 in a 1000 px viewport**), then separately hovered and keyboard-focused it. All **128** measurements had:

- visible, nonempty tooltip fully inside the viewport and nearest outer card, including vertical card containment;
- row scrollWidth exactly unchanged from its measured pre-show value;
- no measured movement of the observed-chart panel;
- no body overflow.

At top-of-viewport the first tooltip actually flips below; read `rev1-tip-0-900.png` and first/last images at 1440/900. These are the real edge cases absent from E's own scrolling helper (finding 2).

### Refresh and binding

At nonzero **pod-list.scrollTop=29 / window.scrollY=1450**, with the non-default memory metric, independently observed **three actual `/live` responses over 17 s**. Selection, both scroll values, eight tooltip identities/count and first math node stayed unchanged. Source has one setup call from DOMContentLoaded and one pointerenter/focusin installation per wrapper (`index.html:1372–1377`); no refresh binding path was introduced.

### Requested stress cases — what actually happened

| Case | Observed result / classification |
| --- | --- |
| Initially shown after page scroll | Full matrix passes; original above-viewport clipping is fixed. |
| Page scroll while keyboard-focused | Tooltip stays at **[940.36,371.75,1260.36,479.88]** while badge moves from y=487.88 to **−12.13**. It remains floating over the observed chart, disconnected from its owner. **Finding 1.** |
| Resize while focused: 1440×1000 → 800×500 | Tooltip keeps x=940.36–1260.36, wholly beyond the new right edge; it is outside both viewport/card. **Finding 1.** |
| Card put inside a scrolling wrapper, then scrolled | Popup remains at its old fixed coordinates while badge moves 160 px. This synthetic layout also demonstrates the lack of scroll re-anchoring. Current bundle does not otherwise nest this card in such a wrapper. |
| 150% visual zoom via CDP `Emulation.setPageScaleFactor` | Visual viewport becomes **960×666.67** CSS px, but helper still fits against innerWidth=1440. Tooltip x=940–1260 is mostly outside the visible area; screenshot shows clipping. **Finding 1 includes this visual-viewport bound issue.** |
| CSS body zoom:150% | Containment passes, but viewport-pixel coordinates assigned as zoomed CSS coordinates displace the popup so it overlaps its badge row. This is a synthetic CSS-zoom test, **not a claim of testing native desktop browser zoom**. Record as a coordinate-space limitation, not a separate blocker. |
| Ancestor `transform:translateZ(0)` | Fixed containing block becomes the ancestor; tooltip top **43.63** vs badge top **487.88**, visibly far from its badge. Current ancestor chain has no such transform; this is a synthetic unsupported-layout limitation, not a demand for a generalized portal architecture. |
| Very small viewport:800×150 | Tooltip fits, top **4**, bottom **129.75**, readable. It overlaps nearby content, but is not clipped. No claim for a viewport smaller than the tooltip itself. |

The first-entry geometry is now good. The remaining ordinary scroll/resize and visual-zoom problems arise because placement only runs on pointerenter/focusin, using layout-viewport coordinates. They do not call for backend changes or generalized hardening.

## 3. Time axes — original overlap fixed

Independent geometry in **Asia/Tokyo, America/New_York and UTC**, each at **900 and 1440 px**, checked the timeline and all three solo time-chart `.xtitle` rectangles against every `.xtick text` rectangle, also checking containment inside the chart box: all passed.

For each zone/width, called the real shared `renderTimeseries` with external ISO strings and checked again: **Time (UTC)**, no collision/clipped title. Forced an actual three-line SVG tick **“00:00 / Nov 7 / 2026”** through Plotly ticktext; all six zone/width cases passed. Read the dedicated three-line screenshot and the ordinary 900 px timeline screenshot: the date and title have visible separation. This closes the round-1 timeline finding.

Source fix is limited to shared timeline layout `index.html:2051–2068`: bottom margin 64 and title standoff 14. The three solo charts retain automargin:true. Date types and the numeric-local / ISO-UTC title selection are preserved.

Current timezone strings independently reconfirmed:

- Tokyo UTC+9; New York UTC−5; UTC+0; Calcutta UTC+5:30;
- Kathmandu resolves in Chromium to **Asia/Katmandu, UTC+5:45**;
- Lord Howe UTC+11 now; date fixture July UTC+10:30 / November UTC+11;
- St Johns date fixtures July UTC−2:30 / November UTC−3:30.

No source zone literal; helper still computes offset for now, not each point spanning a DST transition. The known limitation remains explicit, not silently “fixed.” Copied smoke reconfirmed ISO-versus-numeric rendering and timeline/pod-level clock alignment.

## 4. Smoke honesty, scope, and regressions

Copied current `/tmp/solo-ops-p5/smoke.py` to `/tmp/solo-ops-p5-rv/rev1-smoke.py`, changed **only BASE 8090→8097**, and checked exact source equality with that string reverted. Runner redirects screenshot paths at runtime to RV evidence without overwriting E/P4 images.

Diff against `/tmp/solo-ops-p4/smoke.py` confirms original **every-y-title** exact/≤2-word/`[]:=,` guards and both CDF/PDF x-title guards are restored (`smoke.py:335–349`). Only the three time x titles and Guide count are semantically relaxed as authorized. There is additionally the expected **strengthening** of banned-token checks; thus “only two deltas” means only two relaxations, not a literally two-hunk file diff. E corrected its former y/CDF guard claim. The original round-1 guard finding is closed, but the new edge-case smoke claims still overstate what is tested (finding 2).

Regression checks from the **162/162** own run and source comparison:

- one inline script; all 23 round-1 keep-list IDs exactly once;
- data-tex sequence byte-identical to HEAD, **28/28 rendered / 12 distinct / four panel formulas**;
- seven Guide pages, chain default, status not default, menu switching, all visible-page banned-token checks, exact tooltip repetition, both dormancy paragraphs;
- raw green; partial window neutral while mandatory ready; gate/published not amber merely for raw; genuine computable/drift signals preserved;
- marker on CDF, PDF left of CDF, 288-point timeline and matching counter, Baseline/Lineage gating;
- offline JS-only and all-KaTeX abort modes readable/nonempty, charts present, no page exceptions or overflow at both widths;
- owning/nonce/selection mechanisms, scoring/backend APIs, thresholds and static bundle dependencies unchanged;
- no new console error type versus round 1. Copied smoke has the same single established Plotly automargin race; independent RV probe has zero page/console errors. No need to rerun a HEAD proxy for an unchanged, already established baseline.

Visually read the revised Guide status page, ordinary and three-line timeline, true top-edge tooltip shots, all requested stress screenshots, and E-smoke first/last images. Normal contrast/readability and badge colors are good. The synthetic transformed/zoomed cases and the ordinary stale popup are visibly misplaced; containment alone is not proof of correct anchoring.

## Numbered findings

1. **should-fix — Fixed tooltip is not updated/hidden when its viewport or anchor changes.** `analyser/dashboard_assets/index.html:1337–1369,1372–1376` (CSS `:612–616`). Placement runs only on pointerenter/focusin. The reproducible resize moves the visible popup wholly outside an 800 px viewport; scrolling leaves a keyboard-focused popup floating 500 px away over another chart; 150% visual zoom clips it because innerWidth is the layout, not visible, viewport. These are independent measured cases and read screenshots, not speculation. **Concrete fix:** bind a single active-tooltip reposition/hide path to resize and relevant scrolling, keeping existing wrapper/node identity and bound-once behavior; recompute while its owner is visible or hide it when not. Use visualViewport bounds/events when present for visual zoom. No new API/service, catch-all exception suppression, or generalized layout abstraction is needed. Record CSS zoom/transformed-containing-block limits honestly unless S specifically wants them supported.

2. **should-fix — Smoke “top/bottom” tests still do not scroll to viewport edges, and do not establish all claimed containment/width properties.** `/tmp/solo-ops-p5/smoke.py:1619–1622,1628–1635,1667–1708`; E-P5.md Revision 1 acceptance/tooltip evidence. Its scroll formula places the badge at **vh/2−30** for top and **vh/2+30** for bottom: **470/530 px in a 1000 px viewport**, not near either viewport edge. Only first/last badges get those nominal edge cases. `inCard` checks only left/right, and the predicate checks overflow≤0 rather than comparing pre/post scrollWidth. RV's full true-edge matrix actually passes, so this is a remaining **acceptance-evidence defect**, not a failure of initial geometry. **Concrete fix:** use actual near-top/near-bottom target coordinates for all eight badges, test vertical as well as horizontal card bounds, snapshot row width before show and compare after; include resize/scroll/visual-viewport cases or explicitly narrow the claim. Correct the report/screenshots named “top” so they represent what was exercised.

## Disposition rationale

The substantive score/error corrections and timeline fix are independently established, P4 guards are restored, and the full ordinary tooltip matrix and P2/P4/P5 regression run pass. No backend change or live-observation disturbance was found. Acceptance remains **with findings**, not a clean gate: initial fixed positioning solved the original clipping but introduced observable lifecycle/coordinate limitations, and E's current edge-test labels still do not describe their actual target positions. S may decide whether the residual behavior is an accepted display limitation; RV has not changed implementation or unilaterally blocked the package. Proof remains local static assets plus read-only deployed payloads, not a deployed P5 image.
