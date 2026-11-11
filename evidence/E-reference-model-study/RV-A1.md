# RV Review — SOLO-REFM A1a / A1b / A1c stages 1, 1b, 2

- Date: 2026-11-09. Reviewer: RefmRVA1, reviewer role.
- Findings are **advisory**; the Supervisor decides acceptance and remediation.
- Reviewed the eleven assigned commits, their file lists, current implementations/tests/results, the four cards, E-A1a/E-A1b/E-A1c, R-A1, R-A3 §1, and CAMPAIGN-CONTEXT including D15. A1c stage 3 / S4-real is **not** accepted or reviewed by this record.
- Lab paths below are relative to `pipelineml-model-exploratory-work/reference-model-study/` unless prefixed `orchestration:` or `production:`.

## Disposition per leaf

| Leaf | Disposition | Rationale |
|---|---|---|
| A1a — b588eb6, 21bd3e7, 2519ee4, ca0fd63 | **accepted_with_findings** | Independently rerun parity is real and passes; the restart replay is visible and independently corroborated. The committed gold fixture creates an explicit conflict between the card and the campaign's literal no-raw-data-commit invariant (F1). |
| A1b — 26acad5, a3f3cfa, 76451a6, d41c91f | **accepted** | Seed determinism, raw/block round trips, ground truth, K=11 composition and D13 coupling checked; full-horizon FLAT result independently reproduced. No material implementation defect found in the assigned scenarios. |
| A1c stages 1/1b/2 — 7bbe268, 013c570, 194938f | **accepted_with_findings** | Hand calculations, leakage rejection, five profile reductions and complete caption recomputation agree. Correct the ESS interpretation/count claim, missing observed traces and a vacuous test (F2–F4). The figures/profile are not evidence that the FLAT acceptance band passed: its failure is honestly recorded. |

## Findings

### F1 — should-fix: card/invariant conflict — live raw samples are committed inside the gold fixture

**Location:** `scripts/build_gold_fixture.py:30-36,59-65`; `tests/fixtures/gold_live_b4xkt.json.gz`, JSON `reference_models.<metric>.raw_series`; orchestration `CAMPAIGN-CONTEXT.md:27` versus `omp-workcards/refm-A1a.md:54`.

`git ls-tree -r --long ca0fd63` identifies the tracked 502,054-byte gold fixture. Decompression shows **10,488 CPU, 10,486 memory, 10,435 receive-byte and 10,435 transmit-byte raw timestamp/value samples**. Thus a blanket statement that no raw data was committed is false, even though `data/raw/` itself contains only a tracked `.gitkeep` and the packaged manifest is tracked separately. This is **not an unauthorized executor scope expansion**: the A1a card explicitly required the committed fixture with `raw_series`. It is a requirements conflict for S to resolve, not evidence against parity.

**Recommended fix:** explicitly adjudicate/document the gold-oracle raw-excerpt exception if permitted by the operator, or move the raw-bearing fixture to ignored local data with a tracked manifest/hash and adjust its tests/loader. Do not certify the literal invariant unchanged. No history rewrite or deletion was performed by RV.

### F2 — should-fix: the ESS narrative overclaims the measured mechanism and scored count

**Location:** orchestration `E-reference-model-study/E-A1c.md:105-120`, especially **108**; also stale wording in `R-A1.md:26-27`; implementation `src/refstudy/harness/ess.py:44-60` and `src/refstudy/reference/stl_lite.py:280-285,389-398`.

E-A1c:108 says gate-off scenarios score **1872 ticks**. The JSON's gate-off `p_raw_summary.n_valid` and ESS `scored_ticks` are **1289 for every seed** of S1/S2/S6/S7/S8: the 583-tick warm-up still applies. More importantly, the recorded ~45 stale hours mean **no served model**, not hours in which stale forecasts are scored and strike. Production `scan.py:1320-1332` returns `None` below the ESS floor, and `driver.py:1081-1085` rejects a prior-cycle model as stale. The lab correctly emits no model for that cycle and skips pod scoring when mandatory CPU is unavailable. The persisted running state can survive until a later accepted refit, but it is not served during the skipped cycle. The aggregate FPR changes also have different scored populations and do not by themselves establish the categorical conclusion that the gate “does not improve detection.”

**Recommended fix:** change 1872 to 1289; describe gated periods as uncomputable/unscored and distinguish posterior carry-over/resumed scoring from stale-forecast strikes. Qualify causal/detection conclusions or supply a matched-tick analysis. Mark R-A1's older “not on the per-tick scoring path” claim superseded. Keep the faithful gate implementation and production floor unchanged.

### F3 — should-fix: plotting hides valid observations whenever the reference is unavailable

**Location:** `src/refstudy/plotting/figure.py:123`; `src/refstudy/harness/evaluate.py:165-172`.

The grey “observed” trace is taken from the scored `MetricTick`, which has no observation when the model is absent. In S1 seed 1's displayed 576 blocks, the actual raw-derived CPU/memory/rx observations are finite on **576/576 each**, but the plotted observation arrays are finite on only **324/366/348** respectively: **252/210/228 available observations disappear**. I inspected `figures/part1-scenario-1.png` and `part1-scenario-4.png`; the seasonal figure visibly has those holes. This makes reference-gating gaps look like missing input data and hides exactly the signal structure under study. It also impairs comparison with a candidate serving more ticks.

**Recommended fix:** plot the independently raw-derived block observations in row 0, leaving unavailable forecast/residual/p values as gaps; label or shade model-unavailable intervals separately from true input gaps. Preserve the scoring/fidelity masks. Add a behavioral plot test with a finite observation and absent model.

### F4 — should-fix: an advertised isolation check is an unconditional pass

**Location:** `tests/test_harness_profile.py:73`.

`assert cfg.scenarios["FLAT"] is spec0 or True` always passes; `spec0` is the S1 specification, so removing only `or True` would also be the wrong assertion. It does not establish the preceding comment's “other scenarios are untouched” property. Separately, `tests/test_harness_captions.py:153-169` checks repeatability/status/schema but does not anchor any actual regression value; two identically wrong runs could pass it. The independent numeric recomputation in this review supplies evidence for today's results, not a lasting regression guard.

**Recommended fix:** compare FLAT to `hcfg.scn.scenarios["FLAT"]`, preferably verify all non-S1 scenario specs, and add a small selection of numerical caption expectations with the declared tolerances. The scenario chain smoke at `test_scenarios_counts.py:184-197` is intentionally wiring/range coverage, not proof of FLAT calibration; retain the separate reported-band verdict.

## Checks performed and literal results

### Execution isolation and bounded tests

I did not edit lab/production files, commit, contact the cluster/GPU host, or manage services. Tests used `PYTHONDONTWRITEBYTECODE=1`, disabled pytest's cache provider, and used `/tmp/refm-rva1-mpl` for matplotlib's cache. Because parity's recorder writes a result file, the positive run used an ephemeral YAML copy with **only** `parity.results_path` changed to `/tmp/refm-rva1-parity.json`; a YAML comparison returned `TEMP_CONFIG_DIFFERENCES []` and that single parity-path difference. The negative run used another temporary YAML with an invalid production root. Committed configuration/results were not rewritten.

1. `/usr/bin/time -p env PYTHONDONTWRITEBYTECODE=1 REFSTUDY_PARITY_CONFIG=/tmp/refm-rva1-reference.yaml .venv/bin/python -m pytest -m parity -q -p no:cacheprovider`
   - Exit **0**, 31 success dots, `[100%]`; literal timing **`real 123.89`, `user 121.93`, `sys 1.42`** (tool wall 123.96 s), bounded at 300 s. No skips or failures.
2. Leaf tests: `... .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_reference_*.py tests/test_scenarios_*.py tests/test_harness_*.py tests/test_plotting_*.py`
   - Exit **0**, all success dots through `[100%]`; literal timing **`real 35.15`, `user 33.22`, `sys 0.91`** (tool wall 35.20 s), bounded at 120 s. No skips or failures. No lint/build/formatter was run.
3. Invalid-root copy, `pytest -m parity -q -p no:cacheprovider tests/parity/test_p0_config.py`:
   - Exit **1**, **0.860 s** wall; two setup errors, not skips: **`ProductionImportError: parity.production_root is not a directory: /nonexistent/refm-rva1-production`**. No production configuration was edited.

### A1a: independence, configuration and actual parity

- Exhaustive native grep using `solo_mode|sys\.path|import analyser` over `src/` finds only A3-owned `data/oracle.py:11` (source citation), `data/package.py:645,691` (field/key `solo_mode_config`). There are **no matches in reference/, scenarios/, harness/ or plotting/** and no production imports in src. Thus the literal whole-src empty-grep acceptance remains false because of these three non-import strings, not because these leaves import production.
- Reviewed `git diff 5fc6b0f..HEAD -- reference-model-study/config/reference.yaml`: all 29 mirrored values plus the metric names/kinds pass P0; source constants pass P0_constants. The non-mirror values are explicitly lab-only: rare-count inclusion, short aliases, parity roots/pins/file lists/result path, P3 seed/horizon, P4 tolerances/replay limits/budget. No changed strike law, Simes law, Markov prior/sojourn/gains or 0.2 decision threshold was found. ESS-off/K3 overrides are separately labeled sensitivity runs, not base-configuration changes.
- Committed and freshly rerun JSON agree: **P1=0.0, P2=0.0, P2a=0.0**; every P2b gauge/counter/rare-count delta is **0.0**; P3 all quantities and relative ESS delta **0.0**, **713 scored ticks**, **14,256 metric-ticks**, eligible sizes **[3,11]**, **32** ticks with `p_simes<alpha`, nontrivial `k_eff` on 713 ticks. P3 test asserts these exercised branches, not just array shape, and asserts each numeric maximum `<=1e-12` (`test_p3_chain.py:193-207`).
- Recorded provenance heads are production **5bcc7f9128d55e38d3c09838b3af0699edc4973b**, shared **942b8807f63e614fe3542ed2ba1268046291bfeb**; nine used-file blob IDs, dirty-status lines and versions **Python 3.12.15 / numpy 2.5.4 / scipy 1.18.1** are present. Absolute roots are in `config/reference.yaml:81-84`, not duplicated in JSON provenance. `prod_import.py:109-167` checks pins, used-file cleanliness and imported module locations before calling production.
- **Three specific production-law spot checks:**
  1. Counter right-closed attribution/reset/gap rule: lab `blocks.py:221-258` matches production `scan.py:564-633`: `ceil((ts-ws)/T)-1`, `left<ts<=right`, reset increment=value, gap `<=0` or `>35` invalidates its block, clipped coverage. P2a rerun also gives 0.0 across 48 seeded cases.
  2. `tilde_p`: lab `chain.py:53-59` matches production `fusion.py:73-86`: zero strikes -> 1.0, otherwise `binom.sf(n_k-1,W,alpha)`. Despite the historical function name this is the binomial tail; I did not substitute a different beta-binomial distribution.
  3. Eligibility/gaps: lab `chain.py:467-486` matches production `driver.py:1311-1325,1366-1381`: append None on an uncomputable tick, retain W temporal positions, count only non-None fill, require a p **this tick** and fill>=3. This is not “three strikes required for eligibility.”

### P4 restart replay: independently corroborated, not a hidden tolerance change

- Converted epoch independently: **1794135600 = 2026-11-08T11:00:00+00:00**. R-A3:16-17 records the recreated detector pod starting **11:03:30Z**. These are not the same instant: the refit-cycle label is 11:00; the first cold-record score is **1794135900 = 11:05Z**, 90 seconds after recreation. The recreation falls inside that exact 11:00–11:05 interval.
- Verified SHA256 against the manifest for **all ten compressed oracle files**. Every oracle has the first cold-record tick at **index 78 / 1794135900**, with continuous-model `t0=1794135600`. In b4xkt index 77's CPU p is **0.34912280701754383** (570-population-compatible); index 78 is **0.5938697318007663** (522-population-compatible), memory **0.7452107279693486**. `_find_restart` (`test_p4_real.py:394-415`) uses oracle probabilities alone, not lab output, to identify the cold population; subsequent hybrid replay then compares all outputs. Together with the shared event time and passing downstream parity this supports an environmental cold rebuild; it is not independent access to pod lifecycle logs beyond the preserved R-A3 observation.
- The un-replayed `as_seen` variant is retained in the committed **and fresh** result JSON, **fails on all ten pods**, and records **724–1121** p-family mismatches after the prefix (b4xkt **1003**). `restart_replay` is explicitly selected as primary; all ten primary variants pass, with **0 after-prefix mismatches** and **287/288 comparable ticks per pod**. The missing final tick is recorded as not comparable, not silently omitted. No p tolerance was changed; configured p-family tolerance remains **1e-12**.
- Read the mismatch/replay classifier (`test_p4_real.py:239-304,307-374`). Fresh totals: **27,148 oracle-scored metric-ticks, 0 unexplained observed-cell reproductions**. Counter cells are reconstructed at the oracle's last stamp and checked against value plus attribution; gauge drop-last search is bounded 0..3. Output comparisons distinguish strict quantities from prefix-permitted p-family mismatches and retain verbatim rows.
- **Scope of “unexplained=0”:** oracle `p=None` cells are separately forced gaps, not included in that observed-cell claim: **4422 forced cells** = **4111 block-not-aligned + 311 model-stale**. Of these, **4414** were emitted from final data; the bounded lag probe yields an unemitted cell for **4137** forced cells. The code does **not** prove every missing-p reason from raw data independently; it replays those observed environment inputs as the card permits. Acceptance is therefore **conditional replay parity**, not a claim that an uninterrupted final-data run reproduces live history. P4b remains report-only.

### A1b: scenarios, masks, dither and D13

- Independently generated all nine scenario names twice at seed 1 and SHA256-compared all raw arrays: **deterministic=True for all nine**; each `chain_raw()` has **11** canonical series. Raw-derived continuous blocks are all emitted except S5/rx, **468 non-emitted blocks**; other S5 signals, including tx, remain emitted.
- Independently constructed `[onset,end+4)` exclusion masks from the truth events: **quietmask=True for all nine**. Regimes/gaps remain quiet as specified; persistent anomalies exclude the rest of the horizon. S2's held drift/step, S3's six-block pulses/noise regime, S4 synthetic bumps, S5 intentional receive-byte holes, and S7/S8 subdaily/non-divisor structure match the amended cards. No scenario impossible under its **amended** claim was found; S4 is not represented as recorded real data and S7 is not claimed to be weekly.
- `raw.py:41-54,129-139` re-centres dither by the counter/gauge's own block attribution. Independent regular-grid round trips give maximum scaled relative errors **1.12e-12 to 5.60e-12** across the scenarios (cumulative-counter floating-point cancellation), well within the card's **1e-9** bound. Thus mean preservation holds numerically at the required tolerance, not literal byte-exact equality to targets.
- D13 implementation uses **clean**, not target (`registry.py:211-215`). Independently measured FLAT packet increment means **40.0613247863 / 40.0470085470**, variance/mean **0.9979593240 / 1.0029901191**. On the quiet S4 prefix, packet block sums versus byte block noise have correlations **0.0216628291 / 0.0101829907**. The seed tests also exercise burst coupling and disabled-rare continuous-byte equivalence; these are behavioral checks, not just eleven-key assertions.
- Requested bounded full-horizon chain rerun, **`run_pod(get_scenario('FLAT',1).chain_raw(), cfg)`**: **1289 scored**, median **0.0012893117853352318**, fraction `p_raw>0.2` **0.0395655546935609**, fraction in [0.0012,0.005] **0.9014740108611327**, **1.139 s** wall. The claimed median ~0.0013 / ~3–4% is reproducible, not evidence of a perfectly clean flat control.

### A1c: independent hand derivations, profile reductions and figures

Two hand-built series were evaluated directly against `harness/metrics.py`, separately from the leaf tests:

1. **Bounded anomaly A:** n=700, anomaly [60,64), valid ticks 10..699; baseline .01 on quiet ticks, p[60]=.2, p[61:63]=.3, p[63]=.8, p[67:70]=.8, other p=.01. Strict threshold yields j*=61, **latency=1**. Quiet excludes [60,68), so end+3 (67) is excluded, end+4 (68) included: **FPR=2/682=0.002932551319648094**. The five-low-then-spike interval is insufficient; first six-low run starts at 70, so **settle=70-64=6**, baseline **.01**, tolerance **.05**. Exact configured fidelity exclusion ends at **64+582=646**: with errors +2 on 10..59 and -1 on 646..699, **n=104**, **MAE=154/104=1.4807692307692308**, **RMSE=sqrt(254/104)=1.5627884349161574**, **bias=46/104=0.4423076923076923**. All match implementation output. Truncating detection at 61 gives **censored, horizon 1**; truncating settling at 75 gives **settle_censored**; fewer pre-onset baseline values gives **no_baseline**.
2. **Persistent anomaly B:** n=100, onset 60, search_end 90, baseline .01, subsequent p=.2 except invalid tick 61 with .9. No strict valid crossing: **censored, horizon=30**, **settling=not_detected**, **quiet FPR=0/60**. Persistent fidelity mask excludes onset..end; constant error +3 before onset gives **MAE=RMSE=bias=3.0, n=60**. All match. This also checks an invalid high p does not become a detection.

- Independently wrapped STL-lite with `fit_end += T` and passed it through **evaluate_reference**: rejected with **`ValueError: leakage: tick 581 (1793709000.0) fit_end 1793707200.0 > tick - T - dt = 1793706900.0`**. `run_checked` invokes the guard for every continuous `ReferenceRun`; the test is not just checking provider wiring.
- Five reductions independently computed from committed **per-seed** JSON, rather than trusting stored aggregates:

| Number | Per-seed values | Recomputed mean / sample SD | Stored mean |
|---|---|---|---|
| FLAT FPR | .0395655547, .0287044220, .0395655547, .0356865787, .0411171451 | **.0369278510473 / .0050157423973** | .0369278510473 |
| S1 FPR | .4767759563, .4680555556, .4830508475, .4658119658, .4548022599 | **.4696993169993 / .0108175546069** | .4696993169993 |
| S4 first-event latency | 3, 4, 0, 5, 3 | **3.0 / 1.8708286934** | 3.0 |
| S8 CPU fidelity MAE | 5.2539096486, 5.0554568147, 5.0392809313, 4.9526934952, 4.9465028141 | **5.0495687407734 / .1244016815751** | 5.0495687407734 |
| S1 scored ticks | 732, 720, 708, 702, 708 | **714.0 / 12.0** | 714.0 |

- Also independently reran S1 seed 1 through `run_pod`: **732 scored**, fraction `p_raw>0.2` **0.476775956284153**, median **0.07590346631987673**, **1.012 s** wall. Thus “714/1872, ~47%” is the **five-seed mean scored count / mean conditional exceedance**, not the seed-1 count. Production and lab gate semantics agree as described above; the explanatory stale-strike narrative needs F2.
- S2's second event has **settle_censored on all five seeds**, as claimed. Censored events are excluded from latency/settle means and counted explicitly (`aggregate.py:37-55`), not treated as zero latency. FLAT `flat_band_violation=true` is preserved for all five seeds; no threshold/band was tuned by these results.
- Recomputed the **entire caption-regression object in memory**, bounded at 40 s, without writing result files: **4.609 s**, **`equal_entire_JSON True`**, summary **6 reproduced / 7 changed / 2 recomputed / 5 not_derivable**. Independently reclassified every target from its quoted value/tolerance/faithful/basis and got the same counts. Missing gate-on probe values remain null with reasons; gate-off values are separate. The status labels are numerically honest under their declared definitions, not a disguised widening of parity tolerance. The two recomputed fractions explicitly use their stated pooled finite-p population; they are not marked reproduced.
- Visually inspected S1 and S4 committed PNGs, both **1980×1410**. Signal/reference/residual/per-metric p/p_raw panels, event spans, strike and operator threshold lines, FPR and S4 latency annotations are present. F3 is a substantive input-visibility issue the structural figure tests miss, not a style preference.

## Explicit campaign invariant statements

| Invariant | A1a | A1b | A1c stages 1/1b/2 |
|---|---|---|---|
| No chain-law / threshold change | **Preserved** for the deployed base path: P0/P1–P3 plus three source spot checks. Documented unsupported/omitted plumbing remains as declared in the card. | **Preserved**: edits generate inputs only; D12/D13 change scenario metric composition/count generation, not scoring laws. | **Preserved**: base K=11/ESS floor 36/threshold .2; K3 and gate-off are explicit sensitivities. |
| Production read-only; no production import in src | **Preserved**: production imports are confined to parity tests; current source check and pinned-source comparisons performed. | **Preserved**: no production imports or production paths in assigned source. | **Preserved**: same; caption simulator loaded read-only from the explicit evidence path, not production. |
| Weights/raw data never committed | **Not literally satisfied**: raw-bearing gold fixture, explicitly required by the card; see F1. No weights or bulk raw packages in assigned commit file lists. | **Preserved** in assigned commits: code/config/tests/docs only, no weights/raw package. | **Preserved** in assigned commits: derived profile/caption JSON/CSV and PNGs, not model weights/raw sample packages. |
| YAML-first configuration | **Preserved**: production mirrors/constants/provenance and replay tolerances explicit; P0/missing-key tests exercised. | **Preserved**: scenario structure, sampling/dither, noise, metric/count coupling configured and validated. | **Preserved**: scoring/guards/settling/fidelity/sensitivities/plotting/profile targets in YAML; derived index geometry follows the stated contract. |
| Yardstick p_raw | **Preserved**: mapper absent; P4 compares raw posterior and checks oracle raw fields. | **Preserved** in chain checks; generators themselves do not publish/calibrate probabilities. | **Preserved**: four quantities and strip use p_raw, threshold .2; per-metric p caption values are explicitly separate. |

## D15 assessment

No observed defect can responsibly be attributed to the executor-model swap: the repository/results do not provide a controlled model comparison. F1 follows an explicit card requirement, while F2–F4 are concrete evidence/plot/test issues that receive the same disposition regardless of model. **I would accept this code as if produced by the configured executor, with exactly the advisory findings and invariant qualification above**; I would not waive them for either model. The independent parity, behavioral probes and result reductions are sufficient to remove the D15 code-trust hold for these assigned leaves, subject to S's decision, not to certify unrelated leaves or A1c stage 3.
