# R-P4 — Solo dashboard math rendering & presentation (research)

Date 2026-11-06 · role R (read-only; no repo/product file touched) · package P4 (LOW).
Inputs: P4 prompt, supervisor prompt, report §9 (lines 562-601), R-P2 §3/§7, P2 workcard rev1, `/tmp/solo-ops-p2/smoke.py`.
Source of truth = committed `analyser/dashboard_assets/index.html` (HEAD `37ca32e`, **3258 lines**; the P4 prompt's "~3130" and "script tags 660-661" are stale — tags are at **763-764**).
Nothing modified in the repo. Scratch only: `/tmp/solo-p4-r/**`.

---

## 1. Inventory of formula / notation surfaces `[SOURCE index.html:<line>]`

| Surface | Selector / id | Line(s) |
|---|---|---|
| Packaged model-forecast panel | `#solo-panel .formula` (1) | **949** |
| Per-tick p and tilde_p panel | `.formula` (2) | **956** |
| Residual PDF/CDF card | `.formula` (3) | **963** |
| Pod-level card | `.formula` (4) | **973** |
| Prose with notation, panel | `h3`/`.chart-subtitle`/`p.muted` | 954, 955, 961, 962, 972, 976 |
| Guide container | `#tab-content-guide` (6 `.guide-page`) | 1104-1188 |
| Guide chain page | `#guide-chain`, `table` 8 rows, `td.formula` ×8 | 1104, 1110-1118 |
| Two-norms paragraphs | `#guide-chain p` (not a table) | 1122-1123 |
| Calm-value rows | `td.formula` per page | 1129, 1141, 1153, 1165, 1177 |
| Solo chart layouts (axis titles + traces) | `soloRenderObserved` etc. | 2549-2800 |
| Timeline chart layout | `#timeseries-chart` | 1808-1812 |
| Chart id constants | `solo-chart-ids` | 2604-2609 |

Exact current texts `[SOURCE, verbatim]`:
- 949 → `r = observed − model_forecast (residual; 0 = as expected)`
- 956 → `p = P(r<sub>healthy</sub> ≥ |r|) · n<sub>k</sub> = #{ last W ticks : p < α } · tilde_p = P(N ≥ n<sub>k</sub> | N ~ Binomial(W, α)) = 1 if n<sub>k</sub> = 0 (W = 4, α = 0.05 here). Two norms: surprise-norm (p-value) — small = surprising; calm ⇒ p ~ Uniform(0,1) and tilde_p ≈ 1. Not the anomaly-norm of the pod-level probability (calm ⇒ ≈ 0).`
- 963 → `F(r) = empirical mid-rank CDF of the model's N persisted residuals, strictly inside (0, 1) (tie handling differs from a naive count formula — no closed form is shown); PDF = density of the same N residuals; marker at y = F(latest residual). r = observed − expected.`
- 973 → `p<sub>simes</sub> = min<sub>k</sub> (K/k)·p<sub>(k)</sub> over the metrics' tilde_p → evidence → two-state Markov posterior (prior π = 0.01, mean sojourn 6 ticks) = p<sub>raw</sub>; p<sub>published</sub> = isotonic(p<sub>raw</sub>). Anomaly-norm: P(anomaly); calm ⇒ ≈ 0.`
- 947/948 → h3 `Observed Window and Persisted Model Reference` + note "the overlay is a model reference, NOT a causal forecast history".
- 954/955 → h3 `Per-Tick p and tilde_p (metric)` + subtitle `Published residual-tail p (raw) and time-corrected strike-tail p (tilde_p) per scored tick, …; tilde_p corrects p for the strike-window time base.`
- 961 → `Residual PDF (left) and CDF (right) — current model`
- 972 → h3 `Pod-Level Probability: Raw Markov Posterior vs Published`
- 1111 → `r = observed − model_forecast (forecast error)`; 1112 `p = P( r<sub>healthy</sub> ≥ |r| ) — upper tail of the fitted healthy residual CDF`; 1113 `n<sub>k</sub> = #{ last W=4 ticks : p < α=0.05 }`; 1114 `tilde_p = P(N ≥ n<sub>k</sub> | N ~ Binomial(4, 0.05)): =1.0 if n<sub>k</sub>=0, else binom.sf(n<sub>k</sub>−1,4,0.05)`; 1115 `p<sub>simes</sub> = min<sub>k</sub> (K/k)·p<sub>(k)</sub> over the K metrics' tilde_p`; 1116 `+g·tanh(strength) if p<sub>simes</sub> < α<sub>fuse</sub>, else −f·tanh(deficit)`; 1117 `two-state Markov posterior, prior π = 0.01, mean sojourn 6` (prose, no equation); 1118 `isotonic mapper(p<sub>raw</sub>), fitted on the healthy-reference warm-up window`.
- 1122/1123 → two-norms paragraphs (prose, `p`/`tilde_p`/`p<sub>simes</sub>` tokens; hard-code 0.2/0.8 in 1123).

### 1.1 Notation inconsistencies (each is a P4 edit target)
1. **Residual named three ways**: `model_forecast` (949, 1111, 1133), `expected` (963, 1157), and "model reference" in the observed-card subtitle (947). Payload key is `expected` (§4).
2. **Code identifiers in visible text**: `tilde_p` at 954 (h3), 955 (subtitle), 956/973 (formula blocks), 1098 (guide menu button), 1114 (row 4), 1123/1144/1145/1149/1169 (guide prose+cells), and **2688** — the `soloChartUnavailable` placeholder text `No per-tick p/tilde_p recorded for …` is *visible* text, and 2699 (legend); `p<sub>simes</sub>`/`p<sub>raw</sub>` are acceptable (HTML sub), but 956/973 mix `tilde_p` with `<sub>` forms.
3. **Multiple equations per line**: 956 (3 equations + a norms clause), 963 (3 statements), 973 (3 statements) — violates "one equation per line".
4. **Middle-dot as separator**: 956/963/973 use `·` to join *unrelated clauses*; 1116 uses `·` as multiplication. Same glyph, two meanings.
5. **Threshold duplication**: guide prose hard-codes `0.2`/`0.8` (1122, anomaly-norm paragraph; 1123 is the surprise-norm one) while the charts read `tick.details.thresholds` (P2 invariant). Report §9 says thresholds are payload values.
6. **Axis titles carry norm clauses** (2550 pod-level, 2703 p-panel) and a 49-char metric title (2676).
7. **`(left)/(right)`** (961) is layout-dependent and false below 1024 CSS px (`.chart-grid-2` collapses, 737-757).
8. **`[0,1]`/`density`/`F(r)` inconsistent** between panel, guide and chart titles.

---

## 2. KaTeX delivery — decision: SELF-HOST (v0.16.47)

`[LIVE curl 2026-11-06]` npm registry: `latest` dist-tag = 0.19.1; **newest 0.16.x = 0.16.47**; 48 releases in the 0.16.x line. P4 prompt says "stable 0.16.x" → pin **0.16.47**.

| URL (jsDelivr `katex@0.16.47/dist/...`) | status | bytes | cache |
|---|---|---|---|
| `katex.min.css` | 200 | 23 827 | `max-age=31536000, immutable`, CORS `*` |
| `katex.min.js` | 200 | 272 537 | same |
| `fonts/KaTeX_Main-Regular.woff2` | 200 | 26 272 | same |
| cdnjs `ajax/libs/KaTeX/0.16.47/katex.min.js` | 200 | 272 537 | — |
| cdnjs `.../katex.min.css` | 200 | 23 827 | — |

Both CDNs serve 0.16.47; jsDelivr pins per-version (immutable). Nothing is fetched from the pod, so **pod-network reachability is irrelevant** — the *browser* is the consumer.

**Self-host layout** `analyser/dashboard_assets/vendor/katex/`:
- `katex.min.css` (23 827 B) + `katex.min.js` (272 537 B) = 296 364 B;
- `fonts/*.woff2` — CSS has **20 `@font-face`** rules, and `woff2` is **first in every `src` list** `[LIVE: all 20 verified]` → only woff2 is ever requested by a modern browser. All 20 woff2 = **259 792 B (253.7 KiB)**.
- Total vendored ≈ **543 KiB**; a page load fetches only the families used. `[LIVE]` the final 12-formula set requests exactly 3 files: `KaTeX_Main-Regular.woff2` 26 272, `KaTeX_Math-Italic.woff2` 16 440, `KaTeX_Size4-Regular.woff2` 4 928 → **47 640 B (46.5 KiB)**. Ship all 20 (robustness, +207 KiB) rather than a 3-file subset that breaks on any formula edit.

**Why self-host wins here** (evidence-backed):
1. **Offline/air-gapped operation is the requirement, not an optimisation** — the cluster pod already serves the whole `dashboard_assets/` tree, and the acceptance test "block the KaTeX URL" becomes a *real* test instead of a simulation of a failure that cannot occur in production.
2. **No third-party hang in the render path.** Measured with a hanging server `[LIVE]`: a *head-blocking* script (today's Plotly pattern) leaves the page blank for **25 s**; `defer`/`async` and body-end sync scripts give **22-40 ms** first paint. A self-hosted asset cannot hang (same origin as the page).
3. **Version pinned in git** → rendered math cannot change under the operator.
4. Plotly stays the only external dependency (a CDN block already breaks the charts; that is P2's known behaviour, unchanged).

**Delivery plumbing (all verified, nothing to add):**
- Route serves subdirectories: `detector_dashboard.py:38-40` blueprint `/<path:filename>` → `send_from_directory(bundle_path, filename)`.
- MIME: Flask/`mimetypes` on this Python returns `font/woff2` (`mimetypes.guess_type` check `[LIVE]`).
- **Ignore rules**: no `.dockerignore` anywhere in the repo (repo root, `analyser/`, `deploy/` — none), so the image build context is unfiltered. Root `.gitignore` is the standard Python template; the only patterns that could bite are `dist/` (line 16) and `lib/`/`lib64/`/`sdist/` (20-23). `git check-ignore` on the **flat** vendored paths (`vendor/katex/katex.min.js`, `katex.min.css`, `fonts/*.woff2`) → **exit 1, not ignored** `[LIVE]`.
  **Trap**: KaTeX's download layout is `dist/…`; copying it as `vendor/katex/dist/…` is **silently git-ignored** (`check-ignore -v` → `.gitignore:16:dist/`, exit 0) `[LIVE]`. Copy the *contents* of `dist/` flat into `vendor/katex/` (`katex.min.css`, `katex.min.js`, `fonts/`), which is what §2 sizes assume.
- Dockerfile: single-stage `COPY analyser .` (no per-path whitelist) → `vendor/**` ships. Image cost +543 KiB.
- `analyser/tests/unit/test_static_bundle_contract.py::validate_bundle_path` only **requires** 4 named files (index.html, baseline.html, shared_selectors.js, shared_identifiers.json) and does not forbid extras → unaffected.

---

## 3. Render hook — minimal design (open point 2)

**Markup contract.** Each equation becomes its own element inside the (kept) `.formula` container:

```html
<p class="formula">
  <span class="formula-line" data-tex="r = \text{observed} - \text{expected}">r = observed − expected</span>
  <span class="formula-gloss">the tick's metric value minus the persisted model's expected value; 0 = as expected</span>
</p>
```

- The element's **own text is the readable Unicode fallback**; `data-tex` is the LaTeX source. With KaTeX absent the node simply keeps its text — never a `\(` or `\frac`.
- `.formula` stays the container (P2 smoke pins `#solo-panel .formula` count = 4); the number of `.formula-line` rows varies per block (1, 3, 3, 3 in the panel; 1-2 in the guide cells).
- `data-tex` on `td.formula` cells of the chain table works identically (the cell keeps its Unicode text as fallback).

**Helper** (single global, ~10 lines, placed with the other render functions):

```js
function renderFormulas(root) {
    if (!window.katex || typeof window.katex.render !== 'function') return 0;
    let n = 0;
    (root || document).querySelectorAll('[data-tex]').forEach(el => {
        if (el.dataset.texDone) return;
        try { window.katex.render(el.getAttribute('data-tex'), el,
                { throwOnError: false, displayMode: false }); el.dataset.texDone = '1'; n++; }
        catch (e) { /* keep Unicode fallback */ }
    });
    return n;
}
```

- `displayMode: false` **is deliberate**: measured in Chromium, `displayMode:true` produces a centred block with its own vertical size and detaches from the 0.76rem `.formula` footprint; inline math inside a `display:block` wrapper gives the same "one equation per line" result with the dashboard's own typography (see §8).
- Idempotent via `data-tex-done` (a re-render would otherwise duplicate — measured: a second `katex.render` on the same node is safe, but the guard keeps counts stable for the smoke).

**Call sites (all cheap, all after first pass no-ops):**
1. `<script>` `onload` of `katex.min.js` (covers late load; inline attribute, no extra file);
2. `DOMContentLoaded` (already exists at 830);
3. Guide-tab activation — the tab switcher is `document.querySelectorAll('[data-tab-target]')` → `switchTab` (1315-1355); hook `renderFormulas(document.getElementById('tab-content-guide'))` there (one line), or simply call `renderFormulas(document)` — costs 8 nodes in `#solo-panel` and returns 0.
4. `window.load` optional third safety net (idempotent).

**Never in the refresh path.** Evidence:
- `setInterval(refreshDashboard, 5000)` (269) → `refreshDashboard()` → `loadSoloPayload` → `soloRender*`; the JS never reads or writes `.formula`/`[data-tex]` (grep: no match outside markup), and the Guide DOM is only toggled by `classList` on tab switch (1329/1353).
- `[LIVE]` on the real page (8091) with markup injected: over 7 s (≥1 refresh) `katex` span count stayed 12, block heights 35/116/35/80 px unchanged, no re-render.
- P2 §7 already states the page body is not re-rendered; confirmed again here: `refreshDashboard` writes only `textContent` of badges/notes and `innerHTML` of chart placeholders (R-P2 §7 list).

**Load order / blocking `[LIVE, real Chromium, 8091 page + hang server]`**

| KaTeX script placement | first paint | DCL | KaTeX used | fallback visible |
|---|---|---|---|---|
| `<head>` blocking (today's Plotly pattern) | **25 013 ms** blank | 25 013 ms | yes | — |
| body-end sync | 32 ms | 25 018 ms | yes (at ≥25 s) | yes before |
| `<head>` + `defer` | 32-40 ms | 25 018 ms | yes | yes |
| `<head>` + `async` | 36 ms | 12 ms | yes | yes |
| self-hosted (any) | 28-40 ms | normal | yes | yes |
| CDN blocked via `route.abort` | 304 ms total page | normal | no (0 rendered) | **yes**, no console exception |

Rule: **`<script defer src="vendor/katex/katex.min.js" onload="renderFormulas(document)"></script>`**, never a head-blocking script. `defer` executes after the inline bootstrap has run (so the existing chart init is untouched) and delays `DOMContentLoaded` only by the script's own transfer; a failed load costs nothing.
**CSS**: `<link rel="stylesheet" href="vendor/katex/katex.min.css">` in `<head>` — CSS is render-blocking by nature, but self-hosted it is 24 KB from the same origin as `index.html` (already fetched). A *CDN* CSS would make first paint dependent on a third party (measured: blocked CSS ⇒ blank page until it fails) — the decisive argument for self-hosting, independent of the air-gap argument.

---

## 4. Notation table (open point 3) — FINAL proposal

Residual terminology decision: **`expected`**. Evidence: payload `latest_recorded_residual` carries `{key, expected, observed, residual, model_id, model_age_seconds, tick_epoch}` and per-metric records carry `observed`/`p`/`residual`/`tilde_p`/`p_simes`/`p_raw`; `diagnostics.py` computes `residual = observed − cdf` (the comment calls the cdf "causal forecast"), but **there is no `model_forecast` field anywhere in the payload** (`grep` over `/solo` JSON and `solo_mode/**`: 0 hits). R-P2 §3.4 already recommended `expected`; report §9 row 1 says `r = observed − model_forecast`. Choosing `expected` keeps the formula consistent with the payload, the chart subtitle ("model reference, NOT a causal forecast history") and `r = observed − expected` already at 963. The Guide row 1 formula and the panel text must change to `expected`; the report §9 row-1 wording is superseded (E should note this in the gate, report stays untouched).

| # | Quantity | `data-tex` (LaTeX) | Unicode fallback (element text) | Gloss (plain English) |
|---|---|---|---|---|
| 1 | residual r | `r = \text{observed} - \text{expected}` | `r = observed − expected` | metric value at the tick minus the persisted model's expected value; 0 = as expected |
| 2 | per-tick p | `p = P\left(r_{\text{healthy}} \ge \lvert r\rvert\right)` | `p = P(r_healthy ≥ |r|)` | upper tail of the fitted healthy residual distribution |
| 3 | strike count n_k | `n_k = \#\{\,t \in \text{last } W \text{ ticks} : p_t < \alpha\,\}` | `n_k = #(t ∈ last W ticks : p_t < α)` | number of the last W = 4 ticks whose p is below α = 0.05 |
| 4 | strike-tail p (tilde) | `\tilde{p} = P\left(N \ge n_k \;\middle|\; N \sim \mathrm{Binomial}(W,\ \alpha)\right)` | `p̃ = P(N ≥ n_k | N ~ Binomial(W, α))` | tail probability of seeing at least n_k strikes in W ticks if each tick were healthy (1 when n_k = 0) |
| 5 | Simes gate | `p_{\text{simes}} = \min_k \frac{K}{k}\, p_{(k)}` | `p_simes = min_k (K/k)·p_(k)` | smallest Simes-adjusted strike-tail over the K metrics |
| 6 | evidence | `\ell(t) = \begin{cases} +g\tanh(\text{strength}) & p_{\text{simes}} < \alpha_{\text{fuse}} \\ -f\tanh(\text{deficit}) & \text{otherwise}\end{cases}` | `ℓ(t) = +g·tanh(strength) if p_simes < α_fuse, else −f·tanh(deficit)` | signed evidence fed to the Markov layer (sign = direction) |
| 7 | raw posterior | `p_{\text{raw}} = P(\text{anomaly} \mid \ell(t))` with `π = 0.01`, sojourn 6 | `p_raw = P(anomaly | ℓ(t)), π = 0.01, sojourn 6` | two-state Markov posterior probability of the anomaly state |
| 8 | published | `p_{\text{published}} = \text{isotonic}(p_{\text{raw}})` | `p_published = isotonic(p_raw)` | raw posterior after the fitted isotonic calibration |
| 9 | CDF / PDF | `F(r)`, `f(r)` | `F(r)`, `f(r)` | empirical CDF of the model's persisted residuals / its density |

`·` appears **only** as multiplication (`(K/k)·p_(k)`, `+g·tanh`); clauses are separate lines or glosses.

**Number provenance (P4 "invent no new numbers"):**
- `W = 4`, `α = 0.05`, `π = 0.01`, `sojourn 6` are **not in the `/solo` payload** `[LIVE]`: payload keys at top level are `candidate, calibration, details, drift_state, error, fingerprint, label, latest_recorded_residual, metrics, model_age_seconds, model_family, model_info, model_version, n_points, p, p_posterior_raw, p_simes, padded_*, probability_label, reference_models, residual, residual_cdf, generated_at, …`; `tick.details` = `{thresholds:{anomaly:0.8, normal:0.2}, *, metrics{…}}`; `reference_models[*]` = `{model_id, window_ready, …}`. No `window_fill`/`alpha`/`sojourn`/`prior` anywhere in the JSON. They are algorithm constants of `solo_mode/config.py` and are **already hard-coded today** at 956/1113/1114/1117/1144/1145/1169 → keep them as hard-coded **display** text traceable to report §9 (do not add API fields).
- `K` = number of metrics; present in the payload as `tick.details.metrics` (key count) — display symbolically only.
- `α_fuse`, `g`, `f`: not exposed; symbolic only (no numbers shown).
- `n_k`: not exposed as a field (derived backend-side); symbolic only.
- thresholds `0.2`/`0.8`: **payload-derived** (`tick.details.thresholds`) and read by the charts; the Guide prose hard-codes them today (1123). Recommended: the guide sentence says "the live normal/anomaly thresholds shown on the pod-level chart (read from the payload)" and prints no number — consistent with P2's invariant and with "invent no new numbers". Everything else printed is report §9.

---

## 5. Axis titles (open point 3b) and legend names

**Plotly cannot render KaTeX here — settled** `[LIVE]`: `window.MathJax === undefined`; injecting KaTeX HTML into an axis title renders the MathML string **as literal text** (`.ytitle.textContent` = `<math xmlns="http://www.w3.org/1998/Math…`), because Plotly escapes everything outside its supported subset `<b> <i> <sub> <sup> <br>` `[LIVE, screenshot]`. `<sub>`/`<sup>` **do** render (`tspan` at 70% size) in axis titles *and* in legend entries `[LIVE, screenshot]`; U+0303 combined `p̃` renders correctly in the rotated y title and in the 12px legend `[LIVE, screenshot]`.

| Chart | Current | Proposed |
|---|---|---|
| `solo-metric-chart` (2675-2676) | x `Time`; y `${metricName} (metric units)` | x `Time`; y **`${metricName}`** |
| `solo-pt-chart` (2702-2703) | x `Time`; y `p-value [0,1] (surprise-norm: small = surprising)` | x `Time`; y **`p`** |
| `solo-prob-chart` (2549-2551) | x `Time`; y `P(anomaly) [0,1] (anomaly-norm: small = normal)` | x `Time`; y **`P(anomaly)`** |
| `solo-cdf-chart` (2794-2796) | x `residual (observed − expected), metric units`; y `F(r)` | x **`residual r`**; y `F(r)` |
| `solo-pdf-chart` (2797-2800) | x same; y `density` | x **`residual r`**; y `density` |
| `#timeseries-chart` timeline (1809-1813) | x `Time`; y `Probability` | **keep** (`Probability` is 1 word; the chart is the shared external surface — out of solo scope) |

Metric-name rule for the observed chart: **drop `(metric units)`**, keep the raw metric name. Rationale (measured): "metric units" is not a unit, and the metric name already encodes the unit (`_seconds_total`, `_bytes`, `_packets_total`). With it, the title is 3 words and **332 px tall on a 450 px chart at 900 px width** (`automargin:true`, margin l=45, title spans y 10.6→342.4, not clipped) `[LIVE]`; without it, ~230 px. "≤ 2 words + optional units" is satisfied: `container_cpu_usage_seconds_total` is one token; for a *unit* that is genuinely separate, keep e.g. `… (B)` rather than the phrase "metric units".
`p` (pt chart) is legitimate: both traces (`p`, `p̃`) are p-values on that axis; the tilde trace is distinguished in the legend. The `[0,1]` and "surprise-norm"/"anomaly-norm" clauses move to `.chart-subtitle`/guide prose (the pt subtitle already explains both norms).

**Legend / trace names**

| Line | Current | Proposed |
|---|---|---|
| 2640 | `Observed (boxcar)` | keep |
| 2641 | `Persisted model reference — NOT causal forecast history` | `Persisted model reference` (the clause stays in the card note, 948) |
| 2506-2508 | `Published p — raw (no calibrated mapper)` / `… calibrated: mapper(p_raw)` / `… raw + calibrated ticks` | `p<sub>published</sub> — raw (no calibrated mapper)` / `… calibrated: mapper(p<sub>raw</sub>)` / `… raw + calibrated ticks` |
| 2522 | `Raw Markov posterior p_raw` | `p<sub>raw</sub> — Markov posterior` |
| 2543 | `Simes gate rejected null (anomalous)` | keep |
| 2698 | `p (residual tail p)` | `p — residual tail` |
| 2699 | `tilde_p (strike-tail p, time-corrected)` | `p̃ — strike-tail` (the "time-corrected" clause lives in the subtitle 955) |
| 2732 / 2825 / 2758 | `Residual CDF` / `Residual PDF` / `Latest recorded residual` | keep |

The HTML `.chart-legend` block (913-920) belongs to the general timeline chart and carries no notation → untouched.

---

## 6. `(left)/(right)` on the PDF/CDF card (open point 4) — **DROP**

The two charts are side by side only above 1024 CSS px: `.chart-grid-2 { grid-template-columns: 1fr 1fr }` with a `@media (max-width:1024px)` override to one column (737-757). At 900 px (measured: `gridTemplateColumns: '818px'`, stacked) the parenthetical is false. New card title: `Residual distribution — PDF and CDF (current model)`; each chart's own axis titles identify it (`density` vs `F(r)`), so nothing is lost at any width. No layout change.

---

## 7. Interaction with the 5 s refresh, P2 invariants and the working tree

`/tmp/solo-ops-p2/smoke.py` assertions that touch text P4 changes `[SOURCE smoke.py:<line>]`:
- **211-217**: `#solo-panel .formula` count **== 4** and every `.formula` `textContent.trim()` non-empty → P4 **keeps 4 `.formula` containers**; `textContent` stays non-empty because KaTeX's output embeds the LaTeX in a MathML `<annotation>` (measured: `innerText` no backslash, `textContent` has the source). Never assert "no backslash" on `textContent` — use `innerText` (measured: `innerTextHasBackslash:false`, `textContentHasBackslash:true`).
- **205-206**: axis titles merely non-empty (no pinned strings) → shortening safe.
- **281**: `#guide-chain tbody tr` count **== 8** → the 8-row table must stay a table.
- **655-659**: `#guide-resid` must **not** contain `at or below` → avoid that phrase.
- **641-653**: Pod-Level prose (first `p.muted` inside the `.chart-wrap` holding `#solo-prob-chart`) must **not** contain `calibrating` (case-insensitive) → keep that wording out.
- **256-257 / 279-283**: 6 page buttons; each click leaves exactly one `.guide-page.active` and it changes.
Nothing asserts `tilde_p`, the two-norms text, `(left)/(right)`, or exact axis titles. P2's other 58 assertions are untouched by P4.

Derived **P4 smoke additions** (recommended, not implemented here): `.formula` count 4 + `#solo-panel [data-tex]` == 8 (measured: 1+3+1+3); `.formula .katex` ≥ 1 per container after render; `#solo-panel` and each `.guide-page` `innerText` free of `\\`, `tilde_p`, `p_raw`, `p_simes`, `p_published` (underscored identifiers only — `<sub>` rendering yields `psimes`/`praw` and must not be banned); 8 chain rows each containing `.katex`; axis titles ≤ 2 words and free of `[`, `(`, `:`; offline run (`route.abort` on `**/katex.min.js`) → same fallback assertions, zero console exceptions, `.formula` heights within ±2 px of the rendered run.

**Working tree**: only `analyser/dashboard_assets/index.html` (+ new `analyser/dashboard_assets/vendor/katex/**`) — disjoint from P3 (`analyser/solo_mode/**`, `deploy/**`). Confirmed no overlap; P4 must not touch `solo_mode/**` or the API.

---

## 8. Layout (open point 8) — measured on the REAL page `[LIVE]`

Prototype at `/tmp/solo-p4-r/proto*.html` was superseded by injecting the proposed markup + KaTeX into the live page on the 8091 proxy (real CSS, real cards; no repo change): 4 formated blocks and the 8-row chain table, at 1440 and 900.

| Width | `.formula` block heights (1-eq, 3-eq, cdf, pod) | `.formula` scroll overflow | Guide table | `td` cells | rows |
|---|---|---|---|---|---|
| 900 | 35 / 116 / 35 / 80 px | 0 (all 4) | 816 px | 316 px, no overflow | 33-59 px |
| 1440 | 35 / 116 / 35 / 80 px | 0 | 1040 px | 374 px | 33-59 px |

- Body `scrollWidth == innerWidth` at both widths; no horizontal page overflow.
- The chain table's `Formula` column is the widest (316/374 px) and KaTeX fits with no wrap; the two-line rows (evidence, `p̃` with `binom.sf`) wrap the *gloss*, not the equation, as intended.
- **CSS additions** (3 rules): `.formula-line{display:block;margin:2px 0}`, `.formula-gloss{display:block;font-family:"Avenir Next","Segoe UI","Helvetica Neue",sans-serif;font-size:0.72rem;color:var(--muted);margin:2px 0 6px}`, `.formula .katex{font-size:1em}` (keeps the 0.76rem `.formula` footprint). `overflow-x:auto` is **not** needed (no overflow measured) but is harmless as a safety net on `.formula-line`.
- Screenshots: `/tmp/solo-p4-r/shots/{fblock-1-900,fblock-3-900,guide-chain-900,guide-chain-1440,plotly-sub,plotly-unicode,plotly-katex-title,plotly-axis-sub}.png`.
- The prototype-only artifact "formula block 0 h=148 px" was traced to a missing `Plotly.Plots.resize` in the scratch page, not to P4 markup (the real page at 900 shows 35 px) — recorded so E does not chase it.

---

## 9. Risks / contradictions with the P4 prompt

1. Prompt line references are stale: "script tags 660-661" → **763-764**; "~3130 lines" → **3258**; "`#solo-panel` formula blocks at 949/956/963/973" is correct.
2. P2 workcard: "Only file you may modify: `analyser/dashboard_assets/index.html`" — P4 **must widen this** to allow `analyser/dashboard_assets/vendor/katex/**` (evidence in §2: no ignore rule, no `.dockerignore`, `COPY analyser .`, bundle contract unaffected). Without that, self-hosting is out of contract.
3. Acceptance wording "`tilde_p`/`psimes`/`praw` tokens absent": with `<sub>` rendering the *stem* still appears in `innerText` (`psimes`, `praw`). Interpret the rule as **no underscored code identifiers** (`tilde_p`, `p_raw`, `p_simes`, `p_published`) — otherwise the only compliant rendering would be "p simes"/"p raw", which is worse. Flag for the E gate text.
4. Report §9 row 1 says `model_forecast`; payload says `expected`. P4 picks `expected` (§4) — the report is not to be edited (single source of truth for *content*, but the payload key wins for *token*). E should record the one-word deviation in the gate.
5. `[INFERENCE]` if the pod image is built from a shallow context that excludes untracked files, the vendored dir must be **committed**, not just present — no ignore rule blocks it, so a plain `git add analyser/dashboard_assets/vendor` is required and sufficient.
6. CDN reachability from the pod is irrelevant (the browser fetches it); the *browser* being air-gapped or behind egress filtering is the actual failure mode — one more reason for self-hosting.
7. `font-display: block` in `katex.min.css`: a missing woff2 hides glyphs for up to 3 s before fallback; self-hosting removes the case entirely.
