# E Live — SOLO-REFM / B1 LIVE BATCH (live-openai workers)

Date: 2026-11-09. This file records the LIVE BATCH runs (L0/L2 CUDA here; Mac devices appended later by their worker). No code edits were made by the live workers; a script defect was found (below) and is returned to the Executor — no gate was loosened by the workers.

## CUDA (worker RefmLiveB1cuda)

Scope executed: **L0 (CUDA host setup)** and **L2 (CUDA scaling run + `--flopcount-cuda`)**. L1 (Mac cpu/mps/mlx) is a separate batch and was NOT done. Corrections from E-B1.md §6 applied as instructed (pre-rsync `mkdir -p throwaway results`; weights dir copied + sha256-verified on the host).

### L0 — host setup (all steps passed)

| Step | Command | Result |
|---|---|---|
| (a) GPU idle check | `ssh rtx-4000-test 'nvidia-smi --query-gpu=name,memory.used,utilization.gpu --format=csv,noheader; nvidia-smi --query-compute-apps=pid --format=csv,noheader \| wc -l'` | `NVIDIA RTX PRO 4000 Blackwell SFF Edition, 15 MiB, 0 %` · apps `0` → GO |
| host facts (recorded) | `nvidia-smi --query-gpu=name,driver_version,memory.total,power.limit,clocks.max.sm --format=csv` | `NVIDIA RTX PRO 4000 Blackwell SFF Edition, 595.99.02, 24467 MiB, 70.00 W, 3090 MHz` |
| (b0) E-B1 §6 correction | `ssh rtx-4000-test 'mkdir -p ~/refm-lab/reference-model-study/throwaway ~/refm-lab/reference-model-study/results'` | ok |
| (b) study rsync | `rsync -a --exclude .venv --exclude artifacts --exclude throwaway --exclude __pycache__ --exclude .pytest_cache --exclude .ruff_cache --exclude data/raw/oracle --exclude data/raw/p3 $LAB/reference-model-study/ rtx-4000-test:refm-lab/reference-model-study/` | 219 files (42 MB), rc 0 |
| (c) venv + install | `uv venv --python 3.12 .venv && nice -n 19 uv pip install --python .venv/bin/python -e ".[dev,timesfm]"` | CPython 3.12.14; **torch 2.15.0+cu132** (default PyPI wheel — no cu128 fallback needed); install rc 0 |
| weights copy | `rsync -a --exclude .cache $LAB/reference-model-study/artifacts/timesfm3/ rtx-4000-test:refm-lab/reference-model-study/artifacts/timesfm3/` (config.json + model.safetensors 1,322,898,824 B; 215 s) | host `sha256sum model.safetensors` = `a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da` = expected (also verified on the Mac before the copy) |
| (c2) checkpoint verify | `.venv/bin/python scripts/fetch_timesfm3.py --config config/timesfm3.yaml --verify-only` | rc 0: `checkpoint verified: model.safetensors (1322898824 bytes, 330710976 params)`; manifest → `results/a2-model-manifest.json` (host). Used `--verify-only` because the card's fetch step downloads from HF (~1.3 GB re-download, redundant: weights already copied from the operator's own Mac copy and sha256-verified). |
| (d) arch + matmul | `.venv/bin/python -c "import torch;print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0), torch.cuda.get_arch_list())"` | `2.15.0+cu132 13.2 True NVIDIA RTX PRO 4000 Blackwell SFF Edition ['sm_75', 'sm_80', 'sm_86', 'sm_90', 'sm_100', 'sm_120']` — **sm_120 present**. Tiny matmul on `cuda` ok (`(a@b).sum()` on 64×64 randn, `torch.cuda.synchronize()`); capability `(12, 0)`. Defaults recorded: `float32_matmul_precision=highest`, `cuda_matmul_allow_tf32=False`, `cudnn_allow_tf32=True` (fp32 only, per card §3). |

L0 left in place for B2: host venv (`~/refm-lab/reference-model-study/.venv`), copied weights + manifest under `~/refm-lab/` (private research copy, same operator's own machine — not uploaded anywhere else).

### L2 — CUDA scaling run: **BLOCKED at start hygiene gate (exit 2) — script bug returned to Executor**

Commands (per card): `rsync -a $LAB/.../results/b1-flopcount.json rtx-4000-test:refm-lab/reference-model-study/results/` (rc 0), then the card's exact launch:
`ssh rtx-4000-test 'cd ~/refm-lab/reference-model-study && REFM_LIVE=1 PYTHONUNBUFFERED=1 nohup .venv/bin/python scripts/run_scaling.py --config config/compute_scaling.yaml --device cuda > throwaway/b1-live-cuda.log 2>&1 &'`

Outcome: model loaded on cuda:0 (1 s), then the pre-first-cell gate aborted after 4 attempts × 20 s → **exit 2**, `cells: []` (nothing measured). Verbatim from `throwaway/b1-live-cuda.log` (host):

```
2026-11-09 16:08:24.684 | WARNING  | refstudy.compute.scaling:_gate:166 - hygiene violations (attempt 1): ['gpu other processes 1 > 0']
2026-11-09 16:08:44.734 | WARNING  | refstudy.compute.scaling:_gate:166 - hygiene violations (attempt 2): ['gpu other processes 1 > 0']
2026-11-09 16:09:04.782 | WARNING  | refstudy.compute.scaling:_gate:166 - hygiene violations (attempt 3): ['gpu other processes 1 > 0']
2026-11-09 16:09:24.831 | WARNING  | refstudy.compute.scaling:_gate:166 - hygiene violations (attempt 4): ['gpu other processes 1 > 0']
2026-11-09 16:09:24.832 | ERROR    | refstudy.compute.scaling:run_device:331 - hygiene abort before the first cell: ['gpu other processes 1 > 0']; top processes: stress-ng-vm ×10 @ ~59.7%, stress-ng-cpu ×20 @ ~19.9% (the permanent CPU-only tester-workload stress), then cluster daemons (kubelet/kube-apiserver/greptime/...)
```

**Root cause (worker-verified, deterministic): the gate counts OUR OWN process as a "GPU other process".**
1. `run_scaling.main()` calls `load_device(settings, "cuda", dcfg)` **before** `run_device(...)`; `load_device` → `TimesFM3Forecaster.from_pretrained(..., device="cuda:0")` opens a CUDA context in our own PID.
2. `hygiene.snapshot()` excludes the own process tree from the `top` CPU probe (`_own_tree` + `parse_top(exclude)`) but **not** from the `nvidia-smi --query-compute-apps=pid` probe (`gpu_other_procs = len(lines)`), so our PID is counted. With profile `cuda_host.gpu_other_procs_max: 0`, `check()` reports `gpu other processes 1 > 0` on every attempt → exit 2. A CUDA timing run can therefore **never** pass its own start gate.
3. Proof (controlled, host): with the GPU idle `nvidia-smi --query-compute-apps=pid | wc -l` → `0`; while a minimal python holding only a cuda context (loaded model, sleeping) was alive → exactly `2279589, .venv/bin/python` = its own PID; after killing it → `0` again.
4. No external tenant exists: the L0 pre-check showed 0 apps; the only GPU-visible process during the run was our own.

The abort is stored in the result file (`start_abort.snapshot/violations`; recorded `load: [12.55, 14.16, 14.07]`, `gpu_other_procs: 1`).

**Card fallback attempted (re-run the identical command):** relaunched the same card command (`> throwaway/b1-live-cuda-rerun.log`) → **same abort**, exit 2, `cells: []`. Verbatim tail:
```
2026-11-09 16:18:18.728 | WARNING  | refstudy.compute.scaling:_gate:166 - hygiene violations (attempt 4): ['gpu other processes 1 > 0']
2026-11-09 16:18:18.728 | ERROR    | refstudy.compute.scaling:run_device:331 - hygiene abort before the first cell: ['gpu other processes 1 > 0']; ...
```
This proves the abort is **deterministic** (not a transient tenant / load spike): the "other process" is our own, so no amount of re-running clears it. **This is returned to the Executor, not fixed here** (no code edits by live workers; loosening `gpu_other_procs_max` would also be a gate change, which is S's/E's decision). Suggested minimal fix for E: in `hygiene.snapshot`, exclude `own_pid` (and the own tree) from the nvidia-smi compute-apps line count — symmetric with the `top` exclusion.

### L2 — `--flopcount-cuda` follow-up (completed, exit 0)

Explicitly in this batch's assignment and not blocked by the gate (this path runs `count_cells` after model load; no hygiene gate). Card command with `--flopcount-cuda` appended:
`REFM_LIVE=1 PYTHONUNBUFFERED=1 .venv/bin/python scripts/run_scaling.py --config config/compute_scaling.yaml --device cuda --flopcount-cuda` → **rc 0** (8.5 s). Verbatim:

```
flopcount n=240 v=3: 23.855 GF measured / 23.866 GF analytic
flopcount n=5760 v=3: 375.494 GF measured / 375.675 GF analytic
flopcount n=11520 v=3: 762.953 GF measured / 763.311 GF analytic
flopcount_cuda merged into results/b1-scaling-cuda.json: ratio_to_cpu 1.00000..1.00000
```

3 check cells counted on cuda; merged atomically into `results/b1-scaling-cuda.json` as `flopcount_cuda` (torch `2.15.0+cu132`); `ratio_to_cpu` = **1.00000** (min=max; well within the expected 1 %) → device-independence of the FLOP count confirmed on the GPU. SDPA op counted as `aten._scaled_dot_product_efficient_attention` on cuda (vs `..._for_cpu` on CPU); matmul ops `aten.mm/bmm/addmm` as on CPU.

### Results, versions, housekeeping

- `results/b1-scaling-cuda.json` copied back to the Mac lab `results/` (rsync rc 0) and **committed as `d0e6163`** `chore(refstudy): record B1 CUDA scaling measurements` (explicit `git add` of that one file only; `git diff --check` clean; no push, no trailers). It currently holds: `runtime` (torch 2.15.0+cu132, CUDA 13.2, arch list incl. `sm_120`, capability (12,0), fp32 defaults above), `flopcount_cuda` (3 cells, ratio_to_cpu 1.00000), `cells: []` + `start_abort` (the gate abort — retained verbatim in the record).
- **Timing cells: 0 measured (blocked, see above). No latency/GFLOP-s/peak-memory/energy numbers exist for CUDA yet.** Idle baselines: none taken (run aborted before any cell; pre-run GPU idle = 15 MiB / 0 % util / 8.39 W / 34–35 °C). `external_connected_start`: null (n/a on the Linux host; `require_ac` false for `cuda_host`). Polluted cells: none (no cell ran). Parity: not computed (after-last-cell step not reached).
- Host left clean: `pgrep -af run_scaling` empty (only the pgrep's own shell matches the pattern), `nvidia-smi` = 0 compute apps, 15 MiB / 0 % / 8.39 W. Host venv + weights intentionally kept for B2.
- Deviations: (1) fetch step run as `--verify-only` instead of a full HF download (weights pre-copied + sha256-verified; avoids a redundant 1.3 GB download and any HF egress of the non-commercial weights); (2) one launch attempt used a mistyped config path (`config/config.yaml`, worker typo) → immediate `ValueError: config file not found`, no result file written, killed nothing (it exited by itself), relaunched with the correct path; (3) the abort record in the result file is data, not a measurement — flag for E/S when the timing run lands.

**For the Executor/S:** to complete L2, fix the `gpu_other_procs` self-count (one-line exclusion in `hygiene.snapshot` + its test), resync the file to the host, and rerun the card's launch command — it resumes and measures all 36 cells + energy + parity; then rerun `--flopcount-cuda`-free (the flopcount merge is already present in the committed JSON; a rerun of the timing run keeps `flopcount_cuda` in the resumed doc).

---

## CUDA — L2 re-run (post-fix, worker RefmLiveB1cuda2, 2026-11-09 16:35–16:49 JST)

The `gpu_other_procs` self-count bug was fixed in the lab at **commit `76f4d1c`** (`hygiene.snapshot` now excludes the own PID + descendant tree from the `nvidia-smi --query-compute-apps=pid` count, symmetric with the `top` exclusion; `tests/test_compute_hygiene.py` extended, 17 tests green on the Mac). This batch re-ran **L2 (CUDA scaling timing)** per the card. **No code was edited by this worker; no gate threshold was loosened.** Outcome: the start hygiene gate **passed on attempt 1**, all 36 cells + 6 energy blocks + parity measured, exit 0. The prior BLOCKED result above is superseded (its `start_abort` record was auto-cleared by the passing gate on resume).

### L2 re-run — setup & run (all steps per card)

| Step | Command / note | Result |
|---|---|---|
| host pre-baseline | `nvidia-smi … --query-gpu=power.draw,clocks.sm,temperature.gpu,utilization.gpu,memory.used` + `--query-compute-apps=pid \| wc -l` | **8.32 W, 180 MHz, 34 °C, 0 % util, 15 MiB, 0 compute apps** (bare GPU, no resident process). Host `load average 15.41` = the permanent CPU-only stress workload (not enforced: `cuda_host` profile has `enforce_cpu:false`, `max_load1:null`). |
| sync code | `rsync -a --exclude .venv … --exclude data/raw/p3 $LAB/reference-model-study/ rtx-4000-test:refm-lab/reference-model-study/` | rc 0. Transferred the fix (`hygiene.py` md5 `448ed816…`, `grep -c "count_gpu_other_procs(text, tree)"` → 1) + A1a sibling files. **`results/b1-scaling-cuda.json` was NOT clobbered by the stale Mac copy**: the host copy (authoritative, mtime 16:18:18) was byte-identical to the Mac's committed `d0e6163` doc minus the in-file `start_abort`, and the Mac copy's mtime was aligned to the host's before rsync, so rsync skipped it. `results/b1-flopcount.json` confirmed identical (diff rc 0). No need to move the result aside — the runner resumed it in place (below). |
| launch | `ssh rtx-4000-test 'cd ~/refm-lab/reference-model-study && export PATH=/usr/local/cuda-13.2/bin:$PATH; export LD_LIBRARY_PATH=/usr/local/cuda-13.2/lib64:$LD_LIBRARY_PATH; REFM_LIVE=1 PYTHONUNBUFFERED=1 nohup .venv/bin/python scripts/run_scaling.py --config config/compute_scaling.yaml --device cuda > throwaway/b1-live-cuda-rerun2.log 2>&1 &'` (PID 2319396) | Resumed the existing `results/b1-scaling-cuda.json` (device=cuda, `cells: []`, old `start_abort` present). |
| start gate | pre-first-cell `snapshot/check` | **Passed, attempt 1** — `gpu_other_procs` now correctly excludes the own tree. `start_abort` auto-popped; `external_connected_start` = null (n/a on Linux; `require_ac` false). No other-GPU-process violation from other users. |
| run | 36 cells × (2 warmup + 15 timed) + 6 energy blocks (45 s window each) + post-run CPU parity | **exit 0**, `finished_utc = 2026-11-09T07:48:39+00:00` (≈13 min wall). No `ERROR`/`Traceback`/refusal lines in the log. |

Resume note: `run_device` reads the existing doc, keeps the intact `flopcount_cuda` block (ratio 1.0 from the earlier `--flopcount-cuda` merge, unchanged), fills `cells` 0→36, recomputes `parity`, and clears `start_abort`. **No re-run of `--flopcount-cuda` was needed** — the merged JSON already carried the `flopcount_cuda` block (3 check cells, `ratio_to_cpu` min=max = **1.0**).

### V=3 per-cell timing table (sanity: the 4 mark cells + the 17280 truncation cell)

GPU = RTX PRO 4000 (Blackwell, sm_120, cap 12.0); fp32 defaults (`float32_matmul_precision=highest`, `cuda_matmul_allow_tf32=False`, `cudnn_allow_tf32=True`), `torch_threads:1`. Median of 15 timed runs; GFLOP/s from the **measured** FLOP count; `flop_ratio` = measured/analytic on every cell = **0.9995**.

| N (pts) | days | median ms (p10–p90) | GFLOP/s (meas) | peak GPU mem (MB) | RSS HWM (MB) |
|---|---|---|---|---|---|
| 240 | 0.042 | 68.21 (66.45–73.18) | 349.8 | 1295.6 | 3176.5 |
| 5760 | 1.000 | 203.74 (199.99–209.62) | 1843.0 | 1326.1 | 3176.5 |
| 11520 | 2.000 | 324.82 (323.72–328.47) | 2348.8 | 1361.6 | 3176.5 |
| 15360 (cap) | 2.667 | 448.51 (446.87–454.80) | 2301.7 | 1407.0 | 3176.5 |
| **17280 (3-day truncation)** | 3.000 | 458.53 (449.18–464.76) | 2251.4 | 1407.0 | 3176.5 |

**Truncation plateau confirmed:** 17280-point cell costs essentially the 15360-point (max-context) cost — median ratio 17280/15360 = **1.0223** (V3), and 1.0093 (V1) / 1.0190 (V4). Peak GPU memory is identical at 1407.0 MB for N=15360 and N=17280 (V3) — history beyond the 15360 context cap is truncated, not reprocessed.

Full-grid achieved GFLOP/s (measured) across all 36 cells: **56.1 – 3006.3** (tiny cells are launch/H2D-bound; the ~3000 GFLOP/s region is the large-N V4 cells). V3 median latency range: 68.2 ms (N=240) → 458.5 ms (N=17280). Overall median-range across all 36 cells: 64.8 – 513.7 ms. **Peak GPU memory (all cells): 1455.2 MB** (at N=15360, V4); V3 peaks 1294.6→1407.0 MB.

### Idle power baseline (GPU board, `nvidia-smi -lms 250` stream, host CPU excluded)

- **Bare GPU (no resident process), spot probes:** before run **8.32 W** (34 °C, 180 MHz), after run **8.48 W** (37 °C, 180 MHz).
- **Resident-model idle (in-run 20 s `idle_at` blocks, model loaded on cuda:0):** these are the baselines the energy computation actually subtracts. Per energy cell, `before`/`after` 20 s means: **15.44 / 16.02 W** (N=240), 17.53 / 18.60 W (N=11520,V1), 19.45 / 19.24 W (N=5760), 18.42 / 18.92 W (N=11520,V3), 18.78 / 19.23 W (N=11520,V4), 19.09 / 19.34 W (N=15360). std 2.6–10.7 W, n=80 each, `n_dropped=0`. The ~7 W gap vs the bare-GPU 8.3–8.5 W is a **measured observation** of elevated board power with the model resident; **attributing its entire gap solely to the resident CUDA context (the always-alive python process holding the 1.3 GB model on the device) is an [INFERENCE]** — DVFS/clock and thermal settling are not separated out, and part of the gap may be non-context overhead. (That inference is exactly why the card uses before/after in-run idles rather than the cold idle.)

### Energy-per-call cells (back-to-back 45 s loop window − resident-model idle; all `resolved=true`, `n_dropped=0`)

- **Energy-per-call cells** below report the **mean** board power over each back-to-back 45 s loop window (the `mean W` column), **not a measured peak** — `power.py` retains only the window mean/energy integral, not per-sample peaks, so "~50 W" is a window **mean**.

| N | V | mean W | idle W | excess W | **J/call** | J/GFLOP | n_calls |
|---|---|---|---|---|---|---|---|
| 240 | 3 | 27.77 | 15.77 | 12.00 | **0.924** | 0.0387 | 584 |
| 5760 | 3 | 46.41 | 19.33 | 27.08 | **5.389** | 0.0144 | 226 |
| 11520 | 1 | 40.86 | 18.14 | 22.72 | **6.222** | 0.0245 | 164 |
| 11520 | 3 | 46.69 | 18.70 | 27.99 | **9.201** | 0.0121 | 136 |
| 11520 | 4 | 50.06 | 19.03 | 31.03 | **12.277** | 0.0121 | 114 |
| 15360 | 3 | 49.55 | 19.23 | 30.32 | **13.784** | 0.0134 | 99 |

Scope label on every figure must be **GPU board power only (host CPU excluded)**. `min_resolvable_w=1.0`, `resolution_k=2.0`; all excesses ≫ 1 W → all resolved.

### Polluted cells, hygiene, parity

- **Polluted cells: none** (`polluted=false` on all 36; every per-cell `hygiene.violations` empty). No AC-loss mid-run (n/a, Linux host).
- **Parity (post-last-cell, cuda vs a second CPU forecaster, threads=1): `status=ok`** — max-quantile abs diff ~5.7e-6, max-median abs diff ~2.9e-6 at N=240 (fp32 GPU-vs-CPU agreement at float-noise level). **Thread-count correction (RV-B F6):** the earlier "threads=6" was wrong — `run_scaling.py:109–113` keeps the CUDA device's **own 1-thread budget** for the CPU parity forecaster (`torch_threads=dcfg.torch_threads` = 1 for cuda), not the CPU device's 6-thread config.
- **FLOP device-independence:** `flopcount_cuda` re-count (N=240/5760/11520, V=3, on cuda) vs CPU count → `ratio_to_cpu` min=max = **1.0** (measured GF 23.855 / 375.494 / 762.953). SDPA op on cuda = `aten._scaled_dot_product_efficient_attention`; matmuls `aten.mm/bmm/addmm` as on CPU.

### nvidia-smi clocks/temps summary

- Idle (bare): **180 MHz, 34→37 °C, 8.3–8.5 W**.
- Active (spot mid-run, N≈240 cells): SM clock ~**1515 MHz**, ~40 °C, ~27 W (GPU util low single-digit % — the small calls are host/launch-bound; the board is mostly idle between short kernels). Peak power draw observed during the 45 s energy loops ≈ 50 W (mean W in the energy table), well under the 70 W limit.
- Post-run: **180 MHz, 37 °C, 8.48 W, 15 MiB, 0 % util** — returned to idle.
- Note: `power.py` stores only watts in the energy record (SM clock/temperature are parsed by the sampler but not retained per cell); the clock/temperature figures above are from discrete `nvidia-smi` spot probes, not the 250 ms stream.

### Results, versions, housekeeping (re-run)

- `results/b1-scaling-cuda.json` (host) now holds: `runtime` (torch 2.15.0+cu132, CUDA 13.2, arch list incl. `sm_120`, cap (12,0), fp32 defaults above), **`cells`: 36 (all `status=ok`)**, `flopcount_cuda` (3 cells, ratio_to_cpu 1.0), `parity` (ok), `idle_baselines` (12 blocks), `started_utc`/`finished_utc` set, `start_abort` cleared. Copied back to the Mac lab `results/` (rsync rc 0).
- **All 36 timing cells measured** (this run); 6 energy cells resolved; 0 polluted; exit 0.
- **Host left clean:** `pgrep -af run_scaling` → none; `nvidia-smi --query-compute-apps` → 0 compute apps; GPU at 15 MiB / 0 % / 8.48 W. No stray processes. Host venv + weights retained for B2.
- **Commit:** ONLY `results/b1-scaling-cuda.json` staged (explicit `git add`), no push, no trailers, `git diff --check` clean — see commit hash in the worker's final report.
- Deviations this run: (1) launch log written to a fresh file `throwaway/b1-live-cuda-rerun2.log` (not overwriting the two earlier attempt logs, which are kept as history); (2) `LD_LIBRARY_PATH`/`PATH` exported inline per the D7 environment fact (non-interactive ssh does not source `~/.bashrc`); (3) no `--flopcount-cuda` re-run was required (merged block already present and valid — verified, not re-generated).
