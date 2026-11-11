# SOLO-REFM-1 — reference-model scenario campaign (Part 1: limitation profile) — Gate Record

- Date: 2026-11-09 → 2026-11-11 · Status: **PROMOTED** (limitation profile delivered, three-class re-expression reviewed; open caveats §4)
- S: `anthropic/claude-sonnet-5-5`. Context, decisions D1–D17 / D-A..D-F / D-S1..D-S9 and the leaf table: `evidence/E-reference-model-study/CAMPAIGN-CONTEXT.md`. Lab repo `pipelineml-model-exploratory-work` (local only, no remote).

## 1. Context
- Spec: supervisor instruction 2026-11-09 Phase A1 + Part 1 vision. Deliverable: limitation profile (reference fidelity, detection latency, undecided/decisive occupancy, settling) on S1–S8 + FLAT with figures, a faithful reference library, packaged data. Part-1 yardstick = `p_raw` (D2/C8), three-class vocabulary (operator D-A): <0.2 decisively normal, 0.2–0.8 undecidable, >0.8 decisively anomalous.

## 2. Evidence
- R: `R-A1.md` (source map, 8 contradictions C1–C8; resolved by building a **faithful port** instead of the vision's toy `generate.py`), `R-A3.md` (data source), `R-candB.md`.
- A3 data: 10 pods × 11 metrics, raw irregular series (mean 16.4 s), parity oracle, P3 ticks; hardened after review (identity re-verified 110/110, NaN/read-only SQL/YAML fixes). Lab `b1707f7`, `6d3c6e0`, `d93d228`.
- A1a faithful port + **bit-exact parity** vs pinned production (`5bcc7f9`): P0–P3 max|Δ| = 0.0; real-data P4 0 unexplained p-family mismatches after a 48-tick prefix with an environment-event replay (detector state loss at t0 = 2026-11-08T11:00Z = detector pod recreation). `b588eb6`…`ca0fd63`.
- A1b scenarios S1–S8 + FLAT (raw-first, within-block dither, 11-metric production shape D12, pure-Poisson packets D13). `26acad5`…`d41c91f`.
- A1c harness/plots/profile; D-B re-expression in three-class units with decisive-anomaly mechanism taxonomy (injected / post-gate / fresh-model noise): 180/180 `p_raw` digests identical to the pre-cutover run; mechanism counts per scenario in the campaign log. `7bbe268`…`1d7571a`, fixes `fb8b53a`.
- Headline measured facts (`part1-limitation-profile.md`): the former "FPR at 0.2" on S1 was 94 % decisive-anomaly; the ESS sample-sufficiency guard (floor 36, in the STL-lite fit path) leaves no model on ~45 % of S1 cycles (714/1872 ticks scored) and S2 drift windows are gated 35 %; real flat 0.9866 decisively normal; synthetic FLAT 0.959–0.971 per seed (calm false 5/5, reported not tuned); S4-real: 2/10 pods reproduce the recorded fleet-wide episode (it has no metric counterpart: detector-side).
- Flat control re-asserted at the end (read-only): production repo HEAD `5bcc7f9`, unchanged (`git status`: only the 3 pre-existing paths); live solo pod `…-solo-64676d88bf-5jqgv` family: 10/10 pods `alert_state normal`, indicator A normal, B fresh (2026-11-11 JST morning); no threshold, strike, fusion, calibration, sojourn or prior was touched at any time.

## 3. Review
- RV-A1 (A1a/A1b/A1c): accepted_with_findings, F1–F4 → fixed or adjudicated (gold fixture D16). RV-DB: accepted_with_findings, F1–F4 fixed `fb8b53a` (per-tick injected rule, onset in lookback, label visibility, sensitivity prose). RV-A2-A3: A3 rejected on first pass (identity check, NaN, read-only SQL, YAML, docs) → fixed and re-verified `d93d228`.
- Executor models: configured Qwen throughout except the D15 window (see §4).

## 4. State, deviations, not-exercised
- **D15 deviation (recorded, closed):** S used an unlawful role `live-openai` for 4 measurement jobs and a session-only Sonnet override of the executor model for 12 jobs (A1a/A1b/A1c slices among them). Operator corrected; reverted; all affected work independently reviewed (RV-A1, RV-B); no defect attributed to the swap.
- Not exercised: real anomaly data (none exist); production calibration mapper (out of the p_raw yardstick); the vision's drift-precision target is limited by the guard.
- Open: S1 quiet-tick decisive occupancy common to all references (cause unresolved); caption items `not_derivable` (5) in the regression JSON.

## 5. Next
- Part 2 (SOLO-REFM-2) closed the three-way A/B/C judgment; operator reads `reference-model-study/markdown/part2-recommendation.md`. Orchestration-repo records were committed locally (no push) on the operator's "end of the implementation" signal, 2026-11-11.
