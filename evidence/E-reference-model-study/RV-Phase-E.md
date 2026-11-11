# RV Review — SOLO-REFM stage-2 results and Phase E

- Date: 2026-11-11
- Reviewer: `openai-codex/gpt-6.1-sol` (RV); findings are **advisory**, Supervisor dispositions required.
- Overall disposition: **rejected as written** for the operator-facing recommendation; the underlying no-cutover decision is supported, but the wording and completion claims are not ready for operator consumption.
- Scope: C3 `9277c0d` + note `ed0098d`; C4 `536e6e2` / `4bc2bd5`; cand-B `cdb74e7` / `0d1a3f0`; recommendation `ef09474`. Lab paths below are relative to `reference-model-study/`, except the licence note at lab-root `markdown/timesfm3-licence-note.md`.
- Read first: campaign decisions D-A, D-S5, D-S8, D-S9, D-F, autonomy window; reviewer mandate; all three workcards and stage-2 evidence sections.
- No test suites, model inference, long jobs, GPU/cluster/SSH/service operations, commits, or lab/production modifications were performed. The only numerical replay beyond JSON arithmetic was one real CPU-metric shard, **1.168 s**, using existing forecasts. Only this review file was written.

## Dispositions per item

| Item | Disposition | Specific checks actually performed |
|---|---|---|
| 1. C3 stage 2 + note | **accepted_with_findings** | Current bytes match all named commits. Re-summed valid/quiet three-class counts and mechanism counts on **180 rows: 0 violations**; independently recomputed FLAT counts, latency seed means, S7/S8 ratios, real fleet pooling, and leakage maxima. Missing masking joint-vs-single latency output and note qualification issues remain (F7, F10). |
| 2. C4 stage 2 + figures/note | **accepted_with_findings** | Current JSON/note bytes match named commits; checked **10,080 requested horizon/pair/resolution/segment/signal cells, 0 missing** across 42 units; compared **180 C3 aggregate join fields, 0 mismatches**. Opened synthetic and real figures; recomputed actual coverage extrema and one real CPU block band. Tables support a scoped diagnostic, not universal calibration (F3–F5). |
| 3. cand-B measurement + note | **accepted_with_findings** | Current JSON/note match named commits. Independently averaged per-seed drift MAEs, S1 occupancies and FLAT normal fractions; counted **29/200** event-check regressions; confirmed 9 scenarios × 5 seeds × 2 arms × 2 gates in recorded data, and recorded assertions. The regression verdict is supported; narrow-flat-band and D-A verdicts must not be conflated (F8). |
| 4. Final recommendation | **rejected** | Audited all lines/sentences below, checked licence restrictions, normalized compute arithmetic, validation denominators, missing Mac result files, and provenance. Keep A / do not adopt B or C is defensible; production-shadow permission, completion wording and several scientific/compute claims require correction before release. |

## Findings (advisory)

### F1 — blocker: “shadow benchmark” is not permitted production use under the quoted licence
- **Location:** `markdown/part2-recommendation.md:9`; lab-root `markdown/timesfm3-licence-note.md:14-18,22,30-34`.
- **Issue:** The recommendation correctly identifies the non-commercial/non-production wall, then permits adoption as an “offline / shadow benchmark.” A production-connected shadow detector is still an indirect interaction with production systems, expressly outside the note's quoted permission. Offline does not automatically mean non-commercial either; the note excludes commercial decision-making.
- **Fix:** Replace that sentence with: **“Use C only as an offline, non-commercial research benchmark within the licence's restrictions. Production-connected shadow use, like production adoption, requires an appropriate commercial licence.”** Keep the actual licence wall as the first reason for no production adoption.

### F2 — blocker to claiming a completed final gate: mandatory Mac B1/B2 evidence is absent and the recommendation implies completion
- **Location:** recommendation `:26,62`; `CAMPAIGN-CONTEXT.md:94,98,123`; `HANDOVER-2026-11-11.md:9,11`; compute note `:93-99`.
- **Issue:** Neither `results/b1-scaling-cpu.json` nor `results/b2-refresh-cpu.json` exists. Exact CPU-file discovery returns only `a2-smoke-cpu.json` and `c1-smoke-cpu.json`. Handover explicitly says the mandatory measurements are **NOT done**. “The full B1/B2 Mac measurement was run ... recorded ... when complete” is misleading even with the future qualifier. D-S4/D-F required the CPU-class normalized comparison before Phase E. A2 smoke is not full B1/B2, and is V=3 rather than the V=4 GPU study.
- **Exact replacement:** **“The mandatory full Mac CPU B1/B2 measurements were attempted but did not complete: the exclusive-window hygiene gate did not pass, and neither `results/b1-scaling-cpu.json` nor `results/b2-refresh-cpu.json` exists. Only the earlier A2 CPU smoke is available (943.3 ms, V=3, N=11520); it is not the V=4 B1/B2 CPU-class normalized comparison. The GPU-versus-CPU deployment comparison remains incomplete; see HANDOVER.”**
- **Fix to completion status:** Mark the Phase-E feasibility/completion gate incomplete or explicitly provisional pending that mandatory evidence; do not invent CPU normalization or call earlier library reviews reviews of these results. This does not prevent an immediate licence-based no-adoption decision. RV is not requesting a live benchmark in this review window.

### F3 — should-fix: calibration ranges and blanket calibration claims exceed the table evidence
- **Location:** calibration note `:30,34,55-57,84-88`; recommendation `:24,51`.
- **Issue:** “0.79–0.82 for every unit, signal and horizon” is false even for synthetic seed means: maximum **0.825738** (S1 uni tx b12); individual main-unit range **0.779901–0.833136**. Synthetic block seed means reach **0.939968**, individual units **0.914692**, not universally 0.96–1.00. Real raw memory is materially undercovered: uni **0.713684 / 0.691053**, multi **0.722895 / 0.731316** (b4xkt/m7pr8, b6), not “calibrated” along with everything else. The note's “both modes identical on cpu” is also false for raw coverage: b4xkt uni **0.795000**, multi **0.787632**. PIT b6 individual synthetic bins range **0.070064–0.128199**, so specify aggregation when calling them ≈0.10.
- **Issue, width scope:** The quoted 0.93–1.17 residual/noise-law ratio and 1.9–7.4 band/noise-law ratio describe the selected seed-1 example table, not all main units. Across the synthetic main units, gate off: **0.737537–1.324037** and **1.355883–7.647022**, respectively.
- **Fix:** Say **“Synthetic raw-native coverage is near nominal (seed-mean 0.791–0.826 across the reported main horizons); block bands generally overcover (seed-mean 0.940–1.000). Real memory raw-native coverage undercovers, and real CPU block coverage fails severely.”** Label the width ratios “selected seed-1 examples”; report mode-specific real values. Replace “noise law (calibrated by construction)” with **“empirical residual/noise law; posterior calibration is not established by construction.”** The FLAT failures themselves preclude assuming the whole chain is calibrated by construction.

### F4 — should-fix: the real CPU anomaly is unresolved, but “absorbs a constant bias” is not established and is contradicted as the dominant explanation
- **Location:** recommendation `:24`; calibration note `:84-92`; `src/refstudy/refcompare/handoff.py:14-21,64-70,97-112`; `reference/blocks.py:7-20`.
- **Issue:** Retaining “unresolved” is correct. However, the recommendation adds a causal conclusion: “the chain stays calm ... [record] absorbs a constant bias.” One-shard recomputation found error mean **0.025787** but error SD **1.087608**, against median band width **0.032284**; misses occur on **both** sides. This is not dominantly a constant-offset error. Calm co-occurring with poor block coverage does not by itself prove why the chain stays calm.
- **Bounded evidence:** The code applies one historical counter ratio per cycle, while production blocks average increments over each real block's irregular intervals. On b4xkt CPU the historical scale is **1.089382–1.097104**, but held-out block observed/grid-mean ratios have p05/p50/p95 **0.991775 / 1.082334 / 1.223884**. A nearly constant rate on the 15 s grid can therefore have an extremely narrow raw band while production block increments fluctuate with cadence. This confirms a plausible visible hand-off/cadence mechanism, **not** a complete attribution or a licence to change the production block law.
- **Fix:** Replace the clause with **“The chain remains calm while using its empirical residual record rather than these bands; the source of the real CPU block undercoverage remains unresolved. A historical scalar counter conversion cannot reproduce block-to-block irregular-interval variation and is a concrete candidate mechanism.”** Do not claim repaired coverage without a separate study.

### F5 — should-fix: the real-band fans have misleading time axes and are not readable 65-minute fans
- **Location:** `scripts/run_c4.py:945-954,968`; `src/refstudy/refcompare/plots.py:278-285`; opened `figures/c4-bands-realflat-b4xkt.png`.
- **Issue:** First/middle/last forecasts are all drawn at the **first** cycle's `fit_end + cadence`, and all fan axes share the fleet strip's multiday x-axis. The opened image shows nine almost-vertical fan marks at the same early timestamp, and broadens the nominal last-2-day view to include that early fan. A middle/last forecast is thereby assigned the wrong epoch, not merely styled poorly. One common `fan_t0` cannot express three cycle timestamps. Code also uses that same counter-style first-step timestamp for the gauge; use the existing counter/gauge index law if plotting absolute epochs.
- **Fix:** Give each fan an independent **minutes-ahead 0–65** x-axis, or its own correctly indexed cycle timestamp and local limits; do not share that x-axis with the multiday block/score strip. Preserve first/middle/last provenance and add an assertion checking fan extents and distinct origins, rather than only image dimensions.

### F6 — should-fix: compute summary mixes fitted knees, validation normalization and comparable-call scopes
- **Location:** recommendation `:9,26,52`; compute note `:42-63`; `results/b2-sustainable.json` rows and `b2-refresh-cuda.json.validations`.
- **Issue:** Raw sequential 2-day knees are **429/257/172** pods at 300/180/120 s; validation-adjusted values used in the compute note are **416/249/166**. Both are present in the JSON, but the recommendation silently chooses raw values while the cited note uses adjusted ones. Name the basis, or use the adjusted values consistently.
- **Issue:** The quoted validation ratios **0.970679** and **1.021830** are throughput divided by benchmark `mu_hat_pods_s`, **not the offered arrival rate** (rho=1.3). Literal recomputation: sequential `(212/150)/1.456025 = .970679`, batched `(736/150)/4.801842 = 1.021830`; fractions of offered rho×mu are **0.746676 / 0.786023**. The current “of the offered rate” wording is wrong.
- **Issue:** “0.3–1.1 s per V=4 call on GPU/CPU” attributes a V=4 CPU timing not measured by full B1. The only quoted Mac point is A2 V=3, **943.294 ms**. Keep it separately labelled; the millisecond STL comparison is a CPU-side reference refit, not an end-to-end model refresh benchmark.
- **Confirmed, not findings:** **1017.897101 GFLOP**, **500.975440 GFLOP**, `300*1000/F = 294.725272 / 598.831751` pods/TFLOP/s; overlap **706/423/287**, batched **1429/856/571**; accelerator-only ceiling **1517**; 300-s 2-day GPU-board excess energy **10.254–14.968 J/pod**. D-F's same-host/nontransferable-ratio qualification is correctly retained. Host feasibility for about ten pods is supported; a hardware-general CPU comparison is not.
- **Fix:** State raw versus adjusted basis, rename validation denominator, separate GPU V=4 and CPU V=3 evidence, and retain extrapolated/shared-host/board-power qualifications.

### F7 — should-fix: detection-summary universals and equivalence language omit material deployed-gate effects
- **Location:** recommendation `:18-22,47,50,58`; accuracy note `:7-11,23-48,90-97`.
- **Issue:** “Occupancy ... within a few thousandths ... everywhere” is false against deployed A: S3 decisive **0.407 vs 0.373**, S5 **0.404 vs 0.349**, S6 **0.370 vs 0.313** (rounded note values). Even gate-off A versus C-multi on S4 undecidable occupancy differs by **0.015002**, not a few thousandths. The examples S1/S7/S8 mainly select gate-off A without naming it; C3 D-6 requires naming the comparator. S6's deployed-gate latency/availability benefit is not represented by the net “ties on bursts / small mixed” synopsis.
- **Issue:** “S3 second pulse reaches decisive 3/3” is numerically true over the long search window, not pulse-local evidence: C-multi latencies **66/3/65** for a **6-tick** pulse, hence only **1/3** within the pulse. The accuracy note properly flags this; the recommendation loses that caveat. S4 figures quoted in the recommendation are E0 only; E1 means are equal, not +1–2 ticks.
- **Issue:** “No measurable change”/“does not move decisions” is stronger than rounded proximity. S7 C-multi minus gate-off A is **−0.0009095**, S8 **+0.0013643**; versus deployed A, S7 is **+0.0047063**. No equivalence or significance analysis was supplied.
- **Fix:** Say **“Detection results are mixed on this matrix: better synthetic FLAT calibration and some deployed-gate availability/late-response advantages, slower S2 drift and first S4 burst; no material reduction in quiet decisive occupancy on S7/S8 in these three seeds.”** Name gate-on/off for every comparison; label the S3 3/3 result as long-window crossings, only 1/3 pulse-local. “Small and mixed” is an advisory weighting judgment, not a demonstrated uniform bound or equivalence result.
- **S1 limits:** The ~40% observation itself is matched: A-on **.416220**, A-off **.397351**, C-uni **.403091**, C-multi **.395585**. The recommendation correctly calls this **synthetic**, quiet-tick, unresolved, and not evidence of a C win. Add **“on each reference's own scored ticks within V0; A-on availability .537748, others 1.0”** so it does not imply a matched-tick comparison or general model equivalence. All S1 ticks are quiet; mechanism differs substantially (A-on predominantly post-gate, others fresh-model misfit/noise).

### F8 — should-fix: cand-B regression is supported, but the three-way table switches flat metrics and falsely says structural fidelity was not measured
- **Location:** recommendation `:35-39,45,48-50`; cand-B note `:50-55,65-70,75-81`.
- **Issue:** B's **0.186** is outside the narrow legacy flat probability band, not outside D-A decisive-normal. Comparing it in the same row with A's **96.3% normal** and C's **98.5% normal** mixes yardsticks and horizons/seeds. Cand-B measured D-A normal fractions are **A .963072 / B .923507** (5 seeds, Part-1 offset); decisive fractions **.008534 / .020171**. The outside-narrow-band means **.106905 / .186036** are valid secondary diagnostics, not the D-A verdict's criterion.
- **Issue:** “B structural fidelity: not measured there” is false: the full cand-B JSON contains S7/S8 fidelity and decisions for both arms/gates. For example, quiet decisive occupancy gate-on worsens **S7 .359086→.512904**, **S8 .368429→.708445**. These are not directly comparable with C3's later-offset three-seed rows, but they were measured.
- **Issue:** “Faster on 2/5 seeds” fits decisive onset, not leave-normal (seed 5 improves leave-normal 55→28 but decisive stays 56). The 35% gate number is memory's **76/216 whole-S2 refit cycles**, not a separately demonstrated fraction restricted to drift windows. Do not erase the observed gate-on drift gain with a blanket unreachable-target claim.
- **Fix:** Put B's D-A normal fraction in the summary, explicitly label its five-seed/offset-584 protocol versus C3 offset-1118/seeds-1–3, retain the narrow-band metric only as secondary, replace “not measured” with “measured under the separate cand-B protocol,” and distinguish decisive/leave-normal onset. The supported no-adoption result remains: drift improves but S1/FLAT and 29/200 event checks regress.

### F9 — should-fix: “one-step fidelity,” hidden calibration gains and “not the reference model” overstate what was established
- **Location:** recommendation `:11,22,49,51,57,66`; accuracy note `:4-11`; cand-B note `:117-120`.
- **Issue:** C3 measures the served frozen forecast (blocks 6–11, about 30–55 min ahead), not a one-step forecast. One-step cv1 is B's selector objective, whose mismatch to the served horizon is explicitly a limitation. Also, taking p_raw rather than a fitted mapper does not make the measured reference-induced calibration gains/losses invisible: line 17 itself reports them. Finally, S7/S8 forecast-error gains do not support ruling out reference design as a lever; they only show that these gains did not materially reduce this chain's quiet decisive occupancy under this protocol.
- **Fix:** Use **“served-block forecast fidelity”**; replace line 57's last sentence with **“No reference-specific posterior recalibration was fitted; all comparisons use the unchanged raw posterior chain.”** Rephrase roadmap exclusion to **“The measured reference substitutions do not justify cutover; investigate the guard and residual/chain response before attributing the remaining errors to one component.”** Treat a diurnal width floor and TimesFM-2.5 as untested proposals, not demonstrated repairs.

### F10 — should-fix: C3 omits an expressly requested masking result and contains a contradictory S5 mechanism label
- **Location:** workcard `refm-C3.md:46`; `results/c3-leakage.json`; accuracy note `:52-56,112`.
- **Issue:** C3's leakage result has 16 pair diagnostics/identity flags, but no joint-versus-single S4 leave-normal/decisive latency result (literal search for `latency|joint|single|settling`: **no matches**). This acceptance subitem is neither delivered nor explicitly dispositioned out of scope. Separately, TimesFM S5 has nonzero “post-gate” counts despite no ESS gate; the note flags it rather than suppresses it, which is good, but the label cannot be read as causal evidence of an ESS-gate mechanism.
- **Fix:** Supervisor must disposition the omitted latency subitem; compute from existing scored variants if already available, or explicitly record that it was not delivered instead of claiming unqualified workcard completion. Explain the S5 label as a no-model/gap classification artifact (or correct the taxonomy after tracing it), and do not infer an ESS-gate mechanism for C. No new model/GPU run is needed to clarify the documentation.

### F11 — should-fix: real-flat and review-status summaries need explicit scope
- **Location:** recommendation `:17,46,59,62`; accuracy note `:74-77`; `E-C4.md:520-524,667-668`; `E-C3.md:1015`.
- **Issue:** Deployed A is calm on **10/10**, not just the undifferentiated “all four rows ... 9/10” summary; gate-off A and each C are **9/10**. A-deployed pooled normal **.999510**, C **.995425** differ and both clear the fleet rule, but C fails on vlsl8 while deployed A does not. “About equal” is acceptable as a qualitative fleet summary only with that exception and the unavailable/gated-tick qualification.
- **Issue:** 9.8 days is the raw package, six days the C3 input slice, and only **612 scored ticks per real reference/pod** enter these reported fleet fractions; do not imply every tick in all 9.8 days was evaluated. Before this RV record, older RV-C/RV-C2 records covered libraries/frozen-shard integrity, not the new stage-2 results or the Supervisor's recommendation. “Every leaf reviewed, defects fixed except gates” is too broad without naming this pending/then-new review and unresolved findings.
- **Evidence inconsistencies:** E-C4's earlier stage-2 paragraph says CPU raw coverage **.598** and block **.011–.016**, while final JSON/note show nominal-ish CPU raw and 80%-pair block **.021/.016**; it mixes interval pairs/stale values. E-C3's stage-2 surprise gives S1 availability **.554**, final seed mean is **.537748**. Later correct examples do not clearly supersede the earlier claims.
- **Fix:** Name 10/10 versus 9/10; state source/scored horizons and availability; update evidence paragraphs or mark them superseded with pointers; list this review's findings and the missing Mac gate explicitly rather than asserting closure.

### F12 — nit: cand-B duration conversion is wrong
- **Location:** `markdown/candb-profile.md:62`.
- **Issue/fix:** 15 five-minute blocks are **1.25 h**, not ≈1.9 h. Correct the unit conversion; it does not affect the measured regression verdict.

## Literal numerical cross-checks (JSON arithmetic; not reruns of the study)

Means below were recomputed from per-seed rows/counts where available, not copied only from prose. Ratios were divided from numerator/denominator MAEs. “Matched” permits the recommendation's stated rounding; “mismatched” means its unqualified wording or value is not supported.

| Recommendation claim / JSON source | Result found | Match |
|---|---|---|
| Synthetic FLAT A normal, decisive (`c3-profile`, FLAT per-seed valid classes) | **2181/2265 = .962913907**, **22** decisive | matched |
| Synthetic FLAT C-uni normal, decisive | **2232/2265 = .985430464**, **6** decisive | matched |
| Synthetic FLAT C-multi normal, decisive | **2227/2265 = .983222958**, **7** decisive | matched |
| S7 C-multi / A-off MAE, cpu/mem/rx/tx | **.809569752 / .874735889 / .930056418 / .905139561** | matched |
| S8 C-multi / A-off MAE, cpu/mem/rx/tx | **.515463786 / .477996194 / .629673696 / .632973474** | matched |
| S2 A drift leave/decisive seed means | leave **[54,1,30]→28.333333**; decisive **[76,68,31]→58.333333**, 3/3 | matched |
| S2 C drift leave/decisive | leave **[96,81,30]→69**; decisive **[null,null,31]**, 1/3 | matched |
| S4 E0 A leave/decisive | **2.333333 / 3.333333** | matched, E0 only |
| S4 E0 C-uni; C-multi | **3.666667/4.666667; 4/5** | matched, E0 only |
| S4 E1 all four references | **4.666667/5.666667** | matched “tie”; not universally +1–2 |
| S1 decisive A-on/A-off/C-uni/C-multi | **.416220096 / .397350993 / .403090508 / .395584989** | matched “~40%”, qualified F7 |
| S7 decisive A-off/C-multi | **.302864939 / .301955434** | matched rounded “~.30”, not equality |
| S8 decisive A/C-multi | **.358799454 / .360163711** | matched rounded “~.36”, not equality |
| Real pooled normal deployed A/C (per-pod n-weighted) | **.999509804 / .995424837**, n=6120 each | matched |
| Real decisive deployed A/A-off/C | **2 / 189 / 23**, concentrated on vlsl8 | matched |
| Per-pod calm A-on/A-off/C-uni/C-multi | **10/10 / 9/10 / 9/10 / 9/10** | summary needs qualification F11 |
| B S2 drift mem gate-on A/B (five paired seeds) | **20.947256675 / 12.232681183** | matched |
| B S2 drift cpu gate-on A/B | **11.988198235 / 4.454417287** | matched |
| B S2 drift mem gate-off A/B | **29.321738675 / 7.577710780** | matched |
| B S2 drift cpu gate-off A/B | **9.724399101 / 1.288735533** | matched |
| B S1 gate-on undecidable A/B | **.027955005 / .058312668** | matched |
| B S1 gate-on decisive A/B | **.441744312 / .458041548** | matched |
| B slower event checks / verdict | **29/200**, `regressed` | matched |
| B FLAT outside narrow-band A/B | **.106904577 / .186035687** | matched secondary metric, not D-A normal |
| Leakage maxima, all 16 pairs | ratio **.106187983**, max normalized per-cycle mean shift **.589906315**, mean-absolute max **.120923345**, uni identities all true | matched ≲.6σ / ≲.12σ / ≤11% (rounded) |
| 2-day per-pod analytic cost / closed form | **1017.897101312 GFLOP**; `300000/F` = **294.725271949 pods/TFLOP/s** | matched |
| 1-day cost / closed form | **500.975439872 GFLOP**, **598.831751266** | matched |
| 300-s raw 2-day knees sequential/overlap/batched | **429/706/1429**, adjusted sequential **416** | raw matched; basis not cited consistently |
| 180/120-s raw 2-day ranges | **257–856 / 172–571**, adjusted sequential **249/166** | raw matched; basis caveat F6 |
| 300-s 2-day energy sequential/overlap/batched | **14.968275 / 12.866330 / 10.253954 J/pod**, GPU board excess | matched 10–15 |
| Validation .971 / 1.022 “offered rate” | actual denominator **mu_hat**, offered fractions **.746676/.786023** | **mismatched** denominator |
| Universal raw 0.79–0.82 / block 0.96–1.00 | synthetic seed means **.791114–.825738 / .939968–1.0**; real memory raw lower | **mismatched** F3 |
| Real CPU block coverage, b6 (b4xkt/m7pr8) | **.021052632 / .015789474** | matched “~.02” |
| Mac full B1/B2 completed | both named files **absent** | **mismatched** F2 |

### One-real-shard bounded recomputation: exact method and literal results

Read only `artifacts/refcompare/real_b4xkt_-_11520_multi.npz` and packaged b4xkt CPU; retained its six-day slice and shard origin; used the existing counter `build_blocks`, each cycle's `causal_grid`, `counter_scale(...,576,20)`, and `block_aggregate(...)[b6]`. No forecast inference or score-chain replay. Venv Python `-B`, `PYTHONDONTWRITEBYTECODE=1`, one BLAS/OMP thread. Result:

```text
origin 1793679900.0 cycles 190
raw gap min/median/mean/max 10.001999855 15.871999979 16.338196476 34.538000107
scale min/median/max 1.089382163 1.092970685 1.097103558
CPU b6 coverage 0.021052631578947368
block obs sd 1.0861285447367168
median band width 0.03228440409329991
error mean/sd 0.025786578331272868 1.0876078626169998
miss below/above 0.5631578947368421 0.41578947368421054
heldout observed/grid-block ratio p05/50/95 [0.99177475 1.08233435 1.22388422]
elapsed_s 1.168
returncode 0
```

This independently reproduces the JSON's 4/190 CPU coverage and demonstrates the unresolved hand-off problem without changing laws or retuning anything.

## Recommendation sentence-by-sentence audit ledger

Each nonempty prose/table line of the 67-line recommendation was read; the grouped ledger covers every substantive statement, not only the sampled numbers.

| Lines / statements | Evidence assessment |
|---|---|
| 3–5 authorship, vocabulary, A/B/C definitions, evidence references | Authorship matches Supervisor attribution and commit; D-A boundaries correct. C uses regular-grid raw-cadence input, clarified later. Licence note actually lives in lab-root markdown, not alongside the study notes; give its explicit relative path. |
| 9 no C adoption; offline/shadow; licence; small/mixed; compute | No production adoption supported; shadow permission fails F1. Small/mixed is a defensible qualified judgment, not an occupancy equivalence bound. V=4 CPU timing unsupported, F6. |
| 10 no B adoption; mechanism; one more iteration | Regression verdict supported. “Mechanism right” is supported specifically by drift MAE reductions; a width-floor iteration is an untested proposal. |
| 11–12 keep A, two levers not reference, no package/SARIMA | Keeping A/no cutover follows evidence and constraints. Exclusive attribution to non-reference components overclaims (F9). Deferral is a decision, not a measured SARIMA comparison. |
| 16 synthetic matrix/common valid set | Correct offset/seeds/context; “common valid set” must retain each-row own-scored-set/availability qualification, not imply matched observations. |
| 17 synthetic/real flat/verdicts/pooling | Quoted numbers match; deployed A 10/10 and per-pod C failure must remain explicit; pooled “about equal” is not per-pod equivalence (F11). |
| 18 burst/drift/S3 latencies | Quoted S4 E0 and S2 numbers match; add E1 and S3 long-window versus pulse-local distinction (F7). |
| 19–20 universal occupancy/net judgment | Universal closeness and unqualified tie/no-change statements not supported (F7); net assessment needs gate-aware qualification. |
| 22 structural MAEs, unchanged decisions, mechanism/generalisation | MAE ratios match; not one-step; quiet occupancies remain similarly high but neither equal nor formally equivalent. Mechanism labels are descriptive, not independent causal identification (F7/F9). |
| 24 raw/block/PIT/asymmetry/width/chain/CPU/masking | Masking bounds match on the frozen plans. Universal calibration/width scope fails F3; unresolved CPU anomaly is real, constant-bias causal explanation unsupported F4. Residual-skew co-variation is not universal: note itself gives mostly negative synthetic quiet rx skew and positive S4/real skew; avoid claiming a single matched skew mechanism. |
| 26 GPU hardware/cost/pods/energy/Phase D/normalization/CPU/STL | Analytic FLOPs, raw knees, energy and normalized closed form match; extrapolation/shared-host/same-host caveats good. Use consistent adjusted knees and correct validation denominator. Mandatory Mac remains incomplete (F2/F6). STL figures are reference-refit timing scope, not a measured cross-device end-to-end comparison. |
| 30–39 B table and strict improvement/regression/guard | MAE/occupancy/outside-narrow-band numbers match. Guard identical recorded; strict drift improvement exists even gate on, so “limited” is appropriate, not “gain unreachable.” Label flat metric, onset quantity, and whole-scenario gate fraction (F8). |
| 43–54 three-way table | Numerical rows mostly reflect discussed summaries, but protocols differ. B structural “not measured” is false; A calibrated-by-construction false; CPU V=4 and uniform latency differences require correction (F3/F6/F8). “Production-ready A” means already deployed, not passing all controls; B/C no adoption supported. |
| 57 p_raw yardstick/mapper/invisible calibration gains | Raw common-chain yardstick appropriate; final sentence contradicts visible FLAT gains and needs F9 replacement. |
| 58 S1 not discriminating/unresolved/not evidence for C | Appropriately bounded to this synthetic case, numerically matched, but own-scored ticks and gate availability/mechanism caveat required (F7). Not a proof of universal indistinguishability. |
| 59 real cluster/package/burst/no real anomaly data | One fleet/data period and absent ground-truth real anomaly validation are appropriate limits; distinguish package/input/scored duration (F11). No independent new S4-real replay was run by RV. |
| 60 regular 15 s grid/causal resampling/no uncertainty interface | Consistent with D8 and prior causal-shard review; no new resampling/inference claim made here. |
| 61 power scopes/shared tester host | Correct qualification. |
| 62 independent review/closure | Prior reviews are not this stage-2 review; findings and missing mandatory CPU gate remain open (F2/F11). |
| 65–67 keep A/follow-ups/P6 independent | Supported as decisions/proposals, subject to unresolved final-gate status. TimesFM-2.5 is an unmeasured future option, not an evidence-backed winner. P6 independence/separate gate appropriate; no production change authorized by this review. |

## D-A vocabulary and actual figure inspection

- Exact case-insensitive search over the **four current notes plus five current JSONs** for `false[-_ ]positive`, standalone `FPR`, and `p_raw/p > .2 ... detect` returned **“No matches found.”** Active score labels use decisively normal / undecidable / decisively anomalous and leave-normal versus decisive latency. Historical evidence sections still quote old `FPR` terminology (e.g. E-C3:1001); these are historical descriptions, not the active metric. Clean them or clearly mark historical/superseded if an absolute no-retired-word report is required.
- **Opened `c4-bands-S1-multi.png` (1980×1410):** CPU/mem/rx observed and forecast traces with outer/inner bands, residual and per-metric p rows, and log p_raw strip. Header says **15/755 quiet undecidable**, **296/755 decisively anomalous**, no anomaly events; strip shows long ~.99 episodes. Both .2/.8 lines are labelled decisive-normal/anomaly boundaries; legend explicitly uses `<.2`, `[.2,.8]`, `>.8`. No false-positive/detection-at-.2 label. The upper observed/reference legend has duplicate “model unavailable” entries and no explicit quantile-level key; that is less important than the genuine fan timeline issue.
- **Opened `c4-bands-realflat-b4xkt.png` (1980×1800):** block CPU/mem/rx row, first/middle/last raw fans, bottom tfm-multi p_raw near .001–.004. Both boundary labels and the three-class legend are correct. CPU observed blocks vary far more than their very narrow band. All three fan rows are compressed near the same early epoch, exposing F5; this is not a usable 65-minute diagnostic view.
- **Opened `candb-s2-trend.png` (1980×1410):** two rows, gate-on/off; left memory clean level versus A blue and B red served forecasts, right overlaid p_raw. B follows drift better where served; gate-on forecast disappears during the gated region. Correct three-class legend and .2/.8 labelled lines; grey “no model” shading; no retired threshold semantics. The p_raw plot uses the same colors for arms and class legend, so read arms from the paired forecast legend, but no extra finding on style.

## Test-quality and invariant checks (read, not executed)

- Read C4 tests `tests/test_refcompare_run_c4.py:214-235,266-279`: explicit verbatim join checks and deleted-mechanism/deleted-normal-key failure cases. Independent real JSON comparison gave 180 copied profile fields with 0 mismatches; tests are not merely file-existence checks.
- Read cand-B test `tests/test_candb_run.py:137-155`: tampers B's fit_end and expects a named `ValueError`. Committed full-run assertions: `fit_end_equal=True`, `guard_equal=True`; A-to-Part1 comparison status is the string **"true"**, with **45 compared cells, [] mismatches**. Do not mistake the string for an independently rerun assertion here.
- Read hand-off code and block-law comments; the historical scalar conversion is explicit and causal, not a hidden threshold retune. Prior D-S9 permits conclusions on frozen masking plans only; this review does not silently clear the outstanding boundary-library issue.
- C4 figure tests that check bytes/heights/shared parser behavior do not detect wrong epoch origins or the collapse of local fan axes; F5 recommends the behavior assertion that is missing.

## Flat-control re-assertion and provenance

Literal read-only production commands:

```text
$ git -C /Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector rev-parse --short HEAD
5bcc7f9
$ git -C /Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector status --short
 M AGENTS.md
?? analyser/agent-orchestration/
?? markdown/2026-11-06-solo-dashboard-operations-report.md
```

These are exactly the three pre-existing paths specified by the assignment; no new production-path change appears. Read-only lab-history enumeration found **298 distinct changed paths**, all under `.gitignore`, `markdown/`, or `reference-model-study/`; **no production/analyser paths, no tracked gitlinks or symlinks**. The seven named delivery commits' file scopes are wholly within the lab. This confirms the requested repository-level invariant (not an assertion that HEAD alone can audit arbitrary historical external filesystem writes).

Current on-disk bytes equalled the named git snapshot for all nine checked JSON/note artifacts (three C3 JSONs, C3 note, C4 JSON/note, B JSON/note, final recommendation). Provenance therefore refers to the requested deliveries, not an unlabelled later rewrite.

Session-log inspection under `~/.omp/agent/sessions/-Work-langGraph-appthrust-agent-orchestration/2026-11-09T02-44-20-192Z_01a1be31-3c60-74d1-85d8-c7089d10ed2e/`:

| Session | `model_change.model` and assistant-message model | Fallback |
|---|---|---|
| `RefmEC3s2a` | `vllm-tp2-local/qwen3.8-27b-q4-gpukv-native` | false |
| `RefmEC3note` | same | false |
| `RefmEC4s2a` | same | false |
| `RefmEC4s2b` | same | false |
| `RefmECB41` | same | false |
| `RefmECB42` | same | false |
| `RefmECB44` | same | false |

Those are all discovered `RefmECB4*` JSONL sessions; there is no separate discovered ECB43 session. ECB42's log contains the CB-4.3 commit `641753d`; ECB44 contains the measurement/note delivery. Every observed assistant model in these sessions was the configured local Qwen model; **no observed D15-type executor model/fallback deviation in these slices**. Supervisor-authored `ef09474` is explicitly attributed to Sonnet, not misrepresented as Qwen execution. Historical D15 deviations remain historical and are not erased by this finding.

## Final answer to the operator-readiness question

**The no-cutover recommendation is supported; the recommendation is not supported in all its claims as written.** Before the operator reads it as a completed scientific judgment, the Supervisor should correct the production-shadow licence permission, explicitly disclose the mandatory unfinished Mac CPU comparison, narrow the calibration/occupancy/causal claims, correct compute validation denominators and raw/adjusted knee basis, distinguish B's flat metrics and separately measured structural results, and list unresolved review findings rather than claiming closure. Keep A pending those corrections; neither the existing evidence nor this advisory review authorizes a production detector change.
