# Solo dashboard operations fixes — vision / input note

**Date:** 2026-11-06
**Author:** Observer (read-only author; this is design *intent* + verified findings,
not an implementation).
**Status:** VISION / INPUT for the R → P → E → RV pipeline. R resolves the open
questions (§7), P writes the packages, E implements, RV reviews. This file does not
replace the supervisor's standing rules.
**For:** the card-6 solo-mode detector (`pipelineml-anomaly-detector`, namespace
`rtx-4000-test`), deployed via `deploy/k8s/solo-card6/`, reachable at
`http://127.0.0.1:8080/dashboard/` (laptop port-forward).
**Also read first:** `agent-orchestration/AGENTS.md`;
`agent-orchestration/markdown/04-experimental-environment.md` (if present in this
project — otherwise the root Copilot instructions' experimental posture); and the
**evidence file** below.

## 0. The evidence file (requirement + root cause, already done)

`pipelineml-anomaly-detector/markdown/2026-11-06-solo-dashboard-operations-report.md`
— ten operator-observed dashboard defects, each investigated against the **live
API** and the **source**, with root cause, mechanism, and a named fix. It includes
the tester-side load confirmation (Section 8: `baseline_constant_small`, flat,
normal mode, no overlay), the **calibration test table** (per-tick `p` uniform,
χ² = 2.4; residual white; 4-in-a-row strike 0/288) that clears the p-sequence and
the load, isolating the defect to the calibration-mapper layer, and **Section 9**
(the scoring chain + the two probability norms — canonical content for the in-UI
math labels and the guide page).

**Do not re-derive what that file proves.** Its claims tagged [LIVE] were measured
on 2026-11-06 via the pod's HTTP API; claims tagged [SOURCE] cite file:line in the
current branch. R may re-verify, but may not re-litigate.

## 1. Goal (plain English)

Make the solo dashboard *usable for inspection* under the flat `baseline_constant_small`
load: no indicator flicker caused by a mis-sized freshness window; panels an
operator can actually read (marker on the curve, labeled axes, PDF + CDF, the
formulas themselves, and a Guide page explaining each panel and the two
probability norms); dead surfaces (Baseline View, Lineage) visibly disabled
instead of empty; a pod-level timeline that is populated and internally
consistent; and — the one scoring-side item — a **stable published probability**
under flat load (no ~2 h sawtooth 0.15→0.61, no indicator-A normal/warning
flapping).

## 2. Established facts (from the evidence file — binding context)

| # | Finding | Status |
|---|---|---|
| 1 | Indicator-B flicker: fresh window = 1.0 × 30 s poll cadence, but each pod's data arrives every ~60–190 s (rolling batch, `queue_depth: 10`) → structurally stale most of the time | root cause + 2 fix options named |
| 2 | Indicator-A flicker: per-tick `p` verified **uniform** (χ² = 2.4, P(p>0.95)=0.049, adjacent \|Δp\|>0.9 at 0.0035 vs 0.010 theory, 4-in-a-row 0/288); `r(t)` white (autocorr ≈ 0); load confirmed flat. The flicker is in `p_published` = isotonic mapper(`p_raw`), mapper fit once on 144 near-constant `p_raw` ∈ [0.0013, 0.0019] | isolated to calibration layer |
| 3 | CDF panel: latest-residual marker hard-coded at `y = 1.0` (measured: should be ~0.65 CPU / ~0.51 memory) — rendering defect; x-axis unlabeled (it is the residual in metric units); operator wants PDF (left) + CDF (right) split | mechanism + fix named |
| 4 | Raw-vs-Published seesaw: `p_posterior_raw` pinned at prior (0.0013–0.0019), `p_published` saws 0.1518→0.6094 — **same mechanism as #2** (mapper on degenerate sample) | same root as #2 |
| 5 | Baseline View: `/baseline` returns `applicable: false` in solo (no MLflow artifacts) — dead surface in solo mode | confirmed |
| 6 | Lineage: `run_id`/`model_version` null in solo — dead surface; System/Health: populated and operational — keep | confirmed |
| 7 | Maintenance: operative (event-history export/purge available) — keep; clarify target store | confirmed |
| 8 | "Probability and Decision Timeline" (pod-detail): fed by the in-memory per-scoring-tick `_point_history` (≤ 60 points ≈ 5 h), **not** the 288-tick `/solo` history; live: 0 points (`SCORE_SIGNAL_UNAVAILABLE`) → empty panel; "Points: N" + "No timeseries data available" is a display bug — the counter uses raw `points.length` while the chart filters points without a valid `t` | mechanism + fix named |
| 9 | No axis titles/units on any of the four solo charts (only the pod-level timeseries panel has them, `index.html:1337`); panel subtitles are prose, not math; the exact formulas are not rendered anywhere | confirmed [SOURCE] |
| 10 | No guide / "About this dashboard" surface in solo mode; the two probability norms (anomaly-norm `p_published` ≈ 0 vs surprise-norm `tilde_p` ≈ 1 in calm state) are not explained in-UI — the root of the operator's "why are these opposite" confusion | confirmed |
| — | Load: `baseline_constant_small` (200 mCPU / 128 MiB / 0 net / 0 HTTP, seed 42, forever), normal mode, programmatic OFF, confirmed live via tester `:8081 /api/v1/state` + catalog file + detector-observed series (8/10 pods, ~47 h, flat) | confirmed |
| — | Scoring chain + two norms: the evidence file's **Section 9** gives the per-tick formula table (`p = P(r_healthy ≥ |r|)` → strikes `n_k` → `tilde_p = P(Bin(4,0.05) ≥ n_k)` → Simes → Markov posterior `p_raw` → isotonic mapper → `p_published`) and the anomaly-norm / surprise-norm split. **This section is the canonical content source for P2 items (math labels, guide page).** | binding context |

## 3. Packages (three; do NOT fuse beyond this)

### P1 — Freshness window (config only, no code)

The "fresh" window for a solo pod must cover the **worst-case per-pod data-arrival
interval**, not the 30 s poll cadence. The evidence file names two options:
- **(A, preferred):** raise `dashboard.data_flow_health.degraded_age_multiplier` (and
  keep `stale_age_multiplier` > it) in the solo configmap so fresh ≈ 3–5 × 30 s.
  R picks the concrete value from the observed per-pod arrival distribution
  (the evidence file's 60–190 s sampling is the baseline; re-measure briefly if
  cheap).
- **(B):** reference the solo scoring tick interval (5 min) instead of the poll
  cadence in `_pod_freshness_from_snapshot` — code change, larger surface.

Acceptance: over a 3–5 min observation of `/api/dashboard/pods`, each pod reports
`fresh` ≥ 90 % of the time under the flat load; no red→green→red cycling in the
UI.

### P2 — UI batch (one image, one solo rollout)

All display-layer, all in `analyser/dashboard_assets/` (issue numbers = evidence file):
1. **CDF panel** (`soloRenderCdfChart`, Issue 3): latest-residual marker at
   `y = cdf(latest.residual)` (interpolated from the persisted points), NOT `y = 1.0`;
   add x-axis title ("residual (observed − expected), metric units"); add a **PDF
   sub-panel** (binned density of the same residuals) to the left of the CDF, same
   card. The PDF is what makes "are we in the tail" visually obvious; the CDF keeps
   the exact-value read.
2. **Solo-applicable surfaces** (Issues 5–7): gray out (disabled + tooltip "not
   applicable in solo mode") the **Baseline View** link and the **Lineage** tab when
   `mode == "solo"`; keep System/Health and Maintenance active; Maintenance status
   line should state it acts on the in-process event-history store.
3. **Axis labels + math on every solo chart** (Issue 9): add `xaxis.title` /
   `yaxis.title` (+ units) to the four solo charts (Observed/Reference: y = metric
   units; Per-Tick p/tilde_p: y = "probability [0,1]"; CDF: x = residual (metric
   units), y = "F(r)"; Pod-Level: y = "P(anomaly) [0,1]"). Under each panel's
   existing prose subtitle, add the **exact formula(s)** from evidence-file Section 9
   (e.g. Per-Tick: `p = P(r_healthy ≥ |r|)`, `tilde_p = P(Bin(4, 0.05) ≥ n_k)`); do
   not delete the prose. State the **two norms** where the quantities appear
   (anomaly-norm small = normal; surprise-norm large = quiet).
4. **Pod-level "Probability and Decision Timeline"** (Issue 8): in solo mode, drive
   this panel from the **288-tick `/solo` history** (same source as the "Pod-Level
   Probability" panel: `p_published` + decision vs the 0.2/0.8 thresholds) instead of
   the in-memory per-scoring-tick feed (`exporter._point_history`, ≤ 60 points,
   live-empty); and the "Points:" counter must count only points with a valid
   timestamp (post-filter), never the raw array length, so "Points: N" can never be
   shown alongside "No timeseries data available". If R judges the data-source swap
   too broad for P2, the minimal fallback is the counter fix + an honest
   "solo timeline not populated yet" state — but the data-source swap is the
   recommended target.
5. **Guide / "About this dashboard"** (Issue 10): a new solo-mode tab (or "ⓘ Guide"
   entry) whose content is split into **sub-pages navigable via a left vertical
   menu** (one page per panel + one "The scoring chain" overview page), so each
   panel's documentation is independently maintainable. Each panel page: what the
   panel shows, its formula(s) (Section 9), its norm (anomaly- vs surprise-norm),
   and a one-line "calm value looks like X". Content source: evidence-file Section 9.
   This is display-only static content (no new API surface).
6. **Raw-vs-Published panel** (Issue 4, display half): label the two curves
   explicitly ("raw Markov posterior" vs "calibrated / published") so the reader
   sees which layer moves.

No scoring, no API contract change, no request-set change.

Acceptance (real browser on the new image): select a non-default pod + metric;
≥ 3 automatic refreshes keep selection/scroll (regression of the 2026-10-17 fix);
the red cross lies **on** the CDF curve; every solo chart has x/y axis titles;
formulas visible under the subtitles; PDF panel renders; Baseline/Lineage visibly
disabled; "Probability and Decision Timeline" shows the 288-tick pod-level series
(or an honest empty state) with a consistent counter; the Guide tab renders its
menu + at least the scoring-chain page; refresh stays in-place (no full-page jump).

### P3 — Calibration-mapper refit loop + degeneracy guard (the only scoring-side
package)

**Defect (binding, from §2):** today the mapper is fit **once**, on the warm-up
window's `fit_half` (144 values, `driver.py:1669-1673`), and is then frozen
(`cal_state` is only ever advanced `warmup → scored`; nothing re-fits or demotes).
Under flat load that sample is near-constant (`p_raw` ∈ [0.0013, 0.0019] — the raw
posterior sits at the prior when there is no anomaly evidence), and the existing
gate (`_calibration_gate_passes`, `driver.py:1859`) never rejects such a degenerate
fit: it only checks held-out exceedance against `tau = c·π`. Result: an
ill-conditioned isotonic map (raw 0.0013→0.0019 → published 0.15→0.61) that is
frozen for the pod's life — the sawtooth (Issue 4) and indicator-A flicker
(Issue 2). This is load-independent: any anomaly-free window is degenerate,
anomaly-free windows are the norm, and the campaign's own warm-up window was
anomaly-free (the motivating live case: `b4xkt`, calibrated on the campaign
restore).

**Design (operator-approved 2026-11-06; R pins the mechanism, not the machine):**
the calibration state becomes a *healthy-mapper* state machine:

```
refit trigger (periodic, or on a non-degenerate window):
  window non-degenerate AND gate passes -> adopt, mark mapper healthy
  window degenerate                     -> keep current mapper (no adopt, no demote)

publish:
  healthy mapper present -> p_published = mapper(p_raw)   [calibrated]
  no healthy mapper yet  -> p_published = p_raw           [raw, transient]
```

Consequences (all follow from the machine; R verifies each against the code):
- **New pod / little history:** unchanged — the pod starts in the warm-up state
  and publishes raw until its first gate pass (existing behavior).
- **Degenerate first fit (b4xkt today):** the mapper is NOT adopted (the fit gate
  must add a degeneracy check on the fit sample — dynamic range / variance floor,
  YAML-configured — alongside the existing held-out gate). The pod publishes raw,
  which in an anomaly-free window is calm (≈ prior), i.e. **safe**; the raw state
  is transient and ends at the first non-degenerate window. This is where "keep a
  little of option (a)" lives: the degeneracy guard, not an identity fallback.
- **Steady state with a healthy mapper:** keep it through quiet (degenerate)
  windows; re-fit on a non-degenerate window (tracks the regime — the "option (b)"
  loop); **never** demote to raw, so there is no uncalibrated-onset risk when an
  anomaly arrives.
- **`probability_label`:** "raw" while no healthy mapper exists, "calibrated"
  once one does (existing labels; the transient state reuses the existing
  `calibrating`-style raw path, no new label).

Option (c) from the first draft (display-only raw) is **dropped** — under the
machine, publishing raw *is* the well-defined no-healthy-mapper state, so there is
no separate stopgap.

Hard limit on this package: it changes **how/when the mapper is fit and which
mapper is active**. It does NOT change α_strike, α_fuse, the strike window,
sojourn, prior, Simes/Markov/counter laws, ESS gates, or thresholds. No retuning
to make numbers look better. Note: this deliberately departs from the original
"ONE-TIME calibration" design (the `warmup_assumption` provenance comment,
`driver.py:1674`); R must reconcile the provenance record with repeated refits
(stated fact, not hidden behavior).

Acceptance (flat `baseline_constant_small` load, ≥ 24 h of new ticks on the new
image): `p_published` for all 10 pods stays **below `normal_threshold` (0.2)** for
≥ 95 % of ticks (i.e. indicator A is steadily "normal"); no ~2 h sawtooth; pods
with a degenerate fit sample publish `probability_label = "raw"` (not a
calibrated 0.15–0.61); the gate behavior on the *next real* anomaly campaign is
unchanged in semantics (a non-degenerate window with the held-out gate passing
still yields a calibrated mapper — verified by code path + scenario tests, not by
running a campaign).

## 4. Sequencing and rollout loop

1. **P1** — ConfigMap value (solo-card6 configmap). Apply + rollout restart; no
   image build.
2. **P2** — existing loop: commit on `feature/cnn2dlstm-bayesian-statistical-detector-v2`
   → GitHub `docker-build.yml` `no_cache=false` → digest-pin in
   `deploy/k8s/solo-card6/` → `kubectl set image` on the solo Deployment only
   (preserve PVC/config/service/fsGroup 999/API=false/resources; protected pair
   captured before/after) → verify via the owned 18086 preview route.
3. **P3** — its own R (open questions §7) → P → E (targeted consumer tests +
   one native cold/warm restart smoke in the established style) → RV → ordinary
   small D commit/push → same image/rollout loop → **flat-baseline observation
   window** for the P3 acceptance.

P1 and P2 may ship in one rollout if P1's value is settled by then (P1 is a
ConfigMap edit, P2 the image — one deployment update covers both). P3 must not
ride an image whose P2 proof is incomplete: sequence P2 → P3, not parallel.

## 5. Invariants (restate; from AGENTS.md + the campaign's standing posture)

- Experimental test environment; the only constraint is scope. "Did the user ask
  for it, or did I invent it?" — no invented hardening, no new security/ops
  surface, no new gates/counters/counting mechanisms.
- Protected `ml-components` detector + training-daemon pair untouched; tester
  pods, tester source, and the `baseline_constant_small` catalog untouched.
- No force-push, no new branch, no history rewrite; ordinary small commits on the
  existing feature branch.
- No threshold/statistical retuning anywhere in P1–P3 (P3 changes mapper fit
  *robustness* only, §3-P3 limit).
- No SARIMA work (deferred, user decision 2026-10-15). 24.5 h criterion (iii)
  stays NOT-RUN.
- Gate records ≤ 200 lines; one per terminal package attempt.

## 6. Out of scope (explicit)

- The per-tick `p` sequence, `tilde_p` math, strike window, Simes/Markov layers —
  **verified correct** on flat load (§2); do not "fix" the 0↔0.98 trace or the
  strike behavior.
- Load/baseline changes (tester catalog, targets, overlay) — confirmed adequate.
- The vlsl8 ~44 MiB memory offset: record in the misalignment register if desired;
  no fix authorized.
- Orchestration-repo commits (still wait for the user's "implementation end"
  signal, per the standing rule).

## 7. Open questions for R (P3 only — the machine is approved; these are
mechanism details)

1. **Refit trigger:** periodic (every `L_cal` ticks) or event-driven (on a
   non-degenerate window, or on the existing per-metric `drift_stale` soft flag)?
   Prefer the option that reuses existing cadences/flags and adds **no new
   timer**; state the cadence and its YAML key.
2. **Degeneracy statistic + floor:** which statistic on the fit sample
   (dynamic range of `p_raw`? distinct-value count? coefficient of variation?)
   and what default floor value — must be YAML, validated at load, not a magic
   constant in code. The guard sits **alongside** the existing held-out gate
   (both must pass to adopt); it must not replace or weaken it.
3. **State representation:** with `cal_state ∈ {calibrating/warmup, scored}`,
   how does the machine represent "scored but holds no healthy mapper" (publish
   raw)? Options: a sub-state/flag on the existing calibration row (preferred —
   no new state, no schema migration beyond one column) vs. a new state value.
   Confirm `probability_label` stays within the existing `raw`/`calibrated`
   values.
4. **Provenance reconciliation:** the current design records ONE
   `warmup_assumption` provenance per calibration pass (`driver.py:1674`). With
   repeated refits, what gets persisted (last-pass provenance? rolling record?
   fit count + last window span?) — keep it small; this is a record-only field.
5. **Cold-restore interaction:** `_solo_restore_current` / the WAL rebuild
   (`exporter.py:2540`) must restore the healthy-mapper state consistently with
   the live path (a pod that was publishing raw must not be restored as
   "calibrated"). Verify + cover with the existing restore tests.

## 8. What "done" looks like (whole pass)

All three packages terminal with their acceptance criteria met on the new image
under `baseline_constant_small`: indicators steady, CDF readable with the marker
on the curve, every solo chart axis-labeled with its formula, the Guide surface
rendering, a populated + internally-consistent pod-level timeline, dead surfaces
disabled, and a flat published probability with no sawtooth. The evidence file's
fix-table (Issues 1–10) is the checklist; nothing else is in scope.
