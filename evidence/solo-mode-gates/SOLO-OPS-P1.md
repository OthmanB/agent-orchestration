# SOLO-OPS-P1 — freshness window — Gate Record

- Date: 2026-11-06 · Status: **promoted** (acceptance measured live)
- S: `anthropic/claude-sonnet-5-5` (main session). R/P/E/RV configured per `omp/subagent-setup.md` (researcher deepseek-flash, planner sonnet-5.5, executor local qwen, reviewer gpt-6.1-sol); actual runtime models not independently verified by S.

## 1. Context
- Parent: vision §3-P1 / supervisor prompt (P1). Workcard `evidence/omp-workcards/solo-ops-P1.md`. Shipped in ONE solo rollout together with the P2 image (vision §4), so there was no separate restart.

## 2. Evidence
- **R (R-P1.md) re-measurement — updates the vision/report (recorded here, documents untouched):** per-pod publish interval is **~300 s, not 60–190 s** (20 intervals: min 300, median 301, p95/max 303 s); all 10 pods publish once per 300 s scoring tick in 3 phase groups (+19.5 / +49.5 / +81 s). Root cause (window < arrival interval) is confirmed and stronger than stated. Not treated as hard stop 1: the supervisor prompt names "a re-measured arrival distribution" as a gate-record finding; the mechanism and the P1 fix class are unchanged.
- **Further R findings (all source-verified by P and RV):** (a) the UI-green window is `stale_age_multiplier × 30 s` — `fresh` and `degraded` both map to `state: fresh` (`dashboard_routes.py:2681-2685`), so raising only `degraded_age_multiplier` is a no-op; loader requires `stale > degraded` (`config_loader.py:463-473`), no upper bound; (b) `exporter.ttl_seconds` (300) purges the snapshot at `age > ttl` (`exporter.py:1259`), i.e. at the arrival boundary, so a window > 300 s needs ttl raised too; (c) `last_seen_data_age_seconds` is not the freshness clock (shadow `discovered_at` resets) — acceptance uses `data_freshness_state`.
- **Change (commit `e887f68`, one file `deploy/k8s/solo-card6/configmap.yaml`, values only):** `data_flow_health.degraded_age_multiplier` 1.0→**11.0** (330 s), `stale_age_multiplier` 2.0→**13.0** (390 s green window), `exporter.ttl_seconds` 300→**900** (≥ 390+300+30 = 720). Header comment kept truthful. `exporter.ttl_seconds` is snapshot-retention config, not a threshold/statistical law (RV traced every consumer: dashboard/exporter retention, health chip band, cold-restore age gate 300→900 s; none feeds scoring/calibration/strike/Simes/Markov).
- E: validation helper `/tmp/solo-ops-p1/validate_configmap.py` (product `load_split_config`+`validate_split_config`) → `OK degraded=11.0 stale=13.0 cadence=30s ttl=900s (needs >= 720s)` (E-P1.md, re-run independently by RV).
- Live ConfigMap vs repo before apply: identical to pre-P1 HEAD (`applied-models.yaml` and `detector-common.yaml`); diff live→new = exactly the 3 keys.
- Applied `kubectl apply -f configmap.yaml` (solo ConfigMap only) then `set image` (below) → one pod restart.

## 3. Review
- RV-P1 (`E-solo-dashboard-ops/RV-P1.md`): **accepted_with_findings**. One advisory finding: right after a restart the restored snapshot's freshness headroom can be small (~6 s) until the pod's next publish. S decision: accepted/recorded; observed live effect below (restart at 08:56Z; all pods fresh in the 09:03 measurement window, see §4).

## 4. Acceptance measurement (the actual numbers)
Rollout: `set image` 2026-11-06T08:50:06Z; new pod container started 08:56:21Z (6 min image pull), Ready ≤08:57Z.
Observation: `GET /api/dashboard/pods` every 10 s, **09:03:02Z → 09:09:12Z (38 samples/pod, 380 pod-samples, covering a full 300 s tick cycle incl. the 09:05 publish wave)**, via the supervisor-owned forward to the new pod (the user's 8080 forward died with the Recreate; not renewed). Raw: `E-solo-dashboard-ops/S-P1-live-samples.jsonl`.
- `data_freshness_state == fresh`: **380/380 = 100 %** (each of the 10 pods 38/38); `indicator_b_state fresh` 100 %; **0 freshness state transitions** (no red→green→red cycling). Baseline before P1 (R-P1): 16.2–18.9 % per pod. Criterion ≥ 90 % per pod: **met**.
- Not exercised: a deliberately silent pod (stale detection at >390 s) — not needed for acceptance.

## 5. State / Next
- P1 terminal: promoted. Report §1 text ("60–190 s", "fresh if age ≤ 1.0×30 s") stays uncorrected by design (documents are the record); this gate carries the correction.
- Protected pair before/after for this rollout: see SOLO-OPS-P2.md §4 (identical).
- Next: P3 (R→P→E→RV) after P2 proof — P2 live proof complete, P3 R dispatched.
