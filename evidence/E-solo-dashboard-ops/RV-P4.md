# RV Review — SOLO-OPS-P4

- Date: 2026-11-06
- Reviewer: RV-P4; independent, advisory review of the uncommitted working tree.
- Disposition: **accepted**
- Findings: **0 blockers, 0 should-fix, 0 nits**. Supervisor retains the promotion decision.
- Scope: `analyser/dashboard_assets/index.html` and `analyser/dashboard_assets/vendor/katex/**` only. No product file was modified, staged, or committed by RV; concurrent P3 work was excluded. No cluster/SSH/kubectl operations; no interaction with ports 8090/8091/18086. RV used and stopped its own proxy on 8092.

## Inputs reviewed

Read the complete P4 workcard, including untruncated lines 28/30/32/57/59, P4 operator prompt, E-P4 report, R-P4 report (including its long notation/provenance lines), report §9 (`markdown/2026-11-06-solo-dashboard-operations-report.md:562-601`), P2 gate, reviewer mandate, and orchestration standing rules. Read the full scoped diff, not just the condensed tool display.

## Checks performed

### 1. Scope, bundle, and vendor integrity — PASS

- Ran `git diff -- analyser/dashboard_assets/index.html` and `git status --short --untracked-files=all -- analyser/dashboard_assets`. P4 assets comprise one modified `index.html` (97 additions / 41 deletions) and exactly 23 untracked KaTeX files. No other dashboard asset is changed. The diff contains only the requested CSS, dependency load, static formula/prose/Guide changes, rendering helper/hooks, and solo chart presentation strings.
- Inspected every diff hunk: no API, fetch, route, scoring, threshold computation, selection/nonce/`stillCurrent()` logic, or shared timeline implementation changed. The `#timeseries-chart` markup, styling, layout, `Time`/`Probability` titles, and rendering code have no changed hunk. No P4 changes to must-not-touch files were presented or made; unrelated concurrent P3 paths are not attributed to P4.
- Verified every keep-list ID occurs exactly once: `baseline-page-link`, `tab-lineage`, `timeseries-chart`, `chart-legend`, `chart-point-count`, `maintenance-form`, `export-button`, `purge-button`, `open-history-page-link`, and all five solo chart IDs. Confirmed `index.html`, `baseline.html`, `history.html`, and `shared_selectors.js` remain present. Static bundle contract tests pass below.
- Enumerated all vendor files, computed each size and SHA-256, and ran `git check-ignore -v` over all 23 explicit paths: **empty output, exit 1**. Status lists all 23 as `??`; flat layout, no ignored `dist/` directory. Full individual digest manifest is `/tmp/solo-ops-p4-rv/vendor-manifest.json`.

| Asset | Bytes | Integrity result |
|---|---:|---|
| `katex.min.css` | 23,827 | SHA-256 `0289a02cf451a44dd73add683a09644252363871ac11713a647b732cee8b1ee3` — exact match |
| `katex.min.js` | 272,537 | SHA-256 `a29d2961d3146de5949d78ac7c1a9d93ae54955bad22a6db4fbe836e88e8bf48` — exact match |
| `LICENSE` | 1,107 | Present; SHA-256 `766ccc1f306c885aa45542a9846bbd0a505b27a0374f146778171c2254ce18e3` |
| 20 `.woff2` fonts | **259,792 total** | Exact expected count and aggregate size; all individual digests recorded |

Font sizes: AMS-Regular 28,076; Caligraphic-Bold 6,912; Caligraphic-Regular 6,908; Fraktur-Bold 11,348; Fraktur-Regular 11,316; Main-Bold 25,324; Main-BoldItalic 16,780; Main-Italic 16,988; Main-Regular 26,272; Math-BoldItalic 16,400; Math-Italic 16,440; SansSerif-Bold 12,216; SansSerif-Italic 12,028; SansSerif-Regular 10,344; Script-Regular 9,644; Size1-Regular 5,468; Size2-Regular 5,208; Size3-Regular 3,624; Size4-Regular 4,928; Typewriter-Regular 13,568. Names have the `KaTeX_` prefix and `.woff2` suffix.

### 2. Required execution and test fidelity — PASS

All commands run from the product `analyser/` directory unless stated otherwise:

| Command / check | Result |
|---|---|
| `/tmp/solo-ops-p2/check_syntax.sh` | Exit 0; **SYNTAX_OK** |
| `.venv_test/bin/python -m pytest tests/integration/test_dashboard_overview.py tests/integration/test_dashboard_system_health.py tests/unit/test_static_bundle_contract.py -q` | Exit 0; **10 passed in 7.89 s** (3 integration + 7 bundle checks) |
| E smoke copied to `/tmp/solo-ops-p4-rv/smoke.py`, changing only `127.0.0.1:8090` to `127.0.0.1:8092`; run with `.venv_test/bin/python` | Exit 0; **103/103 passed = 64 P2 + 39 P4**, 50.05 s |
| RV independent `/tmp/solo-ops-p4-rv/review.py` | Exit 0; **37/37 passed**, including exact TeX equality, error recovery, fonts-only abort, late onload, all Guide pages at both widths, and chart dimensions |
| RV nonzero-scroll `/tmp/solo-ops-p4-rv/scroll.py` | Exit 0; **PASS**, 17.05 s, 6 `/pods` requests and 3 `/solo` requests |

Compared `/tmp/solo-ops-p2/smoke.py` with E's `/tmp/solo-ops-p4/smoke.py` using an actual unified diff (`/tmp/solo-ops-p4-rv/p2-vs-p4.diff`): **zero removed or modified original lines**. P4 inserts additional checks/setup; the original P2 assertions and their loop bodies remain unchanged and execute successfully. The copied RV smoke differs from E's only in its port. Its existing screenshot destination remains E's `p4-shots`; the independent RV captures below use a separate directory.

Test-quality observation: E's smoke checks 12 distinct expressions but not verbatim equality, does not cover fonts-only failure or late loading, and its refresh snapshot happened at zero scroll in this run. RV explicitly closed those coverage gaps; they are not product defects. Initial RV scratch attempts encountered a nonexistent selector API and a missing image-composition dependency; the selector probe was corrected to the existing DOM selection pattern, and contact sheets were produced with Chromium instead. Reported pass counts refer to completed successful runs, not those harness errors.

### 3. Markup and notation contract — PASS

- Parsed HTML attributes and compared the set against the workcard's actual E1–E9/D1–D3 strings: **28 total, exactly 12 distinct, no extra or missing strings, verbatim equality** after normal HTML entity decoding. Panel totals **8**, distributed **1/3/1/3**; chain table **8 rows**, one equation each; remaining Guide pages **1/3/1/3/4**.
- All 28 fallback strings are nonempty and contain **no backslash or underscore**. Fallback subscripts are actual `<sub>` markup; tilde is Unicode `p̃`. Dots in fallbacks are multiplication only (Simes/evidence), not equation/clauses separators. Online visible formulas have no raw LaTeX tokens or code identifiers.
- `index.html:969-993` panel formulas and `:1126-1207` Guide content consistently use **expected**, not `model_forecast`; no `(left)/(right)` presentation claims remain. Glosses define strike count, W = 4 and α = 0.05, order statistic, evidence gains, posterior and calibration as specified.
- Checked all five chart axis-title pairs in the live Plotly objects: observed `Time` / `container_memory_working_set_bytes`; per-tick `Time` / `p`; pod `Time` / `P(anomaly)`; PDF `residual r` / `density`; CDF `residual r` / `F(r)`. Type/range/automargin preservation also follows from the diff.
- Legends exactly retain `p — residual tail`, `p̃ — strike-tail`, `Raw Markov posterior p<sub>raw</sub>`, and the calibrated `Published p — calibrated: mapper(p<sub>raw</sub>)` variant. No payload-property access was renamed.
- Six Guide pages and eight rendered table rows remain. Table quantities and Axis / legend entries match workcard item 6. Two norms are separate labeled paragraphs, followed by the separate p̃-not-posterior note. No printed `0.2/0.8` thresholds; chart thresholds still come from payload. Calm-value sections are plain prose, not `.formula`. P2 prose guards pass: no “calibrating” in Pod-Level prose; no “at or below” in Guide residual content.

### 4. Rendering lifecycle and graceful degradation — PASS

- Read `index.html:782-784`, `:1302-1409`, and `:3270-3273`: stylesheet is local, KaTeX script has `defer`, and there is still exactly one inline script. `renderFormulas` guards `window.katex.render`, skips `data-tex-done`, saves/restores fallback markup around `throwOnError:true`, and returns the success count. Its only invocation sites are the script onload, first statement of DOMContentLoaded, and Guide-tab activation. No invocation is in refresh or any `soloRender*` path.
- Page-local malformed-TeX probe exercised a real KaTeX parse throw: returned 0; fallback `readable fallback p<sub>raw</sub> ≥ 0` restored **byte-for-byte**, readable text retained, height **25 px**, no done marker, no uncaught exception. Repeated rendering of already completed page returns 0; absent KaTeX guard also returns 0.
- Fresh-context **JS route-abort**: readable Unicode fallbacks in panel and Guide chain at 1440 and 900; no blanks or page overflow; charts remain rendered. E smoke additionally passed its whole-KaTeX-tree abort case.
- Fresh-context **fonts-only route-abort**: actual font requests aborted while KaTeX JS/CSS load. After browser font fallback settles (4 s wait), equations remain readable in both widths, with system-serif fallback glyphs; no blank lines or uncaught exceptions. Resource-load console errors only, as expected. This is font fallback, not restoration of Unicode source markup.
- **Late-load probe** withheld the original script's src until after DOMContentLoaded. Initially 0 KaTeX nodes and readable fallbacks; assigning src to that same script subsequently fired its original onload handler and rendered **all 28**, with zero exceptions.
- Over the required refresh run `.katex` and done-marker counts stayed **28 → 28** and the first rendered node retained identity. Static formulas are not rewritten by refresh.

### 5. Actual visual review — PASS

Captured **40 original PNGs** plus eight full-resolution contact sheets under [`rv-p4-shots/`](rv-p4-shots/), then **read the images** (not merely screenshot-success flags):

- `panel-{1..4}-{1440,900}.png`: each individual formula block for a selected solo pod and nondefault memory metric.
- `guide-{chain,observed,pertick,resid,podlevel,timeline}-{1440,900}.png`: all six Guide pages at both widths.
- `{js-blocked,fonts-blocked}-panel-{1..4}-{1440,900}.png` and `{js-blocked,fonts-blocked}-guide-chain-{1440,900}.png`: fallback panel and chain coverage at both widths.
- Contact sheets `contact-panel-*`, `contact-guide-*`, `contact-js-blocked-panel-*`, `contact-fonts-blocked-panel-*` cover every panel/other-five-Guide original; chain originals were read separately.

Concrete observations:

1. **Glyphs:** healthy/latest/raw/published/Simes subscripts are visibly lowered, not literal underscore names. The tilde sits above p. The Simes K/k fraction has a visible fraction bar, denominator and multiplication dot; the min index is distinct. E6 has a coherent tall left cases brace spanning the positive/negative rows, clear tanh terms and condition/otherwise column. No tofu/replacement glyphs, collisions, broken braces, or duplicate visible MathML text were seen.
2. **Spacing and long lines:** E4 and E6 fit at 900 without cropping. Each equation occupies its own block; glosses sit below with breathing room. The residual gloss wraps to a second line at 900; equations themselves remain intact. `overflow-x:auto` is present on every line; for these required widths measured `scrollWidth == clientWidth`, so no horizontal scrolling is needed and no scrollbar obscures math. Page body widths equal their viewports.
3. **Chain table:** actual column widths (# / quantity / formula / axis / norm) were approximately **25 / 99 / 547 / 94 / 274 px** at 1440, and **25 / 90 / 411 / 89 / 200 px** at 900. Formula column remains dominant. “Axis / legend” wraps naturally; long glosses wrap inside their column. The strike-count quantity wraps to two lines at 900, without overlap. E4's explanation and E6's gain gloss wrap cleanly. Norm column stays readable and aligned with its row.
4. **Gloss readability:** muted glosses are small but legible at the specified native screenshots, in the dashboard's sans-serif stack; they remain visually subordinate to the formulas. Definitions of W/α and gains are readable rather than crammed into an equation. The two norm labels and the warning that p̃ is not a posterior are distinct blocks. Calm descriptions remain normal-sized prose on all five detail pages.
5. **Offline:** JS-blocked images show readable monospace Unicode equations, real subscripts, tilde, and multiplication-only dots. At 900 the fallback E6 naturally wraps its else branch onto a second visual line within its one equation block; it remains complete. Fonts-only images show slightly different serif metrics and a narrower cases brace but all mathematical content remains discernible after fallback settles. Neither case causes blank formula areas or table/page overflow.

### 6. P2 regression scan — PASS

- Independent smoke CDF marker for nondefault metric: x **−18999.69122800231**, y **0.36403508771929827**, exactly matching interpolated persisted CDF (`1e−9` tolerance); y < 1, annotation agrees. PDF remains left of CDF at 1440 (**PDF right 714; CDF left 726**), histogram uses 570 residuals with probability-density normalization. At 900 charts stack, which is why the new title correctly omits left/right claims.
- Timeline contains **288** probability points; counter = finite history rows = trace length = 288. Two threshold lines, date axis, no stale empty-state placeholder. Existing decision-boundary/null/timestamp/CDF/PDF regression assertions all pass.
- Baseline and Lineage remain visible, grayed/ARIA-disabled with explanatory tooltips before selection; forced Lineage click is correctly guarded. Maintenance event-history wording still passes.
- Required smoke observed **3 automatic `/pods` refreshes over 17.1 s**, retained selection/metric/scroll state, no hidden-panel transition, and stable KaTeX node identity.
- Additional meaningful-scroll run selected the **sixth pod**, metric `container_memory_working_set_bytes`, **window scrollY 1500**, pod-list scrollTop **29** (requested 70, clamped to available range), CDF document-top **3384.0625**. All 17 one-second snapshots identical across **17.05 s**, **6 `/pods` requests / 3 `/solo` requests**, no manual refresh; panel remained visible. This independently checks nonzero scroll rather than relying on E's evidence or the zero-scroll smoke snapshot.
- Asia/Tokyo and UTC contexts both have **timeline-vs-pod first-tick delta 0**; both date axes use the same epoch-ms input. The displayed axis-linear values differ by timezone as expected, but agree within each timezone.
- Guide menu clicks after KaTeX rendering activate exactly one intended page, for all six pages at both widths.
- Live `Plotly.react` charts retain their host dimensions: at 1440, main charts **1236×450**, PDF/CDF **612×450**; at 900, all five **796×450**. `_fullLayout` width/height match host dimensions. KaTeX did not disturb Plotly rendering or resize behavior in the exercised states.

### 7. Mathematical/content traceability — PASS

| Expressions | Source comparison |
|---|---|
| E1 | §9 row 1, with the workcard-approved terminology cutover from `model_forecast` to **expected**; same subtraction and zero-residual interpretation. |
| E2 | §9 row 2: healthy residual upper tail at absolute residual; unchanged meaning. |
| E3 | §9 row 3 and `solo_mode/fusion.py:44-69`: strict **p < α**, last W ticks; W = 4, α = 0.05 are the specified explanatory values. |
| E4 | §9 row 4 and `fusion.py:73-86`: **P(N ≥ n_k)**; 1 when zero strikes, otherwise `binom.sf(n_k−1,4,0.05)`. W/α are explicitly defined by the adjacent E3 gloss in every E3/E4 block. |
| E5 | §9 row 5 and `fusion.py:112-127`: minimum K/k times the ascending k-th strike-tail value. |
| E6 | §9 row 6 and `fusion.py:218-260`: strict Simes gate, **+g tanh(strength)** / **−f tanh(deficit)**; g/f gloss correctly names rising/falling gains; no invented gain/gate values. |
| E7 | §9 row 7 plus two-norm discussion: **P(anomaly | evidence)**, not conditioning on only current ℓ(t); two-state Markov, prior π = 0.01, mean sojourn 6 ticks. `fusion.py:288-300` passes previous posterior and current signed evidence into the shared update, consistent with accumulated evidence. |
| E8 | §9 row 8: isotonic mapping of raw posterior, fitted on healthy-reference warm-up window. |
| E9 | §9 panel display notes: marker at **F(latest residual)**; empirical mid-rank wording preserves the P2-accepted refinement rather than inventing a naive closed-form count. |
| D1–D3 | `dashboard_routes.py:456-483`, specifically **≥ anomaly** at 479 and **≤ normal** at 481; missing probability undecided at 461-462. No numeric thresholds printed. The prose is the prescribed normal finite-probability decision rule, not a new claim about invalid-input handling. |

No invented number or new contradiction with §9 or the inspected code found. The existing 0↔0.98 illustration, prior, sojourn, W and α all occur in §9. The obsolete report word “calibrating” is deliberately not revived; P2 explicitly corrected that wording and P4 preserves the correction.

## Findings

**None.** No blocker, should-fix, or style-preference nit is being proposed. Existing P2 accepted debt (e.g. explicit null-threshold zero-line behavior and hidden-tab resize limitation) is not introduced by this display-only diff and is not reopened here.

## Disposition rationale and limits

**Accepted, advisory:** the change implements the precise workcard contract, preserves the P2 surfaces, passes required targeted tests plus independent browser checks, and the actual images demonstrate readable math and fallbacks at both requested widths. Failure recovery and late loading were exercised directly rather than inferred from source. Product files remained read-only throughout RV review.

This is **local proxy proof using current assets plus the running API**, not deployed-image proof. It does not authorize an image build/rollout, bypass P3's 24-hour promotion constraint, or replace the Supervisor's later deployed-browser acceptance. Only RV's own 8092 proxy was stopped at completion. Scratch artifacts remain under `/tmp/solo-ops-p4-rv/`; the durable visual evidence is linked above.
