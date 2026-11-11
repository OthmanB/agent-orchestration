# E Evidence — SOLO-REFM / A2 (TimesFM-3 env + weights + CPU smoke)

- Date: 2026-11-09. Executor (E). Workcard: `omp-workcards/refm-A2.md` Steps 1–8 (LIVE BATCH SPEC excluded).
- Lab: `/Users/obenomar/Work/langGraph/appthrust/pipelineml-model-exploratory-work` (`$LAB`), study dir `reference-model-study/`, `PY=.venv/bin/python` (py3.12).
- Labels: **OBSERVED** = literal command output; **INFERENCE** = reasoning.
- Commits: `150c0ad` (code) · `1983666` (results). No push. Weights never staged.

## Step 1 — Preflight (OBSERVED)

```
$ git -C $LAB status --short            # empty
$ git check-ignore -v artifacts/timesfm3/model.safetensors artifacts/hf/x
.gitignore:44:reference-model-study/artifacts/*  artifacts/timesfm3/model.safetensors
.gitignore:44:reference-model-study/artifacts/*  artifacts/hf/x
$ git check-ignore -v results/a2-model-manifest.json; echo rc=$?
rc=1
$ df -h / | tail -1
/dev/disk3s1s1  461G  422G   40G  92% /
```
40 GiB free ≥ 10 GiB. PASS.

## Step 2 — Environment (OBSERVED)

- `pyproject.toml` gained `mlx = ["timesfm[mlx]==3.0.2"]` (declared, NOT installed).
- `uv pip install --python .venv/bin/python -e ".[dev,timesfm]"`:
  `Installed 23 packages in 224ms` … `+ timesfm==3.0.2`, `+ torch==2.15.0`, `+ huggingface-hub==2.4.0`, `+ safetensors==0.8.0`, `+ hf-xet==1.8.0`, `Wall time: 25.42 seconds`.
- `$PY -c "import importlib.metadata as m, torch, timesfm3; print(m.version('timesfm'), torch.__version__, torch.backends.mps.is_available())"` → `3.0.2 2.15.0 True`
- `du -sh .venv` → `831M` (184M before install).
- Live-API verification on the installed wheel (OBSERVED):
  - `TimesFM3Forecaster.from_pretrained(pretrained_model_name_or_path='google/timesfm-3.0-pytorch', device=None, **kwargs)` — matches workcard fact §2.
  - `predict(context, horizon, past_only_covariates=None, past_future_covariates=None, ts_id=None, return_quantiles=False, use_symmetric_averaging=False, make_positive=False, sort_quantiles=True, use_znorm=False, padding_mode='none') -> ForecastOutput`.
  - `_MAX_CONTEXT_LENGTH = 15360` present in `timesfm3.torch.timesfm3_forecaster`.
  - `ForecastOutput` fields: `ts_id, forecast, quantiles`.
  - `predict_batch` pads horizon to `global_horizon = ceil(H/64)*64` and passes it as `horizon=batched_hor[0]` into `model.decode`; the per-batch context cap is `batch_context = min(ceil(max_ctx/32)*32, global_context)` — so the workcard's horizon-patch law (Hg/32 → H=120 ⇒ 4) and silent truncation hold on the live install.

## Step 3 — Licence note (written)

`$LAB/markdown/timesfm3-licence-note.md` (40 lines): identity (repo, revision, sha256), the two licences,
the 7 R-A2 clause blockquotes, permitted/forbidden table, local-only rule, production→commercial carry-over.
**Verbatim correction vs R-A2's rendering:** in the actual LICENSE file the term
"Non-Commercial Purpose" is quoted with curly quotes (“ ”); the note uses curly quotes there and
straight quotes elsewhere where the file is straight (step-6 check below proves verbatim-ness).

## Step 4 — Code (written)

Files: `config/timesfm3.yaml`; `src/refstudy/timesfm_access/{__init__,config,checkpoint,loader,forecast,flops,smoke}.py`;
`scripts/{fetch_timesfm3,smoke_timesfm3}.py`; `tests/test_timesfm_access.py`.

Pre-fetch test/ruff (OBSERVED):

```
$ $PY -m pytest tests/test_timesfm_access.py -rs
SKIPPED [1] tests/test_timesfm_access.py:281: TimesFM-3 weights not downloaded yet
8 passed, 1 skipped in 0.15s
$ .venv/bin/ruff check src tests scripts
All checks passed!
```

## Step 5 — Fetch (OBSERVED, tail of `throwaway/a2-fetch.log`)

```
$ $PY scripts/fetch_timesfm3.py --config config/timesfm3.yaml
2026-11-09 12:46:19 | INFO | downloading google/timesfm-3.0-pytorch @ 43046b85… -> artifacts/timesfm3
Fetching 4 files: 100%|██████████| 4/4 [02:28<00:00, 37.12s/it]
2026-11-09 12:48:49 | INFO | checkpoint verified: model.safetensors (1322898824 bytes, 330710976 params)
2026-11-09 12:48:49 | INFO | manifest written to results/a2-model-manifest.json
fetch_rc=0   (Wall time: 150.48 s)
```
`snapshot_download` worked on huggingface_hub 2.4.0 — no curl fallback needed.

Independent check:

```
$ shasum -a 256 artifacts/timesfm3/model.safetensors
a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da  artifacts/timesfm3/model.safetensors
```
Match. `ls artifacts/timesfm3/`: `.cache/ LICENSE(7270) README.md(1436) config.json(1273) model.safetensors(1322898824)`.

## Step 6 — Licence fragment check (OBSERVED)

Throwaway `throwaway/a2-licence-check.py` (not committed): splits each `> "…"` blockquote on ` … `
(U+2026, as in the note/R-A2 rendering), strips edge elision markers, whitespace-normalises, and asserts
each fragment occurs in `artifacts/timesfm3/LICENSE`.

```
blockquotes found: 7
[0] OK   fragment 10 ch: 'Google LLC'...
[0] OK   fragment 93 ch: 'is pleased to make available the weights, parameters and inf'...
[0] OK   fragment 63 ch: 'freely available for your non-commercial and non-production '...
[1] OK   fragment 366 ch: '“Non-Commercial Purpose” means use for testing, evaluation, '...
[2] OK   fragment 252 ch: 'For clarity, use (a) for any revenue-generating activity, (b'...
[3] OK   fragment 351 ch: 'You will not, and will not permit, assist or cause any third'...
[4] OK   fragment 86 ch: 'For the avoidance of doubt, Outputs are not considered Deriv'...
[5] OK   fragment 179 ch: 'you must obtain a commercial license from Company, which Com'...
[6] OK   fragment 181 ch: 'This License applies only to individuals or entities who dow'...
RESULT: all fragments verbatim in LICENSE
```
(The initial run reported 1 fail because the checker split on ASCII `...` while the note uses U+2026 —
fixed the checker, not the note; no note re-copy was needed beyond the curly-quote fix above.)

## Step 7 — Full test + ruff + commit 1 (OBSERVED)

```
$ $PY -m pytest -rs          # 0 skipped now that weights exist
15 passed in 3.60s           # 6 common-config + 9 timesfm (incl. test_real_forecast_cpu, not skipped)
$ .venv/bin/ruff check src tests scripts
All checks passed!           # (on my workcard files; see deviation note re: sibling src/refstudy/data/)
$ git diff --check           # clean
```
Commit 1: `git add reference-model-study/pyproject.toml reference-model-study/config/timesfm3.yaml \
reference-model-study/src/refstudy/timesfm_access reference-model-study/scripts/fetch_timesfm3.py \
reference-model-study/scripts/smoke_timesfm3.py reference-model-study/tests/test_timesfm_access.py \
markdown/timesfm3-licence-note.md` → `150c0ad feat(refstudy): add TimesFM-3 access layer, FLOP cost law and licence note`
(13 files, +1453).

## Step 8 — CPU smoke (OBSERVED; full log `throwaway/a2-smoke-cpu.log`)

```
$ timeout 1200 $PY scripts/smoke_timesfm3.py --config config/timesfm3.yaml --device cpu 2>&1 | tee throwaway/a2-smoke-cpu.log
2026-11-09 12:50:54 | INFO | loading TimesFM-3 (torch) on device=cpu threads=6
Loading weights from local directory
2026-11-09 12:50:56 | INFO | loaded in 2.3s
2026-11-09 12:51:14 | INFO | smoke cpu overall=ok -> results/a2-smoke-cpu.json
smoke_rc=0   (Wall time: 20.89 s  << 20 min)
```
Overall `ok`. Root fields: `load_seconds 2.28`, `rss_after_load_mb 2739.5`, `torch_threads 6`,
`os_cpu_count 10`, `versions {python 3.12.15, timesfm 3.0.2, torch 2.15.0, numpy 2.5.4, huggingface_hub 2.4.0, safetensors 0.8.0}`, `parity null`.

**determinism** — `ok`, `max_abs_diff_quantiles 0.0`, `max_abs_diff_median 0.0` (bit-exact repeat).
**truncation** — `ok`, 17280-pt forecast ≡ last-15360 forecast, diffs `0.0` / `0.0` (bit-exact).

**flat (status `observed`, as designed)** — collapses-to-mean confirmed on all values:

| call | value | max_abs_delta | max_quantile_spread | collapses_to_mean |
|---|---|---|---|---|
| v1 | 3.7 | 7.15e-07 | 2.15e-06 | True |
| v3 variate 0 | 3.7 | 7.15e-07 | 2.15e-06 | True |
| v3 variate 1 | 0.25 | 0.0 | 0.0 | True |
| v3 variate 2 | 120.0 | 7.63e-06 | 0.0 | True |

(R-A2 §6 prediction borne out: flat control collapses to context mean — a tie by construction.)

**latency** (CPU, 6 threads, H=120; cells ascending by n·v):

| n | v | median ms | min ms | max ms | GFLOP | GFLOP/s | RSS hwm MB |
|---|---|---|---|---|---|---|---|
| 240 | 1 | 202.888 | 198.178 | 212.178 | 7.9530 | 39.2 | 2739.5 |
| 240 | 3 | 205.096 | 197.023 | 255.062 | 23.8665 | 116.4 | 2739.5 |
| 5760 | 1 | 278.590 | 276.333 | 306.433 | 125.1873 | 449.4 | 2739.5 |
| 11520 | 1 | 425.859 | 418.217 | 490.169 | 254.3625 | 597.3 | 2739.5 |
| 5760 | 3 | 533.261 | 495.251 | 588.394 | 375.6751 | 704.5 | 2739.5 |
| 11520 | 3 | 943.294 | 925.758 | 1028.859 | 763.3110 | 809.2 | 2739.5 |

GFLOP/s rises with size (matmul efficiency); note the first cell (7.95 GFLOP) is launch/overhead-bound
(39 GFLOP/s), so the 763-GFLOP 2-day 3-series call at ~943 ms is the representative figure for Phase B
(OBSERVED, not the R-A2 1.5–2.5 s inference — CPU is faster than that estimate, likely torch 2.15 threads).

Commit 2: `git add reference-model-study/results/a2-model-manifest.json reference-model-study/results/a2-smoke-cpu.json`
→ `1983666 chore(refstudy): record TimesFM-3 checkpoint manifest and CPU smoke` (2 files, +199).

## Acceptance (all OBSERVED PASS)

1. **sha256/manifest** — `shasum -a 256` = `a7592b0a…f17da`; manifest has `revision 43046b85…`,
   `size_bytes 1322898824`, `param_count 330710976`, `weights_committed false`, filled `versions`
   (python 3.12.15, timesfm 3.0.2, torch 2.15.0, numpy 2.5.4, huggingface_hub 2.4.0, safetensors 0.8.0),
   `dtypes ["F32"]`. Python one-off asserts PASS.
2. **git hygiene** — run from study dir: `git check-ignore -v artifacts/timesfm3/model.safetensors artifacts/timesfm3/config.json artifacts/hf`
   → one rule per path (all `.gitignore:44:reference-model-study/artifacts/*`), both before and after fetch;
   `git status --short` shows no `artifacts/`/`*.safetensors` path; `git ls-files | grep -Ec 'safetensors|artifacts/(timesfm3|hf)'` = 0;
   `ls ~/.cache/huggingface/hub | grep -ci timesfm` = 0.
3. **tests/ruff** — `$PY -m pytest -rs` → `15 passed` (0 skipped); ruff green on my files.
4. **smoke JSON** — python one-off asserts PASS: `overall=="ok"`; shapes/determinism/truncation/latency `ok`;
   `flat.status=="observed"` with per-variate deltas; 6 latency cells each with `median_ms,gflop,rss_hwm_mb` (+gflops_per_s,min,max).
5. **commits** — `git log --stat -2` shows `150c0ad` (incl. licence note) + `1983666` (manifest + smoke JSON);
   `git diff --check` clean; `git status --short` empty except `?? src/refstudy/data/` (sibling A3's untracked
   module, not mine, not committed).

## R-A2 corrections held on live install?

- YES — `from_pretrained(..., device=None, **kwargs)`; `revision`/`local_files_only`/`cache_dir` accepted
  (local-dir load works: "Loading weights from local directory").
- YES — `predict` signature and `return_quantiles` default False; median = `quantiles[..., 4]` (wrapper
  test asserts it even when stub `.forecast` differs; real run identical).
- YES — silent truncation at 15360 (truncation check bit-exact 0.0 diff); horizon H=120 → 4 horizon patches
  (FLOP table reproduced the R-A2 §7 numbers to <0.01 %).
- YES — univariate-vs-multivariate by call shape only; `use_variate_attention` not exposed anywhere.
- Cost law: `forecast_flops(11520, 3, 120)` = 763.311 GF vs R-A2 763.3 — within 0.002 %.

## Deviations

1. **Manifest `versions.python`** comes from `platform.python_version()` — the dist `python` is not an
   importlib.metadata entry in this venv (`importlib.metadata.version("python")` → PackageNotFoundError, OBSERVED).
   Value is `3.12.15`; contract "python … via importlib.metadata, `not installed` if absent" otherwise honored.
2. **Elision marker is U+2026** (`…`), not ASCII `...`, in the note (matching R-A2's rendering); step-6
   checker split on `\s\u2026\s` and stripped edge `…` from fragments (the escalation quote begins with `…`).
3. **`src/refstudy/data/`** (GreptimeDB packaging, A3's leaf) appeared in the tree mid-run and is untracked.
   It is NOT in my workcard; I did not touch or commit it. The workcard's global `ruff check src tests scripts`
   would flag it (5 pre-existing errors in `greptime.py`) until A3 fixes its own files; my workcard files are
   ruff-clean (verified in isolation and via `git show` of the committed tree).
4. **CPU smoke ran ~21 s** (limit 1200 s): the 1.32 GB checkpoint loads in 2.3 s and the largest cell is
   943 ms; no timeout pressure.
5. No licence/weights were committed; weights live only in `artifacts/timesfm3/` (git-ignored) and
   `artifacts/hf/` (git-ignored HF cache with no `timesfm*` entries).
