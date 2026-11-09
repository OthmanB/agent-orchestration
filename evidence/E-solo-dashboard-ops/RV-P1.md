# RV Review — SOLO-OPS-P1

- Date: 2026-11-06
- Disposition: accepted_with_findings
- Authority: advisory; Supervisor decides whether to act.
- Scope: `pipelineml-anomaly-detector`, `git diff -- deploy/k8s/solo-card6/configmap.yaml` only. No product files modified, no cluster access, no apply/restart/commit. Other agents' and pre-existing changes are excluded.

## Checks performed

### 1. Workcard and exact diff

Read the reviewer template, `evidence/omp-workcards/solo-ops-P1.md`, R-P1, E-P1, and the parent vision's P1 acceptance. Independently inspected the requested scoped git diff. It contains one file and exactly these three non-comment changes:

| Current file/line | HEAD | Working tree |
| --- | --- | --- |
| `deploy/k8s/solo-card6/configmap.yaml:97` | `exporter.ttl_seconds: 300` | `900` |
| `deploy/k8s/solo-card6/configmap.yaml:170` | `degraded_age_multiplier: 1.0` | `11.0` |
| `deploy/k8s/solo-card6/configmap.yaml:171` | `stale_age_multiplier: 2.0` | `13.0` |

The remaining edits are only the required header: lines 3–4 remove the obsolete `ONLY` claim and name P1; line 10 adds the values and publish/window/TTL rationale. Lines 11–12 retain the unchanged-other-values statement. No code, threshold, statistical-law, cadence, or `solo_mode` change is present in this diff. This is a scoped conclusion, not a claim that the entire shared working tree has only one dirty file.

### 2. Independent product-loader validation

Read `/tmp/solo-ops-p1/validate_configmap.py:1-30` before executing it. It extracts both ConfigMap data entries into a temporary directory, calls the actual `load_split_config` and `validate_split_config`, and asserts the exact three values, multiplier ordering, and the workcard's TTL inequality. Independently ran from `analyser/`:

```text
$ .venv_test/bin/python /tmp/solo-ops-p1/validate_configmap.py ../deploy/k8s/solo-card6/configmap.yaml
OK degraded=11.0 stale=13.0 cadence=30s ttl=900s (needs >= 720s)
```

Exit code: 0. Thus `900 >= 13*30 + 300 + 30 = 720`, with 180 s headroom against the workcard's buffer criterion. This is real offline loader/value validation, not a live freshness measurement or a statistical-law regression test.

### 3. Independent YAML/HEAD comparison

Used the repository `.venv_test/bin/python`, PyYAML `safe_load_all`, and `git show HEAD:deploy/k8s/solo-card6/configmap.yaml` for an independent in-memory comparison. Asserted exactly one YAML document, `apiVersion: v1`, `kind: ConfigMap`, the expected name/namespace (`pipelineml-anomaly-detector-solo-config` / `rtx-4000-test`), and string keys/values in `data`. Parsed the embedded `detector-common.yaml`, recursively compared every nested key with HEAD, and asserted that the difference list is exactly the three values above. Replacing that one data string with HEAD's produces full outer-object equality; `applied-models.yaml` is byte-for-byte unchanged. Also compared non-header-comment lines textually and asserted exactly three changed line pairs.

```text
OK YAML: one v1 ConfigMap; expected name/namespace; all data values strings
OK HEAD comparison: exactly 3 nested value changes; all other keys and applied-models.yaml unchanged
OK textual comparison: exactly 3 non-header-comment lines changed
dashboard.data_flow_health.degraded_age_multiplier: 1.0 -> 11.0
dashboard.data_flow_health.stale_age_multiplier: 2.0 -> 13.0
exporter.ttl_seconds: 300 -> 900
Exit code: 0
```

No `kubectl` validation was attempted. This establishes YAML parsing and the expected ConfigMap structure, not Kubernetes admission or deployment success.

### 4. Independent source semantics

- `analyser/config_loader.py:128-139,463-473`: multipliers must be numeric (not bool), finite, and positive. **The only cross-multiplier constraint is `stale > degraded`**; no upper bound, relationship to scoring-tick duration, or TTL/window inequality is enforced. `:337-338` independently requires positive-integer refresh/TTL.
- `analyser/dashboard_routes.py:2280-2331`: freshness uses snapshot `updated_at`, with strict `age > cadence*stale` checked first, then `age > cadence*degraded`. For a normally published solo entry the resulting bands are fresh through 330 s, degraded above 330 through 390 s, and stale above 390 s. At exactly 390 s it is still degraded, not stale.
- `analyser/dashboard_routes.py:2649-2695`: **both `fresh` and `degraded` map to `state: fresh`, reason `FLOW_ACTIVE`** (`:2681-2685`); missing snapshots map to stale without waiting for a threshold. Therefore 390 s, not 330 s, controls Indicator B's green window. `:2356-2386` shows these are also consumer-side eligibility states; the multipliers do not alter computed probabilities.
- `analyser/exporter.py:1251-1315`: TTL removes snapshot entries and their gauge/history eligibility, separately expires inventory/history and orphaned error rows, and prunes the detector cache. `:2833-2907` additionally removes solo variants on expiry, leaving scope, or loss of calibrated eligibility; raising TTL does not disable the non-age cleanup conditions.
- `analyser/exporter.py:588-600,3912-3955`: system freshness derives from the newest snapshot timestamp, with fresh through 30 s, degraded through TTL, and stale thereafter. The same helper also evaluates detector-cache freshness. TTL 900 consequently widens those degraded bands; it is not a 900 s green window for individual pods.
- `analyser/exporter.py:2778-2831`: cold restore now accepts persisted ticks through age 900 s instead of 300 s, but still checks current mandatory-model validity and newer persisted skip/error supersession. `:2597-2624,2680-2702` preserves the real persisted tick timestamp rather than minting a fresh timestamp. This changes current-view admission/retention, not scoring or a statistical law.

### 5. Exhaustive requested TTL-use search and consumer inventory

Ran an exact regex search for `_ttl_seconds|exporter\.ttl_seconds` across `analyser/`, excluding `.venv_test`, tests, and Python/pytest caches; repeated with gitignore disabled so ignored production sources were not silently omitted. Also searched bracket/get access to `ttl_seconds`. Because multi-file search caps matches per file, separately retrieved the complete `exporter.py` results and read the downstream bodies. All references to the main exporter TTL fall into the following groups:

| File/line | Consumer / purpose |
| --- | --- |
| `config_loader.py:338` | Positive-integer startup validation. |
| `data_processing.py:156` | Exporter configuration range validation (`>= 1`). |
| `exporter.py:476,632` | Attribute declaration and assignment from runtime exporter configuration. |
| `exporter.py:594-600` | `_derive_shared_state_freshness`: degraded/stale cutoff for snapshot and detector-cache health dimensions; calls at `:3926,3946`. |
| `exporter.py:756,822,932` | Startup/debug logging of configured TTL. |
| `exporter.py:1242-1243` | Reject polling if TTL is unconfigured. |
| `exporter.py:1259-1291` | Snapshot expiry; remove current gauge ownership/eligibility and point history. |
| `exporter.py:1298-1303` | Inventory expiry using `discovered_at`; also remove error/history rows. |
| `exporter.py:1309-1313` | Expire orphaned error rows. |
| `exporter.py:1315` | `DetectorLocalCache.prune_stale(max_age_seconds=TTL)`; `detector_cache.py:48-55` deletes old cached entries. |
| `exporter.py:2788,2804-2809` | Cold-restore documentation and persisted-tick age admission gate. |
| `exporter.py:2855,2878-2880` | `_solo_cleanup_stale` TTL comparison before invalidating owned current variants. |

Other substring hits refer to **the separate discovery cache TTL**, not `exporter.ttl_seconds`: `config_loader.py:365`, `data_processing.py:161`, `exporter.py:741,747,805,909`, `pod_discovery.py:34,42`, `config/detector-common.yaml:102`, and `solo_mode/driver.py:377,439`. Those settings are unchanged.

No use of the main TTL feeds scoring formulas, calibration, strike accumulation, Simes/Markov calculations, or decision thresholds. One nuance matters: cache retention can affect the external-mode Tier-2 fallback inventory (`freshness_orchestrator.py:57-68`); the solo poll returns before that resolution (`exporter.py:1321-1335`). Thus it is accurate to say **no scoring/statistical-law consumer in this solo package**, not that TTL has no externally visible behavior. Current-view retention, gauge lifetime, restore admission, health freshness, and history/error retention do change.

### 6. Assessment against the measured 303 s maximum

R-P1 reports 20 observed publish gaps, max 303 s, and phase groups up to about 81 s after a tick (`R-P1.md:13-17,104-119`). I used these recorded measurements; I did not remeasure the cluster.

- **Steady publishing:** 330 s leaves 27 s before even entering degraded; 390 s leaves 87 s before Indicator B turns stale. TTL 900 cannot race a continuously publishing snapshot with max age 303 s. The measured workload should therefore remain green; the source/arithmetic supports the claimed improvement, subject to actual post-rollout acceptance.
- **A stopped publisher still in scope:** [INFERENCE] with no intervening invalidation, Indicator B can remain green until age 390 s after its last snapshot, approximately 87 s after the latest expected measured next publication. It then becomes stale even though its stored score/gauges may survive until the first cleanup after age 900 s. This is a deliberate detection/retention tradeoff, not a 15-minute per-pod-green window. No tighter outage-detection SLO is specified, so this does not violate the workcard.
- **One skipped scoring tick:** [INFERENCE] a gap around 600 s is red above 390 s until the next result, roughly 210 s. R-P1 `:142-144` calls this "one tick late is not an alarm, two ticks is", but that wording is not the implemented behavior: the first missed expected publication becomes stale after the grace period, before the second expected result. The gate should use the explicit timing, not that slogan.
- **Health/global status:** [INFERENCE] a total publisher outage can leave the aggregate health chip degraded rather than stale until its newest timestamp exceeds 900 s (about 15 minutes, plus observation delay). Current score/gauge retention and restore admission also extend to 900 s. This is materially longer than the old 300 s and must be recorded in the gate, as required by the workcard. Source cleanup is poll-driven, so 900 s is the age threshold, not a guaranteed exact removal wall-clock deadline.
- **Limits:** this does not prevent red for a future healthy-but-delayed publication with a gap above 390 s, a missing/unavailable snapshot, or other legitimate invalidation. Inventory still ages from `discovered_at` and can clear `_point_history` every 900 s even for a healthy pod (`exporter.py:1298-1303`); it does not delete the current snapshot in that branch and therefore does not itself force Indicator B red. The remaining restart-specific headroom issue is finding 1.

## Findings

1. **Low, non-blocking operational/evidence limitation — the 87 s / two-poll jitter margin does not cover restored snapshots.** Locations: `deploy/k8s/solo-card6/configmap.yaml:171`; `analyser/exporter.py:1503-1524,2680-2701`; supporting evidence `R-P1.md:136-140`. Live publication stamps wall time (`exporter.py:2173`), but cold restore stamps the evaluation-tick epoch. For the measured last phase group (~81 s after the tick), [INFERENCE] the restored snapshot can reach roughly `81 + 303 = 384 s` before the next normal publish, leaving only about **6 s**, not 87 s, against the configured 390 s threshold. A further one-poll delay could therefore briefly turn a healthy restored pod red. This is not evidence that the observed steady-state workload fails P1, and it is not a regression introduced into the restore implementation; it limits the claim that these values cover two delayed polls in every lifecycle state. **Recommended action:** keep the config-only change if the Supervisor accepts that boundary, qualify the two-poll claim as steady-state-only, and explicitly observe the last phase group's first post-restart publication in the rollout gate. If restart-time two-poll tolerance is required, the Supervisor should authorize revisiting the values using tick-age plus phase, rather than treating R-P1's wall-time replay as proof for restore. No source change is requested in P1.

## Disposition rationale

The diff exactly implements the approved three-value/header-only workcard. Independent loader validation and YAML/HEAD comparisons passed, and source tracing confirms the actual green window, multiplier constraints, complete TTL consumers, absence of solo scoring/statistical-law retuning, and the intended cold-restore/health/retention side effects. I found no blocking defect in the requested steady-state freshness fix. Acceptance is advisory with one operational finding because restart-restored timestamps have substantially less jitter headroom than the steady-state replay demonstrates. The Supervisor's gate should record that limitation, the explicit 390 s per-pod stale versus 900 s retention/health timing, and the required post-rollout observation; no cluster acceptance is claimed here.
