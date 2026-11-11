# RV-C — C1/C2 and C3/C4 slice-1 libraries

Date: 2026-11-10. Reviewer: RV (`gpt-6.1-sol`). Findings are **advisory; S decides**.

## Disposition and answer to the operator

| Leaf | Disposition | Safe basis for stage-2 conclusions? |
|---|---|---|
| C1 (`5d657f8`, `002170d`, `bf894d7`, `93c594a`) | **rejected** | No: raw-to-grid preprocessing leaks samples after `fit_end`, and missing blocks extend the residual record beyond D-5's time window. |
| C2 (`9370848`, `1863de3`, manifest `1d01aed`) | **rejected** as the complete 118-unit scientific dataset | Storage integrity, call shapes and the sampled CUDA forecasts check out. However, the 20 real units inherit C1's future-sample leakage; they cannot support leak-free real-flat conclusions as-is. The 98 synthetic/leak shards are not invalidated by the demonstrated irregular-grid boundary defect. |
| C3 slice 1 (`d313f42`, `03734c2`) | **rejected** | Digest rebuilding and ESS-gate plumbing work, but masking context selection and the reported masking statistic are wrong. D-A flat-verdict migration is also still required before stage 2. |
| C4 slice 1 (`9955703`) | **accepted_with_findings** | The served-band coverage/PIT arithmetic is independently correct. Do not infer 15/30/60-min calibration from its current pooled served-band helpers, or use the width statistic as the card's ratio of medians. |

**Overall: not yet safe to build the requested C3/C4 stage-2 conclusions on this package.** Passing hashes and CPU/GPU agreement establish that the shards contain outputs of the implemented code, not that the inputs satisfy the no-leakage experiment. Preserve the valid synthetic forecasts; correct preprocessing and have S regenerate affected real forecasts, correct the evaluation issues below, then run the downstream evaluation. No thresholds or chain laws need to change.

## Scope and checks actually performed

Read the campaign context (including D8, D15–D17 and D-A/D-B), reviewer mandate, all four cards, E-C1/E-C2/E-C2-live/E-C3/E-C4, the listed commit file/stat records, the implementation and relevant behavioral tests. Reviewed source paths had no uncommitted diff; unrelated DB/DF work was excluded. Current C3 consumers include committed DB-1.6 migration (`7ea2966`), distinguished below from the requested original slice commits. No lab or production source/results were edited; scratch probes were written under `/tmp` and all four scratch files were deleted after execution. No SSH, cluster, GPU, network fetch, or service operation was performed.

### C1: independent context, grid, hand-off and residual checks

- **Independent truncation test, not the repository's existing test:** resample the same raw series before/after retaining only `ts <= fit_end`, keep origin/grid positions unchanged, and compare `context()` and `digest()`. For 16-second raw timestamps, `fit_end=5100`, quadratic cumulative data and a 240-point counter context:
  ```text
  TRUNC_JITTER True identical False
  digest_full (30959.999999999996, 4227117.158399998, 0)
  digest_cut  (30777.215999999997, 4193707.1677439986, 1)
  last_full_cut 182.78399999999965 nan
  SCALE_TRUNC 1.0651782945736432 1.0653333786003607
  ```
  A separate admitted 34-second bracket straddling `fit_end` also exposes gauges: the last gauge context element changed from `266.1470588235294` to NaN after truncation; the counter changed from `0.44117647058823195` to NaN. Thus selecting grid indices at/before `fit_end` is insufficient: the interpolation's raw source may be later.
- **Actual packaged real input, b4xkt, first 2-day cycle:** CPU/rx/tx counter contexts all changed after raw truncation. CPU full/cut digests were `(172773.7901574422, 2591215.376214618, 0)` versus `(172758.79532256053, 2590990.531141489, 1)`; rx changed NaN count 0→1 and sum `61852876.41723047`→`61847669.08691032`; tx likewise 0→1 and `40010219.89246969`→`40006851.722232014`. Memory happened to be invariant at that particular cycle. This is an observed dataset defect, not just a hypothetical edge case.
- **Three hand resampling cases passed**, with cadence 15, origin 0, max gap 35:
  1. Jitter `[0,10,30,64,90]`, cumulative `2*ts`: increments `[NaN,30,30,30,30,30,30]`.
  2. Gauge timestamps `[0,15,60,75,90]`, values `2*ts`: `[0,30,NaN,NaN,120,150,180]` (45-second gap masked).
  3. Counter `[0,30,60,0,30,60,90]` on the regular grid: `[NaN,30,30,NaN,30,30,30]` (reset masked).
  `pod_origin` on first timestamps 317/329 returned **300**, i.e. floor of the minimum first timestamp on the block grid. Existing behavioral tests additionally cover regular identities, 35-second admission, out-of-range points and scale `16/15` on a constant-rate 16-second source.
- **D8 wheel source read directly:** installed `.venv/lib/python3.12/site-packages/timesfm3/torch/timesfm3_forecaster.py:136-162,512-530` uses `np.interp` for interior NaNs and clamps trailing NaNs to the last valid value; it trims a leading all-variate-NaN prefix. Independent direct call: `[1,NaN,3,NaN,NaN]` → **`[1,2,3,3,3]`**. `runner.py:473-486` forwards NaN-bearing contexts without filling them. Policy is explicit in `config/refcompare.yaml:10,19-23`, recorded in `markdown/refcompare.md:14` and E-C1. It is **not captured as cadence/missing-policy provenance in shard metadata or the C2 manifest** (see F9).
- **Alignment checked against the block law:** counter context ends at grid index `20e` inclusive; gauge at `20e-1`. Counter horizon step `h` ends at `fe+15(h+1)`; gauge step `h` samples `fe+15h`. Both aggregate steps `[20b,20b+20)`. Thus b=3/6/12 selects h=60–79/120–139/240–259, respectively, in the 260-step horizon; served blocks are b=6–11. The 15/30/60-minute labels refer to the forecast block's **start** after fit-end, not its ending time.
- **Actual shard read with `refcompare.store.read_shard`:** `syn_S1_1_240_multi.npz`, shape `(215,4,260,9)`. Rebuilt providers, independently summed the 20 p50 values for cycle 100, CPU, block b=6, then multiplied by its context scale (1.0): hand value **`21.578612899780275`**, `block_bands()` **`21.578612899780275`**, and served provider forecast **`21.578612899780275`**, exact equality. Implementation and `markdown/refcompare.md:16` label mean-of-quantiles as a **comonotone upper bound on block-mean spread**, not an independently calibrated block predictive distribution.
- Independently checked each served residual's value against its **serving** cycle's observed-minus-forecast value, and its serving cycle index `<= current_cycle-2`; all checked entries passed. `check_no_leakage` passed on the built run. However, a missing block inside the active window made a later record contain **one older-than-window entry**, length 570: oldest `1793735400`, required lower bound `1793735700` (F3).
- `run_pod_timesfm` itself does **not** call `check_no_leakage`; only C3's `tfm_pod` wrapper does (`evaluate.py:275-277`). The checker inspects timestamp declarations and newest residual time, not interpolation provenance; it cannot catch F1.

### C2: full store integrity and bounded real-weight CPU check

Executed the requested model-free command:
```text
.venv/bin/python scripts/run_refcompare.py --config config/refcompare_run.yaml --device cpu --verify-store
verify-store: 118 units, 118 ok, all_ok=True
Wall time: 7.98 seconds
```
Additionally rebuilt all units' cycle clocks independently from the scenario origin and each real pod's freshly loaded/sliced raw timestamps, rather than trusting `manifest.cycles_planned`:
```text
INDEPENDENT_PLAN_AUDIT 118 cycle_distribution {215: 98, 190: 20} all_shapes_names_t0_match True
STORE_FILE_COUNT 118
Wall time: 10.09 seconds
```
All arrays had `[C,4,260,9]`, expected continuous metric order and exact planned `t0`s. Manifest: 118 `ok`, zero nonempty per-unit `hygiene_violations`. The verification command checked shard SHA256 against the manifest. The independent plan audit matters because `runner.verify_store:805-816` alone compares counts to the manifest's claimed plan, rather than deriving the plan anew.

**Independent CPU reproduction with local real weights**, offline, no shard or manifest writes: rebuilt S1 seed 1, context 240, first cycle from scenario raw data (not `runner.build_unit`), matched its context digest, used a single direct wheel `predict` V=4 call and a single direct V=1 CPU-metric call. Compared against the corresponding multi and uni CUDA shards:

| Call | Input/output shape | Max absolute difference | Max relative difference | `allclose(rtol=1e-5, atol=0)` | Inference wall |
|---|---|---:|---:|---|---:|
| Multi | `(4,240)` → `(4,260,9)` | 0.00042724609375 | 1.3603374782178435e-6 | True | 0.193304 s |
| Uni CPU metric | `(240,)` → `(260,9)` | 0.00002288818359375 | 1.025509845931083e-6 | True | 0.195900 s |

Weight-load wall **4.162424 s**, complete probe internal wall **4.667682 s**, command wall **6.19 s**. This bounded check confirms one cycle/call-shape pair, not every GPU output.

Inspected `runner.py:470-486` and `_write_shard:367-373`: a multi cycle is one `(4,N)` item, a uni cycle is four separate `(N,)` items, then four output rows are restored to that cycle's variate axis. Batched items are cycles of **one unit**, not variates packed across pods. L0 manifest and E-C2-live agree: 16-cycle B=8 vs B=1 probe **`parity_max_rel=3.4306024190300377e-06`**, tolerance `1e-4`, effective batch **8**. This probe was on the short multi context; I did not rerun a GPU probe. E-C2-live records S's CUDA run per D17, 118 units collected, approximately 1.51 hours of unit wall.

### C3: rebuilt contexts, gates, masking and flat verdict

- Ran `verify_shard` on a real stored synthetic shard and on b4xkt; both passed. It reconstructs grids and contexts, compares cycle `t0`s, forecast digests **and** `meta.context_digest` (`evaluate.py:145-170`), not just stored hashes. Independently changing the first context sum by 1000 produced:
  ```text
  CORRUPTED_CONTEXT_REJECTED shard syn:S1:1:240:multi: cycle 0 container_cpu_usage_seconds_total context digest (6736.565624, 195262.202943, 0) != stored (7736.565624, 195262.202943, 0) (rtol 1e-06)
  ```
  Digest agreement still does not prove causal input construction: the real shard passed despite F1. Sum/sumsq/NaN-count are the card's summaries, not an ordered cryptographic proof of every sample.
- `common_offset(rc, ref)` independently returned **1118**, derived from shared 576 blocks × 20, `first_valid_tick` and reference config. `hcfg_common` uses nested `dataclasses.replace`, not mutation. `stl_pod:301-305` takes the deployed floor from the selected `RefConfig` and only replaces it with zero for gate-off; YAML is not edited. The executed suite includes behavioral gate-on/off tests checking gated cycles, scored ticks, availability and preserved input config, not merely a mocked call signature. TimesFM ESS remains informational and the downstream chain is unchanged.
- Independent masking-window comparison against the **actual `cycle.e`**, for S4 with a 20-block context:
  ```text
  got      (0,1,2,33,34,35,36,37,38)
  expected (0,1,2,3,34,35,36,37,38,39)
  premature [33]; omitted [3,39]
  ```
- Independent alternating `[-σ_B,+σ_B,-σ_B,+σ_B,-σ_B,+σ_B]` effect across six served blocks has required per-cycle mean zero; library returned **`max_abs=1.0, mean_abs=1.0, ratio=0.5`**. This is not the card's statistic.
- Current flat verdict returns **`marginal` for all p_raw=0.1**, and **`fails` for all p_raw=0.3**; amended D-A card requires **calm**, **marginal**, respectively. This is the known pending C3-1c migration, not a retroactive allegation that the pre-amendment slice promised D-A semantics. DB-1.6 alone did not complete it.

### C4: independent Gaussian coverage, PIT, interpolation and width checks

For 19,977 served independent Gaussian observations (seed 62017), independently computed interval membership and PIT bin counts and compared exactly to `coverage_block`:

| Pair | Coverage | Equal to independent membership calculation |
|---|---:|---|
| q10–q90 | 0.8001701957250839 | True |
| q20–q80 | 0.6020924062672073 | True |
| q30–q70 | 0.39555488812133954 | True |
| q40–q60 | 0.20113130099614557 | True |
| q25–q75, interpolated | 0.5043299794763979 | True |

PIT counts matched exactly: **`[2015,1983,2027,1988,2005,2013,1896,2099,1974,1977]`**. The model supplies only q10…q90. `coverage._level_row:57-71` and `QuantileBand.at` linearly interpolate q25 halfway between q20/q30 and q75 halfway between q70/q80; `interp_pair` is identified in YAML and E-C4. The eventual tables/figures must retain the **interp** flag; these are not native model quartiles.

A horizon-isolation probe left finite quantiles only at b=3, 6 or 12. `coverage_raw` returned sample counts **0**, **66600**, **0**, respectively: it is a served-horizon selector, not a diagnostic per-horizon evaluator. Independent width example with widths `[10,20]` and observed levels `[1,100]`: library **5.1**, card's median-width / median-level **0.297029702970297**. See F7/F8.

### Behavioral suite, lint and tracked-file checks

Executed (cache writes disabled where supported):
```text
.venv/bin/python -m pytest tests/test_refcompare_*.py -q -p no:cacheprovider
........................................................................ [ 27%]
........................................................................ [ 54%]
........................................................................ [ 82%]
..............................................                           [100%]
Wall time: 161.54 seconds
```
262 passing test-case dots; no failures or skipped markers. The run's quiet configuration did not emit a separate summary sentence.
```text
.venv/bin/ruff check --no-cache src/refstudy/refcompare tests/test_refcompare_*.py scripts/run_refcompare.py scripts/smoke_refcompare.py scripts/run_c3.py
All checks passed!
```
The suite includes substantive oracle forecast/residual checks, counter/gauge attribution, reset/gap behavior, digest corruption, resume/atomic-write/refusal tests, gate behavior, and Gaussian coverage/overconfidence tests. Nevertheless, the regular-grid-only truncation test misses F1, and masking-window/ratio tests encode the incorrect implementation (F4/F5), so green tests are not sufficient acceptance evidence.

`git ls-files` on data/artifacts/weights/fixtures showed only `.gitkeep`, `data/packaged/MANIFEST-flat-load.json`, `tests/fixtures/candb_boxcar_digests.json`, and the **D16-authorized** `tests/fixtures/gold_live_b4xkt.json.gz` raw parity fixture. `git ls-files '*.safetensors' '*.npz' '*.pt' '*.pth' '*.bin'` returned **no output**. Thus no forecast shards/model weights/raw dump are committed; the explicit D16 fixture exception remains, rather than an unqualified claim that no raw bytes exist in git.

## Findings (specific issue and recommended fix)

Paths below are relative to `reference-model-study/` unless prefixed `markdown/` or named as evidence.

### F1 — blocker — full-series interpolation violates the no-future-raw invariant (C1, inherited by C2)

**Locations:** `src/refstudy/refcompare/grid.py:55-60,101-104`; callers `runner.py:232-244,263-270`, `pipeline.py:165-176`; `cycles.py:167-176` only slices the already-interpolated grid.

The grid is built once from the complete raw series. A grid element at/before `fit_end` can interpolate against a raw observation **after** `fit_end`. Actual b4xkt CPU/rx/tx contexts change on independent truncation, and `counter_scale` also changes on a jittered counter. Gauge contexts can leak too when an admitted raw bracket exceeds 15 seconds. The existing test `tests/test_refcompare_cycles.py:122-150` uses raw timestamps coincident with the grid and cannot reveal this.

**Fix:** derive each cycle's context and scale from raw samples bounded by that cycle's `fit_end`, preserving the fixed pod grid/origin; positions lacking a past-only bracket must remain NaN for the documented wheel fill. Share the causal construction across runner, provider scale and evaluator. Add jittered/gap-boundary raw-truncation tests for counters AND gauges. Have **S**, not RV/E, regenerate the affected 20 real-unit forecasts and manifest entries; retain original measurements as superseded evidence. Merely calling `check_no_leakage` cannot repair or detect this raw-source leak.

### F2 — should-fix — pipeline does not apply the leakage checker

**Location:** `src/refstudy/refcompare/pipeline.py:275-284`.

The direct pipeline hands all runs to `score_pod` without calling `check_no_leakage`. C3's outer wrapper does call it, but direct C1 pipeline callers have no guard, contrary to the requested must-check. The provider's `assert` only covers one newest-residual inequality and is disabled under optimized Python.

**Fix:** check every continuous `ReferenceRun` inside `run_pod_timesfm` before scoring, with a behavioral test injecting an invalid fit-end/record. Keep the raw-truncation tests as a separate causal invariant (F1).

### F3 — blocker for gap-scenario conclusions — count-based residual eviction is not D-5's time window

**Location:** `src/refstudy/refcompare/provider.py:183-193`, especially `lo = max(0, usable - self._window_blocks)` at line 189.

Skipping a NaN observation reduces the append count. Taking the last 570 finite entries then reaches back beyond `[fit_end-570*T, fit_end)`. The independent probe with one missing served block yielded a 570-entry record with one entry 300 seconds older than allowed. Residual values and c+2 eligibility otherwise checked out; this is not future-residual leakage, but it changes the reference's tolerance history around gaps.

**Fix:** derive the lower record index from the timestamp cutoff (while preserving the c+2 upper bound), not a finite-entry count. Add a gap inside a full active window and assert every returned timestamp is inside D-5's window; update the mistaken equivalence in `provider.py:21-22`, E-C1's record description, and tests that assume 570 entries despite missing blocks. Recompute downstream S5/gap-sensitive evaluations; forecast shards themselves do not need regeneration for this issue.

### F4 — blocker for masking conclusions — burst-cycle selector is six blocks ahead of the real context

**Location:** `src/refstudy/refcompare/leakage.py:120-131`; matching incorrect oracle `tests/test_refcompare_leakage.py:110-129`.

The selector uses `n0-1` as the fit-end block, but `Cycle.e` is **`n0-7`**. Its inclusive `blo <= hi` also admits a burst beginning at the exclusive context endpoint. The observed S4 counterexample selects a premature cycle and omits genuinely affected late cycles.

**Fix:** use `cycle.e` and half-open intersection against the actual context's block support, consistent with counter/gauge alignment. Derive boundary tests from independently inspected context samples, including a burst just before/at/after fit-end and expiration from context; do not reproduce the same wrong `n0-1` formula in the oracle.

### F5 — blocker for masking conclusions — statistic is not mean-of-served-block effects

**Location:** `src/refstudy/refcompare/leakage.py:214-227`; `tests/test_refcompare_leakage.py:75-99`.

The card defines `dF_B[c] = mean_b(delta F_B[c,b])/sigma_B`. Code keeps `[C,6]` effects, then reports the maximum and mean of **absolute individual blocks**, not the absolute per-cycle means. Alternating effects that should cancel to zero report 1.0. The own-effect denominator also remains in raw A units while B is normalized, so the reported ratio is not a common noise-normalized effect ratio.

**Fix:** reduce the six served blocks along the block axis first, normalize A analogously when forming `dF_A` (or explicitly resolve/document any intended dimensional denominator with S), then calculate cycle-level max/mean and ratio. Test signed, nonconstant effects and unequal A/B noise scales. The current test explicitly expects the wrong A maximum (2.0 rather than the mean of its six values).

### F6 — should-fix / required pre-stage-2 amendment — D-A flat verdict and schema are not migrated

**Location:** `src/refstudy/refcompare/flat.py:35-71,105-107,153-169`.

The function still bases calmness on `p_raw > 0.02` and calls any tick over 0.2 a failure. It does not implement the amended 98%-decisively-normal rule, marginal-with-no-`>0.8` rule, or report the required class fractions/decisive count. All-0.1 and all-0.3 examples give wrong amended-card verdicts. `p_raw_summary` also does not supply the amended fields.

**Fix:** finish the explicitly planned C3-1c cutover, sourcing 0.8 from harness config, not a new chain threshold; retain `<0.02` only as the secondary calmness statistic. Test equality at 0.2/0.8 and the exact 98% boundary. This is a stage-2 prerequisite, not an unrecorded demand to rerun the older leaf against a later specification.

### F7 — should-fix / stage-2 interpretation gate — served-only coverage cannot establish the three diagnostic horizons

**Location:** `src/refstudy/refcompare/coverage.py:127-141,170-188` and `bands.py:291-301`.

`coverage_block` always consumes `served_band`, while `coverage_raw` chooses the latest **serving** cycle by tick. Before the final tail this selects offsets 6–11, pooling horizons 30–55 minutes. There is no explicit b selector, so b=3/12-only probes yield zero samples. This is not a defect in the independently validated pooled served-band arithmetic; it is a missing integration capability for C4 D-1/D-3/acceptance 2. Do not label the pooled result as 30-min coverage or as all 13 horizons.

**Fix:** before reporting diagnostic calibration, evaluate each requested `(cycle,b)` against its own observed block/raw indices and masks, with a horizon parameter/helper or an explicit stage-2 implementation. Add per-horizon tests at b=3,6,12 with nonstationary, distinguishable forecasts; count all eligible cycle/horizon pairs, not only latest-serving forecasts.

### F8 — should-fix — width normalization differs from the declared statistic and drops the absolute width

**Location:** `src/refstudy/refcompare/coverage.py:192-215`.

The card asks for median band width relative to the median observed level. The library returns `median(width[c,b] / abs(obs[c,b]))`, which is generally not `median(width[:,b]) / abs(median(obs[:,b]))`; `[10,20]` over `[1,100]` gives **5.1 versus 0.297029702970297**. It returns no absolute median width. Thus a reporter cannot use that return value directly as the card's physical-width or normalization column.

**Fix:** emit/report the absolute median width and the declared ratio of medians, with explicit handling/reporting of a zero median level; if the median of per-cycle ratios is retained as a separate sensitivity, name it distinctly. Update the behavioral test to distinguish these statistics instead of enshrining the alternative.

### F9 — should-fix — policy provenance is not attached to the stored experiment

**Location:** `src/refstudy/refcompare/runner.py:386-399` (shard metadata), `294-304,321-339` (manifest structure).

The YAML and C1 documentation describe the 15-second grid and NaN/model-fill policy, satisfying the explicit configuration part of D8. Neither stored shard metadata nor the manifest binds those outputs to the cadence/max-gap/interpolation policy, config checksum, or model revision. E-C2-live mentions code/config MD5 prefixes, but that is not complete per-store provenance. A later YAML edit cannot be audited from an isolated shard/manifest.

**Fix:** record the effective input policy and relevant config/model identities in the run manifest (and/or shard metadata with a manifest link), including the causal boundary policy after F1. Preserve existing raw forecasts unless regeneration is required for F1; do not present newly attached provenance as information originally recorded by the CUDA run.

## Campaign invariants and role/model provenance

- **No chain-law/threshold change:** preserved by the reviewed commit scopes. The candidate swaps continuous providers and calls the unchanged `score_pod`; rare-count providers are unchanged. Gate-off is a lab-only `dataclasses.replace` sensitivity, not an edit to deployed thresholds. F3 is a provider-window compliance defect, not authorization to change the chain.
- **Production read-only:** reviewed commits target the lab only; no production code edit was present in their changed-file lists. This review performed no production writes or cluster/host operation.
- **Weights/raw data/artifacts never committed:** no model weights, forecast NPZ shards or raw dumps found tracked; D16's small raw parity fixture is an explicit existing exception, not hidden. Model weights remained local and were loaded offline for the CPU probe.
- **YAML-first configuration:** input cadence, missing policy, max gap, context/horizon/matrix and evaluation thresholds are explicitly configured; tests exercise missing-key failures. F9 is a provenance gap. The current alignment implementation assumes 20 samples per block (`cycles.py:167`) even though config loading only checks integer T/cadence; any future cadence change must either be rejected explicitly or propagated through alignment before use. The reviewed dataset uses the configured 15 seconds.
- **Yardstick `p_raw`:** preserved; no `p_published`/mapper substitution in the reviewed path. The pending D-A flat migration concerns reporting semantics, not recalibration or new thresholds.
- **Operator D8 regular-grid:** satisfied in representation and documented NaN/model-fill policy, **not sufficient for causality**: F1 remains a blocker. The installed wheel has no timestamps in these calls; missing grid values reach its interpolation as verified above.
- **D15 question — were these executors on Sonnet from C1-S1a onward?** The available session notes say **no**. I read the `model_change` entries and every assistant message's actual provider/model metadata in `~/.omp/agent/sessions/-Work-langGraph-appthrust-agent-orchestration/2026-11-09T02-44-20-192Z_01a1be31-3c60-74d1-85d8-c7089d10ed2e/RefmEC{1s1a,1s1b,1s2a,1s2b,2s1a,2s1b,3s1a,3s1b,4s1}.jsonl`. All nine recorded only **`vllm-tp2-local/qwen3.8-27b-q4-gpukv-native`** assistant responses (respectively 120/77/93/152/133/185/156/231/144 messages), not Sonnet. They are not the earlier Sonnet-override jobs enumerated in campaign D15. No finding can be attributed to a model swap on this evidence. The defects are concrete missing-adversarial-test/formula mistakes, irrespective of executor model. **C2's live CUDA batch was run by S directly on Sonnet under D17**, as E-C2-live records; that is distinct from who implemented C1/C2/C3/C4.

## Recommended S disposition

Accept the independently checked store integrity, bounded CPU/GPU reproduction, served-band arithmetic, and nonmutating gate implementation as usable evidence. Do **not** accept leak-free real-flat accuracy, masking-effect magnitudes/ratios, D-A flat verdicts, per-horizon calibration, or the declared width normalization yet. Fix F1/F3/F4/F5 and complete the already-planned D-A/reporting integration before treating C3/C4 stage-2 results as campaign conclusions; F2/F9 harden invariant enforcement and traceability. Final acceptance remains S's advisory-review decision.
