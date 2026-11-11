# SOLO-REFM-2 — TimesFM-3 candidate reference (Part 2: compute/scaling/power, accuracy, judgment) — Gate Record

- Date: 2026-11-09 → 2026-11-11 · Status: **PROMOTED WITH ONE OPEN ITEM** (recommendation delivered; the Mac CPU-class B1/B2 measurements are NOT done — environmental blocker §4; independent review of the final stage-2 results queued/in progress: `RV-Phase-E.md`)
- S: `anthropic/claude-sonnet-5-5`. Log: `evidence/E-reference-model-study/CAMPAIGN-CONTEXT.md`.

## 1. Context
- Spec: supervisor instruction Phases A2, B, C, (D), E + Part 2 vision; acceptance against the Part-1 yardstick (SOLO-REFM-1). Operator additions: D-A three-class semantics, D-E cand-B, D-F hardware-normalized read-off, D8 (TimesFM-3 regular-grid only).

## 2. Evidence
- **Research/licence:** `R-A2.md`; weights `timesfm-non-commercial-license-v1.0` (non-commercial, non-production, no redistribution; local research use only; never committed): a deployment would need a commercial licence. TimesFM-3: 330 710 976 params, ctx cap 15 360, no input-uncertainty interface (Part-2 §5 spread variant not implementable), univariate = call shape only.
- **Phase B (compute/power):** B1 CUDA 36/36 cells (`7cbda00`), measured FLOP count / analytic law = 0.9995; B2 CUDA remeasured clean after review fixes `c74e59e` (batched variant measured): pods per 300 s tick at 2-day context, sequential/overlap/batched = 429 / 706 / 1 429 (extrapolated, two validated); D-F normalized: per-pod 1 017.9 GFLOP, 294.7 pods/TFLOP/s/tick (closed form), 10–15 J/pod; Phase D not entered (budget not binding beyond ~10 pods on the GPU). **Mac cpu/mps/mlx B1/B2: NOT run** (§4).
- **Phase C (accuracy):** 118 TimesFM units on CUDA (S-run, D17) incl. 20 real units regenerated with causal contexts after RV-C F1; C3 profile/masking/real flat `9277c0d` + note; C4 calibration tables/13 figures + note; cand-B 180 arm-runs `cdb74e7` + note (verdict regressed).
- **Phase E:** `markdown/part2-recommendation.md` — do not adopt TimesFM-3 for production (licence wall; small mixed detection advantage: better flat calibration, ties on bursts, slower on drift, MAE gains on S7/S8 do not change decisive occupancy); do not adopt cand-B as measured; keep A; levers = ESS guard and noise-law/chain response.
- **Flat control re-asserted unchanged:** see SOLO-REFM-1 §2 (production untouched; live 10/10 pods normal).

## 3. Review
- RV-A2-A3 (A2 accepted_with_findings), RV-B (B1 accepted_with_findings; B2 stages rejected first pass: F1 calibration collapse, F2 D8 regular grid → fixed and remeasured), RV-C (C1/C3 rejected first pass: F1 future-sample leak in real contexts, F4/F5 masking probe, F6 flat verdict → all fixed; RV-C2 accepted_with_findings: data + libraries safe on the frozen matrix), RV-DB, RV-CB-DF-P6 (cand-B/D-F/P6 plan accepted_with_findings; doc corrections applied `fe195ee`, `166bb4b`). Pending: `RV-Phase-E.md` (stage-2 results, cand-B CB-4, recommendation text).

## 4. State
- **Open — Mac CPU-class measurements (mandatory per operator D-F, not trimmed):** the exclusive window could not be obtained on 2026-11-11 04:50–06:25 JST: the B1/B2 hygiene gate aborted 12 times (per-process CPU of the operator's terminal `iTerm2` ~110 %, `WindowServer` ~16 %, Spotlight `corespotlightd` 114–132 % indexing, load1 2.4–5.5 with idle CPU otherwise); no measurement was taken, no result file produced, no gate threshold loosened in committed configs (throwaway copies with a corrected top-sampling and load check were tried and also blocked by the terminal's CPU). Resumable procedure: HANDOVER-2026-11-11.md.
- **Held by design:** P6 (SQLite retention + scored-tick durability, production, local commits only): cards reviewed and ready (`solo-ops-P6*.md`, RV accepted_with_findings); E not started (needs the lab parity re-pin step afterwards).
- Operator-owned follow-ups listed in the recommendation roadmap.

## 5. Next
- Operator: read `part2-recommendation.md`; schedule the Mac window (HANDOVER); decide P6 start. S: on the Mac data, regenerate the D-F table and append the CPU-class addendum; RV-Phase-E findings → disposition.
