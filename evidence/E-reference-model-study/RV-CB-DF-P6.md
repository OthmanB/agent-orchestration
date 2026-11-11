# RV review — cand-B CB-1..CB-3, D-F, and P6 production plan

- Reviewer: RV (`RefmRVCB`), 2026-11-10. Findings are **advisory**; S decides.
- Dispositions: **CB-1..CB-3: accepted_with_findings; D-F: accepted_with_findings; P6 plan: accepted_with_findings**. No implementation blocker found in CB/DF; P6 has no execution-blocking design finding, but remains subject to S's evidence-freeze/release gate.
- Scope: the eight assigned lab commits, cards, research, execution evidence, D-S5/D-F/amended D-D and accepted defaults. Production HEAD observed: `5bcc7f9128d55e38d3c09838b3af0699edc4973b`. No production file, cluster, GPU host, or service was modified/accessed. No commit/push. The only lab write was the expressly requested parity result regeneration followed by restoration; scratch experiments are under `/tmp`.

## 1. Candidate B — CB-1..CB-3

Reviewed `482e3ea`, `5843a09`, `c8c1b9f`, `refm-CB.md`, `E-CB.md`, `R-candB.md`, and D-S5. CB-4 measurements/recommendation are not part of this disposition.

### Checks performed and literal results

From the lab's `reference-model-study/`:

```text
.venv/bin/python scripts/run_parity.py --config config/reference.yaml --stage 1
exit 0; stage-1 subprocess: ......... [100%]
P0 0 (n_keys=29); P1 0; P2 0 (n_blocks=912); P2a 0 (n_cases=48)
P2b_counter 0 (n_cold=3, n_cycles=27, n_steady=24)
P2b_gauge 0; P2b_rare_count 0; P3 0 (n_scored=713)
P4: all ten pods passed=True, replay_unexplained=0, p_family_after_prefix=0
.venv/bin/python -m pytest -m parity -q
............................... [100%]  [exit 0]
.venv/bin/python -m pytest tests/test_reference_trend*.py tests/test_reference_trend_select.py tests/test_reference_trend_provider.py -q
................................................................. [100%]  [exit 0]
```

The final command exercises 65 tests (pytest deduplicates the explicitly repeated files); the parity command exercises 31. Stage 1 alone does not re-exercise P3/P4, but the subsequent full parity selection does. The displayed P4 aggregate `22` is an existing diagnostic maximum, not 22 unexplained replay failures.

Independent recursive numeric comparison of the rewritten `results/a1a-parity.json` against `git show HEAD:reference-model-study/results/a1a-parity.json`:

```text
parity differences: 60 critical: 0 non-wall: 0
non-wall differences: []
git restore results/a1a-parity.json  [exit 0]
```

Thus every delta/mismatch/unexplained/strict/comparable/ESS/fit-end result, including P4b, is unchanged; only 60 `wall_seconds` leaves differed. Restoration was performed only after this comparison.

Independent script `/tmp/rv_cb_independent.py` recomputed SHA-256 from the eight `ReferenceRun` array byte buffers for six scenarios × four continuous signals, without importing the test's `digests()` function:

```text
COMMITTED BOXCAR DIGESTS: 192 / 192 EXACT MATCH
```

The disk fixture also equals the fixture in **commit `482e3ea`**, including `generated_at_head=25752fc4a859c51d5f5204adff7905e126fae322`. This is a committed pre-provider-change oracle, not a fixture regenerated against the reviewed adaptive code.

Independent truncation/causality tests:

- `/tmp/rv_cb_independent.py`: 28 selected-width comparisons after scrambling all blocks at/after the served scored block, using the emitted fit-window prefix; identical selected widths and candidate scores. Nine ESS probes (S1/cpu, S2/mem, FLAT/cpu; offsets 0/48/96, K=570) all select the smallest width, 6: `ess degenerate: 9 /9`.
- `/tmp/rv_cb_served_cutoff.py`: additionally ran the **actual provider**, not merely the selector on a manually truncated array. For first/middle/last built cycles in each scenario, replace every value at/after the scored block by large seeded noise, run only through the target tick, and compare selected width, served forecast, and record. Literal result: `ACTUAL PROVIDER CUTOFF CHECKS: 9/9 PASS` (includes finite-width and sentinel cases).
- Full 1,872-tick, seed-1 A/B runs: `S1 cpu ... A/B gated 94 94 identical; check_no_leakage PASS`; `S2 mem ... A/B gated 76 76 identical; check_no_leakage PASS`; `FLAT cpu ... A/B gated 0 0 identical; check_no_leakage PASS`. `fit_end`, `model_t0`, and `ess` arrays compare exactly, NaN-safe. Initial 1,158-tick runs also confirmed the same `ReferenceRun` field names and per-field shapes. The committed provider tests independently cover S1/S2/FLAT cpu.

Independent record recomputation used scalar `np.mean` of explicit preceding slices and explicit phase-bin residual lists, **neither `AdaptiveStlState.fit` nor the adaptive residual helper**. Conditional on the reported width W, it computed `y_i - (mean(y[max(0,i-W):i]) + centred_mean_of_prior_detrended_residuals_in_bin_i)`:

```text
cold record entry 137 width 11
stored 0.09340244863329161; independent 0.09340244863334846
abs_delta 5.684341886080802e-14
steady record entry 527 width 11
stored -0.7325603940716086; independent -0.7325603940718288
abs_delta 2.2026824808563106e-13
```

Both are below `1e-9`. Source `reference/stl_lite.py:395-413,487-490,510-514` appends exactly the last `len(new_r)` entries for finite-width cycles; retained entries are not recomputed. The existing test additionally checks all 522 cold entries and the next steady cycle's six entered entries.

### Routing, vision deviations, and test quality

- Reviewed the actual `c8c1b9f` integration diff: H1 imports at `stl_lite.py:29-34`; H2 `CycleReport.trend_width` at 314; H3 `_Prior.served` at 328; H4 separate adaptive state at 121-241; H5 config dispatch at 350-358; H6 selection/adoption at 478/490/514/518/531; H7 serving at 591-594. Legacy `StlLiteState.update/forget/forecast` arithmetic is not rewritten. ESS gate remains **before** selection (`473-478`).
- Sentinel and boxcar serve `prior.F`; `_adopt` returns the original legacy residual list for `sel is None` or sentinel. The forced-sentinel provider test compares all eight arrays exactly on three scenarios; it passed. No adaptive numerical kernel or width scan executes for boxcar, although dispatch hooks do execute (finding CB-F1).
- The key deviations are clearly stated in the card: exclusive record trend (`refm-CB.md:10`), corrected MAE/cv1 rather than ESS argmax (`14`), `[30 min,12 h]`, explicitly not the stray `[8 h,12 h]` (`16`). Evidence states exclusive vs inclusive semantics (`E-CB.md:43-54,395`), diagnostic-only degenerate ESS versus cv1 (`239-244,267-274`), and uses the actual 30/720-minute adaptive configuration (`400`). This is faithful to **D-S5**, not an unacknowledged implementation of the original contradictory vision.
- Warm-up, structural fallback, sentinel special case, unchanged guard/staleness, and reuse of the existing `gauge_epsilon` are explicit. In particular, the card correctly rejects R-candB contradiction 8 for the lab; `reference.yaml:88` has that constant. The later CB-4 note/vision-deviation synthesis is intentionally outside this review.
- Tests are substantive: explicit-loop primitive oracle, committed byte digests, strict config/missing-key cases, ESS degeneracy, sentinel equivalence, independent-prefix record construction, deterministic repeats, and gate-set equality. A distinction matters: candidate forecasts are prefix-causal, but the CV loss necessarily reads its target, and a width fitted to the whole training window is not a historical prefix-selected width (CB-F2).

### Findings

1. **CB-F1 — should-fix, documentation/contract accuracy:** `src/refstudy/reference/stl_lite.py:360-361`, `tests/test_reference_trend_provider.py:5-7`, `E-CB.md:439`, and `refm-CB.md:31` say boxcar “executes none” of the new hooks/code. In fact `_select` is called at 478, `_adopt` at 490/514, H5 stores dispatch state, and H7 chooses `prior.F`. The numeric no-regression claim is proven, but the literal execution claim is false. **Fix:** say “executes no adaptive numerical work; dispatch hooks return identity/legacy values.” If S requires literally zero hook calls, that is a different requirement and requires guarded callsites, not the present evidence wording.
2. **CB-F2 — should-fix, causality claim precision:** `src/refstudy/reference/trend_select.py:41-45` says `e_i` depends only on blocks `< i`, and `E-CB.md:297-300` concludes that the selection depends on block i only through older blocks. `e_i = y_i - F_i` necessarily depends on `y_i`, and the selected width depends on every target in the fitted training window (`trend_select.py:183-204`). **Fix:** distinguish prefix-causal **candidate forecasts** from target-dependent CV residuals/losses and full-window width selection; state leakage safety at the **served tick's fit cutoff**, which the independent scramble tests above actually establish. No demand for nested CV or change to D-S5's specified algorithm.

**Rationale:** specified numerical behavior, corrected criterion, causal serving, record rule, guard equality, sentinel equivalence, and bit-exact default all pass. Findings correct scientific/contract claims rather than the accepted algorithm.

## 2. D-F — hardware-normalized B2 read-off

Reviewed `c5fba0f`, `e9d612f`, `60628d1`, `b2a8165`, `3f3ac04`, `refm-DF.md`, `E-DF.md`, and operator D-F.

### Independent arithmetic from the source JSONs

Read `b1-scaling-cuda.json`, `b1-flopcount.json`, and `b2-refresh-cuda.json`. Did **not** use `Normalizer`, `build_table`, `find_knee`, or `forecast_flops` for the independent recomputation. With P=330710976, d=1280, L=20, V=4, H=120, stitched horizon adds four patches, so `n=ceil(N/32)+4` and `F=2PVn+4n²dLV+4V²dLn`.

| N | n | per-pod GFLOP F | flop-counter GFLOP | counter/analytic | G = F / B1 median seconds |
|---|---:|---:|---:|---:|---:|
| 5760 | 184 | 500.975439872 | 500.734455808 | 0.999518970303092 | 2459.445595588 GFLOP/s |
| 11520 | 364 | 1017.897101312 | 1017.420371968 | 0.999531652714812 | 2597.947224908 GFLOP/s |

Analytic F exactly matches the B1 cells. At 300 s, transferable normalization is `300/F` pods per GFLOP/s, or `300*1000/F` pods per TFLOP/s. Machine prediction multiplies by G: **`300*G/F`** (not division by G).

| N | closed form pods/TFLOP/s | closed form pods at B1 G |
|---|---:|---:|
| 5760 | 598.831751266 | 1472.794113150 |
| 11520 | 294.725271949 | 765.680702369 |

Re-fitted raw B2 PASS burst points with independent scalar least-squares sums, solved `(300-intercept)/slope`, floored, and applied the existing sustained-ratio adjustment. Every 300-s knee exceeds the largest measured pod count, so interpolation of `mean_w` and J/pod clamps to the last measured point. All values below match the regenerated JSON to relative tolerance `1e-10`:

| N | variant | unrounded knee | effective pods | pods/TFLOP/s | consistency ratio | mean W | pods/W [gpu_board] | J/pod |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 5760 | sequential | 734.172929 | 734 | 298.441243 | 0.498372443 | 36.645039 | 20.029996 | 7.847252 |
| 5760 | overlap | 1234.527904 | 1234 | 501.739092 | 0.837863208 | 46.224941 | 26.695545 | 6.866212 |
| 5760 | batched_overlap | 2965.160596 | 2965 | 1205.556246 | 2.013180236 | 68.020032 | 43.590100 | 4.893028 |
| 11520 | sequential | 429.942520 | 416 (adjusted) | 160.126424 | 0.543307411 | 39.269180 | 10.593549 | 14.968275 |
| 11520 | overlap | 706.581800 | 706 | 271.753018 | 0.922055366 | 49.202303 | 14.348922 | 12.866330 |
| 11520 | batched_overlap | 1429.522377 | 1429 | 550.049665 | 1.866313198 | 68.643607 | 20.817670 | 10.253954 |

All six rows have `power_scope=gpu_board` and `extrapolated=True`. Mean W includes idle; the displayed J/pod uses the existing power integration convention, not a new energy measurement.

Independent probe calculation at **N=11520 only**:

```text
b_star=32; pods_per_s=5.059694458237388
achieved GFLOP/s=5150.248322564227
gain over B1 batch-1 G=1.982429925129589
1429/(300*pods_per_s)=0.9414270708735057
```

For the two-day batched row, `1.9824299251 * 0.9414270709 = 1.866313198`, so the observed >1 ratio is numerically explained relative to this batch-1 baseline. The one-day ratio is also numerically correct, but has no same-context batch probe in these files.

### Additive-only, tests, figure

Recursive comparison of **every pre-existing key/value**, including list lengths/order, using `git show b2a8165^:.../b2-sustainable.json` versus `git show b2a8165:.../b2-sustainable.json`:

```text
additive-only old-value differences: []
old/new row counts: 30 30
reviewed sustainable commit equals disk: True
```

Thus sustainable JSON is additive-only, not merely numerically close. (Headline text is a separately permitted template change.) Targeted compute tests were also exercised:

```text
.venv/bin/python -m pytest tests/test_compute_sustain.py tests/test_compute_refresh_config.py tests/test_compute_refresh_plots.py -q
........................................................................ [ 78%]
.................... [100%]
exit 0 (92 tests)
```

Opened the actual `figures/b2-normalized.png`, not only its artist data. One CUDA column, two panels; x-axis is 2 d then 1 d. Top: blue sequential, orange overlap, green batched curves, grey closed-form ticks around 294.7 and 598.8, correct x0.54/x0.92/x1.87 and x0.50/x0.84/x2.01 annotations. Bottom: six hollow pods/W markers at the table values. `gpu_board` is present in both panels. No Mac measurement is shown. The suptitle is visibly clipped at both image edges, losing part of the qualification; top markers are labelled “measured” although every tick-300 knee is extrapolated (DF-F3).

### Explicit answer: are all statements in the note supported?

**No. The arithmetic is supported; some interpretations are too strong.** `markdown/phase-b-compute-study.md:19-31,38-45` agrees with the recomputation. The choice of B1 `gflops_s_analytic` is **defensible and clearly identified at lines 22-24**: analytic matmul work divided by actual measured latency at the same batch-1 shape is an achieved workload rate in the campaign's cost unit. It is not a theoretical hardware peak, not a FLOP-counter measurement itself, and not the saturated batched rate. The analytic/counter-rate distinction changes these cells by only 0.0481%/0.0469%. Naming the field and same-shape baseline makes the definition reproducible; the prose should explicitly retain “batch-1” at first definition.

The observed batched >1 comparison at two days is defensible; “>1 by construction,” “not hardware,” and transferring the same measured ratio to **any** machine are not established by this one GPU experiment. The note's final same-host-class qualification helps, but does not make those stronger sentences true.

### Findings

3. **DF-F1 — should-fix, unsupported inevitability/attribution:** `markdown/phase-b-compute-study.md:47-51,81-84` (also `refm-DF.md:26`) says batched ratios are >1 “by construction” and treats the displayed batched advantage as not hardware. A batch-1 denominator permits >1; it does not guarantee it. The ratio is batch gain **times** end-to-end efficiency, and can be below 1. The measured 1.9824 gain/0.9414 efficiency explains the **two-day** row only; there is no one-day probe to prove the same explanation for 2.0132. **Fix:** state this as an observed same-host result, explicitly label the probe N=11520, and mark the one-day mechanism attribution as inference. Clarify that batching efficiency depends on hardware/backend as well as pipeline scheduling.
4. **DF-F2 — should-fix, transfer recipe overclaim:** `markdown/phase-b-compute-study.md:51,53-61` calls the consistency ratio “the transfer factor” and applies the measured sequential/overlap/batched ratios to “any machine.” Fixed fetch/chain time does not scale with target model latency: even a serial model `pods≈budget/(F/G+c)` gives ratio `1/(1+cG/F)`, which changes with G for unchanged c. Batch gain is likewise machine-dependent. Lines 65-69/83-84 acknowledge limits but do not establish invariance. **Fix:** retain the hardware-independent FLOP constant and B1-based **model-bound** prediction; label old ratios as explicitly conditional scenario estimates, not validated transferable factors, and require target pipeline/batch characterization before claiming target wall-clock capacity. No new measurement is requested for this D-F correction.
5. **DF-F3 — should-fix, figure provenance/legibility:** `scripts/plot_refresh.py:334-336,375-385,445-450` and `markdown/phase-b-compute-study.md:34` call values measured; the saved figure clips the long suptitle, while all six underlying rows are `extrapolated=true`. The note correctly calls these predictions at 68-69, but the standalone figure/table heading contradicts it. **Fix:** label these as fitted/extrapolated read-offs, carry that status in the top-panel marker legend/caption as well as bottom hollow markers, and wrap/fit the title so its qualification survives saving. This concerns provenance visibility, not aesthetic preference.

**Rationale:** additive table implementation, arithmetic, power scope, and tests pass; the scientific note/figure need bounded claims before being used as a hardware-transfer recommendation.

## 3. P6 — production workcard review before execution

Reviewed `solo-ops-P6.md`, `solo-ops-P6-slices.md`, `R-P6.md`, amended D-D, accepted Q1-Q7, and the production sources at the pinned HEAD. This is **plan acceptance, not implementation acceptance**: no retention or scored-tick feature has yet been exercised in production code.

### Verified source facts (more than the required eight)

All paths in this table are relative to the production repo unless prefixed `lab/`.

| Fact checked | Source and result |
|---|---|
| 1. Raw schema/index duplication | `analyser/solo_mode/window_store.py:143-160`: PK `(pod_key,metric_name,ts_epoch)` and explicit index on precisely that triple. Scratch confirms substitution by the autoindex. |
| 2. SQLite/store lock model | `window_store.py:96-104,125-132`; `state.py:58-70`: separate cross-thread connections and per-store RLocks. `driver.py:125-139,176-189` opens both against one resolved file. WAL does not eliminate SQLite's single-writer contention. |
| 3. Existing O(window) hot path | `window_store.py:268-282`: `_merge_episodes` loads the whole stream, with no timestamp predicate, before building `stored_by_ts`. P6 explicitly leaves this untouched and adds no raw-window query to scoring inserts. |
| 4. Current raw trim | `scan.py:2413-2416,2684-2686`; `window_store.py:429-442`: delete before `fit_start` (counter: subtract `counter_max_gap_s`). Registered scope is filtered at `scan.py:2418-2427`; fetch failures continue before trim at 2606-2610/2635-2640. TTL is a backstop, not seven-day retention for active streams. |
| 5. ESS rejection persists no failure record | `scan.py:1320-1332`: logs and returns None below the configured floor; deployed floor is 36 at `deploy/k8s/solo-card6/configmap.yaml:326`, not research's 60. |
| 6. Freshness | `driver.py:1081-1085`: model only scores within `[t0,t0+dt)`; a stale metric returns no score. Thus scored `model_age_seconds` alone cannot reveal long stale periods. |
| 7. Mandatory CPU route | ConfigMap `366-367` mandates CPU. `driver.py:1493-1520` sends an unready CPU to `record_skipped_tick`; second no-eligible branch at 1527-1547 does the same. Neither reaches `complete_scored_tick` at 1906. |
| 8. Missing history on skipped route | `state.py:583-624`: skipped path writes the Markov/dedupe marker but no history. It also lacks rollback-on-error today. S2 correctly adds the writer and rollback on this path, not only the scored path. |
| 9. Existing scored transaction | `state.py:694-810`: history, Markov, and calibration are committed together; failure rolls all back. Planned metric upsert before that commit preserves the unit. |
| 10. Scoring-model provenance | `driver.py:1334-1349`: ESS/t0/age/method come from the captured model actually used. S2 uses those values for scored rows, only consulting the persisted t0 fallback for unscored rows. |
| 11. Metric publication strip | `driver.py:1962-1967`: `_public_metrics` strips private keys and `unready`, not the p/ESS/reason/model fields needed by `metric_tick_rows`. |
| 12. Ring depth | `driver.py:300-307`: `max(1,depth_seconds//T)`. `state.py:743-753` retains the newest depth rows per pod. One day at 300 s is 288, so two rings require 576 ticks/172800 s. |
| 13. Validator insertion point | `config.py:429-430,473,930-943`: `Dt_seconds`, derived `tick_seconds`, and `depth_seconds` exist in the same validator scope. Existing duration helper at 120-139 rejects non-string/nonpositive/unsupported units. |
| 14. Runtime ownership | `driver.py:2185-2226`: existing `SoloRuntime` daemon is ingest/refit work. S4 adds a separate daemon rather than a TTL sweep inside that tick path. |

### Scratch SQLite verification

Executed `/tmp/rv_p6_sqlite.py` using `/tmp/solo-p3-venv/bin/python`, SQLite **3.54.1**, scratch databases only. It extracts the actual table/index DDL from the repo AST rather than inventing a simplified raw schema.

```text
raw rows 11000
indexes before: idx_solo_window_points_key; sqlite_autoindex_solo_window_points_1
```

For each of the five current query shapes—full-stream merge select, bounded ordered read, slide-drop delete, max timestamp, count—`EXPLAIN QUERY PLAN` uses `idx_solo_window_points_key` before DROP and `sqlite_autoindex_solo_window_points_1` afterwards with the same equality/range search geometry. Max/count remain covering-index searches. A distinct SQL statement after DROP avoids falsely reporting a cached old plan. This corroborates redundancy; it does not claim to reproduce the live 178 MB index measurement.

Created the exact planned eight-column scored table with all 11 canonical metric names, 10 pods × 2016 ticks = **221,760 rows**, 85-character pod keys, realistic REAL values and `model:stl_lite` provenance. Independent measured file allocation:

```text
rowid:        bytes 78553088; B/row 354.2256854256854
WITHOUT ROWID: bytes 45064192; B/row 203.21154401154402
```

`dbstat` assigns 45,060,096 B to the WITHOUT ROWID table (the file includes one schema page). These measurements support the card's approximate 358 vs 205 B/row and ≤260 B/row acceptance, not research's old 130 B estimate. Different numeric/key distributions explain small differences; they do not reverse the conclusion. The card's literal example pod string is actually 87 characters: the 87-character run measured **360.4502 vs 207.5521 B/row**, also safely below the planned cap.

### Plan consistency, scope, and readiness

- **Validation:** seven required retention keys, explicit allowed-key set, no hidden code default; all seven missing-key cases plus the absent block and unknown-key rejection are specified (`slices:7-15`). Arithmetic independently reproduced: lookback `172800+43200+300=216300 s`; raw floor **540750 s**, below seven-day 604800 s; headroom factor **2.7961165**. Scored floor **172800 s** = twice the exact derived ring depth. Boundary tests immediately below/at both floors are specified. `counter_max_gap_s<T` is already validated (`config.py:879-883`), so the extra T in the lookback bound covers that raw predecessor headroom. Required runtime indexing fails rather than inventing defaults.
- **Writer cost:** S2's one PK-prefix query for model t0s and ≤11 upserts is O(number of configured metrics × log table size), not literally constant-time and not an O(raw-window) scan. That is consistent with “O(small)” and preserves `_merge_episodes`. Required keyword-only arguments force migration of both skip calls and the scored call; exhaustive caller search also found the direct calls in `tests/unit/test_solo_state.py`, which S2 explicitly migrates. No extra commit per metric is proposed.
- **Sweep/locking:** S3's per-pod/per-metric index seeks and bounded timestamp subquery avoid a global old-row scan; each delete commits under its store lock and releases both transaction and lock **before** the pause. A separate mid-tick daemon reduces boundary contention but is not a scheduling guarantee. The structural pause test using both another thread and another connection, plus the ≤0.5 s writer-latency backlog test, is appropriate for the actual separate-lock/single-file model. I reviewed this design; I did not claim to rerun the planner's 1.166 M-row concurrency benchmark or exercise unimplemented production sweep code.
- **Coverage:** tests specify scored **and skipped** persistence, gated CPU rows, failure rollback, upsert/idempotence, migration warning/INFO behavior, file-DB restart survival, exact TTL cutoff, batch boundaries, and the insert-cost/disk checks. These are command-verifiable on scratch/file DBs. The banned dashboard suite is explicitly excluded because it rewrites evidence. Environmental baseline failures are to be recorded, not silently treated as feature passes.
- **Slices:** implementation S1..S6 touch **5/4/5/2/1/2 files**, respectively; explicit dependencies are real, and each is a local independently committable unit once its prerequisites land. No dispatch should include the entire implementation bundle. P6-repin is a separately named lab-only slice with **seven paths: six hand-edited files plus the regenerated result JSON**, close to the “~6” guideline and not hidden production scope.
- **Parity:** the authoritative current pin is `lab/reference-model-study/config/reference.yaml:99-110`, with nine `parity.used_files`: production `noise.py`, `baseline.py`, `scan.py`, `fusion.py`, `driver.py`, `config.py`; shared `bayesian/short_term.py`, `bayesian/common.py`; production `deploy/k8s/solo-card6/configmap.yaml`. P6 touches precisely **config.py, driver.py, configmap.yaml** of that list. State/window/retention are unpinned. `lab/tests/parity/prod_import.py:109-138` hard-fails on HEAD mismatch or dirty used files and records blob IDs; it does not silently skip or have separate blob-value pins. `markdown/reference-port.md` really exists at the **lab root**, so the slices file's `../markdown/reference-port.md` is correct. P6-repin correctly waits for the last production commit, updates the literal config-test pin too, reruns both stages, compares every non-provenance/non-wall result exactly, and records the campaign-log change. Later deployment digest commits move HEAD again and need another explicit re-pin. The card's older source line numbers for the YAML pin are stale navigation hints; the named keys/files are correct.
- **Amended scope:** no Prometheus gauges/new route/exporter/API/dashboard change; no `scan.py` change, no threshold/chain-law or protected component change. Seven-day SQLite is explicitly the sole TTL-bounded scored history while the scrape leg is deferred. Reopen triggers and all three parked options are stated (`master:60-64`). Raw TTL is honestly a backstop; the master corrects the old ~2.9 GB fleet sizing claim and assigns PVC sizing to the operator. Accepted proxy `gate_fired`/NULL failing ESS/per-metric p_raw/WITHOUT ROWID defaults are preserved.

### Finding

6. **P6-F1 — nit, precise raw-window bound:** `evidence/omp-workcards/solo-ops-P6.md:11` says in-scope streams hold exactly “2 d + 5 min.” `scan.py:2413-2416,2684-2686` actually trims from the refit boundary, with extra `counter_max_gap_s` for counters; between refits ingest advances the newest timestamp. The span is therefore phase-dependent, not a fixed `Dt+T` duration. **Fix:** state the cutoff formula and describe the active window as approximately two days, with counter headroom and within-refit growth. This does not invalidate the accepted seven-day backstop, safety-factor floor, or the SQLite design; it is not an execution blocker. Similarly, label the example pod string 87 chars or shorten it when reproducing the declared 85-char disk probe.

**Readiness:** **ready for execution by the configured Qwen executor when S explicitly releases P6 after parity-dependent evidence is frozen**, dispatching one named slice at a time under its ownership/test gate. No required design change before S1 was found; P6-F1 is a documentation precision fix. Production implementation remains unreviewed/unexecuted and must still satisfy the recorded acceptance criteria and subsequent RV gate. Optional index drop remains non-blocking. No push/deploy/PVC sizing is authorized by this review.

## Invariants statement

- **No chain-law or threshold change:** reviewed CB integration is confined to the reference layer and leaves the raw ESS guard and downstream law untouched; D-F is re-derivation; P6 expressly excludes scoring-math/protected-component changes.
- **`boxcar` default bit-for-bit:** independently reproduced all 192 committed byte digests; full parity passed; zero numerical result changes, only 60 timing leaves, then restored the result file. Dispatch-code wording is qualified by CB-F1.
- **Production read-only:** verified pinned HEAD and read source/DDL; all SQLite experiments were scratch-only. No production edits, commits, live restart, network/SSH, cluster, GPU work, or service management.
- **YAML-first:** adaptive settings/default routing and normalization paths are YAML-derived and covered by config tests; P6 plan requires all seven retention keys with missing/unknown-key failures and both cross-field floors. This last claim is a reviewed design requirement, not a claim that unimplemented P6 code already passes.
