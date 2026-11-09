# RV Review — SOLO-OPS-P3 revision 1

- Date: 2026-11-06
- Disposition: **accepted_with_findings** (advisory; S decides)
- Reviewed `solo-ops-P3-rev1.md` fully, E-P3.md Revision 1/R1.1–R1.6, revised source/tests/docs, and the round-one diff captured during RV-P3.
- **All three original findings are resolved. No remaining scoring blocker found.** One documentation should-fix below; no request to change the approved statistic, floor, mapper, or protected scoring laws.
- Read-only detector repo: no product edits/staging/commits, cluster/SSH/kubectl, service management, GPU work, or prohibited dashboard-route/browser tests. Scratch probes/data are under `/tmp/solo-p3-rv/rev1/`.

## Numbered findings

1. **SHOULD-FIX — qualify the claimed probability-rise guarantee; the guard does not constrain the mapper's empirical tail.** `markdown/2026-10-09-solo-mode-runtime-cutover.md:580-582` says floor 1.0 means a p_raw move of one π “may lift the published value by at most the normal threshold.” Read literally for the published mapper, that is stronger than the implemented bulk-only statistic. An independently tested, **accepted and real-tick-adopted** Gaussian fit (`default_rng(0).normal(.2,.02,144)`, held-out `[.2]*144`) has guard ratio **1.0933512728222932**, but its fitted mapper rises **.23234954768150917** across a raw interval of width .01 starting at **.23005**. Here x_(m)=**.23603269739732252**, so the interval crosses the empirical tail, which the approved guard intentionally does not inspect. This is **not a guard regression or a reason to weaken/change the tail law**. It is a factual limitation missing from the unqualified documentation claim. E's own fuzz result, accepted-fit maximum rise .246, likewise cannot establish an exact global .2 bound.
   **Concrete fix:** state the exact guarantee: no raw interval narrower than `floor*pi` contains k fit scores **within bulk ranks 1..m**; describe approximately normal-threshold-sized bulk rises, and explicitly exclude the intentionally full-resolution empirical tail from any global slope guarantee. Do not introduce another product gate or retune thresholds.

## 1. Revision scope, implementation, and original findings

`git diff --stat -- analyser/solo_mode analyser/exporter.py analyser/config deploy markdown analyser/tests` reports the same **16 contract files, +1599/-62**. For a true round-one-to-revision comparison, reconstructed the round-one Python files **in memory** from `git show HEAD:<file>` plus the already-reviewed complete unified diff (`artifact://1074`), checking context lines and parsing all reconstructed modules. Wrote readable deltas under `/tmp/solo-p3-rv/rev1/*.py.diff`.

- `fusion.py:397-407`: exactly `min(srt[k-1:m] - srt[:m-k+1])/prior`; m and k unchanged, same input validation, no other fusion function changed. A separate Python sorted-list/loop implementation—not NumPy slicing—matched on every directly checked adversary/live/wide fit. k=1 still yields zero. The first window is in the minimum, so **shorth ≤ round-one D1 pointwise**.
- Driver production behavior delta is restricted to the fit_count fallback and truthful retained/raw log; other driver changes are explanatory docstrings/comments and the guard warning. Gate ordering/arguments and gate-AND-guard adoption remain intact. No new timer/state/label/default; protected p_raw computation and laws remain outside the delta.
- `driver.py:1749-1755`: existing dict with fit_count uses its count; absent dict or absent key defaults from **persisted mapper presence**. Original #2 fixed. New `test_legacy_provenance_fit_count` drives fresh adopt=1, genuine 18-key legacy provenance adopt=2, next refit=3, absent provenance with mapper adopt=2 through actual ticks. Its provenance-present leg seeds healthy=True rather than the card's False, but the fallback is independent of that flag; the absent-provenance leg exercises False, and the original real-tick legacy count counterexample is no longer supported by the code.
- `driver.py:1794-1820,2004-2011`: retained condition equals publication condition; healthy rejected refit logs “keeping the healthy calibrated mapper,” unhealthy logs “publishing raw”; guard errors say “not adopting” and preserve current publication. `driver.py:1896-1904` and `state.py:673-685` correctly describe carried-forward health and complete failed-window stamping. Original #3 fixed.
- Original #1: both A and B now reject **with the held-out gate explicitly passing**, including actual tick publication/persistence (table below). A/B regression tests assert gate=True and guard=False before the real tick, then raw, p_pub==p_raw, healthy=False, mapper=None and stamped attempt. This isolates the guard rather than passing because another gate rejects.
- State revision changes only `complete_scored_tick`'s docstring; no SQL/migration/write-path behavior changes. Exporter, config validator, state tests, config tests and dashboard API tests are byte-identical to round one. Exporter-test delta is wording only. AST assertion-multiset comparison on all changed Python files found **zero round-one assertions removed/loosened**.
- Both YAMLs still have `min_calm_span_ratio: 1.0`; only the common-YAML comment changes in revision. ConfigMap **ttl 900 / degraded 11.0 / stale 13.0** retained. Thresholds remain read-only rank inputs. Runtime/schema docs describe the new min-window formula; first-window references are contrast/history, not the active statistic.

## 2. Independent real-tick adversarial checks

Command, from `analyser`:
```sh
env PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared PYTHONDONTWRITEBYTECODE=1 /tmp/solo-p3-venv/bin/python -B /tmp/solo-p3-rv/rev1/probe.py
```

The probe seeds production-sized **288-value histories** at exact T spacing with `_seed_p_raw`, then invokes actual `_drive` → `handle_solo_request`; default n_bins=48, fit n=144, τ=.02, π=.01, thresholds .2/.8, floor 1.0. It independently computes the min-window ratio with sorted Python lists, checks the real gate, asserts persisted health/label agrees with gate AND guard, attempt stamped, and p_pub==p_raw for every rejection. **43 real-tick cases completed successfully**, including all ten fresh GET windows. The command then exited 1 because its broad input glob additionally tried `/pods/summary/solo` from `solo_summary.json` and got HTTP 404; this was **after all ten requested pod GETs and all 43 cases**, not a product failure. Narrowed only that scratch glob afterward; did not rerun already successful cases or claim a clean initial command exit. Ten GET reductions and all case SQLite files persist under the scratch directory.

| Case | Independent shorth ratio | Gate | Real-tick result / judgement |
|---|---:|---|---|
| RV-A: low outlier + 143-point pile | **.0147887324** | True | **raw**, healthy=False; original blocker closed |
| RV-B: broad lower 36 + narrow upper 108 | **.0196261682** | True | **raw**, healthy=False; original blocker closed |
| RV-B twice wider lower tail | **.0196261682** | True | **raw**, healthy=False |
| Calm pile + 1, 2, 3, 4 spikes @.98 | **.0119332157** each | True each | **raw** in all four; contamination still rejected |
| Noisy U(.005,.075) fit + 10 .98 anomalies; anomalies also held-out | **1.3122562794** | False | raw: spread passes guard, existing gate rejects genuine held-out episode |
| Same noisy fit; anomaly-free held-out [.005,.065] | **1.3122562794** | True | **calibrated**, healthy=True; sensible approved healthy-window assumption |
| Wide U(0,.95), seeds 0/1/2/42/123; clean U(0,.5) held | **17.30335 / 18.86257 / 18.59176 / 17.73760 / 15.02185** | True all | **calibrated** all five; genuine wide acceptance retained |
| Two 35-point clusters, .04 apart, remaining 74 points wide | **4.0** | True | calibrated; known <k staircase limit |
| Three 35-point clusters, .04 apart, remaining 39 points wide | **4.0** | True | calibrated; same known limit |
| Five 28-point clusters, .04 apart, four wide tail points | **4.0051851852** | True | calibrated; same known limit |
| Two large tight 72-point clusters | **.0295774648** | True | **raw**; each cluster contains ≥k |
| Three large tight 48-point clusters | **.0446808511** | True | **raw**; each cluster contains ≥k |
| Smooth ramp [.02,.0302] (total width 1.02π) | **.2496503497** | True | **raw**; correctly insufficient width per k-window, not just total span |
| Bimodal 100-point calm + 44-point elevated pile | **.0212121212** | True | **raw** |
| Calm pile + 25% uniformly spread contamination | **.0147538602** | True | **raw** |
| Exponential post-burst decay + 36/72/108 calm pile ticks | **.0600 / .0295774648 / .0196261682** | True all | **raw** in all three; realistic decay + quiet mass not falsely certified |

Two/three <36-point clusters cannot themselves fill a 144-value fit; the wide remainder above preserves the requested production n. The accepted staircases have local mapped rises ≈**.1828 / .1828 / .1425** per raw π in these examples, not a live-style 0→.8 jump over a .0006 pile. Acceptance is exactly the card's explicitly acknowledged <k-cluster limit, **not a newly concealed blocker**. Larger concentrated clusters are rejected. No realistic live-flat pile, post-burst-pile window or clearly wide noisy baseline tested was wrongly adopted/rejected by the approved property.

### Gaussian/noisy-window boundary

Independently sampled 300 anomaly-free fit windows per σ, `default_rng(seed).normal(.2,σ,144)` (mean .2 avoids clipping; the statistic is translation-invariant). Clean held-out `[.2]*144` isolates the guard from unrelated held-out sampling failures. Ran an actual tick for a passing and failing sample when both existed:

| σ | Guard passes /300 | Ratio min / median / max | Actual-tick samples |
|---|---:|---|---|
| 1π=.01 | **0** | .3550 / .5175 / .7161 | seed-0 raw, ratio .546676 |
| 1.5π=.015 | **1** | .5325 / .7763 / 1.0742 | pass calibrated at 1.074155; seed-0 raw at .820013 |
| 2π=.02 | **177 (59%)** | .7101 / 1.0350 / 1.4322 | seed-0 calibrated at 1.093351; failing sample raw at .888212 |
| 3π=.03 | **300** | 1.0651 / 1.5526 / 2.1483 | seed-0 calibrated at 1.640027 |
| 4π=.04 | **300** | 1.4201 / 2.0701 / 2.8644 | seed-0 calibrated at 2.186703 |
| 5π=.05 | **300** | 1.7751 / 2.5876 / 3.5805 | seed-0 calibrated at 2.733378 |

Thus the statistic **does reject some genuinely anomaly-free noisy windows**, especially σ≤2π; it is a conditioning criterion, not a health classifier. The σ=2π boundary reproduces the card's explicit **59% pass** caveat. σ=3–5π consistently passes here. Do not claim all anomaly-free windows should adopt; this conservatism is approved and the unhealthy path retries each valid tick. No added tuning requested.

## 3. Ten freshly fetched live windows

Read-only GETs of `http://127.0.0.1:18086/api/dashboard/pods/<full-pod-name>/solo?namespace=ml-components&cluster=` for the ten identities discovered in the saved live-window filenames, not cluster access. Each response had **288 p_raw rows**, epochs **1793890200–1793976300**. Reduced JSON files saved as `/tmp/solo-p3-rv/rev1/live-<suffix>.json`.

| Pod suffix | Independent ratio | Gate | Real tick |
|---|---:|---|---|
| b4xkt | 1.6023619064e-11 | True | raw / healthy=False |
| mjnlq | 0 | True | raw / healthy=False |
| rzpzm | 2.8044932956e-08 | True | raw / healthy=False |
| hcfj7 | 1.0638980755e-08 | True | raw / healthy=False |
| vlsl8 | 1.7629315976e-10 | True | raw / healthy=False |
| 2vwwd | 3.2526065175e-16 | True | raw / healthy=False |
| 7gjdg | 7.7740236492e-08 | True | raw / healthy=False |
| c5bdh | 2.7278973676e-08 | True | raw / healthy=False |
| m7pr8 | 1.1873993644e-06 | True | raw / healthy=False |
| qsv2m | 6.3056114150e-12 | True | raw / healthy=False |

All ten real ticks asserted p_pub==p_raw. **The gate now passes on these later live histories**, unlike the older E demo snapshots; this is chronological window movement, not altered gate semantics. The guard independently prevents adoption in all ten, including this gate-passing regime.

## 4. Verification commands and results

From `analyser`, env as above, ran the exact card fast selection (only read-only-friendly pytest flags added):
```sh
/tmp/solo-p3-venv/bin/python -B -m pytest -p no:cacheprovider tests/unit/test_solo_fusion.py tests/unit/test_solo_state.py tests/unit/test_solo_window_store.py tests/unit/test_solo_driver.py tests/unit/test_solo_exporter.py tests/unit/test_solo_mode_config.py tests/unit/test_split_config_loader.py tests/unit/test_config_validation.py tests/unit/test_solo_throughput.py tests/unit/test_solo_diagnostics.py tests/unit/test_solo_scan.py tests/unit/test_solo_noise.py tests/unit/test_solo_fresh_api.py tests/unit/test_solo_baseline.py tests/unit/test_solo_mlflow_absence.py tests/unit/test_dashboard_api_routes.py tests/unit/test_exporter.py tests/integration/test_canonical_route_contracts.py tests/unit/test_solo_scenarios.py -m 'not slow' -q
```
**Exit 0: 574 passed, 0 failed, 20 deselected in 99.41 s**, matches E. Raw output `artifact://1157`.

Targeted new regressions:
```sh
/tmp/solo-p3-venv/bin/python -B -m pytest -p no:cacheprovider tests/unit/test_solo_fusion.py tests/unit/test_solo_driver.py -k 'single_low_outlier or broad_lower_tail or n2_is_zero or never_exceeds_first_window or legacy_provenance_fit_count or retained_healthy_failed_refit_logs_keep_not_raw' -q
```
**Exit 0: 8 passed, 71 deselected in 1.49 s**. Read all eight new tests, including the complete log assertions. These drive real ticks/persisted outputs where relevant; no mocked adoption or weakened old assertion was substituted. Existing affine adoption/exporter restore tests remain in the passing fast command.

`bounds.py` under the same scratch directory, run with the same venv/env, **exit 0**, independently examined the fitted mapper rise for finding #1. It also restricted checks to intervals wholly below x_(m); no >.201 bulk-only counterexample was found among 500 σ=.02 seeds. The demonstrated >.2 rise crosses the intentionally unguarded tail; do not mislabel it a bulk guard failure. An initial attempt to import NumPy in the host Eval Python failed because that interpreter lacks NumPy; all numerical/tick execution used the supplied venv afterward, without installing packages.

## 5. Slow-scenario reconciliation

Read E's six revision logs and compared `gate=True guard_ok=False` counts to the corresponding original logs by independent text aggregation:

| Param | Round one | Revision 1 |
|---|---:|---:|
| 20261012-healthy | 88 | 88 |
| 20261012-one_metric | 119 | 119 |
| 20261013-group3 | 43 | 43 |
| 20261014-healthy | 152 | 152 |
| 20261014-one_metric | 84 | 84 |
| 20261015-group3 | 31 | 31 |

All six retain never-committed/no-healthy-mapper outcomes; retained-healthy log count is zero in every log. **E's identical-count claim is plausible and supported by the files.** No additional RV slow run was required/requested for this narrow re-review; round-one RV independently paired the representative baseline/P3 parameter already.

The exact reasoning is stronger than “a stricter guard always preserves test verdicts” in arbitrary stateful systems: in **these twenty fixtures**, round one adopted **zero** maps, raw computation is unchanged, and every round-one guard rejection remains rejected because shorth≤D1. Therefore the raw trajectories remain the same and no previously absent adoption can arise; no slow fixture can newly adopt or lose a previously held mapper. Some windows that already failed the held-out gate could change guard-only True→False, but that cannot change an adoption/publication. No baseline-pass params existed in the earlier reconciliation. The unchanged six observed counts and original all-twenty no-adoption evidence support carrying forward the slow failure classification; no fixture/YAML/guard weakening is justified.

## Disposition rationale

Accept the revised mechanism subject to the advisory documentation correction. Independent real ticks close A/B, contamination and decay pile cases reject, wide windows and clearly broad Gaussian/noisy windows adopt, all ten fresh gate-passing live windows remain raw, and fit_count/log/comment repairs are covered by real regression tests. The accepted <k staircase and σ≈2π conservative boundary are now explicit limits rather than hidden failures. The only remaining finding is an overstatement of a global published-probability bound in documentation; it does not call for another scoring change. Offline review still does not replace S's rollout/restart smoke or ≥24-hour live acceptance window.
