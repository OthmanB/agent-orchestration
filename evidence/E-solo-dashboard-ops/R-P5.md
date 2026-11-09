# R-P5 — status clarity, badge legend, axis timezone, Guide content (research)

**Date:** 2026-11-07 · **Role:** R (read-only) · **HEAD:** `01f6c50` (P4, local-only) on `20588af`
**Method:** source reads at HEAD, offline Python over cached live payloads, live read-only GETs via
`127.0.0.1:18086`, real Chromium (Playwright, `.venv_test`) against a scratch copy of `dashboard_assets`
on my own port 8095 (killed; `18086` forward untouched). Facts tagged `[SOURCE file:line]`, `[LIVE]`,
`[INFER]`.

## 0. Contradictions / corrections to the P5 brief (read first)

1. **`degraded_fraction` direction — brief is RIGHT, the field NAME is inverted.** `[SOURCE analyser/solo_mode/driver.py:1601-1605]`
   `fraction = sum(1 for m in metrics_out.values() if m['p'] is not None) / len(metrics_out)` with the
   comment `# Degraded fraction (computable / expected) … 1.0 = all computable, 0.0 = none computable`.
   So 1.0 = healthy (all configured metrics computable); 0.0 = nothing computable. Badge text must state
   "share computable, 1.0 = healthy", never "fraction degraded".
2. **`calibration: scored` + `probability: raw` is not a bug — it is the current steady state on all 10 pods.**
   `calibration_state` = the static gate (`scored`), `probability_label` = per-tick mapper validity `[SOURCE driver.py:1822-1827]`.
   Live: on every one of 288 ticks/pod `calibration_state == 'scored'`, while ticks 210–287 carry
   `probability_label == 'raw'` `[LIVE /tmp/p5_hist.json]`. The P3 degeneracy guard demoted the mapper at
   `2026-11-06T16:00:00Z` (all 10 pods, same epoch `1793980800`) and it has stayed raw 6.4 h since.
3. **`window: warming` on all 10 healthy pods is a MISLABEL.** `window_ready` = 0.979 (fraction of filled
   window bins) with 288 scored ticks present `[LIVE]`. Level mapping MUST NOT use `window_ready`
   `[INFER from LIVE + SOURCE diagnostics.py:220-232 — window_ready counts filled bins, not scoring health]`.
4. **Badge tooltips do not exist at HEAD.** P5 brief calls them verification; they are P5 work — the badge
   row is 8 plain `<span class="badge">` at `[SOURCE dashboard_assets/index.html:949-957]`; `.tooltip-container`
   CSS exists (550-595) but is used nowhere in the solo row. P4's card lists tooltips as deferred.
5. **Line numbers in the brief predate P4.** Verified anchors at HEAD: `_solo_analysis_state` 2108,
   `/current` 3033, `/overview` 3730, `/pods` list 3795-3810, snapshot-error guard 3778, `renderLiveSummary`
   3022, badge block 2436-2462, `setBadgeVariant` 1249, `renderTimeseries` 1714, `soloRenderChart` 2244.
6. **P4 bans the word `calibrating` in the pod-level Guide prose** `[SOURCE /tmp/solo-ops-p4/smoke.py:1044]`;
   new Guide text must avoid it there (use "dormant/degenerate").

## 1. `analysis_state` inventory and the four-level decision

Producer (single, solo-only):
`[SOURCE dashboard_routes.py:2108-2125]` `_solo_analysis_state(entry)` → `'error'` if the snapshot entry has
`error_message`; else `'degraded'` if `calibration_state != 'scored'`; else `'ready'`; `'unknown'` if no entry.

| Site | value domain | under option (i) new values | under option (ii) display-local |
|---|---|---|---|
| `dashboard_routes.py:2108` `_solo_analysis_state` | ready/degraded/error/unknown | 4 new strings | unchanged |
| `:3033` `/current` detail `analysis_state` | same | new strings | unchanged |
| `:3730` `/overview` summary | same | new strings | unchanged |
| `:3795-3810` `/pods` rows | same | new strings | unchanged |
| `:4295-4307` inventory rows | `'unknown'` (no solo path) | unchanged | unchanged |
| `:4366-4367` None-guard | passthrough | unchanged | unchanged |
| external pods (`snapshot_entry.analysis_state`, `core_orchestration.py:119`) | plugin domain (`alternate_active`/`failsafe_active`, `unknown`) | MUST stay untouched | untouched by construction |
| `dashboard_assets/index.html:3022-3034` `renderLiveSummary` badge (`#analysis-state-badge`) | maps 4 values → ok/warn/critical/neutral | relabel only | badge derives new level |
| `shared_selectors.js` | **does not read `analysis_state` at all** (only `runtime_state`/`status`, 562-580) | — | — |
| `index.html:3026` `analysisStateLabel` | 4-value map | new keys | unchanged |
| tests `test_dashboard_api_routes.py` (65/67/90/100/142-170/233-262) | pin `'unknown'` (external) and `'degraded'` (raw solo) | must be re-derived | pins keep passing |

**Decision: option (ii) — keep `analysis_state`, derive the level client-side.** Rationale, in order:
(a) the solo `analysis_state` is produced in ONE function and consumed in ONE place (`renderLiveSummary`),
so server-side reachability buys nothing; (b) option (i) changes both the `/solo` payload (`/current` +
`/overview` + `/pods`) and every pinning test, and risks external consumers of the plugin field
(`/solo` payload parity with `/api/dashboard` is untested elsewhere); (c) the JSON key name `analysis_state`
is shared with the external path, so new solo-only strings would make one key carry two vocabularies.
The cost of (ii) is one JS helper (`soloAnalysisLevel(payload)` ~15 lines) plus the badge mapping.

**Four-level value set (proposal, exact strings).** Names chosen so `ready` never appears for raw (§safety)
and no `·`/underscore:

| level | display | variant | derivation (payload facts only) |
|---|---|---|---|
| `healthy-calibrated` | `healthy - calibrated` | ok | `tick.details.probability_label === 'calibrated'` |
| `healthy-raw` | `healthy - raw` | warn | `probability_label === 'raw'` **and** mapper-healthy precondition absent, fraction OK |
| `degraded` | `degraded` | warn | `degraded_fraction` finite and `< MANDATORY_MIN` (see §2) |
| `error` | `error` | critical | `pod.error_message` / `inventory.error_message` / `!fresh` / no `tick` |

Order: error ≻ degraded ≻ healthy-calibrated / healthy-raw. `unknown` kept only for "no payload".
`mapper_healthy` is **not** exposed in any payload `[SOURCE: grep shows only driver-internal use]`, so the
discriminator for healthy-raw is simply `probability_label === 'raw'` with scoring otherwise healthy.
**Reachability at HEAD:** healthy-calibrated ✔ (ticks 0-209, i.e. before 16:00Z), healthy-raw ✔ (current),
degraded ✔ (any tick with fraction <1 under the mandatory rule), **error ✘ for solo pods** — no code sets
`error_message`/non-fresh on a live solo pod today; it becomes reachable only via the freshness/`no tick`
fallback I propose (`solo errors` are emitted by the exporter as `error` level strings, out of scope).
Safety: raw is never shown as plain `ready`; a real problem still shows `degraded`/`error` red/orange.

## 2. Flat-load reality check `[LIVE]`

10 pods × 288 ticks (`/solo` history, 5 min cadence, 2026-11-05T22:25Z → 2026-11-06T22:25Z):

| ingredient | live value (all 10 pods) |
|---|---|
| `probability_label` (current) | `raw` ×10; over history 2100 `calibrated` / 780 `raw` = 210/78 per pod |
| raw run | contiguous tail, ticks 210-287, 16:00:00Z → 22:25:00Z (6.42 h), identical start epoch `1793980800` |
| `calibration_state` | `scored` on 288/288 ticks |
| `degraded_fraction` | `==1.0` on 2102/2880 pod-ticks (73.0%); `<1.0` on 778 (27.0%); per pod 72-98 ticks (25-34%) |
| fraction <1 causes | 9/11 network counters `"block not aligned"` (uncomputable) + occasional `container_memory_working_set_bytes` uncomputable; **`container_cpu_usage_seconds_total` never uncomputable** |
| `mandatory_status` | `ready` ×10 (cpu + memory of the mandatory pair computable every tick) |
| `window_ready` | 0.979 → badge `window: warming` (mislabel, §0.3) |
| `model_age_seconds` | 600 |
| `drift_stale` | n/a |
| `k_eff` | 2.658 |
| `analysis_state` today | `degraded` ×10 |

**Consequence:** the literal rule "degraded = configured metrics not computable" makes all 10 calm pods
`degraded` on ~27 % of ticks (778/2880) for structural reasons (network counters are uncomputable under
this deployment's counter alignment). Acceptance "healthy - raw, NOT degraded" then fails on those ticks.
**Minimal rule that stays truthful:** degrade only on the MANDATORY set — `mandatory_metrics` =
`container_cpu_usage_seconds_total` (+`container_memory_working_set_bytes`) `[SOURCE diagnostics.py:723, 726]`.
Per-tick rule: `degraded` iff any mandatory metric is uncomputable (`details.ignored_metrics` contains a
mandatory name, or its per-metric entry has `p: None`); non-mandatory shortfalls stay INFORMATIONAL (the
`degraded fraction` badge + tooltip already say "informational network counters often fail to align").
This keeps the fraction visible as a number while the level stays `healthy - raw`.
`[INFER]` under this rule the current live level is `healthy - raw` ×10 and `degraded` becomes reachable only
on a real mandatory loss (verifiable by test fixture, not reachable live today).
**Operator-decision point O1:** mandatory-only rule (recommended) vs literal all-configured rule (labels
calm pods degraded 27 % of the time) vs sustained rule (N consecutive ticks) — I recommend mandatory-only;
it needs no new counter and no threshold.

## 3. Badge reference verification (B)

Row markup `[SOURCE index.html:949-957]`, writers `[SOURCE 2436-2462]`, reset map `[SOURCE 2930-2960]`.

| badge (id) | label at HEAD (live) | JS | payload field | derivation in source | verified meaning / "good" |
|---|---|---|---|---|---|
| `solo-window-badge` | `window: warming` | 2426-2436 | `window_ready` | `diagnostics.py:220-232` filled-bin fraction | `[SOURCE]` right, `[LIVE]` misleading: 0.979 ≠ not-ready; **drop from the level logic**, keep as info |
| `solo-mandatory-badge` | `mandatory: ready` | 2438-2440 | `mandatory_status.status` | `diagnostics.py:723-730` = a scored tick whose mandatory metrics are all computable | prompt statement CONFIRMED; add "cpu+memory" to tooltip |
| `solo-calibration-state` | `calibration: scored` | 2451 | `details.calibration_state` | static gate, `driver.py:1760-1770` | "gate open", NOT "mapper valid" |
| `solo-prob-label` | `probability: raw` | 2452 | `details.probability_label` | `driver.py:1822` mapper-verified | "published uses raw posterior"; pair explanation required |
| `solo-model-age` | `model age: 600s` | 2454-2456 | `details.model_age_seconds` | `diagnostics.py:338` `tick_epoch - m0` | seconds since reference model rebuild at the tick — CONFIRMED (older-badge semantics = "age of the model in use", not build age of newest) |
| `solo-drift-flag` | `drift: n/a` | 2458-2459 | `details.drift_stale` | `scan.py:57-70` split-half Wasserstein vs `t_cl`; record-only `[SOURCE driver.py:1641]` | CONFIRMED: soft flag, never blocks scoring; shows stale/n-a only (no live drift on flat load) |
| `solo-degraded-fraction` | `degraded: 1.000 (healthy)` | 2462-2480 | `details.degraded_fraction` | `driver.py:1601-1605` computable/expected | direction confirmed; **rename display to `computable: 1.000`** or keep label + tooltip "1.0 = all computable" |
| `solo-keff` | `Keff: 2.658` | 2482-2490 | `details.k_eff` | `fusion.py` participation ratio of residual correlation matrix (1..K) | CONFIRMED "participation ratio", good = near K (independent metrics) |

**Final badge names (proposal):** `window` keep · `mandatory` keep · `calibration` → `calibration (gate)` ·
`probability` → `published` · `model age` keep · `drift` keep · `degraded` → `computable` (0-1, 1.0 healthy) ·
`Keff` keep. Tooltip text (1-2 lines each, plain English) prototyped verbatim in the scratch copy; e.g.
`computable`: "Share of the configured metrics that were computable at this tick, 0-1. 1.0 = all computable
(healthy). Informational network counters often fail to align."

**Tooltip implementation (verified, 3 widths).** `setBadgeVariant` rewrites `textContent` + `className`
`[SOURCE 1249-1256]` every 5 s, so the tooltip MUST be a SIBLING inside a wrapper, never a child:
`<span class="tooltip-container"><span id="…" class="badge">…</span><i class="tooltip-dot"></i><span class="tooltip-text">…</span></span>`.
Measured at HEAD: `.tooltip-container{position:relative;display:inline-flex}` and `.card{overflow:hidden}`
`[SOURCE index.html:142-148, 550-595]` ⇒ the 320 px tooltip is **clipped at the card boundary for the last
badges** (1440: `keff` tip right 1416 > card 1366). CSS-only fixes fail because the row wraps at 1200/900
(a right-anchored tooltip then overflows left to x=-166). Working fix (prototype, ~15 lines, display-only):
a `fitTooltip(container)` called on `pointerenter`/`focusin` that resets `transform` then shifts the text
left/right to stay inside `container.closest('.card').getBoundingClientRect()` (±4 px). Measured after fix:
**clipped/empty = NONE at 1440, 1200 and 900 px** (8/8 badges each), keyboard `focusin` included; screenshots
`/tmp/solo-ops-p5/g-{1440,1200,900}-{first,keff}.png`. No native `title` fallback needed.

## 4. Adaptive timezone label (C)

Verified in real Chromium with Playwright `timezone_id` contexts `UTC`, `Asia/Tokyo`, `America/New_York`,
`Asia/Calcutta` `[LIVE /tmp/solo-ops-p5/probe.json]`, Plotly 2.27, HEAD assets:
- epoch-ms input → axis renders on the **browser local clock** (Tokyo shows `13:20 11/22` for a
  `2026-11-22T04:20Z` sample tick; `America/New_York` shows `-1 h` vs UTC).
- ISO-UTC strings (external path) → rendered on the **base/UTC clock** regardless of context.
- So solo charts (numeric ms) are TRUE only with the viewer's zone; external ISO path is UTC; the solo
  timeline is also ms → local. One label cannot be true for both paths.
**Change shape (one helper, three call sites):**
```js
function timeAxisTitle() {                    // ~10 lines, top of the script
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  const m = /(?:GMT|UTC)([+-])(\d{1,2})(?::?(\d{2}))?/.exec(new Date().toString()) || [];
  const off = m.length ? `${m[1]}${Number(m[2])}${m[3] && m[3] !== '00' ? ':' + m[3] : ''}` : '+0';
  return `Time (${zone}, UTC${off})`;
}
```
Offset is computed for **now** (the newest rendered point), not per point: a range spanning a DST switch shows
one offset — state the limitation, do not fix it. Measured strings: `Time (Asia/Tokyo, UTC+9)`,
`Time (America/New_York, UTC-5)`, `Time (Asia/Calcutta, UTC+5:30)`, `Time (UTC, UTC+0)`.
Call sites: `soloRenderChart` shallow-merges `{...axisLayout}` `[SOURCE 2244-2270]`, so the title set per
chart call (2644-2830) is the only change — replace literal `'Time'` with `timeAxisTitle()` on the three solo
time charts; keep `automargin: true`.
**Timeline decision (D-C):** `renderTimeseries` `[SOURCE 1714-1780]` is shared ⇒
`xaxis.title.text = solo ? timeAxisTitle() : 'Time (UTC)'`, using the same branch that selects the data source.
Length at 900 px: one line, 173 px in the measured shot, no overflow; stress
`Time (America/Argentina/ComodRivadavia, UTC-3)` ≈ 320 px still inside the ~800 px plot area.
**P5 intentionally changes these P4 smoke assertions** `[SOURCE /tmp/solo-ops-p4/smoke.py:309-333]`: for
`solo-metric-chart`, `solo-pt-chart`, `solo-prob-chart` the exact x-title table becomes (i) regex
`^Time \(.+,\sUTC[+-]\d{1,2}(:\d{2})?\)$`, (ii) equality with the page's own `timeAxisTitle()`, (iii) word-count
`<= 2` relaxed to `<= 3` for those x titles only, (iv) the `[]:=,` charset ban relaxed for `,` and `:` there.
Y titles and the CDF/PDF charts keep the strict checks. Add: `#timeseries-chart` = `Time (UTC)` external,
`timeAxisTitle()` in solo.

## 5. Guide content (D)

Structure at HEAD `[SOURCE index.html:1113-1230]`: `.guide-layout` → `nav.guide-menu` (6 `button[data-guide]`)
→ 6 `.guide-page` (`#guide-chain` active), each `.card` with `h3` What this shows / Norm / A calm value looks
like; formulas are `<span class="formula-line" data-tex="…">rendered</span><span class="formula-gloss">…</span>`.
Banned-token contract `[SOURCE smoke.py:209-222]`: no `p_raw/p_simes/p_published/n_k/r_healthy/model_forecast/
(left)/(right)/tilde_p`, no backslash, no `·`; `calibrating` is additionally banned in the pod-level prose
`[SOURCE smoke.py:1044]`. Subscripts stay `p`, `p_simes`, `p_raw`, `p_published` (as `<sub>` + `data-tex`);
never print the JSON key `analysis_state` in prose — write "analysis state".
**New page 7** `#guide-status`, menu button `data-guide="guide-status"`, title *Reading the status*:
- What this shows: "Four analysis levels, computed from the live payload: healthy - calibrated, healthy - raw,
  degraded, error. They describe the scoring path, not the workload." Then the 4-row table
  (Level | How it is decided | Variant) mirroring §1, then one 1-2 line block per badge using the §3 tooltip
  sentences verbatim (window, mandatory, calibration, probability, model age, drift, computable fraction, Keff).
- Norm: "healthy - raw is the expected calm state on flat load; a raw probability means the calibration mapper
  is not verified healthy at this tick, not that the metric is degraded."
- Calming rule: "degraded = a required metric could not be computed at this tick; informational counters that
  fail to align do not change the level."
**Calibration-dormancy paragraph** for `#guide-chain` (after the table) and `#guide-podlevel` (after Norm):
> "**Why the published probability is often raw.** Calibration maps the score onto the healthy reference
> exceedance scale: an isotonic fit on a healthy window, kept only if a held-out gate passes, and refit at most
> every 288 ticks (24 h). A refit is rejected when the healthy window has no genuine spread - no narrow cluster
> worth learning a mapping from - so the mapper stays dormant and the published value is the raw posterior.
> Obtaining raw under flat load is therefore expected; calibrated means verified."
All numbers there are pre-existing display text; gate/π/sojourn stay only in payload-sourced text.
**Smoke updates:** `guide: 6 menu buttons` → 7 `[SOURCE smoke.py:648-649]`; add the new page to the
banned-token sweep and pin it is not active by default.

## 6. Backend + test surface (fast, safe)

- `dashboard_routes.py`: **no change** under option (ii) — the four levels are derived client-side. Under (i)
  only `_solo_analysis_state` (2108) + the 4 emission sites + 3 pinning tests.
- `index.html`: `soloAnalysisLevel()` + badge mapping (3022-3034), badge wrappers + `fitTooltip` (947-960 and
  script top), `timeAxisTitle()` + 3 call sites, `renderTimeseries` x-title branch, badge names/tooltips
  (2436-2492), Guide page + two prose inserts (1113-1230). `shared_selectors.js`: no change.
- Tests touching this: `analyser/tests/unit/test_dashboard_api_routes.py` (external `unknown`, raw-solo
  `degraded`), `tests/unit/test_solo_dashboard_routes.py`, `tests/integration/test_canonical_route_contracts.py`
  (1131/1136 `unknown`, 1364 `ready`). Under (ii) they keep passing unchanged — they are the "external
  payloads untouched" proof.
- Fast command: `cd analyser && export PYTHONPATH=…/pipelineml-shared && PY=/tmp/solo-p3-venv/bin/python &&
  $PY -m pytest tests/unit/test_dashboard_api_routes.py tests/unit/test_solo_dashboard_routes.py
  tests/integration/test_canonical_route_contracts.py -q -k "not browser_inputs_smoke"`.
- **Safe recipe** for `test_solo_dashboard_browser_inputs_smoke` (rewrites untracked evidence): it writes into
  `agent-orchestration/evidence/solo-mode-research/E-card4C-api-records/` via `REDORDS_DIR` (every run rewrites
  the 409 existing files). Keep the `-k "not browser_inputs_smoke"` de-selection; if it must run, prefix
  `REDORDS_DIR=/tmp/p5-records` or back up and restore that directory.
- No scoring/calibration/strike/Simes/Markov file is touched; no threshold added (only existing payload fields
  and the existing `mandatory_metrics` names are read).

## 7. Shipping with P4

Overlapping regions (same file, same regions): axis-title call sites 2644-2830; Guide 1113-1230; badge row
947-960 plus writers 2436-2492; formula blocks are NOT edited by P5 (no `data-tex` changes). Layer P5 on top of
committed P4 (`01f6c50`) and keep all P4 smoke assertions except the two documented deltas (§4 axis table,
§5 page count 6→7) — 101 of 103 stay green. **Recommendation: one workcard (P5) + one combined post-P3 image
(P4+P5)** — one rebuild, one deploy, one gate; nothing in P5 waits on the 24 h window. No reason found not to.

## Operator-decision points

- **O1** degradation rule: mandatory-only (recommended) vs all-configured (calm pods read degraded on 27 % of
  ticks) vs sustained-N.
- **O2** option (ii) display-local four levels (no `/solo` payload change) vs (i) new `analysis_state` strings
  for the solo path only.
- **O3** badge renames (`computable`, `published`) and keeping `window` as info-only (out of the level logic).
- **O4** timeline label: `timeAxisTitle()` in solo + `Time (UTC)` external (recommended) vs leaving external
  as bare `Time`.
