# E-A2-live — SOLO-REFM / A2 LIVE BATCH (Apple MPS + MLX smoke, 2026-11-09)

Executor: live-test worker (`RefmLiveA2`), per the **LIVE BATCH SPEC** in `omp-workcards/refm-A2.md`
(steps 1–4) + S's addendum (sudo-free power sampler alongside each device run; MLX run even though
MPS passed, for Phase B characterisation of both Apple GPU routes).

## Environment

- `LAB=/Users/obenomar/Work/langGraph/appthrust/pipelineml-model-exploratory-work`, branch `main`.
  Pre-batch HEAD `2cadaf2` (A3 leaf E commits), study dir `reference-model-study/`, `PY=.venv/bin/python`.
- Apple M2 Pro (6 P-cores visible to torch + E-cores; `os_cpu_count=10` in the reports), 32 GiB, macOS arm64.
- Versions at run time: python 3.12.15, timesfm 3.0.2, torch 2.15.0 (`torch.backends.mps.is_available() == True`),
  numpy 2.5.4, huggingface_hub 2.4.0, safetensors 0.8.0; MLX added during the batch: `mlx 0.32.4` + `mlx-metal 0.32.4`.
- `PYTORCH_ENABLE_MPS_FALLBACK` unset (per spec, not set).
- **Deviation (environment):** spec says "laptop on AC"; the Mac was **on battery** throughout
  (`pmset -g batt`: "Now drawing from 'Battery Power'", 74 % → 72 % discharging, ~5 h remaining). No AC cable.
- **Deviation (concurrent load):** sibling agent `RefmEA3` was concurrently writing under
  `src/refstudy/data`, `scripts/package_flat_load.py`, `tests/test_data_*` (its 3 modified files appeared in
  `git status` mid-batch; left untouched, never committed by me). One power window below shows their effect.

## Commands executed

```
cd $LAB/reference-model-study
# step 1 (MPS) — run #1 13:22 local (+0900), run #2 (power re-capture) 13:30 local
timeout 1800 .venv/bin/python scripts/smoke_timesfm3.py --config config/timesfm3.yaml --device mps 2>&1 | tee throwaway/a2-smoke-mps.log
# step 2 (MLX, run by S instruction even though MPS passed) — install 13:24 local, run #1 13:24 local, run #2 13:31 local
uv pip install --python .venv/bin/python -e ".[mlx]"          # + mlx==0.32.4, + mlx-metal==0.32.4 (13.8 s, no deps churn)
timeout 1800 .venv/bin/python scripts/smoke_timesfm3.py --config config/timesfm3.yaml --device mlx 2>&1 | tee throwaway/a2-smoke-mlx.log
# step 3 (S addendum) — power sampler alongside each device run: 20 s idle baseline, then timed run, then kill
nohup bash throwaway/a2-power-sampler.sh throwaway/a2-power-{mps,mlx}.txt &   # 1 Hz: date +%s; ioreg -rn AppleSmartBattery -> "SystemLoad"=mW
# step 4 (manifest, since mlx was installed)
.venv/bin/python scripts/fetch_timesfm3.py --config config/timesfm3.yaml --verify-only   # checkpoint re-verified; manifest rewritten
shasum -a 256 artifacts/timesfm3/model.safetensors    # a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da (unchanged)
git add results/a2-smoke-mps.json results/a2-smoke-mlx.json results/a2-model-manifest.json
git commit -m "chore(refstudy): record TimesFM-3 MPS/MLX smoke"   # 97de27d (pre-rebase historical hash; final on main = eb49314, see below)
```

`throwaway/a2-power-sampler.sh` (throwaway, not committed) implements the spec's one-liner with mW extraction:
`while sleep 1; do printf '%s %s\n' "$(date +%s)" "$(ioreg -rn AppleSmartBattery | grep -o '"SystemLoad"=[0-9]*' | grep -o '[0-9]*')"; done > out.txt`.

Note: `build_report` loads a second CPU forecaster for the parity block, so each run's wall clock is
MPS 16 s / MLX 17 s (timed latency cells exclude both loads).

## Device outcomes

| Device | overall | shapes / determinism / flat / truncation / latency | exit |
|---|---|---|---|
| mps (torch/MPS) | **ok** | ok / ok (max_abs_diff = 0.0) / observed / ok (diff = 0.0) / ok | 0 |
| mlx | **ok** | ok / ok (0.0) / observed / ok (0.0) / ok | 0 |

- No exceptions on either route; R-A2 §11's feared MPS operators (masked SDPA, `nn.RMSNorm`) did **not** fail on
  torch 2.15.0; `PYTORCH_ENABLE_MPS_FALLBACK` unnecessary.
- MPS memory: `mps_allocated_mb` = **1291.6 MiB** (weights alone are 1260.6 MiB F32).
- Load: MPS 2.64 s, MLX 0.57 s (vs CPU 2.3 s in E's run).
- Determinism at `atol=0.0` held on MPS and MLX (bit-identical repeat); truncation at `atol=0.0` held on both.

## Parity (device vs second CPU forecaster, seeded signal; input ptp ≈ 8.29–8.61)

| case (n, v) | MPS max_abs_diff quantiles | MPS max_abs_diff median | MLX max_abs_diff quantiles | MLX max_abs_diff median |
|---|---|---|---|---|
| (240, 1) | 6.68e-06 | 5.72e-06 | 8.58e-06 | 5.72e-06 |
| (240, 3) | 1.14e-05 | 1.05e-05 | 9.54e-06 | 7.63e-06 |
| (5760, 3) | 1.05e-05 | 5.72e-06 | 9.54e-06 | 7.63e-06 |

Relative to input ptp ~8.3–8.6: ≤ ~1.4e-6 — both backends numerically faithful to CPU.

## Latency / GFLOP/s (median of 5 timed runs, 1 warmup; GFLOP = R-A2 matmul-only cost law, not measured FLOPs)

| cell (n, v) | GFLOP | CPU med ms / GF/s (E ref) | MPS med ms / GF/s | MLX med ms / GF/s | MPS/CPU | MLX/CPU |
|---|---|---|---|---|---|---|
| 240, 1 | 8.0 | 202.9 / 39.2 | 75.9 / 104.7 | 14.9 / 534.4 | 0.37× | 0.07× |
| 240, 3 | 23.9 | 205.1 / 116.4 | 77.5 / 307.9 | 26.7 / 892.7 | 0.38× | 0.13× |
| 5760, 1 | 125.2 | 278.6 / 449.4 | 147.9 / 846.7 | 78.9 / 1585.9 | 0.53× | 0.28× |
| 11520, 1 | 254.4 | 425.9 / 597.3 | 255.3 / 996.4 | 153.4 / 1658.5 | 0.60× | 0.36× |
| 5760, 3 | 375.7 | 533.3 / 704.5 | 337.8 / 1112.1 | 186.2 / 2017.1 | 0.63× | 0.35× |
| 11520, 3 | 763.3 | 943.3 / 809.2 | 634.7 / 1202.6 | 409.7 / 1863.1 | 0.67× | 0.43× |

Ratios are wall-time ratios (MPS/MLX median ÷ CPU median; < 1 = faster). Both GPUs speed up with context length
(GPU-bound regime), as expected from the cost law's n² term.

## Memory

| | rss after load | rss hwm (last cell) | device-allocated |
|---|---|---|---|
| CPU (E) | 2739.5 MB | 2739.5 MB | – |
| MPS | 2739.2 MB | 2739.2 MB | 1291.6 MiB MPS-heap |
| MLX | 2590.75 MB | 2590.8 MB | – (no metric in report) |

## Power (S addendum; `ioreg -rn AppleSmartBattery` → `PowerTelemetryData.SystemLoad`, mW, whole-system, 1 Hz, no sudo)

> **Whole-smoke windows, not inference-only** (RV-B F6): these windows bracket the
> **entire smoke run** — they include **loading the model and the second CPU
> forecaster used for the parity block** (see `throwaway/a2-smoke-{mps,mlx}.log` and
> the note above the device outcomes), on battery with coarse whole-system telemetry.
> The +2/+4 W differences are therefore **not** isolated MPS/MLX inference energy and
> **not** a controlled backend comparison; they are whole-process, load-inclusive,
> whole-system numbers.

Raw samples: `reference-model-study/throwaway/a2-power-mps.txt`, `a2-power-mlx.txt` (35 lines each).
Pass-1 samples archived as `a2-power-{mps,mlx}-pass1.txt` — **discarded**: pass-1's MLX window was contaminated
by (a) the MPS-phase sampler still running and (b) a 26.6 W system-wide spike (~10 s) from concurrent machine
activity (A3's work); both smokes were therefore re-run (~30 s each) with a single monitored sampler and clean windows.

| device | idle baseline (20 s, pre-run) | mean during timed run | Δ vs idle |
|---|---|---|---|
| MPS | n=18, 6036 mW (5265–8040) | n=15, 8040 mW | **+2004 mW** |
| MLX | n=16, 8040 mW | n=17, 12123 mW (8040–16717) | **+4083 mW** |

Method verdict for Phase B: works without sudo and separates load from idle by ≥ 2 W, but `SystemLoad` is
whole-system and coarse (observed quantisation: 4125/5265/6035/8040/8462/16717/26609 mW levels) and sensitive to
any other activity on the machine (the 26.6 W spike above). Use exclusive windows and longer samples for Phase B;
note both numbers here are from a battery-discharging Mac (see deviation).

## Artefacts and commits

- `results/a2-smoke-mps.json`, `results/a2-smoke-mlx.json` committed; `results/a2-model-manifest.json` re-committed
  after `--verify-only` (only `utc_time` changed; `package_versions()` tracks timesfm/torch/numpy/huggingface_hub/
  safetensors — mlx is not in that set, so no version churn).
- Commit (at the time): **`97de27d`** `chore(refstudy): record TimesFM-3 MPS/MLX smoke`
  (3 files: both smoke JSONs + manifest). **Historical identifier:** the A3 executor later
  re-ordered main's history (fold its D1–D4 fixes into commit 1 via `git rebase -i`, see
  `E-A3.md` D6), and this commit replayed onto main as **`eb49314`** — `eb49314` is the FINAL
  live commit on main; `97de27d` remains valid only as the pre-rebase hash of the same change.
- Time-zone labels: all run times above are LOCAL +0900 (JST); the manifest refresh timestamp
  is `2026-11-09T04:31:58+00:00` (UTC) = 13:31:58 local.
- Weights/logs not committed; `artifacts/*` and `throwaway/*` git-ignored (verified via `git check-ignore -v`:
  `.gitignore:44` and `:55` rules); sha256 of `model.safetensors` unchanged post-batch.
- `git status --short` after commit shows only A3's 3 in-progress modified files (`scripts/package_flat_load.py`,
  `src/refstudy/data/oracle.py`, `tests/test_data_oracle.py`) — sibling's uncommitted work, intentionally left alone.
- Evidence logs (not committed): `throwaway/a2-smoke-mps.log`, `a2-smoke-mlx.log`, power files above.
