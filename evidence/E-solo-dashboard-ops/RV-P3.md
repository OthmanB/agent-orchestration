# RV Review — SOLO-OPS-P3

- Date: 2026-11-06
- Disposition: **rejected** (advisory; Supervisor decides)
- Reviewed uncommitted P3 against HEAD `eadd2e3`, the complete workcard including S DECISION D1–D3/RV checklist, E-P3, R-P3, vision §3-P3/§5/§7, supervisor hard stops, and reviewer mandate.
- No detector-repo source/config/doc edits, staging, commits, cluster/SSH/kubectl operations, or service changes. Only this requested report and scratch files under `/tmp/solo-p3-rv` were written by RV. Tests used `-B`, `PYTHONDONTWRITEBYTECODE=1`, and `-p no:cacheprovider`.

## Numbered findings

1. **BLOCKER — a degenerate pile can still be adopted; D1 needs a Supervisor decision.** `analyser/solo_mode/fusion.py:383-389`, consumed at `analyser/solo_mode/driver.py:1722-1728`.
   The implementation exactly follows approved D1, but subtracting the absolute minimum makes the statistic sensitive to a single *low* outlier. With shipped n=144, π=.01, τ=.02, thresholds .2/.8, floor=1, n_bins=48:
   ```python
   fit = [0.0013] + list(np.linspace(0.0115, 0.0121, 143))
   held = [0.0117] * 144
   ```
   Independent ratio = **1.0343661971830984**, guard=True, existing held-out gate=True. A **real `handle_solo_request` tick** over this seeded 288-value history adopted the mapper, persisted `mapper_healthy=True`, and published `calibrated`. The fitted map sends calm `.0117` to **.2799054373522459** (warning), even though 143/144 fit values lie in a raw band only .0006 wide. The real driven current tick had p_raw=.16865590704431763 and was mapped to 1.0. A second required adversarial case, `fit=linspace(.0013,.01141,36) + linspace(.01142,.01202,108)`, `held=[.0117]*144`, also adopted on a real tick: ratio **1.011**, map(.0117)=**.4932387706855807**. Its broad lower quartile conceals a narrow three-quarter pile. This is the motivating ill-conditioning shape in another location, not a protected-law or threshold change.
   **Concrete action:** escalate this counterexample to S before rollout; amend/approve D1 so an isolated low point or broad lower tail cannot certify a narrow calm bulk as healthy, and add both real-tick regressions. Do not silently retune the YAML floor or any protected threshold/statistical law. RV is not substituting a new architecture for the approved one.

2. **SHOULD-FIX — migrated provenance undercounts the legacy fit.** `analyser/solo_mode/driver.py:1743-1748`.
   A pre-P3 mapper normally has the existing 18-key provenance dict, but no `fit_count`. The non-None branch uses `.get("fit_count", 0)`, so the first P3 adopt records **1**, not the contract's **2** (legacy persisted mapper is fit #1). The fallback to 1 only runs when the *entire provenance object* is absent. Independently reproduced through a real tick using an existing mapper and its genuine 18-key provenance with only the two P3 keys removed.
   **Fix:** default a missing `fit_count` key to `1 if previous_mapper_persisted else 0`, whether provenance is absent or present; then increment. Add a legacy-with-provenance adoption assertion and a subsequent refit increment assertion.

3. **SHOULD-FIX — rejected healthy refits falsely log raw publication, and new comments contradict carry-forward.** `analyser/solo_mode/driver.py:1788-1797`, `:1874-1877`; `analyser/solo_mode/state.py:673-680`.
   The never-demote path works, but a real healthy-mapper/degenerate-window tick returned `probability_label='calibrated'` while logging `gate=True guard_ok=False ... publishing raw.` The warning helper at driver `:1977` has the same unconditional claim. This is operationally false for a healthy mapper retained after a failed refit. In addition, “mapper_healthy=True only on an adopt” is false on every retained healthy tick, and state `:679-680` says a “failed/incomplete window never stamps” although a complete gate/guard-failing window correctly *does* stamp the attempt.
   **Fix:** log retained calibrated publication vs raw according to the actual held mapper/state, and describe health as a carried-forward flag set True on adopt; distinguish complete rejected windows (stamp) from incomplete windows (do not stamp). No new logging surface/counter is needed.

## Checks performed and results

### 1. Scope / protected laws — PASS

Commands: `git status --short`; `git diff -- analyser/solo_mode analyser/exporter.py analyser/config deploy markdown analyser/tests` from the detector repo. Read the full raw diff (including the portions elided by the initial diff renderer) and `/tmp/solo-p3-e/git-before.txt`.

The scoped diff is exactly **16 contract files**: the four solo modules, exporter, two YAMLs, six named test files, three existing docs; +1188/-62. Unrelated status entries (`AGENTS.md`, P4 index/vendor, `analyser/agent-orchestration/`, and untracked `markdown/2026-11-06-solo-dashboard-operations-report.md`) already appear in E's before snapshot and were ignored. The whole worktree is not falsely represented as containing only P3.

`p_raw`, Simes, strikes, Markov/sojourn/prior, ESS, α_strike/α_fuse, and .2/.8 values are untouched. No P3 changes to `dashboard_routes.py`, `_solo_analysis_state`, `_pipeline_status_payload`, or dashboard JS. Independent AST comparison found **all pre-existing fusion functions unchanged** (only `calm_span_ratio` added); only `handle_solo_request` changes among existing driver function ASTs, and **every statement before calibration-row loading is unchanged**, including p_raw computation and threshold retrieval. The guard merely **READS thresholds** to choose k; it does not alter the decision thresholds or their laws.

Exporter changes are X1 only: the `scored = calibrated or cal_state_str == "scored"` local/comment and the two inventory `status` expressions (`exporter.py:2421,2430,2456`). No restore/cleanup/canonical-gating edits.

### 2. Guard / YAML / live and adversarial recomputation — formula PASS; robustness FAIL (#1)

Read `fusion.py:333-389`, `driver.py:1716-1728,1944-2011`, `config.py:739-748`, both YAML diffs. Formula is `(x[k-1]-x[0])/π`, m=`calibration_order_index(n,τ)`, k=`max(1,ceil(m*normal/anomaly))`; at n=144, m=141, k=36. Gate runs first with its original arguments and short-circuited `len(held_out)>=2`; adoption requires **gate AND guard**, not a replacement/weakened gate. `ValueError` returns `(False,None)` with warning (independently exercised with NaN fit input). Affine `slope_intercept` bypass returns `(True,None)` (independently exercised); both shipped affine adoption tests still pass individually.

Floor is required YAML, no code default. The individual config test passed: absent mapping, non-mapping, absent leaf, 0, negative, True, and string all raise `ConfigurationError`; positive values pass. Both YAMLs contain 1.0. ConfigMap still has **ttl=900 / degraded=11.0 / stale=13.0** at `:98,:171-172`.

Read-only native GET, then programmatic JSON reduction, of:
- `http://127.0.0.1:18086/api/dashboard/pods/pipelineml-tester-workload-checkout-api-v1-55d59c5477-b4xkt/solo?namespace=ml-components&cluster=`
- same route for suffix `mjnlq`.

Both returned 288 chronological `history[].p_raw` values, epochs **1793886300–1793972400**. An independent Python `sorted`/`floor`/`ceil` calculation matched the implementation (not a self-comparison): b4xkt ratio **1.6023619063554317e-11**, mjnlq **0**, both gate=False/guard=False. On E's saved windows the same calculation gives b4xkt **9.385990248911291e-11**, mjnlq **0**, consistent with E demo's printed 0.0000 (the newly fetched window is later). The seeded RNG-0 wide window from E's demo independently yields **27.131264399555803**, gate=True, and a real tick adopts healthy/calibrated; matches `/tmp/solo-p3-e/demo.out` **27.131**.

Adversarial results (same shipped constants):

| fit / held-out | ratio | gate | decision / judgement |
|---|---:|---|---|
| calm U(.0013,.0019) + 1,2,3,4 spikes at .98; clean held | .0153138–.0153645 | True | reject in all four; sensible |
| broad bottom 36 values then narrow upper 108-value pile; constant .0117 held | 1.011 | True | **real-tick adopt, calm maps .49324; blocker** |
| one low .0013 plus 143-value narrow pile [.0115,.0121]; constant .0117 held | 1.03437 | True | **real-tick adopt, calm maps .27991; blocker** |
| noisy genuine baseline U(.005,.075), 10 .98 anomalies in each half | 1.90348 | False | guard accepts actual baseline spread; held-out gate properly rejects anomaly episode |
| same noisy fit, anomaly-free held-out [.005,.065] | 1.90348 | True | accept; approved healthy-window assumption, not a degenerate pile |

The broad-bottom-quartile case with held-out values extending through the fitted upper tail rejects on the held-out gate; narrowing held-out to calm .0117 exposes that this rejection is not protection from the guard.

Commands: `env PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared PYTHONDONTWRITEBYTECODE=1 /tmp/solo-p3-venv/bin/python -B /tmp/solo-p3-rv/probe.py` and the analogous `edges.py` command; both exited 0. These are independent scratch probes, not product edits. E's saved sliding demonstration reports 0/10 new-guard adoptions vs 10/10 old-statistic adoptions; RV read its source/output, but did not repeat all 4,010 sliding windows.

### 3. State machine / edges — PASS except #2/#3

Read driver `:1647-1805,1880-1899` and the early dedupe `:1440-1462`. No healthy mapper ⇒ evaluate each valid tick; healthy ⇒ attempt age ≥ L_cal*T, or absent attempt; no new timer. Only a complete contiguous prior history stamps an attempt, so prior-L_cal/adopt-at-L_cal+1 timing is unchanged. No-adopt preserves state, mapper, healthy flag, provenance; only a complete evaluated window advances attempt time. Publication requires scored + mapper + healthy; labels remain {raw,calibrated}, calibration_state remains the row's state.

`test_healthy_mapper_kept_across_degenerate_window` (`test_solo_driver.py:1287-1346`) genuinely seeds a healthy row, drives an earlier real tick, supplies a later degenerate due window, then drives another **real** tick and checks same mapper/provenance, healthy=True, calibrated label, and advanced attempt. It is not a mocked guard assertion. Both pacing tests also drive real ticks. My separate edge probe reproduced retention with gate=True/guard=False; a healthy row with attempt equal to tick_end did not refit. An incomplete window preserved an old attempt **123** and published raw/scored.

Absent row ⇒ False/None; absent columns ⇒ migration creates them; nullable health (if supplied by a nonstandard older table) is decoded with `bool(None)==False`; normal P3 DDL forbids NULL. Persisted mapper with absent/false health stays inert unless newly adopted. Healthy row with absent attempt is immediately eligible, but an incomplete window cannot stamp it. Held-out <2 cannot adopt and is already prohibited by load-time L_cal≥4 validation.

Independent fresh-store restart/dedupe probes covered **raw/scored** and **calibrated/scored** persisted details. Replaying the same tick hits the early return, does **not** re-run refit or re-stamp attempts, and preserves calibration row/provenance. A restart may replay an old pre-rollout calibrated tick until the first new scored tick; this is the card's explicit accepted transition.

AST comparison verified the previous **18 provenance key/value expressions unchanged**; only `fit_count`/`calm_span_ratio` were added. Fresh adoption count=1 is tested; legacy-with-existing-provenance count is broken as #2 describes.

### 4. Migration / callers — PASS

`probe.py` executed the **actual PRE-change state module** obtained by `git show HEAD:analyser/solo_mode/state.py`, used its `SoloStateStore` to create `/tmp/solo-p3-rv/actual-head-legacy.sqlite` and ten scored mapper/provenance rows, closed it, then opened with P3. Observed exactly two warnings, one each for `mapper_healthy` and `last_fit_attempt_epoch`; all ten read **False/None** with old mapper/provenance intact. PRAGMA confirmed `mapper_healthy INTEGER NOT NULL DEFAULT 0`, nullable REAL attempt. Reopen produced **zero** ALTER warnings; reads unchanged. Extended shipped migration test also passed individually.

`grep complete_scored_tick\( analyser/` found **one driver caller + 15 test callers**, none in scenarios harness. AST inspection confirms driver passes both required keywords; tests pass them explicitly or through updated `_base_complete_kwargs`. Signature at `state.py:626-646` is keyword-only with **no defaults** for the two new fields. Existing atomic rollback/details tests remain green. Fresh DDL and per-column migration both match the contract. By schema semantics, all **ten deployed pre-P3 rows** will read 0 on the first new-image open; no cluster access was needed to infer this.

### 5. Exporter X1 / restore / dashboard — PASS

`exporter.py:2233-2235` remains label-driven: canonical children only for available `calibrated` details. Raw/scored now gets inventory scored; raw/calibrating still gets warming. `_solo_cleanup_stale:2889-2897` is unchanged and explicitly excludes valid fraction-only raw pods from lost-canonical eligibility cleanup.

Read and individually ran `test_solo_raw_scored_pod_fraction_only_and_restores_raw` (`test_solo_exporter.py:826-933`): actual exporter polls persist ≥2 raw/scored ticks, assert p_pub==p_raw, raw/scored/calibrated=False snapshot, scored inventory, fraction child present, both canonical label variants absent; a fresh exporter restores identical raw/scored outputs with no canonical child. Individual `test_solo_repeated_poll_and_restart_dedupe` passed, including the unchanged warming assertions now at **1126/1212/1279** (formerly 1015/1101/1168).

The new fixture-backed route test at `test_dashboard_api_routes.py:2240-2261` invokes the actual `/api/dashboard/pods` route and asserts **alert_state.state=normal, indicator_a_state=normal, pipeline_state=active, analysis_state=degraded**, plus raw probability, running, scoreable. It passed individually. No helper/UI rewrite was used to force the result.

### 6. Fast suite / targeted quality / assertion preservation — PASS

From `analyser`, with `PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared`, `PYTHONDONTWRITEBYTECODE=1`, `PY=/tmp/solo-p3-venv/bin/python`, ran:
```sh
$PY -B -m pytest -p no:cacheprovider tests/unit/test_solo_fusion.py tests/unit/test_solo_state.py tests/unit/test_solo_window_store.py tests/unit/test_solo_driver.py tests/unit/test_solo_exporter.py tests/unit/test_solo_mode_config.py tests/unit/test_split_config_loader.py tests/unit/test_config_validation.py tests/unit/test_solo_throughput.py tests/unit/test_solo_diagnostics.py tests/unit/test_solo_scan.py tests/unit/test_solo_noise.py tests/unit/test_solo_fresh_api.py tests/unit/test_solo_baseline.py tests/unit/test_solo_mlflow_absence.py tests/unit/test_dashboard_api_routes.py tests/unit/test_exporter.py tests/integration/test_canonical_route_contracts.py tests/unit/test_solo_scenarios.py -m 'not slow' -q
```
Result: **566 passed, 0 failed, 20 deselected in 107.32 s**, matching E's counts. Log `/tmp/solo-p3-rv/fast.log`. No whole unit-directory run, dashboard-route evidence-rewriting test, static bundle/browser tests, or live GPU work.

Also ran `/tmp/solo-p3-rv/targets.py`: **16 separate pytest commands**, each selecting one node and each exit 0/1 passed: three new fusion tests; six new driver tests; the two shipped affine adoption tests; raw/scored exporter restore; existing repeated-poll/restore; new config validation; extended migration; new dashboard API test. Exact command/node and individual output are retained in that launcher and `/tmp/solo-p3-rv/<test_name>.log`.

New driver tests use real `_drive`→`handle_solo_request` and persisted state, exporter tests real polls, API test a real route over a deliberately fixture-backed exporter. `_seed_p_raw` uses `append_scored_tick`, **not `complete_scored_tick`** as the card suggested, but correctly seeds history at **start=tick_end-L_cal*T, step=T, last=tick_end-T**, and does not pre-decide calibration state. This is a valid isolated history seam, not a tautological adoption mock. It seeds the strike ring for scorable ticks. One test's prose says ≥4 spikes while its six-value fit actually has **3**; the separate fusion test and my probes cover 4, so this does not explain away #1.

No existing assertion was removed or loosened: AST assertion-multiset comparison against HEAD found old assertions all retained (routes 408→417; driver 583→642; exporter 322→345; fusion 94→98; config 48→48 plus new raises cases; state 146→166). The two affine tests are unchanged rather than gaining the requested direct mapper_healthy assertion; their calibrated-publication assertions nevertheless exercise the now-health-gated adoption path. Missing low-outlier and legacy-with-provenance regressions are the substantive coverage gaps behind #1/#2.

### 7. Slow scenarios — recorded failures are not a reason to weaken the guard

Read E's complete table and all 20 P3 log final verdicts, all 15 non-exempt baseline log verdicts (`/tmp/solo-p3-e/base/*.log` plus `base-check/20261013-one_metric.log`), and the three available R-P3 baseline logs. The other two exempt healthy baseline failures are established in the binding card/R-P3 evidence, not independently rerun here. Checked SHA-256 equality to `git show HEAD:<path>` for the baseline copy's state, driver, fusion, scenario synth and scenario-test modules: all match pristine HEAD.

Independent aggregation of E's logs confirms **1062 gate=True/guard=False** rejections, max ratio **.267734**, across 20 failing P3 params; no observed genuinely wide (ratio≥1) gate-passing window was wrongly rejected. The approved machine naturally converts late-committed **pile** cases to never-committed cases. That is guard-by-design, not an unintended scoring-law regression. All 15 newly reconciled baseline params also fail; the five card-exempt failures remain pre-existing. Therefore the table establishes **no baseline-pass→P3-fail param**, not proof that the guard is generally robust (finding #1 is independent).

Nuance: the healthy-param logs are not uniformly a clean top-level `fixture_unscorable` exception: the fresh producer asserts calibrating != scored, then pre-existing `_fail` NameError masks it. The underlying no-commit outcome is visible. This is pre-existing harness debt, not a P3 fix request.

RV additionally launched the *same* representative `20261014-healthy` parameter on P3 and pristine baseline concurrently (two slow processes maximum), using:
```sh
# cwd=<detector repo>/analyser, then cwd=/tmp/solo-p3-base/analyser
env PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared PYTHONDONTWRITEBYTECODE=1 /tmp/solo-p3-venv/bin/python -B -m pytest -p no:cacheprovider 'tests/unit/test_solo_scenarios.py::test_run_scenario_slow[20261014-healthy]' -q
```
Results: **P3 exit 1, 1 failed in 395.96 s** (never committed; producer remained calibrating, followed by the existing `_fail` NameError), and **baseline exit 1, 1 failed in 394.66 s** (`fixture_unscorable`, committed after onset **307800 ≥ 270000**). Full command outputs: `artifact://1077` (P3), `artifact://1078` (baseline). This independently reproduces E's late-commit → never-commit classification for this parameter, not a baseline-pass→P3-fail regression; the P3 output contains gate=True/guard=False pile rejections such as ratio **4.35124e-08**. These are two slow invocations of one parameter across the two trees, not a claim to have re-run two distinct parameters or all twenty.

### 8. Docs / comments — substantive addendum PASS, caveats #2/#3

Read all three doc diffs and grep-searched one-time/frozen wording in driver/state and those docs, then searched the repo excluding `.venv*`, unrelated dashboard assets and orchestration evidence. Stale claims that calibration is currently one-time/frozen are gone from the contracted driver/state/docs; remaining matches describe **not** one-time, legacy frozen mappers, frozen config, or unrelated one-time model migration. The unchanged historical healthy-test comments still say one-time provenance; no current runtime behavior relies on that wording.

The existing runtime addendum accurately states formula, units, YAML-required floor, pacing, DEFAULT 0, raw/scored sub-state, last adopted provenance and X1. No new P3 doc file. Its legacy fit-count promise is not fulfilled for existing provenance (#2); newly added state/driver comments and raw log need the factual correction in #3.

### 9. Operational consequences / start compatibility

[INFERENCE from schema + live samples + exercised exporter/API paths] On each of the ten pods' first **new scored tick** after rollout, the old mapper starts unverified; the observed flat windows reject adoption, so label=raw, state=scored, p_published=p_raw. `analysis_state=degraded`, inventory scored/pipeline active, canonical probability gauge empty, fraction gauge present; indicator A follows p_raw and is normal on calm ticks, still warning/critical on real raw spikes. Cold restore before that first new tick can briefly replay the old calibrated label, as explicitly allowed by the card.

No startup-crash path was found for the **new matching ConfigMap plus existing PVC schema**: required floor validates, legacy schema upgrades/reopens successfully, no protected PVC/security/service config was changed. This is offline compatibility evidence, not a deployed rollout/restart proof. **New image + OLD ConfigMap refuses to start by design**: my old-config probe observed `ConfigurationError: Missing required configuration key 'degeneracy'.` Load-time validation in `config.py:742` propagates through `config_loader.py:1027`; it is a clear configuration error, not a later KeyError in scoring. Apply ConfigMap and image together. Live rollout/restart and ≥24-hour acceptance remain S's tasks; RV has not declared P3 operationally complete.

## Disposition rationale

The implementation preserves protected scoring laws, follows the approved refit/never-demote machine, migrates safely offline, and passes the requested fast and individual tests. Nevertheless, independent adversarial **real-tick** evidence proves the approved D1 statistic can certify and permanently retain another ill-conditioned pile mapper. The explicit RV criterion makes that a blocker, even though the source matches D1 literally. Resolve/escalate that design counterexample and fix the legacy count and misleading state-machine evidence before treating this package as accepted. Findings are advisory; S owns the decision.
