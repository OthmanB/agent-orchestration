# RV Review — SOLO-REFM / B1, B2 stages 1–2, A2 Mac live smoke

- Date: 2026-11-09. Reviewer: RefmRVB, reviewer role. Findings are advisory; S decides.
- Read: campaign decisions D1–D15 and the subsequently recorded D16, reviewer template, B1/B2 workcards, E-B1/E-B1-live/E-B2/E-B2-live/E-A2-live, assigned commits and relevant implementations/tests.
- Scope: local, read-only inspection and bounded CPU tests/lint/model-free arithmetic; wrote only this review. No GPU inference, SSH, cluster, production modification, service management, commit or push.

## Dispositions

| Leaf / deliverable | Disposition | Rationale |
|---|---|---|
| B1 implemented library/FLOP cross-check and committed CUDA measurements (`3515abf`, `76f4d1c`, `d0e6163`, `7cbda00`) | **accepted_with_findings** | FLOP counts, all 36 timing cells, six energy summaries and the own-PID fix are internally consistent. Hygiene failure handling and evidence qualifications need correction. This does **not** certify completion of the pending Mac full grid or B1 stage-2 read-off/documentation. |
| B2 stages 1–2 library/runner (`eebebe9`, `b375742`) | **rejected** | Two blocking compliance defects: batch-size calibration degeneracy prevents the required batched pipeline study, and the real-data loader explicitly violates D8's regular-grid requirement. Passing small tests do not cover these conditions. |
| B2 CUDA result file (`7194c9c`) | **accepted_with_findings** as a **partial measurement record**, not completed B2 | The 42 recorded runs are arithmetically coherent and consumable by `build_table`. Sequential/overlap measurements remain useful under stated model/host conditions; batched grid/stagger/validate and most sustained validation are absent. |
| A2 MPS/MLX smoke JSONs (`eb49314`) | **accepted_with_findings** | Functional/parity/truncation summaries and all 12 latency-cell arithmetic checks agree with the evidence. Battery/shared-load smoke is not an exclusive-window B1 measurement or isolated accelerator-energy comparison. |

## Checks performed and literal results

Paths below are relative to the lab's `reference-model-study/` unless prefixed `evidence/` or `markdown/`.

### 1. Commit provenance and bounded library checks

- Inspected the assigned commits' file lists: code/config/tests are within the B1/B2 owned paths; the live commits contain the stated JSON outputs (A2 also its model manifest). No uncommitted changes were present in the inspected B-owned source/config/result paths.
- Compared the four final local measurement files byte-for-byte with `git show <assigned-commit>:<path>`: **True for all four**. SHA256:
  - `7cbda00`, `results/b1-scaling-cuda.json`: `5c7dd1e074ce9ec84cb52a504f80a7c88077b1264211068801a75dc186298fcd`.
  - `7194c9c`, `results/b2-refresh-cuda.json`: `4b9bdfaf317fa5771d780a109a2b617c84234a1a00f78274cfaee74e51da2eb9`.
  - `eb49314`, `results/a2-smoke-mps.json`: `b9a350620c81af71825f0a7a9badd139e969b376b3e6301942bb59e200cfec68`.
  - `eb49314`, `results/a2-smoke-mlx.json`: `445584149e75cfb570061787401e6f7f6cd787af1e926b7320f50b00f5eeeaf2`.
- Inspected the earlier `d0e6163` B1 JSON: **0 cells**, `start_abort` present; its `flopcount_cuda` block equals the final file's block exactly. It was an abort/count record, not a latency measurement; `7cbda00` supplies the timing data.
- Ran exactly `.venv/bin/python -m pytest tests/test_compute_*.py -q` with a 180 s deadline. **Successful completion, 234 dot-marked cases, no failures/skips shown**. Literal terminal progress: `[30%]`, `[61%]`, `[92%]`, then `.................. [100%]`; tool wall time **46.28 seconds**. The repository already supplies `addopts = "-q"` (`pyproject.toml:28–30`), so this double-quiet invocation omits the usual passed-count summary.
- Ran `.venv/bin/ruff check src/refstudy/compute scripts/run_scaling.py scripts/plot_scaling.py scripts/run_refresh.py scripts/plot_refresh.py tests/test_compute_*.py`: **`All checks passed!`**.

### 2. B1 result-file integrity

Independently checked **every one of the 36 cells** for `status == ok`, `polluted == false`, empty hygiene violations, 15 timing samples, exact median/min/max consistency with `runs_ms`, analytic FLOPs recomputed from the configured law, and both GFLOP/s fields recomputed from the stored median: **errors `[]`**. Five explicit analytic-throughput checks (GFLOP / (median_ms / 1000)):

| Cell | Recomputed analytic GFLOP/s | Stored analytic GFLOP/s |
|---|---:|---:|
| N64,V1 | 56.14752195108948 | 56.14752195108948 |
| N240,V3 | 349.923379066064 | 349.923379066064 |
| N5760,V3 | 1843.8930109362716 | 1843.8930109362716 |
| N11520,V4 | 2597.9472249076152 | 2597.9472249076152 |
| N15360,V3 | 2302.729137829648 | 2302.729137829648 |

The evidence's GFLOP/s table uses **measured**, not analytic, FLOPs; its slightly lower numbers are therefore correct, not a discrepancy.

- All 36 CPU FLOP records have positive measured counts, and `sum(by_op)/1e9 == gflop_measured` within floating-point comparison: **sum errors `[]`**. Measured/analytic range: **0.9995055054563549–0.9995397425473109**. CPU SDPA is counted.
- N17280/N15360 analytic and measured FLOP ratios are **exactly 1.0 for V1/V3/V4**, satisfying the card's 0.1% FLOP plateau tolerance. Corresponding median-latency ratios: **1.0093487451 / 1.0223458424 / 1.0190343873**; device memory is equal for each pair. This supports a plateau with timing variation up to 2.24%, not exact latency equality. No separate numerical latency-plateau tolerance is specified in YAML.
- Rechecked the three `flopcount_cuda` cells against the CPU counts: **`ratio_to_cpu = [1.0, 1.0, 1.0]`**; the CUDA efficient-attention op is present.
- All six energy cells have `resolved=true`, `n_dropped=0`, `scope=gpu_board`; their energy arithmetic matches exactly. Example N240,V3:
  `(27.77067748904181 − 15.768376789223497) × 44.93684458732605 / 584 = 0.923536851435086 J/call`.
- The other recalculated J/call values are **6.2219407856** (N11520,V1), **5.3894895368** (N5760,V3), **9.2011973756** (N11520,V3), **12.2767868161** (N11520,V4), **13.7837408143** (N15360,V3). All match the stored fields and rounded live evidence table.
- Resolution is checked against **2 × max(before/after idle std, 1 W)**, not merely a 1 W excess. For N5760,V3 the actual threshold is **21.3371 W**, below its **27.0761 W** excess. All six pass their actual thresholds.
- Inspected all 12 before/after idle records; each stored `idle_w` lies between its corresponding means. The implementation uses the **resident-model** idle blocks, not the 8.3 W bare-GPU spot reading. Correct choice for energy above the loaded-model idle baseline.
- **Independent-integral limitation:** no per-sample telemetry or B1 energy-window endpoints are committed. Consequently the true trapezoid integral and exact B1 midpoint interpolation cannot be reconstructed from the measurement JSON alone. The calculation above verifies summary arithmetic, not the original sample stream. `power.py:205–236` and its exercised tests verify the integration/interpolation implementation. Do not claim a replay of absent samples.

### 3. B2 JSON, schema, knees, conservation and sustained ratio

- Observed **42 runs**: `{calibrate: 10, grid: 16, stagger: 8, validate: 1, pool_sweep: 7}`; status counts **`{ok: 42}`**; polluted count **0**. All `refresh_s` values equal medians of `wall_s`; all power blocks are final; energy-summary arithmetic errors **`[]`**. Resolution counts **`{True: 41, False: 1}`**.
- Compared `refresh_run.new_doc/execute` (`refresh_run.py:79–127,386–469`) with `sustain.py:3–15,38–109`: the committed field names and nesting match. Invoked **`sustain.build_table([doc], cfg)` in memory**, without writing outputs: **30 rows, 5 accelerator-bound entries, 2 stability entries**, no exception. Ten batched rows correctly have **`pods=None`, `method=insufficient_points`, `extrapolated=true`**. There is one measured N32 calibration pass per batched context, not a completed batched throughput grid.
- Recomputed the knees by calling the actual `knee.find_knee` on eligible non-aborted calibrate+grid burst runs:

| Context | Variant | 120 s: pods / method | 180 s: pods / method | 300 s: pods / method |
|---|---|---|---|---|
| 11520 | sequential | 176.060679 / interpolated | 264.083302 / interpolated | 438.340884 / extrapolated_linear |
| 11520 | overlap | 292.338692 / interpolated | 441.797061 / interpolated | 732.648317 / extrapolated_linear |
| 5760 | sequential | 308.990845 / interpolated | 463.336873 / interpolated | 772.106733 / extrapolated_linear |
| 5760 | overlap | 537.970182 / interpolated | 809.636010 / interpolated | 1335.869061 / extrapolated_linear |

These reproduce E-B2-live's nearest-integer presentation. **`build_table` floors**, rather than rounds, capacity: e.g. overlap@11520/tick becomes **732**, not the evidence table's rounded crossing **733**. Preserve that distinction in sustainable-capacity reporting.

- The 300 s PASS knees are all honestly marked **extrapolated** in the computed table; the evidence table also labels them extrapolated. The raw run document contains measurements/calibrations, not a precomputed knee table. The single 300 s arrival-window validation does not turn a PASS knee into a measured crossing.
- Exact sustained definition: completions in **`(W/2, W]`**, divided by `W/2`, divided by calibration throughput. `pipeline.py:429–431`, `refresh_run.py:712–723`: **`218 / 150 / 1.4967189381705677 = 0.9710128577044236`**, identical to the JSON. This is only **sequential@11520**. It does not validate overlap, batched_overlap or the 5760 context.
- The sole abort is **`pool_sweep:overlap:ctx11520:n75:w4-c1-block`**, `aborted=true`, **55 completed, 0 dropped, 20 unfinished**; wall **37.744476 s**, consistent with the configured **1.25 × 30 = 37.5 s** admission deadline plus draining in-flight work. `status=ok` denotes a recorded pass result, not all pods completed; these two flags are not contradictory. JSON/config support the stated deliberate capacity-1 stress deadline, although intent itself is not a result-file field.
- The drop run is **`...:w4-c8-drop`**, **8 completed + 67 dropped = 75**, `dropped_frac = 0.8933333333333333`, not aborted. This verifies the “89% dropped by design” arithmetic **for a burst of 75 simultaneous arrivals**, not a general production loss rate.
- `batched_overlap` grid/stagger/validate is **UNMEASURED**. The two N32 calibration passes and accelerator-only probe exist; their measured mean batch is **16**, so even those calibration passes must not be described as the B32 probe/pipeline equivalence.

### 4. A2 committed smoke and local logs

- Both reports: `overall=ok`; shape/determinism/truncation/latency statuses `ok`, flat status `observed`; deterministic repeat differences **0.0**; N17280 versus N15360 output difference **0.0**. Verified all six latency cells per device have `min <= median <= max` and exact GFLOP/s arithmetic: **errors `[]`**. Individual timing samples are not in these JSONs, so their medians cannot be rederived independently.
- N11520,V3: MPS **634.717 ms / 1202.601 analytic GFLOP/s**; MLX **409.692 ms / 1863.135**. The evidence table agrees after rounding. Maximum quantile parity differences: MPS **1.1444091796875e-5**, MLX **9.5367431640625e-6**; this supports numerical agreement, not bit-exact device-to-CPU identity.
- Local `throwaway/a2-smoke-{mps,mlx}.log` ends `smoke ... overall=ok -> results/...json`; log load times **2.6 s / 0.6 s** agree with committed **2.64414 / 0.57350 s**.
- Read the retained 35-line power files. The stated MPS pre-window mean **6035.8333 mW** (first 18 samples), active plateau **8040 mW**, MLX idle **8040 mW**, later 17-sample mean **12123.2941 mW** are reproducible. These uncommitted whole-system samples bracket entire smoke processes, including CPU-reference parity, and are coarse/context-sensitive; see finding F6.
- No local CUDA live-run logs were found among the retained measurement logs. CUDA command/exit/host-cleanup history is therefore checked against committed fields and the quoted evidence, **not independently corroborated by a local full raw log**. No remote retrieval was attempted.

### 5. Hygiene, energy boundaries, tests and presentation

- Own process tree: `hygiene.py:101–120,131–154`; CPU/top and GPU count exclude the own PID/descendants. `count_gpu_other_procs` excludes known own integer PIDs and conservatively counts unattributable nonempty rows. The exercised regression tests cover own-only, own+foreign and `[N/A]` (`test_compute_hygiene.py:145–170`). This fixes the original deterministic self-count abort without raising a threshold.
- Thresholds/CPU enforcement come from `compute_scaling.yaml:49–80`. CUDA deliberately sets `enforce_cpu:false`, no load/CPU caps, other-GPU-process maximum **0**. Thus `polluted=false` means **no enabled-policy violation**, not “unloaded host.” B2 JSON load1 actually spans **12.25–20.02**, broader than E-B2-live's claimed 12.5–15.3.
- `parse_ioreg` divides `SystemLoad` mW by **1000**, while NVIDIA values are W. No mW/W error found. Trapezoid edge interpolation uses strict-interior samples plus interpolated endpoints, avoiding duplicate endpoint area. B1 counts **len(completion_times) − 1** over the first-to-last in-window completion interval (`scaling.py:212–220`): correct complete-call interval count, not an off-by-one bug.
- B2 subtracts the midpoint of a linearly interpolated before/after idle baseline. Recomputed this from **every run's stored endpoints and block baselines**: maximum absolute difference from stored idle **0.0 W**. Because each window lies between the baseline midpoints, subtracting this midpoint value × duration is the exact integral of that linear idle model.
- Tests assert behavior, not only wiring: exactly-once conservation and no residual threads (`test_compute_pipeline.py:103–112`), serialized infer (`125–132`), bounded inflight/queue plus producer waiting and no drops (`142–150`), unbounded growth/drop disjointness (`153–169`), deadlines/errors (`210–234`), hand-built queue/backlog arithmetic (`271–314`), and analytic knee recovery/interpolation/extrapolation/degenerate cases (`test_compute_knee.py:17–78`). Power tests cover real subprocess sampler stop, units, ramp/constant/edge energy, unbracketed windows, linear idle and noisy/negative excess (`test_compute_power.py:50–146`).
- Blind spots: runner tests select only B*=2 with calibration counts 3/6, so miss B*=32 with 10/30; pod fixtures use aligned regular timestamps, missing D8 irregular-grid behavior; hygiene tests omit failed mandatory GPU probes; plotting tests check file magic/table values but not cross-figure x-limits or energy-panel unresolved markers. Passing these tests does not discharge those criteria.
- Scope labels are present in both JSON families and plot implementations: B1 energy legend/axes (`plot_scaling.py:156–188`); B2 power titles/axes (`plot_refresh.py:264–276`); table/headline `power_scope` (`sustain.py:104,240,255`). Mac **`system_whole`**, CUDA **`gpu_board`** are distinct, and module/YAML documentation says host CPU is excluded from CUDA energy. No unlabelled cross-device power table was found in the reviewed evidence. A2 labels whole-system mW and battery status explicitly.
- Inspected B2 plots **in memory only** on the committed CUDA doc: refresh axes **`(0.8, 2805.8187471257606)`**; power axes **`(0.8, 1563.0)`**. Scope labels and `hollow = extrapolated` title were present. No production result/figure file was generated.

## Findings

### F1 — blocker — calibration rounding destroys the required batched study

**`src/refstudy/compute/refresh_run.py:626–637,667–669,693,705`**, with `config/refresh_study.yaml:53–55,66–67`.

The real probe chose B*=32; `round_up_to(10,32)` and `round_up_to(30,32)` are **both 32**. Both calls use the same run key, so the second resumes the first; fewer than two distinct points remain, `calibrate` returns None and the grid is skipped. `stage_stagger`/`stage_validate` then look up a nonexistent calibration and raise the reported ValueError (`refresh_run.py:184–191`). `knee.fit_linear:49–50` correctly refuses equal pod counts; the knee finder/pipeline are not the cause. This is a real code bug, confirmed without re-running live work.

**Minimal fix:** choose strictly increasing rounded calibration counts in `calibrate`, advancing a collapsed next count by one batch, so `[10,30], B=32` yields **`[32,64]`**; retain the measured B* and existing fit semantics. Add a regression with the actual YAML counts and B*=32 that requires two distinct calibration runs, a calibration entry, and successful dependent-stage lookup. Do not hide the failure by lowering B*, suppressing the exception or fabricating batched knees. Batched pipeline conclusions remain unmeasured until S authorizes the corrected live measurements.

### F2 — blocker — real-data PodWorld bypasses binding regular-grid decision D8

**`src/refstudy/compute/podgen.py:10–12,58–61`**, `config/refresh_study.yaml:8–14`; D8 in campaign context.

The loader discards timestamps, differences counters by sample index, truncates all metric arrays to the shortest length, and stacks them positionally. The code explicitly says “no resampling.” D8 explicitly names B2 PodWorld and requires regular-grid cadence and missing-data policy in consuming YAML/manifest. Merely labelling this compute-realistic does not override D8. It also omits resampling/alignment work from the measured preparation path; counter arrays lose their first sample while gauges do not, so even positional stacking is not aligned by time.

**Fix:** implement the D8-compliant timestamp-aligned regular-grid input path, with explicit YAML cadence/fill policy and provenance/manifest recording, and test irregular/jittered/missing samples and counter alignment. Preserve these JSONs as **old, fixed-shape compute measurements**, not proof of a measured end-to-end regular-grid 1-/2-day refresh path. S decides whether corrected prep materially requires remeasurement; do not silently relabel old data.

### F3 — should-fix — B2 live interpretation exceeds what its measurements establish

**`evidence/E-reference-model-study/E-B2-live.md:65,99,120,126`**, `E-B2.md:96`, and `evidence/omp-workcards/refm-B2.md:59`.

- Host load range is **12.25–20.02**, not 12.5–15.3. Prep, arrival/gate coordination, Python/model dispatch, H2D/D2H handling and wakeups all execute on the saturated host CPU (`refresh_run.py:227–240`, `pipeline.py:259–345`). Sleeping fetch/chain are modelled latency, not zero CPU dependence. “Host CPU is otherwise idle” is false. **[INFERENCE]** contention tends to inflate measured service/wakeup times and lower sustainable capacity, and can change batching and relative overlap gains; its magnitude/direction for each ratio is unmeasured. These are shared-host end-to-end numbers, not isolated GPU ceilings.
- At rho **1.1**, backlog is already **12/99 = 12.12% sequential** and **22/168 = 13.10% overlap**, both above the configured 5% threshold. The first tested threshold crossing is **1.1**, not 1.4; `build_table` estimates rho* about **0.9692 / 0.9691**. Replace the onset claim with these recorded results.
- A sequential-only second-half throughput ratio **0.971** does not prove “no thermal drop-off,” independently validate every variant/context, or establish all 300 s PASS knees as trustworthy. There is no retained per-run temperature history/control experiment. Also the overlap/sequential capacity gain is about **1.66–1.75×** in the shown knee table, not up to **1.93×**; the latter is the B32/B1 accelerator probe gain.

**Fix:** correct the range/onset/ratio text and qualify sustained/thermal claims. Keep all 300 s PASS knees extrapolated and restrict validation attribution to sequential@11520. State the 89.33% drop rate as this **simultaneous-burst admission experiment**, not a production steady-state rate.

### F4 — should-fix — a failed mandatory hygiene probe can be recorded as clean

**`src/refstudy/compute/hygiene.py:151–154,169–175,183–185`**.

A failed GPU-process command sets `gpu_other_procs=None`; `check` ignores None even when the YAML cap is 0. A model-free call with the CUDA profile and unknown GPU occupancy returned **`[]`**. Likewise missing enforced load/top probes can bypass their rules. This matters because `polluted=false` is used as evidence of measurement hygiene.

**Fix:** distinguish unknown/failed required probes from disabled checks and report a violation for enabled checks whose required observation is missing; exercise command failure/unparseable output in tests. The reviewed live files do contain successful numeric GPU counts, so this is a latent reliability defect, not evidence that an actual foreign tenant was present.

### F5 — should-fix — power presentation/resolution does not fully meet B2's contract

**`scripts/plot_refresh.py:123–198,207–276`**, **`src/refstudy/compute/power.py:257–272`**, `tests/test_compute_refresh_plots.py:145–178`.

The workcard requires the same pod-axis range across refresh and power figures; in-memory inspection yields **2805.82** versus **1563.0** upper limits because one includes extrapolated continuations/knees and the other only measured power points. Unresolved points are hollow only in the power-W panel; energy/J-per-pod remain connected as ordinary values. Furthermore the generic `resolved` predicate is amplitude-versus-idle-noise only; it never implements the card's explicit **Mac pass <30 s unresolved** condition, nor does it require an adequate telemetry sample count. Thus future short Mac passes could be declared resolved from a stale battery-gauge level.

**Fix:** share the computed per-device x-limits between the two figures; mark unresolved points in the energy panels too; implement the scope-specific short-window/sample adequacy rule through YAML and expose resolution in downstream tables where used. Add assertions for these behaviors. This is not a detected mW/W or trapezoid error, and it does not invalidate the six long-window CUDA B1 summaries.

### F6 — should-fix — distinguish power observations from attribution and correct small evidence mismatches

**`evidence/E-reference-model-study/E-A2-live.md:88,97–105`**, `E-B1-live.md:114,132,138`, `E-B2-live.md:103`.

A2's whole-process smoke power windows include loading and the second **CPU** forecaster/parity (`throwaway/a2-smoke-mps.log:5–8`, MLX log `4–7`), on battery with coarse whole-system telemetry. Their +2/+4 W differences are not isolated MPS/MLX inference energy or a controlled backend comparison. MLX committed `rss_after_load_mb` is **2590.75**, not the table's **2593.1**. B1's claimed parity CPU **6 threads** conflicts with `run_scaling.py:109–113`, which preserves CUDA's **1-thread** budget. The ~50 W energy-loop **mean** is not a measured **peak**. The elevated resident idle is a measured observation, but attributing its entire gap solely to the context is unproven; DVFS/thermal settling is not separated. E-B2-live:103 calls its power “excess,” while the adjacent table actually shows total mean board W.

**Fix:** retain the observations but label whole-smoke versus inference-only, correct the memory/thread facts, call mean power a mean, distinguish board mean from excess, and mark idle-gap attribution as an inference. No re-run is needed to fix these reporting defects.

## Campaign invariants and research hygiene

| Invariant | B1 | B2 | A2 live smoke |
|---|---|---|---|
| No chain-law/threshold change | **Preserved:** only compute tooling/config/results changed. | **Preserved:** chain is an explicitly modelled 10 ms sleep, not an alternate implementation or law change. This does not validate real chain cost. | **Preserved:** result/manifest-only commit. |
| Production read-only | **Preserved in reviewed changes:** no production paths modified or used by these compute tests. Historical host/cluster side effects are supported only by worker evidence, not independently re-probed. | Same; modelled fetch never queries cluster. | Same; local smoke logs only. |
| No committed weights/raw dump/artifacts | **Preserved for assigned commits.** `git ls-files` shows no tracked weight files; raw/artifact trees contain only `.gitkeep`, packaged tree `.gitkeep` + manifest. | Same. | Same; copied host weights are documented local noncommercial research copies, not committed/uploaded result content. No host inspection was performed. |
| YAML-first configuration | Core thresholds/timing/grids/devices/power scopes are YAML-driven; no live threshold relaxation was found. Smoke-only hygiene relaxation is explicit. | Core pipeline/budget/fetch/arrival knobs are YAML-driven, **but D8 cadence/fill policy is absent (F2)**. Internal polling constants do not establish measurement-policy compliance. | Existing YAML settings used; battery/shared-load deviations recorded, not silently promoted to B1-compliant measurements. |
| Yardstick `p_raw` | **Preserved / not exercised** by compute measurements; no accuracy claim certified. | Same; refresh feasibility cannot establish anomaly-detection fidelity. | Same; forecast parity is not `p_raw` chain parity. |

**D16 exception:** the tracked `tests/fixtures/gold_live_b4xkt.json.gz` is a **small fixture excerpt, accepted by S** (one pod/window; I observed 10,488/10,486/10,435/10,435 raw rows for the four metrics). It is outside the assigned B/A2 commits and is not counted against these leaves; the full raw dump remains untracked. No additional fixture-generation finding is necessary for this review.

`markdown/timesfm3-licence-note.md:5–24` records the pinned identity and noncommercial/nonproduction licence; E-B1-live:18–22 records the same hash on the private CUDA host copy. This review confirms the documented research-only posture and absence of tracked weights, **not legal clearance for production/commercial use or independent proof of remote storage behavior**. Production adoption remains licence-gated.

## D15 attribution and acceptance of measurement evidence

The calibration defect and D8 noncompliance are present in executor-produced code. The own-GPU-PID bug was also in executor code and is demonstrably fixed by `76f4d1c`. **There is no evidence establishing that any of these defects was caused by the executor-model swap**; there is no counterfactual same-task comparison. Likewise, no result corruption or code modification attributable to the unlawful live-role was found. Reporting overclaims/inaccuracies in worker-authored evidence are concrete findings, but their causal connection to the role choice is **not established**. D15 remains a provenance/governance violation; numerical consistency does not erase it.

I accept the committed files as evidence of **B1's analytic/device FLOP agreement and observed CUDA per-call costs**, **A2's functional backend smoke**, and **B2's partial sequential/overlap fixed-shape, modelled-fetch/chain performance on this CPU-contended CUDA host**. Energy is conditional on measured resident idle and the stated scope; absent raw samples prevent independent integration replay. I do **not** accept them as evidence that all Phase B acceptance criteria are complete, that the batched pipeline is measured, that real regular-grid end-to-end prep is validated, that every 300 s knee was directly measured/sustain-validated, that thermal effects are excluded, or that battery Mac smoke provides controlled cross-device energy rankings. The B2 code disposition remains rejected pending F1/F2; the useful partial measurement records should be retained with these caveats, not discarded or silently upgraded.
