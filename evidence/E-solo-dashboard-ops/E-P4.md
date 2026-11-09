# E-P4 — solo dashboard math rendering (KaTeX, display only)

Date 2026-11-06 · role E · package P4 (LOW). Workcard `evidence/omp-workcards/solo-ops-P4.md`
(items 1–6 + acceptance 1–8). Repo `pipelineml-anomaly-detector`, branch
`feature/cnn2dlstm-bayesian-statistical-detector-v2`, work started at HEAD `eadd2e3`.
Only `analyser/dashboard_assets/index.html` modified + new `analyser/dashboard_assets/vendor/katex/**`
created (23 files). All changes left uncommitted in the working tree. No commit/push/add/stash;
no docker/build/cluster; no touch of `solo_mode/**`, `deploy/**`, P3 files, tests, markdown, or
the 8091/18086 ports. Scratch under `/tmp/solo-ops-p4/**`.

## Item 1 — Vendor KaTeX 0.16.47 (flat, self-hosted)

Commands (cwd `analyser/dashboard_assets`), all exit 0:

- `mkdir -p vendor/katex/fonts`
- `curl -fsSL -o vendor/katex/katex.min.css https://cdn.jsdelivr.net/npm/katex@0.16.47/dist/katex.min.css`
- `curl -fsSL -o vendor/katex/katex.min.js https://cdn.jsdelivr.net/npm/katex@0.16.47/dist/katex.min.js`
- `curl -fsSL -o vendor/katex/LICENSE https://cdn.jsdelivr.net/npm/katex@0.16.47/LICENSE`
- font names via `grep -o 'fonts/[A-Za-z0-9_-]*\.woff2' katex.min.css | sort -u` → 20 names;
  each `curl -fsSL -o "$f" https://cdn.jsdelivr.net/npm/katex@0.16.47/dist/$f`

Sizes (expected → got):

| file | expected | got |
|---|---|---|
| `vendor/katex/katex.min.css` | 23 827 | 23 827 |
| `vendor/katex/katex.min.js` | 272 537 | 272 537 |
| `vendor/katex/fonts/*.woff2` (20) | 259 792 total | 259 792 total |
| `vendor/katex/LICENSE` | MIT notice | 1 107 B, "The MIT License (MIT)" |

sha256 (expected → got, both match):

- `katex.min.css` `0289a02cf451a44dd73add683a09644252363871ac11713a647b732cee8b1ee3`
- `katex.min.js` `a29d2961d3146de5949d78ac7c1a9d93ae54955bad22a6db4fbe836e88e8bf48`

Ignore/status checks (cwd repo root):

- `git check-ignore -v <each of the 23 paths>` → no output, exit 1 (none ignored).
- `git status --short -uall analyser/dashboard_assets/vendor` → exactly 23 `??` entries
  (LICENSE + 2 css/js + 20 woff2).

## Item 2 — Load + hook

- `<head>` after the Plotly tag:
  `<link rel="stylesheet" href="vendor/katex/katex.min.css">`
  `<script defer src="vendor/katex/katex.min.js" onload="renderFormulas(document)"></script>`
  (never head-blocking; still exactly one inline `<script>`).
- One global `renderFormulas(root)` in the existing inline script: returns 0 unless
  `window.katex && typeof window.katex.render === 'function'`; for each `[data-tex]` in `root`
  without `data-tex-done`, saves the node's fallback markup, calls
  `katex.render(tex, el, {throwOnError:true, displayMode:false})`, sets `data-tex-done="1"`;
  on throw restores the saved fallback; returns the rendered count.
- Call sites: (a) the script `onload`; (b) first statement of the `DOMContentLoaded` handler;
  (c) `setupTabs` click handler, after the tab-specific branches:
  `if (tab.id === 'tab-guide') renderFormulas(document.getElementById('tab-content-guide'));`.
- Not called from `refreshDashboardView`, the `setInterval`, `loadSelectedPodDetails`, or any
  `soloRender*` (formulas are static markup).

## Item 3 — Markup + CSS

- 4 panel `.formula` containers kept (`#solo-panel .formula` = 4); each now holds, per equation,
  `<span class="formula-line" data-tex="…">FALLBACK</span>` then `<span class="formula-gloss">…</span>`
  (closing gloss without a line = norm note).
- Added 3 CSS rules next to `.formula`:
  `.formula-line{display:block;margin:2px 0;overflow-x:auto}`,
  `.formula-gloss{display:block;font-family:"Avenir Next","Segoe UI","Helvetica Neue",sans-serif;
  font-size:.72rem;color:var(--muted);margin:2px 0 6px}`,
  `.formula .katex{font-size:1em}`.
- Fallback = node's own HTML: Unicode + `<sub>` + `p̃` (p + U+0303); no `\`, no `_`, no U+00B7
  except as multiplication. `data-tex` escapes `<`→`&lt;`, `&`→`&amp;`.
- All clause-separating `·` removed.

## Item 4 — Notation (12 distinct data-tex, 28 total; verified)

`document.querySelectorAll('[data-tex]').length == 28` (panel 8 + guide 1+3+1+3+4+8);
`new Set(data-tex).size == 12` — both asserted in the smoke (pass). E1–E9/D1–D3 verbatim per card
table; residual wording "expected" on every surface; `p̃`/`p<sub>…</sub>`/`n<sub>k</sub>` inline in
prose/h3/buttons/glosses. No threshold numbers printed (D1–D3 use `anomaly threshold` /
`normal threshold` in TeX; two-norms lines say thresholds are "drawn on the pod-level and timeline
charts, read from the payload").

## Item 5 — Axis titles + strings

- metric: `Time` / `${metricName}`; p-panel `Time` / `p`; pod-level `Time` / `P(anomaly)`;
  CDF `residual r` / `F(r)`; PDF `residual r` / `density`. `type`/`range`/`automargin` kept.
- Legends: `p — residual tail`, `p̃ — strike-tail`, `Raw Markov posterior p<sub>raw</sub>`,
  `Published p — calibrated: mapper(p<sub>raw</sub>)` (and the two other published variants keep
  "Published p"). Observed legend and note unchanged.
- `:2688` placeholder → `No per-tick p / p̃ recorded for ${metricName} yet.`
- Prose/h3/buttons: `Per-Tick p and p̃ (metric)`, `:1098`/`:1123`/`:1144`/`:1147`/`:1149`/`:1169` →
  `p̃`; `:961`/guide-resid → `Residual distribution — PDF and CDF (current model)`; `(left)/(right)`
  dropped. Payload property accesses (`.tilde_p`, `.p_raw`, `.p_published`) left intact.

## Item 6 — Guide

- Chain table column "Axis label" → "Axis / legend" (`residual r`, `p`, `—`, `p (legend p̃)`, `—`,
  `—`, `P(anomaly)`, `P(anomaly)`); Quantity column updated per card. 8 rows kept a table
  (`#guide-chain tbody tr` = 8, asserted).
- "The two norms" = 3 separate `<p>` lines (Anomaly-norm / Surprise-norm with calm values, then the
  p̃-not-unfiltered note); `0.2/0.8` removed; thresholds described as "drawn on the pod-level and
  timeline charts, read from the payload".
- Calm-value rows became plain `<p>` (class `formula` dropped) with inline notation only.
- P2 wording guards kept: no "at or below" in `#guide-resid`, no "calibrating" in the Pod-Level
  prose (both asserted in the smoke).

## Acceptance steps 1–8

cwd `analyser/` unless stated.

1. **Item-1 checks** — sizes/sha256 match (table above); `git check-ignore -v` on all 23 paths →
   empty, exit 1; `git status --short -uall analyser/dashboard_assets/vendor` → 23 `??`. PASS.
2. **`/tmp/solo-ops-p2/check_syntax.sh`** → `SYNTAX_OK` (run after each item; exit 0). PASS.
3. **Targeted pytest** —
   `.venv_test/bin/python -m pytest tests/integration/test_dashboard_overview.py
   tests/integration/test_dashboard_system_health.py tests/unit/test_static_bundle_contract.py -v`
   → **10 passed in 8.29 s** (exit 0; P2 baseline 10/10). PASS.
4. **grep** —
   - `grep -nE 'model_forecast|\((left|right)\)' dashboard_assets/index.html` → nothing (exit 1).
   - `grep -n 'tilde_p' dashboard_assets/index.html` → only the property access
     `row.details.metrics[metricName].tilde_p` (line 2749).
   - `tilde_p|p_raw|p_simes|p_published` absent from the HTML part (above the inline `<script>`
     tag at line 1216) — 0 hits. PASS.
5. **Smoke** — copied `/tmp/solo-ops-p2/smoke.py` → `/tmp/solo-ops-p4/smoke.py` (P2 section kept
   byte-identical; P4 additions appended). Proxy `python3 /tmp/solo-dash-dev/static_proxy.py
   --port 8090` started as a background process, killed afterwards.
   - **P2 re-run, unedited, against the new page**: `64/64 checks passed` (exit 0) — zero P2
     edits.
   - **P4 smoke**: `103/103 checks passed` (exit 0). 103 = 64 P2 + 39 P4. P4 additions (all PASS):
     - Online 1440×1000, solo pod + non-default metric: `window.katex` set; `[data-tex]` = 28,
       `#solo-panel [data-tex]` = 8, all `data-tex-done`; 4 `.formula` each with ≥1 `.katex`;
       `.katex-error` = 0; 12 distinct `data-tex`; `#solo-panel .formula` still 4 non-empty.
     - Per block (panel counts [1,3,1,3]; guide-observed/pertick/resid/podlevel/timeline =
       1/3/1/3/4; chain = 8 `td.formula` with one `.katex` each): each `.formula-line` holds exactly
       one `.katex`, `display:block`, and (while its page is the active/visible one) its rects are
       ascending and non-overlapping.
     - Visible-page `innerText` clean: no `\`, no U+00B7, none of
       `tilde_p|p_raw|p_simes|p_published|n_k|r_healthy|model_forecast|(left)|(right)`; "expected"
       present in panel 1, chain row 1, PDF/CDF block. Banned-token + axis-title + legend-name
       check across the 5 solo charts' `_fullData[].name`s and axis titles (none contain a banned
       token, `[ ] : , =`, or "norm").
     - Axis titles equal the item-5 table exactly, each ≤ 2 whitespace words, none containing
       `[ ] : , =` or "norm" (5 charts).
     - Refresh window (existing ≥16 s block): `.katex` count, `[data-tex-done]` count and the first
       `.katex` node identity unchanged (marker `data-p4-marker` survives; 28→28).
     - 900×1000 context (online, dashboard tab): no `.formula`/body horizontal overflow
       (`scrollWidth ≤ clientWidth+1`).
     - Offline, two fresh Chromium contexts — `route('**/vendor/katex/katex.min.js', abort)` and
       `route('**/vendor/katex/**', abort)`: `.katex` = 0; every visible `.formula-line` has
       non-empty `innerText` and `offsetHeight > 0` (lines in hidden guide tabs are excluded by
       design — offsetHeight 0 there; all 28 lines still carry non-empty fallback text); no `\`,
       banned tokens absent, U+00B7 only inside `.formula-line`; zero `pageerror`, zero console
       errors other than "Failed to load resource"; `#solo-pt-chart .main-svg` present; 4
       `#solo-panel .formula` non-empty; no overflow at 1440 and 900.
     - Timezone re-check (Asia/Tokyo + UTC, delta 0) carried by the retained P2 block. PASS.
6. **Screenshots** → `evidence/E-solo-dashboard-ops/p4-shots/`:
   `panel-1440`, `panel-900`, `guide-chain-1440`, `guide-chain-900`,
   `guide-observed-1440`, `guide-pertick-1440`, `guide-resid-1440`, `guide-podlevel-1440`,
   `guide-timeline-1440`, `offline-panel`, `offline-guide-chain` (11 PNGs). PASS.
7. **`git diff --stat -- analyser/dashboard_assets`** = `index.html` only
   (`1 file changed, 97 insertions(+), 41 deletions(-)`); `vendor/katex/**` untracked; changes
   left uncommitted. PASS.
8. **This report** written. PASS.

## Deviation from the card

- **P2 assertion count**: the card states the P2 smoke has "64 assertions, must pass unedited".
  The unedited P2 smoke (`/tmp/solo-ops-p2/smoke.py`) runs to **64/64** at runtime (some `check`
  calls are emitted per loop iteration — e.g. the 6 guide pages, 5 axis-title pairs, 2 timezones —
  so the static `check(` call-site count is 54 but the executed total is 64, matching the P2 report
  §3 "64/64"). The P4 smoke therefore reports **103/103 = 64 P2 + 39 P4**, all PASS. This is a
  counting note, not a content deviation: the P2 section is byte-identical to
  `/tmp/solo-ops-p2/smoke.py` and passes with zero edits.
- **`shared_identifiers.json`**: the card's keep-list names it as a 4th bundle file, but
  `test_static_bundle_contract.py`'s `validate_bundle_path` actually requires only 3 named files
  in `dashboard_assets` (`index.html`, `baseline.html`, `shared_selectors.js`) plus `history.html`;
  `shared_identifiers.json` is not present in `analyser/dashboard_assets/` (the targeted suite
  still passes 10/10, confirming the contract is unaffected). No action needed.
- No other deviation. No scope creep: no scoring/threshold/`solo_mode`/API/route/fetch change,
  no SRI/CSP/hardening, no MathJax, no KaTeX inside Plotly, timeline chart `Time`/`Probability`
  untouched.

## Honest limits

- Local 8090-proxy proof (repo assets + live `/api` proxied to the running solo API) ≠ the deployed
  image; the P4 image/rollout ships only after P3's 24 h window closes (recorded in the gate).
  `font/woff2` MIME + subdirectory serving were verified via the proxy (200s) and R-P2's
  `mimetypes` check.
- KaTeX glyph/typography quality is a visual judgment left to RV/S (headless Chromium reports
  0 `.katex-error` and the MathML annotations match the 12 expected TeX strings, but I could not
  run a vision review in this environment).
- The offline `offsetHeight > 0` assertion is scoped to `.formula-line`s in visible scopes; lines in
  hidden guide tabs legitimately report `offsetHeight 0` and are covered instead by the
  non-empty-`innerText` assertion across all 28 lines.
