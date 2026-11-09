# Solo dashboard status clarity, badge legend, and axis timezone — follow-up prompt (P5, LOW PRIORITY)

**Date:** 2026-11-07
**Status:** follow-up execution prompt for the Supervisor, injected by the operator.
Re-read after compaction.
**Priority: LOW.** Display/status-clarity workcard (P5) for the SOLO-OPS campaign.
It must NOT delay or interfere with P3 (calibration-mapper refit loop), which owns
the active 24 h observation window.

---

## Read these files first, in this order

1. `agent-orchestration/AGENTS.md` (standing rules).
2. `agent-orchestration/evidence/solo-mode-plans/solo-dashboard-operations-supervisor-prompt-2026-11-06.md` — the campaign loop, rollout loop, and hard stops still apply.
3. `agent-orchestration/evidence/solo-mode-plans/solo-dashboard-math-rendering-p4-prompt-2026-11-06.md` — the P4 workcard (KaTeX math rendering). **P5 and P4 are display-only and share the same file (`index.html`) and the same post-P3 rollout slot; coordinate so they are not duplicated and can ship in ONE image if convenient.**
4. `pipelineml-anomaly-detector/markdown/2026-11-06-solo-dashboard-operations-report.md` **Section 9** (the scoring chain + the two-norms explanation — the canonical text source for the new Guide content).
5. **THIS file.**

## Operator decision (baked in)

The operator finds the solo status surface confusing and wants it made accurate and
self-explanatory. Three concrete asks, all display/status-text (NO scoring, NO
threshold, NO new counting mechanism):

**(A) A more accurate 4-level "Analysis State"** — the current `analysis_state` maps
a raw/calibrating score to `"degraded"`, which the operator objects to: publishing the
raw probability because the window has no anomaly spread to calibrate against is a
**healthy, calm** condition, not a degraded one. The operator wants four levels that
separate "healthy" into two sub-cases:
   1. **healthy — recalibrated** (a proven calibrated mapper is active: `p_published`
      = mapper(`p_raw`), label `calibrated`);
   2. **healthy — raw** (scoring correctly, but no healthy calibrated mapper yet →
      `p_published = p_raw`, label `raw`; the "no anomaly-justified calibration yet"
      state);
   3. **degraded** (genuinely degraded: warming / no scored tick yet, or configured
      metrics not computable);
   4. **error** (runtime not running / error).
   R decides the exact `analysis_state` string values and how they propagate to the
   "Analysis State" badge and any consumers, **but the four-way distinction is the
   requirement**, and it must not mislabel the calm-raw state as degraded nor hide a
   real degradation. It must stay display/status-only: it changes a status string and
   its presentation, not what the detector scores.

**(B) A legend + clearer text for the "Solo diagnostics" badge wall.** The badges
currently give a value with little context and read as contradictory. For each badge:
keep the value, but (i) give it a clearer name where the current one is ambiguous, and
(ii) add an explanatory tooltip (the existing `.tooltip-container`/`.tooltip-text`
idom) that says in one or two plain-English lines **what it measures and what "good"
looks like**. The required content (grounded in source — see "Badge reference" below;
R may refine wording but must not contradict it):
   - **window** — fraction of the scoring window filled for the metrics; `ready` = all
     filled, `warming` = partial, `no data` = none. (It is about window fill, NOT
     about calibration.)
   - **mandatory** — whether the pod's mandatory metrics have produced a scored tick
     (model built + strike ring filled). `ready`/`warming`. It is a readiness fact,
     NOT a calibration fact.
   - **calibration** — the calibration machine state (`scored` = "the one-time warm-up
     gate has a mapper"; `calibrating`/`warming` = not yet). Explain that a pod can be
     `calibration: scored` while `probability: raw` simultaneously (P3): the pod is in
     the scored state but is currently publishing raw because no *healthy* mapper is
     active yet. This is the pair that reads as contradictory today — the tooltip must
     resolve it.
   - **probability** — `raw` vs `calibrated` (which value is being published).
   - **model age** — seconds since the reference model for this pod was last (re)built.
   - **drift** — a record-only soft flag: `stale` when a continuous metric's learned
     residual distribution has drifted past its distance threshold. It never blocks
     scoring; `n/a` = not flagged this tick. Explain "which drift" = the learned
     residual CDF vs the current data.
   - **degraded fraction** — a **unitless fraction (0–1)** of configured metrics that
     are fully computable this tick; **1.0 = all good (healthy)**, < 1.0 = some metric
     is not producing usable data. The number is a fraction, not a percentage, and it
     measures metric computability, not anomaly. (R MUST re-verify the exact
     direction/naming in `solo_mode/driver.py` + the payload — the field is named
     `degraded_fraction` but the payload comment says "1.0 = all computable" — and use
     the source-of-truth meaning, not the name.)
   - **Keff** — effective number of independent metric evidences (participation ratio),
     a diagnostics descriptor, not a gate.

**(C) An adaptive timezone label on the time axes.** The time charts already render in
the **browser's local time** (Plotly `type:'date'` over epoch-ms). The operator wants
the timezone made explicit on the x-axis, **adaptive to the viewer's region** (NOT a
hardcoded "JST"): compute it client-side (e.g. from `Intl.DateTimeFormat().resolvedOptions().timeZone`
and/or `new Date().getTimezoneOffset()`) and append it to the time-axis title, e.g.
"Time (Asia/Tokyo, UTC+9)" or "Time (UTC+9)". No hardcoding; it must track the
viewer's browser. Apply to all time axes the solo charts set (the pod-level, per-tick,
observed, and timeline charts).

**(D) Guide content for all of the above.** Add to the existing Guide tab (P4's menu
machinery) the material above: a "Reading the status" page (the 4-level analysis state
+ each badge, one short block each) and fold the "what calibration is, and why it can
be dormant under flat load" explanation into the scoring-chain / pod-level pages.
Use the operator's framing: calibration becomes meaningful when a window has genuine
spread to learn a mapping from; a perfectly calm window leaves it in the "publish raw,
no healthy mapper yet" (healthy-raw) state. Keep it accurate to source — do not
describe calibration as literally "removing outliers"; describe it as mapping the raw
posterior onto the healthy-reference exceedance scale so the 0.2/0.8 thresholds are
well-calibrated, and note the calm-raw state is the expected outcome under flat load.
Content traceable to report §9 + the "Badge reference" below; invent no new numbers.

## Sequence constraint (IMPORTANT — do NOT disturb P3's window)

- Same rule as P4: P5 code + local proof may proceed now, but **no P5 image build /
  rollout until P3's 24 h observation window is closed and promoted** (a restart would
  reset the window). P5 is display/status-only, so it **may share P4's post-P3 image
  and rollout** (one restart, both display batches) — the Supervisor's call; either way
  nothing ships before P3 closes. Keep P5's `index.html`/`dashboard_routes.py` changes
  uncommitted-or-branch-local until that slot, exactly as P4 did.
- Local pre-deploy proof uses the R-P2 §9 scratch proxy (`/tmp/solo-dash-dev/static_proxy.py`,
  port 8090; use a different port from P4's 8092 to avoid a clash) — never a cluster
  change.

## Badge reference (source anchors for R — keep the new text consistent with these)

All in `pipelineml-anomaly-detector/analyser/`:
- `index.html:949-957` — the eight badge elements; `index.html:2436` window,
  `:2440` mandatory, `:2451` calibration, `:2452` probability, `:2455-2456` model age,
  `:2458-2459` drift, `:2461-2482` degraded fraction, `:2484-2485` Keff.
- `index.html:2420-2436` — `window` derives from `payload.window_ready` (per-metric
  fraction; minReady/maxReady → no data / ready / warming / degraded).
- `solo_mode/diagnostics.py:721-735` — `mandatory_status` = `ready` if a scored tick
  with details exists else `warming` (model built + strike ring filled).
- `dashboard_routes.py:2110-2145` `_solo_analysis_state` — the current mapping:
  calibrated → `ready`; raw/calibrating → `degraded`; no published score → `unknown`.
  **This is the function (A) changes** (the raw case must become a distinct
  healthy-raw level, not `degraded`).
- `dashboard_routes.py:4055, 4303` — where `analysis_state` is emitted to list/current.
- Tooltip idom: `.tooltip-container`/`.tooltip-dot`/`.tooltip-text` (`index.html:550-595`).
- Axis titles: the solo chart call sites set `xaxis`/`yaxis` (P4 owns them); the
  timezone label is appended to the **time** axes' titles.

## Scope / hard limits (unchanged campaign invariants)

- Display/status-text + one status-string semantics change (A). NO scoring, NO
  calibration/strike/Simes/Markov law, NO thresholds, NO new counting mechanism, NO new
  security/ops surface.
- If (A) changes `analysis_state` values, R MUST enumerate every consumer
  (badge, pod-list, `/current`, `/live`, `/overview`, any `shared_selectors.js`
  mapping) and update them consistently, or keep the change display-local. Do NOT break
  the existing "raw is never `ready`" safety semantics in a way that hides a real
  problem — the point is to *label* it more accurately, not to make everything green.
- P4 keep-list intact (ids, 4 bundle files, legend, Maintenance card, Playwright-visible
  elements). P2 + P4 acceptance items still hold after P5 (marker on CDF, 288-point
  timeline + consistent counter, ≥ 3 refreshes selection/scroll stable, grayed
  Baseline/Lineage, Guide pages present, KaTeX formulas render). P5's smoke re-asserts
  them plus the new status/badge/axis checks.
- No new files beyond the bundle and the gate record.
- Gate record ≤ 200 lines: `agent-orchestration/evidence/solo-mode-gates/SOLO-OPS-P5.md`.
- Orchestration-repo commits still wait for the operator's "implementation end" signal.

## R open points (P5)

1. The four `analysis_state` string values + exact mapping (calibrated→healthy-recalibrated;
   raw-with-metrics-computable→healthy-raw; warming/no-scored-tick→degraded; not-running/
   error→error). Confirm the calm-raw case is the majority state under flat load and is
   labeled healthy-raw, and that a real `degraded` (metrics not computable / warming) is
   still distinguishable from it.
2. Whether the 4-level is a new `analysis_state` value set (touches consumers) or a
   presentation-layer re-label of the existing value — pick the smallest correct one.
3. The `degraded_fraction` direction/naming (verify against source; use source-of-truth).
4. The exact adaptive timezone string + whether to show IANA zone, UTC offset, or both.
5. Whether P5 ships in the same image as P4 (recommended: yes, one post-P3 restart).

## Acceptance (real browser, on the deployed image, at the P5/P4 rollout)

- "Analysis State" shows the correct level per pod on the flat load (expect
  **healthy — raw** for the 10 pods, NOT "degraded"); the four levels are reachable in
  code and the mapping is documented in the gate.
- Every solo badge has a tooltip explaining what it measures; the `calibration: scored`
  + `probability: raw` pair is explained (no longer reads as contradictory).
- `degraded fraction` tooltip states it is a 0–1 fraction of computable metrics, 1.0 =
  healthy.
- Time axes show an adaptive timezone label matching the viewer's browser (verify by
  reading the rendered title; it must not say a hardcoded zone).
- Guide "Reading the status" page present; scoring-chain/pod-level pages carry the
  calibration-dormancy-under-flat-load explanation; all text traceable to §9 + badge
  reference.
- All P2 + P4 acceptance re-asserted (see Hard limits). Local 8090-proxy proof before
  deploy; live proof after.
