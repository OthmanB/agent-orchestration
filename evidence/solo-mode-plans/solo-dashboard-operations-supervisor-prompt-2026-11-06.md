# Solo dashboard operations fixes — Supervisor prompt (autonomous execution)

**Date:** 2026-11-06
**Status:** one-shot execution prompt for the Supervisor. **Re-read after every
context compaction.**
**Role of this file:** the execution loop + autonomy rules. It does NOT contain the
requirement — that is the vision document (packages, design, invariants, open
questions, acceptance criteria) and the evidence report (root cause + Section 9
content). It tells the Supervisor how to drive the fixes to done **fully
autonomously, without asking the user mid-run.**

---

## Read these files first, in this order

1. `agent-orchestration/AGENTS.md` — standing rules, parallel-execution +
   serialization policy, experimental-environment posture. **Re-read after any
   compaction.**
2. `agent-orchestration/markdown/04-experimental-environment.md` — how to act in
   this test environment (if present; otherwise the root Copilot instructions'
   experimental posture).
3. **The vision** — `agent-orchestration/evidence/solo-mode-plans/solo-dashboard-operations-vision-2026-11-06.md`
   — the three packages (P1/P2/P3), the operator-approved P3 machine, the
   established facts (§2), sequencing (§4), invariants (§5), out-of-scope (§6),
   open questions for R (§7), and acceptance criteria.
4. **The evidence report** — `pipelineml-anomaly-detector/markdown/2026-11-06-solo-dashboard-operations-report.md`
   — root cause + mechanism for Issues 1–10, the load confirmation (Section 8),
   the calibration test table, and **Section 9** (the scoring-chain formulas +
   two-norms explanation — the canonical text source for P2's in-UI math labels
   and guide page).
5. **THIS file** — the execution loop + autonomy rules + hard stops.

**Do not re-derive or re-litigate what (3) and (4) establish.** R may re-verify
mechanisms against current source, but the [LIVE]/[SOURCE] findings are binding
context (see Hard stops if re-verification contradicts one).

## Task

Drive **all three packages to terminal** in one Supervisor campaign, through the
normal **R → P → E → RV** sequence, in the vision's order:

- **P1** (freshness window, config-only) and **P2** (UI batch, 6 items) —
  sequence P2's R/P, and if P1's value is settled by then ship **P1 + P2 in one
  solo rollout** (P1 is a ConfigMap value, P2 the image).
- **P3** (calibration-mapper refit loop + degeneracy guard) — **its own
  R → P → E → RV** (open questions are vision §7, mechanism details only — the
  machine itself is operator-approved and not open), **strictly after** P2's
  proof is complete; P3 never rides an unproven P2 image.

Full autonomy: **do not pause to ask the user for mid-run confirmations.** The
operator already decided the scope; the only remaining choices are the §7
mechanism details, which R resolves and records.

## Autonomy rules

- **Decisions are baked in; R resolves §7, not the user.** R picks the refit
  trigger, the degeneracy statistic + YAML floor, the state representation, the
  provenance record shape, and the cold-restore handling — per §7's stated
  preferences (reuse existing cadences/flags, no new timer; no new state value
  if avoidable; labels stay `raw`/`calibrated`). Record each choice + rationale
  in the P3 gate record.
- **Scope test (apply before adding anything):** *did the user ask for it, or did
  I invent it?* No new security/operational surface (no auth/CSRF/CSP, no rate
  limiting, no mutation logging, no monitoring, no image tooling), no new
  product gates/counters/counting mechanisms. The guide page is static
  display content; the timeline fix is display + (at most) the solo branch of
  the existing route — the **external pod** `/timeseries` contract is
  unchanged.
- **The two documents are the record.** Do NOT modify the evidence report or the
  vision document during execution. Findings that update them (e.g. a
  re-measured arrival distribution) go in the gate records.
- **Hard stops (write a gate record with findings, then HALT and notify the
  user — do not proceed on a contradictory assumption):**
  1. R's re-verification contradicts an established fact (vision §2 / report).
  2. Any required change would touch the protected `ml-components` detector +
     training-daemon pair, the tester pods/source, the `baseline_constant_small`
     catalog, or any threshold/statistical law (α_strike, α_fuse, strike window,
     sojourn, prior, Simes/Markov/counter laws, ESS gates, operator
     thresholds 0.2/0.8).
  3. A conflict with `AGENTS.md` that cannot be resolved inside the vision's
     scope.
  4. The image build or rollout fails twice in a row (environment problem, not
     code).

## Execution loop (concretized from vision §4)

**P1** — set `dashboard.data_flow_health.degraded_age_multiplier` in the
`deploy/k8s/solo-card6/` configmap (R picks the value from the observed per-pod
arrival distribution; vision's 60–190 s sampling is the baseline). Apply +
rollout restart. No image build.

**P2** — workcard covering all six items (vision §3-P2), all in
`analyser/dashboard_assets/` (+ the solo branch of the timeseries route for
item 4, if R lands the data-source swap server-side). Then the established
loop, **once**:
1. commit on `feature/cnn2dlstm-bayesian-statistical-detector-v2` (ordinary
   small commits, no force-push, no new branch);
2. build via the **GitHub `docker-build.yml`** workflow (`no_cache=false`) —
   never ad-hoc/local docker;
3. on success, digest-pin in `deploy/k8s/solo-card6/`;
4. `kubectl set image` on the **solo Deployment only** (preserve
   PVC/config/service/fsGroup 999/API=false/resources; capture the protected
   pair's state before and after and record it — the pair must be untouched);
5. **RV live at `http://127.0.0.1:8080/dashboard/`** — the user's port-forward
   (use it read-only, never stop/renew it; or an equivalent supervisor-owned
   forward to the same pod, e.g. the 18086 preview route from vision §4) —
   the vision §3-P2 acceptance list is the acceptance (real browser: selection/scroll survives ≥ 3 auto-refreshes,
   marker on the CDF curve, axis titles + formulas on all four solo charts,
   PDF panel, Baseline/Lineage disabled, timeline populated + counter
   consistent, Guide menu + scoring-chain page, no full-page jump on refresh).

**P3** — its own R (resolve §7) → P (one workcard: the machine in vision §3-P3,
the degeneracy guard alongside — never replacing — the held-out gate, the
YAML floor, provenance + cold-restore handling) → E (edit `analyser/solo_mode/`
+ config; run the solo_mode consumer/scenario test suite; add the scenario
coverage: degenerate window → no adopt → raw publish; non-degenerate window →
adopt → calibrated; cold restore of a raw-publishing pod) + one native
cold/warm restart smoke in the established style → RV → same image/rollout
loop as P2 → **start the P3 observation window** (below).

## Verification that counts

- **P1:** over a 3–5 min observation of `/api/dashboard/pods`, each pod reports
  `fresh` ≥ 90 % of the time under the flat load; no red→green→red cycling in
  the UI.
- **P2:** the vision §3-P2 acceptance list, verified in a real browser on the
  new image. A source-only change with no redeploy does not count.
- **P3:** flat `baseline_constant_small` load, **≥ 24 h of new ticks on the new
  image**: `p_published` for all 10 pods stays below `normal_threshold` (0.2)
  for ≥ 95 % of ticks; no ~2 h sawtooth; pods whose fit sample was degenerate
  publish `probability_label = "raw"`; indicator A steadily "normal". The
  24 h window **may span sessions**: record the rollout timestamp + a first-
  hour sanity check (p_published pinned near prior, no sawtooth start) in the
  P3 gate record, and mark P3 **"deployed — observation window in progress"**
  if the window has not elapsed when the session ends. **NEVER declare P3
  complete without the full window measurement.** A later session resumes by
  re-reading THIS file and measuring against the recorded rollout timestamp.

## Gate records

- **≤ 200 lines**, one per terminal package attempt, in
  `agent-orchestration/evidence/solo-mode-gates/` following the existing naming
  convention. Record: R findings (P3: each §7 choice + rationale), the commit
  + image digest, protected-pair before/after, acceptance measurements (the
  actual numbers), and the P3 window-start timestamp.
- **Orchestration-repo commits still wait for the user's "implementation end"
  signal** (standing rule): gate records are written to disk; do not commit the
  orchestration tree unless the user gives that signal.

## Out of scope (explicit — do not start)

- The per-tick `p` / `tilde_p` math, strike window, Simes/Markov layers —
  verified correct on flat load; do not "fix" the 0↔0.98 trace or strike
  behavior.
- SARIMA (deferred, user decision 2026-10-15). The 24.5 h criterion (iii)
  stays NOT-RUN. No retuning anywhere (P3 changes mapper fit robustness only,
  vision §3-P3 hard limit).
- Load/baseline changes; the vlsl8 ~44 MiB offset; tester/protected-pair
  mutation; force-push / new branch / history rewrite.
