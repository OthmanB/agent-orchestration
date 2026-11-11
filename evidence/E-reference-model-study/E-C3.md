# C3 — Phase C evaluation, per-unit pod evaluation (Executor evidence)

One section per workcard slice. This leaf (E) owns **S1a**:
`config/refcompare_eval.yaml`, `src/refstudy/refcompare/{eval_config,evaluate}.py`,
`tests/test_refcompare_{eval_config,evaluate}.py`.  S1b (`sidebyside.py`,
`leakage.py`, `flat.py`, `scripts/run_c3.py`) is a separate slice; its section
is added when it lands.  All paths relative to `reference-model-study/`
(lab repo `pipelineml-model-exploratory-work`).

---

## S1a — evaluation config (`refcompare_eval.yaml`) + per-unit evaluation (`evaluate.py`)

### 1.0 Preflight (record all)

```
$ git log --oneline -5
35fba07 chore(refstudy): archive pre-D8 B2 CUDA refresh measurement (superseded by remeasurement)
1863de3 feat(refstudy): add Phase C resumable inference runner and live-batch CLI (C2 slice 1b)
f8c618d fix(refstudy): shared plot limits, unresolved-power markers and power resolution rule (B2 fix C)
9370848 feat(refstudy): add Phase C run matrix config and unit expansion (C2 slice 1a)
93c594a feat(refstudy): add TimesFM pod pipeline, paired variants and CPU smoke (C1 slice 2b)
```

C1 Commit 2 (`93c594a`) and A1b3 (`76451a6`) are ancestors of HEAD
(`git merge-base --is-ancestor` ⇒ both yes).  `git status --short` at start: clean.

```
$ .venv/bin/python -c "from refstudy.refcompare import pipeline, store; \
from refstudy.harness import evaluate_records, load_harness_config; \
h=load_harness_config('config/harness.yaml'); \
print(h.ref_synth.metrics.include_rare_count, len(h.ref_synth.metrics.entries))"
True 11
```

```
$ grep -n "Stage 3" evidence/E-reference-model-study/E-A1b.md
95:## Stage 3 — production-shaped 11-metric set (tx_bytes + 7 quiet rare counts), Commit 3
(stage-3 FLAT K=11 p_raw summaries present: 700-tick and 1872-tick rows, seeds 1-3;
E-C3 will cross-check its own STL-lite recomputation at the common offset against them)
$ ls artifacts/refcompare | wc -l
0        # stage 2 not yet run (118 shards are S2b's stage 2; this slice is stage 1)
$ df -h / | tail -1
/dev/disk3s1s1  461G  419G   43G  91% /
```

### Files owned by S1a

- `config/refcompare_eval.yaml` (all evaluation tunables + provenance comments)
- `src/refstudy/refcompare/eval_config.py` (frozen `EvalConfig` + `load_eval_config`)
- `src/refstudy/refcompare/evaluate.py` (`common_offset`, `hcfg_common`,
  `verify_shard`, `tfm_pod`, `stl_pod`, `matched_valid`, `availability`, `EssReport`)
- `tests/test_refcompare_eval_config.py`, `tests/test_refcompare_evaluate.py`

### 1.1 YAML + `eval_config.py` (test: `test_refcompare_eval_config.py`, 41 tests)

`load_eval_config(path, rc_cfg, run_cfg, hcfg)` loads + fully validates
`config/refcompare_eval.yaml`; `ValueError` names the dotted key.

- **every required key named**: 32 missing-key cases covered
  (`inputs.*` 3, `profile.*` 8, `matched.min_ticks`, `leakage.*` 4, `flat.*` 4,
  `outputs.*` 4, plus the top-level `profile`/`matched`/`leakage`/`flat`/`outputs`
  nodes); e.g. `required config key missing: profile.digest_rtol`.
- **bool-as-number rejected** for `profile.digest_rtol`, `profile.seed_sweep`,
  `flat.calm_p`, `matched.min_ticks`, `leakage.window_blocks`,
  `profile.contexts.main` (via `refstudy.common.config.require`).
- **behavioural invariants that fail with a named key**:
  `profile.references` must be exactly the D-2 row set
  `{stl-gate-on, stl-gate-off, tfm-uni, tfm-multi}`; `profile.contexts.main`
  and each `profile.contexts.sweep[i]` must be a refcompare `input.contexts`
  value; `profile.digest_rtol` in `(0, 1)`; `leakage.bases` must be matrix
  scenarios (`run_cfg.matrix.scenarios`), no duplicates; `leakage.*_signals`
  must be continuous metrics of `reference.yaml`; `leakage.window_blocks`
  must equal `refcompare.cycle.shared_first_cycle_context_blocks` (576);
  `flat.*` fractions in `[0, 1]`; `flat.threshold` must equal the harness
  `scoring.alpha_threshold` (0.2, one operator threshold, not retuned).

### 1.2 `evaluate.py` (test: `test_refcompare_evaluate.py`, 12 tests)

All tests use the stub-shard machinery of C1 `store` on
`get_scenario('S4', 1, n_ticks=900)` with the card's overrides: a stub plan
from the C2 shared-2d first cycle `n0 = min_first_n0(11520) = 588` (53
cycles on 900 ticks; the 1 h ctx-240 model contexts), the test-only
`min_served=12` gate override, and the small common offset
`hcfg_common(hcfg, 606)` where 606 is the stub pod's own first scored tick.
Stub forecasts = deterministic seeded float32 quantile rows (seed 17); every
stub shard is written with `write_shard_atomic` at the C2 standard name
(`syn_S4_1_240_{multi,uni}.npz`).

- `common_offset(rc_cfg, ref_cfg) == 1118`: derived from YAML
  (`first_valid_tick(576 blocks × 20 pts, ref_cfg, origin 0)`), never retyped.
- `hcfg_common` returns a new frozen config; the input's
  `scoring.warmup_tick_end_offset` (584) is unmodified; `offset` 0 / 2.5
  raise `ValueError` naming `offset`.
- **first valid `k+1` = the offset**: `tfm_pod` on the stub multi shard under
  `hcfg_common(hcfg, 606)` ⇒ `first_valid_k_plus_1 == 606 == the offset`,
  `n_valid == |valid|`.
- **a shard with one altered digest ⇒ `ValueError`**: the stored digest row of
  cycle 3 / variate 2 is bumped by 1.0 in the `.npz` while `q` stays
  consistent ⇒ `tfm_pod` fails with `...forecast digest...` (the verify
  re-hashes every forecast row against the stored digest, so any altered
  digest row - whether `q` or the digest was moved - is caught).
- **a shard whose `fit_end` is shifted by +T ⇒ leakage `ValueError`**: the
  stub's `t0` array is shifted by `+300 s` (one tick), i.e. every cycle's
  `fit_end = t0 - T - dt` moved by `+T` ⇒ the verify's t0-vs-plan check fails
  with `...fit_end moved... - leakage` (the model's data would extend past
  the planned fit end).
- **uni and multi shards holding the same arrays ⇒ identical `EvalResult`**:
  two stubs (same `q`, same digests, `mode` uni vs multi) ⇒
  `p_raw` array-equal and `quantities` of `fpr` / `events` / `fidelity`
  equal (the call shape only changes how the forecast was produced, not the
  chain's input once the rows are in the shard).
- **gate on vs off on the strongly diurnal S1 hand scenario (SNR≈6.7, 900
  ticks)**: `stl_pod(scn, hc, gate=True)` has `gated > 0` per-metric
  (cpu 26/54, mem 19/54, rx_bytes 26/54, tx_bytes 23/54 - from the
  `on_cycle` `CycleReport`s, floor 36 read from `reference.yaml`), fewer
  scored ticks (163 vs 317) and lower `availability` than `gate=False`
  (`gated == 0`); `n_v0` identical (same V0); `stale_ticks == 0` on the
  off-variant; the input `hcfg` / `RefConfig` are unmodified
  (`H.ref_synth.noise.min_effective_samples == 36` asserted after both runs);
  the `EssReport` per-metric carries `cycles`, `gated`, `ess_min`,
  `ess_median` and `ess_min < 36` wherever `gated > 0`.
- `matched_valid` on hand masks: intersection of two valid masks
  (10:40 ∧ 20:50 = 20 ticks, mask asserted tick-wise); empty sequence ⇒
  `ValueError`; a mismatched `n_ticks` ⇒ `ValueError`.
- `availability` on hand masks: `n_v0`, `n`, fraction and `stale_ticks`
  (the gate's stale hours) checked against hand values; a `v0` mask input
  gives the same block as the offset form; `v0 = 0` raises.

### 1.4 E smoke (real-weights C2 stage-2 CPU shards, card step 1.4)

`throwaway/c3_s1a_smoke.py` (git-ignored) takes the C2 stage-2 smoke shards
(`throwaway/c2-smoke/shards`, ctx 240, 3 cycles, real TimesFM-3 weights on
CPU) with the test-only `min_served=0` (a 3-cycle shard never reaches the
`min_served=12` gate) and the small common offset = the pod's own first
scored tick.  Literal output (nothing asserted):

```
$ .venv/bin/python throwaway/c3_s1a_smoke.py
syn shard S1@1 ctx240: n_records=1872 scored=6 first_scored=600 wall_s=1.3
  first_valid_k_plus_1=600 (== offset 600) n_valid=6 median=0.0012 max=0.0013 fpr=0.0 (n=6)
  availability=0.005 n=6 n_v0=1273 stale=1267
  stl ess: on gated=345 off gated=0
real shard b4xkt ctx240: n_records=1728 scored=6 first_scored=601 eval_result=None (real units skip evaluate_records) wall_s=4.5
smoke ok
```

(`stale=1267` is expected here: 3 of 53 planned cycles carry models -
the smoke cap, not a gate effect; the `stl_pod` ESS numbers are the same
real S1 pod: gate-on gates 345 of the dt-cycles, gate-off none.)  Wall
≈ 7 s total, far under the 5-min budget.

### 1.5 Gates (literal, post-commit)

```
$ .venv/bin/python -m pytest tests/test_refcompare_eval_config.py \
    tests/test_refcompare_evaluate.py -q
.....................................................                    [100%]
53 passed in 5.20s        (41 + 12, 0 skipped)

$ .venv/bin/python -m pytest tests/test_refcompare_*.py -q
........................................................................ [ 78%]
.......................................                                  [100%]
183 passed in 99.47s      (all 14 test_refcompare_*.py files, 0 skipped:
                           130 pre-existing + 53 new)

$ .venv/bin/ruff check src/refstudy/refcompare \
    tests/test_refcompare_eval_config.py tests/test_refcompare_evaluate.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare
# (empty, exit 1)

$ git diff --check
# (clean)
```

### Commit

```
feat(refstudy): add Phase C evaluation config and per-unit evaluation (C3 slice 1a)
```

Commit hash: `d313f42` (lab repo `main`, 5 files, +1216 lines; explicit
`git add` of the 5 owned paths only).

### Deviations / notes for S1b

- **`verify_shard` signature**: the contract's `verify_shard(shard,
  scenario_or_real, rc_cfg, rtol)` takes `ref_cfg` as a keyword because the
  chain's `RefConfig` (K=11, grid T/dt) is needed to rebuild the pod grid -
  it is the `ref_synth` (syn/leak) or `ref_real` (real) of the harness, not a
  property of the refcompare config.  `tfm_pod`/`stl_pod` pass it internally.
- **`tfm_pod` needs `rc_cfg`** (keyword) for the same reason: the grid
  cadence / max-gap of the context rebuild live in `refcompare.yaml`.  The
  card's one-arg `store_dir` is kept; `rc_cfg` is the extra keyword.
- **The verify re-hashes BOTH the forecast rows (`digest` vs
  `shard.digest`) and the rebuilt contexts (`context()` vs
  `meta.context_digest`)**: the forecast-row check catches any altered digest
  (step 1.2), the t0-vs-plan check catches a shifted `fit_end` (the leakage
  case), the context check proves the Mac re-derived the model inputs (P3).
- **`stale_ticks`** = ticks at/after the first model tick at which NO
  continuous metric carries a model (card D-6 "ticks ≥ first …").  0 for
  TimesFM rows (the provider never un-serves); the gate's stale-model hours
  for STL rows.
- **Real-pod pod grid**: the 4 continuous series sliced by `real_slice`
  define `origin`/`n_ticks` (the shard domain, exactly C2 `build_unit`); the
  7 rare-count series are cut at the same 6.0 d cutoff and enter the K=11
  chain.  Verified identical (same origin, same `n_ticks` = 1728) on all 10
  packaged pods before committing (probe, not a test).
- **`matched_valid` / `availability`** are pure helpers on `EvalResult`s;
  S1b's `sidebyside.py` composes them into the per-row `availability` /
  `matched` blocks of `c3-profile.json`.

---

## S1b — side-by-side profile, masking probe, flat control (`sidebyside.py`, `leakage.py`, `flat.py`, `scripts/run_c3.py`)

### Files owned by S1b

- `config/refcompare_eval.yaml` (extended: `special` node - `s3.scenarios`,
  `s3.pulse_peak_ticks`, `advantage.signals`)
- `src/refstudy/refcompare/eval_config.py` (extended: `SpecialSpec`,
  validation of the `special` node)
- `src/refstudy/refcompare/sidebyside.py` (new: `build_profile`,
  `s3_pulse_rows`, `s7s8_advantage`, `deltas`, `profile_rows`,
  `write_profile_csv`)
- `src/refstudy/refcompare/leakage.py` (new: `burst_cycles`,
  `forecast_bands`, `cross_signal_leakage`, `uni_input_identity`)
- `src/refstudy/refcompare/flat.py` (new: `verdict`, `p_raw_summary`,
  `synthetic_flat_summary`, `real_flat_summary`)
- `scripts/run_c3.py` (new: `--stage verify|profile|leakage|real|all`,
  `--smoke-dir`, `--max-minutes`)
- `tests/test_refcompare_eval_config.py` (extended: +8 new tests -
  `special` missing-key cases, bool-as-number, S3-matrix/duplicate and
  advantage-vs-continuous-count checks; 49 collected)
- `tests/test_refcompare_{sidebyside,leakage,flat}.py` (new: 22 tests:
  6 + 6 + 10)

### 1.3 Tests (literal)

```
$ .venv/bin/python -m pytest tests/test_refcompare_sidebyside.py \
    tests/test_refcompare_leakage.py tests/test_refcompare_flat.py -q
......................                                                   [100%]
22 passed        (6 sidebyside + 6 leakage + 10 flat; wall 6.7 s first run,
                 10.3 s after the post-smoke dead-helper cleanup)

$ .venv/bin/python -m pytest tests/test_refcompare_*.py -q
........................................................................ [ 27%]
........................................................................ [ 54%]
........................................................................ [ 82%]
..............................................                           [100%]
262 passed in ~110 s   (0 failed, 0 skipped; run AFTER the commit, so it
                        includes the sibling C4-S1 files that were in tree
                        at the time - test_refcompare_bands.py (38) and
                        test_refcompare_coverage.py (11).  S1b-relevant
                        total: 262 - 49 = 213 = the 183 S1a baseline
                        + 8 new eval_config + 22 new S1b)
```

### 1.4 E smoke (real-weights C2 stage-2 CPU shards, card step 1.4)

`run_c3.py --smoke-dir throwaway/c2-smoke/shards` (ctx 240, 3 cycles,
real TimesFM-3 weights on CPU; test-only `min_served=0`; the smoke common
offset is the first syn shard's pod's own first scored tick = 600, NOT
asserted, NOT the 1118 common offset).  Literal (INFO lines only):

```
$ .venv/bin/python scripts/run_c3.py --stage verify --smoke-dir throwaway/c2-smoke/shards
2026-11-10 08:33:03.871 | INFO | verified leak:S4@cpu:1:240:multi (leak_S4@cpu_1_240_multi.npz)
2026-11-10 08:33:04.373 | INFO | verified real:b4xkt:-:240:multi (real_b4xkt_-_240_multi.npz)
2026-11-10 08:33:04.400 | INFO | verified syn:S1:1:240:multi (syn_S1_1_240_multi.npz)
2026-11-10 08:33:04.426 | INFO | verified syn:S1:1:240:uni (syn_S1_1_240_uni.npz)
2026-11-10 08:33:04.426 | INFO | verify: 4/4 shards ok (rtol 1e-06)
2026-11-10 08:33:04.426 | INFO | stage(s) verify done in 2.5 s        (wall 3.2 s)

$ .venv/bin/python scripts/run_c3.py --stage profile --smoke-dir throwaway/c2-smoke/shards
2026-11-10 08:34:17.005 | INFO | tfm_pod syn:S1:1:240:uni -> 1872 records (6 scored)
2026-11-10 08:34:17.673 | INFO | tfm_pod syn:S1:1:240:multi -> 1872 records (6 scored)
2026-11-10 08:34:18.677 | INFO | stl_pod S1 gate=True -> 1872 records (732 scored), gated=345
2026-11-10 08:34:19.882 | INFO | stl_pod S1 gate=False -> 1872 records (1289 scored), gated=0
2026-11-10 08:34:19.887 | INFO | profile: 1 scenario-context blocks -> results/c3-profile.json / results/c3-profile.csv
2026-11-10 08:34:19.888 | INFO | stage(s) profile done in 6.2 s        (wall 6.9 s)
  -> S1@240: refs {stl-gate-on, stl-gate-off, tfm-uni, tfm-multi},
     matched {n: 0, min_ticks: 48, available: False} (honest smoke outcome:
     the 3-cycle tfm pods' 6 valid ticks do not overlap the stl rows' valid
     set at the same V0), 4 delta pairs (tfm-{uni,multi}/stl-gate-{on,off}),
     first_valid stl-on 618 / tfm-multi 600, csv 44 rows
     (smoke artifacts deleted post-smoke; stage 2 regenerates)

$ .venv/bin/python scripts/run_c3.py --stage leakage --smoke-dir throwaway/c2-smoke/shards
2026-11-10 08:34:58.874 | INFO | leakage: 24 pairs -> results/c3-leakage.json
2026-11-10 08:34:58.874 | INFO | stage(s) leakage done in 5.4 s        (wall 6.1 s)
  -> all 24 pairs {error: "run_c3: shard missing for leak:S4@none:1:240:multi: ..."}
     (the smoke store carries ONLY the S4@cpu variant; the @none/S6 variants
     are stage-2 - by construction, not a failure; recorded as a deviation)

$ .venv/bin/python scripts/run_c3.py --stage real --smoke-dir throwaway/c2-smoke/shards
2026-11-10 08:35:28.948 | INFO | tfm_pod real:b4xkt:-:240:multi -> 1728 records (6 scored)
2026-11-10 08:35:28.951 | INFO | real flat: 1 pods x 4 refs -> results/c3-real-flat.json
2026-11-10 08:35:28.951 | INFO | stage(s) real done in 2.9 s           (wall 3.6 s)
  -> b4xkt pod_offset=601 (its own first scored tick, card D-1):
     tfm-multi n_pods=1 fleet verdict=calm n=6;
     tfm-uni + both stl rows -> "no pod carries this reference
     (shard missing ...)" (stl rows skipped in smoke; tfm-uni never sharded)
```

Wall total ≈ 20 s across the four stages, far under the 5-min budget.

**Refusal without `--smoke-dir`** (no C2 shard store present):

```
$ .venv/bin/python scripts/run_c3.py --stage verify
2026-11-10 08:35:43.823 | ERROR | refusing verify: the shard store
  /Users/obenomar/Work/langGraph/appthrust/pipelineml-model-exploratory-work/reference-model-study/artifacts/refcompare has no shards.
  The real runs need the C2 shard store (... - run the approved C2 live batch first),
  or pass --smoke-dir pointing at the C2 stage-2 CPU smoke shards (throwaway/c2-smoke/shards).
$ echo $?
1
```

`--stage real` without a store refuses identically (exit 1).

### 1.5 Gates (literal, post-commit)

```
$ .venv/bin/ruff check src/refstudy/refcompare tests/test_refcompare_eval_config.py \
    tests/test_refcompare_evaluate.py tests/test_refcompare_sidebyside.py \
    tests/test_refcompare_leakage.py tests/test_refcompare_flat.py scripts/run_c3.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare
# (empty, exit 1)

$ git diff --check
# (clean)

$ git status --short
# modified: the 5 owned lab files (+ the S1b-owned test files staged in the
# commit); untracked sibling C4-S1 paths (config/refcompare_bands.yaml,
# src/refstudy/refcompare/{bands,coverage}.py,
# tests/test_refcompare_{bands,coverage}.py) left untouched;
# no reference/ / harness/ / C1-C2 / pyproject diffs
```

### Commit

```
feat(refstudy): add Phase C side-by-side profile, masking probe and flat-control library (C3 slice 1b)
```

Commit hash: `03734c2` (lab repo `main`, 10 files, +2085/−1; explicit
`git add` of the 10 owned paths only).

### Deviations / notes for stage 2

- **Leakage smoke = 24/24 pairs `error` by construction**: the C2 smoke
  store carries only `leak_S4@cpu_1_240_multi`; every (base, A, B) pair
  additionally needs the `@none` variant shard (and S6-base pairs the S6
  shards), which are stage-2 outputs.  The probe code itself is covered by
  the seeded unit tests in `test_refcompare_leakage.py` (dF_B = 0.5σ for a
  uniform +0.5σ shift, `uni_input_identity` true/false, `burst_cycles`
  exact selection, band shape checks).
- **Profile smoke = S1@240 only**: the smoke store's only syn units are
  S1 seed 1 @240 uni+multi.  `matched.available=False` is the honest
  3-cycle outcome (6 tfm valid ticks, no overlap with the stl rows' valid
  set at the common smoke V0=600), not a gate failure.
- **Real smoke = b4xkt tfm-multi only**: smoke skips the stl rows (the 6.0 d
  chain run is a stage-2 cost) and runs only pods the store carries;
  `real_flat_summary` on one pod/fleet of n=6 verdicts `calm`.
- **`results/c3-*.json/csv` smoke artifacts were deleted post-smoke** (stage
  2 regenerates them at the full matrix); they are not part of the commit.
- **`build_profile` is subset-safe**: it builds only the reference rows
  PRESENT in `results` (each a D-2 row name; ≥1 stl + ≥1 tfm required;
  unknown names → `ValueError`).  `deltas`, `s3_pulse_rows` and
  `s7s8_advantage` iterate present rows - this is what makes the
  store-scoped smoke run possible without a second config path.
- **A/B vocabulary in `leakage.py` is the card's SHORT names**
  (`sigma_B` from `hcfg.scn.signals`, `EvalResult` arrays keyed short);
  shard/band keys are CANONICAL - `cross_signal_leakage` accepts both via
  the short→canonical map, `uni_input_identity` maps short→canonical for
  the context grid.  `burst_cycles` takes the caller's C2 `plan_cycles`
  plan (the card's `min_first_n0(shared_pts)` first n0), not a scenario
  attribute.
- **Real-pod V0** = the pod's own first scored tick (card D-1), computed
  once per pod from the first available reference's `PodRun` and shared by
  all four references; `pod_offset` is recorded in `c3-real-flat.json`.

---

## Fix C3a — RV-C F4, F5, F6 (masking-probe windows + statistic, D-A flat verdict)

RV-C rejected C3 slice 1 (`d313f42`, `03734c2`): the burst-cycle selector
(F4), the reported masking statistic (F5) and the D-A flat verdict
migration (F6) were all wrong. This slice fixes the three findings
in-place (no new module, no threshold / chain-law change, no shard or
result-file regeneration).

### Files owned by Fix C3a

- `src/refstudy/refcompare/leakage.py` (F4 `burst_cycles`, F5
  `cross_signal_leakage` + module docstring)
- `src/refstudy/refcompare/flat.py` (F6 `verdict`, `p_raw_summary`,
  `synthetic_flat_summary`, `real_flat_summary` + module docstring)
- `scripts/run_c3.py` (migrate the `real_flat_summary` caller to pass the
  harness `decisive` 0.8)
- `tests/test_refcompare_leakage.py`, `tests/test_refcompare_flat.py`
- `sidebyside.py` was checked: it does NOT consume the flat summary
  (zero `flat` references), so no change was needed there.
- `config/refcompare_eval.yaml` is UNCHANGED: the D-4 flat block already
  carries `calm_p 0.02 / threshold 0.2 / max_outside_fraction 0.02 /
  workers 4`, and the decisive 0.8 comes from the harness
  `scoring.decisive_threshold` (workcard D-4: "never a literal", not a new
  `flat` key) — sourced inside `synthetic_flat_summary` and passed by
  `run_c3.py` for `real_flat_summary`.

### F4 — `burst_cycles` now uses the actual context's block support

The old selector used `n0 - 1` as the fit-end block and an inclusive
`blo <= hi` test, so it flagged a cycle SIX BLOCKS EARLY (selecting c = 33
prematurely) and OMITTED the genuinely-affected late cycles (c = 3, 39).
`Cycle.e` is `n0 - 7` (the block index of `fit_end`, the model's last
usable data; `cycles.py` header), and the ACTUAL context read by
`cycles.context` carries `window_blocks` whole blocks back from `e`
(counter context ends at grid idx `20e + 1` = block `e`; gauge ends at
`20e` = block `e - 1` + last sample). The selector now intersects the
burst windows `[onset, onset + duration)` (half-open, in blocks) against
the context support `[e - window_blocks, e]` half-open:

    flagged iff  (burst_lo <= e) AND (e - window_blocks < burst_hi)

`window_blocks < 1` raises.  **Boundary tests are derived from
independently inspected context samples** (the block range of
`cycles.context` was computed for each cycle on the real S4 grids), NOT by
reproducing the formula: on S4 seed 1 (bumps `[564,582)`, `[780,798)`),
`window_blocks = 20`:

| cycle | n0 | e | context blocks | verdict | why |
|---|---|---|---|---|---|
| c = 0 | 588 | 581 | [561, 581] | flagged | burst [564,582) overlaps 564..581 |
| c = 3 | 606 | 599 | [579, 599] | flagged | burst just before fit-end: ends 581, still in [579,599] |
| c = 4 | 612 | 605 | [585, 605] | NOT flagged | expiry: context starts 585, past burst end 581 |
| c = 33 | 786 | 779 | [759, 779] | NOT flagged | burst just after fit-end: starts 780, past e = 779 |
| c = 34 | 792 | 785 | [765, 785] | flagged | burst at/into context: 780..785 overlap |
| c = 39 | 822 | 815 | [795, 815] | flagged | expiry boundary: burst ends 797, still in [795,815] |
| c = 40 | 828 | 821 | [801, 821] | NOT flagged | expiry: context starts 801, past burst end 797 |

So `burst_cycles(S4@cpu, 20) = (0,1,2,3,34,35,36,37,38,39)`; the old
`n0 - 1` formula gave `(0,1,2,33,34,35,36,37,38)` (premature 33, missing 3
and 39).  A 300-block context is still a strict superset.

### F5 — statistic is now mean-of-served-block effects, noise-normalised

The card's `dF_B[c] = mean_{b=6..11}(F_B[c,b]^{A} - F_B[c,b]^{none}) /
sigma_B`. The old code kept the `[C,6]` per-block effects and reported the
max/mean of ABSOLUTE individual blocks, so signed effects that cancel
across the six blocks reported 1.0 instead of 0, and `dF_A` was left in
raw A units while B was normalised (a mixed-dimensional ratio). The fix
reduces the six served blocks along the block axis FIRST (per-cycle mean,
raw units) and THEN normalises by that signal's own `noise_sd` — A and B
share a common noise-normalised scale (the dimensional choice of card D-3,
documented in the module + `cross_signal_leakage` docstrings). New
behavioural tests:

- uniform +0.5σ shift of B → `dF_B` = 0.5 (unchanged); A's own effect is
  now the per-cycle MEAN of `[1,2,0.5,1,1.5,1]` = 7/6, normalised by
  `sigma_A = 1.5` → `dF_A_max_abs = 7/9` (the old test wrongly expected the
  per-block maximum 2.0 — fixed).
- alternating `±1` across the six blocks → per-cycle mean exactly 0.0
  (`dF_A_max_abs = 0`, `ratio = None`), not 1.0.
- unequal A/B noise scales (both +3.0 raw, `sigma_A = 1.5` vs
  `sigma_B = 12.0`) → `dF_A = 2.0`, `dF_B = 0.25`, `ratio = 0.125`
  (a common noise-normalised ratio, not 1.0).
- the output now also carries `sigma_A`.

### F6 — D-A flat verdict + three-class summary (C3 slice 1c cutover)

`verdict(calm_p, threshold, decisive, max_outside_fraction, p)`:
`calm` iff `frac_normal (= frac p_raw < 0.2) >= 1 - max_outside_fraction`
(≥ 98 % decisively normal); `marginal` iff not calm and ZERO ticks
decisive (`p_raw > 0.8`); else `fails` (any decisive tick). Both class
boundaries are strict (D-A): a tick AT 0.2 is undecided, a tick AT 0.8 is
not decisive. `calm_p` (0.02) is not a verdict input — it only feeds the
secondary `frac_lt_calm_p`.  `p_raw_summary(p, calm_p, threshold,
decisive)` now returns `{n, q50, q99, max, frac_normal, frac_undecided,
frac_decisive, n_decisive, frac_lt_calm_p}` (the old `frac_gt_calm_p` is
retired; `frac_lt_calm_p` is the secondary Q4 statistic). The decisive 0.8
is read from `hcfg.scoring.decisive_threshold`, never a literal. RV-C's
counterexamples now give the amended verdicts: all-0.1 → `calm`,
all-0.3 → `marginal`. `synthetic_flat_summary` sources the 0.8 from the
harness; `real_flat_summary` takes it as a required `decisive=` keyword
(`run_c3.py` passes `hcfg.scoring.decisive_threshold`).

New/updated flat tests: the exact 98 % boundary (98/100 normal = calm,
97/100 = marginal), p == 0.2 (undecided, does not count as normal) and
p == 0.8 (not decisive) boundaries, all-0.1 = calm and all-0.3 =
marginal, a lone 0.8 leaving the pool calm, threshold-ordering sanity
(`calm_p <= threshold < decisive`), and the three-class fractions with
`n_decisive` / `frac_lt_calm_p` reported.

### Gates (literal)

```
$ .venv/bin/python -m pytest tests/test_refcompare_leakage.py \
    tests/test_refcompare_flat.py -q -p no:cacheprovider
15 + 9 = 24 passed          (leakage 9, flat 15; 0 skipped)

$ .venv/bin/python -m pytest tests/test_refcompare_*.py -q -p no:cacheprovider
357 passed, 0 failed, 0 skipped   (full C3/C4 slice-1 tree, incl. the
                                   in-tree C1-fix-B F3 provider/pipeline
                                   changes - confirming compatibility)

$ .venv/bin/ruff check src/refstudy/refcompare \
    tests/test_refcompare_leakage.py tests/test_refcompare_flat.py \
    tests/test_refcompare_sidebyside.py tests/test_refcompare_eval_config.py \
    scripts/run_c3.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare
# (empty, exit 1)

$ git diff --check
# (clean)
```

### Commit

```
fix(refstudy): masking-probe windows and statistic, D-A flat verdict (RV-C F4 F5 F6)
```

Commit hash: `c947347` (lab repo `main`, 5 files: `leakage.py`, `flat.py`,
`run_c3.py`, `test_refcompare_leakage.py`, `test_refcompare_flat.py`,
+439/−107; explicit `git add` of the 5 owned paths only). The concurrent
C1-fix-B files (`provider.py`, `pipeline.py`) and the pre-existing
`results/a1a-parity.json` modification were deliberately NOT staged.

### Deviations / notes for S

- **No `config/refcompare_eval.yaml` change**: workcard D-4 keeps the flat
  block at `calm_p / threshold / max_outside_fraction / workers`; the 0.8
  is the harness `scoring.decisive_threshold` (never a literal, never a new
  `flat` key). The "YAML keys as needed (required keys + tests)" in the
  task was satisfied by the existing required keys — no new key was
  required.
- **`sidebyside.py` unchanged**: it does not consume the flat summary
  (verified: zero `flat` references), so its tests needed no update.
- **`burst_cycles` window_blocks guard**: a `window_blocks < 1` call now
  raises (defensive; the YAML cross-check already forces it to equal the
  576 shared-first-cycle blocks).
- **F6 "fails" needs BOTH not-calm AND ≥ 1 decisive tick**: with 100 ticks
  a single decisive tick still leaves `frac_normal = 0.99 >= 0.98` (calm);
  the tests use > 2 % non-normal + ≥ 1 decisive to reach `fails`.

---

## Slice 1c + F4 (refm-C3 step 1.6 sidebyside part + RV-C2 F4 residual)

Two small slices, two commits (lab repo `main`, explicit `git add` of the 4
owned paths only, no push):

1. `refactor(refstudy): express Phase C side-by-side rows in D-A three-class units (C3 1c)` — hash `005faaf` (2 files, +213/−8).
2. `fix(refstudy): half-open burst-cycle selector at fit_end (RV-C2 F4)` — hash `3b34c1a` (2 files, +95/−5).

### C3 1c — side-by-side rows in D-A three-class units (card step 1.6, `sidebyside.py` part)

The DB 1.6 cutover commit `7ea2966` had already migrated the two occupancies
(`undecided_occupancy` / `decisive_occupancy`) and the two per-event
latencies (`latency_leave_normal` / `latency_decisive`) into the seed rows,
the deltas and the CSV, and had added the S3 decisive-anomaly latency.  This
slice completes step 1.6 for the remaining D-A units the card names
(`class_fraction`, `p_raw_quantile`, `mechanism_count`) and the per-row
D-B attribution (acceptance 2: "every row has its DB `classes` … and
`mechanism`"):

- **`_seed_list` (per-seed JSON rows)** now carry `classes` (the valid and
  quiet three-class counts, `n == normal + undecided + decisive`) and the
  per-seed `mechanism` block (the D-B counts that sum to the decisive ticks),
  next to the existing `availability`, `undecided_occupancy`,
  `decisive_occupancy` and `events`.
- **`deltas`** (each tfm row vs BOTH stl rows) now carry, in addition to the
  two latencies / two occupancies / settle / fidelity ratio already there,
  `class_fraction` (per class: `tfm_mean`, `stl_mean`, absolute `delta`),
  `p_raw_quantile` (per q05..q99 level, same shape) and
  `mechanism_count` (per D-B class, same shape).
- **`profile_rows` (flat CSV)**: the generic pre-D-A `p_raw` quantity rows
  (which mixed quantiles, class fractions, `max` and `n_valid` under one
  quantity name) are replaced by the D-A quantity rows, matching the harness
  `aggregate.profile_rows` convention: `class_fraction` (key = the class),
  `p_raw_quantile` (key = q05..q99; `max` / `frac_*` stay in the JSON only)
  and `mechanism_count` (key = the D-B class).  The availability, two
  occupancies, `latency_leave_normal` / `latency_decisive`, settle and
  fidelity rows are unchanged; the CSV field set (base columns) is unchanged
  so `scripts/run_c3.py`'s `csv.DictWriter` path is unaffected.

`flat.py` needed no change for this slice (its D-A three-class
`p_raw_summary` + `verdict` landed in `c947347`, card step 1.6 flat part).

New tests (`tests/test_refcompare_sidebyside.py`, 9 total: 6 pre-existing +
3 new), all on hand-built `EvalResult`s in the new schema (no model, no
weights): `test_deltas_carry_da_units` (the deltas of each tfm row vs BOTH stl
rows carry `class_fraction` / `p_raw_quantile` / `mechanism_count` with the
right absolute deltas, alongside the occupancies + latencies),
`test_profile_rows_emit_da_quantities` (the CSV carries one
`class_fraction`/class, `p_raw_quantile`/level and `mechanism_count`/D-B
class row per reference, the old generic `p_raw` rows are gone, spot-checked
values), `test_seed_rows_carry_classes_and_mechanism` (each seed row's
`classes.valid` sums to `n` and its `mechanism` counts sum to the decisive
tick count).

### F4 — half-open burst-cycle selector at `fit_end` (RV-C2 F4 residual)

`leakage.burst_cycles` flagged a cycle iff `any(blo <= e and lo < bhi)` —
the inclusive left edge admitted a burst whose first block was exactly
`e`, the fit-end block.  The correct half-open intersection of the burst
window `[blo, bhi)` against the actual context block support is
`blo < e and lo < bhi` (context support `[e - W, e)`, block `e` excluded).
This is a library boundary/test defect only: no actual S4/S6 cycle of the
frozen C2 plans ever sits at a burst's first block (`564`/`780` are not of
the form `6k − 7` = `n0 − 7`), so the frozen 576-block selections are
unchanged and the stage-2 leakage numbers are unaffected.

The existing S4 20-block regression (`test_burst_cycles_select_context_window`,
expected `(0, 1, 2, 3, 34, 35, 36, 37, 38, 39)`) still passes unchanged — no
S4 cycle has `e` exactly equal to a burst onset, so the boundary change is
invisible to it.

New test `test_burst_cycles_half_open_boundary_at_fit_end` (11 leakage
tests total: 10 pre-existing + 1 new).  It encodes the five boundary cases
independently of the selector formula: for each single-block burst it
INSPECTS the actual context samples read by `cycles.context` — a counter raw
grid (rate raised inside the burst block, resampled through `grid.to_grid`)
AND a gauge raw grid (level raised), both fed through the real
`cycles.context` on the cycle at `e = 581` with a 20-block window — and
records whether the context changes:

| case | burst block `b` | inspected counter context | inspected gauge context | selector (`blo < e and lo < bhi`) | old (`blo <= e`) |
|---|---|---|---|---|---|
| burst starts at `e-1` | 580 | changed | changed | flagged | flagged |
| burst starts at `e` (= `fit_end`) | 581 | unchanged | unchanged | NOT flagged | **flagged (the bug)** |
| burst starts at `e+1` | 582 | unchanged | unchanged | NOT flagged | NOT flagged |
| burst ends at context start | 560 | unchanged | unchanged | NOT flagged | NOT flagged |
| burst's first block = context start | 561 | changed | changed | flagged | flagged |

Counter and gauge agree in every case (both contexts exclude block `e`), and
the test asserts the selector reproduces the inspected truth on hand
scenarios carrying a single bump at each onset (`dataclasses.replace` on the
`FLAT` base scenario), including that the start-`e` case is NOT flagged.
The old formula would have failed exactly the start-`e` assertion.

### Gates (literal, post-commit; `reference-model-study/`)

```
$ .venv/bin/python -m pytest tests/test_refcompare_sidebyside.py \
    tests/test_refcompare_leakage.py -q
...................
19 passed, 0 skipped    (9 sidebyside + 10 leakage)

$ .venv/bin/python -m pytest tests/test_refcompare_*.py -q \
    --ignore=tests/test_refcompare_plots.py
288 passed, 0 failed, 0 skipped   (19 tracked test_refcompare_*.py files;
                                   ~183 s wall)

$ .venv/bin/ruff check src/refstudy/refcompare/sidebyside.py \
    src/refstudy/refcompare/leakage.py \
    tests/test_refcompare_sidebyside.py tests/test_refcompare_leakage.py
All checks passed!

$ grep -rniE 'solo_mode|sys\.path' src/refstudy/refcompare
# (empty, exit 1)

$ git diff --check
# (clean)
```

### Deviations / notes

- **`tests/test_refcompare_plots.py` is UNTRACKED** (a concurrent C4
  plots-slice sibling file, `??` in `git status`; it imports the untracked
  `src/refstudy/refcompare/plots.py`).  On the disk it currently fails 5 of
  its own tests (`NameError: name 's' is not defined` inside
  `test_plot_real_bands_fans_and_strip`, a matplotlib
  `twin`-with-bool `TypeError`, and 3 assertion failures) — a half-written
  sibling file, NOT caused by this slice (this slice touches none of
  `plots.py` / `bands.py` / `plots` tests; all 5 failures are inside that
  one untracked file).  The gate above therefore excludes it with
  `--ignore`; on the COMMITTED tree (no untracked file in the glob) the full
  `pytest tests/test_refcompare_*.py -q` is green 288/288, 0 skipped.  The
  committed tree is the authoritative gate result; S should re-run the gate
  once the C4 plots slice lands (or delete the untracked file if it is
  scratch).
- **No `config/` or `results/` changes**: slice 1c re-expresses existing
  quantities into the card's named D-A rows; no new YAML key was required
  (the D-A units already exist in the harness schema the `EvalResult`
  payloads carry).
- **No chain law, threshold or tolerance retuned** (D-7); the F4 fix is a
  boundary correction of the context-support test, verified against the
  actual `cycles.context` samples for both counter and gauge.

---

## Stage 2 runs (refm-C3 step 2.1–2.3; commit `9277c0d`; 2026-11-11 00:32–01:20 JST; Mac CPU)

Commands (study dir `reference-model-study/`):
`$PY scripts/run_c3.py --config config/refcompare_eval.yaml --stage verify|profile|leakage|real`.
git_head at run time `1252182`; `config_sha256` in the JSONs: refcompare
`69353882fa00…`, refcompare_run `b3dc5e43aa54…`, harness `c89a972b2fe0…`
(= the C2 manifest's frozen configs). `common_offset = 1118` in every output.

### Preflight (literal)

```
$ .venv/bin/python -c "...include_rare_count, len(entries)..."
True 11
$ ls artifacts/refcompare/*.npz | wc -l
118
$ .venv/bin/python -m pytest tests/test_refcompare_eval_config.py tests/test_refcompare_evaluate.py \
    tests/test_refcompare_sidebyside.py tests/test_refcompare_leakage.py tests/test_refcompare_flat.py -q
95 passed, 0 skipped   (13.4 s)
$ git log --oneline -5   (3b34c1a 005faaf … C2 manifest 0d30e5f present)
$ df -h /    461G total, 38G free
```

### 2.1 verify — 118 shards (wall 124.5 s)

```
verify: 118/118 shards ok (rtol 1e-06)
```
Cycle counts = plan for every unit (manifest `cycles == cycles_planned`,
0 errors; 215 cycles at ctx 11520, 42 at 5760, 8 at 240; real units their
own plan). No digest mismatch, no shard edit.

### 2.2 profile (wall 345.7 s; 9 main × {stl-on, stl-off, uni, multi} × seeds 1–3 + 18 sweep rows; 180 wall rows in `c3-profile.json:wall_seconds`)

Per-reference wall (45 rows each): stl-on mean 1.12 s, stl-off 1.20 s,
tfm-uni 2.61 s, tfm-multi 2.61 s (max ≤ 2.9 s; CPU pool unbounded by design
here — the chain itself is sequential per pod, no process pool is used; the
YAML `flat.workers: 4` bounds nothing in this stage, recorded as-is).
`first_valid_k_plus_1 = 1118` on every synthetic 2 d TimesFM record
(9×2 refs×3 seeds = 54 rows; sweep rows likewise all 1118).

Headline table (straight from `results/c3-profile.json`: occupancy means
over seeds 1–3; latencies in ticks per event, `n` seeds observed, `c`
censored; MAE per signal; availability = |scored ∧ V0|/|V0|; matched n):

| scenario | ref | av | stale | undec-band occ | decisive occ | leave-decisive-normal (ticks) | to-decisive-anomaly | MAE cpu/mem/rx/tx |
|---|---|---|---|---|---|---|---|---|
| S1 (n=382) | stl-gate-on | .554 | 127 | .035 | .416 | – (no event) | – | 1.33/10.31/0.133/0.134 |
| | stl-gate-off | 1.000 | 0 | .036 | .397 | – | – | 1.35/10.32/0.132/0.131 |
| | tfm-uni | 1.000 | 0 | .032 | .403 | – | – | 1.61/12.00/0.144/0.141 |
| | tfm-multi | 1.000 | 0 | .032 | .396 | – | – | 1.45/11.31/0.132/0.129 |
| S2 (346) | stl-gate-on | .466 | 0 | .019 | .008 | drift 28.3(3); step 3.0(3) | drift 58.3(3); step 4.0(3) | 1.33/10.12/0.132/0.135 |
| | stl-gate-off | 1.000 | 0 | .019 | .008 | drift 28.3(3); step 0.0(3) | drift 58.3(3); step 0.0(3) | 1.33/10.12/0.132/0.135 |
| | tfm-uni | 1.000 | 0 | .016 | .005 | drift 69.0(3); step 3.0(3) | drift 31.0(1)+2c; step 4.0(3) | 1.21/9.61/0.120/0.125 |
| | tfm-multi | 1.000 | 0 | .016 | .005 | drift 69.0(3); step 3.0(3) | drift 31.0(1)+2c; step 4.0(3) | 1.20/9.53/0.120/0.126 |
| S3 (431) | stl-gate-on | .698 | 150 | .043 | .407 | E1 43.0(3); E2 39.5(2)+1c | E1 132.3(3); E2 50.0(1)+2c | 1.31/9.93/0.129/0.128 |
| | stl-gate-off | 1.000 | 0 | .058 | .370 | E1 3.0(3); E2 39.5(2)+1c | E1 4.0(3); E2 50.0(1)+2c | 1.33/9.91/0.129/0.131 |
| | tfm-uni | 1.000 | 0 | .061 | .381 | E1 3.7(3); E2 25.7(3) | E1 4.7(3); E2 42.0(1)+2c | 1.46/11.16/0.142/0.139 |
| | tfm-multi | 1.000 | 0 | .058 | .373 | E1 3.0(3); E2 22.3(3) | E1 4.0(3); E2 44.7(3) | 1.37/11.25/0.133/0.131 |
| S4 (755) | stl-gate-on | 1.000 | 0 | .028 | .016 | E0 2.3(3); E1 4.7(3) | E0 3.3(3); E1 5.7(3) | 1.32/10.07/0.128/0.130 |
| | stl-gate-off | 1.000 | 0 | .028 | .016 | E0 2.3(3); E1 4.7(3) | E0 3.3(3); E1 5.7(3) | 1.32/10.07/0.128/0.130 |
| | tfm-uni | 1.000 | 0 | .015 | .014 | E0 3.7(3); E1 4.7(3) | E0 4.7(3); E1 5.7(3) | 1.22/9.67/0.120/0.121 |
| | tfm-multi | 1.000 | 0 | .013 | .009 | E0 4.0(3); E1 4.7(3) | E0 5.0(3); E1 5.7(3) | 1.21/9.53/0.120/0.121 |
| S5 (418) | stl-gate-on | .728 | 0 | .035 | .404 | – | – | 1.32/10.28/0.133/0.131 |
| | stl-gate-off | 1.000 | 0 | .038 | .351 | – | – | 1.33/10.28/0.133/0.131 |
| | tfm-uni | 1.000 | 0 | .034 | .351 | – | – | 1.43/9.64/0.158/0.140 |
| | tfm-multi | 1.000 | 0 | .031 | .349 | – | – | 1.34/9.77/0.136/0.132 |
| S6 (370) | stl-gate-on | .562 | 175 | .046 | .370 | drift 37.0(3); bump 57.0(3) | drift 37.7(3); bump – | 1.32/10.14/0.131/0.129 |
| | stl-gate-off | 1.000 | 0 | .052 | .321 | drift 17.0(3); bump 1.7(3) | drift 18.0(3); bump 2.7(3) | 1.35/10.19/0.130/0.131 |
| | tfm-uni | 1.000 | 0 | .045 | .320 | drift 16.3(3); bump 4.0(3) | drift 17.3(3); bump 5.0(3) | 1.49/11.32/0.143/0.140 |
| | tfm-multi | 1.000 | 0 | .042 | .313 | drift 17.0(3); bump 3.7(3) | drift 18.0(3); bump 4.7(3) | 1.39/11.33/0.132/0.129 |
| S7 (670) | stl-gate-on | .984 | 12 | .052 | .297 | bump 3.3(3) | bump 4.3(3) | 2.67/18.53/0.163/0.172 |
| | stl-gate-off | 1.000 | 0 | .052 | .303 | bump 3.3(3) | bump 4.3(3) | 2.63/18.05/0.165/0.172 |
| | tfm-uni | 1.000 | 0 | .052 | .307 | bump 4.0(3) | bump 5.0(3) | 2.22/15.83/0.165/0.163 |
| | tfm-multi | 1.000 | 0 | .053 | .302 | bump 4.3(3) | bump 5.3(3) | 2.13/15.79/0.153/0.155 |
| S8 (755) | stl-gate-on | 1.000 | 0 | .104 | .359 | bump 5.0(3) | bump 6.0(3) | 5.17/42.26/0.274/0.274 |
| | stl-gate-off | 1.000 | 0 | .104 | .359 | bump 5.0(3) | bump 6.0(3) | 5.17/42.26/0.274/0.274 |
| | tfm-uni | 1.000 | 0 | .108 | .368 | bump 6.3(3) | bump 7.3(3) | 2.86/19.83/0.211/0.208 |
| | tfm-multi | 1.000 | 0 | .106 | .360 | bump 6.3(3) | bump 7.3(3) | 2.66/20.20/0.172/0.174 |
| FLAT (755) | stl-gate-on | 1.000 | 0 | .027 | .010 | – | – | 1.33/10.28/0.132/0.131 |
| | stl-gate-off | 1.000 | 0 | .027 | .010 | – | – | 1.33/10.28/0.132/0.131 |
| | tfm-uni | 1.000 | 0 | .012 | .003 | – | – | 1.22/9.64/0.120/0.120 |
| | tfm-multi | 1.000 | 0 | .014 | .003 | – | – | 1.21/9.53/0.120/0.121 |

Mechanism counts of decisive ticks per seed-mean (from `mechanism_counts`):
S1 stl-on post-gate 167 + fresh 1.7 (gate-dominated); S1 stl-off fresh 300;
S1 tfm fresh 304/299. S2 injected 38/234/15/14 (tfm sees 1/3 the decisive
ticks of stl-off in the drift span). S3 fresh 13.7/271.7/280.3/274.3 +
injected 2.7/2/3. S4 injected 28.3/28.3/39.3/34.7 (tfm decisive INSIDE the
bursts is comparable; fresh-noise decisive OUTSIDE: 11.3/11.3/3/2.7 — tfm
much quieter in the quiet ticks). S5 post-gate 192 (stl-on) / fresh 21–265.
S6 injected 81/149/141/139 + post-gate 82 (stl-on only). S7 fresh
196/222/218/218 + injected 13/13/23/19. S8 fresh 260/260/265/261 +
injected 17/17/20/18. FLAT fresh 7.3/7.3/2/2.3 (all fresh-model noise — the
quiet-state floor). tfm rows: `post-gate` = 0 everywhere (no gate), as the
card expects.

Sweep rows (seed 1, single-seed, occupancy undec-band/decisive; stl-on =
stl-off where the gate is silent, so both stl rows quoted): S4 stl
(.038/.021 at all three contexts); S8 stl .109/.368 (1 h) vs .104/.359
(1 d, 2 d); tfm rows move with context: S4 tfm-uni worst at 1 h
(.032/.041) vs 2 d (.015/.014) and 1 d (.021/.016); tfm-multi improves
with context (S4: 1 h .017/.030 → 1 d .016/.011 → 2 d .013/.009); FLAT tfm-uni .038/.031 at 1 h
vs .012/.003 at 2 d; S8 tfm-uni .101/.367 (1 h), .117/.378 (1 d),
.108/.368 (2 d). No scenario where 1 h beats 2 d on decisive occupancy
for any tfm row; the 2 d context is the primary row, as the card names.

S3 pulse rows (per pulse × seed; latency to leave decisive-normal /
to decisive-anomaly; peak p_raw in [onset, onset+8)): E1 (pre-switch):
stl-on 41/126, 47/174, 41/97 (peak null — the [onset, onset+8) window is
UNSCORED: the pulse sits inside a gated stale-model stretch, so the peak
is no evidence and the 97–174-tick decisive latency is post-gate
carry-over, not the pulse); stl-off 3/4 all seeds (peak ≈.989);
tfm-uni 3/4, 3/4, 5/6 (peak .989/.988/.943); tfm-multi 3/4 all seeds
(peak .989/.988/.989). E2 (post-switch, ×3 noise; leave/decisive per seed): stl-on leave
censored/11/68, dec censored/50/censored; stl-off identical to stl-on;
tfm-uni leave 66/11/0, dec censored/42/censored; tfm-multi leave 65/2/0,
dec 66/3/65 (detected on all three seeds — the only ref with no censored
E2 decisive). E2 peak p_raw is the point-mass floor (~.002) for stl rows
and tfm-uni (the pulse is washed out by the ×3 noise for them) but rises
to .46–.94 for tfm-multi (s2/s3), so multi alone is decisively anomalous
in-window on the widened-noise pulse.

S5 (rx gaps): scored-tick fraction (availability) stl-on .728 vs stl-off /
tfm 1.000; rx MAE after gaps: stl .133/.133, tfm-uni .158, tfm-multi .136
— tfm-uni's self-interpolated NaN fill is the worst rx fidelity of the four
rows; tfm-multi ≈ stl.

S7/S8 advantage (MAE_tfm < MAE_stl on ≥3 of 4 signals): S7 tfm-multi/
stl-gate-off advantage = true (n_better 4/4; ratios .81/.87/.93/.91);
tfm-uni .84/.88/.99/.95 → true. S8 tfm-multi/stl-gate-off true
(ratios .52/.48/.63/.63); tfm-uni .55/.47/.77/.76 → true. Advantage
reported, not gated.

### 2.2b — ESS gate evidence (card D-6; `ess` block per scenario, floor 36 from `reference.yaml`)

Gated cycles (stl-gate-on, mean over seeds 1–3 / 216 cycles per metric):
S1 cpu 96 / mem 80 / rx 87 / tx 84 (≈45 % of cycles, matches part-1 E-A1b
stage 3: S1 seed-1 732/1872 scored, 47.7 % outside decisive-normal; part1
mean over 5 seeds cpu gated 97 — cross-check within ~1). S2 cpu 68 / mem 76
/ rx 0 / tx 0. S3 73/64/62/56. S4 0/0/0/0. S5 cpu 63 / tx 56 (rx in
cold-cycle case, mem 0). S6 93/81/65/59. S7 17/12/9/10. S8 0/0/0/0.
FLAT 0/0/0/0. stl-gate-off: 0 gated everywhere (floor 0, `reference.yaml`
untouched). Availability drop from the gate: S1 .554, S2 .466, S3 .698,
S5 .728, S6 .562, S7 .984 (all stl-gate-on; stl-gate-off and both tfm rows
= 1.000 on every scenario). `stale_ticks` (ticks ≥ first model tick with no
model on any continuous metric): S1 127, S3 150, S6 175, S7 12 (stl-on).
TimesFM `would_gate_fraction` (share of its informational per-tick ESS
values below the floor — would-have-gated, never enforced, C1 D-8; uni and
multi identical, the ESS is the detector-block property, not a model
property): S1 .461, S2 .532, S3 .341, S4 0.0, S5 .300, S6 .453, S7 .051,
S8 0.0, FLAT 0.0 — the same structure the gate measures on STL-lite
(S1/S6 heavy, S4/S8/FLAT clean), confirming the asymmetry is the GATE's
finding, not the data's.

### 2.2c — FLAT K=11 yardstick (synthetic, seeds 1–3 pooled, K=11, common offset 1118; `flat_control` block)

| ref | n | q50 | q99 | max | frac normal (<.2) | frac undecided | frac decisive (> .8) | n_decisive | frac <.02 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| stl-gate-on | 2265 | .00129 | .779 | .9895 | .9629 | .0274 | .0097 | 22 | .923 | **fails** |
| stl-gate-off | 2265 | .00129 | .779 | .9895 | .9629 | .0274 | .0097 | 22 | .923 | **fails** |
| tfm-uni | 2265 | .00129 | .413 | .9865 | .9854 | .0119 | .0026 | 6 | .968 | **calm** |
| tfm-multi | 2265 | .00129 | .498 | .9865 | .9832 | .0137 | .0031 | 7 | .962 | **calm** |

(The two STL rows are identical: 0 cycles gated on FLAT, so the floor-0
replace is a no-op.) Cross-check vs E-A1b stage 3 / `results/part1-profile.json`
FLAT (old offset 584, seeds 1–5): q50 .00129 (identical), frac normal
.959–.971 per seed (our pooled .963 at offset 1118 is in that band), max
.9883–.9895 (our .9895 = the seed-1/2 maxima), 55 decisive ticks summed
seeds 1–5 (per-seed 15/7/15/9/9, all fresh-model noise) vs our 22 at
seeds 1–3 — the D-B mechanism attribution (all fresh-model noise, 0 %
cycles gated) is unchanged. Part-1 verdict `calm: false 5/5` there (the
0.2-threshold "outside" reading); under D-A the yardstick reading is the
one above: STL-lite `fails` (3.7 % of valid ticks not decisively normal,
22 decisive), TimesFM `calm` (≥98 % decisively normal) on BOTH call
shapes. The real flat (2.3) confirms.

### 2.3 leakage — masking probe (wall 87.6 s; 16 pairs = 8 per base S4/S6, A ∈ {cpu, mem, rx_bytes}, B clean per card D-3; ctx 11520, multi, seed 1, offset 1118)

`max|dF_B|` / mean|dF_B| (σ-normalised per card D-3/RV-C F5), own effect
`max|dF_A|`, ratio `max|dF_B|/max|dF_A|`; `uni_input_identity = true` on
all 16 pairs (the uni B-context is byte-identical across variants — the
burst signal never reaches B's univariate input). n_cycles = 55 (S4: both
bursts ≤2 d old across the plan) / 23 (S6).

| pair | max\|dF_B\| | mean\|dF_B\| | own max\|dF_A\| | ratio |
|---|---|---|---|---|
| S4 cpu→mem | .140 | .025 | 8.25 | .017 |
| S4 cpu→rx | .087 | .019 | 8.25 | .011 |
| S4 cpu→tx | .099 | .014 | 8.25 | .012 |
| S4 mem→cpu | .099 | .018 | 12.37 | .008 |
| S4 mem→rx | .133 | .020 | 12.37 | .011 |
| S4 mem→tx | .101 | .015 | 12.37 | .008 |
| S4 rx→cpu | .329 | .031 | 3.59 | .092 |
| S4 rx→mem | .381 | .040 | 3.59 | .106 |
| S6 cpu→mem | .567 | .121 | 14.04 | .040 |
| S6 cpu→rx | .490 | .108 | 14.04 | .035 |
| S6 cpu→tx | .590 | .101 | 14.04 | .042 |
| S6 mem→cpu | .184 | .043 | 8.19 | .022 |
| S6 mem→rx | .180 | .032 | 8.19 | .022 |
| S6 mem→tx | .241 | .035 | 8.19 | .030 |
| S6 rx→cpu | .338 | .088 | 5.04 | .067 |
| S6 rx→mem | .345 | .089 | 5.04 | .069 |

All ratios ≤ .107: a burst on A shifts B's served forecast by ≤ .11 σ_B at
most (mean ≤ .121 σ) — cross-signal masking is real (S6 > S4, as expected:
S6's diurnal+drift couples the signals in the context) but ≤ 9 % of the
own-signal effect in every pair. B's strikes in the residual window
[onset, onset+576) (`B_strikes`, per tag, in the JSON): @A vs @none
differ by ≤ 1 on every pair (e.g. S4 cpu→mem 10 vs 11, S6 cpu→mem 8 vs 6)
— no burst-on-A strike cascade on B; B_residual mean/sd per tag also in
the JSON.

### 2.3 real flat — 10 pods × 4 references, K=11, same 6.0 d slice (wall 82.6 s; per-pod wall 0.9–3.1 s)

Every pod's own first scored tick-end offset (V0) = 1117 (all 10 pods;
TimesFM property, card D-1). Per-tick `p_raw` (rounded to 6 digits) +
`availability` + `mechanism` per pod/ref in `per_pod`; pooled n = 6120.

| ref | q50 | q99 | max | frac normal | frac undecided | frac decisive | n_decisive | frac <.02 | fleet verdict |
|---|---|---|---|---|---|---|---|---|---|
| stl-gate-on | .0013 | .0026 | .9859 | .9995 | .0002 | .0003 | 2 | .998 | **calm** |
| stl-gate-off | .0013 | .9895 | .9895 | .9596 | .0095 | .0309 | 189 | .951 | **fails** |
| tfm-uni | .0013 | .0032 | .9895 | .9954 | .0008 | .0038 | 23 | .994 | **calm** |
| tfm-multi | .0013 | .0032 | .9895 | .9954 | .0008 | .0038 | 23 | .994 | **calm** |

Per-pod verdicts: all four refs `calm` on 9/10 pods; on `vlsl8` stl-gate-off
`fails` (n_decisive 189, the pod's memory working-set series has a slow
drift the fixed boxcar trend chases → decisive quiet-tick runs, mechanism
all fresh-model noise 189), stl-gate-on `calm` there (the gate blocks those
fits → 2 post-gate decisive ticks), tfm-uni/multi `fails` (23 decisive
each, fresh-model noise). Decisive mechanism attribution (pooled, per
`per_pod` mechanism blocks): stl-on 2 post-gate / 0 fresh; stl-off 189
fresh / 0 post-gate; tfm-uni and tfm-multi 23 fresh / 0 post-gate each
(no gate ⇒ no post-gate, as expected). Fidelity MAE per continuous metric
(pooled): cpu stl .856 / tfm .821; mem stl-on 129 185 / stl-off 329 554 /
tfm-uni 111 372 / tfm-multi 110 681 (bytes; the gate-OFF STL trend chases
the drift hardest); rx stl 311.8 / tfm 300.4 (uni) / 301.6 (multi); tx
stl 201.7 / tfm 194.3 / 195.3.

### Gates (literal, post-commit)

```
$ .venv/bin/python -m pytest tests/test_refcompare_eval_config.py tests/test_refcompare_evaluate.py \
    tests/test_refcompare_sidebyside.py tests/test_refcompare_leakage.py tests/test_refcompare_flat.py -q
95 passed, 0 skipped   (12.4 s)
$ .venv/bin/ruff check scripts/run_c3.py src/refstudy/refcompare/
All checks passed!
$ git diff --check    # clean
```

Acceptance 2–3 invariants, checked programmatically against the three JSONs
(0 FAIL / 19 PASS): 9 main + 18 sweep blocks; seeds 1–3 main / seed 1
sweep on all 4 refs; `first_valid_k_plus_1 = 1118` on all 54 main tfm
records (and all sweep tfm records); every per_seed row: valid+quiet class
counts sum to n and sum(mechanism counts) = decisive ticks; every row has
`availability` and both occupancies carry `n`; every scenario block has an
`ess` and a `matched` block; `flat_control` = 4 refs + verdicts;
leakage 16 pairs, 0 error, 8 per base, `uni_input_identity` all true;
real 10 pods × 4 refs with per-pod D-A verdicts + availability +
mechanism + rounded p_raw.

Commit: `9277c0d` `data(refstudy): record Phase C accuracy profile,
masking probe and real flat control` (owned paths only: `scripts/run_c3.py`,
`src/refstudy/refcompare/evaluate.py`, `results/c3-{profile.json,
profile.csv,leakage.json,real-flat.json}`).

### Deviations / notes

1. **`_shard_unit` parser fix (owned `scripts/run_c3.py`)**: the S1b
   parser split shard names on every `_`, which breaks the 8 leak shard
   names whose signal carries an underscore (`leak_S4@rx_bytes_…` → 6
   parts). Fix: split off `kind`, then `base@signal` vs `base` at `@`,
   then the trailing seed/ctx/mode. `stage_verify` would have crashed on
   the first rx_bytes leak shard before verifying it; post-fix 118/118
   verify (the 8 leak shards included). No shard was edited.
2. **`tfm_pod` re-verify rtol (owned `evaluate.py`)**: S1b's `tfm_pod`
   re-verified its shard's context digests at hardcoded rtol 0.0 ("same
   machine"). The 118 shards were built on the CUDA host (C2,
   `input_policy causal-fit-end-v1`) and are scored on the Mac; a
   cross-machine context rebuild differs at ~1e-16 (first hit:
   `syn:S1:1:11520:uni` cycle 21 mem, sumsq rel diff 3e-16 — inside the
   card's `profile.digest_rtol: 1e-6`, which the `verify` stage already
   passed 118/118 at). `tfm_pod` now takes `digest_rtol` (default 0.0,
   the test/smoke path unchanged) and the full-run stages pass the YAML
   value. No gate loosened: the same 1e-6 the card's `verify` uses.
3. **`flat_control` computed from the FLAT rows' `EvalResult`s** (the
   library's `synthetic_flat_summary`), not re-scored; the cross-check
   numbers are read read-only from `results/part1-profile.json` (E-A1b
   stage 3 values, re-expressed by D-B) and quoted in 2.2c.
4. **Wall times are the shared-Mac wall** (load 4–10 concurrent agents at
   run time); no process pool is used by the stage bodies themselves
   (the per-pod chain is sequential; the YAML `flat.workers` is not a
   run_c3 knob). Per-row walls are in `wall_seconds` (profile: 180 rows;
   real: 40 rows + `stage_wall_seconds`).
5. **Surprising numbers, reported as measured (not tuned)**: (a) the
   synthetic FLAT yardstick is `fails` for STL-lite under D-A (3.7 % of
   valid ticks not decisively normal, 22 decisive) while TimesFM is
   `calm` on both call shapes — the K=11 dilution that made part-1's
   "FPR" look acceptable still leaves STL-lite outside the ≥98 %
   decisively-normal bar at the common offset; (b) real flat confirms:
   stl-gate-on `calm` fleet-wide (the gate removes the drift-chasing
   decisive runs; 2 post-gate decisive ticks) but stl-gate-off `fails`
   (189 decisive, vlsl8 memory drift) while both tfm rows are `calm`
   (23 decisive each, fresh-model noise, vlsl8 the only per-pod
   `fails`); (c) S3 E1 pre-switch pulse: stl-gate-on is NOT
   decisive-in-window on any seed (peak p_raw null; leave-normal 41–47
   ticks, decisive 97–174 ticks) — the gate's stale model hides the
   pulse in the decisive window; stl-gate-off and both tfm rows are
   decisive in 3–6 ticks; (d) S8: TimesFM halves the mem MAE
   (20.2 vs 42.3) and cpu MAE (2.7 vs 5.2) at the cost of ~1 tick
   latency; S7 same direction (mem 15.8 vs 18.1); (e) S5 rx: tfm-uni's
   self-interpolated gap fill is the worst rx MAE (.158 vs .133/.136);
   (f) S1: the gate dominates — stl-on availability .554 with 167
   post-gate decisive ticks/seed vs 300 fresh-model-noise decisive for
   stl-off; TimesFM's would-gate fraction (.461) mirrors the gate's
   structure but is never enforced.
6. **Note 2.4 (`markdown/part2-accuracy-profile.md`) is the later
   slice** (this assignment: runs + this evidence section only);
   cand-B rows = pending (stage 2b, only after the cand-B leaf).
7. `results/a1a-parity.json` shows as modified in `git status` — that is a
   pre-existing dirty file from an earlier session (not touched or staged
   by this run); the sibling C4 plots (`plots.py`,
   `test_refcompare_plots.py`) and cand-B (`src/refstudy/candb/`,
   `config/candb.yaml`, `test_candb_measure.py`) untracked paths were
   neither touched nor staged.

## Stage 2.4 — Part-2 accuracy profile note (C3 2.4; separate slice, this file not committed by it)
Note: `markdown/part2-accuracy-profile.md` (114 lines, ≤ 120 verified via `wc -l`; section order fixed: 0 setup + ESS-gate
asymmetry → 1 Q1 → 2 Q3 → 3 Q4 → 4 Q6 → 5 S3 → 6 S5/S7S8 → 7 surprising; D-A vocabulary grep clean for
"false-positive"/"FPR"/">0.2 = detection"). Committed in the lab as `ed0098d`
(`docs(refstudy): Phase C accuracy profile note (C3 2.4)`, 1 file = the note only, `git diff --check` clean).

Recomputed cross-check numbers (one-shot script, json stdlib only, over `results/c3-{profile.json,leakage.json,real-flat.json}`
commit `9277c0d`):
1. max over the 16 leakage pairs of `ratio` = max|dF_B|/max|dF_A| = **0.1062**, pair `S4:ctx=11520:A=rx_bytes:B=mem`
   (note's "≤ .107" bound; rounded 0.106).
2. synthetic FLAT stl-gate-on: `frac_normal` = **0.9629 = 2181/2265** decisively normal; `n_decisive` = 22.
3. real flat stl-gate-on fleet: `frac_normal` = **0.9995 = 6117/6120**; `n_decisive` = 2; verdict `calm`.
4. S3 E1 stl-gate-on decisive latencies seeds 1/2/3 = **[126, 174, 97]**; E2 stl-gate-on seed 1 leave/decisive =
   None/None (censored; stl-on == stl-off on E2).
5. tfm-multi E2 (decisive_latency, peak_p_raw) = **[(66, 0.0013), (3, 0.9416), (65, 0.5055)]**.

Deviations vs the Stage-2 narrative above (both are measured; reported, not tuned):
1. **Aggregation**: the note quotes SEED-MEAN availability/occupancies per the card ("mean over seeds 1–3");
   this file's Stage-2 headline table quotes seed-1 values (S1 .554, S3 .698, S5 .728, S6 .562, S7 .984 vs
   note .538/.658/.699/.546/.949). Both correct on their own basis.
2. **S5 tfm post-gate = 25.3/seed** on both tfm rows (JSON `post-gate` mechanism), contradicting this file's
   "tfm rows: post-gate = 0 everywhere" — kept and flagged in note §6/§7 (mechanism non-zero despite no gate);
   the exact cause is traced in the RV-Phase-E F10 section below (a no-model/gap artifact, not an ESS gate).
3. **S3 gate-stale mean = 176** ([150,168,210]) and **S7 stale mean = 8** ([12,0,12]) as per-seed lists in the note;
   S3 availability seed-mean .658 (seed-1 .698).
4. Full 16-pair leakage table reproduced in this file's Stage-2 §2.3; the note compresses it to 2 summary
   rows per base (all 16 ratios + per-pair strikes retained there).

## RV-Phase-E F10 — C3: deliver the omitted S4 joint-vs-single latency subitem + explain the S5 no-model "post-gate" label

Owner: `RefmEFixPE2` (Executor). Scope: F10-a + F10-b of `RV-Phase-E.md`.
All paths relative to `reference-model-study/` (lab repo
`pipelineml-model-exploratory-work`). No new inference, no shard
modification; the committed result numbers are unchanged (verified
additive-only below).

### F10-a — S4 joint-vs-single latency (the card's D-3/2.3 subitem, literally
`'S4 joint-vs-single latency to leave decisive-normal and to
decisive-anomaly'`)

**What was delivered.** A new `joint_vs_single` block in
`results/c3-leakage.json` (a top-level key, sibling of `pairs`), computed
from the SAME shards the C3 leakage stage already used: the 4 S4 multi
units at `ctx 11520`, `seed 1` — the single-signal-burst variants
`leak:S4@{cpu,mem,rx_bytes}` and the joint S4 burst `syn:S4:1:11520:multi`
— each scored through the COMMITTED pipeline (`refcompare.evaluate.tfm_pod`
+ the harness `evaluate_records` under the common V0 offset 1118; shard
digests re-verified at the card's `digest_rtol` 1e-6 exactly as the C3
verify stage does; no inference, no new model call).  Per burst event (the
two S4 bumps, onsets 1536/1752), the block reports the single-signal
variant's and the joint burst's pod-level `p_raw` latency to leave
decisive-normal and to decisive-anomaly, plus the peak `p_raw` in the
first 8 valid ticks after onset, and a `versus` delta (single − joint,
ticks, `None` when either side censored).

**Numbers (from the JSON, seed 1).**
- Joint S4 burst: E0 (onset 1536) leave-normal 4 / decisive 5,
  peak .9894; E1 (onset 1752) leave-normal 5 / decisive 6, peak .9868.
- `S4@cpu`: E0 leave 4 / decisive 5 (both Δ 0 vs joint), peak .9893;
  E1 leave 6 / decisive 7 (Δ +1/+1), peak .9411.
- `S4@mem`: E0 leave 4 / decisive 5 (Δ 0/0), peak .9893; E1 leave 6 /
  decisive 7 (Δ +1/+1), peak .9411.
- `S4@rx_bytes`: E0 leave 4 / decisive 5 (Δ 0/0), peak .9893; E1
  leave 5 / decisive 6 (Δ 0/0), peak .9868.
- Interpretation (reported as measured, not tuned): dropping the
  co-bumped signals from S4's burst costs ≤ 1 tick on pod `p_raw`
  (0–1 tick on both latencies, per event); the masked cross-signal shift
  measured by the D-3 probe (≤ .107 of the own effect) is far too small to
  move the joint's two latencies — the joint burst's detection latency is
  not driven by the co-bumped signals.

**Additive-only proof.** `git show HEAD:reference-model-study/results/
c3-leakage.json` (16 pairs, 7 top-level keys) vs the new file (16 pairs, 8
top-level keys): the new `joint_vs_single` key is the ONLY addition; all 16
`pairs` entries are byte-identical (deep-compared); `schema_version`,
`config_sha256`, `ctx_pts`, `common_offset`, `smoke` unchanged;
`git_head` moved `1252182` → `7bb2328` (the file's own regeneration
provenance stamp = the lab HEAD at re-run; it is not a result value and is
the only pre-existing key that differs).

### F10-b — S5: why TimesFM rows carry non-zero `post-gate` counts despite
no ESS gate (traced; documented; harness taxonomy UNCHANGED)

**The taxonomy (unchanged).** `harness/mechanism.py`: a decisive episode
is `post-gate` iff, within its onset lookback `[e0 − L, e0]` (L = 12 ticks),
there is a `no_model` tick, i.e. some listed metric's
`TickRecord.metrics[c].reason` is one of `{"model not built", "model
stale"}` (chain `reference/chain.py:432-433`: `reason = _STALE if
ever_model[name] else _NO_MODEL` — a no-model tick, not an ESS-gated
cycle).  This is a NO-MODEL/GAP classification, not an ESS-gate mechanism;
the rule is records-only and therefore also applies to TimesFM rows.
`harness/mechanism.py` was NOT changed.

**The trace (S5 seed 1, ctx 11520, multi, offset 1118, committed shards).**
S5's rx_bytes gap rule (30 min every 2 h) makes rx's 570-block
production window carry 30 % fewer observed blocks than the 3 complete
signals (cpu/mem/tx), so the TimesFM provider's usable-residual
`min_served = 522` gate (derived from `reference.yaml`, never retuned)
is reached LATER for rx: first finite forecast at tick k = 1289 vs
k = 1115 for cpu/mem/tx.  Inside V0 (`k + 1 >= 1118`), rx_bytes therefore
carries `reason = "model not built"` on the continuous stretch
`k ∈ [1117, 1288]` (172 ticks; the other 3 metrics are clean the whole
V0 range).  The D-B rule then labels every decisive episode whose onset
falls in the 12-tick lookback of a `k ∈ [1117, 1288]` no-model tick as
`post-gate`.

**Where the S5 tfm `post-gate` ticks actually sit (committed
`results/c3-profile.json` seed 1).** The mechanism `runs` (start, length,
name) of the S5 tfm rows: tfm-uni seed 1 `[[1117,23],[1142,1],[1144,1]]`,
tfm-multi seed 1 `[[1117,23],[1142,1],[1144,1],[1246,1]]` — every
`post-gate` run lies INSIDE the `k ∈ [1117, 1288]` no-model stretch, and
its onset is within the 12-tick lookback of that stretch (the dominant
run starts at k = 1117; the isolated 1-tick runs at 1142/1144/1246/1267
are single decisive ticks whose onset still falls in the lookback of the
same no-model stretch).  The counts (tfm-uni seed 1 = 25;
tfm-multi seed 1 = 26) match the committed per-seed `post-gate` count
(25.3/seed) exactly.  No S5 tfm `post-gate` tick lies outside the
`k ∈ [1117, 1288]` window.  **The `post-gate` label on S5 TimesFM is a
no-model/gap classification artifact** (rx's delayed cold-start), NOT an
ESS-gate mechanism — the harness rule's `no_model` trigger fires on the
gap's cold-start stretch, and the label is a faithful consequence of the
unchanged D-B taxonomy.

### Files owned by F10
- `src/refstudy/refcompare/leakage.py` (+`joint_vs_single`, `+` docstring
  note)
- `scripts/run_c3.py` (`stage_leakage` writes the new `joint_vs_single`
  block via `_jv_block`/`_jv_single`; the 16 `pairs` are unchanged)
- `tests/test_refcompare_leakage.py` (+4 tests:
  `test_joint_vs_single_latencies_and_peak`,
  `test_joint_vs_single_peak_none_when_window_invalid`,
  `test_joint_vs_single_rejects_mismatched_onsets`,
  `test_joint_vs_single_rejects_no_events`)
- `results/c3-leakage.json` (+`joint_vs_single` block, additive-only)
- `markdown/part2-accuracy-profile.md` (masking-paragraph
  joint-vs-single sentence; S5 label sentence replaced)
- `evidence/E-reference-model-study/E-C3.md` (this section)

### Gates (literal)
```
$ .venv/bin/python -m pytest tests/test_refcompare_leakage.py -q
14 passed in ~4 s        (10 pre-existing + 4 new, 0 skipped)

$ .venv/bin/ruff check src/refstudy/refcompare/leakage.py \
    scripts/run_c3.py tests/test_refcompare_leakage.py
All checks passed!

$ git diff --check
# (clean)

$ .venv/bin/python scripts/run_c3.py --stage leakage
leakage: 16 pairs, joint_vs_single ok -> results/c3-leakage.json
stage(s) leakage done in 99.8 s
```

### Commit
`data(refstudy): add S4 joint-vs-single latency to the masking probe and
explain the S5 no-model label (RV-Phase-E F10)` — explicit `git add` of the
owned lab paths only (5 lab files + this evidence file is in the
orchestration repo, not the lab commit).
