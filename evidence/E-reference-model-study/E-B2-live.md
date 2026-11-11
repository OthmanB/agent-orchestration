# E-B2-live — B2 CUDA refresh-vs-pods remeasurement (run by S, per operator D17)

- Date: 2026-11-09 19:53Z → 21:30Z (2026-11-10 04:53 → 06:30 JST). Run by the supervisor session (S = `anthropic/claude-sonnet-5-5`), from the approved LIVE BATCH SPEC of `omp-workcards/refm-B2.md`. Supersedes the pre-D8 worker-authored measurement (`E-B2-live-preD8-worker.md`, archived result `results/archive/b2-refresh-cuda-preD8.json`, which S kept only as an old fixed-shape measurement; RV-B F2/F3).
- Why a remeasurement: RV-B found (F1) the `batched_overlap` calibration collapsed (B*=32 ⇒ both calibration counts rounded to 32) so the batched pipeline was unmeasured, and (F2) `PodWorld` bypassed operator D8 (regular-grid input). Fixes committed before this run: `a2c4584` (F1/F4), `6b99fb3` (F2), `f8c618d` (F5 plots/power resolution). Host code md5 == Mac code md5 (`refresh_run.py 9c7cb538…`, `podgen.py 6a20ff55…`, `refresh_study.yaml 3a3b083c…`).

## Setup (as observed)
- Host `rtx-4000-test`, GPU RTX PRO 4000 Blackwell SFF (70 W limit), torch 2.15.0+cu132, 1 torch thread; idle GPU, 0 compute apps before; host CPU saturated by the tester stress (`load1` 11.4–19.6, mean 14.9 across the 57 run-start snapshots, recorded not enforced). The pipeline's prep/arrival/gate/dispatch threads share that saturated host CPU ⇒ **shared-host end-to-end numbers, not isolated GPU ceilings** (RV-B F3).
- Command: `REFM_LIVE=1 nohup timeout 12000 .venv/bin/python scripts/run_refresh.py --config config/refresh_study.yaml --device cuda` (all stages), one process, **exit clean** (log has 0 `Traceback|ERROR`), 57 runs, 0 polluted, 1 intentional deadline abort (`pool_sweep … w4-c1-block`). Wall 97 min. Result `results/b2-refresh-cuda.json` (resume doc), plots by `scripts/plot_refresh.py` (figures `figures/b2-*.png`, tables `results/b2-sustainable.json`, `results/b2-headline.json`).
- Input path (D8): per pod, the irregular raw series are resampled on the regular 15 s grid by `refstudy.refcompare.grid.to_grid` (counters as increments of the interpolated cumulative, gauge interpolated, NaN for gaps > 35 s; `series_len_min` 56 578 grid points; NaN fraction ≈ 4×10⁻⁴; unique windows 190 @ 2 d, 210 @ 1 d).

## Results (V=4 series per pod, H=120, fetch/chain modelled per the card, model call and prep measured)
Probe (2 d context, V=4): batch B=1/2/4/8/16/32 → 2.61/3.92/4.24/4.66/5.00/5.06 pods/s, `b_star = 32`, batching effective (+94 % over B=1). Numerics: single-vs-batched max|Δ| = 32.0 on memory-scale values (≈2.55×10⁸ B, i.e. relative ≈1.3×10⁻⁷ — same as the earlier 1.25×10⁻⁷; the report's `rel` is null because `np.ptp` of a NaN-bearing window is NaN: a small reporting bug, logged below); packing variates of several pods into one call differs by 1.4×10⁵ (rel ≈ 5.6×10⁻⁴) — INVALID, as before.

Sustainable pods per refresh pass (one pass of the whole list within the budget; `interpolated` = bracketed by measured runs, `extrapolated` = beyond measured, hollow in the figure):

| variant | ctx | 120 s | 180 s | 300 s (tick) |
|---|---|---|---|---|
| sequential | 2 d | 172 | 257 | 429 (extrap.) |
| overlap (4 workers, prefetch) | 2 d | 287 | 423 | 706 (extrap.) |
| batched_overlap (B=32) | 2 d | 571 | 856 | 1 429 (extrap.) |
| sequential | 1 d | 293 | 441 | 734 (extrap.) |
| overlap | 1 d | 497 | 741 | 1 234 (extrap.) |
| batched_overlap | 1 d | 1 188 | 1 783 | 2 965 (extrap.) |
| accelerator-only bound (probe B*=32, 5.06 pods/s) | 2 d | 607 | 910 | 1 517 (derived from probe) |

- Asynchronism buys: overlap/sequential ≈ 1.65–1.7×; batching adds another ≈ 2× at 2 d (batched/sequential ≈ 3.3×); batched_overlap reaches 94 % of the accelerator-only bound at 300 s.
- Validation of the extrapolated 300 s knees (staggered full 300 s tick at ρ = 1.3): sequential 2 d, 568 pods, `sustained_ratio` 0.971; batched_overlap 2 d, 1 873 pods, `sustained_ratio` 1.022. Only these two (variant, context) pairs were validated; every 300 s knee in the table remains `extrapolated` and no thermal claim is made (no retained temperature history).
- Pool sweep (production-like admission, 71 pods, simultaneous burst): `drop` (production 4 workers, queue 8) completes in 3.7 s and drops 63/71 pods (89 %) — a burst-admission experiment, not a steady-state drop rate; `block` variants complete in ≈30 s; `w4-c1-block` hit its deadline (intentional abort).
- Power (GPU board only; `power_resolved` true on all rows): idle (resident model) ≈ 17.4–18.0 W; mean board power during passes sequential ≈ 37–39 W, overlap ≈ 43–49 W, batched_overlap ≈ 68 W (at the 70 W limit); energy per pod above idle sequential ≈ 15 J (2 d) / 7.6 J (1 d), overlap ≈ 13 / 6.2–6.9 J, batched_overlap ≈ 10.3 / 5.0 J. Power scope differs from the Mac's whole-system telemetry; not comparable.
- Queue/backpressure (stagger, 300 s window, `end_frac` = backlog at window end / pods): ρ 0.6/0.9/1.1/1.4 → sequential 0.019/0.013/0.115/0.320; overlap 0.012/0.015/0.108/0.327; batched_overlap 0.017/0.073/0.237/0.377; max queue depth sequential 1, overlap 7, batched_overlap 32 (= B*). The unbounded-growth threshold (5 %) is first crossed at ρ = 1.1 for sequential/overlap and already at ρ = 0.9 for batched_overlap (7.3 %): batching raises capacity but its queue builds earlier ([INFERENCE]: waiting to fill a batch) — see `figures/b2-queue-backpressure.png`.

## Reading (for Phase E; "the target the plots show the hardware can sustain")
On the RTX PRO 4000 with the saturated host, a 4-signal 2-day-context refresh of the whole pod list within one 300 s tick is sustained for ≈430 pods sequentially, ≈700 with overlapped scans and ≈1 400 with batched inference (model-bound ceiling ≈1 500); at the stricter 180 s / 120 s budgets 260–860 and 170–570 respectively; halving the context (1 d) roughly doubles those. These are shared-host, fixed-fetch-model numbers; the 300 s values are extrapolated except where validated above. CPU/MPS/MLX (Mac) B2 runs have NOT been performed (the CUDA host is the primary hardware, D7; Mac B1 per-call numbers exist from A2/B1).

## Deviations / open items
- D15: the previous B2 measurement was produced under an unlawful role and is superseded by this S-run.
- The `numerics` block's `rel` fields are null when the window contains NaN (`np.ptp` instead of `np.nanmax-np.nanmin`): reporting bug, values above are computed by S; recorded for a later small fix, no effect on measurements.
- No hygiene abort occurred; load recorded only.
