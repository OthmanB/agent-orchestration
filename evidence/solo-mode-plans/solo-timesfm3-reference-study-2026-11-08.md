# A candidate replacement reference: evaluating TimesFM-3 for the solo reference model (SOLO-OPS reference study, part 2)

**Date:** 2026-11-08
**Status:** vision document, injected by the operator for the Supervisor to drive.
**Scope:** a confined research and experimentation study. It ingests packaged data and runs
TimesFM-3 beside the present reference in a local harness. It is explicitly **not** an
end-to-end pipeline change and it makes no production mutation.
**Relation:** this is part 2 of the two-part reference-model study. Part 1
(`solo-reference-model-scenario-campaign-2026-11-08.md`) produces the scenario limitation
profile and the shared measuring stick. This part's acceptance is defined against that
profile, so it is sequenced after part 1.

---

## 1. The gap in the present reference that motivates a replacement

The present reference is a parametric model of a fixed, simple form: a two-day moving mean
plus a daily seasonal term of forty-eight centred phase-bin means. Its strength is that it
is honest, cheap, and exact on the signals it was shaped for — it tracks a stable mean and a
clean daily cycle with negligible one-step error, and it is provably calm on a flat signal,
which is the behaviour the P3 window confirmed across the whole fleet. Its limitation is
the same fixed form. It cannot represent a slow multi-day trend, it cannot represent a
regime that is not the mean-plus-daily-cycle of the last two days, and, because it is
univariate in its shape, it cannot use the joint structure between the CPU, memory, and
network signals of one pod. The adaptive layer is the empirical noise law, but that law only
re-learns the *tolerance*; it cannot re-shape the reference itself. So the system has no
mechanism to adapt the *reference* to a workload whose structure is outside the
mean-plus-daily-cycle family, and the slow-scoring and self-masking behaviour that part 1
measures is, in part, the price of that fixed shape.

The SARIMA option was the earlier candidate for a richer univariate reference and was
deferred, for a reason that is still the right reason: making it a *per-pod selected*
reference turns the problem into a statistical model-order-selection problem, and the design
deliberately did not adopt that. What a different kind of model offers is to replace the
"fit a reference per pod from its own recent history" step with a *pretrained, zero-shot,
multivariate* forecaster that has already seen a corpus far larger than any single pod's two
days, and to draw on the other metrics of the pod as structure. That is the proposal this
part tests, and it is tested as a hypothesis, not adopted on trust.

## 2. What TimesFM-3 is, and what claims must be verified rather than assumed

TimesFM-3 is reported, in the Google Research announcement of August 2026, as a
three-hundred-and-thirty-million-parameter decoder-only transformer that is natively
pretrained for multivariate forecasting. The claims that matter for this problem, and that
each need to be checked against our data rather than accepted, are these. It is *zero-shot*:
it makes a forecast from the provided context with no task-specific training, which is what
would let it be a drop-in reference without a per-pod fitting step. It is *natively
multivariate*: in one call it can forecast several related target series and can take, as
input, past covariates known only historically and past-future covariates whose values are
known ahead. It normalises each series internally, so the differing scales of CPU, memory,
and network rates are handled. It is built on patches of thirty-two time steps and decodes
the whole horizon in a single non-autoregressive pass, which is relevant to latency. And it
emits, for each target at each horizon step, a set of nine quantiles from the tenth to the
ninthieth percentile, which is a full probabilistic forecast rather than a point estimate.

Two of these are the load-bearing ones for us. The first is that it is a *probabilistic,
non-parametric* forecaster. This answers the operator's question about non-Gaussian errors
in the strongest available way: there is no Gaussian, or any other, likelihood assumed in
its output. It gives a predictive distribution; whether that distribution is *calibrated* on
our data is a separate, testable question, weighed as one of the dimensions in §6. The
second is the
multivariate capability, which is exactly the "put the continuous variables in" use the
operator described: CPU, memory, and network of a pod as jointly-modeled series. The
announcement is a primary source and its benchmark claims are on public retail, finance, and
observability series; our signals are Kubernetes counter rates, which are a different
population, so no benchmark number here transfers by assumption. The model card, the exact
inference API, the context limits, the license, and the hardware notes are read in phase A,
because the study is not sound until those are known and none of them are asserted here.

## 3. How it would sit in the architecture, and why that fit is important

The scoring chain of the solo detector is, by construction, *reference-agnostic*. It takes a
reference forecast, forms the residual of the observed block against it, scores that
residual's surprise against the empirical noise law, and carries the result through the
strike ring, the Simes combination, the Markov posterior, and finally the isotonic
calibration mapper to the published probability. The reference is the *only* input to that
chain that is workload-shaped; everything downstream operates on the residual and is
therefore indifferent to how the reference was produced. That means TimesFM-3 slots in as
one more value of the continuous-method configuration, alongside the present STL-lite, the
mean-only, and the deferred SARIMA: the p50 quantile of its forecast would be the reference,
and nothing from the residual onward changes.

This separation is not incidental; it is the property that makes the study safe and the
future cutover cheap. Because the calibration mapper is fit only on windows assumed healthy,
it remains, as it is today, the layer that excludes anomalies from the reference rather
than letting them in. A better reference and a healthy-only calibration are two distinct
concerns, and the architecture keeps them apart. So adopting TimesFM-3 would improve the
*reference* without disturbing the *calibration* machinery that P3 just made robust, and
the study can evaluate the two layers independently. This is also why the study can be
confined: it is enough to show that the new reference, fed through the *existing unchanged*
downstream scoring chain, produces a better limitation profile than the present reference. No new
scoring law, no new gate, is needed for the comparison to be meaningful.

One consequence of the reference-agnostic design is that the two candidates are fed data
at *their own* resolutions, and that asymmetry is a feature, not a defect. The present
reference operates on five-minute box-car blocks — the mean of twenty fifteen-second samples
for a gauge, the attributed sum of increments for a counter — because that discretisation
is what a windowed mean-plus-seasonal model is defined on. That discretisation is a
property of the moving-average model, not of the data. A pretrained transformer is a
full-stack predictive model with no need for it, and feeding it the boxes would impose one
model family's artefact on another and discard nineteen of the twenty samples in each box.
TimesFM-3 is therefore fed the *raw-cadence* series — the fifteen-second samples, and for
counters the per-interval increments — and its quantiles at the scoring instants are what
enter the unchanged chain: the model itself decides how to use the raw grid, and only at
the hand-off to the residual does the comparison land on the shared five-minute block. The
study must evaluate the candidate at this full resolution; any evaluation on coarsened
input is a distinct, explicitly labelled degradation study, and it is treated as one in §5.

## 4. The scientific questions the study must answer

The study is organised around six questions, each of which the present reference either
cannot answer or answers only by assumption; together they produce the evidence that §6
weighs in its final judgment.

The first, and the one the operator asked for first, is *fidelity on our data, not on public
benchmarks*. The public results are on a different population of series. The question is
how TimesFM-3's one-step reference error compares with the present STL-lite reference on
the scenarios of part 1 — diurnal, drift-and-step, noise-increase, the real burst,
counter-discontinuity, and the mixed case — and where it is better or worse, by how much,
and why. "Better" here is judged against what the reference is for, and the two models are
different enough that a flat "no worse everywhere" rule is not the right test: the present
reference is a primitive one — one time frame, one recurring cycle — and a general model
may trade a small fidelity cost where the primitive model is exact for a large one where
the primitive model cannot reach. That trade, weighed and reported, is what this question
produces.

The second is *calibration of its own predictive distribution, and how its uncertainty grows
with the horizon*. It emits quantiles; the question is whether, on our series, the empirical
coverage of the reported quantiles is close to nominal — whether its tenth percentile
actually holds out about ten percent of the time. A reference whose quantiles are
confidently wrong is a poor generaliser to our data even if its point forecast is decent,
and the calibration-mapper layer above it is not designed to repair a miscalibrated
reference, only to map a healthy-window raw score. Because a detector's decision happens at
a fixed horizon — the present path scores the next five-minute block, so the operative
horizon is thirty minutes at the scoring cadence — the study must report the quantiles at
that horizon for every comparison, and separately, as examples of how the uncertainty
envelope widens, at a shorter horizon (fifteen minutes) and a longer one (an hour and
beyond). The required output for this question is not a table of metrics but a set of
plots: for each of the CPU, memory, and network-rate signals, the observed series with the
model's quantile band overlaid, so that the width and the calibration of the band can be
seen directly. One caution belongs in the design: the network rate in particular is rarely
Gaussian, so its quantile band is judged against the shape of that process, and a band that
is asymmetric or heavy-tailed is a correct answer, not an error.

The third is the *masking risk of cross-variate attention*, and it is the one that needs the
most care because it is a hypothesis that could cut either way. The model attends across the
series in a pod, which is helpful when the metrics share a workload signature — a CPU and
memory rise caused by the same load are informative of each other. It is harmful, in
contrast, when an anomaly in one metric contaminates the forecast of another: if a network
burst pulls the memory forecast up with it, the memory residual shrinks and the anomaly in
memory is masked. The study must therefore run the model in both its univariate mode and its
multivariate mode on our data and compare, because the right answer for a *detector* —
where the goal is to surface a departure in any one signal — is not obvious in advance and
cannot be assumed from a forecaster's benchmark, which rewards joint accuracy, not
per-signal anomaly sensitivity.

The fourth is *flat-case behaviour*, and it is the one that protects what is already
promoted. On the current flat load the present reference is exactly calm: the residual is
tiny and the published raw probability sits at about 0.0013 to 0.0042. That value is
indicative only — it is what a deliberately simple reference happens to produce on a
structureless signal, and it is lower than the system needs. The requirement is that the
quiet case stays *very low*, a band, not a target: a candidate reference at 0.02 on the
flat load still satisfies it — that is a decisive probability of calm — while one drifting
toward the 0.2 operating threshold does not. Being noisier than the two-day mean on a flat
counter is therefore not, by itself, a failure; the judgment asks only that the flat case
remain clearly on the calm side of the operating threshold, with enough margin that a real
event on a flat pod still has room to be seen.

The fifth is *compute and scaling*, and it is the one with the least reliable public
information. There is no trustworthy published latency for a three-hundred-and-thirty-
million-parameter model at our context, and the production path must produce a forecast at
each refit, for roughly ten pods each with a small fixed set of continuous metrics — CPU,
memory, and the network rates — on the hardware we actually have. The test node has a
graphics card, which such a model uses trivially, but whether the reference runs on CPU or
on GPU in production is exactly the kind of thing that must be measured, not inferred, so
the study carries a dedicated compute phase before any accuracy claim is trusted. Its
required deliverable is a scaling plot: the horizontal axis is the amount of history the
model is asked to ingest, shown twice, in raw fifteen-second sample points and in days at
the nominal fifteen-second cadence, so that both the raw-size and the wall-clock reading are
available; the vertical axis is the per-call compute cost, measured on both the CPU and the
GPU and expressed in a machine-independent quantity (an effective FLOP count, or a
comparable normalised unit chosen by the driving process) so that the numbers remain
meaningful on other hardware, not only on the test node. The number of series forecast in
a single call is a fixed input to that plot and is stated on it, since the model is
multivariate. From that plot the study reads off whether a full-context forecast at the
refit cadence fits within a sane wall-clock budget on the available hardware, with margin;
if it does not fit on any available hardware at a usable context, the candidacy ends on
feasibility, which is the one requirement that can fail the candidate on its own.

The sixth is *context-length sensitivity*. The present reference uses two days. The study
should sweep the amount of context given to the model — from about an hour to a day to two
days — and record how fidelity moves, because the answer determines how much history the
production path must retain and how the model behaves on a pod that has been live only a
short time. A reference whose quality collapses when the context is short is a different
operational animal from one that is robust to it.

## 5. The shape of the campaign

The campaign has three movements, and they are sequenced because each one's result
determines whether the next is worth doing.

The first is *research and packaging*. It reads the model card and the inference API,
confirms the context limits and the license, notes the hardware requirements, and it
packages the real data that the study will run on: the currently running flat load for all
ten pods, drawn out of the cluster as the *raw-cadence* fifteen-second samples of the CPU,
memory, and network signals, in a form the local harness can ingest. The five-minute box-car
blocks that the present reference consumes are not a separate input but a *derived* view,
built from those samples by the same box-car law the detector uses, so that the two
candidates are scored on one underlying dataset at their own resolutions. It also fixes the
shared evaluation harness so that it computes exactly the four quantities of part 1 —
reference fidelity, detection latency, false-positive rate, and settling time — on any
reference, present or candidate. This movement changes nothing about the deployed system; it
produces a packaged dataset and a yardstick.

The second is the *compute study*. It measures the per-call compute cost of the model on
the available hardware, across the context lengths of the sixth question, and it produces
the scaling plot required by the fifth question: history ingested, in raw fifteen-second
sample points and in days, against per-call cost on both the CPU and the GPU, in a
machine-independent normalised unit, with the number of series in the call stated. It then
reads off whether a full-context forecast at the refit cadence fits within a sane wall-clock
budget with margin. If it does not fit on any available hardware at a usable context, the
campaign stops here, because no accuracy result matters for a reference that cannot run at
the cadence; this is the only dimension that can fail the candidate on its own. This
movement produces a hardware decision and the scaling profile.

The third is the *confined study*. It runs TimesFM-3, in both its univariate and its
multivariate mode, as a fourth continuous method, through the *existing, unchanged*
downstream scoring chain, on the packaged flat data, on the six scenarios of part 1, and on
the context-length sweep. It is confined in the sense the operator set: it is a series of
capability, performance, scaling, precision, and accuracy tests on packaged data, run beside
the present reference on the same harness, not an end-to-end pipeline integration and not a
change to the running detector. Two additions are required of it beyond the part-1 matrix.
First, a set of *structural-limit scenarios* that the toy reference cannot represent at all
— a signal carrying two or more recurring cycles of different periods, and one whose
dominant variability is shorter than a day — on which the candidate is expected to clearly
outperform the smooth-plus-STL reference, and which therefore carry the weight of the
generalisation claim. Second, the *quantile-band plots* required by the second question:
for each of the CPU, memory, and network-rate signals, the observed series with the
model's predictive band overlaid at the operative thirty-minute horizon, with the fifteen-
minute and one-hour horizons shown as examples of how the band widens. Its total output is a
side-by-side profile of the candidate against the present reference — reference fidelity,
detection latency, false-positive rate, and settling time on every scenario, the quantile-
band plots, and the compute cost — in both modes and across context lengths, ready for the
weighted judgment of §6.

A fourth, *conditional* study is held in reserve and is not part of the accuracy judgment.
It asks what the candidate loses, and at what cost, if it is fed coarsened input — a box-car
mean over the five-minute blocks, optionally carrying a within-box statistic (the standard
deviation, so that some measure of the discarded intra-block variation is preserved) — as
opposed to the raw-cadence series. This is the lever for scaling to a very large number of
pods: coarser input shrinks the per-pod context and therefore the per-call cost, and the
question is whether a model that has seen a box-car mean and a spread, or only the mean,
retains enough of the signal to stay a serviceable reference. It is entered only if the
scaling profile of the second movement shows that the raw-cadence full-context forecast does
not fit the production budget at the target pod count; it is then read as a *degradation*
result — how much fidelity and calibration are traded per step of coarsening — never as the
basis of the adopt decision. It also poses a capability question that the model-card read of
the first movement must answer first: whether the model's published interface accepts any
form of input uncertainty at all, or only point series. If it accepts point series only, the
"with within-box spread" variant is out of scope for this model and the study reduces to the
mean-only coarsening, and that fact is recorded rather than assumed.

## 6. The final judgment

The study does not end with a report; it ends with a decision, and that decision is a
*weighted judgment over the evidence as a whole*, not a pass/fail against a list of hard
thresholds. The reason is that the present reference is a deliberately primitive model:
one time frame (the two-day window) and one recurring variability (the daily cycle). It is
a good toy reference inside a narrow slice of workload space, and that is exactly the slice
the P3 window certified. A pretrained multivariate reference has a different failure
profile, and a strict rule of "no worse than the toy reference on every scenario, on every
quantity" would misjudge it in both directions. It can be *better* where the toy model is
structurally weak — multiple or sub-daily cycles, cross-metric structure — and *worse*
where the toy model is exact; both can be true at once. And it can be *honest in a way the
toy model is not*: a general model that sees a slowly changing regime widens its quantile
interval instead of pretending the regime is stable, which is uncertainty rightly expressed
rather than a defect to be penalised. So no single scenario, quantity, or margin is
dispositive on its own; the evidence is organised into dimensions that the judgment weighs.

The primary dimension is *detection quality*, because the reference's job is to detect:
to separate low anomaly probabilities from high ones with a clean margin. This is read
across the whole part-1 matrix and the flat control together — quiet signals must give
decisively low published probabilities, and genuine events must give clear, timely high
ones. "Decisively low" is a *band*, not a number: the present reference sits at about
0.0013 to 0.0042 on the current flat load, and that value is indicative only — it is what
a deliberately simple reference happens to produce on a structureless signal, and it is
lower than the system needs. The requirement is that the quiet case stays *very low*: a
candidate at 0.02 on the flat load still satisfies it, one at 0.2 does not, and the toy
model's own value is not the boundary.

The second dimension is *generalisation*, and it is where the candidate should earn its
keep: on the structural-limit scenarios this study adds to the part-1 matrix — multiple
seasonality, and variability shorter than a day — cases the toy reference cannot
represent at all, it should clearly outperform the smooth-plus-STL reference. That is the
concrete, measurable form of the generalisation claim, and a candidate that does not show
it there offers no advantage over the model it would replace.

The third dimension is *uncertainty quality*: the calibration of its quantiles on our data,
and the cost of its honesty. Where its intervals are wider than the toy model's, the
judgment asks *why* — regime awareness the toy model cannot have is a credit, weighed
against whatever it costs on the flat case; and on the network rate in particular, where
the underlying process is rarely Gaussian, the coverage is judged against that process
shape, not a Gaussian assumption. A reference whose intervals are miscalibrated in the
tails is a liability regardless of how good its point forecast is.

The fourth dimension is *feasibility*, and it is the only one with a hard floor: a
reference that cannot run at the refit cadence on the available hardware simply cannot be
a reference, and that ends the candidacy on its own. It is a feasibility fact, not a
quality judgment, and it is the only dimension that can fail the candidate by itself.

On that basis the study closes with a recommendation — adopt, do not adopt, or adopt with
a specified adaptation (a context length, a mode, a horizon) — with the pros and cons
weighed in writing against the dimensions above. If the recommendation is to adopt, the
consequence is not an immediate cutover but a *roadmap decision*: the reference cutover is
its own implementation package, driven through the ordinary research-to-plan-to-evidence-
to-review sequence, because replacing the deployed reference is a production change that
deserves its own gates. If it is not to adopt, the present reference stays and the SARIMA
option remains exactly where it is — deferred, fixed-order, and not worth the investment
that a foundation model now makes available for the ambitious case. The campaign's value in
either outcome is the same: a measured answer, on our data, to whether a pretrained
multivariate reference is a genuine improvement for this detector, rather than an
assumption inherited from a benchmark.

## 7. Boundaries

The campaign is confined and read-only with respect to the deployed system. It ingests
packaged data and runs a local harness; it does not alter the running detector, the
production pipeline, or any of the scoring laws. The model is brought in through its
published interface with weights pulled from the public repository, and the license is
confirmed before the weights are committed anywhere. No threshold, strike, fusion, or
calibration law is touched; the only thing that varies between the present and the candidate
is the reference forecast, which is exactly the point of the reference-agnostic design. The
flat control is asserted unchanged at the end, as the evidence that the study introduced no
drift into the promoted behaviour. The deliverable is the side-by-side profile against the
present reference, the hardware and scaling decision, and a written recommendation — adopt,
do not adopt, or adopt with a specified adaptation — for or against taking a
reference-cutover package forward.
