# RV Review — SOLO-REFM / D-B (stages 1 and 2 only)

- Date: 2026-11-10
- Disposition: **accepted_with_findings** (advisory; Supervisor decides).
- Reviewed commits: `7c78f0b`, `25752fc`, `dd9c255`, `48f8050`, `d233b45`, `7ea2966`, `496255c`; baseline `7c78f0b^ = 1d01aed`.
- **Stage 3 is excluded.** This does not approve the not-yet-rewritten limitation-profile note.
- File references below are relative to the lab's `reference-model-study/`, unless explicitly orchestration evidence. Concurrent C1 changes were excluded. Before execution, a scoped diff against `496255c` was empty for harness, plotting, their tests, the verifier, harness YAML, reference and scenarios; those executed paths therefore matched the reviewed committed state.

## Findings

### F1 — should-fix: injected attribution uses future episode ticks, not the card's per-tick rule

**`src/refstudy/harness/mechanism.py:106-107,144-150`; `tests/test_harness_mechanism.py:59-64`; orchestration `evidence/omp-workcards/refm-DB.md:21`.** The card says tick `k` is injected iff `!quiet[k] || !quiet[e0]`. The implementation instead labels the **entire** episode injected if **any** episode tick is non-quiet. Thus a decisive episode that starts before a later injection retrospectively calls its earlier quiet ticks true detections. Controlled probe: three consecutive decisive ticks, quiet `[True, True, False]`, no model outage: implementation `[0,0,0]`; literal card `[2,2,0]` (0 injected, 2 fresh). This mismatch is deliberately asserted by the existing late-span test, so green tests do not establish card compliance here. The independently recomputed S1/S7 base cells have no affected ticks, so their headline counts are not disputed by this finding.

**Fix:** implement the card's per-tick injected precedence and split exported classified runs when the class changes within a decisive episode; add a quiet-prefix-before-injection regression. Alternatively, the Supervisor must explicitly amend the card/interpretation to uniform whole-episode attribution before reusing that taxonomy; do not silently equate pre-injection ticks with true detections.

### F2 — should-fix: the onset tick is omitted from the specified no-model lookback

**`src/refstudy/harness/mechanism.py:108-110,148-149`; `tests/test_harness_mechanism.py:105-111`; card `refm-DB.md:21`.** The card includes `e0` in `no_model[max(0,e0-L) … e0]`; the implementation uses `[e0-L:e0)` and the test explicitly demands exclusion. Controlled probe with a decisive onset at tick 1 and `no_model[1]=True`: implementation `[-1,2]`, literal card `[-1,1]` (1 post-gate). This can matter when an optional continuous metric is unavailable while the mandatory metric still permits pod scoring (`reference/chain.py:354-356,488-503`); onset unavailability is not inherently impossible on a valid pod tick.

**Fix:** include the onset (`:e0+1`) and update the behavioral test, or have the Supervisor explicitly resolve the contradictory intended boundary. The independent S1/S7 probe found no actual base-cell differences between the two rules at L=12.

### F3 — should-fix: the evidence overstates lookback invariance

**Orchestration `evidence/E-reference-model-study/E-DB.md:674-676`.** “Only S7 moves … every other scenario is lookback-invariant” is false. Independent raw-chain re-derivation found S1 post/fresh = **1570/7** at L=6 and L=12, but **1571/6** at L=24; S1 seed 1 changes from 318/2 to 319/1. The committed profile already contains that change, and E-DB's earlier section at lines 188-192 reports it. S7's advertised post counts **332/473/676** at L=6/12/24 are correct.

**Fix:** correct the stage-2 evidence and report S1's small sensitivity alongside S7; preserve the honestly stored sensitivity cells. This is a reporting correction, not a reason to alter thresholds or force the counts to the prose.

### F4 — should-fix: the regenerated images do not all meet the requested visible-label check

**`src/refstudy/plotting/realfig.py:79-80,139-140`; `src/refstudy/plotting/figure.py:248-255,266-281`.** Direct PNG inspection shows S4-real has both dotted lines but **neither boundary label nor a three-class legend**; its dense numeric panel titles do not identify the classes in words. The scenario S1 and S4 strips contain the requested labels and legend, but their upper-left legend overlays/fades the “Decisive-normal boundary (0.2)” text. The 0.8 label is legible. This is an acceptance/readability defect, not a style preference. Existing real-figure tests check line coordinates/titles, not the missing legend/labels (`tests/test_harness_real.py:543-578`).

**Fix:** add an unobscured shared three-class legend and both exact boundary labels to real figures, reposition the scenario legend or lower-boundary text so they do not overlap, regenerate affected PNGs, and assert rendered visibility/non-overlap as well as text presence.

## Checks performed and literal results

### 1. Faithful numerical cutover — independently re-run

Created the requested isolated worktree with `git worktree add /tmp/rv-db-base 7c78f0b^`; copied the **committed** verifier into it. Ran its `digest` using the study venv and baseline `PYTHONPATH`, from the baseline study directory, then ran `digest` on the reviewed source. Both were bounded at 180 seconds:

```text
baseline: digest: 180 digests written /tmp/rv-db-evidence/old-digest.json
          Wall time: 45.29 seconds
reviewed: digest: 180 digests written /tmp/rv-db-evidence/new-digest.json
          Wall time: 45.79 seconds
```

Extracted baseline and `496255c` profile/S4-real/real-flat JSONs directly with `git show` into separate temporary directories, then ran:

```text
.venv/bin/python scripts/verify_part1_cutover.py compare \
  /tmp/rv-db-evidence/old/part1-profile.json /tmp/rv-db-evidence/new/part1-profile.json \
  /tmp/rv-db-evidence/old-digest.json /tmp/rv-db-evidence/new-digest.json

digests: 180/180 equal (label sets match)
reported (non-gate) items (3):
  config_sha256.harness old=44e186b18427… new=c89a972b2fe0… (expected: YAML changed by D-A)
  config_sha256.reference old=0356d2c0e3bd… new=534f8d83d148… (expected only if concurrent lab work touched config/reference.yaml)
  s4real.projected_total_seconds old=23.2734 new=22.7800 (wall time; reported, not gate-checked)
compare: all pre-existing numbers equal under the D-A rename map; class-sum and re-label invariants hold
PASS
```

This confirms pre-existing measured quantities under the verifier's rename map, not literal identity of metadata/wall times. Inspected verifier coverage of event/settling/fidelity/ESS/flat/real comparisons (`scripts/verify_part1_cutover.py:212-340,443-520`). Recursively inspected the committed profile's keys: **zero** `fpr`, `detection`, `frac_gt_thr`, or `alpha_threshold` keys. The baseline worktree was removed afterwards with `git worktree remove --force /tmp/rv-db-base`; only its deliberately copied untracked verifier required force.

### 2. Three-class semantics, guard band, thresholds

Checked `metrics.py:80-107`, `evaluate.py:102-107,241-295`, `config.py:204-233`, and the real summaries. Normal is `< alpha`, undecidable includes **both** exact edges, decisive is `> delta`; `at_alpha`/`at_decisive` are informational subset counts, not extra classes. Boundary tests exercise 0.2, 0.8, 0.8+epsilon, NaN, warm-up and excluded quiet ticks. The compared profile has zero edge ties.

Occupancies select **valid AND quiet**, with quiet excluding `[onset,end+4)` for bounded anomalies and onset through horizon for persistent anomalies. Regime changes/gaps alone remain quiet (`scenarios/truth.py:51-64`); the tests check end+3 excluded/end+4 counted. Independent S1 and S7 chain runs reconstructed the mask and all three class counts for every seed, matching the JSON for valid and quiet populations.

S1 old count over five seeds = **1677 = 100 undecided + 1577 decisive**; approximately **94.0%** of the old quantity was decisive, not undecidable. More generally the exact edge-aware identity is `old_count = undecided + decisive - at_alpha`, not an unconditional pure rename.

Scoring thresholds are required YAML keys (`config/harness.yaml:20-21`, alpha=0.2, delta=0.8); parsing rejects alpha>=delta. Evaluator and real plots receive the configuration values. A source search found no hard-coded **computational class boundaries** in harness/plotting; explanatory strings, plot sizes/styles, quantile levels and the fixed `>0.8` mechanism-table heading are not scoring computations.

### 3. Detection, censoring and independent settling calculation

`evaluate.py:104` explicitly uses `inclusive=True`: leave-normal is first valid **p>=0.2**, which agrees with the card and with leaving D-A's p<0.2 class. Decisive is first valid **p>0.8**. Both search `[onset,next onset)`; absent hits return censored, null j_star/latency and the searched horizon. Settling continues to receive **leave_normal.j_star**, not decisive.j_star (`evaluate.py:107`).

There is a documentation ambiguity, not a measured latency discrepancy: CAMPAIGN-CONTEXT D-A(ii) describes the *old* latency as first p>0.2 and the YAML header still says all quantities use strict `>` (`config/harness.yaml:5`). The card resolves the new leave-normal rule as inclusive. Future text should distinguish the old strict rule from the new inclusive one; equality does not occur in these committed runs.

Re-ran **S4 seed 1, full bounded 1872-tick horizon**, obtained p_raw directly from chain TickRecords, and independently searched hits and six-tick settling windows without calling the harness detection/settling helpers. Exact JSON matches:

```text
S4-E0-bump: leave j=1539 latency=3 horizon=216; decisive j=1540 latency=4 horizon=216
settling: settled, settle=4, s_star=1558, baseline=0.0012882714701472474, tol=0.05
S4-E1-bump: leave j=1757 latency=5 horizon=120; decisive j=1758 latency=6 horizon=120
settling: settled, settle=4, s_star=1774, baseline=0.0012881713703130904, tol=0.05
```

Censoring behavior is also tested with an exact-boundary non-decisive input and a bounded S4 fixture whose first event has no decisive crossing; the requested test suite passed.

### 4. Mechanism repair, independent finder, expected counts

The repaired run finder ends each maximal `valid & p>delta` episode at its **own last decisive tick + 1** (`mechanism.py:128-142`), so invalid ticks and non-decisive gaps split episodes. It fixes the actual slice-1.2 inter-run-gap defect. Loaded the original classifier **from `git show 25752fc:reference-model-study/src/refstudy/harness/mechanism.py` in memory**, substituted it into the new regression's globals, and executed the unchanged regression:

```text
old 25752fc classifier + unchanged new regression: FAIL (AssertionError), as required
```

The regression now passes in the requested suite. It checks that two `[100,105)` / `[110,115)` quiet decisive runs remain fresh despite non-quiet tick 105 in their gap, and that 105 remains unclassified. The repair is real, not a weakened test. One limitation of `mechanism_block`'s count-sum check (`mechanism.py:201-207`) is that summing separately found run lengths is intrinsically equal to the decisive count even if class assignments span gaps; the new targeted regression supplies the missing behavioral protection.

For **S1 and S7, all five seeds**, independently regenerated raw chain outputs, derived no-model flags directly from the per-metric reasons, constructed quiet masks from events, and used my own tick-by-tick while-loop episode finder/classifier (not `classify_decisive` or `mechanism_block`). All per-seed counts and sensitivity cells matched the committed JSON under the implemented uniform-episode rule:

```text
                         injected / post / fresh
S1 L=6:                  0 / 1570 / 7
S1 L=12:                 0 / 1570 / 7
S1 L=24:                 0 / 1571 / 6
S7 L=6:                 64 / 332 / 1796
S7 L=12:                64 / 473 / 1655
S7 L=24:                64 / 676 / 1452
```

Also ran the committed expected-count gate on the committed profile:

```text
FLAT (0,0,55) OK; S1 (0,1570,7) OK; S2 (195,0,35) OK;
S3 (2,1826,23) OK; S4 (137,0,81) OK; S5 (0,1957,22) OK;
S6 (402,1239,15) OK; S7 (64,473,1655) OK; S8 (85,0,2316) OK
check-mechanism: all 9 base scenarios match the card's expected counts
```

These match `markdown/part1-mechanism-table.md:3-11` and E-DB's stage-2 table. S7's substantial 332/473/676 lookback sensitivity is honestly stored/reported; the exclusive “only S7” claim is the defect in F3.

**Operational interpretation:** post-gate is a **recent missing-model/outage association inherited from episode onset**, not proof that stale-model scoring caused every classified tick. The proxy uses any served continuous metric's `model stale`/`model not built` reason, not explicit ESS-cycle causality or model-age/causal attribution. Fresh-model noise means the complementary class under that lookback, **not demonstrated stochastic noise**; S7/S8 contain structured-reference misfit. This implements the specified recorded-field proxy apart from F1/F2, but must not be promoted into a causal stale-model-versus-noise conclusion. In real replay, quiet is all true, so even the observed detector-side episode is a residual class, not a known injected anomaly.

### 5. Real summaries and D-A(iv)

Recomputed class counts and fractions directly from committed S4-real p_raw arrays for all ten pods. Examples:

```text
vlsl8: n=31, normal=15, undecided=5, decisive=11
       frac_undecided=0.16129032258064516; frac_decisive=0.3548387096774194
m7pr8: n=31, normal=19, undecided=4, decisive=8
       frac_undecided=0.12903225806451613; frac_decisive=0.25806451612903225
```

Recounted episode p>0.5 from the raw tick/value pairs: vlsl8=14, m7pr8=10, other eight pods=0. Thus **2/10** meet the unchanged >=8-of-15 historical episode criterion; fleet needs seven, so `partial` is consistent with the earlier 2/10 result. This historical reproduction criterion remains **0.5**, not the new decisive-anomaly boundary: do not describe “2/10 reproduced” as applying a new p>0.8 fleet test.

Recomputed pooled real-flat counts from the per-pod n_valid and fractions (no raw per-tick flat array is stored in that JSON):

```text
normal 22150 / 22450 = 0.9866369710467706
undecided 89 / 22450 = 0.003964365256124721
decisive 211 / 22450 = 0.009398663697104678
```

These exactly match pooled fields. `calm = frac_normal >= 1 - max_outside_fraction` is `0.9866369710467706 >= 0.98`, hence true; that matches **D-A(iv)**. The maximum **0.9895222052884711** and decisive occupancy are separately reported, so “calm” does **not** mean no decisive excursions. Synthetic flat summaries and real flat use the same requested normal-fraction calm criterion; narrow flat-band occupancy remains a separate diagnostic.

### 6. Direct inspection of the three requested PNGs

Opened the actual regenerated images, not reconstructed figure objects:

- `figures/part1-scenario-1.png`: diurnal observed/reference rows, orange unavailable-model intervals, residual/p rows and a bottom log-p_raw strip. Three-class legend and orange undecidable band are present; blue **Decisive-anomaly boundary (0.8)** readable. Red **Decisive-normal boundary (0.2)** exists but is obscured by the legend. Annotation says 29/732 undecided and 320/732 decisive; no FPR wording.
- `figures/part1-scenario-4.png`: two injected spikes and their residual/p responses, with post-event reference excursions; the same strip/legend/boundaries and same lower-label overlap. Annotation shows leave/decisive latencies 3/4 and 5/6, settle=4, and mechanisms 27 injected/0 post/16 fresh. No FPR wording.
- `figures/part1-s4real.png`: ten pod panels, grey recorded versus blue lab traces, pale-red episode shading; only vlsl8 and m7pr8 lab traces reproduce the large episode while the others remain near the floor. Header says partial, 2/10. Red/blue boundary lines visible, but the requested named boundaries and three-class legend are absent (F4). No FPR wording.

### 7. Behavioral tests and lint

Ran the assignment's bounded command, not the full unrelated/refcompare suite:

```text
.venv/bin/python -m pytest tests/test_harness_*.py tests/test_plotting_*.py -q
........................................................................ [ 30%]
........................................................................ [ 60%]
........................................................................ [ 90%]
......................                                                   [100%]
Wall time: 25.52 seconds
```

Exit 0; 238 dot cases, no failures/errors/skip markers (the configured quiet output omits the usual summary). Reviewed actual behavioral assertions for boundary ties, inclusive leave-normal, decisive censoring, guard edges, on-cycle/no-model equality, split episodes, quantiles and real-class summaries. These are not merely import/wiring tests; F1/F2 identify where the asserted behavior itself conflicts with the card, and F4 identifies missing visual assertions.

```text
.venv/bin/ruff check src/refstudy/harness src/refstudy/plotting \
  tests/test_harness_*.py tests/test_plotting_*.py \
  scripts/run_part1.py scripts/verify_part1_cutover.py
All checks passed!
```

### 8. Campaign invariants

- **No D-B chain-law change:** each of the seven named commits has an empty diff for `src/refstudy/reference/`, `src/refstudy/scenarios/` and `data/`. D-B's only changed YAML values concern reporting/mechanism configuration, not chain laws.
- **Important scope correction:** the requested *whole history range* stat is **not empty**. `git diff --stat 7c78f0b^..496255c -- src/refstudy/reference src/refstudy/scenarios` from the study directory is equivalent to the command I ran with repository-root-prefixed paths, and reports reference config/STL/trend/trend_select changes: **4 files, 750 insertions, 6 deletions**. Those belong to interleaved cand-B commits (`482e3ea`, `5843a09`, `c8c1b9f`), not D-B. Scenarios remain untouched. I checked the seven D-B commits individually rather than falsely certifying the whole range empty. The 180/180 raw digests additionally establish unchanged default outputs despite that interleaving.
- **Yardstick = p_raw:** evaluator metrics consume TickRecord.p_raw; no published/calibrated mapper output is substituted. The independent recomputation also used p_raw directly.
- **0.2/0.8 unchanged:** YAML reports the original operator boundaries; class endpoints are as D-A requires. The intentional inclusive leave-normal reporting change is not a threshold/law change and changes no measured legacy run because there are no ties.
- **Production read-only:** no named commit changes production; all tracked reviewed changes reside in the lab. This review made no production edit, production execution, SSH/cluster/GPU call, commit, service action, or lab implementation edit. Only this review record is a persistent project deliverable; the explicitly requested temporary baseline worktree was removed.

### 9. Executor model provenance

Read model-change records **and actual assistant-message provider/model fields** in:

`~/.omp/agent/sessions/-Work-langGraph-appthrust-agent-orchestration/2026-11-09T02-44-20-192Z_01a1be31-3c60-74d1-85d8-c7089d10ed2e/{RefmEDB11,RefmEDB12,RefmEDB13,RefmEDB14,RefmEDB15,RefmEDB16,RefmEDB2}.jsonl`.

All seven sessions report **`vllm-tp2-local/qwen3.8-27b-q4-gpukv-native`**, `resolvedModelIsFallback=false`, with no model switches; assistant-message counts respectively 50/58/95/143/95/102/237 all name that same provider/model. Thus slices 1.1-1.6 **and** stage 2 ran on configured local Qwen, not a hidden stronger-model fallback. The original episode-boundary bug was introduced in a Qwen session and repaired in another Qwen session. It is an ordinary interval-construction/test-coverage defect; these logs do not establish model-specific causation. Any claim that quantisation or this model family caused it would be **[INFERENCE]**, unsupported here.

## Disposition rationale and downstream safety

The numerical cutover is substantiated: byte-identical raw outputs across all 180 planned runs, pre-existing measured summaries preserved, correct D-A class endpoints, independently reproduced latency/settling and real-data summaries, a genuine regression-tested gap repair, and passing requested behavioral/lint checks. No blocker to using those **numerical** outputs was found. The remaining findings concern two explicit mechanism-contract mismatches, an overstated sensitivity claim, and missing/obscured visual semantics; acceptance is not approval of those defects or of stage 3.

**The re-expressed Part-1 p_raw/class/latency/settling yardstick is safe for C3/C4 stage 2 and cand-B (CB-4) to build on, with caveats: resolve F1/F2 before treating the mechanism classifier as card-faithful; use post-gate/fresh-model noise only as observational proxy categories, retain gate-on/off population differences and the S1/S7 lookback sensitivity, correct F3/F4 before publishing the profile, and do not treat the pending stage-3 narrative or unrelated C1/C3 correctness gates as approved by this review.**
