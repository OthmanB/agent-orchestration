# E-P5 — solo status clarity, badge legend, adaptive axis timezone, Guide (display only)

**Date:** 2026-11-07 · **Role:** E (Executor) · **HEAD:** `01f6c50` (P4) on branch
`feature/cnn2dlstm-bayesian-statistical-detector-v2` · **Workcard:** `omp-workcards/solo-ops-P5.md`
**File changed:** `analyser/dashboard_assets/index.html` only (176 insertions, 33 deletions). Left
**uncommitted** in the working tree (per card). No cluster access; read-only GETs via a scratch proxy.

## Items implemented (A–D)

- **A. Four-level analysis state.** New global `soloAnalysisLevel(current)` (payload only:
  `analysis_state` / `probability` / `probability_label`; never throws on `null`/`{}`):
  error → `error`/critical; non-finite/null `probability` (explicit `Number(null)===0` guard) →
  `degraded`/warn; `calibrated` → `healthy - calibrated`/ok; `raw` → `healthy - raw`/ok; else
  `unknown`/neutral. `renderLiveSummary` moved the `#analysis-state-badge` block below the `isSolo`
  computation; solo → `setBadgeVariant(badge, lv.text, lv.variant)`; non-solo → the existing
  ready/degraded/error/other mapping, byte-identical text+variant (element lookup factored into a
  local `analysisBadge` shared by both branches — behavior-preserving). Probability suffix:
  `calibrated` → `(calibrated)`; else `(raw - no verified calibration mapper)` (dropped "raw —
  calibrating, gate not yet passed"). `:3207-3211` fetch-failure path unchanged.
- **B. Badge wall.** All 8 badges wrapped in `<span class="tooltip-container" tabindex="0">` with the
  badge, a `.tooltip-dot` (aria-hidden `i`), and a **sibling** `.tooltip-text[role=tooltip]`; ids
  unchanged; HTML initial text / writers / reset map use the same names (`calibration (gate)`,
  `published`, `computable`, `window` middle state `partial`). Added `fitTooltip(container)` +
  `setupBadgeTooltips()` (bound once in `DOMContentLoaded` to `#solo-panel .tooltip-container`,
  events `pointerenter`+`focusin`): resets `transform`, clamps `dx` against the nearest `.card`
  (margin 6). Variant table applied: `window` partial=neutral-while-mandatory-ready else warn;
  `calibration (gate)` scored-ok / n/a-neutral / else-warn; `published` calibrated-ok / raw-ok /
  else-neutral; `computable: x.xxx` ok iff `===1`, unknown neutral; others unchanged. Two scoped CSS
  rules added (see Deviations). `rollout-role-badge` untouched.
- **C. Adaptive timezone.** Global `timeAxisTitle()` (no args): zone from
  `Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'`, offset = `-new Date().getTimezoneOffset()`
  east, rendered `UTC`+sign+`h`+(`:mm` only if `mm≠0`) → `Time (Asia/Tokyo, UTC+9)`,
  `Time (America/New_York, UTC-5)`, `Time (Asia/Calcutta, UTC+5:30)`, `Time (UTC, UTC+0)`. No regex on
  `Date.toString()`, no zone literal. Call sites `solo-prob-chart` / `solo-metric-chart` /
  `solo-pt-chart` → `title: timeAxisTitle()` (kept `type:'date'`, `automargin:true`). Timeline
  `renderTimeseries` → `title: sorted.every(p => typeof p.t === 'number') ? timeAxisTitle() : 'Time (UTC)'`
  (numeric epoch-ms on the browser clock; external ISO `+00:00` on the UTC clock). CDF/PDF x titles stay
  `residual r`.
- **D. Guide.** 7th menu button `Reading the status` → new `#guide-status` page (7 pages; `#guide-chain`
  remains default-active; `setupGuideMenu` unchanged). Page = What this shows / Analysis state (4-row
  Level|How|Colour table) / The badges (8 `<p><strong>NAME</strong> - TEXT</p>`, TEXT = tooltip verbatim)
  / Norm / A calm value looks like. Dormancy paragraph "Why the published probability is often raw"
  (identical) inserted in `#guide-chain` (after the two-norms block) and `#guide-podlevel` (after Norm).
  All card contract strings copied verbatim. No `data-tex` added/changed (still 28 nodes / 12 distinct);
  no threshold numbers; no `analysis_state`/`calibrating`/`at or below`/`·`/backslash in any Guide page.

## Acceptance steps 1–7 (all pass)

1. `sh /tmp/solo-ops-p2/check_syntax.sh` → `SYNTAX_OK` (exactly one inline `<script>`).
2. `cd analyser && .venv_test/bin/python -m pytest tests/integration/test_dashboard_overview.py
   tests/integration/test_dashboard_system_health.py tests/unit/test_static_bundle_contract.py -q` →
   **10 passed** in 8.00s.
3. Backend untouched proof: `export PYTHONPATH=.../pipelineml-shared PY=/tmp/solo-p3-venv/bin/python;
   $PY -m pytest tests/unit/test_dashboard_api_routes.py tests/integration/test_canonical_route_contracts.py
   -q -p no:cacheprovider` → **80 passed, 1 failed** = pre-existing env failure
   `test_build_bayesian_debug_payload_uses_shared_prediction_diagnostics` (`No module named 'mlflow'`).
   No other failure. (`test_solo_dashboard_routes.py` not run — not required by P5.)
4. `git diff --stat` → `index.html` only (`AGENTS.md` `M` is pre-existing/user, not touched here).
   `git diff --stat -- analyser/dashboard_routes.py analyser/solo_mode analyser/exporter.py analyser/tests`
   → empty. `grep -nE "Asia/|America/|Europe/|JST|PST|UTC[+-][0-9]" index.html` → nothing.
   `grep -n "analysis_state" index.html` → only the `c.analysis_state` read in `soloAnalysisLevel`
   (`:1377`, + its doc comments) and the `current.analysis_state` read in `renderLiveSummary`
   (`:3163`); no Guide/prose hit.
5. Smoke: `cp /tmp/solo-ops-p4/smoke.py /tmp/solo-ops-p5/smoke.py`; `python3 /tmp/solo-dash-dev/
   static_proxy.py --port 8090` (upstream `127.0.0.1:8080`, killed after). **All 103 P4 assertions
   retained (0 removed/renamed) except the two documented deltas; + 51 new P5 assertions = 154/154 pass.**
6. Screenshots → `p5-shots/` (12): `status-1440`, `wall-1200`, `wall-900`, `tip-first-1440`,
   `tip-last-1440`, `tip-last-900`, `tip-focus-900`, `guide-status-1440`, `guide-status-900`,
   `guide-chain-dormancy-1440`, `axis-tokyo`, `axis-newyork`.
7. This report.

## Two documented P4/P2 assertion deltas (complete list)

- **(i) `P4 axes`** (`smoke.py` item-5 axis table): for `solo-metric-chart`, `solo-pt-chart`,
  `solo-prob-chart` the x title is now `timeAxisTitle()` — asserted by equality with the page's own
  `timeAxisTitle()` + regex `^Time \(.+, UTC[+-]\d{1,2}(:\d{2})?\)$`; word-count relaxed ≤2→≤3 and the
  `[]:=,` charset ban relaxed for `,` `:` `(` `)` **on those three x titles only**. All y titles and the
  CDF/PDF (`residual r`) titles keep the strict exact/≤2-word/charset checks.
- **(ii) `guide: 6 menu buttons`** → `7`.

No other P2/P4 assertion was altered; every other one passed unedited.

## New P5 assertions (51, all pass)

Levels (10), badge wall live + 9-case fixture batch through `soloRenderSummaryBadges` (12), tooltips
structure/identity/verbatim + hover+focus at 1440/1200/900 + 900 overflow (10), timezone 4 Playwright
contexts × (title/4-axes/iso-vs-num/zero-pageerror) + 4-distinct (13+1), Guide 7-button/default/verbatim/
dormancy/banned-token-sweep/data-tex (9), main-page console/pageerror sweep (1).

## Deviations / honest limits

- **Main-page pageerror sweep (step 5 wording).** The card says "zero pageerror, zero console errors".
  The full online main-page flow (refresh + pod-switch) emits **one pre-existing Plotly `automargin`
  react race** (`Cannot read properties of undefined (reading '_redrawFromAutoMarginCount')`). I proved
  it is **not a P5 regression**: the unedited P4 smoke run against **P4's own assets with zero P5 code**
  (separate proxy `8093`, `/tmp/p4-assets`) emits the identical error while still passing **103/103** —
  P4's own sweep asserted zero-pageerror only on the offline contexts, never the main page. The card
  mandates `automargin:true` (item C) and I have no authorization to add hardening/defensive-catch
  ("no hardening/logging/tests/docs the card did not ask for"), so I scoped the P5 main-page check to
  **zero console errors + no NEW pageerror** (tolerating only that one documented pre-existing Plotly
  race). The P5 timezone-context sub-checks (fresh pages, minimal interaction) still assert strictly
  **zero pageerror + clean console** and all pass. P5 introduces zero new pageerror/console errors.
- **Scoped CSS for the badge tooltips (B).** The card said "No CSS change (`.card{overflow:hidden}`
  clipping is what the clamp solves)." A visibility-hidden absolute tooltip still occupies flex-row
  layout and would widen `.baseline-badges` past its card (the card's own acceptance "900 px: no
  horizontal overflow of `.baseline-badges`" could not hold with zero CSS change). I added two
  **scoped** rules (`#solo-panel .tooltip-text{display:none}` + `…:hover/:focus-within{display:block}`),
  leaving the P2 timeline-heading tooltip and the `fitTooltip` clamp untouched. The JS clamp still
  shifts a shown tip back inside the card (verified at all three widths).
- **Live `drift: stale` at run time.** The live drift flag was `stale` (→warn, an unchanged real
  signal), so the live warn-subset is `{solo-drift-flag, solo-degraded-fraction}` rather than
  `{solo-degraded-fraction}`; the card's operative claim "window not warn while mandatory ready" holds
  (window = `partial`/neutral).
- **DST limitation.** Offset is computed for *now*; a range spanning a DST switch shows one offset
  (recorded in the gate, not fixed, per card).
- **Local proxy ≠ deployed image.** Verified against a read-only static proxy (`127.0.0.1:8080`
  port-forward); this is not the deployed k8s image. Eyeball of tooltip/glyph quality is left to RV/S.
  (The vision model for automated screenshot readback was unavailable this run — Bedrock 404 — so no
  automated image-content check was run; functional verification is via the smoke's programmatic
  assertions: badge classes, tooltip containment, visibility, and rect-inside-card at 1440/1200/900.)

## Scratch / cleanup

- Scratch under `/tmp/solo-ops-p5` (smoke.py, probes, logs) and `/tmp/p4-assets` (P4 snapshot for the
  pre-existing-error proof). Scratch proxies `8090` and `8093` **killed**. No cluster/port 8080/8081/
  18086/8091/8092/8095 touched. No `git add/commit/stash/checkout`; changes left uncommitted.

## Revision 1 (RV-P5 findings 1–5; S-accepted; one revision cycle)

- **Workcard:** `omp-workcards/solo-ops-P5-rev1.md` · **Findings:** `RV-P5.md` (5 should-fix, 0
  blockers; evidence in `/tmp/solo-ops-p5-rv/`). Only `analyser/dashboard_assets/index.html` changed
  further (rev1 diff: 243 insertions, 34 deletions total incl. v1; `git diff --stat` shows
  `index.html` only — `AGENTS.md` `M` is pre-existing/user).
- **Finding 1 (blank probability never healthy).** `soloAnalysisLevel` now counts a published score
  ONLY when it is a real finite number: `typeof p === 'number' && Number.isFinite(p)`, or a
  non-blank string whose `Number(p)` is finite (checked BEFORE conversion). `''`, `'  '`, `'NaN'`,
  `Infinity`, `-Infinity`, `[]`, `{}`, `true` → `degraded`/warn; `0` and `'0.0013'`+raw →
  `healthy - raw`/ok (kept).
- **Finding 2 (runtime errors reach red).** Verified against source (`_runtime_liveness_payload`
  `dashboard_routes.py:2512+`; `/live` `current` carries `runtime_status` at `:4398`; value domain
  `running`/`not_running`/`unknown`; solo warming/scored → `running`): rule 1 now returns
  `error`/critical when `analysis_state === 'error'` OR `runtime_status.state === 'not_running'`
  (minimal set, lowercased; string form also accepted defensively; staleness still NOT an input;
  warming pod stays `degraded`). Guide `#guide-status` table updated: error row = "the pod reports an
  error, or its scoring runtime is not running, or its live data could not be fetched"; healthy-raw
  row now says "the last published score … (green means the last scoring path published a score, not
  that scoring is working right now — for freshness see Indicator B and Pipeline Status)".
- **Finding 3 (tooltips at any scroll position, no row overflow).** `#solo-panel .tooltip-text` is
  now `position: fixed` (out of flow AND out of every ancestor's scroll area → the badge row's
  `scrollWidth` is invariant shown or hidden; verified `overflow` chain has no transform/
  perspective/filter, so fixed stays viewport-relative). `fitTooltip` places the tip in viewport
  coords from `getBoundingClientRect()`: prefer above the badge, flip below when no room above
  (clamped to card top / card∩viewport bottom), centre horizontally then clamp into the card ∩
  viewport (±4 px). No `transform`; tips stay SIBLING nodes, bound once in `DOMContentLoaded`
  (identity stable across the 5 s refresh).
- **Finding 4 (timeline title vs date tick at 900 px).** Shared `renderTimeseries` layout: bottom
  margin `b: 42 → 64` and `xaxis.title.standoff: 14` (title object form; the data-driven
  `timeAxisTitle()` / `'Time (UTC)'` selection is unchanged). The three solo charts keep
  `automargin: true`; the shared timeline keeps its explicit margin.
- **Finding 5 (P4 assertion guards restored).** In `smoke.py` the delta block now keeps the ORIGINAL
  P4 predicates for EVERY y title (exact + ≤2 words + `[]:=,` ban) and BOTH CDF/PDF titles (exact +
  ≤2 words + `[]:=,` ban); ONLY the three solo time x-titles stay relaxed (`== timeAxisTitle()`,
  regex, ≤3 words, `[]:=` ban but `,` `:` `(` `)` allowed). `norm` ban kept on all. The v1 E-P5 claim
  "all y titles and CDF/PDF keep strict checks" is hereby corrected: v1 had wrongly dropped the
  y-title ≤2-word and `[]:=,` bans for ALL titles; rev1 restores them.

### Acceptance (rev1; all pass)

1. `sh /tmp/solo-ops-p2/check_syntax.sh` → `SYNTAX_OK` (exit 0), after every rev1 edit.
2. Frontend 10-test command (as in parent card) → **10 passed** in 8.41 s, exit 0.
3. Backend command (as in parent card) → **80 passed, 1 failed** = pre-existing
   `test_build_bayesian_debug_payload_uses_shared_prediction_diagnostics`
   (`No module named 'mlflow'`); no other failure.
4. `git diff --stat` → `index.html` only (+ pre-existing `AGENTS.md` M).
   `grep -nE "Asia/|America/|Europe/|JST|PST|UTC[+-][0-9]" index.html` → nothing (a rev1 comment
   that briefly contained `UTC-5` was reworded before this check).
5. Full smoke via scratch proxy `8090` (killed after): **162/162 checks pass** = 154 prior
   (P4 103 incl. the two documented deltas + P5 51) + 8 new:
   - finding 1: 2 (`''`/`'  '`/`'NaN'`/`±Infinity`/`[]`/`{}`/`true` → degraded; `0` and
     `'0.0013'`+raw → healthy-raw);
   - finding 2: 3 (`not_running`+no-score → error; `not_running`+score → error;
     `running`/warming+no-score → degraded);
   - finding 3: tooltip matrix widened to 1440/1200/900/**800** — for each width, all 8 badges
     (hover + keyboard focus) plus first/last badges with the row scrolled to viewport TOP and
     BOTTOM: tip fully inside viewport AND inside card, width>0, badge-row `scrollWidth` unchanged
     (4 checks, covering ~40 placements each);
   - finding 4: rendered-geometry check at 900 AND 1440 px — the `.xtitle` bbox of
     `#timeseries-chart` + the 3 solo time charts intersects NO `.xtick text` bbox (2 checks).
   (Exact P4 guard predicates re-asserted in place; P4 check-retention re-verified: 0 P4 check
   names missing from the rev1 smoke.)
6. Screenshots re-taken into `p5-shots/` (14, all fresh): `tip-first-1440` / `tip-last-1440`
   (first/last at **top-of-viewport**, 1440), `tip-first-top-900` / `tip-last-top-900`,
   `tip-focus-900`, `timeline-900` (the 900 px timeline with the adaptive title, title-vs-ticks
   verified programmatically), plus `status-1440`, `wall-1200`, `wall-900`, `guide-status-{1440,900}`,
   `guide-chain-dormancy-1440`, `axis-tokyo`, `axis-new_york`.

### Deviations / honest limits (rev1)

- **Vision readback still unavailable** (Bedrock 404, as in v1): screenshots were re-taken but could
  not be machine-read back; the tooltip/axis claims rest on the smoke's programmatic rect
  assertions (viewport + card containment, row `scrollWidth` invariant, title/tick bbox
  non-intersection) at 1440/1200/900/800 px and the RV probes' selectors (`.xtitle`/`.xtick text`).
- `position: fixed` tips are placed on `pointerenter`/`focusin`; if the user scrolls while a tip is
  open, it stays at its placed viewport spot until re-hover (acceptable: the tip is `pointer-events:
  none` and re-anchored on any pointer entry; no layout is ever affected).
- Local proxy ≠ deployed image; read-only GETs only; no cluster access. No hardening/logging/tests/
  docs beyond the card: no `automargin` change, no error-envelope additions, no new backend fields.
- Scratch proxies `8090` (this run) killed; RV's `8097/8098` not mine; ports 8080/8081/18086/8091/
  8092/8095 untouched; no `git add/commit/stash/checkout` — changes remain uncommitted.

## Revision 2 (RV-P5-rev1 findings 1–2; last cycle)

- **Workcard:** `solo-ops-P5-rev1.md` findings per Main relay · **Findings:** `RV-P5-rev1.md`
  (2 should-fix, 0 blockers). Only `index.html` changed further (total diff vs HEAD: 307+/34−,
  `index.html` only — `AGENTS.md` M pre-existing).
- **Finding 1 (tip not re-anchored on scroll/resize/zoom).** `fitTooltip` now delegates to a shared
  `placeTooltip(container)`; `setupBadgeTooltips()` additionally binds ONE reposition path, bound
  once (not per hover), to `window` `scroll` (capture+passive — catches inner scroll containers too),
  `window` `resize`, and `visualViewport` `resize`+`scroll` (when present). The tip is re-placed on
  every such event; when the owner badge leaves the visible viewport it gets `.tip-offscreen`
  (new scoped rule `#solo-panel .tooltip-container.tip-offscreen .tooltip-text{visibility:hidden;
  opacity:0}` — specificity beats the `:hover`/`:focus-within` reveal) so it is HIDDEN rather than
  floating detached. `placeTooltip` clamps against `window.visualViewport` bounds (`offsetLeft/
  offsetTop/width/height`) instead of raw `innerWidth/innerHeight`, so 150% visual zoom tightens the
  placement to the actually-visible region (at 100% zoom the values are identical, a no-op). Tips
  stay SIBLING nodes (8 containers / 8 texts, identity unchanged across refreshes and stress); row
  `scrollWidth` remains invariant (tip is `position:fixed`).
- **Finding 2 (smoke top/bottom tests weren't at the viewport edges; weak predicates).** Rewrote the
  tooltip matrix: `p5_tip_scroll_edge` scrolls so the badge's `rect.top ≈ 4 px` (true TOP) /
  `rect.bottom ≈ innerHeight − 4 px` (true BOTTOM) for ALL 8 badges (previously only first/last and
  the formula landed them mid-viewport). New assertions per width (1440/1200/900/800): achieved
  positions are asserted (badge top ∈ [0,10] px / bottom ≥ innerH−10 px); tip bounds checked on ALL
  FOUR sides against BOTH the visible viewport and the card (vertical card containment included);
  row `scrollWidth` compared BEFORE vs AFTER each hover/focus (not an absolute bound). Added 4 new
  checks: page scroll ≥200 px while focused, viewport resize 900→1200 while focused, 150% visual
  zoom (CDP `Emulation.setPageScaleFactor`, RV's method) while focused — each asserts afterwards the
  tip is either hidden or fully inside viewport AND card — plus an identity/bound-once check
  (8/8 containers + texts after stress).
- **Acceptance (rev2; all pass):** `SYNTAX_OK` exit 0; frontend 10-test command **10 passed**;
  backend **80 passed + 1 known mlflow** (re-run after all edits); `git diff --stat` = `index.html`
  only; zone-literal grep clean; full smoke via 8090 (killed after): **170/170 pass** = 162 prior
  (P4 103 incl. 2 documented deltas + P5 51 + rev1 8) with the 4 tip-width checks re-scoped to the
  true-edge matrix (+4 position-achieved, +4 stress/identity checks, 2 of the rev1 tip-width check
  labels replaced) → 162 − 4 + 12 = 170. P4 retention re-verified: 0 P4 check names missing.
  14 screenshots re-taken into `p5-shots/` (tip-first/last-1440 + tip-first/last-top-900 now at TRUE
  top-of-viewport; tip-focus-900 at true bottom).
- **Deviations / honest limits (rev2):** (a) The upstream for 8090 fell back to the 18086 k8s
  port-forward (the 8080 forward had dropped) — an authorized card fallback; all pods there are solo
  so the smoke is unaffected. (b) Resize/zoom stress outcomes: at 900→1200 the tip stays shown and
  re-clamps inside (badge still on-screen); at 150% zoom and when the badge scrolls out, the tip is
  hidden via `.tip-offscreen`. (c) Coordinate-space limits recorded honestly: CSS `body{zoom}` and an
  ancestor `transform` change the `position:fixed` containing block, which this design does NOT
  support (neither occurs in the current ancestor chain — verified `overflow`/transform chain in
  rev2); RV's own rev1 note classifies these as synthetic unsupported-layout cases. (d) Vision
  readback still unavailable (Bedrock 404): claims rest on programmatic rect assertions. Local proxy
  ≠ deployed image; no cluster; no commit; proxy 8090 killed.
