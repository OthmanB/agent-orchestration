# Workcard: SOLO-OPS-P1 — freshness window (ConfigMap values only)

- Parent: [vision §3-P1/§5](../solo-mode-plans/solo-dashboard-operations-vision-2026-11-06.md) (2026-11-06), [supervisor prompt](../solo-mode-plans/solo-dashboard-operations-supervisor-prompt-2026-11-06.md), [R-P1](../E-solo-dashboard-ops/R-P1.md)
- Date: 2026-11-06 · Status: draft (P output; Supervisor accepts)
- Repo: `/Users/obenomar/Work/langGraph/appthrust/pipelineml-anomaly-detector`, branch `feature/cnn2dlstm-bayesian-statistical-detector-v2`

## Deviation from the vision (R-P1 verified against source; adjudicated by Main as a refinement, not re-litigated)

Vision P1-A says "raise `degraded_age_multiplier`". Source says that alone is a **no-op**: `_pod_freshness_from_snapshot` returns `stale` when `age > cadence·stale_age_multiplier`, else `degraded` when `age > cadence·degraded_age_multiplier` (`dashboard_routes.py:2307-2310`), and `_data_freshness_payload` maps **both** `fresh` and `degraded` to `state:"fresh"` (`:2681-2685`). So Indicator B's green window is `stale_age_multiplier × 30 s`. And `exporter.ttl_seconds` purges the snapshot at `age > ttl` (`exporter.py:1259`; inventory `:1298`), so a window above 300 s needs the ttl raised too. Measured cadence is one result per 300 s tick per pod (max 303 s), not 60–190 s. Hence **three** keys, one file.

## Objective / non-goals

Objective: every solo pod reads `fresh` ≥ 90 % of the time under the flat load (R-P1 replay predicts 100 %).
Non-goals: any code; `analyser/config/**` (dev defaults); `deploy/k8s/pipelineml-analyser-configmap.yaml` (external deployment); `refresh_interval_seconds`; `solo_mode.*`; thresholds/statistical laws; applying to the cluster, restarting anything, committing (Supervisor/S do those).

## Exact change — `deploy/k8s/solo-card6/configmap.yaml` only (inside `detector-common.yaml: |`)

| Key | Line | Now | New |
| --- | --- | --- | --- |
| `exporter.ttl_seconds` | 96 | `300` | `900` |
| `dashboard.data_flow_health.degraded_age_multiplier` | 169 | `1.0` | `11.0` |
| `dashboard.data_flow_health.stale_age_multiplier` | 170 | `2.0` | `13.0` |

Arithmetic: 11.0×30 = 330 s (= 303 s + 27 s); 13.0×30 = 390 s green window; ttl 900 ≥ 390 + 300 (one tick) + 30 (poll) = 720.
Constraints (loader, `config_loader.py:463-473`): both multipliers finite and > 0, `stale > degraded`, no upper bound. The loader does **not** check ttl against the window — the validation script below does.

**Header comment (lines 1-11) must stay truthful.** It currently says "with ONLY the workcard-mandated standalone adaptations (card-6d step 3)" — that becomes false. Change that clause to "…the workcard-mandated standalone adaptations (card-6d step 3) plus the solo-ops P1 freshness values", and add one bullet to the list (after line 9) stating: `exporter.ttl_seconds 300 -> 900`, `data_flow_health degraded 1.0 -> 11.0 / stale 2.0 -> 13.0`; why (each pod publishes once per 300 s scoring tick, measured max 303 s; UI-green window = `stale_age_multiplier × refresh_interval_seconds` = 390 s; `ttl_seconds` must exceed it by one tick + one poll or the snapshot is purged first). Keep the "All other values … UNCHANGED" sentence (still true). Comments go in the header, outside the `|` block.

## Preserved invariants

- No code, no schema, no other key changes (vision §5: no retuning). `applied-models.yaml` entry in the same ConfigMap untouched.
- Protected `ml-components` pair, tester, `baseline_constant_small`: not referenced.

## R findings that matter

- Side effects of `ttl_seconds` 300→900 (same ConfigMap, no code): health-panel freshness chip's `degraded` band widens 300→900 s (`exporter.py:593-600`); inventory/error rows and `_point_history` survive 3 ticks instead of being wiped each cycle (also what empties the pod timeline, report Issue 8); **P found one more consumer R did not list**: the cold-restore age gate `_solo_restore_eligibility_gate` (`exporter.py:2804-2809`) now accepts a persisted tick up to 900 s old instead of 300 s. Not a threshold/statistical law; RV records it.
- `last_seen_data_age_seconds` is not the freshness clock (R-P1 C4); do not use it to judge acceptance. Use `data_freshness_state`.
- Values are read at process start; the ConfigMap is a directory mount with no watcher → S must `rollout restart` the **solo Deployment only** (never the tester pods).

## E acceptance (no cluster access needed or allowed)

From `analyser/`:
1. `git diff --stat` lists only `deploy/k8s/solo-card6/configmap.yaml`; `git diff -U0` shows exactly the 3 value lines + the header-comment edits.
2. `.venv_test/bin/python /tmp/solo-ops-p1/validate_configmap.py ../deploy/k8s/solo-card6/configmap.yaml` prints `OK degraded=11.0 stale=13.0 cadence=30s ttl=900s (needs >= 720s)`.
   (Scratch, verified by P: it writes the ConfigMap's two data entries to a temp dir and runs `load_split_config` + `validate_split_config` — the exact startup sequence of `api_layer.py:455-456` — then asserts the three values, `0 < degraded < stale`, and `ttl ≥ stale×cadence + 300 + cadence`. On the pre-edit file it passes the loader and fails the value assert, as expected.)
3. Write `agent-orchestration/evidence/E-solo-dashboard-ops/E-P1.md`: the two command outputs, nothing else. No `kubectl`, no apply.

## RV checklist

- [ ] Diff = one file, 3 values + header comment only; header no longer claims "ONLY"
- [ ] Validation script output pasted; ttl inequality holds
- [ ] No other ConfigMap (external, dev `analyser/config`) touched
- [ ] ttl side effects (chip band, cold-restore gate 900 s) noted in the gate record

## Gate / dependents

Gate: `/Users/obenomar/Work/langGraph/appthrust/agent-orchestration/evidence/solo-mode-gates/SOLO-OPS-P1.md` (≤ 200 lines; record rollout timestamp, 3–5 min `/api/dashboard/pods` observation: per-pod `data_freshness_state == "fresh"` fraction ≥ 90 %, no red→green→red cycling; correct report §1's "60–190 s" with the measured 300 s in the gate, not in the report).
Unlocks: ships together with the P2 image in one solo rollout (vision §4); P3 unaffected.

## Open points P resolved

- Three keys instead of one: R-P1 C2/C3 verified in source (anchors above are current; R's `2304-2310`/`1258-1260` are off by 1–3 lines).
- ttl value 900 (R's): smallest round number ≥ 720 with headroom; no upper bound exists.
- Validation by running the product loader on the ConfigMap content (offline, no new test file) rather than a YAML-only parse.
