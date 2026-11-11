# RV-C2 — re-check of RV-C after causal regeneration

- Date: 2026-11-10 (UTC).
- Reviewer: RV, `gpt-6.1-sol`.
- Disposition: **accepted_with_findings**, qualified below. Findings are advisory; **S decides**.
- Reviewed fixes: `a7133a3` (F1), `c947347` (F4/F5/F6), `152f37c` (F2/F3/F9), `594664b` (F7/F8), regenerated manifest/archive `0d30e5f`.

## Answer to the operator

**The C2 data — all 118 units after regeneration — are now a safe input dataset for stage-2 analysis within the frozen campaign matrix. The C4 coverage/width libraries pass this re-check. C3's mean-effect/normalisation and D-A flat changes pass, and its actual S4/S6 masking selections are correct for this matrix; however, the C3 selector is still wrong when a burst starts exactly at `fit_end`. Thus I do NOT give an unqualified joint “C2 data and C3/C4 libraries are now safe” sign-off.** Close the remaining F4 equality case before claiming the C3 library fully fixed. Alternatively, S can explicitly accept a frozen-matrix-only disposition: I checked that none of its current burst onsets exercises that case. This remaining selector issue needs no GPU regeneration.

Remaining caveats: incomplete historical per-shard provenance for the 98 synthetic/leak shards (honestly disclosed), `code_git_head="unknown"` even on the regenerated real shards, the bounded nature of the CPU/GPU reproduction, and the original interpretation limits (raw-native versus comonotone block bands, interpolated quartiles, ESS-gate asymmetry, scored-tick availability, single-seed context sweep, non-commercial weights). These are not evidence that the corrected real contexts still leak.

| Area | Re-check result |
|---|---|
| F1 causal contexts and scale | **Pass**: independent real raw-truncation checks and jittered counter/gauge adversary; regenerated metadata agrees with causal rebuilds. |
| F2 mandatory pipeline checker | **Pass**: four continuous runs checked; injected invalid `fit_end` raises before scoring. |
| F3 timestamp residual window | **Pass**: gap-inside-window record has 569 entries and starts exactly at the cutoff. |
| F4 masking selector | **Partly fixed**: `cycle.e` replaces the six-block-ahead clock; upper-bound equality is still inclusive incorrectly. Current frozen S4/S6 selections nonetheless match a strict half-open oracle. |
| F5 masking statistic | **Pass**: signed per-cycle means, then each signal's noise normalisation; alternating effects cancel. |
| F6 D-A flat verdict | **Pass**, including exact thresholds and 98% boundary; decisive crossings remain separately reported even when the aggregate verdict is calm. |
| F7 per-horizon coverage | **Pass**: b=3/6/12 hand-count agreement for block and raw, counter and gauge. |
| F8 width statistic | **Pass**: absolute median width and ratio of medians distinguished from median of ratios. |
| F9 policy provenance | **Substantially fixed, with traceability finding**: effective policy/config/model fields recorded; 98 historical shards lack the field; regenerated code revision is unknown. |

## Scope and checks performed

Read the campaign context first, including D-S8, D-A(iv), D15–D17 and the AUTONOMY WINDOW; reviewer mandate; RV-C; C1–C4 workcards; the E-C1 fix sections, E-C2-live Regeneration, E-C3 Fix C3a and E-C4 Fix C4a; inspected the five commits' changed-file scopes and current relevant source/tests. No lab/production source, forecasts, manifests or committed results were modified by this review. Repository output is only this review. Independent probes and a copied pipeline module were written under `/tmp`. No SSH, cluster, GPU, network request, or service operation was performed. The real model check was CPU-only and offline.

Source paths below are relative to `reference-model-study/` in the lab unless otherwise stated.

### F1 — independent raw truncation, causal metadata and synthetic neutrality

Implementation inspected: `grid.py:92-108` truncates the **raw source** before interpolation; `cycles.py:182-270` shares the causal construction; `runner.py:161-179,537-541` uses it for input/context metadata; `pipeline.py:164-193` uses the causal grid for counter scale and unit scale for gauges; `evaluate.py:179-194` reconstructs each metadata context from raw samples.

Executed `.venv/bin/python /tmp/refm_rvc2_causal.py`, command wall **17.16 s**. This was a new probe, not a call to a repository truncation test. For b4xkt multi, 11520 points, I rebuilt contexts from the complete raw source through the new construction and independently from **explicitly filtered `ts <= fit_end` raw arrays** through `to_grid`, preserving origin/grid positions. I rebuilt detector blocks on both raw sources too, then recomputed counter scale. All eight context comparisons were bit-identical including NaNs; all eight scale comparisons were exact.

| Cycle | Metric | Causal context digest `(sum, sumsq, n_nan)` | Scale, identical before/after raw truncation |
|---|---|---|---|
| 0, `fit_end=1793854500` | CPU | `(172758.79532256053, 2590990.531141489, 1)` | `1.0957364585436418` |
| 0 | mem | `(2932938581822.462, 7.46732141892491e20, 0)` | `1.0` |
| 0 | rx | `(61847669.08691032, 343259320434.6497, 1)` | `1.088033014242482` |
| 0 | tx | `(40006851.722232014, 143630145901.6308, 1)` | `1.0880321939271989` |
| 100, `fit_end=1794034500` | CPU | `(172759.14201448218, 2591000.917755752, 1)` | `1.0920642089763892` |
| 100 | mem | `(2946076740742.2812, 7.534175796914348e20, 0)` | `1.0` |
| 100 | rx | `(61844211.85800144, 343065766305.8801, 2)` | `1.0919498533763354` |
| 100 | tx | `(40004681.54077244, 143548174666.74304, 2)` | `1.091950177324128` |

These are genuinely irregular real timestamps: for example first-cycle CPU/mem bracket the cutoff at offsets `[-1.4110000134,+14.7130000591]` s, rx/tx at `[-7.4100000858,+10.8239998817]` s; cycle-100 rx/tx bracket it at `[-18.6219999790,+0.4590001106]` s.

Executed a separate seeded jitter adversary in `/tmp/refm_rvc2_additional.py`: 10–34-second intervals, forced admitted bracket `[5078,5112]`, `fit_end=5100`, quadratic cumulative/gauge values. The old gauge context's last value was `258674.13999999998`, the old counter's `1528.500000000029`; both new last values were NaN and both equalled explicit raw-truncated rebuilds. Counter scale was exactly `1.4346617951849177` on both past-only constructions; gauge scale was 1. This independently exercises the gauge failure that happened not to occur in b4xkt's sampled memory contexts.

`verify_shard(..., rtol=1e-6)` rebuilt **every cycle and all four variates** of three regenerated real units, `real:{b4xkt,mjnlq,rzpzm}:-:11520:multi`: 760 context rows per unit, **2280 rows total**, matching the actual shards' `meta.context_digest` (and forecast digests/cycle clocks).

For five synthetic units I compared the new causal context arrays against the old full-grid slices for **every cycle/variate**, exactly including NaNs, and also ran `verify_shard` against each actual shard's metadata:

- `syn:S1:1:240:multi`
- `syn:S2:1:5760:multi`
- `syn:S4:1:11520:multi`
- `syn:FLAT:1:11520:uni`
- `syn:S5:1:11520:multi`

Each had **860 exact old/new context-array matches**: **4300 total**. All stored digest comparisons passed at the card's `rtol=1e-6`. This is stronger than merely asserting that synthetic timestamps are grid-coincident, and includes the S5 gap case. Cross-platform digest comparisons are tolerant summaries (sum/sumsq/NaN count), not ordered cryptographic proofs of all input values; exact old/new array neutrality was checked separately on this machine.

### Regenerated store and retained superseded evidence

Executed the required command:

```text
.venv/bin/python scripts/run_refcompare.py --config config/refcompare_run.yaml --device cpu --verify-store
verify-store: 118 units, 118 ok, all_ok=True
Wall time: 5.08 seconds
```

Additionally inspected current and archived manifests and read the archived shards:

- Both manifests contain 118 entries. Current counts: 90 synthetic + 8 leak units at 215/215 completed/planned cycles, 20 real units at 190/190; every status `ok`; zero nonempty `hygiene_violations`.
- **98/98 synthetic/leak shard SHA256 values are unchanged** from the archived manifest; **20/20 real values changed**.
- `artifacts/refcompare/superseded-preF1/` contains **20 old real NPZ shards**. All 20 file SHA256 values match their entries in `results/archive/c2-run-manifest-preF1.json`.
- The manifest's `superseded_preF1` block names the 20 real unit IDs and the F1 causal-regeneration reason. The old manifest exists and is tracked by `0d30e5f`; old/new NPZ files remain untracked artifacts.

### Regenerated real-unit CPU/GPU spot check with real weights

Executed `.venv/bin/python /tmp/refm_rvc2_cpu.py` with offline HF/transformers flags, `local_files_only=True` via the existing loader, CPU device, **two torch threads**, and no artifact writes. Rebuilt **b4xkt cycle 0**, `fit_end=1793854500`, causal input **`(4,11520)`**, and checked its input digests against the regenerated multi shard. Used exactly one V=4 forecast call and one V=1 CPU-metric call (one-item `predict_batch` each, H=260); compared against the corresponding regenerated multi and uni CUDA shard rows.

| Call | Output shape | Max absolute difference | Max relative difference | `allclose(rtol=1e-5, atol=0)` | Inference wall |
|---|---|---:|---:|---|---:|
| V=4 multi | `(4,260,9)` | `64.0` | `8.387115187888905e-6` | True | `1.108818 s` |
| V=1 CPU metric | `(260,9)` | `1.9073486328125e-6` | `1.273031365201382e-7` | True | `0.357257 s` |

The absolute multi difference must be read in the metrics' physical units (memory is about `2.5e8`), not as a dimensionless error. Weight-load wall **5.123567 s**; total internal probe wall **10.324417 s**, command wall **11.17 s**. This is a bounded numerical reproduction of one real cycle and two call shapes, not exhaustive CPU inference of the store, nor a throughput benchmark.

### F2/F3 — pipeline guard and timestamp record

Executed `.venv/bin/python /tmp/refm_rvc2_logic.py`, command wall **1.42 s** for the combined logic probes.

- Inspected `pipeline.py:299-307`: every continuous `ReferenceRun` is checked before the unchanged `score_pod` call. Loaded a **copy of the actual pipeline module under `/tmp`**, counted four checker invocations on a clean FLAT run, then injected `fit_end + 300` on its providers' finite declarations. The copied real call path raised:
  ```text
  leakage: tick 605 (1793716200.0) fit_end 1793714400.0 > tick - T - dt = 1793714100.0
  ```
  This is a `ValueError`, not an assertion, and exercises the direct pipeline rather than C3's outer wrapper.
- Inspected `provider.py:193-217`: lower index derives from timestamp search, while `hi=usable` preserves c+2 eligibility. Independently built a mature block stream, removed one block inside the active window, and inspected its served record: **569 entries**, oldest **158100.0**, required cutoff **158100.0**, newest **328800.0**. All entries were in `[fit_end-570*T,fit_end)`. The record is not extended backwards to recover 570 finite entries.

### F4/F5 — sampled context support, boundary cases and masking effect

**Check actually performed for F4:** independently encoded block-label values onto the regular raw grid, using counter right-closed increment attribution and gauge half-open sample attribution, then read the actual `cycles.context` arrays. With `e=581`, W=20, both contexts contain **blocks 561 through 580**, not block 581. A second indicator-valued encoding gives:

| One-block burst onset | Actual context affected, counter | Actual context affected, gauge | `burst_cycles` selects |
|---|---|---|---|
| 560, just expired | False | False | False |
| 561, first included block | True | True | True |
| 580, last included block | True | True | True |
| **581, exactly at fit-end** | **False** | **False** | **True — wrong** |
| 582, after fit-end | False | False | False |

The increment ending exactly at `fit_end` belongs to block **e−1**, not e; admitting that increment does not admit a burst beginning at e. See finding R1.

I then independently compared the **actual full-run** S4/S6 burst plans against strict half-open intersection, for each A in cpu/mem/rx_bytes, W=576. All agree today: S4 bursts `[1536,1554)`, `[1752,1770)` give **55 selected cycles** per A; S6 burst `[1728,1746)` gives **23**. There are **zero onset==e cycles** in those plans. This bounds the current-data impact; it does not make the faulty equality branch correct. The existing 900-tick S4 test (`tests/test_refcompare_leakage.py:193-247`) similarly misses exact onset==e.

**Check actually performed for F5:** hand-built two-cycle `[C,6]` effects with unequal configured noise scales (`sigma_cpu=1.5`, `sigma_mem=12`). A's six raw effects all 3 give `dF_A_max_abs=2`; B's first cycle alternates `+12/-12`, second is all 24: library returned **B max=2, B mean=1, ratio=1**, matching per-cycle signed means then signal-specific normalisation. Making B alternate in both cycles returned **max=0, mean=0, ratio=0**. Inspected `leakage.py:249-273`: reduction precedes absolute values and both signals are normalised. No residual F5 issue found.

### F6 — D-A verdict and thresholds

Inspected `flat.py:43-82,108-118,142-158` and `scripts/run_c3.py:551-557`. The decisive boundary is sourced from **`hcfg.scoring.decisive_threshold`**, not a new literal in the reporting implementation; real flat receives it as a required keyword. Independent probe results:

| Input | Verdict | Normal / undecided / decisive fraction |
|---|---|---|
| all 0.1 | calm | `1 / 0 / 0` |
| all 0.3 | marginal | `0 / 1 / 0` |
| all exactly 0.2 | marginal | `0 / 1 / 0` |
| all exactly 0.8 | marginal | `0 / 1 / 0` |
| 98 values 0.1, then 0.2 and 0.8 | calm | `.98 / .02 / 0` |
| 97 values 0.1, then 0.2, 0.3, 0.8 | marginal | `.97 / .03 / 0` |
| 98 values 0.1, then 0.3 and 0.9 | calm; **one decisive tick reported** | `.98 / .01 / .01` |

The last row is intentional under the amended card/D-A(iv): calm is the ≥98% normal-occupancy rule, not a claim that no decisive tick exists. Keep `n_decisive` and `max` beside the verdict. `<0.02` is secondary only. The executed suite also covers the fails branch and threshold sanity checks.

### F7/F8 — per-horizon coverage and width

Inspected `coverage.py:161-204,207-267,292-349` and the shared counter/gauge alignment. Independent nonstationary cycle/step forecasts, observed drift, masks and a missing observation were constructed without repository test fixtures. Hand enumeration selected each cycle's own block `e+b` and raw index `20e + int(counter) + h`; comparison used the actual forecast row, not the coverage helper's selector.

| b | Block n, hand = library | Block q10–q90 coverage, hand = library | Raw n for gauge / counter | Raw q10–q90 coverage, hand = library |
|---|---:|---:|---:|---:|
| 3 | 16 | 1.0 | 320 / 320 | .45 / .45 |
| 6 | 16 | 1.0 | 320 / 320 | .075 / .075 |
| 12 | 15 | 0.0 | 300 / 300 | 0 / 0 |

All requested diagnostic horizons have their own eligible populations; b=3/12 no longer disappear through latest-serving-cycle selection. The result labels distinguish `horizon_b{b}` from `pooled_served_30_55min`. Native decile versus interpolated q25/q75 interval flags remain explicit; the suite checks both pairs and their interpolation.

Independent width example, widths `[10,20]` over observed `[1,100]`:

```text
median_width = 15.0
ratio_median_level = 0.297029702970297
sensitivity_median_of_ratios = 5.1
zero_median_level = False
```

This matches the declared statistic; the sensitivity is distinctly named. Zero-median handling and malformed input are covered in the executed suite. Raw-native and block hand-off calibration remain separate scientific quantities, not interchangeable labels.

### F9 — actual manifest/shard provenance

Inspected `runner.py:400-474,537-556`, the current manifest `input_policy`, and **all 118 shard metas**, not only the evidence description.

- Effective fields agree with the reviewed configuration: policy `causal-fit-end-v1`; cadence 15 s, tick 300 s, 20 samples/block; max gap 35 s; missing policy `nan`; counter estimator `block_ratio`; explicit past-only `ts <= fit_end`; timestamp-window/c+2 residual statement; 240/5760/11520 contexts.
- All four recorded config SHA256s match the actual config files. Model revision is `43046b85ec22d584a13f8098c2ed39c889e129c2`; declared weights SHA256 is `a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da`.
- **20/20 regenerated real shards contain `meta['policy']` exactly equal to the manifest policy.** All record **`code_git_head: "unknown"`**. That is an explicit missing identity, not a verified code commit; see R2.
- **90 synthetic + 8 leak shards have no per-shard policy**. E-C2-live.md:12 explicitly distinguishes these pre-field shards from the regenerated ones and describes digest-neutral causal rebuilding. **That historical disclosure is adequate:** it does not claim those fields were captured during the original CUDA run, and retaining the 98 original files is appropriate. Together with the unchanged hashes, archived manifest and sampled exact context-neutrality checks above, it is enough for this frozen dataset; do not represent an isolated old shard as independently carrying complete provenance.
- E-C2-live's reference to a C3 verification “below” has no accompanying verification transcript in that file as read. This review supplies its own requested sampled rebuild evidence; it does not claim to have run C3 stage-2 verify on every shard.

## Findings

### R1 — medium, remaining RV-C F4 — selector still admits a burst at the exclusive context endpoint

**Files/lines:** `src/refstudy/refcompare/leakage.py:127-140,154-156`; false support statement repeated in `tests/test_refcompare_leakage.py:196-221` and orchestration `E-C3.md:425-431`.

`blo <= e` is still inclusive at the upper endpoint. The actual context's block support is **`[e-W,e)` for both counter and gauge**. My raw-label and indicator probes above show no context effect for a one-block burst at e, but the selector includes it. This fails the named half-open boundary acceptance even though the original six-block error is fixed and the current S4/S6 selections happen not to encounter equality. Tests label counter grid index `20e` as block e, overlooking right-closed increment attribution to e−1.

**Recommended fix:** use `blo < e and lo < bhi`; correct the support documentation and add behavioral counter/gauge cases with onset exactly e, onset e−1, and expiration exactly at the lower boundary, derived from encoded raw samples. Retain the existing actual-S4 regression. No forecast regeneration is needed. Until corrected, any expanded/shifted masking experiment needs an explicit independent selector audit. S owns the decision whether the demonstrated current-matrix non-impact permits stage 2 before this small fix.

### R2 — low, residual RV-C F9 traceability — regenerated code identity is unknown

**Files/lines:** `src/refstudy/refcompare/runner.py:437-444,473`; `results/c2-run-manifest.json` field `input_policy.code_git_head`; all 20 regenerated real shards' `meta.policy.code_git_head`; orchestration `E-C2-live.md:12`.

**Specific check:** read every shard's policy, compared each real policy to the manifest, checked the four config hashes, and counted code identities: **20 × `unknown`**. The evidence's unqualified statement that the manifest now carries “code head” should not be read as a recorded revision. The code deliberately falls back to unknown when the remote synced directory lacks git metadata; config/model identities and input reconstruction remain usable, so this does not invalidate numerical results.

**Recommended action:** disclose this limitation explicitly in the regeneration evidence. Bind future synced runs to an externally supplied, verified revision or source-tree identity rather than relying solely on remote `git rev-parse`. If S adds a retrospective sidecar tying the existing MD5/sync evidence to a lab revision, label it retrospective; do not silently alter the forecasts or pretend a missing run-time identity was originally captured. No regeneration requested for this finding.

## Behavioral suite, lint, tracked payloads and invariants

Executed the requested full bounded suite, once:

```text
.venv/bin/python -m pytest tests/test_refcompare_*.py -q -p no:cacheprovider
........................................................................ [ 24%]
........................................................................ [ 49%]
........................................................................ [ 73%]
........................................................................ [ 98%]
....                                                                     [100%]
Wall time: 177.64 seconds
```

**292 passing case dots, no failure or skip markers.** The quiet configuration emits no separate summary sentence. Passing tests do not close R1: its existing boundary tests miss exact onset==e.

Executed:

```text
.venv/bin/ruff check --no-cache src/refstudy/refcompare tests/test_refcompare_*.py scripts/run_refcompare.py scripts/smoke_refcompare.py scripts/run_c3.py
All checks passed!
```

Inspected tracked payload paths with `git ls-files` covering data/artifacts/weights/fixtures and `*.safetensors`, `*.npz`, `*.pt`, `*.pth`, `*.bin`. Only `.gitkeep` placeholders, `data/packaged/MANIFEST-flat-load.json`, `tests/fixtures/candb_boxcar_digests.json`, and **D16's explicitly authorised `gold_live_b4xkt.json.gz` parity fixture** were listed. **No weights, forecast shards, or raw dump are tracked**; the pre-existing D16 raw-fixture exception must remain explicit. The reviewed five commits affect only the expected lab candidate code/tests/config or current/archived C2 manifests; no production, chain-law or threshold change appears in their file scopes. This is not a new full production-parity run.

The source keeps the unchanged rare-count provider and `score_pod`; TimesFM still substitutes only the four continuous references. Thresholds are reporting inputs from configuration, not retuned chain laws. The model's informational ESS remains distinct from STL's fit-path gate; conclusions must retain gate-on/off, availability, and raw `p_raw` vocabulary.

## Executor models and D15

Parsed every JSONL event in the four requested session logs under
`~/.omp/agent/sessions/-Work-langGraph-appthrust-agent-orchestration/2026-11-09T02-44-20-192Z_01a1be31-3c60-74d1-85d8-c7089d10ed2e/`.

| Session | Actual assistant provider/model | Assistant messages | Model-change fallback flag |
|---|---|---:|---|
| `RefmEFixC1a` | `vllm-tp2-local/qwen3.8-27b-q4-gpukv-native` | 278 | False |
| `RefmEFixC1b` | same | 171 | False |
| `RefmEFixC3a` | same | 108 | False |
| `RefmEFixC4a` | same | 108 | False |

Each log has one model-change entry selecting that configured local Qwen model; every assistant message records it. **No D15 model/fallback deviation is evidenced for these fix slices; none ran on Sonnet.** The regeneration is separately recorded as supervisor-run per D17 in E-C2-live; this reviewer did not run GPU work.

## Disposition rationale

The demonstrated F1 real-data leak has been removed and the affected 20 units genuinely replaced without destroying the original evidence. Independent raw truncation, stored-context rebuilds, unchanged synthetic hashes, store verification and a real-unit CPU reproduction now support using C2's 118 units scientifically. F2/F3/F5/F6/F7/F8 pass the requested behavioral checks. The remaining F4 equality defect prevents declaring the C3 library wholly compliant, but its exact non-impact on the frozen masking plans is measured, not assumed. Accept C2/C4 as stage-2 foundations with the stated provenance/interpretation caveats; close or explicitly disposition R1 before issuing an unrestricted C3/stage-2 safety claim. Final gate authority remains with S.
