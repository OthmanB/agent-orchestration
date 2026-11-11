# R-candB — research for candidate B (adaptive-width boxcar trend + STL-lite)

**Role:** researcher (campaign SOLO-REFM, directive D-E). **Date:** 2026-11-10.
**Inputs:** vision `evidence/solo-mode-plans/solo-adaptive-smoothing-stl-vision-2026-11-10.md`;
production `pipelineml-anomaly-detector` @ `5bcc7f9` (READ-ONLY); lab
`pipelineml-model-exploratory-work` @ `9955703` (`reference-model-study/`, `.venv` py3.12).
**Method:** every production/lab fact below is a source read at the cited line; every number is
OBSERVED by a throwaway probe under `/tmp/candb_probe` run with the lab venv on
`refstudy.scenarios.registry.get_scenario({S1,S2,FLAT}, seed=1)` blocks built by the A1a block law
(scratch deleted after use; no lab/production file was modified).

Labels: **SOURCE** = file:line read; **OBSERVED** = measured this session; **INFERENCE** = reasoning.

## 1. Production facts, and what each means for a trailing boxcar of width W

### 1.1 `stl_lite_fit` / `stl_lite_forecast` — the forecast is the phase mean, and T cancels

**SOURCE `baseline.py:69-113`** (`stl_lite_fit`): two O(N) passes; `trend = raw_sum / n`
(`baseline.py:96`); `seasonal_by_phase = {b: s / seasonal_counts[b] - trend}` (`baseline.py:103`),
i.e. S(j) = mean of the window's blocks in bin j **minus the trend**.
**SOURCE `baseline.py:115-127`** (`stl_lite_forecast`): `M_k(t1) = fit["trend"] + S(phase(t1))`;
missing bin → trend only (`baseline.py:127`).

⇒ Algebraically `M_k(t1) = mean of the window's blocks in bin j(t1)` — **the trend cancels out of the
served forecast**. Two consequences that decide the whole design:
1. Replacing the trend by a trailing mean of width W **cannot change anything** unless the seasonal is
   re-estimated on the detrended residual (the vision's §2.1 "sequencing constraint"). The load-bearing
   change is the *centring convention*, not the width. (SOURCE + algebra.)
2. The current residual record is `y_t − prefix phase mean` (the trend also cancels there,
   §1.4), so the current reference **already implements** "one-step forecast from blocks strictly older
   than the block" — the sentinel of candidate B is the present code, not an approximation of it.

### 1.2 `StlLiteRunningState` — an order-free sum; a trailing mean is not expressible on it

**SOURCE `noise.py:466-528`**: `_raw_sum`, `_n`, `_bin_sums`, `_bin_counts`; `update(ts,value)` adds one
block (`noise.py:487`), `forget(ts,value)` subtracts it (`noise.py:495`), `forecast(t1)` = trend + centred
bin mean (`noise.py:508`). O(1), **no notion of order** — the state is a *window sum*.

⇒ A trailing mean of adaptive width W is an **order-dependent** statistic (which W blocks are "last"
depends on the sequence). It cannot be folded into a running sum: it needs the ordered ring of block
values (or an index into the window array that `scan._tick_aligned_blocks` already materialises in
`build_one`). The lab R-state must therefore gain a ring buffer / window index — this is the one real
structural addition, and it is why the adaptive path cannot reuse `StlLiteState` unchanged.

### 1.3 `bartlett_ess` — the clamp makes the vision's objective identically 1

**SOURCE `noise.py:229-262`** (lab port `noise_law.py:78`): `ESS = N / (1 + 2·Σ_{j≤L} ρ_j)`, denominator
clamped `>= 1`, result clamped `[1,N]`, `L = bartlett_max_lag = 144` (`config/reference.yaml`,
`noise.py:243`).

⇒ Any residual produced by detrending with a trailing mean has `Σρ_j ≈ −1` (the operator
`1 − mean_W` has zero DC gain), so the denominator floors at 1 and **`ESS = N` for every W**.
"ESS = 1 exactly when white" is false: it is also 1 whenever the residual is anti-correlated.
This is measured in §4.2 and it is the decisive defect of the §2.1 objective.

### 1.4 `scan.build_one` — the 570-entry record is a *causal prefix* record

**SOURCE `scan.py:1098-1236`**: F and R are two running states over the same 570-block window
(`scan.py:1189-1210`: `forget` the blocks that slid out, `update` from the new ones); the record is the
retained residuals of earlier blocks **plus** the R-state forecast of each *entered* block, computed
**before** that block is folded in (`scan.py:1212-1218`), appended and cropped (`scan.py:1236`).
**SOURCE (A1a fact 2):** cold = 522 entries, +6/cycle, 570 steady; *"each residual is forecast by the
sliding R state AT ENTRY ⇒ record ≠ obs − served forecast"*.

⇒ For a trend of adaptive width the record must obey the same rule: block t's residual is forecast with
t's **predecessor** level (`d(t−1)`, exclusive) and the seasonal known then; the served forecast uses
`d(fit_end)` (**inclusive** of the last fitted block — legal, fit_end is the last known block). Both come
from one state with an explicit inclusive/exclusive switch, and the width in force is the one selected at
the last refit (retained verbatim, as production retains residuals).

## 2. The lab port: where the switch goes, and how `boxcar` stays bit-for-bit

Files (lab): `reference/stl_lite.py` (`StlLiteState` 46-117, `advance_residuals` 119,
`rolling_one_step_residuals` 143, `StlLiteProvider._cycle` 253 with the ESS gate at 282-283,
`run` 340), `reference/provider.py` (`ReferenceRun` 22, `ReferenceProvider` 62,
`check_no_leakage` 68), `reference/noise_law.py` (`bartlett_ess` 78), `reference/config.py`,
`config/reference.yaml` (`baseline.continuous` block, every value provenance-commented).
⚠ The ticket cites `markdown/reference-port.md`: **that file does not exist** in the lab repo
(`markdown/` holds only `part1-limitation-profile.md`); the port contract is the A1a card
§Library contract + the module docstrings (`stl_lite.py:1-10` cites `prod:noise.py:456-541`).

The switch (default = today, bit-for-bit):

```yaml
baseline:
  continuous:
    method: stl_lite
    trend:
      method: boxcar            # boxcar (default, current behaviour) | adaptive
      adaptive:
        grid_min_minutes: 30    # vision §2.1 lower bound
        grid_max_minutes: 720   # <= period_seconds/2 (no cycle nulling, §2.1 rationale)
        n_grid: 32              # log-spaced, deduped; + the sentinel (full window)
        criterion: cv1          # cv1 (causal one-step MAE, recommended) | ess (vision §2.1)
        min_lag_blocks: 48      # = noise.min_fit_blocks; residual warm-up (§3.1 warning)
```

`boxcar` must take the untouched code path (`stl_lite_fit` semantics byte-for-byte, float op order
preserved — A1a D-4): measured P2/P2b = 0.0 stays 0.0 **because no line of the current path changes**.
`adaptive` must produce the identical `ReferenceRun` shape: one forecast per served tick from data older
than `fit_end` (`check_no_leakage` unchanged) and a residual record of *earlier* blocks (§1.4 rule).

## 3. The design question the vision leaves open — and the closure

### 3.1 Definition of the adaptive record and of the served forecast (recommended)

Per block t, with W the width selected at the last refit and `r` accumulated only from
`t >= min_fit_blocks` (48):

```
d_t      = mean(y[t-W : t])                     # exclusive: blocks strictly older than t (record)
r_t      = y_t - d_t
S_t(j)   = mean{ r_s : s < t, bin(s) = j } - mean{ r_s : s < t }
F_t      = d_t + S_t(j(t))                      # one-step forecast used for the record
resid_t  = y_t - F_t
served   = d_last + S_last(j)   ,  d_last = mean(y[fit_end-W+1 : fit_end+1])   # inclusive
```

**Reduction to today's definition:** W = sentinel (whole window ⇒ `d_t =` prefix mean) gives
`S_t(j) = ` prefix phase mean − prefix mean, hence `F_t =` prefix phase mean =
`M_k(t1)` of `baseline.py:127` / `noise.py:508`. So the sentinel *is* the current reference
(algebraically exact; **bit-exact only if special-cased**, because production accumulates with
`forget()` and a prefix `mean_W` is not bit-identical to `_raw_sum/_n`). The card must therefore say:
`sentinel ⇒ call the legacy path`; the general formula applies only for W < K.

⚠ **Measured trap (the head):** `d_0` has no history. With `d_0 = 0` the first residual is ~5·10²
(S2/mem) and it poisons one phase bin for a whole cycle: OBSERVED `off = +252.8` for bin 40 at i=284,
which inflated the S2 predictive MAE from 9.4 to 11.7 until I dropped t < 48. The vision's "first W−1
blocks have a shrinking window" must be replaced by "no residual is accumulated before `min_fit_blocks`"
(production's own warm-up, `noise.yaml min_fit_blocks: 48`).

### 3.2 §2.1 consistency audit (vision text vs code/measurement)

| Item | Verdict |
|---|---|
| `z_t = r_t − S(j_t) + rbar`, S mean-centred | **consistent** (mean(z) = 0) |
| `d_t = mean[y_{t−W+1..t}]` (inclusive) | **CONTRADICTION** with no-leakage (`baseline.py:59-67`): the block enters its own trend; residual shrunk by `(1−1/W)`, served forecast peeks. Measured artefact §4.2/§4.3 |
| "first W−1 blocks shrinking window, exactly as the current global mean" | **CONTRADICTION**: production starts at `min_fit_blocks = 48`, and a shrinking head is measurably destructive (§3.1) |
| `K < 48` ⇒ sentinel | consistent with `min_fit_blocks = 48`; never fires in the steady state (K = 570; cold = 522 — A1a fact 2) |
| constant window (`gauge_epsilon`) ⇒ sentinel | **CONTRADICTION/needs a key**: `gauge_epsilon` exists nowhere in production or the lab YAML (only a `1e-9` block-index epsilon, `scan.py:527`, and `bartlett_ess`'s zero-variance branch). A constant window already yields ESS = N ⇒ the selector is undefined there |
| span range | **CONTRADICTION (§2:47)**: `[8 h, 12 h]` vs `[30 min, 12 h]` (§2.1:95). Load-bearing (§4.3) |
| §2.2 "guard unchanged ⇒ the advantage must come from the stale-model effect shrinking" | **CONTRADICTION**: with the guard unchanged, staleness is unchanged; nothing in B shrinks it |

## 4. Throwaway numeric probe (lab code, /tmp, deleted)

Windows: real 570-block fit windows (`SPAN = (48 h − 5 min)/5 min = 570`) on S1/cpu (diurnal),
S2/mem (drift+step), FLAT/cpu, seed 1, 6 windows spread 40 min apart; candidates
`W ∈ {6,12,18,24,36,48,72,96,144}` blocks (30 min … 12 h) + sentinel (full window).

### 4.1 The §2.1 objective is degenerate — it cannot select a width

**OBSERVED, exclusive (leak-free) detrending:** `ESS(z)/K = 0.998` for **every** candidate in 12 of 18
windows (the clamp of §1.3), and `argmax = 6` (tie-break order) in **18/18**. No discrimination.
**OBSERVED, inclusive detrending (as written in §2.1 item 1):** `obj: 6:1.000 12:1.000 18:1.000
24:1.000 36:0.514 48:0.176 72:0.051 96:0.027 144:0.013` — monotone decreasing in W, `argmax = 6` in
**18/18**; the shortest width always wins because a short trailing mean is a high-pass filter.
**OBSERVED, in-sample Gaussian log-likelihood** (the vision's "equivalently"): `argmax = 6` in **24/24**
windows (S1/S2/FLAT × 8), e.g. S1 `ll: 6:-114.5 12:-142.7 … 144:-611.7`, because `−K/2·log σ̂²` is
dominated by the `(1−1/W)²` self-fit shrinkage — the "equivalence" is false and its direction is the
inclusive-window artefact.
⇒ **CONTRADICTION (critical):** the objective of §2.1 has no interior optimum on either reading; it
returns the grid's lower bound. The claim "the full-window constant is added as a sentinel, so adaptive
can never be worse than current" is vacuous: the sentinel is never selected (18/18), so the guarantee
never binds.

### 4.2 An honest criterion disagrees with the objective, and the "best width" is scenario-dependent

**OBSERVED, causal one-step predictive MAE** (forecast for block i uses blocks `< i` only; common
sample i ≥ 48; warm-up corrected, §3.1):

| window | best | MAE at best | sentinel (current) | shape |
|---|---|---|---|---|
| S1/cpu (diurnal) | 12–18 blocks (1–1.5 h) in 4/6, 6 in 2/6 | **1.42–1.51** | 1.65–1.74 | interior, rises to 2.8–3.5 at 12 h |
| S2/mem (no drift in window) | sentinel | 10.1–10.5 | **9.3–9.9** | monotone: 0.5 h worst (11.1–11.6) |
| FLAT/cpu | sentinel | 1.25–1.31 | **1.16–1.23** | monotone |

⇒ Adaptive helps the diurnal (~13 % better than current) and **regresses** flat/white metrics by 5–10 %.
That is the opposite of the vision's §2 target ("precision gain on S2 drift, S1 not expected to move").
And S1's optimum (1–1.5 h) lies **outside** the §2 bullet range `[8 h, 12 h]` — under that range B would
have produced no S1 gain at all. The width is scenario/metric-dependent ⇒ a per-metric selector is
mandatory, and neither candidate criterion is the one the vision proposes.

### 4.3 Drift: the mechanism is real, the payoff is mostly unreachable

**OBSERVED, S2/mem, 140 built cycles, trend-level bias at `fit_end` vs the clean truth:**
- windows that actually span the drift (level moved > 5, n = 11): current window mean **17.4** (p90 25.6,
  max 27.4); adaptive W = 12 (1 h) **3.6**; W = 30 min 4.2; W = 2 h 4.8; W = 6 h 10.3 ⇒ 4–5× better.
- the other 129 windows: current **0.22**; W = 12 **3.05**; W = 30 min 4.5 ⇒ 14× worse.
So the drift benefit is real but confined to the few windows that contain the drift.
**OBSERVED, and this is the blocker:** the ESS guard fires exactly on those windows — S2 raw-block ESS
during the drift **3.9–7** (window p50 = 493; 76/216 cycles gated = 35 %). Served-model age
(lab provider): FLAT max **1.08 h** (no gating; this is the cadence floor), S1 p90 **5.0 h**, max 7.1 h,
3 % of served ticks older than 6 h, S2 p90 **28.3 h**, max **39.1 h**, **31 % of served ticks older than
6 h**. On the drift scenario the reference serves a model 1–1.6 days old; B's trend cannot be applied at
all there. ⇒ **CONTRADICTION with §2's target** and with §2.2: B does not touch the guard, so B cannot
deliver on the drift where the guard is the binding constraint. (The vision's "~6 h" of un-scored
stretches matches S1 exactly — OBSERVED max blackout 12 consecutive skips = 6 h — and is exceeded 6× on
S2, which the vision did not measure.)

### 4.4 ESS reconciliation: vision "~42", Part-1 "22–35", floor 36

**OBSERVED, S1/cpu raw-block ESS over all 216 cycles:** min 18.7; p5/p25/**p50**/p75/p95 =
20.6/26.5/**41.8**/164.0/570.0; fraction `< 36` = **44 %**; built 122/216 (56 %), `ess_gate` 94/216.
⇒ The vision's "~42" is the **median** (41.8 ✔). Part-1's "22–35" is the **lower quartile**. The floor 36
sits inside the interquartile range, so the firing rate is a coin flip, not a data property.
**OBSERVED attribution:** on the same 24-h sine, windows return either 20.2 or 570 (clamp) depending only
on the window's phase against the 288-block period (570 blocks ≈ 1.98 cycles); sawtooth-only gives
13.7–66.6; noise-free clean 19.2–23.5. ⇒ S1's 44 % gating is an **estimator/phase artefact** of the
Bartlett sum on a near-periodic window; a trend width cannot change it (the guard reads the raw blocks —
verified in the port at `stl_lite.py:282-283`).

### 4.5 Cost

**OBSERVED** (Mac, numpy, 570 blocks, incl. 48-bin seasonal and ESS with L = 144): **1.08 ms/refit** for
N = 9 candidates, **4.70 ms/refit** for N = 43 (the vision's N ∈ [24,48]). Negligible against the 30-min
cadence. Note the complexity is O(N·K·L), not the claimed O(N·K).

### 4.6 Reality check on the vision's §1 numbers

OBSERVED: 44 % of S1 refits are gated (vision "~40 %" ✔); max blackout 6 h on S1 (vision "~6 h" ✔);
but the drift regime — the one B targets — is gated 35 % of cycles with 28–39 h stale models (§4.3).

## 5. Risks and contradictions

**CONTRADICTION-1 (critical, blocking).** §2.1's objective `argmax_W ESS(z(W))/K` is monotone (inclusive
reading) or flat at the clamp (exclusive reading): it returns the smallest candidate in 18/18 windows and
therefore encodes no information about the data (§4.1). Implementing it as written would ship a selector
that sets W = 30 min on every metric.
**CONTRADICTION-2 (critical).** §2.1 item 1 (inclusive trend) violates the no-leakage invariant that
production enforces (`baseline.py:59-67`) and that the lab enforces (`provider.check_no_leakage:68`).
Under the inclusive reading the measured gain of the adaptive recipe was ~20 % on every scenario —
exactly the `(1−1/W)` self-inclusion factor (§4.2).
**CONTRADICTION-3.** Span range stated twice: `[8 h,12 h]` (§2:47) vs `[30 min,12 h]` (§2.1:95).
**CONTRADICTION-4.** §2.2's staleness argument is self-refuting (§2.2, §4.3).
**CONTRADICTION-5.** "ESS normalises to [0,1] and is 1 exactly when white" (§2.1 item 3) is false given
the clamp in `noise.py:229-262` (§1.3). "Equivalently the iid-Gaussian log-likelihood" is false: the
likelihood includes σ̂², which the self-fit shrinks with 1/W (§4.1).
**CONTRADICTION-6.** "so adaptive can never be worse than current" is true only of the objective (a
trivial property of an argmax set), not of accuracy: on FLAT and S2-flat the selected width is 5–10 %
worse than the sentinel on the honest criterion (§4.2).
**CONTRADICTION-7 (target).** The stated target (drift precision, §2) is unreachable because the guard
gates the drift windows and the served model is 28–39 h stale there (§4.3). What B measurably improves is
the *diurnal* one-step error (1.42–1.51 vs 1.65–1.74) — precisely what §2 says it should not move.
**CONTRADICTION-8 (config).** `gauge_epsilon` does not exist in production or in the lab YAML (§3.2).
**CONTRADICTION-9 (docs).** The ticket's `markdown/reference-port.md` does not exist (§2).

**Risks for the planner:**
- R1 The selector must be redefined before any card is written; the default (`method: boxcar`) makes the
  whole question moot for parity, so the card can be sliced without touching production at all.
- R2 A per-metric width reintroduces a tunable (N, grid bounds, criterion) — three new YAML keys with no
  production counterpart; they must be provenance-commented as *study-only*, not ported values.
- R3 A width chosen at the refit is frozen for the 6 entered blocks; production retains residuals verbatim,
  so the record becomes a mixture of models (already true in production for the trend). Determinism holds
  only if the width selection is a pure function of the window (it is).
- R4 If the operator later tunes the guard (the actual S1/S2 lever), the diagnostic changes: the ESS is a
  phase artefact (§4.4) and any guard tuning should be validated on the same 6 scenarios.
- R5 Any lab change to `StlLiteState` risks P2/P2b: the ring buffer must be additive (a new class), never a
  rewrite of `update/forget` float order.

## 6. Recommended lab interface and the tests that prove it

```
reference/trend.py                     (new; no production counterpart)
  boxcar_trailing(values, width, *, inclusive) -> np.ndarray      # causal mean, NaN before min_lag
  class TrendState:                                                # O(1) ring + running sums
      from_config(cfg) -> TrendState
      def update(self, ts: float, value: float) -> None
      def forget(self, ts: float, value: float) -> None
      def level(self, *, inclusive: bool) -> float                  # trailing mean of W blocks
      def set_width(self, width: int) -> None
  select_width(values, bins, candidates, *, min_lag, criterion) -> tuple[int, dict[int, float]]
      # criterion="cv1": causal one-step MAE (recommended, §4.2) | "ess": vision §2.1 (degenerate, §4.1)
reference/stl_lite.py                  (extend, default path untouched)
  class AdaptiveStlState:               # TrendState + 48 centred bins on r = y - d
      from_config(cfg) ; update/forget/forecast(t1)/snapshot()
  StlLiteProvider(cfg).run(...)         # per cycle: if trend.method == "adaptive":
                                        #   width = select_width(window blocks, ...) -> set_width
                                        #   residual record via AdaptiveStlState (exclusive, t >= 48)
                                        #   served forecast via level(inclusive=True) + S(j)
reference/config.py                    (add Trend/AdaptiveTrend dataclasses, `require`-loaded)
provider.py                            (UNCHANGED: ReferenceRun shape + check_no_leakage already right)
```

Tests (deterministic, seeded, behaviour-asserting; docs only under `markdown/`):
1. `test_boxcar_default_is_bit_exact` — `method: boxcar` vs the pre-change provider on all 6 scenarios,
   seed 1: every `ReferenceRun` array equal with diff **0.0**, identical cycle reasons (P2/P2b = 0.0).
2. `test_sentinel_equals_current` — `adaptive` with `candidates=[full]` on S1/S2/FLAT: forecasts exactly equal to the boxcar run (a 1-ulp difference means the sentinel must be routed to the legacy function; this test enforces that).
3. `test_no_leakage_adaptive` — `check_no_leakage(run, ticks, cfg)` passes with W < full.
4. `test_record_is_causal` — for every entered block, an independent recomputation from blocks `< t` reproduces its residual exactly (§1.4 rule).
5. `test_warmup_head_not_poisoned` — y[0:48] replaced by a 0-offset series: no residual before 48 and no phase-bin offset above a few units (guards the measured +252.8 failure, §3.1).
6. `test_selector_has_interior_optimum` — on synthetic AR(1)+drift the `cv1` selector returns a width strictly inside the grid, while the `ess` selector is asserted *degenerate* (encodes CONTRADICTION-1; fails on the vision-as-written criterion).
7. `test_constant_window_sentinel` — constant window ⇒ sentinel, no NaN, no ZeroDivisionError.
8. `test_gate_unchanged` — identical gated-cycle set under both methods (the guard reads raw blocks) — the property §5/CONTRADICTION-4 says the vision cannot deliver on.
9. `test_determinism` — two runs bit-identical.

**Hand-off (planner RefmPDB):** cheapest decisive order — (a) `trend.py` + config keys, default `method: boxcar`, test 1; (b) `select_width` with `criterion: cv1`, tests 6-7; (c) `AdaptiveStlState`, tests 2-5; (d) the S1/S2/FLAT measurement arm (Supervisor runs it, D17). Never default the `ess` criterion: measured degenerate (§4.1).


