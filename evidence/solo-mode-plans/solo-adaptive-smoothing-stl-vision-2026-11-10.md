# Solo-mode reference candidate B: adaptive-width boxcar trend + STL-lite

Date / time: 2026-11-10. Author: operator observer, on operator instruction.
Status: **vision for a small production change to `pipelineml-anomaly-detector` (solo mode),
to be measured as candidate B in the SOLO-REFM accuracy comparison.**

## 1. Problem (measured, not hypothesized)

The current solo reference is STL-lite: a fixed 2-day window, trend = window
mean (a boxcar of $D_t = 2\,\text{d}$), seasonal = 48 phase-bin means on the
residual, noise law on the one-step residuals (Part-1 study, decision log:
limitation L-ESS, SNR sweep).

Measured limitation, diurnal regime: for a metric whose signal is a strong
clean 24-h cycle (the common case for production pods), the fit window holds
~2 cycles of 570 five-minute block means. Consecutive blocks are nearly
identical, so the Bartlett effective-sample-size of the **block averages**
collapses to ~42, right at the floor of 36. The sample-sufficiency guard
(`scan.py`, `ess < min_effective_samples` ⇒ skip cycle) therefore fires on
~40 % of refits, leaving up to ~6 h of un-scored stretches and long-stale
models. Consequence in the study's diurnal scenario (S1): the undecidable band
occupancy (0.2 < `p_raw` ≤ 0.8, three-class semantics) is ~47 % on a clean,
anomaly-free workload, vs ~0.8 % on real flat production data.

Root cause: the trend term is a fixed 2-day boxcar. It cannot separate the
slow-moving daily cycle's *drift/level* from the *cycle itself*, so the whole
structure stays in the data the guard inspects, and the guard — which measures
independence as if the block series were white noise — is maximally over-
conservative on the most structured signal the model is best at.

## 2. Proposal

Replace the fixed full-window boxcar trend (the current global mean) with an
**adaptive-width boxcar** — a trailing equal-weight mean whose width (span) is
selected per metric at each refit by an iid likelihood — then run the existing
STL-lite seasonal + noise law on the detrended residual. **This is a boxcar,
not an exponential/Kalman filter**: equal weights, hard trailing window, finite
memory. That choice is deliberate and load-bearing (see §2.1): the boxcar mean
is the maximum-likelihood / BLUE estimator of a constant level *under an
iid-Gaussian noise assumption*, so it is the smoothing whose validity is
exactly the iid guarantee this change is meant to preserve. An exponential /
local-level filter would instead assume a random-walk state — a non-iid model
on the level — and would not follow from the iid premise.

The two techniques are complementary, not adversaries:

- the adaptive boxcar (span $\in [8\,\text{h},\, 12\,\text{h}]$, sub-period)
  absorbs slow level drift / the slow envelope;
- STL's 48-bin seasonal absorbs the 24-h cycle itself;
- the noise law absorbs the white remainder.

**Target (stated to avoid mis-scope):** this is a *precision* improvement —
less residual level-lag bias on slow level drift (scenario S2, the drift the
operator asked about). It is **not** expected to move the S1 diurnal numbers,
where the dominant effect is the sample-sufficiency (ESS) guard firing and
serving a stale model; that is a separate, operator-owned guard-tuning
question. Candidate B is therefore judged on drift regimes (§6), not on S1.

**Sequencing constraint (binding):** fit the smoothing **first**, on the raw
window; run STL on the **detrended residual**. No joint parameter estimation
of $(\tau,\ \text{seasonal})$ — the operator's degeneracy concern: in regions
of the parameter space where a long-smoothing span and the seasonal term both
try to absorb the cycle, joint likelihood is multimodal. Sequential
estimation removes that degeneracy by construction; the cost (a slightly
sub-optimal $\tau$ given the later seasonal) is acceptable and is itself a
measured quantity (see §6).

### 2.1 Width selection: iid likelihood on the detrended residual

Discretize the fit window into $K$ 5-minute block means $y_1,\dots,y_K$ (the
same blocks the guard already consumes — the guard input is unchanged, it
still runs on the raw blocks). For each candidate boxcar width $W$:

1. **Detrend**: $d_t = \bar y_{[t-W+1,\,t]}$, the trailing equal-weight mean
   of the last $W$ blocks (hard window; the first $W-1$ blocks have a
   shrinking window, exactly as the current global mean does at cold start).
2. **Seasonal (per the binding sequencing constraint)**: fit the 48-bin
   phase means on the detrended residual $r_t = y_t - d_t$, centered on the
   residual mean — the existing STL-lite seasonal, applied one step later in
   the pipeline.
3. **Score iid-ness** of the final residual
   $z_t = r_t - S(j_t) + \bar r$ (noise on the level+seasonal-removed
   series) under the iid-Gaussian model, by reusing the existing Bartlett-ESS
   machinery: $\mathrm{ESS}(z)$ normalizes by $K$ to $[0,1]$, and is $1$
   exactly when the samples are uncorrelated white noise. Objective:

   $$\hat W = \arg\max_{W \in \mathcal{W}}\ \mathrm{ESS}(z(W))\ / K$$

   (equivalently the iid-Gaussian log-likelihood on the standardized
   residual; the ESS form reuses in-repo code and needs no new distribution
   assumptions).

Candidate set $\mathcal{W}$ and the span cap:

- **Span range: $W \in [30\,\text{min},\, 12\,\text{h}]$, sub-period.** The
  upper bound is the boxcar's constraint, not an arbitrary choice: a moving
  average has a sinc frequency response, and at $W \approx$ the 24-h period
   it *nulls* the daily cycle — aliasing the season into the trend and making
   trend and seasonal degenerate (the very adversariality this design avoids).
   The full-window constant (today's behaviour) is **added as a sentinel
   candidate**, so "adaptive" can never be worse than "current".
- **method = grid** (default): a log-spaced list, N ∈ [24, 48] entries inside
  the span range plus the sentinel; deterministic, O(N·K) — cheap enough for
  the 6-tick refit cadence;
- **method = gradient** (alternative, same objective): coordinate/grid
  refinement around the grid argmax if $N$ is made small; the operator's
  fallback rule applies — if it is flaky in tests, grid is the sanctioned
  method.
- **degenerate fallback**: $K < 48$ blocks, or a constant window (variance
  below `gauge_epsilon`) ⇒ the sentinel (full-window constant) is used. This
  preserves today's behaviour exactly on the cases where it is already
  correct.

Why this keeps the iid property the operator requires: the *only* model
assumed is that the final residual $z$ should be iid-Gaussian; the width is
the single scalar chosen so that it most nearly is. No state-space, no
random walk, no memory beyond the boxcar window.

### 2.2 What stays unchanged

- The fit window $D_t$ stays **fixed at 2 days**: the *seasonal* term needs
  two full cycles of phase data; $D_t$ is not the adaptive quantity. What
  adapts is the **trend time constant inside** that window.
- The no-leakage invariant: a forecast at $t_1$ is built only from
  $[t_1 - D_t,\ t_1 - dt]$; the adaptive fit uses the same window, same
  blocks, no extra data.
- Seasonal 48-bin structure, noise law, strike ring, Simes, Markov chain,
  mapper: all unchanged. Only the trend term changes, from "global window
  mean" to "trailing equal-weight mean of width $\hat W$" (same estimator
  family, adaptive width) plus the detrended seasonal.
- The ESS guard: **kept as-is** (it is a protected threshold). With the
  adaptive trend, the block means it inspects are unchanged (it runs on the
  raw blocks, not the detrended ones) — so its behaviour is unchanged and the
  candidate's advantage must come from the *stale-model* effect shrinking,
  not from the guard. The study must report the guard fraction for candidate B
  separately; if it is unexpectedly lower, that is a finding, not a pass.

## 3. Scope of the modification (expected small)

| File | Change |
|---|---|
| `analyser/solo_mode/trend_adaptive.py` | **new module.** Pure functions: `span_candidates(cfg) -> list[float]` (log-spaced widths + the full-window sentinel), `boxcar_trend(blocks, width_blocks) -> np.ndarray` (trailing equal-weight mean; O(K) via cumsum), `select_width(blocks, cfg) -> (W_hat, diagnostics)` (runs the detrend → 48-bin seasonal → normalized-ESS loop of §2.1 and returns the argmax width). No I/O, no clock, numpy only. |
| `analyser/solo_mode/baseline.py` | `stl_lite_fit` gains an optional `trend: str` argument (`"boxcar"` default = current behaviour bit-for-bit; `"adaptive"` = new module). Adaptive path: detrend first (width $\hat W$), seasonal bins on the detrended residual, trend = last value of the trailing mean. |
| `analyser/solo_mode/scan.py` | `build_one` passes the configured trend choice; records `trend_width_s` in the persisted metric-model snapshot (additive column). |
| `analyser/solo_mode/config.py` | schema + early validation for the new `solo_mode.reference.trend` block. |
| `config/detector-common.yaml` (solo block) | new block (below). |

### 3.1 Configuration (YAML-first, no runtime defaults)

```yaml
solo_mode:
  reference:
    trend:
      method: boxcar          # boxcar (current, default) | adaptive
      span:                   # used only when method=adaptive
        method: grid          # grid | gradient (refinement around the grid argmax)
        candidates: [30m, 1h, 1h30m, 2h, 3h, 4h, 6h, 8h, 12h]  # log-spaced, sub-period
        # the full-window constant is always appended as a sentinel candidate
        fallback: boxcar      # degenerate window -> full-window constant (= today)
```

Validation: `method=adaptive` requires `span.candidates` non-empty, sorted
strictly increasing, each candidate ≥ 30 min and ≤ `seasonal.period/2`
(sub-period: a boxcar near the period nulls the daily cycle, §2.1);
`method=boxcar` requires the `span` block absent (no dead parameters). All
durations via the existing duration parser. The deployed default is
`boxcar`: activating candidate B in a pod/deployment is a config flip, not a
code change.

### 3.2 Persistence / observability

- Per-metric model snapshot gains `trend_width_s` (null for `boxcar`) and
  `trend_method` — additive, no migration.
- Scored-tick history (the 288-tick ring) gains no new fields; the per-tick
  `p_raw` is what the retention change (§5) records.

## 4. What this is NOT

- Not an exponential / Kalman filter: it is an **adaptive-width boxcar**
  (equal-weight trailing mean), chosen so the boxcar's iid premise holds.
- Not a replacement for the guard tuning question: the guard stays, and the
  candidate's value is precision on drift (fresh, less-lagged trend), not
  guard coverage.
- Not a joint estimator, not a statsmodels-STL port, no new dependencies.
- Not a threshold change: 0.2 / 0.8 are untouched; this candidate is
  expected to *shift `p_raw` values on drift scenarios*, which is exactly
  what the accuracy comparison measures.

## 5. Related operator directive (retention + durability, separate from this file)

The study exposed that derived per-tick quantities (`p_raw`, ESS value,
gate-fired, stale-model age) exist only in the restart-volatile ring, and that
raw points in `solo_window_points` (SQLite) currently have **no lifetime** —
correct today, wrong at scale across many pods. Operator directive:

(a) **Configurable TTL on raw points** (YAML, required, no hidden default):
    delete rows with `ts_epoch < now - retention`. Default retention:
    **1 week** — ~3× headroom over the worst lookback the reference needs
    (`Dt` = 2 d + max adaptive boxcar ≤ 12 h + scoring tail), small per pod,
    and batched on a low-frequency sweep off the hot path. The SQLite file
    is then a ~1-week *working set*, not an archive.
(b) **Scored-tick persistence**: append scored ticks to a second SQLite
    table (`solo_scored_ticks`: pod, metric, tick, `p_raw`, ess, gate-fired,
    stale hours, provenance) with the same TTL mechanism, depth ≥ 2 × ring.
(c) **Prometheus exposure**: the same per-tick quantities as scrape-able
    gauges (`solo_p_raw`, `solo_ess_value`, `solo_ess_gated`,
    `solo_model_stale_hours`, labels pod/metric) on a dedicated metrics
    route. With (a)+(c) the durable archive lives in the existing
    Prometheus/Greptime backend that the detector already talks to; no new
    database inside the detector.

All YAML-first: TTL, enable flags and route path in `solo_mode.persistence.*`
/ `solo_mode.observability.*`; missing keys fail fast. This is production
code in `pipelineml-anomaly-detector` — its own workcard, independent of the
candidate-B workcard.

## 6. Evaluation (in the SOLO-REFM accuracy comparison)

Candidate B is the second arm of the accuracy phase, alongside candidate A
(current reference, fixed full-window boxcar) and candidate C (TimesFM-3):

- Same scenarios S1–S8 + FLAT, same chain, same three-class yardstick;
- **Headline numbers (per the target in §2):** on the drift/level-shift
  scenarios (S2 and its variants): trend-lag bias / MAE / RMSE of the
  reference, A vs B; detection onset and undecidable-band occupancy on S2;
  guard fraction A vs B (expected ~equal, §2.2);
- On S1 (diurnal): B must not be worse than A on any three-class quantity
  (the two are expected to be close there; A regression is a finding);
- **Sequencing cost check (one offline study, not production code):** width
  selected on the raw window (sequential, as production does) vs a
  counterfactual width co-fitted with the seasonal (joint), to quantify the
  cost of the no-joint-estimation constraint;
- Flat control: B must stay in the flat band on FLAT (calibration check
  under the operator's three-class directive).

Decision rule: B is recommended for adoption only if it strictly improves
drift-regime reference fidelity (bias/MAE on S2) without regressing any
scenario's detection or the FLAT calibration. Otherwise the guard-tuning
option (operator-owned, out of study scope) remains the lever for the
diurnal regime, and the drift question stays open for a later iteration.
