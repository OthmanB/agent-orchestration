# E Completion — SOLO-REFM / B1 (stage 1: library + CPU FLOP count + CPU smoke; commit 1)

- Date: 2026-11-09. Executor: RefmEB1s1b (S-approved session-only fallback model). Lab: `/Users/obenomar/Work/langGraph/appthrust/pipelineml-model-exploratory-work`, study dir `reference-model-study/`, `PY=.venv/bin/python`.
- Scope: stage 1 only. LIVE BATCH (L0–L2) and stage 2 (plots/read-off/note, commit 2) NOT done. No GPU device run, no host work, no cluster access.

## 1. Changed files (commit 1 = `3515abf`, 19 files, +3544; only owned paths)

| Path | Summary |
|---|---|
| `config/compute_scaling.yaml` | all tunables exactly as the card (grid, timing, flopcount, energy, power sources, hygiene profiles, devices, readoff, outputs, `smoke:` block); one smoke addition, see §5 D1 |
| `src/refstudy/compute/{__init__,config}.py` | frozen dataclasses, `load_compute_config(path, *, smoke)`, `load_shared(path)` (B2 reuse), validation per card |
| `.../devices.py` | `load_device`, `describe_runtime`, `reset_peak`, `peak_mb` (never raise) |
| `.../power.py` | `parse_ioreg`, `parse_nvidia_csv`, `PowerSampler` (poll/stream), `window_stats`, `integrate_energy`, `idle_at`, `energy_record` |
| `.../hygiene.py` | `parse_uptime`, `parse_top`, `snapshot`, `check` |
| `.../flopcount.py` | `count_flops`, `count_cells`, `run_flopcount`, `load_flopcount_doc` |
| `.../scaling.py` | `cell_grid`, `cell_key`, `write_atomic`, `load_resume`, `time_cell`, `derive_cell`, `run_device`, `merge_flopcount_cuda`, `Hooks` (test seams) |
| `.../readoff.py` | `readoff(docs, cfg)`, `attention_share` (used by stage 2) |
| `scripts/run_scaling.py`, `scripts/plot_scaling.py` | CLIs per card (refusals exit 4) |
| `tests/test_compute_{config,power,hygiene,flopcount,scaling,readoff,plot_scaling}.py` | 77 deterministic CPU tests |
| `results/b1-flopcount.json` | real CPU measured FLOP count, 36 cells |

Not modified: any A2/A1a/A3 file, `pyproject.toml`, `.gitignore`. A1a's own commit `b588eb6` landed between my preflight and my commit (not mine, not touched).

## 2. Commands and results

Preflight: `git -C $LAB status --short` → only A1a untracked files (`reference-model-study/config/reference.yaml`, `src/refstudy/reference/`, `tests/test_reference_blocks.py`, `tests/test_reference_config.py`). `$PY -c "import torch,mlx.core;print(torch.__version__)"` → `2.15.0`. `df -h / | tail -1` → `/dev/disk3s1s1 461G 421G 40G 92% /`. Hardware: Mac14,9 (M2 Pro).

Tests/lint (final): `$PY -m pytest tests/test_compute_*.py -rs` → `77 passed in 5.24s` (0 skipped, 0 failed).
`.venv/bin/ruff check src/refstudy/compute scripts/run_scaling.py scripts/plot_scaling.py tests/test_compute_*.py` → `All checks passed!`.
`grep -rn "print(" src/refstudy/compute scripts/run_scaling.py scripts/plot_scaling.py` → no output (rc=1).

Refusals (REFM_LIVE unset), exit code 4 each:
```
--device mps --smoke   : REFUSED: --device mps is a live batch; set REFM_LIVE=1
--device cuda          : REFUSED: --device cuda is a live batch; set REFM_LIVE=1
--device cpu (no smoke): REFUSED: a non-smoke timing run is a live batch; set REFM_LIVE=1 (or use --smoke)
--device mlx --flopcount-only : --flopcount-only is CPU-only (use --device cpu)
--device cpu --flopcount-cuda : --flopcount-cuda needs --device cuda
```

## 3. FLOP count (step 3) — `$PY scripts/run_scaling.py --config config/compute_scaling.yaml --device cpu --flopcount-only` (79 s, rc 0)

- torch 2.15.0, CPU, 4 threads, H=120, 36 cells (12 N × V∈{1,3,4}); `by_op` seen: `aten._scaled_dot_product_flash_attention_for_cpu`, `aten.addmm`, `aten.bmm`, `aten.mm` (`sdpa_counted: true`).
- measured/analytic ratio: **min 0.9995055, max 0.9995397** (every cell inside the expected 0.9995±0.002; no cell outside [0.98, 1.02] — outlier list empty).
- Truncation: `measured(17280) == measured(15360)` exactly (ratio 1.0) for V=1, 3, 4 (344.007 / 1032.319 / 1376.623 GF).
- Spot values: (240,V3) 23.855/23.866 GF; (2880,V3) 189.230/189.322; (5760,V1) 125.127/125.187 — identical to P's.
- Acceptance 2 one-off: `len(cells)==36`, `sdpa_counted` true, all `gflop_measured>0` → asserted OK.

## 4. CPU smoke (step 4)

`$PY scripts/run_scaling.py --config config/compute_scaling.yaml --device cpu --smoke --out throwaway/b1-smoke-cpu.json` (rc 0, ≈15 s). Cells in order (ascending n·v): `n240-v1, n480-v1, n240-v3, n480-v3`; median ms 101.8 / 101.7 / 155.3 / 136.8 (smoke, 2 runs, not a measurement); `polluted` false; `energy` null; `parity` null; `external_connected_start` true.
Rerun, same command → `4 cells already completed, skipped: ['n240-v1', 'n480-v1', 'n240-v3', 'n480-v3']`, rc 0, `cells` list byte-identical to the first run (compared: True).
Doc top-level keys: `schema_version, device, backend, host, versions, runtime, hygiene_profile, power, external_connected_start, parity, idle_baselines, cells, started_utc, finished_utc`. Cell keys: `key,n,v,days_nominal,status,gflop_analytic,gflop_measured,flop_ratio,runs_ms,median_ms,p10_ms,p90_ms,min_ms,max_ms,gflops_s_measured,gflops_s_analytic,rss_hwm_mb,device_peak_mb,polluted,hygiene,energy`. Runtime block: torch `float32_matmul_precision=highest`, `cuda_matmul_allow_tf32=False`, `cudnn_allow_tf32=True`, num_threads 6; versions timesfm 3.0.2, torch 2.15.0, mlx 0.32.4, numpy 2.5.4.
`$PY scripts/plot_scaling.py --config config/compute_scaling.yaml --results-dir throwaway --out-dir throwaway` → rc 0; wrote `throwaway/b1-scaling.png` (171 KB), `b1-energy-memory.png` (105 KB), `b1-readoff.json` (figure viewed: 3 panels, days twin-axis, marks, V legend OK).
Acceptance 4: `git check-ignore -v results/b1-flopcount.json` → rc=1 (not ignored); `git diff --cached --check` clean; commit shows only the 19 owned paths.

**First smoke attempt (verbatim, before D1 below):** with the card's smoke block, the Mac hygiene gate aborted at batch start, exit 2, nothing measured (4 retries × 20 s):
`hygiene violations (attempt 4): ['load1 2.21 > max_load1 2.00', 'other process WindowServer (pid 617) cpu 39.8% > 15.0%', 'other process com.apple.Safari (pid 59277) cpu 15.3% > 15.0%']` — top list: WindowServer 39.8, Safari 15.3, iTerm2 13.2, kernel_task 11.1, cli.js 7.1 … (Docker Desktop 18.0 on attempt 3).

## 5. Deviations from the card (all judgment calls; none loosens a gate of the LIVE config)

- **D1 — YAML change (`smoke:` block gained a `hygiene:` entry).** Card says the smoke needs no REFM_LIVE and runs ≈20 s, but the card's own hygiene gate (applied to every run) aborts on this shared, desktop-busy Mac (see §4). Added to the smoke block only: `hygiene.profiles.mac: {enforce_cpu: false, require_ac: false, max_retries: 0}` and `cuda_host: {max_retries: 0}`. The base (live) thresholds are unchanged; a test asserts the live profile is still `enforce_cpu true, require_ac true, max_retries 3` and another that the smoke merge relaxes only these keys. Smoke additionally redirects `outputs.scaling` to `throwaway/b1-smoke-{device}.json` (so a smoke can never overwrite `results/`) and `timing.runs` applies to every device (instead of `runs_by_device`).
- **D2 — AC probe.** `snapshot` probes `ExternalConnected` on any darwin host (not only when `require_ac`), so `external_connected_start` is recorded in smoke too. Enforcement stays tied to `require_ac`.
- **D3 — parity timing.** For non-cpu devices parity is computed once AFTER the last timed cell (a second CPU model in RAM would inflate the RSS high-water mark of the cells). CPU reference for cuda parity uses the cuda profile's `torch_threads` (1), for mps 6, for mlx the cpu profile (6). Skipped when the resume file already holds parity.
- **D4 — `peak_mb` semantics.** mps has no peak API → `torch.mps.driver_allocated_memory()` (current driver allocation, not a peak), as the card says; mlx `mx.get_peak_memory` (fallback `mx.metal.*`) and cuda `max_memory_allocated` are implemented but UNEXERCISED here (no GPU run). cpu → `None` (observed in smoke).
- **D5 — numpy API.** Trapezoid is `np.sum(0.5*(w[1:]+w[:-1])*np.diff(t))` rather than `np.trapezoid` (name differs across numpy versions; host numpy may differ). Same value (tests: 50 J exact).
- **D6 — extras not in the card (small):** energy records carry `n_dropped`; `idle_baselines` entries carry `cell` and `phase` (`before|after`); a failing energy block is stored as `{"error": ...}` without discarding the cell's timing; a failing cell is stored `status: "error"` (resume re-runs it, exit 1); a start-gate abort is stored in the file as `start_abort`. The energy loop keeps the device busy (uncounted calls) until the sampler has a sample after the window end, so the trapezoid integral is bracketed.
- **D7 — `top`/`ps` formats:** macOS `top -l 2 ... -stats pid,command,cpu` parsed as the last block; command with spaces handled (`Google Chrome H`, `Docker Desktop`); no format surprise. Linux `ps -eo pid=,pcpu=,comm=` parser covered by a fixture only (not run on the host).
- The card's literal `$PY -m pytest ...` was run as `.venv/bin/python -m pytest`; no other deviation.

## 6. What the LIVE worker needs (for S to dispatch; exact, in order)

Env facts discovered that S must weigh BEFORE dispatching L1:
1. **Mac hygiene gate will likely exit 2 on L1** unless the Mac is quiet: right now `WindowServer` alone sits at ~38–44 % (card threshold `max_other_cpu_pct 15.0`) and load1 ≈ 2.2–3.2 (threshold 2.0); also Safari / Docker Desktop / iTerm2 hover 13–18 %. The gate does not exempt WindowServer. S options: have the operator quiet the machine (close Safari/Docker Desktop, let the display sleep/lock screen, pause A1a runs) or amend `hygiene.profiles.mac.max_other_cpu_pct` in YAML (my call? no — a gate loosening is S's decision; E only recorded it). Exit 2 stores the full top-process list in `start_abort` of the result file; rerun resumes.
2. The Mac was on AC at my runs (`ExternalConnected = Yes`, `SystemLoad` ≈ 10.4 W at idle sample); card said battery at planning — S re-check at dispatch.
3. `throwaway/` is excluded by the L0 rsync, so the host command `... > throwaway/b1-live-cuda.log` fails unless the dir exists: **add to L0: `ssh rtx-4000-test 'mkdir -p ~/refm-lab/reference-model-study/throwaway ~/refm-lab/reference-model-study/results'`** (the `results/` dir arrives via rsync; the flopcount JSON copy in L2 needs it).

Commands (unchanged from the card; verified to exist/parse):
- **L0** per card (a)–(d). Weights: `scripts/fetch_timesfm3.py --config config/timesfm3.yaml` (A2). Add the `mkdir -p throwaway` above.
- **L1** per device d ∈ cpu, mps, mlx (cpu first): `cd $LAB/reference-model-study; REFM_LIVE=1 PYTHONUNBUFFERED=1 timeout 3000 .venv/bin/python scripts/run_scaling.py --config config/compute_scaling.yaml --device <d> 2>&1 | tee throwaway/b1-live-<d>.log` → `results/b1-scaling-<d>.json`. Needs `results/b1-flopcount.json` (committed in `3515abf`). Exit codes: 0 ok, 1 a cell errored (file kept; rerun re-runs only non-ok cells), 2 hygiene/AC abort at start, 3 AC lost mid-run, 4 refused (REFM_LIVE unset). Parity for mps/mlx is appended after the last cell (a second CPU model is loaded then; ≈1.3 GB + 3 CPU forecasts incl. N=5760,V=3 — a few minutes on the Mac).
- **L2** per card: `rsync -a $LAB/reference-model-study/results/b1-flopcount.json rtx-4000-test:refm-lab/reference-model-study/results/`; `ssh rtx-4000-test 'cd ~/refm-lab/reference-model-study && REFM_LIVE=1 PYTHONUNBUFFERED=1 nohup .venv/bin/python scripts/run_scaling.py --config config/compute_scaling.yaml --device cuda > throwaway/b1-live-cuda.log 2>&1 &'`; after exit 0 rerun the same command with `--flopcount-cuda` appended (merges `flopcount_cuda` with `ratio_to_cpu`; refuses with exit 4 if `REFM_LIVE` unset or device ≠ cuda; errors "cuda result file missing" if the timing file does not exist yet). Collect `results/b1-scaling-cuda.json` back. Host hygiene profile `cuda_host`: load/CPU recorded not enforced; aborts (exit 2) only if another compute process holds the GPU (`nvidia-smi --query-compute-apps=pid` count > 0) — the card's L0(a) check should be repeated right before L2. `nvidia-smi` and `ps` must be on the non-login ssh PATH (`/usr/bin`, normally yes); the Python venv is self-contained (torch wheel carries its CUDA runtime).
- Single-cell debug on any device: append `--only n=240,v=3`.
- Files the worker writes (commit message from card): `results/b1-scaling-{cpu,mps,mlx,cuda}.json` + `evidence/E-reference-model-study/E-B1-live.md`; nothing else.
- Unexercised-until-live code paths (record any failure verbatim, send back to E): `peak_mb`/`reset_peak` for cuda/mlx, `PowerSampler` against real `nvidia-smi -lms 250` and `ioreg`, `describe_runtime` cuda block (`get_arch_list`), cuda model loading in `devices.load_device`, mlx/mps parity, `--flopcount-cuda`, Linux `ps` parser against the real host.

## 7. Not done
Live batch L0–L2, stage 2 (figures/read-off JSON/§1 note, commit 2) — as instructed. `markdown/phase-b-compute-study.md` not created (stage 2).

## Hygiene fix (RefmEB1fix)

- Live symptom: `hygiene violations: ['gpu other processes 1 > 0']`. `run_scaling` loads the model on cuda before the hygiene gate; `snapshot` excluded the own process tree from the `top` check but counted every `nvidia-smi --query-compute-apps=pid` row, so our own PID was counted as "other".
- Fix (`src/refstudy/compute/hygiene.py`): new `count_gpu_other_procs(text, exclude_pids)`; `snapshot` now passes the own process tree (`_own_tree(own_pid)`: own pid + descendants) to it. Rows that are not integer pids (e.g. `[N/A]`) cannot be attributed and still count as foreign. YAML threshold `gpu_other_procs_max` semantics unchanged ("other" processes).
- Mac path review: the `top`/`ps` check already excluded the own tree plus the probe child PID; no same-class bug there.
- Regression tests (`tests/test_compute_hygiene.py`): `test_count_gpu_other_procs_excludes_own_pids` (own+foreign -> 1, own only -> 0, empty -> 0, `[N/A]` -> 1) and `test_snapshot_gpu_count_excludes_own_pid` (stubbed nvidia-smi via monkeypatched `_GPU_APPS_ARGV`; own+foreign -> violation `gpu other processes 1 > 0`, own only -> clean).
- Checks: `pytest tests/test_compute_*.py -q` all passed; `ruff check src/refstudy/compute tests/test_compute_*.py` clean; `git diff --check` clean. (`ruff format --check` flags 10 pre-existing files incl. unchanged code; not applied.)
