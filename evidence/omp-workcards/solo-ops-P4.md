# Workcard: SOLO-OPS-P4 — solo dashboard math rendering (KaTeX, display only, LOW priority)

- Parent: [P4 prompt](../solo-mode-plans/solo-dashboard-math-rendering-p4-prompt-2026-11-06.md), [supervisor prompt](../solo-mode-plans/solo-dashboard-operations-supervisor-prompt-2026-11-06.md), [R-P4](../E-solo-dashboard-ops/R-P4.md), report `pipelineml-anomaly-detector/markdown/2026-11-06-solo-dashboard-operations-report.md` §9 (lines 562-601 = only source of formula content), P2 cards `solo-ops-P2.md` + `-rev1.md`, gate `SOLO-OPS-P2.md`.
- Date 2026-11-06 · Status: draft (P output; Supervisor accepts). Repo `/Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector`, branch `feature/cnn2dlstm-bayesian-statistical-detector-v2`, HEAD `eadd2e3`; `index.html` = 3258 lines, unmodified since P2 (`37ca32e`). Line numbers below re-checked today.

## Where P differs from R-P4 (verified)

1. R's markup anchors are right (`:949 :956 :963 :973`, guide `:1090-1188`, `<script>` tags `:763-764`, chart sites `:2507 :2522 :2550 :2676 :2698-2699 :2703 :2795-2800`). R's **JS anchors are wrong**: refresh timer is `scheduleDashboardRefresh` `:1292-1305` (`setInterval` `:1302` → `refreshDashboardView` `:1281`, which only runs `updateSystemHealth` + `refreshPods`); `DOMContentLoaded` is `:3215`; tabs are `setupTabs` `:1307-1334` (`data-tab`, no `switchTab`); `setupGuideMenu` `:1340`. Guide calm rows are `:1125 :1149 :1161 :1173 :1185` (not 1129…).
2. R's legend rename `p<sub>published</sub> — raw…` / `p<sub>raw</sub> — Markov posterior` would break P2 smoke (`smoke.py:246-249`: names contain "Raw Markov posterior" and "Published p"). **Keep those words**, swap only the identifier.
3. R's row-7 `P(anomaly | ℓ(t))` → `| evidence`: §9 writes `P(anomaly | evidence)`; the posterior accumulates history, ℓ(t) is one tick.
4. R missed: `(left)/(right)` also at Guide `:1156`; Guide Timeline page `:1181` carries a decision-rule formula; Guide `:1122` hard-codes `0.2/0.8` (P2 invariant: thresholds come from the payload) → print no threshold numbers.
5. R §7 "offline `.formula` heights ±2 px of rendered" dropped (plain-text fallback legitimately differs); replaced by overflow/visibility checks.
6. `model_forecast` exists nowhere but index.html visible text (`grep` over `analyser`: 3 hits, all markup); payload key is `expected` (`diagnostics.py:556-562`) → "expected" everywhere. `p_(k)` = k-th smallest (`fusion.py:100-125`); `g,f` = rising/falling evidence gains, `α_fuse` = gate level (`fusion.py:218-256`).
7. Proxy `--upstream` default `127.0.0.1:8080` answers 200 now; if it ever fails use `--upstream http://127.0.0.1:18086` (read-only GET; never touch/restart that forward or 8091).
8. KaTeX facts re-measured: jsDelivr `katex@0.16.47/dist` css 23 827 B, js 272 537 B, 20 woff2 = 259 792 B; `katex.render` **empties the node before parsing** (a throw would leave it blank — see item 2).

## Objective / non-goals

Objective: P4 prompt items 1-5 — KaTeX-rendered formulas, one equation per line, one notation, short axis titles, Guide same treatment, graceful offline fallback.
Non-goals: any API/route/request-set/fetch change; scoring, thresholds, `solo_mode/**`; new gates/counters; SRI/CSP/hardening; MathJax; KaTeX inside Plotly; the shared timeline chart (`#timeseries-chart`: `Time`/`Probability` unchanged); redesign beyond the 3 CSS rules in item 3.

## Scope / must NOT touch

Modify only `analyser/dashboard_assets/index.html` and create `analyser/dashboard_assets/vendor/katex/**` (this widens P2's one-file rule). **Do not touch:** `analyser/solo_mode/**`, `deploy/**` (P3 edits both concurrently in this tree), `dashboard_routes.py`, `exporter.py`, `shared_selectors.js`, `baseline.html`, `history.html`, `analyser/tests/**`, `markdown/**`, `.gitignore`, `AGENTS.md`, `analyser/agent-orchestration/`, tester source, protected `ml-components` pair, Dockerfile. No `git add/stash/checkout/commit`, no build/deploy/cluster access; leave all pre-existing and P3 uncommitted items alone; do not run the full unit suite (P3's half-edited `solo_mode` may fail it).

## Items

**1. Vendor KaTeX 0.16.47 — flat.** `mkdir -p analyser/dashboard_assets/vendor/katex/fonts`; curl from `https://cdn.jsdelivr.net/npm/katex@0.16.47/dist/{katex.min.css,katex.min.js}`, the 20 files `fonts/*.woff2` (names = `grep -o 'fonts/[A-Za-z0-9_-]*\.woff2' katex.min.css | sort -u`) into `vendor/katex/` (never a `dist/` dir: `.gitignore:16 dist/` silently ignores it), and `https://cdn.jsdelivr.net/npm/katex@0.16.47/LICENSE` (MIT notice). Expect sizes 23 827 / 272 537 / 259 792 (20 files); sha256 css `0289a02cf451a44dd73add683a09644252363871ac11713a647b732cee8b1ee3`, js `a29d2961d3146de5949d78ac7c1a9d93ae54955bad22a6db4fbe836e88e8bf48`. Mismatch → stop and explain. `git check-ignore -v <each of the 23 paths>` must print nothing (exit 1); `git status --short -uall analyser/dashboard_assets/vendor` must list 23 `??`. Record sizes + sha256 in E-P4.md.

**2. Load + hook.** In `<head>` after the Plotly tag (`:763`): `<link rel="stylesheet" href="vendor/katex/katex.min.css">` and `<script defer src="vendor/katex/katex.min.js" onload="renderFormulas(document)"></script>` (never head-blocking; no second plain `<script>` — `check_syntax.sh` requires exactly one). One global `renderFormulas(root)` in the existing inline script: return 0 unless `window.katex && typeof window.katex.render === 'function'`; for each `[data-tex]` in `root` without `data-tex-done`: save the node's fallback markup, `katex.render(tex, el, {throwOnError:true, displayMode:false})`, set `data-tex-done="1"`; on throw restore the saved fallback; return the rendered count. Call sites: (a) the script `onload`, (b) first statement of the `DOMContentLoaded` handler (`:3215`), (c) `setupTabs` click handler after the tab-specific branches: `if (tab.id === 'tab-guide') renderFormulas(document.getElementById('tab-content-guide'));`. **Never** from `refreshDashboardView`, the `setInterval`, `loadSelectedPodDetails` or any `soloRender*` (formulas are static markup).

**3. Markup + CSS.** Each `.formula` container stays (`#solo-panel .formula` count stays **4**; container may stay `<p class="formula">`) and holds, per equation, `<span class="formula-line" data-tex="TEX">FALLBACK</span>` then `<span class="formula-gloss">…</span>` (a closing gloss without a line = norm note). Fallback = the node's own HTML: Unicode + `<sub>` + `p̃` (p + U+0303); **no `\`, no `_`, no U+00B7 except as multiplication**. Inside `data-tex` HTML-escape `<`→`&lt;`, `&`→`&amp;`. Add 3 rules next to `.formula` (`:618`): `.formula-line{display:block;margin:2px 0;overflow-x:auto}`, `.formula-gloss{display:block;font-family:"Avenir Next","Segoe UI","Helvetica Neue",sans-serif (the body stack, `:39`);font-size:.72rem;color:var(--muted);margin:2px 0 6px}`, `.formula .katex{font-size:1em}`. Separators `·` between clauses are deleted everywhere.

**4. Notation contract (TeX verbatim — all 12 parse in KaTeX 0.16.47 with `throwOnError:true`; the same string is reused on every surface).**
- **E1** `r = \text{observed} - \text{expected}` · fb `r = observed − expected` · gloss "metric value at the tick minus the persisted model's expected value; 0 = as expected"
- **E2** `p = P\left(r_{\text{healthy}} \ge \lvert r\rvert\right)` · fb `p = P(r<sub>healthy</sub> ≥ |r|)` · "upper tail of the fitted healthy residual distribution"
- **E3** `n_k = \#\{\, t \in \text{last } W \text{ ticks} : p_t < \alpha \,\}` · fb `n<sub>k</sub> = #{ t ∈ last W ticks : p<sub>t</sub> &lt; α }` · "number of the last W = 4 ticks whose p is below α = 0.05"
- **E4** `\tilde{p} = P\left(N \ge n_k \;\middle|\; N \sim \mathrm{Binomial}(W,\ \alpha)\right)` · fb `p̃ = P(N ≥ n<sub>k</sub> | N ~ Binomial(W, α))` · "chance of at least n<sub>k</sub> strikes in W ticks if every tick were healthy; 1 when n<sub>k</sub> = 0, else binom.sf(n<sub>k</sub> − 1, 4, 0.05)"
- **E5** `p_{\text{simes}} = \min_{k} \frac{K}{k} \cdot p_{(k)}` · fb `p<sub>simes</sub> = min<sub>k</sub> (K/k)·p<sub>(k)</sub>` · "over the K metrics' p̃ values sorted ascending; p<sub>(k)</sub> = k-th smallest"
- **E6** `\ell(t) = \begin{cases} +g\tanh(\text{strength}) & p_{\text{simes}} < \alpha_{\text{fuse}} \\ -f\tanh(\text{deficit}) & \text{otherwise} \end{cases}` · fb `ℓ(t) = +g·tanh(strength) if p<sub>simes</sub> &lt; α<sub>fuse</sub>, else −f·tanh(deficit)` · "signed evidence fed to the Markov layer; g, f = rising / falling gains, α<sub>fuse</sub> = gate level (no values shown)"
- **E7** `p_{\text{raw}} = P(\text{anomaly} \mid \text{evidence})` · fb `p<sub>raw</sub> = P(anomaly | evidence)` · "two-state Markov posterior of the signed evidence ℓ(t); prior π = 0.01, mean sojourn 6 ticks"
- **E8** `p_{\text{published}} = \mathrm{isotonic}(p_{\text{raw}})` · fb `p<sub>published</sub> = isotonic(p<sub>raw</sub>)` · "isotonic mapper fitted on the healthy-reference warm-up window"
- **E9** `y_{\text{marker}} = F(r_{\text{latest}})` · fb `y<sub>marker</sub> = F(r<sub>latest</sub>)` · "F(r) = empirical mid-rank CDF of the model's N persisted residuals, strictly inside (0, 1) (no closed form shown); PDF = density of the same N residuals; marker = latest recorded residual; x = r = observed − expected"
- **D1** `p_{\text{published}} \ge \text{anomaly threshold} \Rightarrow \text{anomaly}` · **D2** `p_{\text{published}} \le \text{normal threshold} \Rightarrow \text{normal}` · **D3** `\text{otherwise (or } p_{\text{published}} \text{ missing)} \Rightarrow \text{undecided}` (fb = same text in Unicode; gloss on D1: "thresholds are the dashed lines on the chart, read from the payload"; no numbers).

| Block (panel `:949 :956 :963 :973` / Guide page) | equation lines | closing norm note (panels only) |
| --- | --- | --- |
| Observed / `guide-observed` | E1 | — |
| Per-tick / `guide-pertick` | E2 E3 E4 | "Surprise-norm: small = surprising; calm ⇒ p uniform on (0, 1), p̃ ≈ 1. Not the anomaly-norm of the pod-level probability (calm ⇒ ≈ 0)." |
| PDF+CDF / `guide-resid` | E9 | — |
| Pod-level / `guide-podlevel` | E5 E7 E8 | "Anomaly-norm: P(anomaly); small = normal; calm ⇒ ≈ 0." |
| `guide-timeline` | E8 D1 D2 D3 | — |
| `guide-chain` table (rows 1-8) | row n = En, in the existing `td.formula` cell with its gloss (norm sentences stay in the Norm column) | — |

Page totals: `document.querySelectorAll('[data-tex]').length == 28` (panel 8 + guide 1+3+1+3+4+8), exactly 12 distinct `data-tex` strings. Residual wording is **"expected"** on every surface (`:949 :1111 :1133` currently `model_forecast`; drop "forecast error"). `p̃`/`p<sub>…</sub>`/`n<sub>k</sub>` appear as inline Unicode+`<sub>` in prose, h3, buttons, glosses (KaTeX only in `data-tex` lines).

**5. Axis titles + strings (Plotly cannot render KaTeX — Unicode only).** x/y: metric `Time` / `${metricName}` (drop "(metric units)", `:2676`); p-panel `Time` / `p` (`:2703`); pod-level `Time` / `P(anomaly)` (`:2550`); CDF `residual r` / `F(r)`; PDF `residual r` / `density` (`:2795-2800`); keep `type`, `range`, `automargin`. Legends: `:2698` → `p — residual tail`; `:2699` → `p̃ — strike-tail`; `:2522` → `Raw Markov posterior p<sub>raw</sub>`; `:2507` → `Published p — calibrated: mapper(p<sub>raw</sub>)` (other legend names unchanged). `:2688` (`textContent`, plain) → `No per-tick p / p̃ recorded for ${metricName} yet.` Payload property accesses (`.tilde_p`, `.p_raw`, `.p_published`) stay. Prose/h3/buttons: `:954` → `Per-Tick p and p̃ (metric)`; `:955` and `:1098`, `:1123 :1144 :1147 :1149 :1169` → `p̃`; `:961` → `Residual distribution — PDF and CDF (current model)`; `:1156` drop "(left)/(right)"; observed legend and `:948` note unchanged.

**6. Guide.** Chain table: column "Axis label" → "Axis / legend" with `residual r`, `p`, `—`, `p (legend p̃)`, `—`, `—`, `P(anomaly)`, `P(anomaly)`; Quantity column `residual r`, `per-tick p`, `strike count n<sub>k</sub>`, `strike-tail p̃`, `p<sub>simes</sub>`, `evidence ℓ(t)`, `p<sub>raw</sub>`, `p<sub>published</sub>`. "The two norms" = three separate lines (labeled **Anomaly-norm** / **Surprise-norm** with calm values, then the "p̃ is not the unfiltered p<sub>raw</sub> and not P(anomaly) — 4-tick persistence p-value, opposite convention by design" note), no `0.2/0.8`, thresholds described as "drawn on the pod-level and timeline charts, read from the payload". Calm-value rows become plain `<p>` (drop class `formula`) with inline notation only. Keep P2 wording constraints: no "at or below" in `#guide-resid`, no "calibrating" in the Pod-Level prose.

## Preserved invariants (P2 card + refresh fix; unchanged)

All P2 acceptance still holds: CDF marker on curve, 288-point timeline + consistent counter, selection/scroll stability over ≥ 3 refreshes, grayed solo surfaces, Guide 6 pages + 8-row table; keep-list ids (`#baseline-page-link #tab-lineage #timeseries-chart #chart-legend #chart-point-count #maintenance-form #export-button #purge-button #open-history-page-link`, 5 solo chart ids, 4 bundle files); `sameIdentitySilent`/nonce/`stillCurrent()` logic; no fetch/route/request-set change; thresholds only from payload; Guide handlers bound once; the 5 s refresh never re-renders formulas.

## E acceptance (cwd `analyser/` unless stated; no cluster access)

1. Item-1 checks (sizes, sha256, `check-ignore`, 23 `??`). 2. `/tmp/solo-ops-p2/check_syntax.sh` → `SYNTAX_OK`. 3. `.venv_test/bin/python -m pytest tests/integration/test_dashboard_overview.py tests/integration/test_dashboard_system_health.py tests/unit/test_static_bundle_contract.py -v` → pass (P2 baseline 10/10). 4. `grep -nE 'model_forecast|\((left|right)\)' dashboard_assets/index.html` → nothing; `grep -n 'tilde_p' …` → only property accesses/comments; `tilde_p|p_raw|p_simes|p_published` absent from the HTML part (above `<script>` at `:1195`).
5. Smoke: `mkdir -p /tmp/solo-ops-p4`, copy `/tmp/solo-ops-p2/smoke.py` → `/tmp/solo-ops-p4/smoke.py`; start `python3 /tmp/solo-dash-dev/static_proxy.py --port 8090` as a background process (kill afterwards). **All 64 P2 assertions pass with zero edits** (P verified `:205-217 :246-251 :281 :653-659` stay satisfiable; a failing P2 assertion = page regression — fix the page, never the assertion). Add, with `page.on('pageerror'/'console')` collected from page load:
   - Online 1440×1000, solo pod + non-default metric: `window.katex` set; `[data-tex]` total 28, `#solo-panel [data-tex]` 8, all `data-tex-done`; 4 `.formula` each with ≥ 1 `.katex`; `.katex-error` 0; 12 distinct `data-tex`; `#solo-panel .formula` still 4 non-empty.
   - Per block (panel, and each Guide page after clicking it; chain = 8 `td.formula` with one `.katex` each): `.formula-line` count = table above (1/3/1/3; 1/3/1/3/4), each holds exactly 1 `.katex`, `display:block`, rects ascending and non-overlapping. Check text only on **visible** (active) pages with `innerText` (hidden pages' `innerText` = `textContent`, which includes the MathML LaTeX annotation): no `\`, no U+00B7, none of `tilde_p|p_raw|p_simes|p_published|n_k|r_healthy|model_forecast|(left)|(right)`; "expected" present in panel 1, chain row 1, PDF/CDF block; same banned-token check on Plotly `_fullData[].name`s and axis titles of the 5 solo charts.
   - Axis titles equal the item-5 table exactly; each ≤ 2 whitespace words; none contains `[ ] : , =` or "norm".
   - Refresh window (existing ≥ 16 s block): `.katex` count, `[data-tex-done]` count and first `.katex` node identity unchanged.
   - 900×1000 context: no `.formula`/chain-table horizontal overflow (`scrollWidth ≤ clientWidth+1`), `body.scrollWidth ≤ innerWidth`.
   - Offline, two fresh Chromium contexts — `route('**/vendor/katex/katex.min.js', abort)` and `route('**/vendor/katex/**', abort)`: `.katex` 0; every `.formula-line` has non-empty `innerText` and `offsetHeight > 0`; no `\`, banned tokens absent, U+00B7 only inside `.formula-line`; zero `pageerror`, zero console errors other than "Failed to load resource"; `#solo-pt-chart .main-svg` present; 4 `#solo-panel .formula` non-empty; no overflow at 1440 and 900.
   - Timezone re-check (Asia/Tokyo + UTC timeline alignment, delta 0) comes from the retained P2 block.
6. Screenshots → `/Users/obenomar/Work/langGraph/appthrust/agent-orchestration/evidence/E-solo-dashboard-ops/p4-shots/` (`mkdir -p`): `panel-1440`, `panel-900`, `guide-chain-1440`, `guide-chain-900`, one per other Guide page, `offline-panel`, `offline-guide-chain`.
7. `git diff --stat -- analyser/dashboard_assets` = `index.html` only; vendor tree untracked; changes **left uncommitted** in the working tree.
8. Write `…/E-solo-dashboard-ops/E-P4.md`: commands + exit codes, file sizes/sha256, `check-ignore` output, smoke pass count (64 + new), screenshots list, any deviation from this card, honest limits (local proxy ≠ deployed image; eyeball of KaTeX glyph quality left to RV/S).

## RV checklist

- [ ] Diff = `index.html` + `vendor/katex/**` only; none of the must-not-touch files; 23 vendor files not ignored, sizes/sha256 match; keep-list ids intact
- [ ] `defer` script + CSS link, one inline `<script>`; `renderFormulas` guarded, idempotent, restores fallback on throw; not reachable from refresh/`soloRender*`
- [ ] 28 `data-tex`, 12 distinct strings equal to E1-E9/D1-D3; one equation per `.formula-line`; no `·` separators; fallback readable, no `\`/`_`
- [ ] Notation spot-check on panel, chain page, axis titles: "expected", `p̃`, `p<sub>…</sub>`; no `tilde_p`/`model_forecast`/`(left)`/`0.2/0.8` in visible text; payload property accesses untouched
- [ ] Axis titles per item 5; legends keep "Raw Markov posterior" / "Published p"; timeline chart untouched
- [ ] Guide: 6 pages, 8-row table with rendered math, two norms = separate lines, calm rows plain prose; P2 wording guards kept
- [ ] Smoke 64 unmodified P2 assertions + P4 set pass; offline runs clean; 900 px clean; screenshots read

## Gate / dependents

E report `…/E-solo-dashboard-ops/E-P4.md`; gate `…/solo-mode-gates/SOLO-OPS-P4.md` (S, ≤ 200 lines) records: self-host choice, "expected" vs report's `model_forecast`, underscored-identifier reading of the acceptance, Unicode axis titles (Plotly), E7 `| evidence`, no printed thresholds, wait for P3's 24 h window (no P4 image/rollout before), explicit `git add analyser/dashboard_assets/index.html analyser/dashboard_assets/vendor` by S. Unlocks: RV-P4 → S commit → image/rollout after P3 promotion.

## Open points P resolved

CDN vs self-host = self-host (S). Hook = `data-tex` + Unicode fallback, no static pre-render. `displayMode:false`. Residual = "expected". Underscored identifiers banned, `<sub>` stems (`praw`) allowed. `(left)/(right)` dropped. Thresholds/W/α/π/sojourn: thresholds never printed; W/α/π/sojourn stay static §9 text (not in payload). Observed legend/note untouched. Guide-tab render call kept though `onload` already renders hidden pages (KaTeX needs no layout; harmless safety net). No escalation: nothing touches scoring, thresholds, the protected pair, the tester, or conflicts with AGENTS.md.
