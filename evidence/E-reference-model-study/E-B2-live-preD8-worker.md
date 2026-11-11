# E Live — SOLO-REFM / B2 LIVE BATCH

> **⚠ PRE-D8-FIX MEASUREMENT.** This whole file is a measurement taken **before** the
> regular-grid input fix (Fix B, RV-B F2 / operator D8). It used the **old fixed-shape
> `PodWorld`** (positional truncation, `podworld.series_len_min = 51729` — not the
> resampled grid length 56578) and **modelled fetch/chain**. It is kept as the old,
> fixed-shape compute measurement and will be **superseded by a remeasurement** on the
> corrected timestamp-aligned regular-grid input (S decides whether corrected prep
> materially requires remeasurement; old data is not relabelled). No number below is a
> measured end-to-end regular-grid 1-/2-day refresh figure.

Date: 2026-11-09. This file records the B2 LIVE BATCH runs (CUDA here; Mac devices appended later by their workers). No lab code was edited by the live workers; one **script bug** was found (below) and is returned to the Supervisor/Executor — no gate was loosened.

## CUDA (worker RefmLiveB2cuda)

Scope: **M0** (host sync + 10-pods/GPU-idle check) and **M1** (CUDA refresh study, all six stages: probe → numerics → grid → stagger → validate → pool_sweep), per the card LIVE BATCH SPEC and E-B2.md "LIVE BATCH — what the live worker needs". The finalize pass was NOT done (card: files only).

### M0 — host sync & checks (all passed)

| Step | Command | Result |
|---|---|---|
| rsync (same excludes as B1-L0(b), no `--delete`) | `rsync -a --exclude .venv --exclude artifacts --exclude throwaway --exclude __pycache__ --exclude .pytest_cache --exclude .ruff_cache --exclude data/raw/oracle --exclude data/raw/p3 $LAB/reference-model-study/ rtx-4000-test:refm-lab/reference-model-study/` | rc 0; fast (only B2 files new on host). `results/b1-scaling-cuda.json` was **not** clobbered: md5 `c90d2325…` identical on Mac and host (rsync skipped it). |
| md5 verify host == Mac | `md5sum src/refstudy/compute/refresh_run.py config/refresh_study.yaml` | `6636e030fb2031440f8dcd0c04aa81b1` (refresh_run.py) and `bf39657224735d37c86d56548ad1c816` (refresh_study.yaml) — **match** the Mac copy. |
| 10-pods check | `.venv/bin/python -c "from refstudy.data.loader import list_pods; print(len(list_pods()))"` | `10` → `['b4xkt','mjnlq','rzpzm','hcfj7','vlsl8','2vwwd','7gjdg','c5bdh','m7pr8','qsv2m']` |
| GPU idle | `nvidia-smi` | `15 MiB, 0 %, 8.57 W, 34 °C`; **0 compute apps** |

Host context recorded: `load average 15.27` = the permanent CPU-only tester-workload stress (recorded, **not enforced** — `cuda_host` profile has `enforce_cpu:false`, `max_load1:null`, `gpu_other_procs_max:0`). No `b2-refresh-cuda.json` pre-existed.

### M1 — CUDA run (launch)

`ssh rtx-4000-test 'cd ~/refm-lab/reference-model-study && export PATH=/usr/local/cuda-13.2/bin:$PATH; export LD_LIBRARY_PATH=/usr/local/cuda-13.2/lib64:$LD_LIBRARY_PATH; REFM_LIVE=1 PYTHONUNBUFFERED=1 nohup timeout 9000 .venv/bin/python scripts/run_refresh.py --config config/refresh_study.yaml --device cuda > throwaway/b2-live-cuda.log 2>&1 &'` → pid 2461838. (PATH/LD_LIBRARY_PATH exported inline per the D7 environment fact — non-interactive ssh does not source `~/.bashrc`.) Runtime: python 3.12.14, timesfm 3.0.2, torch 2.15.0 (cuda 13.2), RTX PRO 4000 (sm_120, cap 12.0), fp32 defaults `float32_matmul_precision=highest`, `cuda_matmul_allow_tf32=False`, `torch_threads=1`. Hygiene gate **passed attempt 1**; `start_abort` absent. `external_connected_start`: null (n/a Linux, `require_ac:false`).

**The all-stages run crashed deterministically at `stagger` → exit 1.** Probe, numerics, the full grid, and the sequential+overlap stagger all measured before the crash; the result file (resumable) was kept and completed by two card-sanctioned slices (below).

### The script bug (returned to Supervisor/Executor — not fixed here, no code edit)

With the probe result `b_star = 32` and YAML `batch.round_n_to_batch: true`, `calibrate()` for variant `batched_overlap` rounds **both** calibration pod counts up to the batch: `round_up_to(10,32)=32` and `round_up_to(30,32)=32` → the two passes collapse to one usable point →
`calibrate()` logs `calibration batched_overlap ctx=11520: < 2 usable points, grid skipped` (and ctx=5760 likewise) and stores **no calibration** for batched_overlap. `stage_grid` then degrades gracefully (skips that variant's grid). But `stage_stagger` and `stage_validate` call the **lookup** `Runner.calibration(variant, ctx, stage)`, which **raises** `ValueError` for the missing entry — and only `AcLost` is caught in `run_device`; `main()` maps `ValueError` → exit 1. Verbatim crash (tail of `throwaway/b2-live-cuda.log`):

```
2026-11-09 19:04:57.793 | ERROR    | __main__:main:98 - stage 'stagger' needs calibrations[variant='batched_overlap', context_pts=11520] (run stage 'grid' first)
```

Deterministic (re-running the identical command fails identically — `b_star=32` reproduces every time at this context). Root cause is a calibration-pod-count vs. batch-size degeneracy in `refresh_run.calibrate`, not a transient host condition. **Fix belongs to the Executor** (e.g. choose distinct `calibration_pods` that survive `round_up_to(n, b_star)`, or make the `batched_overlap` stagger/validate not hard-depend on its own calibration, or cap `b_star` below `calibration_pods[1]`). This blocked the `batched_overlap` grid/stagger/validate and the all-in-one `pool_sweep` ordering only via the shared crash; the **overlap**-variant pool_sweep (independent of the bug) was completed by slicing.

### M1 completion via card-sanctioned slices (exact `--stage`/`--variant`)

Both re-launches use the same launch prefix as above. The result file `results/b2-refresh-cuda.json` is the single resumable artifact; slices skip already-measured runs by key.

| Slice | Command (extra args) | Exit | Log |
|---|---|---|---|
| validate (sequential only) | `--stage validate --variant sequential` | **0** | `throwaway/b2-live-cuda-validate-seq.log` |
| pool_sweep (overlap; 7 pool configs) | `--stage pool_sweep` | **0** | `throwaway/b2-live-cuda-pool-sweep.log` |

Resume proof (identical command re-run on a doc copy): validate-slice re-run → exit 0, 1× "already measured"; pool-sweep re-run → exit 0, 7× "already measured". No re-measurement. `batched_overlap` stagger/validate remain **unmeasurable** until the bug is fixed (their calibration does not exist); `validate:sequential` is the one `sustained_ratio` that could be produced this batch.

**Exit-code semantics (observed):** all-stages main run = **1** (the `ValueError` above). validate slice = **0**. pool_sweep slice = **0**. (No exit 2/3/4 occurred; hygiene passed, no AC loss — n/a on Linux — and `REFM_LIVE=1` was set.)

### Per-stage wall (host-local/JST times, from `throwaway/b2-live-cuda*.log`; doc `started_utc`=09:10:32Z → `finished_utc`=10:22:45Z)

| Stage | window (host log) | wall |
|---|---|---|
| probe | 18:10:32 → 18:11:12 | ~40 s |
| numerics | 18:11:12 → 18:11:13 | ~1 s |
| grid (all variants, both contexts) | 18:11:13 → 18:54:22 | ~43 min (seq+overlap full; batched skipped) |
| stagger (seq+overlap; crashes at batched) | 18:54:22 → 19:04:57 | ~10 min measured, then crash |
| validate:sequential (slice) | 19:06:42 → 19:14:07 | ~7.4 min |
| pool_sweep:overlap ×7 (slice) | 19:18:44 → 19:22:45 | ~4 min |

All 42 measured runs `status=ok`; no run raised an exception. One intentional deadline abort: `pool_sweep:overlap:…:w4-c1-block` (`aborted=true`, 55/75 done) — the capacity-1 stress config hit the `abort_factor×30 s` deadline, expected for that probe.

### Hygiene outcome

Pre-first-run gate **passed attempt 1** (`start_abort` absent; `gpu_other_procs=0`). `polluted=false` on **all 42 runs** (every per-run `hygiene.violations` empty). Host load **12.25–20.02** recorded throughout (not enforced). GPU left clean afterwards: `0` compute apps, `15 MiB / 0 % / 8.49 W`; `pgrep -af run_refresh` empty. No stray processes.

> **Shared-host end-to-end numbers, not isolated GPU ceilings** (RV-B F3): the permanent
> tester-workload stress keeps the host CPU saturated (load 12–20, 14 cores), and the
> pipeline's **prep / arrival-gate coordination / Python-model dispatch / H2D-D2H and
> wakeup handling all run on that saturated host CPU** (`refresh_run.py` worker threads)
> — so "host CPU is otherwise idle" is **false**. The modelled fetch/chain sleeps are
> modelled latency, not zero CPU dependence. **[INFERENCE]** host-CPU contention tends to
> inflate measured service/wakeup times and lower sustainable capacity, and can change
> batching and the relative overlap gain; its magnitude/direction per ratio is unmeasured.
> All numbers here are shared-host end-to-end measurements, not isolated GPU ceilings.

### Probe (V=4, ctx=11520) — `b_star` & batching effectiveness

`b_star = 32` (cap 32), `min_gain 1.10`, **`batching_effective = True`**, `pods_per_s(B=1) = 2.585`. Peak GPU mem 5.1 GB at B=32 (24 GB card). Batching is clearly effective on CUDA (2.585 → 5.003 pods/s, ≈1.94× over B=1, ≫ 1.10) — the same `b_star=32` is what triggers the calibration bug above.

| B | ms/call (med of 2) | pods/s | peak MB |
|---|---|---|---|
| 1 | 386.8 | 2.585 | 1384 |
| 2 | 512.4 | 3.903 | 1508 |
| 4 | 946.4 | 4.227 | 1742 |
| 8 | 1733.4 | 4.615 | 2223 |
| 16 | 3231.0 | 4.952 | 3183 |
| 32 | 6396.7 | **5.003** | 5102 |

### Numerics (V=4, ctx=2880, 3 pods)

- `single_vs_batched`: `max_abs_diff = 32.0` on `ptp = 2.56e8` → **rel 1.25e-7** (`rel_per_variate_max 1.63e-6`). Batching along the batch axis is numerically independent per pod on CUDA torch (expected ~float-noise; not bit-exact like CPU's 0.0, but negligible vs the signal ptp).
- `packed_vs_separate`: `max_abs_diff = 131760` (rel 5.15e-4, `rel_per_variate_max 0.0173`) — variate packing measurably mixes pods (confirms B1: packing is INVALID; not used in any pipeline).
- `backend_note`: "torch: one decode per chunk of per_core_batch_size (= number of pods in the call)".

### Knee table (per variant/context/budget, method from `knee.find_knee` on measured calibrate+grid points)

Pods at which `T(N)=a+s·N` crosses each budget. `interpolated` = measured points straddle the budget; `extrapolated_linear` = all measured ≤ budget (always flagged `extrapolated`).

| context | variant | 120 s | 180 s | 300 s (tick) | measured max N |
|---|---|---|---|---|---|
| 11520 | sequential | 176 (interp) | 264 (interp) | 438 (**extrap**) | 359 |
| 11520 | overlap | 292 (interp) | 442 (interp) | 733 (**extrap**) | 610 |
| 11520 | batched_overlap | — | — | — | **unmeasured (bug)** |
| 5760 | sequential | 309 (interp) | 463 (interp) | 772 (**extrap**) | 624 |
| 5760 | overlap | 538 (interp) | 810 (interp) | 1336 (**extrap**) | 1042 |
| 5760 | batched_overlap | — | — | — | **unmeasured (bug)** |

Fit lines (calibrate-only `a`,`s`): seq@11520 `0.048+0.668·N` (r²1.000); overlap@11520 `0.482+0.393·N` (r²1.000); seq@5760 `-0.036+0.385·N` (r²1.000); overlap@5760 `0.115+0.230·N` (r²1.000). (Full-grid `find_knee` uses all measured points; values above are from that.) Overlap ≈ **1.66–1.75×** more pods than sequential at equal budget (from the knee table: 733/438 @11520·300 s, 1336/772 @5760·300 s) — the **≈1.93×** figure above is the **accelerator-only probe** gain (B=32 vs B=1 pods/s, 5.003/2.585), a different quantity. (async buys a lot; its cost is queue depth / gate-wait, below.)

### Mean GPU board power & J/pod (scope = **gpu_board**, host CPU excluded)

**Mean total board power** and J/pod per (variant, context) over its measured runs (`idle` interpolated between the block's before/after baselines; idle baselines range 9.6–20.2 W, resident-model ≈ 18–20 W). The column is the **board mean `mean_w` (total), not the excess above idle** — the excess is `mean_w − idle_w` (e.g. sequential@11520 ≈ 39.1 − ≈18 ≈ 21 W mean excess). J/pod is the excess energy per pod per refresh pass.

| variant | ctx | mean board W (range, n) | mean J/pod (n resolved) |
|---|---|---|---|
| sequential | 11520 | 39.1 (34.4–40.8, 12) | 16.2 (11) |
| overlap | 11520 | 47.9 (37.2–50.9, 18) | 13.3 (18) |
| batched_overlap | 11520 | 64.0 (n=1, calibrate) | 9.95 (1) |
| sequential | 5760 | 36.5 (31.6–38.0, 5) | 7.0 (4) |
| overlap | 5760 | 44.2 (34.0–47.9, 5) | 5.8 (5) |
| batched_overlap | 5760 | 55.3 (n=1, calibrate) | 3.93 (1) |

Note: J/pod here is **per refresh pass** (excess energy ÷ pods), not per inference; it grows with context and, for sequential, with load (more idle between the serial calls is *not* free board power). All runs `resolved=true` except `calibrate:sequential:ctx5760:n10` (3.8 s pass, below resolution — expected for a <10 s pass on a coarse 250 ms sampler).

### Queue-depth / backpressure summary

- **sequential**: single-thread ⇒ queue depth ≡ 1, `gate_wait` = the serial fetch-queue wait (grows linearly with N; p95 ≈ 0.77×N·0.668 s at N=359 → 233 s). No concurrency benefit.
- **overlap (4 workers, cap 8, block)**: queue depth pinned at **7** (cap−1) and mean depth ≈ 6.0–6.3 once N > ~2×cap; `gate_wait p95` ≈ 2.5–2.7 s (arrivals wait outside the pipeline when the gate is full). Accelerator `busy_frac` → 0.999 (GPU saturated). At N=610@11520 the pass still finishes in 250 s (accelerator-bound, not queue-bound).
- **stagger (stratified arrivals, ctx=11520)**: **saturation onset is already at ρ=1.1** — the end-of-window backlog is `12/99 = 12.12 %` sequential and `22/168 = 13.10 %` overlap, **both above the 5 % threshold**; the **first tested threshold crossing is 1.1, not 1.4** (`build_table` interpolates `rho* ≈ 0.969` for both variants). At **ρ=1.4** the unbounded-growth signal is far beyond the threshold — `backlog.at_window_end = 39/126 (seq, 0.31)` and `68/214 (overlap, 0.318)` end-frac, both ≫ the 0.05 threshold ⇒ at ρ=1.4 the 60 s window does not drain (the scale-invariant pod count for the 300 s tick is confirmed by the validate run).
- **pool_sweep (overlap, N=75@11520)**: production `w4-c8-block` refresh 29.7 s; `w4-c8-drop` **drops 67/75 (0.89 frac)** — in this **simultaneous-burst admission experiment** (all 75 pods arrive at t=0, `on_full:drop` = the production admission policy) only 8 are admitted (= capacity 8), then all the rest are skipped, never blocked; the **89 % drop is the fraction lost by that admission policy under this burst overload, not a production steady-state loss rate** (arrivals here are a modelled burst, not the real 300 s tick arrival pattern). `w4-c1-block` aborts at the deadline (55/75). `w4-c32-block`/`w16-c32-block` let depth run to 31 (mean 22.6/23.8) with wait p95 ≈ 12.4–12.7 s but complete; `w4-cinf-block` depth to 62 (mean 30.8), wait p95 23.1 s. So at N=75 the bottleneck is the single GPU (all block configs ≈ 30 s); drop is the only one that "completes fast" — by discarding work.

### Sustained run (`sustained_ratio`)

`validations` (only entry this batch — batched blocked by the bug):
- **sequential, ctx=11520, ρ=1.3, N=584, window 300 s, drain cap 150 s**: `mu_hat = 1.497 pods/s`, `done_second_half = 218`, **`sustained_ratio = 0.971`**, refresh 399.1 s, aborted=false, 584/584 done. The sequential-only second-half throughput ratio of **0.971** does **not** by itself prove "no thermal drop-off," independently validate every variant/context, or establish that all 300 s PASS knees are trustworthy — there is no retained per-run temperature history and no control experiment isolating thermal settling from the other effects. What it does show: this single sustained sequential@11520 run held ≈1× throughput in the second half (≈3 % drop, consistent with but not proof of thermal stability). The 300 s-tick throughput is confirmed at ρ=1.3 **for sequential@11520 only**; the extrapolated 300 s knees remain extrapolations. `pods_adjusted` in the finalize table ≈ floor(pods·0.971) **for sequential** (other variants have no validation entry).

### Polluted / aborted / dropped runs

- **Polluted: none** (42/42 `polluted=false`, empty violations).
- **Errors: none** (all 42 `status=ok`).
- **Aborted (intentional deadline):** 1 — `pool_sweep:overlap:ctx11520:n75:w4-c1-block` (capacity-1 stress; 55/75 done).
- **Dropped (production `on_full:drop`):** 67/75 in `pool_sweep:overlap:ctx11520:n75:w4-c8-drop` (by design of that policy).
- **Not measured (script bug, see above):** batched_overlap grid/stagger/validate at both contexts.

### Housekeeping

- Final `results/b2-refresh-cuda.json` copied host → Mac (`rsync -a rtx-4000-test:refm-lab/…/results/b2-refresh-cuda.json $LAB/…/results/`, rc 0; md5 `1ec53a73…` matches the host source; 42 runs, 20 idle baselines, 1 validation). `git check-ignore -v results/b2-refresh-cuda.json` → rc=1 (tracked).
- `scripts/plot_refresh.py` **not run**: the card's finalize pass (figures / b2-sustainable / b2-headline) is explicitly deferred; the four device JSONs are just kept.
- Host left clean (0 compute apps, GPU idle, no stray `run_refresh` processes). Host venv + weights retained for the Mac-device batches (M2).
