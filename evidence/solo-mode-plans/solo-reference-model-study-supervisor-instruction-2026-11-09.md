# Reference-model study — supervisor instruction (parts 1 + 2)

**Date:** 2026-11-09
**Status:** injected by the operator for the Supervisor to drive. One campaign, one
supervisor. The two vision documents are the spec; this file sets the supervision shape,
the repository, the sequencing/parallelism, and the invariants.

---

## Read first, in this order

1. `agent-orchestration/AGENTS.md` (standing rules).
2. `solo-mode-plans/solo-reference-model-scenario-campaign-2026-11-08.md` — **Part 1**
   (scenario campaign; the limitation profile and the yardstick).
3. `solo-mode-plans/solo-timesfm3-reference-study-2026-11-08.md` — **Part 2** (TimesFM-3
   candidate reference; the compute/scaling study and the final weighted judgment).
4. `solo-mode-plans/solo-dashboard-operations-supervisor-prompt-2026-11-06.md` — the
   R→P→E→RV campaign loop and the hard-stop conventions; those apply here unchanged.
5. THIS file.

## One supervisor, one yardstick

The whole study is driven by a **single** supervisor, not two. Part 2's acceptance is
defined against Part 1's limitation profile; a single authority keeps that yardstick and
the final judgment consistent. Parallelism is achieved by dispatching the dependency-free
slices concurrently under this one supervisor (see the plan below), not by splitting the
study across two supervisors — splitting is how the two yards would diverge.

## The lab repository

Create a new local repository **`pipelineml-model-exploratory-work`**, a sibling of the
existing `pipelineml-*` repos under the same parent directory. Local only; no remote, no
push, until the operator asks. It is a *general* exploratory research lab, reusable for
many experimental studies, not a product; the reference-model study is its first tenant
and lives in its own top-level directory (`reference-model-study/`), so later experiments
can coexist alongside it:

- `reference-model-study/` holds: the packaged data; the faithful reference + noise-law
  library (generalise the Part 1 `scenario-figures/generate.py` into a reusable module);
  the scenario generators (S1–S6 plus the Part 2 structural-limit scenarios); the shared
  evaluation harness (the four Part-1 quantities plus the quantile-band plotting);
  TimesFM-3 access; the compute/scaling/power study; the confined accuracy comparison;
  all figures and profiles; the written recommendation; and all throwaway.
- `.gitignore`: model weights, exported raw data, virtualenvs, and heavy generated
  artefacts (the repo tracks code, config, and small result summaries — not the model or
  the raw data dump).
- **The production detector repo is not touched.** Part 1's generators and the reference
  re-implementation live in the lab, *not* as edits to production tests. If any scenario
  later becomes a permanent production regression fixture, that is a separate, later,
  production pull request, explicitly out of this campaign.

This repository creation is the first gated action of the campaign: `git init`, the
`.gitignore`, one initial commit, and the directory layout. No remote.

## Campaign records

Gates and R/P/E/RV live under `agent-orchestration/evidence/E-reference-model-study/`
with gates `solo-mode-gates/SOLO-REFM-1.md` (Part 1) and `SOLO-REFM-2.md` (Part 2). The
two vision documents already sit in `solo-mode-plans/`.

## Plan and dependency rule

The phases below; the rule is that a phase may start only when its inputs exist, and the
independent phases run concurrently.

- **Phase A — run in parallel.**
  - **A1 (Part 1):** build the scenario matrix S1–S6 in the lab, run the faithful
    reference + noise law, produce the limitation profile (reference fidelity, detection
    latency, false-positive rate, settling time) on the six scenarios plus the flat
    control, and the figures. Generalise the existing `generate.py` into the lab's
    reference library so A2/B/C all reuse it.
  - **A2 (Part 2 research):** read the model card and inference API; confirm the context
    limits and the license; answer whether the interface accepts any form of input
    uncertainty or point series only; stand up the dependency target and pull the weights
    (subject to the license check). This is the long pole and depends on nothing in A1.
- **Phase B — compute, scaling, and power study (Part 2).** Needs the runnable model (A2)
  and the packaged data; does **not** need A1's accuracy results. It produces two related
  plots, both on CPU and GPU. The first is the scaling plot required by Part 2 §4: history
  ingested (raw fifteen-second points and days) against per-call cost in a
  machine-independent normalised unit, with the number of series in the call stated. The
  second confronts that cost with the *refresh-rate budget*: the production path must
  deliver a new anomaly diagnostic within a few minutes of the last data point arriving,
  for the whole list of pods scanned in one pass, so the relevant quantity is the *wall
  clock to refresh all pods*, not the per-pod cost alone. The study measures that
  end-to-end refresh time as the pod count grows from the current ten upward, records the
  power (or energy) draw at each point so the operator can confront power against the
  refresh bottleneck directly, and reports the point at which the refresh stops fitting the
  budget. It also records what asynchronism buys — overlapping pod scans, prefetching,
  batching — against the queue and backpressure that asynchronism introduces, so the
  trade is visible, not assumed. This is the study from which the "large number of pods"
  target is read: there is no fixed number, only the refresh-rate and power constraints
  above, and the target is whatever the plots show the hardware can sustain.
- **Phase C — confined accuracy comparison (Part 2).** Needs A1's yardstick **and** the
  model + data from A2/B. Runs TimesFM-3, in both univariate and multivariate mode,
  through the *existing, unchanged* downstream scoring chain, at the raw-cadence input
  and the shared five-minute hand-off, on the six Part-1 scenarios plus the Part-2
  structural-limit scenarios (multiple seasonality; sub-daily variability), across the
  context-length sweep, and produces the quantile-band plots on CPU, memory, and network
  rate.
- **Phase D — degradation/undersampling study (Part 2, conditional).** Entered only if B
  shows that, beyond roughly ten pods, the raw-cadence full-context forecast stops fitting
  the refresh-rate budget and power draw (the operator's "above 10 is good" threshold; the
  exact point comes from B's plots). Measures the fidelity and calibration traded per step
  of coarsening (box-car mean only, and box-car mean plus a within-box spread if the model
  accepts it). Read purely as a degradation curve, never as the basis of the adopt
  decision.
- **Phase E — final judgment (Part 2).** The weighted judgment over the evidence as a
  whole (detection quality, generalisation, uncertainty quality, feasibility) and the
  written recommendation: adopt, do not adopt, or adopt with a specified adaptation.

Dependency rule: **A1 ∥ A2**; **B ∥ A1** (B after A2); **C after A1 and B**; **D after B**
(conditional); **E after C**.

```
A1 (part-1 yardstick) ──┐
                        ├─ C (accuracy comparison) ─ D (conditional) ─ E (judgment)
A2 (model runnable) ─ B ┘   (needs A1 yardstick + A2/B model+data)
```

## Invariants and hard stops

- **Read-only to the deployed system and to the production detector.** No threshold,
  strike, fusion, calibration, sojourn, or prior is changed; no retune of any kind. The
  only writes are the lab repository and the orchestration evidence records.
- **The flat control is re-asserted unchanged at the end**, as evidence the study
  introduced no drift into the promoted behaviour.
- **No production commit or push.** Orchestration-repo commits await the operator's
  "implementation end" signal, as in the SOLO-OPS campaign.
- **Part 2 is a weighted judgment, not hard categorical gates.** The single hard floor is
  feasibility: a reference that cannot run at the refit cadence on the available hardware
  ends the candidacy on its own; it is a feasibility fact, not a quality judgment. No
  other quantity or margin fails the candidate by itself.
- **The candidate is fed the raw-cadence series; the comparison lands on the shared
  five-minute block at the hand-off** (the box-car is a property of the moving-average
  model, not of the data — Part 2 §3).
- **TimesFM-3 license is confirmed before its weights are committed anywhere.**
- **Environment and data.** The target is the `rtx-4000-test` cluster (ssh host
  `rtx-4000-test`, kind cluster `kind-rtx-4000-cluster`), namespace `ml-components`, the
  ten tester pods. The deployed solo detector and its dashboard are reached through the
  supervisor's forward at `127.0.0.1:18086`. **The cluster is a data source, not an
  experiment bed** — nothing is deployed or mutated there, and no experiment runs against
  the running pods.
  - Part 1's real burst is drawn from the P3 tick store; the synthetic scenarios are
    seeded; both live in the lab.
  - Part 2's packaged data must be at the **raw fifteen-second cadence**. The dashboard
    forward exposes only the scored five-minute ticks, not the fifteen-second samples, so
    the raw series must be pulled from the raw source (Greptime), using the same
    counter→increment and gauge semantics the detector uses, and packaged out to the lab.
    The supervisor must confirm the raw-cadence export path at the Phase A gate before the
    confined study starts; if the raw source is not reachable read-only, that is a
    blocker to raise, not something to paper over with the five-minute ticks.

## Deliverables

- **Part 1:** the limitation profile, with the measured numbers and the figures, in the
  lab repo; a gate record `SOLO-REFM-1.md`.
- **Part 2:** the scaling and power profiles — the two plots of Phase B (per-call cost
  against ingested history, and all-pods refresh time plus power draw against pod count,
  confronting the refresh-rate budget and the cost of asynchronism); the quantile-band
  plots; the side-by-side accuracy profile against the present reference on every scenario
  and context length in both modes; the hardware and scaling decision; and the written
  recommendation with the pros and cons weighed against the four dimensions of Part 2 §6.
  A gate record `SOLO-REFM-2.md`.

## Resolved parameters

- **Repository:** `pipelineml-model-exploratory-work`, a general exploratory research lab
  reusable for many studies; the reference-model study is its first tenant under
  `reference-model-study/`.
- **Pod-count target:** open, by design. There is no fixed number; the constraint is the
  refresh-rate budget (a new anomaly diagnostic within a few minutes of the last data
  point, for the whole pod list scanned in one pass) and the power draw. "Above roughly
  ten pods" is the operator's threshold for when the conditional Phase D is worth
  entering; the exact point at which the refresh budget or power draw is exceeded comes
  from Phase B's plots.
- **Supervision:** one supervisor, confirmed.
