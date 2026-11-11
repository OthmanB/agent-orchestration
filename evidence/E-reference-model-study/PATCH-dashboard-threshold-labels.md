# D-C patch note — dashboard probability-threshold label relabelling

**Leaf:** D-C (operator-owned, low priority; R prepares, operator applies). **Author:** RefmRDC (research role).
**Prepared:** 2026-11-10. **Source pin:** `pipelineml-anomaly-detector` @ `5bcc7f9` (`5bcc7f9128d55e38d3c09838b3af0699edc4973b`, "docs(deploy): repin solo-card6 image to 50cdf54 digest b12ba06b").
`git rev-parse HEAD:analyser/dashboard_assets/index.html` = `d8253970ce9285daddf8ebadab8f4cf1a1adfe9d` (the blob the diffs below are cut against). Working tree of that file is clean (= HEAD).
**No file of the production repo was modified by this leaf.** Only `git apply --check` (read-only dry run) was run there.

Vocabulary (operator **D-A**, binding): `p_raw = P(anomaly | evidence)`; `< 0.2` = decisively normal; `0.2 … 0.8` = undecidable; `> 0.8` = decisively anomalous. 0.2 is **not** a warning level.

---

## 1. What the two dashed lines actually are (source evidence)

| Fact | Evidence |
|---|---|
| The 0.2 dashed line is `thresholds.normal_threshold`; the 0.8 dashed line is `thresholds.anomaly_threshold` | `analyser/dashboard_assets/index.html:2071-2072` (`thresholds?.normal_threshold` / `thresholds?.anomaly_threshold`) |
| Both values come from the API payload, not from constants in the page | `index.html:3282` → `renderTimeseries(points, payload.thresholds?.probability || {})`; payload built at `analyser/dashboard_routes.py:557,603` from `roles.main.inference.{normal_threshold,anomaly_threshold}` (0.2 / 0.8) |
| The same two `CHART_LEGEND_LABELS` strings name the plotly traces, so they also appear in the chart's own hover/legend UI (not only the static HTML legend) | `index.html:2089` (`name: CHART_LEGEND_LABELS.warningThreshold`), `index.html:2105` (`name: CHART_LEGEND_LABELS.criticalThreshold`) |
| Nothing in the detector *backend* emits the words "Warning Threshold"/"Critical Threshold" (config keys are `normal_threshold`/`anomaly_threshold`) | repo-wide grep, see §6 |

Conclusion: the two labels are a pure **presentation** string pair; the values 0.2/0.8 are untouched by this patch (as required: the operator's thresholds do not change).

---

## 2. Every site in `analyser/dashboard_assets/` that names the 0.2 / 0.8 lines (OBSERVED)

`baseline.html`, `history.html`, `shared_selectors.js`, `vendor/` contain **no** probability-threshold legends: `baseline.html`'s legend is Observed / Fitted / Residual / Zero / Empirical / Theoretical-H0 (`baseline.html:698-703`); `history.html` only has the event-type names including `threshold_configuration_changed` (`history.html:445,448`); `shared_selectors.js` only carries alert-state vocabulary (§3).

**In scope — changed by Patch A (4 strings, 1 file):**

| # | Location | Old text | New text |
|---|---|---|---|
| 1 | `index.html:969` (static chart legend, swatch `.warning-threshold`) | `Warning Threshold` | `Decisive-normal boundary (0.2)` |
| 2 | `index.html:970` (static chart legend, swatch `.critical-threshold`) | `Critical Threshold` | `Decisive-anomaly boundary (0.8)` |
| 3 | `index.html:1315` (`CHART_LEGEND_LABELS.warningThreshold`, drives the plotly trace name) | `'Warning Threshold'` | `'Decisive-normal boundary (0.2)'` |
| 4 | `index.html:1316` (`CHART_LEGEND_LABELS.criticalThreshold`) | `'Critical Threshold'` | `'Decisive-anomaly boundary (0.8)'` |

**Deliberately NOT renamed (identifiers, not user-visible text):** CSS classes `--chart-warning`, `--chart-critical` (`index.html:26-27`), `.legend-swatch.warning-threshold` / `.legend-swatch.critical-threshold` (`index.html:770-783`), `CHART_COLORS.warning|critical` (`index.html:1309-1310`), and the JS local variables `warningThreshold` / `criticalThreshold` / `warningThresholdRaw` / `criticalThresholdRaw` (`index.html:2071-2078`) and the object keys `warningThreshold`/`criticalThreshold` (`index.html:1315-1316`). Renaming these changes no pixel and forces a large churn diff across CSS + trace construction; the campaign rule is a minimal, reviewable operator patch. [INFERENCE: operator's intent is the visible labels.]

**Completeness of the "every place" claim [OBSERVED]:** the timeline chart draws exactly two threshold traces and nothing else textual about the thresholds — `index.html:2083-2097` (0.2 dashed, `hoverinfo: 'skip'`) and `index.html:2099-2113` (0.8 dashed, `hoverinfo: 'skip'`); there are no plotly `shapes`/`annotations` keys anywhere in the page (grep: none), so after Patch A no rendered on-chart text says "Warning"/"Critical" for these lines. The guide's formula block (`index.html:1241`) calls them "normal threshold" / "anomaly threshold" — correct under D-A (0.8 *is* the significance line), so it stays.

**Related, probability-scale, but outside D-C's literal text — operator may want a second patch (NOT included in Patch A/B):**

| Location | Text | Why it is probability-scale | Recommendation |
|---|---|---|---|
| `index.html:940` | `Consecutive > warning:` (value `#above-warning-count`) | reads `current.alert_state.consecutive_above_warning` = count of consecutive ticks above the 0.2 line (`index.html:2169-2172`) | Low value to change: the field is **hard-coded to `None`** by the API (`analyser/dashboard_routes.py:4410-4411`), so this row renders `n/a` permanently. Proposed if the operator wants it: `Consecutive > decisive-normal boundary (0.2):` |
| `index.html:941` | `Consecutive > critical:` | same, 0.8 line (`dashboard_routes.py:4411`) | same (`Consecutive > decisive-anomaly boundary (0.8):`) |
| `index.html:972` | `Decision: undecided/warning` | decision classes, one of which (`warning`) is the legacy name of the detector's `undecided` state (mapped at `dashboard_routes.py:2736-2737`) | Leave: it is a **decision marker legend**, and the string covers both the current (`undecided`) and legacy (`warning`) payload vocabularies. Changing it alone would hide the legacy value. |

**Docs that use the old formulation (informational, not patched):** `markdown/2026-06-16-dashboard-parity-spec.md:643-644` ("consecutive count above warning threshold / critical threshold", §13.1 items 3-4 of the frozen Alert-State panel contract). It is a historical design record, not runtime text; editing frozen spec records is outside D-C. `markdown/2026-06-16-audit-6.0.4-threshold-usage.md`, `2026-06-16-workstream-6C-*`, `2026-10-09-solo-mode-config-schema.md`, `audit-2026-06-16.md` all use the config keys `normal_threshold`/`anomaly_threshold` — correct already, nothing to change. No `markdown/` file contains the literal strings "Warning Threshold"/"Critical Threshold" (verified by repo-wide grep, §6).

---

## 3. Left unchanged on purpose — legitimate status vocabulary (must NOT be relabelled)

These use "warning"/"critical" for *state*, never for the 0.2/0.8 probability lines.

| Location | Text | Why it stays |
|---|---|---|
| `index.html:875`, `880`; `baseline.html:610`, `615` | `Running - Warning`, `Running - Critical` (indicator-A filter checkboxes) | pod **running/alert-state** indicator classes, produced by `shared_selectors.js:300-304` from `indicator_a_state`; a different object (workload state), no probability scale |
| `shared_selectors.js:271,287-291,327-331,357-361` | `resolveIndicatorAState`, `normal|warning|critical|not_running|unknown` dot classes | status-badge machinery shared by all pages |
| `shared_selectors.js:24-25`, `867-868` | filter registry `warning: true`, `critical: true` | filter keys mirroring the state classes above |
| `index.html:449,345-346`; `baseline.html:389,300-301`; `history.html:214,339` | `.badge.critical`, `.dot-warning`, `.dot-critical`, `--critical` | CSS for error/warning **badges** (health/error severity), not threshold lines |
| `index.html:1490,1680,2188,2206,2220,2234,2404,2690-2693,3309,3326,3482` | `variant: 'critical'` / `'error'` | badge variants driven by runtime/freshness/coverage/model-availability state |
| `index.html:1257-1260` (Guide → `guide-status`, card at `index.html:1249-1276`) | Analysis State levels `healthy - calibrated`, `healthy - raw`, `degraded`, `error` | Analysis State taxonomy — explicitly out of scope (and it does not use "warning"/"critical") |
| `index.html:971-974` | decision-class legend `Decision: normal` / `undecided/warning` / `anomaly/critical` / `unknown/stale` | decision markers, see §2 note |
| `history.html:445,448` | `threshold_configuration_changed`, `confidence_threshold_crossing` | history **event-type** enum values (also server-side contract values) |
| `index.html:1270` | drift badge "beyond a healthy-reference distance threshold" | descriptive prose about the drift flag, unrelated to 0.2/0.8 |

---

## 4. Patch A — required relabelling (verified)

Apply from the repository root (`/Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector`):

```diff
diff --git a/analyser/dashboard_assets/index.html b/analyser/dashboard_assets/index.html
index d825397..60b8a93 100644
--- a/analyser/dashboard_assets/index.html
+++ b/analyser/dashboard_assets/index.html
@@ -966,8 +966,8 @@
                                 <div id="timeseries-chart"></div>
                                 <div id="chart-legend" class="chart-legend" aria-label="Chart legend">
                                     <span class="legend-item"><span class="legend-swatch probability"></span>Composite Anomaly Probability</span>
-                                    <span class="legend-item"><span class="legend-swatch warning-threshold"></span>Warning Threshold</span>
-                                    <span class="legend-item"><span class="legend-swatch critical-threshold"></span>Critical Threshold</span>
+                                    <span class="legend-item"><span class="legend-swatch warning-threshold"></span>Decisive-normal boundary (0.2)</span>
+                                    <span class="legend-item"><span class="legend-swatch critical-threshold"></span>Decisive-anomaly boundary (0.8)</span>
                                     <span class="legend-item"><span class="legend-swatch normal"></span>Decision: normal</span>
                                     <span class="legend-item"><span class="legend-swatch warning"></span>Decision: undecided/warning</span>
                                     <span class="legend-item"><span class="legend-swatch critical"></span>Decision: anomaly/critical</span>
@@ -1312,8 +1312,8 @@
         };
         const CHART_LEGEND_LABELS = {
             probabilitySeries: 'Composite Anomaly Probability',
-            warningThreshold: 'Warning Threshold',
-            criticalThreshold: 'Critical Threshold',
+            warningThreshold: 'Decisive-normal boundary (0.2)',
+            criticalThreshold: 'Decisive-anomaly boundary (0.8)',
         };
 
         function setBadgeVariant(element, text, variant) {
```

Effect: `1 file changed, 4 insertions(+), 4 deletions(-)`.

## 5. Patch B — optional: one-sentence H1 gloss (verified; independent of A)

Observed: no tooltip or guide text currently calls 0.2 a "warning" level — the timeline guide says "the normal / anomaly decision thresholds" (`index.html:1243`) and "decision thresholds" (`index.html:1240`). So Patch B is **not needed to fix a wrong claim**; the operator asked for a one-sentence H1 wording *if* such wording existed. Offered as a one-line clarification in the two places an operator actually reads (chart tooltip + timeline guide):

> **p_raw is P(anomaly | evidence): below 0.2 a tick is decisively normal, between 0.2 and 0.8 it is undecidable, above 0.8 it is decisively anomalous.**

```diff
diff --git a/analyser/dashboard_assets/index.html b/analyser/dashboard_assets/index.html
index d825397..2ed10fc 100644
--- a/analyser/dashboard_assets/index.html
+++ b/analyser/dashboard_assets/index.html
@@ -954,7 +954,7 @@
                                 <h3 style="margin: 0 0 8px;" class="tooltip-container" tabindex="0">
                                     <span>Probability and Decision Timeline</span>
                                     <span class="tooltip-dot" aria-hidden="true">i</span>
-                                    <span class="tooltip-text">Hover reports the active representation (probability), model family, decision, confidence, freshness, and fallback state for each point.</span>
+                                    <span class="tooltip-text">Hover reports the active representation (probability), model family, decision, confidence, freshness, and fallback state for each point. p<sub>raw</sub> is P(anomaly | evidence): a tick below 0.2 is decisively normal, between 0.2 and 0.8 undecidable, above 0.8 decisively anomalous.</span>
                                 </h3>
                                 <p class="muted" style="margin: 0 0 8px;">
                                     Last refreshed: <span id="chart-last-updated">Never</span>
@@ -1240,7 +1240,7 @@
                                     <p>Probability and Decision Timeline: p<sub>published</sub> per scored tick against the decision thresholds, with a marker per decision class. In solo mode it is driven from the solo tick history (the /solo payload), so hover shows model family, decision, confidence, freshness, and fallback state as recorded for the point — n/a where the solo record carries none.</p>
                                     <p class="formula"><span class="formula-line" data-tex="p_{\text{published}} = \mathrm{isotonic}(p_{\text{raw}})">p<sub>published</sub> = isotonic(p<sub>raw</sub>)</span><span class="formula-gloss">isotonic mapper fitted on the healthy-reference warm-up window</span><span class="formula-line" data-tex="p_{\text{published}} \ge \text{anomaly threshold} \Rightarrow \text{anomaly}">p<sub>published</sub> ≥ anomaly threshold ⇒ anomaly</span><span class="formula-gloss">thresholds are the dashed lines on the chart, read from the payload</span><span class="formula-line" data-tex="p_{\text{published}} \le \text{normal threshold} \Rightarrow \text{normal}">p<sub>published</sub> ≤ normal threshold ⇒ normal</span><span class="formula-line" data-tex="\text{otherwise (or } p_{\text{published}} \text{ missing)} \Rightarrow \text{undecided}">otherwise (or p<sub>published</sub> missing) ⇒ undecided</span></p>
                                     <h3>Norm</h3>
-                                    <p>Anomaly-norm: P(anomaly). Calm ⇒ ≈ 0; the dashed lines are the normal / anomaly decision thresholds.</p>
+                                    <p>Anomaly-norm: P(anomaly). Calm ⇒ ≈ 0; the dashed lines are the decisive-normal boundary (0.2) and the decisive-anomaly boundary (0.8). p<sub>raw</sub> is P(anomaly | evidence): below 0.2 a tick is decisively normal, between 0.2 and 0.8 it is undecidable, above 0.8 it is decisively anomalous.</p>
                                     <h3>A calm value looks like</h3>
                                     <p>p<sub>published</sub> line under the dashed normal-threshold line; markers all "normal".</p>
                                 </div>
```

Effect: `1 file changed, 2 insertions(+), 2 deletions(-)`. A and B touch disjoint hunks, so either order / either subset applies.

---

## 6. Tests and smoke scripts that assert the old strings — NONE (so no test edits in the diff)

Searched (OBSERVED, 2026-11-10):

* `grep -rniI "warning threshold\|critical threshold" .` in the repo (excluding `.git`, `.venv`, `.venv_test`) → the only hits are `index.html:969,970,1315,1316` plus `markdown/2026-06-16-dashboard-parity-spec.md:643-644`. **Zero hits under `analyser/tests/`.**
* `grep -rn "index.html" analyser/tests --include='*.py'` → `test_dashboard_overview.py:8`, `test_dashboard_system_health.py:8,18` (Playwright page loads), `test_static_bundle_contract.py:20,35,106` (temp fixtures). None reads the real `index.html`.
* `grep -rn "legend\|threshold" analyser/tests --include='*.py'` → text/visibility assertions only: `test_dashboard_overview.py:26` `expect(page.locator("#chart-legend")).to_be_visible()`; `test_dashboard_history_baseline.py:40` `#baseline-chart-legend` visible; `test_static_bundle_contract.py:73-84` asserts *baseline* legend strings (Observed Training Data / Fitted Model Overlay / Residual Series / Theoretical H0 Distribution) — untouched by this patch.
* No JS test harness exists (no `package.json` anywhere outside site-packages), no `*smoke*` script anywhere in the repo (`find . -maxdepth 2 -iname '*smoke*'` → empty), `validate_setup.sh` / `BUILD_COMMANDS.md` carry no dashboard-text assertions.
* Repo has no `docs/`/`instructions/`/`deploy/` file asserting these labels (only `instructions/2026-06-11/rollout-and-migration.md:146` referencing an external smoke-test document by path).

⇒ **The applied patch breaks no test.** If the operator wants a regression guard anyway, the minimal addition (not included, since it is not needed) would be two assertions in `analyser/tests/unit/test_static_bundle_contract.py` next to the existing legend test:

```python
def test_index_page_timeline_threshold_legend_labels():
    index_path = os.path.join(os.path.dirname(__file__), "../../dashboard_assets/index.html")
    with open(index_path, "r") as f:
        html = f.read()
    assert "Decisive-normal boundary (0.2)" in html
    assert "Decisive-anomaly boundary (0.8)" in html
    assert "Warning Threshold" not in html
    assert "Critical Threshold" not in html
```

Note (INFERENCE): such a test would pin the *hard-coded* numbers. See §8 risk.

---

## 7. How the patches were verified (transcript)

Scratch copy, deleted afterwards — the production repo was never written:

```
# 1. faithful copy of the tracked assets at HEAD 5bcc7f9
rm -rf /tmp/dc-patch && mkdir -p /tmp/dc-patch && cd /tmp/dc-patch && git init -q .
(cd /Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector && git archive HEAD analyser/dashboard_assets) | tar -x -C /tmp/dc-patch
git add -A && git commit -qm base            # index.html blob = d825397 (matches HEAD)

# 2. edits made on the copy, diffs generated
git diff > /tmp/dc-patch-A.diff              # 4 +/4 - , 2 hunks
git checkout -- . ; <Patch B edits> ; git diff > /tmp/dc-patch-B.diff   # 2 +/2 -, 2 hunks

# 3. verification
git checkout -- .
git apply --check -v /tmp/dc-patch-A.diff    -> "Checking patch analyser/dashboard_assets/index.html..." OK
git apply --check -v /tmp/dc-patch-B.diff    -> OK
git apply /tmp/dc-patch-A.diff && git apply --check /tmp/dc-patch-B.diff -> OK  (A then B compose)

# 4. read-only check against the real repository (no write)
cd .../pipelineml-anomaly-detector
git apply --check -v /tmp/dc-patch-A.diff    -> OK
git apply --check -v /tmp/dc-patch-B.diff    -> OK
git status --porcelain                        -> unchanged ( M AGENTS.md, ?? analyser/agent-orchestration/, ?? markdown/2026-11-06-solo-dashboard-operations-report.md — pre-existing, not ours)
# 5. re-verification of the diffs AS PASTED IN THIS FILE (byte-identical to the generated ones)
<the two diff blocks in the sections above, extracted verbatim>  -> /tmp/ext-1.diff, /tmp/ext-2.diff
git apply --check -v /tmp/ext-1.diff -> OK      # Patch A
git apply --check -v /tmp/ext-2.diff -> OK      # Patch B
git apply /tmp/ext-1.diff && git apply --check /tmp/ext-2.diff -> OK ; git diff --stat -> 8 ++++----
git checkout -- .
rm -rf /tmp/dc-patch /tmp/dc-patch-A.diff /tmp/dc-patch-B.diff /tmp/ext-1.diff /tmp/ext-2.diff   # scratch removed
```

## 8. Apply / verify instructions (operator)

1. In `/Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector`, on your feature branch (never push until you decide):
   `git apply --check -v <this-file-extracted>.diff && git apply -v <...>.diff` — or paste the hunk into the file by hand (4 lines, §2).
2. Verify: `git diff --stat` → `analyser/dashboard_assets/index.html | 8 ++++----`; `grep -c "Warning Threshold\|Critical Threshold" analyser/dashboard_assets/index.html` → `0`.
3. Optional local check: `pytest analyser/tests/unit/test_static_bundle_contract.py -q` (no assertion touches these strings; it must stay green).
4. **Deployment note (OBSERVED):** the assets are baked into the image — `analyser/Dockerfile:72` `COPY analyser .` — and the live solo Deployment pins a digest (`deploy/k8s/solo-card6/deployment.yaml:72` `...@sha256:b12ba06b…`). The relabelled legend therefore only appears on `/dashboard/` after a rebuild + digest repin + rollout; editing the file alone changes nothing in the running pod.
5. Nothing outside `analyser/dashboard_assets/index.html` needs to change: no backend, config, threshold, API payload or test is touched.

## 9. Risks / open points

* **Hard-coded numbers in label text** [INFERENCE]: the operator's requested strings embed `(0.2)` and `(0.8)`. If `roles.main.inference.{normal,anomaly}_threshold` is ever changed, the legend text would lie while the dashed lines stay truthful (they are read from the payload). Alternative, not applied: derive the label from the payload in `renderTimeseries`, e.g. `name: \`Decisive-normal boundary (${warningThreshold.toFixed(1)})\`` and set the static legend spans from the same values; that is a larger, stateful change and out of D-C's scope. Current config is 0.2/0.8 (`analyser/config/...` via `roles.main.inference`), and D-A keeps them fixed.
* **Static legend vs plotly legend duplication**: `index.html:968-974` (hand-written HTML legend) and the plotly trace names (`index.html:2089,2105`) are two independent surfaces; Patch A updates both, which is why it is 4 strings and not 2.
* `consecutive_above_*` rows in the Alert State panel remain `n/a` by construction (`dashboard_routes.py:4410-4411`); relabelling them (§2 third table) would be cosmetic only.
