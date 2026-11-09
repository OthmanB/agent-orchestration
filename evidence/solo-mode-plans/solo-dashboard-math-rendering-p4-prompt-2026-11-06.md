# Solo dashboard math rendering & presentation — follow-up prompt (P4, LOW PRIORITY)

**Date:** 2026-11-06
**Status:** follow-up execution prompt for the Supervisor, injected by the operator.
Re-read after compaction.
**Priority: LOW.** This is a display-polish workcard (P4) for the SOLO-OPS campaign.
It must NOT delay or interfere with P3 (calibration-mapper refit loop), which is
the active work.

---

## Read these files first, in this order

1. `agent-orchestration/AGENTS.md` (standing rules).
2. `agent-orchestration/evidence/solo-mode-plans/solo-dashboard-operations-supervisor-prompt-2026-11-06.md` — the campaign loop, rollout loop, and hard stops still apply.
3. `pipelineml-anomaly-detector/markdown/2026-11-06-solo-dashboard-operations-report.md` — **Section 9 is the single source of truth for the formula content** (the 8-row chain table, the two norms, per-panel display notes). P2 shipped plain-Unicode one-line formulas; this workcard replaces that presentation.
4. `agent-orchestration/evidence/E-solo-dashboard-ops/R-P2.md` §3 (math-rendering findings: Plotly CDN is the bundle's only external asset; no MathJax/KaTeX anywhere; internet reachable at R time) and the P2 workcard's "must not touch" / keep-list (ids, bundle files, tests).
5. **THIS file.**

## Operator decision (baked in, overrides the original vision's "plain Unicode, no math library")

The P2 formula lines are not readable: one long line crammed with "·" separators
(ambiguous with multiplication), unexplained set-builder notation (`#{ last W ticks
: p < α }`), literal "tilde_p"/"psimes"/"praw" tokens, inconsistent notation
("observed − model_forecast" in one panel, "observed − expected" in another), and
over-long jargon in y-axis titles. The operator's call: **render the math properly
(LaTeX-like, via KaTeX), one equation per line, with consistent notation.** This
is the whole of this workcard — no new features, no layout redesign beyond it.

## Sequence constraint (IMPORTANT)

- P2's image (digest `9bc505fe`, image source `37ca32e`) is the proven base; P3 is
  in flight and its acceptance needs **≥ 24 h of ticks on ITS new image**.
- **A P4 image build + rollout would restart P3's 24 h window. Therefore: P4 code +
  local proof may start now, but the P4 image/rollout ships ONLY after P3 is
  promoted (24 h window elapsed and gate closed).** If P3 is not yet deployed,
  P4 code lands on the feature branch and waits; if P3's image is live, P4 rides
  the next rollout slot after P3's window closes. Record the wait in the P4 gate.
- Local pre-deploy proof uses the R-P2 §9 scratch proxy (`/tmp/solo-dash-dev/static_proxy.py`,
  port 8090, repo assets + live API) — never a cluster change.

## Scope (five items, all in `analyser/dashboard_assets/`)

### 1. Math rendering: KaTeX

- R decides CDN vs self-hosted; **recommendation: KaTeX from the same CDN family
  as the existing Plotly script** (one `katex.min.css` + `katex.min.js` in the two
  `<script>`/`<link>` slots at `index.html:660-661`), because the bundle already
  depends on a CDN asset (Plotly 2.27.0) and the environment's internet reachability
  was verified at R-P2 time. If R judges the offline case important, self-host the
  KaTeX files under `dashboard_assets/` instead (adding assets is free — the bundle
  contract only requires the existing 4 files to keep existing; see
  `test_static_bundle_contract.py`). No other new dependency.
- **Graceful degradation:** if KaTeX fails to load (offline), the formula lines must
  still show readable plain text (the LaTeX source or the current Unicode fallback —
  R's call), not raw `\(`…`\)` tokens. No blank formula area, no broken layout.
- Render formulas in: the four `.formula` lines under the solo panels, the Guide
  pages (scoring chain + the five panel pages). Nothing else.

### 2. One equation per line; no cramping

- Every formula gets **its own line** (block element / `<br>` structure per R's
  choice). No "·" separator between formulas anywhere.
- Each formula line: the equation, then (if needed) a short plain-English gloss in
  the same line or the next ("strike = a tick whose p falls below 0.05").
  Cryptic notation is only allowed if defined in the same block: e.g.
  `n_k = #{ t ∈ last W ticks : p_t < α }` must come with the words "number of the
  last W=4 ticks whose p is below α=0.05".
- The "two norms" paragraph becomes two labeled lines (or a 2-row table):
  anomaly-norm vs surprise-norm, each with its calm-state value. No run-on sentence.

### 3. Consistent notation (the whole surface, one convention)

Standardize on this set (R may adjust glyphs but must keep ONE convention
everywhere — panel formulas, Guide pages, and axis titles):

| Quantity | Render |
|---|---|
| residual | `r = observed − expected` (pick "expected" or "model forecast" ONCE; the CDF/PDF note and the Observed panel currently disagree) |
| per-tick p | `p = P(r_healthy ≥ |r|)` with r_healthy subscripts rendered, plain gloss "upper tail of the healthy residual distribution" |
| strike count | `n_k` with its set-builder DEFINED in words in the same block |
| tilde p | `\tilde{p}` (never the token "tilde_p") |
| Simes | `p_simes = min_k (K/k)·p_(k)` with subscripts rendered; "·" here is multiplication and is correct only where it means product |
| raw posterior | `p_raw` ("raw Markov posterior", prior π = 0.01, mean sojourn 6 ticks) |
| published | `p_published` = isotonic mapper applied to `p_raw` |
| decision thresholds | from the payload only, never hard-coded in JS (P2 invariant) |

No literal tokens (`tilde_p`, `psimes`, `praw`) may remain rendered as plain
identifiers; they are subscript/tilde names.

### 4. Axis titles: short + conventional

Y-axis titles currently carry whole clauses ("p-value [0,1] (surprise-norm: small
= surprising)"). **Axis titles must be short and conventional**; the explanation
belongs in the formula line and the Guide, not the axis. Proposal for R to adapt:
x = "Time"; p panel y = "p"; tilde trace distinguished in the legend; CDF y =
"F(r)"; PDF y = "density"; pod-level y = "P(anomaly)"; observed/reference y =
metric name + "(metric units)". If KaTeX cannot render inside Plotly axis titles
(it cannot without MathJax), use minimal Unicode ("p", "F(r)", "P(anomaly)") and
let the formula lines carry the full math — state this decision in the gate.

### 5. Guide pages: same treatment

The "The scoring chain" overview page and each panel page get the KaTeX-rendered,
one-equation-per-line versions of the same content (traceable to report §9 —
invent no new numbers). The "a calm value looks like" rows stay plain prose.

## Hard limits (unchanged campaign invariants)

- Display layer only: no API/route/request-set/fetch change; external-pod
  `/timeseries` contract untouched; no scoring/calibration/threshold changes; no
  new product gates/counters.
- Keep P2's keep-list intact (ids, the 4 bundle files, legend block, Maintenance
  card, Playwright-visible elements).
- All P2 acceptance items must still hold after P4 (marker on CDF curve, 288-point
  timeline + consistent counter, selection/scroll stability over ≥ 3 refreshes,
  grayed solo surfaces, Guide 6 pages): P4's smoke must re-assert them, not just
  the new math items.
- No new files in the repo beyond the bundle (self-hosted KaTeX, if R chooses that)
  and the gate record.
- Gate record ≤ 200 lines: `agent-orchestration/evidence/solo-mode-gates/SOLO-OPS-P4.md`.
- Orchestration-repo commits still wait for the operator's "implementation end"
  signal; feature-branch product commits follow the existing loop.

## R open points (P4)

1. KaTeX CDN vs self-hosted (with the offline-fallback behavior defined).
2. Exactly where KaTeX renders (a small `renderFormulas(root)` helper called on
   load + when the Guide tab activates, vs static pre-rendered HTML) — keep it out
   of the 5 s refresh path (formulas are static; never re-rendered per tick).
3. The final notation table (§3) and axis-title set (§4) — record the chosen
   convention in the gate so it cannot drift.
4. Whether the PDF/CDF card title keeps its "(left)/(right)" wording.

## Acceptance (real browser, on the deployed image, at the P4 rollout)

- All formula blocks render as KaTeX (no raw backslash tokens in the visible text);
  one equation per line; "·" used only as multiplication (or nowhere in
  separators); `tilde_p`/`psimes`/`praw` tokens absent from visible text.
- One consistent notation per the §3 table (spot-check 3 surfaces: per-tick
  panel, scoring-chain page, axis titles).
- Axis titles short (≤ 2 words + optional units); clauses moved out.
- Guide: 6 pages intact, scoring chain shows the 8-row table with rendered math.
- Offline simulation (block the KaTeX URL in the browser): formula areas still
  readable, layout unbroken, no console exceptions.
- All P2 acceptance re-asserted (see Hard limits). Local 8090-proxy proof before
  deploy; live proof after.
