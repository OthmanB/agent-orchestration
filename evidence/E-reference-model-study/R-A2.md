# R Evidence — SOLO-REFM / R-A2 (Part 2, Phase A2: TimesFM-3 primary-source research)

- Date: 2026-11-09
- Environment: local Mac (arm64, macOS 25.6.0, `uv` 0.13.1, python 3.10/3.11/3.12). Sources queried over HTTPS: PyPI JSON API, Hugging Face Hub API, raw.githubusercontent.com. No cluster access required for this leaf.
- Labels: **OBSERVED** = command output; **SOURCE** = file/line or quoted product text with URI; **INFERENCE** = my reasoning, not observed.

## 1. Context verification

- Lab repo `reference-model-study/` exists with the subdirs named in CAMPAIGN-CONTEXT (OBSERVED: `config/ data/ src/ scripts/ results/ figures/ tests/ artifacts/ throwaway/`).
- Local python 3.11.15 + `uv` 0.13.1 available (OBSERVED). 40 GiB free on `/` (OBSERVED `df -h`).
- Nothing was installed, downloaded or created in the lab repo by this leaf; all scratch lived under `/tmp` and was deleted (see §11).
- Divergence worth flagging up front: the CAMPAIGN-CONTEXT task table lists R-A2 output as "model card, API, context limits, licence, input-uncertainty, deps, hardware". All of those are answered except where §10 says otherwise.

## 2. Does TimesFM-3 exist as described? (Q1)

**Yes — one public checkpoint, one format.** Facts:

- **HF repo:** `google/timesfm-3.0-pytorch`, created 2026-08-24, lastModified 2026-09-02 (OBSERVED `https://huggingface.co/api/models/google/timesfm-3.0-pytorch`). Revision `43046b85ec22d584a13f8098c2ed39c889e129c2` (OBSERVED, same API). `gated: false`, downloads 8, likes 1.
- **Files in the repo (OBSERVED, full listing):** `.gitattributes`, `LICENSE` (30,189 B), `README.md` (1,023 B), `config.json` (1,273 B, blob `c1de41214b9c86940224b802a0d1744d65ad7781`), `model.safetensors` (1,322,898,824 B = 1.32 GB, blob `8c1bfefdfab936c302b14c25f46265e65805d7c5`, file sha256 `a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da` per `x-linked-etag`).
- **No other variants.** OBSERVED HF model search: exactly one repo for `google/timesfm-3*` (`google/timesfm-3.0-pytorch`); no flax/jax, no ONNX, no quantised variant, no 200M variant for 3.0.
- **Params = 330,710,976** in the safetensors header, dtype F32 (OBSERVED via HF API `?blobs=true`). Matches the blog's "330 million parameters" (SOURCE `https://research.google/blog/timesfm-3-a-zero-shot-foundation-model-for-multivariate-forecasting/`, dated **August 31, 2026**).
- **Config (`config.json`, OBSERVED verbatim):** `input_patch_len 32`, `input_transform "identity"`, `linear_detrending_threshold 0.5`, `output_patch_len 64`, `quantiles [0.1,0.2,…,0.9]`; `residual_block_config {activation relu, hidden_dims 1280, output_dims 1280, identity_skip false, use_bias false, prenorm "none"}`; `transformer_config {num_layers 20, use_remat true, transformer {model_dims 1280, num_heads 16, hidden_dims 1280, attention_norm rms, feedforward_norm rms, qk_norm rms, v_norm none, ff_activation relu, causal_attention true, use_rope_seq true, use_rope_var false, use_sdpa true, use_memory_efficient_attention true, max_variates 32, use_bias false, deterministic true}}`; `use_iterative_cpm_revin true`, `use_linear_detrending true`, `use_stitching true`, `use_variate_attention true`, `use_frozen_running_stats false`, `value_clip 1e20`.
  - Caveat: the checkpoint file does **not** carry `global_context_length`, `checkpoint_path`, `use_future_covariates`, `use_ff_denorm`, `use_zero_denorm`, `residual_scale_logits` — those are `ModelConfig` dataclass defaults in the code (SOURCE `src/timesfm3/torch/configs.py`), and the operative context cap is the module constant `_MAX_CONTEXT_LENGTH = 15360`.
- **Design claims confirmed:**
  - decoder-only forecast head over 32-step patches / 64-step output patches (SOURCE `src/timesfm3/torch/model.py:117-129`, `config.json`);
  - non-autoregressive single pass: SOURCE `src/timesfm3/torch/model.py:376` docstring "Non-autoregressive single-pass decoding for TimesFM3"; blog (same URL) "the model fills in all masked horizon patches simultaneously, with no iterative loop required";
  - natively multivariate with cross-series attention: SOURCE `src/timesfm3/torch/transformer.py:397-410` (MixingTransformer = seq attention → ↔-mix variate attention → FFN), `:485-500` seq attention reshaped `(b·v, n, d)`, `:505-520` variate attention reshaped `(b·n, v, d)`;
  - 9 quantiles 10th–90th, median at index 4: SOURCE `src/timesfm3/torch/timesfm3_forecaster.py:54-59` (`quantiles` default and `median_quantile_index: int = 4`), confirmed by the model card ("Median at index 4") and the blog.
- **Package (OBSERVED PyPI):** `timesfm` versions `3.0.0` (2026-08-28), `3.0.1` (2026-09-07), `3.0.2` (2026-11-03, current). `requires_python >=3.10`. **Base deps are only `numpy>=1.26.4`, `huggingface_hub>=0.28.0`, `safetensors>=0.5.3`** — torch is an *extra*: `torch>=2.0.0; extra == "torch"`. Extras: `torch` (torch), `mlx` (`mlx>=0.32`, safetensors, huggingface-hub), `flax` (`flax`, `optax`, `einshape`, `orbax-checkpoint`, `jaxtyping`, **`jax[cuda]`**), `xreg` (**`jax[cuda]`**, `scikit-learn`).
  - **Install caveat for this Mac:** `timesfm[flax]` and `timesfm[xreg]` pull **`jax[cuda]`**, which has no macOS arm64 wheels — installing them here is expected to fail. Use `[torch]` or `[mlx]` only (INFERENCE from the dependency marker; not attempted, since it would install packages).
  - A bare `pip install timesfm` gives **no backend at all** (no torch, no mlx) — the extra is mandatory.
- **No TimesFM-3 paper found**: blog cites the 2023 TimesFM paper (ICML 2024 / arXiv 2310.10688) but no new arXiv id for v3 (OBSERVED: grep of the blog text for `arxiv` → 0 hits).

## 3. Licence — decision-critical (Q2)

**Code: Apache-2.0. Weights: TimesFM Non-Commercial License v1.0. They are different licences.**

- SOURCE `https://github.com/google-research/timesfm` → GitHub API: `license: {'key': 'apache-2.0', 'spdx_id': 'Apache-2.0'}`, last push 2026-10-29, default branch `master`, HEAD commit `65be4bdf5e96c60e498a1c26` (OBSERVED). Code licence = Apache-2.0.
- SOURCE HF repo `LICENSE` = **`TimesFM Non-Commercial License v1.0`** (OBSERVED: card metadata `license: other`, `license_name: timesfm-non-commercial-license-v1.0`; full text fetched from `https://huggingface.co/google/timesfm-3.0-pytorch/raw/main/LICENSE`). **Verbatim clauses** (exact wording; these are the words S should gate on):
  - grant: "Google LLC … is pleased to make available the weights, parameters and inference code for the TimesFM Model … freely available for your **non-commercial and non-production use**";
  - definition: "'**Non-Commercial Purpose**' means use for testing, evaluation, or research not tied to commercial gain, production deployment, or revenue generation. This includes **internal benchmarking, academic research, and experimentation on private or public datasets**, provided the results are not used in commercial decision-making, client deliverables, or paid products/services.";
  - hard exclusion: "For clarity, use (a) for any revenue-generating activity, (b) in direct or indirect interactions with end users or production systems, or (c) to train, fine-tune, or distill other models for commercial use, in each case is **not** a Non-Commercial Purpose.";
  - restrictions: "You will not, and will not permit, assist or cause any third party to: use, modify, copy, reproduce, create Derivatives of, or **Distribute** the TimesFM Model (or any Derivative thereof, **or any Outputs and data produced by the TimesFM Model**), in whole or in part for any **commercial or production purposes**; or **Distribute the TimesFM Model or a Derivative**."
  - outputs carve-out: "For the avoidance of doubt, **Outputs are not considered Derivatives** under this License."
  - escalation: "…you must obtain a **commercial license** from Company, which Company may grant in its sole discretion and which additional use may be subject to a fee, royalty or other revenue share."
  - scope: "This License applies only to individuals or entities who **download** the TimesFM Model. For customers accessing the TimesFM Model through our API, other terms and conditions may apply."
- **The two licences overlap in wording**: the HF text names "inference code" as part of "the TimesFM Model", while GitHub is Apache-2.0 and the README says "The TimesFM source code in this repository is licensed under `Apache-2.0`". Practical reading (INFERENCE, and the README is explicit): **repo source = Apache-2.0, TimesFM-3.0 weights = non-commercial**.
- **Gating: none.** `gated: false`; an anonymous, unauthenticated `curl` retrieved `config.json`, `README.md` and `LICENSE` and a `HEAD` on `model.safetensors` returned the full size + etag (OBSERVED). No login, no ToS click.
- **Answers in the form the Planner asked for:**
  - Download & run locally for this research study → **OK.** The study is literally inside the licence's own example list ("internal benchmarking, academic research, and experimentation on private or public datasets"), with no client deliverables and no commercial decision-making.
  - Store weights on local disk outside git → **OK**, and is the shape that keeps the "Distribute" clause untouched.
  - **Commit weights to any git repo, upload to a hub, or hand a copy to a third party → NOT PERMITTED** ("will not … Distribute the TimesFM Model or a Derivative"). The campaign's "never commit weights" rule therefore coincides with the licence, not just with repo hygiene.
  - Publishing *forecasts/results* from the study → permitted for research: outputs are not Derivatives and the distribution bar only bites "for any commercial or production purposes".
  - Any **production** use of the detector (this reference inside anything that interacts with end users, or as part of a paid service) → **NOT PERMITTED** without a commercial licence. This is a wall for E's recommendation, not for A2.
- **Fallback if a permissive licence is later required:** `google/timesfm-2.5-200m-pytorch` (and 2.0) are **Apache-2.0** (OBSERVED: card metadata `license: apache-2.0` on both, in the HF API listing). Caveat: 2.5 is **univariate only** (covariates via XReg linear regression), i.e. it does not deliver the cross-series attention that motivates Part 2.

## 4. Inference API (Q3)

- **Install:** `pip install "timesfm[torch]==3.0.2"` (README). `flax` extra exists in metadata but **there is no TimesFM-3 flax checkpoint and no flax code path for 3.0** (SOURCE: repo tree `src/timesfm3/{torch,mlx}` only, no `flax` dir) → torch (and MLX on Apple) are the only usable backends for v3. `xreg`/`sklearn` extra is only needed for 2.5 XReg.
- **Python:** `>=3.10` (PyPI metadata). With 3.10 the resolver picks torch 2.14.1; with 3.11/3.12 it picks torch 2.15.0 (OBSERVED `uv pip install --dry-run`, see §9).
- **Device:** `TimesFM3Forecaster.from_pretrained(repo, device=...)` accepting a `str`; default `cuda:0` if `torch.cuda.is_available()` else `cpu` (SOURCE `timesfm3_forecaster.py:370-375`). **MPS is not a special case** — it is whatever you pass; the only CUDA-specific code is a `torch.cuda` guard in the try/gc path (SOURCE `model.py`, `try: torch.cuda.empty_cache()`).
- **Signatures (SOURCE, exact):**
  - `TimesFM3Forecaster.from_pretrained(checkpoint_path=None, *, model_name_or_path="google/timesfm-3.0-pytorch", revision=None, **kwargs)` — `revision` exists, so A2 can pin sha `43046b85ec22d584a13f8098c2ed39c889e129c2`.
  - `def predict(self, context: np.ndarray, horizon: int, past_only_covariates=None, past_future_covariates=None, ts_id: str|None = None, return_quantiles: bool = False, use_symmetric_averaging: bool = False, make_positive: bool = False, sort_quantiles: bool = True, use_znorm: bool = False, padding_mode: str = "none") -> ForecastOutput` (`timesfm3_forecaster.py:433-446`) — thin wrapper that calls `predict_batch(contexts=[context], ...)`.
  - `def predict_batch(self, contexts: list[np.ndarray], horizon: int, past_only_covariates: list[np.ndarray|None]|None = None, past_future_covariates: list[np.ndarray|None]|None = None, ts_ids: list[str]|None = None, return_quantiles: bool = False, use_symmetric_averaging: bool = False, make_positive: bool = False, sort_quantiles: bool = True, use_znorm: bool = False, padding_mode: str = "none") -> Iterator[ForecastOutput]` (`timesfm3_forecaster.py:465-478`) — a **generator** over batch items.
  - Note `return_quantiles` defaults to **False** in both forecaster methods (the README examples pass `return_quantiles=True`; `TimesFM3Evaluator` defaults it to True).
- **How series are passed:** a **list of numpy arrays**; each element is `(T,)` → univariate (V=1) or `(V, T)` → multivariate (V variates sharing one horizon). **No frequency flag** (grep `freq` over the 3.0 sources: 0 hits — 2.5 removed it and 3.0 did not reintroduce it), **no group id** (`ts_id`/`ts_ids` are display labels only), **no mask argument** at this level (`mask` exists only on the internal `model.decode`, built from NaNs; see §5).
- **Output (SOURCE `timesfm3_forecaster.py:750-765`):** 1-D input → `forecast: (H,)`, `quantiles: (H, 9)`; 2-D `(V,T)` input → `forecast: (V, H)`, `quantiles: (V, H, 9)` (README MLX example confirms `(2, 32)` / `(2, 32, 9)`). Quantiles are in ascending order (10th…90th) and are **sorted across the quantile axis post-hoc** when `sort_quantiles=True` (default, SOURCE `:721-722`). `forecast` is literally `quantiles[..., median_quantile_index]` with `median_quantile_index = 4` (SOURCE `:59`, `:757-765`). **There is no separate mean output** — 2.5 had one at index 0; do not carry that convention over.
- **Minimal runnable snippets** (shapes/semantics verified against source; (a) is the README form):
  ```python
  import numpy as np
  from timesfm3 import TimesFM3Forecaster          # == timesfm3.torch.TimesFM3Forecaster

  f = TimesFM3Forecaster.from_pretrained(
      "google/timesfm-3.0-pytorch",
      revision="43046b85ec22d584a13f8098c2ed39c889e129c2",   # optional pin
      device="cpu")                                          # "cpu" | "mps" | "cuda:0"

  # (a) univariate
  out = f.predict(np.sin(np.linspace(0, 20, 240)).astype(np.float32),
                  horizon=120, return_quantiles=True)
  # out.forecast (120,)   out.quantiles (120, 9)   median = out.quantiles[:, 4]

  # (b) multivariate — several related series in ONE call (one forward pass, joint attention)
  ctx = np.random.randn(3, 240).astype(np.float32)   # (num_variates, context_len)
  out = f.predict(ctx, horizon=120, return_quantiles=True)
  # out.forecast (3, 120)   out.quantiles (3, 120, 9)

  # (c) past-only covariates + past-future (dynamic) covariates
  past_only   = np.random.randn(1, 240).astype(np.float32)        # (C_past, T)
  past_future = np.random.randn(1, 240 + 120).astype(np.float32)  # (C_dyn, T+H): future part MUST be filled in
  out = f.predict(ctx, horizon=120,
                  past_only_covariates=past_only,
                  past_future_covariates=past_future,
                  return_quantiles=True)
  ```
  For batched evaluation use `f.predict_batch([ctx1, ctx2, ...], horizon=..., return_quantiles=True)` (generator) or `TimesFM3Evaluator(ModelConfig(checkpoint_path=repo, per_core_batch_size=32, device="cpu"))` which adds variate chunking at `_MAX_VARIATES_PER_FORWARD = 32` (SOURCE `evaluator.py:29`).

## 5. Context and horizon limits (Q4)

- **Max context = 15,360 time steps = 480 patches.** SOURCE `_MAX_CONTEXT_LENGTH = 15360` (`timesfm3_forecaster.py:32`), `global_context_length: 15360` (`config.json`), and README (PyTorch section + MLX section): "Contexts longer than `global_context` (15,360) are truncated to their most recent points before decode".
- **Longer than max → silent truncation, never an error.** Two places: `global_context` caps the batched context (`timesfm3_forecaster.py:654-662`, `batch_context = min(ceil(max_ctx/32)*32, global_context)`), and `_Query.format` keeps the **last** `context_len` points (`:211-246`). Consequence: a 4-day context would be silently cut to its most recent 2.67 days — no warning.
- **Shorter than a patch / not a multiple of 32 → left-padded with zeros and masked** (min 32; pad positions carry `mask=True`, so they are excluded from attention and from the RevIN statistics). No error.
- **Max horizon: no hard cap in the code.** The horizon is padded up and generated in `num_forecast_patches = ceil((H-32)/32)` output patches (min 1), then `num_horizon_patches = num_forecast_patches + rolls - 1` with `rolls = output_patch_len // input_patch_len = 2` (`model.py:118-129`, `:433-447`); i.e. rolling 64-step output patches overlapping by 32, stitched. For our operative horizon H=120: 3 forecast patches → 4 horizon patches → padded horizon 128, `hor_padding=8`. README warns stitched long horizons are "worth checking on their own" (MLX numerics quoted per-horizon).
- **Our raw cadence, 15 s (OBSERVED arithmetic, 1 day = 86,400 s = 5,760 pts):**

| window | raw points | patches | within limits? |
|---|---|---|---|
| 1 h | 240 | 8 (padded) | ✅ |
| 5 min (one scoring block) | 20 | 1 (padded to 32) | ✅ but < 1 patch of context → heavily masked |
| 1 day | 5,760 | 180 | ✅ |
| 2 days | 11,520 | 360 | ✅ (7,680 pts of headroom) |
| 2.67 days (max) | 15,360 | 480 | limit |
| 3 days | 17,280 | 540 → truncated to 480 | ❌ silently truncated to most recent 2.67 days |

- **So: a 11,520-point (2-day) raw context fits with room to spare.** If a scenario ever needs >2.67 days at 15 s, the Planner must either (a) subsample (e.g. 60 s cadence → 10 days at the same 15,360 budget) or (b) accept that only the most recent 2.67 days influence the forecast. Recorded as an explicit design constraint, not a defect.

## 6. Input uncertainty — none (Q5)

- **The published interface is point-series only.** Exact signature quoted above (`timesfm3_forecaster.py:433-446`): parameters are `context`, `horizon`, `past_only_covariates`, `past_future_covariates`, `ts_id`, and behaviour flags. **There is no per-step variance/std, no weight, no sample-weight, no observation-noise and no interval argument anywhere in `predict`/`predict_batch`/`TimesFM3Evaluator.predict_batch`** (OBSERVED: full parameter lists, §4; grep for `std|variance|sigma` in the forecaster finds only the internal RevIN statistics).
- The only per-step auxiliary input is a **numeric covariate channel** (`past_only_covariates` / `past_future_covariates`), and covariates are treated as additional *point* series to attend over — not as uncertainty.
- **Consequence for the vision's §5 variant:** the "box-car mean + within-box spread" interface *does not exist* in this model. The only two shapes it can take are (i) feed the box-car **mean** series and drop the spread, or (ii) feed the box spread as an extra **covariate channel**, in which case the model consumes it as signal. The latter is a modelling decision for the Planner, **not** an "input-uncertainty feature" — it must not be described as such in the workcard.
- Related source fact worth knowing for the flat control: the RevIN reverse pass multiplies by the **raw** σ while the forward pass clamps σ at `_SAFE_SIGMA = 1e-6`, so for near-constant contexts the forecast **delta collapses to ~0** — the model returns approximately the context mean (SOURCE `util3.py:30-32`, `:227-259`; upstream issue **#522** open, 2026-09-17, "Reversible Instance Normalization contains an asymmetry … unnormalized forecasts biased"). For a quiescent flat pod this is benign-looking, but it means the model contributes no information there — the flat control will be a *tie*, not a discriminator.

## 7. Compute facts (Q6)

**Architecture (SOURCE `config.json`, `transformer.py:397-560`):** 20 identical `MixingTransformer` layers, each = RMSNorm → **sequence attention over patches** (RoPE, causal, full over 0…n) → residual → RMSNorm → **variate attention across series at a fixed patch index** (no RoPE) → residual → RMSNorm → FFN (`d_ff = 1280`, ReLU, `use_ff_denorm`) → residual. d_model 1280, 16 heads, head_dim 80, `max_variates 32`.

**Parameter budget (INFERENCE, arithmetic that reproduces the published 330.71 M):**

| block | M params | note |
|---|---|---|
| per layer: seq QKVO 4·d² | 6.554 | |
| per layer: var QKVO 4·d² | 6.554 | |
| per layer: FFN 2·d·d_ff | 3.277 | |
| ×20 layers | 327.68 | |
| input embed (32+64 → d) + residual block (192→d, d→d) | 2.13 | |
| output head (d → 64·9) | 0.74 | |
| **total** | **≈330.55** | actual 330.71 (norms/scales account for the 0.16 M gap) |

**FLOPs per forward call (INFERENCE; matmul-only, 2 FLOP per MAC, ignores norms/softmax):**
`F ≈ 2·P_eff·V·n_total  +  4·n_total²·d·L·V  +  4·V²·d·L·n_total`, where `V` = series in the call, `n_total = ceil(N/32) + horizon_patches`, `d = 1280`, `L = 20`, and `P_eff ≈ 330 M`. The three terms are: (1) the linear/FFN bulk, (2) sequence attention over patches, (3) variate attention.

**Critical correction for the Planner's cost model:** series in a multivariate call are **NOT** attended as a flattened `(V·n)²` block. Sequence attention runs per variate (`(b·v, n, d)`, cost `∝ V·n²`) and variate attention runs per patch index (`(b·n, v, d)`, cost `∝ n·V²`). So the cost is **linear in V**, not quadratic — the vision's "attention cost ∝ (series×patches)²" is wrong by construction.

Numbers with `H = 120` (4 horizon patches, n_total = patches + 4):

| N (pts) | n_total | V=1 | V=3 | V=5 |
|---|---|---|---|---|
| 240 | 12 | 8.0 GFLOP | 23.9 | 39.8 |
| 5,760 | 184 | 125.2 | 375.7 | 626.3 |
| 11,520 | 364 | 254.4 | **763.3** | 1,272.6 |
| 15,360 | 484 | 344.2 | 1,032.8 | 1,721.8 |

Attention is only **2.8 % (N=5760) → 7.0 % (N=15360)** of the total at V=3, i.e. **within our operating range the cost is essentially linear in context length** (N scaling ≈ linear, with a 1/V-attenuated quadratic tail). A 3-series call at the 2-day raw context is ≈763 GFLOP.

**Published performance (SOURCE README, only number published):** 330 M model, **Apple M4 Max**, context 512, horizon 64, fp32 with `mx.compile`, MLX backend: p50 **11.1 ms** batch 1, 19.7 ms batch 8, 48.1 ms batch 32 (666 series/s). INFERENCE cross-check: my formula gives ≈12.1 GFLOP for that shape → 11.1 ms ⇒ ≈1.1 TFLOP/s effective; applying the same rate to 763 GFLOP gives **≈0.7 s per 3-series call at 11,520 pts on an M4 Max**, so roughly **1.5–2.5 s on the local M2 Pro** (INFERENCE, ±2×; must be measured in A2/B).

**Memory:**
- weights: 1.32 GB (fp32) — this is the only dtype in the checkpoint.
- activations at V=3, n_total=364, H=120: hidden states `3·364·1280·4 B ≈ 5.6 MB` per tensor; the biggest single buffer is a full attention score matrix `3·16·364·364·4 B ≈ 25 MB` (sequence attention is non-chunked); the variate side is `364·16·3·3·4 B` (negligible). Peak working set INFERENCE **≈1.8–2.2 GB** including the torch runtime (measured on CPU/MPS by A2, not here). No KV cache is retained across calls (single-shot decode).

## 8. Hardware notes (Q7)

- **RAM:** weight file 1.32 GB + runtime → INFERENCE ≥4 GB free needed, 8 GB comfortable. Peak measured by A2 (`torch.mps.current_allocated_memory` / `resource` RSS) is the number to report in B.
- **VRAM (CUDA):** INFERENCE ≥2.5 GB; no published 3.0 VRAM figure. Note for the compute study: **CUDA is not available on the data-source node** (`rtx-4000-test`: kernel module not loaded — campaign context fact), so the local Mac (MPS) or CPU is the only compute available for B; do not plan a GPU run there.
- **bf16 / fp16: NOT supported on the published path.** Weights are fp32; every input is explicitly cast `.to(self.device, dtype=torch.float32)` before `decode` (`timesfm3_forecaster.py:674`, `:690`, `:704`), and no inference source casts parameters or activations to half (OBSERVED grep `torch.compile|torch.jit|.half()|bfloat16|float16` over `src/timesfm3/torch/*.py`: **0 hits**). Upstream issue **#543** (open, 2026-10-22) reports fp16/bf16 runs dying on the CPU/SDPA path and asks for low-precision dtype preservation, i.e. half precision is not a supported configuration today. README benchmarks are explicitly "fp32 with `mx.compile`". **Plan fp32**; 1.32 GB weights + fp32 activations fit comfortably.
- **torch version pins:** `torch>=2.0.0` (PyPI metadata); the SDPA path is annotated "PyTorch >= 2.1" (SOURCE `transformer.py:344`). Resolution on this Mac today: **torch 2.15.0** (py3.11/3.12) or 2.14.1 (py3.10) — §9.
- **`torch.compile`: not needed and not used.** No `torch.compile`/`torch.jit` in the 3.0 inference path (grep of forecaster/model/transformer/evaluator/util: 0 hits). `mx.compile` appears only in the MLX benchmark harness.
- **MPS (Apple Silicon) — the honest state:**
  - 3.0 contains **no MPS-specific code** (OBSERVED grep `-i mps` over `src/timesfm3/torch/*.py`: **0 hits**); whatever `torch.device` you pass is used, and the 2.5-era float64 trap is gone because inputs are cast to fp32 before transfer (SOURCE `:674`, `:690`, `:704`).
  - The 2.5 docs claim "macOS 13+ fully supported, MPS acceleration on Apple Silicon"; the 3.0 README does **not** claim MPS support and instead advertises an **MLX backend** as the Apple path (`pip install timesfm[mlx]`, `mlx>=0.32`), stated to be numerically matched to PyTorch (max abs err 9.5e-7 median / 1.8e-6 quantiles at ctx 512, h 64; 2.3e-6 / 2.7e-6 at h 128), same `predict`/`predict_batch` surface, covariate support included.
  - **Residual MPS risk (INFERENCE):** the attention path always calls `F.scaled_dot_product_attention(..., attn_mask=<bool 4-D>)` (`transformer.py:344-360`), and the manual fallback **cannot be selected** from the public config because `use_sdpa=False` is ignored (upstream issue **#549**, open, 2026-11-02). On MPS under torch 2.15 SDPA still partially routes through MPSGraph ("Attention runs entirely on Metal" is advertised for **2.16**, HF blog 2026-10-20), so masked-SDPA + `nn.RMSNorm` on MPS are unverified. **A2 must smoke-test `device="mps"` explicitly and record either a working run or the exact operator that raises**; fallbacks in order: `device="cpu"` (works, slower), MLX backend (fastest on Apple, "no PyTorch required").

## 9. Local dependency target on THIS Mac (Q8)

**Proposed sequence (not executed here — A2 owns the install):**
```bash
LAB=/Users/obenomar/Work/langGraph/appthrust/pipelineml-model-exploratory-work/reference-model-study
uv venv --python 3.12 "$LAB/.venv-timesfm"
uv pip install --python "$LAB/.venv-timesfm/bin/python" "timesfm[torch]==3.0.2"
# weights: keep them OUT of git, inside an ignored dir or the HF cache
export HF_HOME="$LAB/artifacts/hf"          # lab .gitignore already excludes weights
"$LAB/.venv-timesfm/bin/python" - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("google/timesfm-3.0-pytorch",
                  revision="43046b85ec22d584a13f8098c2ed39c889e129c2",
                  allow_patterns=["*.json","*.safetensors","LICENSE","README.md"],
                  local_dir="/Users/obenomar/Work/langGraph/appthrust/pipelineml-model-exploratory-work/reference-model-study/artifacts/timesfm3")
PY
```
`snapshot_download` is used rather than a CLI because the CLI entry point differs between `huggingface_hub` generations (`hf` vs legacy `huggingface-cli`); the Python API is stable in the resolved version.

**Dry-run evidence (OBSERVED, `uv pip install --dry-run`, throwaway venvs under `/tmp`, since deleted):**
- python 3.11 → `timesfm==3.0.2`, `torch==2.15.0`, `numpy==2.2.4`, `huggingface-hub==2.4.0`, **25 packages** ("Would download 25 packages").
- python 3.12 → identical versions: `torch==2.15.0`, `numpy==2.2.4`, `huggingface-hub==2.4.0`, 25 packages.
- python 3.10 → `torch==2.14.1` (2.15.0 requires `>=3.11`), same `timesfm==3.0.2`. **Use 3.11 or 3.12.**
- approx download size ≈160 MB: torch 2.15.0 arm64 wheel **138.6 MB** (OBSERVED PyPI) + numpy 2.2.4 arm64 wheel **5.2 MB** (`macosx_14_0_arm64`) / 14.1 MB (`macosx_11_0`) + hf-xet 3.6 MB + safetensors 0.48 MB + timesfm 0.125 MB + small pure-python deps (filelock, fsspec, jinja2, markupsafe, mpmath, networkx, packaging, pyyaml, regex, requests, tokenizers, tqdm, typing-extensions, sympy, certifi, charset-normalizer, idna, urllib3, shellingham, typer, click…). Installed venv INFERENCE ≈0.5 GB (torch is the bulk).
- **Total local disk footprint (venv + weights) ≈2 GB**, well inside the 40 GiB budget. No weights were downloaded by this leaf.
- Resolvability: **clean, no conflicts** — `timesfm 3.0.2` has no upper bound on torch/numpy and its deps are all mainstream.

## 10. What the Part-2 vision gets right, wrong, or cannot be confirmed (Q9)

| # | Vision claim (§2) | Verdict |
|---|---|---|
| 1 | ≈330 M params | **CONFIRMED** (330,710,976) |
| 2 | decoder-only | **CONFIRMED** (decoder-only head; patches in, quantiles out) |
| 3 | natively multivariate, series attended jointly | **CONFIRMED**, with a nuance: alternating **seq→variate** attention, not one joint `(V·n)²` block; and the ablation switch `use_variate_attention=False` is silently ignored (issue #502, open) → univariate-vs-multivariate must be done with separate V=1 calls, not a flag |
| 4 | patch 32 | **CONFIRMED** for input; **incomplete** — output patch is **64** with 32-step stitching, which is what makes long horizons cost more than one pass and makes stitched horizons numerically distinct |
| 5 | non-autoregressive single-pass decode | **CONFIRMED** |
| 6 | 9 quantiles 10th–90th | **CONFIRMED**; median is **index 4**, and there is **no mean output** (the vision's phrase "point forecast" = quantile 4) |
| 7 | "normalises each series internally" | **CONFIRMED** (iterative CPM RevIN per patch, `use_znorm` optional and off by default) — plus the flat-series σ-floor asymmetry (§6) that the vision does not anticipate |
| 8 | zero-shot, no task-specific training | **CONFIRMED** |
| 9 | past covariates and past-future covariates | **CONFIRMED**; past-future channels must cover `T+H` (future part supplied by the caller), so for our detector the "known future" must be a genuine exogenous schedule, not a forecast |
| 10 | licence assumed usable for the study | **PARTLY CONTRADICTED**: weights are **non-commercial, non-production** only; research use in the lab is permitted, any production/end-user use is not (§3) |
| 11 | input uncertainty variant ("box-car mean + within-box spread") | **NOT CONFIRMED — does not exist.** Point series + numeric covariate channels only (§6). The vision's §5 wording must be rewritten or dropped |
| 12 | max context unknown / "1 h, 1 day, 2 days at 15 s" | **RESOLVED**: 15,360 pts = 2.67 days; 11,520 (2 days) fits; 3 days would be silently truncated (§5) |
| 13 | "attention cost ∝ (series×patches)²" (if assumed) | **WRONG**; cost is `V·n² + n·V²`, linear in V, and attention is ≤7 % of FLOPs at our sizes (§7) |
| 14 | a GPU is available for the compute study | **NOT AVAILABLE**: the data-source node has no loaded CUDA driver; MPS/CPU (or MLX) are the real options |
| 15 | 16k context (from the 2.5 docs) | **MISLEADING**: the 3.0 code/docs cap at **15,360**, not 16,384; the "16k" figure belongs to 2.5 |

## 11. Unresolved conditions

1. **MPS execution of TimesFM-3 is unverified.** Not tested because this leaf installs nothing and downloads no weights, and because the A2 gate owns the env. Tried instead: full source read (no MPS path), upstream issue search (`mps` → only #415 for 2.5, merged/closed), HF PyTorch-2.15 MPS post. Residual risk is concentrated on masked `scaled_dot_product_attention` and `nn.RMSNorm`; the manual-attention workaround is *not* reachable from config (`use_sdpa=False` ignored, #549). A2 must smoke-test `device="mps"` and record the outcome verbatim.
2. **No published latency or memory number for the PyTorch backend at all** (the only table is MLX/M4 Max/ctx 512/h 64). Our 11,520-pt × 3-series estimate (§7) is INFERENCE and must be replaced by a measurement.
3. **The MLX backend was confirmed to exist and mirror the API** (repo `src/timesfm3/mlx/` = 12 files, ~60 KB, incl. `model_parity_test.py`), but I did not audit its `from_pretrained` signature for `revision=`/local-path support — only relevant if A2 takes the MLX fallback.
4. **No TimesFM-3 paper / no published ablation** behind the architecture claims; every statement in §2/§7 comes from the released code + config + blog, not from a peer-reviewed description. The architecture section of the workcard should cite the code, not a paper.
5. **Benchmark rank claims** (FEV-Bench #1, TIME #1, GIFT-Eval #1 among foundation models) are the vendor's own (README + blog). They were not independently checked and are irrelevant to our scenario matrix; do not carry them into the workcard as evidence of fitness on 15 s telemetry.

## 12. Commands run (all read-only; scratch under `/tmp`, deleted)

```text
curl -sS https://pypi.org/pypi/timesfm/json                      # versions, requires_python, deps, extras
curl -sS https://pypi.org/pypi/timesfm/3.0.2/json                # release URLs/sizes/upload dates
for v in 3.0.0 3.0.1 3.0.2: curl pypi json -> upload_time, wheel sizes
curl -sS "https://huggingface.co/api/models?search=timesfm-3"    # only google/timesfm-3.0-pytorch
curl -sS "https://huggingface.co/api/models?search=timesfm&limit=50"  # 2.5/2.0/1.0 repo ids + gated flags + licenses
curl -sS "https://huggingface.co/api/models/google/timesfm-3.0-pytorch"        # sha, gated, cardData
curl -sS "https://huggingface.co/api/models/google/timesfm-3.0-pytorch?blobs=true"  # sizes + blobIds
curl -sI "https://huggingface.co/google/timesfm-3.0-pytorch/resolve/main/model.safetensors"  # 1,322,898,824 B, etag
curl https://raw.githubusercontent.com/google-research/timesfm/master/README.md
curl https://raw.githubusercontent.com/google-research/timesfm/master/src/timesfm3/{configs.py,torch/{timesfm3_forecaster,model,transformer,evaluator,norm,util3}.py}
curl https://api.github.com/repos/google-research/timesfm                      # license apache-2.0, HEAD 65be4bdf5e96c60e498a1c26
curl https://api.github.com/repos/google-research/timesfm/contents/src/timesfm3/{,torch/,mlx/}?ref=master
curl https://huggingface.co/google/timesfm-3.0-pytorch/raw/main/LICENSE         # TimesFM Non-Commercial v1.0
curl https://huggingface.co/google/timesfm-3.0-pytorch/raw/main/config.json
curl https://huggingface.co/google/timesfm-3.0-pytorch/raw/main/README.md       # model card
curl https://research.google/blog/timesfm-3-a-zero-shot-foundation-model-for-multivariate-forecasting/
curl "https://api.github.com/search/issues?q=repo:google-research/timesfm+is:issue&per_page=100"  # 802 issues; filtered mps/multivariate/uncertainty/sdpa/revin
curl https://api.github.com/repos/google-research/timesfm/issues/{502,522,543,547,549}
curl https://huggingface.co/blog/mps-pytorch-2-15                              # torch 2.15 MPS state, 2026-10-20
uv venv /tmp/refm-a2-venv && uv pip install --python /tmp/refm-a2-venv/bin/python --dry-run "timesfm[torch]"
   -> py3.10: torch==2.14.1 ; py3.11 & py3.12: torch==2.15.0, numpy==2.2.4, huggingface-hub==2.4.0, 25 pkgs
rm -rf /tmp/refm-a2-venv /tmp/tfmsrc /tmp/*.md /tmp/*.html /tmp/hub.toml   # scratch removed
```

## 13. Recommendations for the Planner

1. **Write the licence into the A2 gate verbatim** (README "License notice for pretrained weights" + `timesfm-non-commercial-license-v1.0`): weights are non-commercial, **non-production**, no redistribution; local-only storage, **never** `git add` anything under the weights dir. Download needs no login/acceptance, so the gate is about *use*, not access.
2. **Budget the disk at ~2 GB** (venv ≈0.5 GB + weights 1.32 GB) and pin `timesfm==3.0.2` + `torch==2.15.0` on **python 3.12**; 3.10 silently downgrades to torch 2.14.1.
3. **Pin the checkpoint revision** `43046b85ec22d584a13f8098c2ed39c889e129c2` in the download step and record the file sha256 (`a7592b0a…d98f17da`) in the MANIFEST — the study's compute numbers must be attributable to one artefact.
4. **Design the context window as 11,520 points (2 days at 15 s)**, leaving 3,840 points of headroom; document that anything beyond 15,360 (2.67 days) is *silently truncated* to the most recent points, so 3-day+ scenarios need subsampling instead.
5. **Operate at horizon 120 (30 min at 15 s)** as the vision states; expect 4 stitched horizon patches and ~128 padded steps, and do not extrapolate the model's per-step error from a ≤32-step test (stitching changes the numerics).
6. **Drop the "input uncertainty" variant of §5 of the vision, or relabel it.** No variance/weight/noise argument exists. If the planner still wants within-box spread available to the model, it is a *covariate channel* and must be named that way in the workcard.
7. **Implementation of the univariate-vs-multivariate ablation must be by call shape** (V=1 arrays vs `(V,T)` arrays), never by `use_variate_attention=False` — that flag is ignored (issue #502, open).
8. **Take the median as `quantiles[..., 4]`** and never assume a mean column; `return_quantiles=True` must be passed explicitly (default is False).
9. **Feed covariates as `past_only_covariates` / `past_future_covariates`** with the past-future array covering `T+H`; the future part must be genuinely known (schedule/mask), which for a 30-min horizon is real only for the daily/time-of-day channels.
10. **Treat the flat control as a tie by construction:** with the σ-floor asymmetry (issue #522) a near-constant pod's forecast collapses to its own mean. That is a finding for the limitation profile, not a bug to route around.
11. **Smoke-test both `device="cpu"` and `device="mps"` in A2**, record RSS/`torch.mps.current_allocated_memory` and latency at N=240 / 5,760 / 11,520 for V∈{1,3}; if MPS fails, evaluate `timesfm[mlx]` before settling for CPU — it is the vendor's Apple path and is numerically matched.
12. **Do not plan CUDA anywhere in this campaign**: no driver on the data-source node; the compute study runs on the Mac (MPS/CPU) and must state that the FLOP-normalised "cost" is measured, not GPU-derived.
13. **Use §7's FLOP formula as the scaling law** (`2·P·V·n + 4·n²·d·L·V + 4·V²·d·L·n`) and state that cost is linear in V and near-linear in N in our range — this is what makes the "compute vs context length" panel meaningful.
14. **Do not depend on the repo's `timesfm-forecasting/` skill docs for the 3.0 API** — they describe 2.5 (`ForecastConfig`/`model.compile`, 10 quantiles, 800 MB weights, `xreg`); following them will produce a wrong harness.
15. **Carry the licence wall into Part 2's judgment section now**, not at the end: even if TimesFM-3 wins every accuracy/scaling panel, the deployed reference cannot be a non-commercial, non-production weight set, and the Apache-2.0 alternative (2.5) is univariate-only with linear-regression covariates. This is the decision E must weigh explicitly.

## 14. Open questions that need an operator decision

1. **Licence posture for the end state.** The study itself is clearly inside the non-commercial/research grant. But if the *outcome* of Part 2 is "adopt TimesFM-3 as the reference", the deployed detector would need a commercial Google Cloud route (BigQuery ML) rather than self-hosted weights. Does the operator want the study to (a) evaluate TimesFM-3 purely as an upper bound, (b) also benchmark the Apache-2.0 TimesFM-2.5 as a deployable fallback, or (c) leave the licence question to E? This changes A2/B/C's scope, so it is worth answering before the workcards are written.
2. **Compute medium for the claim about cost.** With no CUDA on the data-source node, "cost per forecast" will be measured on the Mac (MPS/CPU). If E is expected to compare TimesFM-3 against a *cluster-side* reference implementation on equal hardware, that expectation cannot be met and the operator should say how to state it instead.



