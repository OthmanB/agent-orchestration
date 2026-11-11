# Reference-model behaviour under non-flat load: a scenario campaign (SOLO-OPS reference study, part 1)

**Date:** 2026-11-08
**Status:** vision document, injected by the operator for the Supervisor to drive.
**Scope:** read-only with respect to the deployed system; local synthetic fixtures plus
already-recorded live data. No threshold, no law, no retune of any kind.
**Relation:** this is part 1 of a two-part reference-model study. Part 2 evaluates a
candidate replacement reference (TimesFM-3). Part 1 produces the measuring stick and the
limitation profile that part 2's acceptance depends on, so it must land first.

---

## 1. What has actually been proven so far

Through the P1–P5 campaign the solo detector has been promoted and live-proven, but on
one workload: a fleet of tester pods that, over the whole observation period, produced a
nearly constant signal. The P3 window is the cleanest evidence of this — across ten pods
and roughly forty hours of post-rollout ticks, the published probability stayed in a band
of about 0.0013 to 0.0042, no pod ever crossed the 0.2 operating threshold on more than a
handful of ticks, and no degenerate calibration mapper was ever adopted. That is a genuine
result, and it is exactly what the system is *supposed* to do under flat load: a calm window
should read as calm.

The limitation is that flat load is a degenerate input. Every adaptive mechanism in the
reference model is, in that case, doing essentially nothing. A two-day moving average of a
constant is that constant; the daily seasonal term has no cycle to find; the noise law, fit
to the residuals of a constant series, is a tight spike at zero. The fact that the system
behaves well there therefore tells us almost nothing about how it will behave on the
workloads it will actually be asked to monitor — signals with a diurnal rhythm, with slow
level drift, with step changes at deploys, with short genuine anomaly bursts, and with the
counter discontinuities that already show up today as the informational network counters
failing to align. This campaign exists to close that gap: to describe, in measured
quantities, where the current reference model is faithful and where it degrades, so that a
future decision about whether to replace it is made against evidence on realistic signals
rather than on the one case it is known to pass.

## 2. First, what is actually adaptive in the present design

There is a misconception worth removing before any experiment, because it determines what
the experiments must look for. The shape of the reference model is *not* data-adaptive. The
family is fixed by configuration: for continuous metrics it is an STL-lite decomposition
over a two-day window of five-minute blocks, namely a full-window mean acting as the trend
term and, on top of it, a daily seasonal term made of forty-eight centred phase-bin means.
No parameter of that shape is ever searched against the data. There is no BIC or AIC or
residual-sum-of-squares selection over a window length, an AR order, or a smoothing
coefficient. The only place a value is chosen at runtime is a compute-budget search that
coarsens the *internal fit sample* by powers of two if the fit computation threatens to
exceed the thirty-minute refit cadence; it touches neither the forecast nor the scoring.
The SARIMA path, which does compute BIC and AICc, is fixed-order, refused by the
incremental steady-state path, and its information criteria are consumed only by tests.

What *is* adaptive, and is the whole of the adaptation, is the noise law. The residual is
the observed block minus the reference forecast, and the surprise of that residual is scored
against the empirical mid-rank cumulative distribution of the one-step residuals collected
over the same two-day window:

$$F(r) = \frac{c(r) + \tfrac{1}{2}}{N}, \qquad p = F(-|r|) + 1 - F(|r|).$$

That formula is the answer to "how does the model match the observations": the reference
*shape* is fixed, but the *scale and shape of the tolerance* is non-parametric and re-learns
from the pod's own residual history. This separation — fixed reference, adaptive noise law —
is the thing the campaign is really probing, and it implies that the interesting failure
modes will not appear as "the moving average chose a bad window." They will appear in the
interaction between the two layers, which is described next.

## 3. The two failure modes the design must distinguish

Because the reference is a lagged estimator and the noise law is fit on the same window,
there are two distinct ways the system can misbehave on a non-flat signal, and they have
different signatures and different causes. Keeping them separate is the organising principle
of the whole campaign.

The first is *reference lag*. A two-day sliding mean is, mathematically, a moving average
whose response to a step or a ramp is that of a low-pass filter with an effective time
constant of roughly half the window. A level shift or a sustained slow drift therefore does
not get absorbed instantly; it appears as a systematic residual that persists, and decays,
over a period of order one day after the change. At the moment of the change this systematic
residual is *correct* behaviour — it is the detector flagging the departure from the
reference. The question the campaign must answer is what happens *after* that: how long
until the reference has tracked the new regime, and whether the detector settles back to
calm or keeps ringing.

The second, and the more dangerous, is *noise-law contamination*. Because the empirical
distribution is fit over a two-day window that includes whatever just happened, a genuinely
anomalous episode or a sustained drift does not merely get flagged at onset; it then feeds
back into the very distribution used to judge subsequent residuals. A burst that lasts long
enough to populate the residual window inflates the tail of $F$, which raises the threshold
at which later residuals look surprising. In plain terms, the detector partly teaches
itself to expect the abnormal, and its sensitivity to that class of event degrades for the
remaining life of the polluted window. This is self-masking. It is the structural blind spot
of the current design, and it is precisely the role that the calibration mapper was built to
cover a second time — the mapper is fit only on windows assumed healthy, so it is the layer
that is meant to "exclude anomalies from the reference" rather than let them in. The
campaign does not set out to fix either effect; it sets out to *measure* them, because their
magnitude on realistic signals is exactly the quantity that part 2 will need to compare a
candidate reference against.

There is a third, subtler hypothesis that the campaign should be able to confirm or refute,
raised directly by the operator: whether the machinery over-fits high-frequency variation
that is pure noise. The moving average averages high-frequency noise *down*, which is a
strength, not a risk, at the reference layer. The risk instead sits in the noise-law layer
and takes two forms. One is that an *increase* in background noise, with the mean unchanged,
widens the empirical distribution and thereby dulls sensitivity to a real anomaly of the
same size. The other is a misspecification risk that is worth stating explicitly: the
empirical-distribution score treats the one-step residuals as interchangeable samples from a
single law, which is only true if the residuals are effectively independent. If the
reference fails to track a slowly varying component, the residuals are correlated over
time, and a correlated residual stream violates the assumption behind the two-sided tail
score. The diurnal and drift scenarios in the next section are designed so that each of
these hypotheses has a scenario whose signature it would produce, and the quantities
measured in §5 are chosen to be able to tell them apart.

## 4. The scenario design

The campaign is a small controlled matrix, each case holding most of the input space fixed
and moving one factor, so that the observed effect can be attributed. There are six named
cases, and they are described here in terms of what they isolate rather than as a list.

Each case is illustrated by one figure, generated by the seeded script
`scenario-figures/generate.py` that accompanies this document, and all figures share a
common template so that they can be read against each other. The columns are the three
continuous signals of a pod — CPU utilization in percent, the memory working set in
mebibytes, and the received network rate in mebibytes per second; the count-based error
metrics are intentionally absent, because they are scored by the rare-count law, not the
reference-plus-noise-law pair that this study probes, and mixing the two would obscure the
attribution each figure is meant to make. The rows are the three layers of the mechanism,
in the order it operates: the top row shows the simulated observed series together with
the reference forecast the STL-lite model actually computes at each step — the causal
two-day mean plus the daily seasonal term, with the thirty-minute no-leakage tail; the
middle row shows the residual, observed minus reference; the bottom row shows the
per-metric p-value, the two-sided surprise of that residual against the empirical noise
law of the same two-day window, with the strike line at p = 0.05 drawn so that a tick
falling below it is one the strike ring would count. The displayed window is forty-eight
hours of simulated data, preceded by four and a half days of the same regime, so that
from the first displayed step the reference window and the noise law are already fully
populated. The figures are therefore not just depictions of the input: they show how the
model responds to each case, and the responses they show — sustained strikes after a
shift, false strikes at a variance switch, a second burst read as less surprising than
the first — are the measured signatures of the two failure modes of §3, made visible.

The *diurnal* case puts a daily cycle on the load — a smooth sinusoid plus a sawtooth that
repeats with a one-day period on the CPU and memory signals — so that the forty-eight-bin
daily seasonal term is actually asked to do its job. It tests whether the reference tracks a
slow, periodic variation that sits squarely inside its design intent, and it establishes the
fidelity of the reference on a clean, predictable, non-flat signal. It is the baseline for
every later comparison.

![S1 — diurnal](scenario-figures/scenario-1-diurnal.png)

*Figure 1 (S1, diurnal).* This is the case the reference is built to win, and it wins it.
The learned seasonal term in the inset, S(j) fitted on the two-day window, reproduces the
true daily cycle almost exactly (correlation with the injected cycle of about 0.99, and no
phase lag): the forty-eight-bin seasonal term is doing its job. The reference therefore
tracks the observed cycle tightly (correlation with the observed series of about 0.97),
and the residual is essentially the injected noise alone (residual standard deviation of
about 1.6, against 1.5 injected), not a systematic departure. The consequence, visible in
the bottom row, is that the per-metric p-values sit high for most of the window (median
near 0.5, meaning the residual is unsurprising) and only a small fraction — about five
percent, the expected chance rate at the p = 0.05 strike line — falls below it on any given
tick. That small, steady false-strike rate is not a defect of this case; it is the reason
the strike *ring* (three of four) and the Simes combination exist, rather than a single
tick deciding. S1 is the honest baseline against which the failure modes that follow are
judged: on the signal shape it was designed for, the reference-plus-noise-law pair is
calm and correct.

The *drift-and-step* case moves the operating level. A slow monotone drift over several
hours, and separately a sudden step that mimics a deploy or a restart changing the steady
load, each isolate the reference-lag failure mode of §3. The slow drift is the one the
operator specifically asked about — whether slow-frequency variability is captured — and the
step is its sharp limit. The test here is not that the system detects the shift (it should),
but *how long the reference takes to settle* after it, and whether it settles at all within
the two-day window, or lags behind for the whole duration.

![S2 — drift and step](scenario-figures/scenario-2-drift-step.png)

*Figure 2 (S2, drift and step).* Both moved factors show the reference-lag mechanism of §3
directly. After the slow drift on memory, the reference sits below the raised level and
the residual is a persistent positive band; after the step on CPU, the residual jumps at
the shift and then decays with the slow time constant of the sliding two-day window, which
is the low-pass response of the moving mean. In the bottom row this appears as a *sustained
run of strikes immediately after the shift* (the departure from the reference is real, so
this is correct detection at onset), then a decaying pattern of intermittent strikes as the
reference chases the new level, and finally a return to the quiet p-level. The measured
settling on this seed is of order a day: at two hours after the shift the per-metric
p-value is still near the strike line (about 0.03), at twelve hours it has risen (about
0.04, still marginal), and only by about thirty-six hours has it returned to a quiet
baseline (about 0.7). The exact figure depends on the drift's slope and on how the noise
law, still polluted by the departure, competes with the reference catching up — which is
precisely the interaction §3 asked the campaign to measure.

The *noise-increase* case keeps the mean level and the diurnal structure fixed and raises
the background variance by a factor of about three. It isolates the noise-law behaviour:
does the empirical distribution re-adapt to the new noise scale cleanly, without chasing the
new noise as a sequence of anomalies, and does a genuine anomaly of fixed size still clear
the threshold once the distribution has widened? This is the direct test of the over-fitting
hypothesis.

![S3 — noise increase](scenario-figures/scenario-3-noise-increase.png)

*Figure 3 (S3, noise increase).* The figure separates the two effects the hypothesis
predicts. Immediately after the variance switch, the *reference* is still correct in level
(the mean has not moved) but the *noise law* is still fitted to the quiet regime, so the
now-wider noise reads as a run of false strikes — visible as a burst of low p-values in
the bottom row around the switch, which decays as the noise law re-learns the new scale
over the following days. That transient is honest: the detector is genuinely seeing a
regime change in its own residuals. The second effect is the one the operator asked about
directly: an anomaly of *identical size* (the two marked bumps in the CPU row, equal in
height to each other) produces a p-value deep below the strike line on the quiet noise
(about 0.002), but the *same* anomaly on the widened noise produces a p-value far above it
(about 0.31) — the fixed-size anomaly is four times the background standard deviation on the
quiet regime and only about one and a third on the widened one, so it no longer reads as
surprising. This is not a bug in the mechanism; it is the correct
behaviour of a noise-adaptive law, and it is the quantitative price of adaptivity that any
candidate reference in part 2 must not do worse on.

The *anomaly-burst* case does not need to be synthesised at all, because one is already
recorded: the fleet-wide burst on 6 November between 01:15 and 02:20 UTC, captured in the
P3 tick store, where the raw probability climbed toward one across the whole fleet for about
an hour. It is the most valuable case in the matrix because it is real. It is used to
measure detection latency — how many ticks from onset until the published probability clears
0.2 through the strike, Simes, and Markov chain — and, more importantly, to measure
*recovery and self-masking*: how the residual distribution, once the burst has passed into
the two-day window, changes the sensitivity to a second, identical burst. This is the
contamination mechanism of §3 observed on data rather than in principle.

![S4 — anomaly burst](scenario-figures/scenario-4-anomaly-burst.png)

*Figure 4 (S4, anomaly burst).* Both bursts are detected: on this seed each one occupies a
contiguous run of about fourteen struck ticks out of its eighteen, well below the 0.05
line, against a quiet background whose median p-value is near 0.44. The contamination
effect of §3 is visible but, at this duration, *modest*, and the figure is best read as
honest about its size. After burst 1 has passed into the two-day residual window, the
distribution now contains the burst's own large residuals; on this seed that is about one
percent of the window's residuals, and the consequence is that the *same* event reads as
less surprising the second time: the median p-value inside burst 2 is roughly ten times
higher than inside burst 1 (about 0.018 against 0.002), even though the depth of the
deepest residual is unchanged. The strike fraction over the burst, however, barely moves
(about 0.78 in both), because the bulk of the burst's residuals are still far out in the
inflated tail. The mechanism is duration-limited: contamination scales with the fraction
of the two-day window an event occupies, so a burst of an hour costs a detector little,
whereas a slow drift that persists for days occupies a much larger fraction of the window
and the self-masking is correspondingly stronger — which is why S2, not S4, carries the
worst-case form of this effect, and why the two cases must be read together.

The *counter-discontinuity* case takes the already-observed behaviour where the informational
network counters report "block not aligned" and makes it systematic and controlled, so that
the interaction between a partially-uncomputable metric and the mandatory set can be studied
without the confound of a real anomaly. It is the case that exercises the mandatory-only
degradation rule that the status-clarity work just put in place, and it checks that a gap in
an informational metric degrades the display honestly without being misread as a workload
anomaly.

![S5 — counter discontinuity](scenario-figures/scenario-5-counter-gaps.png)

*Figure 5 (S5, counter discontinuity).* The network counter is missing a block every two
hours (the shaded intervals, 30 minutes each); on this seed those are the only missing
data. The figure's point is what the mechanism *does not* do: a missing block produces no
tick at all — the alignment check rejects it ("block not aligned"), it is never padded,
never imputed, and never scored — so the gap leaves no mark on the residual row and no
false spike in the p-value row of the network column. The reference and the noise law are
computed only from the blocks that are present, and on this seed the surviving blocks
score normally (median p-value near 0.49, no persistent run of strikes). CPU and memory,
which are gap-free in this case, are shown so that the figure also certifies the absence
of cross-metric contamination: nothing in the network gap leaks into the other two
signals. This is the controlled version of the already-observed behaviour where the
informational network counters fail to align; the campaign's job is to confirm that, under
a systematic version of it, the mandatory-only rule of the status work labels the display
honestly — degraded on the affected metric, not anomalous on the workload.

The *mixed* case stacks the diurnal structure, a slow drift, and a burst together, in the
manner of a real operational episode, to see how the effects compound — in particular
whether a burst occurring on a drifting, diurnal signal is detected as well as it is on the
flat or clean-diurnal signal. This is the closest the matrix gets to the workloads the
detector will actually face, and it is the case most likely to expose an interaction that the
single-factor cases hide.

![S6 — mixed](scenario-figures/scenario-6-mixed.png)

*Figure 6 (S6, mixed).* The slow memory drift is visible in the middle row as a rising
residual band across the second displayed day, while the CPU and network, which carry no
drift, remain calm (their p-values stay near their quiet baselines, confirming there is no
cross-metric leakage from the drifting series). The burst on top of the drifting, diurnal
signal is detected cleanly: a contiguous run of about fourteen struck ticks, with p-values
reaching about 0.002 — as deep as the burst in S4 on the flat background. The compound
case therefore shows, on this seed, that the two failure modes of §3 do not *interfere*
with each other here: the drift costs the memory metric its settling time (as in S2), and
the burst is still caught at full depth. This is the case the campaign will re-run with
the candidate reference in part 2, because it is the one in which a reference that can use
the joint structure of the three signals has the best chance to show an advantage over the
univariate mean-plus-seasonal model.

## 5. The quantities measured, and why each one

For every case the campaign records the same small set of quantities, because comparing
references in part 2 requires a common yardstick and these four are the ones that separate
the failure modes of §3.

Reference fidelity is the one-step-ahead error of the reference forecast on the *quiet*
segments of each case — the parts of the signal that contain no anomaly and where the
reference is doing its honest job. A good reference tracks the slow structure (diurnal,
drift) with small one-step error; a bad one leaves a large systematic residual. This is the
quantity that directly answers the operator's first question, whether slow-frequency
variability is captured.

Detection latency is the number of ticks between a known anomaly onset and the first tick
whose published probability exceeds the 0.2 operating threshold. It measures the end-to-end
sensitivity of the whole chain, reference to mapper, on a real event.

The false-positive rate on quiet segments is the fraction of non-anomalous ticks whose
published probability clears 0.2. It is the price paid for sensitivity, and it is the
quantity most at risk from both the noise-increase case and, after a burst, the
contamination case.

The settling time is the number of ticks after an event, or after the *end* of an event,
before the published probability returns to its pre-event baseline and stays there. It is the
direct observable of reference lag and of self-masking: a long settling time after the
*end* of a burst is the signature of a contaminated noise law, while a long settling time at
the *onset* of a drift is the signature of a lagging reference.

Recording these four for every case produces, for the current reference, a limitation
profile: a description of its fidelity, latency, false-positive rate, and settling behaviour
across a realistic slice of workload space. That profile is the deliverable of part 1.

## 6. The data

Three sources, each with a distinct role. The synthetic cases come from the existing
scenario fixture harness that the P3 work already used, so the machinery, the generators,
and the seeding are all in place and deterministic; the campaign extends that harness with
the six scenarios rather than inventing a new one. The real burst comes from the P3 tick
store, which already holds the full post-rollout history for all ten pods; the 6 November
burst is extracted from it as-is, without modification, so that the anomaly-burst case is
grounded in a real fleet event. And the currently running flat load is carried through
every case as a control, not merely a convenience: it is the non-regression anchor, and it
must show that whatever the campaign adds does not disturb the one behaviour already
promoted and live-proven.

## 7. How this feeds part 2

Part 2 proposes a candidate replacement reference and will need to claim that it is *better*
than the present one. "Better" is only meaningful against a yardstick, and the yardstick is
exactly the limitation profile this part produces: the same four quantities, on the same
six scenarios, on the same packaged data. Part 2's final judgment is made against that
profile, on this data, rather than on public benchmarks. The two parts are therefore a
single study in two
movements, and the ordering is not a formality: part 2 cannot be judged until part 1 has
fixed the measuring stick.

## 8. Boundaries

The campaign is read-only with respect to the deployed system. No threshold, no strike or
fusion or calibration law, no sojourn, no prior, no operating threshold, is changed; the
only thing the campaign may touch is the fixture harness and the local analysis that runs
on it and on the recorded data. The live cluster is a data source, not an experiment bed:
real data is packaged out of it and tested locally, and no experiment runs against the
running pods. The flat control is asserted to be unchanged at the end, which is the
evidence that the campaign itself introduced no drift. The deliverable is the limitation
profile, written up with the measured numbers, and the packaged data and harness that
part 2 will reuse. Nothing in this part is a production change, and nothing here authorises
one.
