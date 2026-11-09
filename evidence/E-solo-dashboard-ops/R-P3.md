# R-P3 — calibration-mapper refit loop + degeneracy guard (research findings)

Date: 2026-11-06. Repo `pipelineml-anomaly-detector`, branch
`feature/cnn2dlstm-bayesian-statistical-detector-v2`. Read-only research: no product
file, config, cluster object or pod state was modified. Live API
`http://127.0.0.1:18086` (supervisor forward), read-only GET.

---

## 0. Contradiction / refinement check (read first)

**No contradiction of an established fact was found.** Re-verified against current
source: the mapper is fit **once** (`driver.py:1680-1703` + 1724-1726 are reachable only while
`cal_state == _warmup_state(...)`, `driver.py:1629-1674`), it is **frozen** for the pod
(`cal_state` is only ever written as `"scored"` at `driver.py:1694`; nothing demotes it),
and the live windows are near-constant in their calm mass. Three **refinements** P must
not lose:

1. **[LIVE] "near-constant `p_raw`" is true of the calm mass, not of the whole window.**
   All 10 live 288-tick windows reach `p_raw ≈ 0.99`; 8-11 % of ticks are `> 0.2`. The
   fit half of 2/10 pods (mjnlq, rzpzm) contains genuine anomalies
   (`x_(141) = 0.0748 / 0.0727`, i.e. `calm_span/π ≈ 7.3`). A degeneracy statistic built
   on `max-min` of the window is therefore wrong; it must be built on the **calm bulk**.
2. **[SOURCE] The held-out gate is already the operator's criterion** — it is
   `P(map(p_heldout) > threshold) ≤ τ` (`fusion.py:387-421`). It is **not** a
   conditioning test: a window whose `p_raw` is flat always yields exceedance 0 and
   passes. That is exactly how the 2026-10-18 window was adopted.
3. **[LIVE] `indicator_a` is already not "normal" on 7/10 pods** (`mean p_published`
   0.17-0.44; `frac(p_published < 0.2)` = 0.000-0.705). R-P2's payload caveat is
   confirmed: `inventory status` is `scored` for all 10, `analysis_state` is `ready`,
   `calibration_state` is `scored`, `probability_label` is `calibrated` for all 10.

---

## 1. Source map (current source, verified line numbers)

### 1.1 Fit / gate / state (driver)
| What | Where |
|---|---|
| `L_cal` = `fusion.calibration.gate.window` / tick; `_warmup_state` | `driver.py:291`, `:301` |
| calibration row load; `cal_state` (default = warmup state); defaults `p_published=p_raw`, label `raw` | `driver.py:1629-1636` |
| warmup block `if cal_state == _warmup_state(...)` → `read_scored_history(pod_key, L_cal)`, `window_ok`, 288/144 split | `driver.py:1644-1668` |
| held-out gate call + `cal_state="scored"` + `_fit_mapper` (**one-time fit**) | `driver.py:1669-1673` |
| one-time `warmup_assumption` provenance dict (18 keys) | `driver.py:1680-1703` |
| publication decision `if cal_state == "scored" and mapper is not None` → `_apply_mapper`; raw + label otherwise (the vision's ":1724") | `driver.py:1724-1729` |
| `details` snapshot / response analysis (`probability_label`, `calibration_state`) | `driver.py:1750-1752`, `:1821-1830` |
| restore replay reads persisted label/state verbatim | `driver.py:1965`, `:1980` |
| `anomaly` flag = `p_published > threshold` | `driver.py:1759`, `:1819` |
| `_calibration_gate_passes` (isotonic) / `_fit_mapper` / `_apply_mapper` | `driver.py:1859`, `:1888`, `:1901` |

`fusion.py`: `calibration_order_index` `:308`, `evaluate_calibration_gate` `:387`,
`fit_isotonic_calibration` `:423`, `isotonic_from_control_points` `:528`.

### 1.2 Persistence (what is stored per pod)
`solo_pod_calibration` DDL `state.py:159-173`: **`pod_key` PK, `state`, `mapper_json`,
`tau`, `updated_at`, `provenance_json`**. The fitted mapper is stored as
`{"kind":"isotonic","x":[…],"y":[…],"slope","intercept"}` — **knots only**: the fit
sample is *not* stored, `x` contains the explicit `(0,0)` and `(1,1)` anchors plus one
entry per control point, `y` is the averaged isotonic output. WAL/SQLite files:
`/app/cache/solo_mode_state.sqlite` (`deploy/k8s/solo-card6/configmap.yaml:379`,
PVC-mounted). Migration precedent (logged `ALTER`): `_migrate_pod_calibration`
`state.py:340-372`. Per-scored-tick `details_json` (includes
`probability_label` + `calibration_state`) is in `solo_pod_scored_history`
(`state.py:145-158`, depth 1d = 288 rows, `configmap.yaml:383-384`).
WAL rebuild for the exporter view: `exporter.py:2624-2700` (`_solo_restore_current`),
which calls `_persisted_analysis` and publishes with `calibrated` derived from the
persisted label (`exporter.py:2233-2235`).

### 1.3 Config schema for the calibration path
`analyser/solo_mode/config.py:714-780`: `fusion.calibration` mapping requires
`mapper ∈ {isotonic, slope_intercept}` (`:719`), `isotonic.n_bins` positive int (`:725`),
`gate` mapping with `window` (duration), `max_fare_multiple > 1.0`, `warmup_state ∈
WARMUP_STATES` (`:731-742`), plus the load-time viability checks
(`L_cal ≥ 4`, `τ = c·π ∈ (0,1)`, `m = floor((1-τ)·L_cal//2) ∈ (0, L_cal//2)`,
`:748-780`). **There is no closed-schema / unknown-key rejection** for `fusion`
(grep: only `mandatory_metrics` has an unknown-key check, `:822-826`) → a new
`degeneracy:` sub-block needs its own validator lines, not an allow-list update.
Shipped YAML: `analyser/config/detector-common.yaml:318-325` and the deployed
ConfigMap `deploy/k8s/solo-card6/configmap.yaml:352-359` (identical block).

---

## 2. The defect, verified live (10/10 pods, persisted mappers)

Data: `/api/dashboard/pods/<pod>/solo?namespace=ml-components&cluster=` history (288
ticks each) copied to `/tmp/solo-p3-r/`, plus the `solo_pod_calibration` rows read
read-only out of the pod (`kubectl exec … python3 -c \"…SELECT…\"`, sqlite3 CLI is absent
in the image) into `/tmp/solo-p3-r/calib.json`. Mapper evaluation offline with its own
knots reproduces the live `p_published` **exactly** (`map(pr_min) == pp_min` for 10/10,
e.g. b4xkt 0.001288→0.1518 vs live `p_published` min 0.1518) — the persistence path is
sound, the *map* is the artifact.

| pod | `p_raw` [min,max] | distinct | `mass(<0.25)` fit | `p_pub` [min,max] | mean | `frac<0.2` | knots | map(min)→map(max) | ramp `x@y≥0.2 − x₀` / π |
|---|---|---|---|---|---|---|---|---|---|
| b4xkt | 0.001288, 0.989522 | 92 | 1.000 | 0.1518, 0.7866 | 0.376 | 0.194 | 43 | 0.152→0.787 | **0.0000** |
| mjnlq | 0.001288, 0.989522 | 70 | 0.986 | 0.3050, 0.7682 | 0.408 | 0.000 | 34 | 0.305→0.768 | **0.0000** |
| rzpzm | 0.001288, 0.989522 | 92 | 0.986 | 0.0113, 1.0000 | 0.309 | 0.392 | 53 | 0.011→1.000 | **0.0000** |
| hcfj7 | 0.001288, 0.989522 | 75 | 1.000 | 0.3050, 0.7738 | 0.441 | 0.000 | 34 | 0.305→0.774 | **0.0000** |
| vlsl8 | 0.001288, 0.989522 | 75 | 1.000 | 0.0113, 0.8479 | 0.185 | 0.646 | 53 | 0.011→0.848 | **0.0000** |
| 2vwwd | 0.001288, 0.989522 | 98 | 1.000 | 0.0113, 0.7602 | 0.172 | 0.705 | 53 | 0.011→0.760 | **0.0032** |
| 7gjdg | 0.001288, 0.989522 | 90 | 1.000 | 0.1688, 0.7421 | 0.373 | 0.156 | 39 | 0.169→0.742 | **0.0000** |
| c5bdh | 0.001288, 0.989522 | 108 | 1.000 | 0.1518, 0.8329 | 0.370 | 0.097 | 43 | 0.152→0.833 | **0.0000** |
| m7pr8 | 0.001288, 0.989522 | 114 | 1.000 | 0.1179, 0.8448 | 0.389 | 0.087 | 45 | 0.118→0.845 | **0.0000** |
| qsv2m | 0.001288, 0.989522 | 83 | 1.000 | 0.0113, 0.7602 | 0.225 | 0.524 | 53 | 0.011→0.760 | **0.0000** |

**Count: 10/10 pods carry a degenerate frozen mapper.** The signature is identical and
machine-checkable: the persisted knots' 0→0.2 ramp has **zero x-width** (`x@y≥0.2 ==
x_data_min`) — the map is *vertical* over the calm mass (isotonic averaged 10-40 ties at
~0.0013 into one x), so a 2e-4 jiggle of `p_raw` moves `p_published` between **0.0113 and
0.85** (b4xkt: 0.152→0.787 over `p_raw` 0.001288→0.003349). 6/10 pods (`rzpzm`,
`vlsl8`, `2vwwd`, `qsv2m`, plus `b4xkt`/`7gjdg`/`c5bdh`/`m7pr8` partially) cross the 0.2
normal threshold repeatedly — the live sawtooth. Aggregated acceptance today: **0/10 pods
have `p_published < 0.2` for ≥95 % of ticks** (best 0.705, worst 0.000).
Second, independent defect signal: applying each persisted map to its own **held-out
half** gives exceedance 0.083-0.111 ≫ τ=0.02 → **the current 288-tick windows would fail
the existing gate for 10/10** — so re-running the gate alone can never lift these pods out
of the frozen map; only a guard on adoption + a migration of the persisted rows can.

---

## 3. Vision §7 — the five open questions, resolved

### Q1 — refit trigger (no new timer)

Candidates: (a) periodic at the existing scored-tick boundary once a full gate window has
elapsed; (b) event-driven on the existing `drift_stale` flag; (c) every scored tick.
`drift_stale` is **record-only** and fires on 21-34 of 288 ticks in every live window
(`driver.py:1668` merely counts it) → useless as a trigger. `read_scored_history(pod_key,
L_cal)` is already called at `driver.py:1645` and the scored-history ring is 1 d = 288 rows
(`configmap.yaml:383-384`), so a full window is always readable.

**Recommendation (a), hooked into the existing block:** change the condition at
`driver.py:1644` to `cal_state in {warmup, scored} and (last_fit_attempt_epoch is None or
tick_epoch - last_fit_attempt_epoch >= L_cal * T)`; everything after it (`window_ok`, the
288/144 split, `_calibration_gate_passes`, `_fit_mapper`) is reused unchanged.
**Cadence: L_cal = 288 scored ticks = 24 h** at T=5 min per pod — the gate window that
already exists; no new timer, key or flag. Attempt pacing lives in the calibration row
(`last_fit_attempt_epoch`) so a failed re-evaluation is not retried every tick.
**Demotion rule:** a pod that already holds a healthy mapper **keeps** it when a later
window fails gate/guard (record the attempt, change nothing); only `scored +
mapper_healthy=0` refits to 1 on success → no label flapping, `p_raw` untouched.

### Q2 — degeneracy statistic and floor

Measured on the real live samples (`/tmp/solo-p3-r/q2.py`, venv python):

| candidate | live value (10 pods) | healthy reference | verdict |
|---|---|---|---|
| dynamic range `max−min` of `p_raw` | 0.988 (all 10) | 0.99 | **blind** (accepts everything) |
| distinct-value count | 70-114 | 144 | weak, collides at the top |
| coefficient of variation | 24-35 | — | **blind** |
| mass fraction with `p_raw < 0.25` | 0.986-1.000 | 1.0 | **blind** (accepts everything) |
| calm-ramp width `x_(m) − x_(1)` | 0.048-0.125 π (8 pods), 7.1-7.4 π (mjnlq, rzpzm — real anomalies in the fit half) | 95 π (uniform 144) | **separates** |

**Recommendation — statistic:** `calm_span_ratio = (x_(m) − x_(1)) / π`, with `x_(1)`,
`x_(m)` order statistics of the fit half and `m = calibration_order_index(n, τ)`
(`fusion.py:308` — the **same primitive the fit already calls**, no new math). Meaning: the
width of the calm mass **in units of the prior anomaly rate**; the map ramps
0→`anomaly_threshold` exactly over `[x_(1), x_(m)]`, so this is its resolution over the
calm bulk. Units: dimensionless multiples of π.
**Floor: `min_calm_span_ratio: 1.0`** — live calm mass 5.0e-4/0.01 = **0.05 → reject**
(all 10 persisted maps **0.000** → reject); synthetic uniform 144-sample 0.954/0.01 =
**95 → accept**; a genuine calm spread [0.005, 0.02] → **1.5 → accept**; a window with 25 %
anomalies passes the guard but the held-out gate rejects (0.25 > τ=0.02) → **no adopt**
(both must pass). No healthy *persisted* sample exists (fit half not stored, knots only),
so the accept side is shown on the repo's own `fit_isotonic_calibration` with uniform data
plus the 2 live windows that genuinely contain anomalies.

YAML shape (add to `detector-common.yaml:318-325` **and** the deployed
`configmap.yaml:352-359`; validation next to `config.py:731-742`, required key +
`_require_positive_number`, fail-fast at load):

```yaml
    calibration:
      mapper: "isotonic"
      isotonic: { n_bins: 48 }
      gate: { window: "1d", max_fare_multiple: 2.0, warmup_state: "calibrating" }
      degeneracy:
        min_calm_span_ratio: 1.0     # calm-ramp width, in units of prior_anomaly_rate
```

The guard sits **alongside** `_calibration_gate_passes` in the same `if`
(`driver.py:1669-1671`) — both must pass to reach `_fit_mapper`.

### Q3 — state representation

**Recommendation: keep the two-state enum, add two columns** (no new state value, no
change to `probability_label`'s domain):

```sql
ALTER TABLE solo_pod_calibration ADD COLUMN mapper_healthy INTEGER NOT NULL DEFAULT 0;
ALTER TABLE solo_pod_calibration ADD COLUMN last_fit_attempt_epoch REAL;
```

`state='scored' + mapper_healthy=0` is the new *sub-state* "scored, no healthy mapper →
publish raw". `probability_label` stays `raw`/`calibrated` (`driver.py:1724-1729` is the
only place that sets it); `calibration_state` stays the persisted row's `state`.
`DEFAULT 0` is the migration: **every pre-P3 row reads 0** (see Q5b), new adopts write 1.

Every consumer, and what changes:

| consumer | site | effect for a raw-publishing `scored` pod |
|---|---|---|
| publication decision | `driver.py:1724-1729` | add `and mapper_healthy` → `p_published = p_raw`, label `raw` |
| `anomaly` flag | `driver.py:1759`, `:1819` | becomes `p_raw > 0.8` (same tri-state as warmup; spikes still flag — unchanged today because `map(0.99)=1.0`) |
| details/response replay | `driver.py:1750-1752`, `1821-1830`, `1965`, `1980` | no change (label/state replayed verbatim) |
| canonical-child gating | `exporter.py:2228-2235` | `calibrated=False` → no canonical child, fraction child published |
| stale cleanup | `exporter.py:2882-2889` | **safe as is**: reaps only `not calibrated` + *canonical child*; fraction-only pods are explicitly not stale → raw pods do not vanish |
| dashboard payload | `dashboard_routes.py:2122-2127`, `:2233`, `:2255` | `probability_label='raw'`, `calibration_state='scored'`, `probability` = `p_raw`; **`analysis_state='degraded'`** — `_solo_analysis_state` (`dashboard_routes.py:2110-2148`, used by list/current/live at `:4055`, `:4303`, `:3033`) is explicitly "raw -> degraded, never ready". Pre-existing P1 semantics (warmup pods already read degraded); P3 must accept it, not change it |
| index.html | `dashboard_assets/index.html:2449-2452`, `:2555-2563`, `:3044` | badges flip to `warn` and the chart title becomes "Published p - raw (no calibrated mapper)"; markers render raw. Display only, no code change (the copy already describes exactly the P3 state) |
| `shared_selectors.py` | grep: no `calibrated`/`probability_label` reference | no change |
| Prometheus | gauge defined `exporter.py:222`; solo canonical publication `:2228-2320`; fraction `solo_mode_degraded_fraction` | canonical gauge goes **empty for all 10** (fraction gauge keeps publishing) — accepted by the vision; `_solo_model_availability` (`dashboard_routes.py:2065-2095`) keys on `probability` presence, not on `calibrated` → pods stay `solo_statistical_available` |
| `operator_alert_state` / indicator A | `dashboard_routes.py:2733-2760` | driven by `p_published` vs 0.2/0.8 → raw calm value 0.0013 → `normal` ✓ (but the 3.5-11 % spike ticks still read `critical`, today too) |
| cold restore | `exporter.py:2624-2700` | label-driven → a raw pod restores raw with **no exporter change** (Q5a) |
| `_pipeline_status_payload` | `dashboard_routes.py:2699-2732` | `status='scored'` stays (do **not** flip raw pods to `warning` — that would re-open P1's freshness semantics) |
| dashboard pod-card status | `dashboard_routes.py:2397`, `:2637-2645` | collides with the owner's `status` field; P must keep `calibration_state` the source of truth |

### Q4 — provenance reconciliation

Keep `warmup_assumption` (`driver.py:1680-1703`) as the **last-pass** record with unchanged
keys (`healthy_reference_provenance`, `window_start_epoch`, `window_end_epoch`,
`span_seconds`, `n_ticks`, `fit_half_n`, `held_out_n`, `simes_rejects_in_window`,
`drift_warn_refits_in_window`, `gate_pass`, …); its only readers are the carry-forward in
`state.py:684-697` and the driver tests — **no dashboard/exporter consumer** (grep: none
in `exporter.py`/`dashboard_routes.py`). Add two record-only fields inside the same JSON on
each adopt: `fit_count` and `calm_span_ratio`. Attempt time stays in the new column
(`last_fit_attempt_epoch`), so pacing needs no JSON decode.

### Q5 — cold restore and migration

**(a) Restore reproduces the live path — verified, no exporter change.** `_solo_restore_current`
(`exporter.py:2624-2700`) rebuilds via `driver._persisted_analysis` (`driver.py:1916-1985`),
replaying `probability_label`/`calibration_state` verbatim from `details_json`;
`_solo_publish_analysis` derives `calibrated` from the label alone
(`exporter.py:2233-2235`). A raw pod restores raw (fraction child, no canonical child), and
the next scored tick re-reads `mapper_healthy` and re-derives the same label → test only.

**(b) Migration of the 10 live frozen mappers — the decisive finding.** The fit sample is
**not** persisted (knots only), so degeneracy cannot be recomputed from stored data; it *is*
derivable from the persisted mapper's own knots (ramp width **0.000 π for 10/10**, 0.0032 π
for 2vwwd), but the store layer has no π. **Recommended:** declare `mapper_healthy INTEGER
NOT NULL DEFAULT 0` — every pre-P3 row is by construction "not verified healthy". Rows are
rewritten each scored tick (`state.py:698-726`), so the driver's first post-rollout tick
publishes **raw for all 10 pods**, and each re-adopts when a full window passes gate **and**
guard (Q1 cadence). No data re-derivation, self-healing, matches the live acceptance.
**Before P3, on restore, the pods replay the persisted `calibrated` label** → they come back
calibrated with the degenerate map and keep sawtoothing (verified: all 10
`probability_label=calibrated` after the ~09:00 JST restart). Hence the acceptance needs the
`DEFAULT 0` migration, not only the guard; without it the 10 pods keep their frozen maps.

---

## 4. Scenario / test surface (what P3 will move)

| test (file:line) | pins | P3 effect |
|---|---|---|
| `test_isotonic_calibration_gate_and_tail` (fusion:369) | map construction + tail | keep; add `test_calm_span_ratio_*` next to it |
| `test_isotonic_calibration_healthy_heldout_passes_same_tau` (fusion:440) | healthy held-out half passes the gate | the guard's *accept* neighbour — keep |
| `test_calibration_order_index_shared_guard` (fusion:304) | `m` definition | reused by the guard, no change |
| `test_slope_intercept_calibration_*` (fusion:323-352) | affine mapper | guard must be **isotonic-only** (affine ramp spans the domain → ratio 100 π) |
| `test_calibration_warms_then_scored_on_lcal_plus_one` (driver:987) / `test_default_288tick_healthy_reaches_scored` (driver:2818) | adopt at L_cal+1 / default cadence reaches `scored` — **both override `mapper: slope_intercept`** | must still pass; they break if the guard is applied to the affine mapper |
| `test_calibration_gate_cannot_pass_before_lcal_ticks` (driver:1049), `test_warmup_state_reads_configured_value` (driver:3011) | no adopt before a full window; config plumbing | untouched |
| `test_default_288tick_isotonic_stays_calibrating` (driver:2917) | shipped default YAML leaves the pod calibrating | stays true, no edit |
| `test_dedupe_replays_persisted_details_not_current_state` (driver:946) | persisted `calibration_state` replay | the raw/calibrated split rides on it — keep |
| `test_pod_calibration_roundtrip`/`_missing` (state:419/434) | calibration row shape | extend for the two new columns |
| `test_scored_history_and_calibration_schema_migrate_with_logged_alter` (state:942) | the logged-ALTER pattern | **pins the new ALTER**; add legacy-row-reads-0 |
| `test_provenance_written_only_when_given_and_carried_forward`/`_roundtrip` (state:874/924) | provenance once + carried | update: provenance becomes last-pass + `fit_count` |
| `test_solo_calibrated_only_publication` (exporter:762) | raw-**calibrating** pod gets no canonical child | keep; **add raw-*scored* (`mapper_healthy=0`)** |
| `test_solo_restored_freshness_is_original_tick_not_now_lease` (exporter:1936) | restore-path freshness | extend to the restored-raw label (Q5a) |
| `test_criteria_*` (4) / `test_run_scenario_slow[*]` (20 params) (scenarios) | AP/decision criteria; **end-to-end calibration timing** | the slow fixtures encode "gate commits before onset" — the tests most likely to move |

Where the three required tests belong: (i) degenerate window → no adopt → raw:
`test_solo_driver.py`, new `test_isotonic_degenerate_window_stays_raw`, seeding a
near-constant `p_raw` history (`_seed_p_raw`, already used by the OOM tests), asserting
`calibrating` + `raw` + no `solo_pod_calibration` row; (ii) non-degenerate → adopt:
driver-level with a uniform-ish seeded window (or a new `scenario-fixture` YAML), asserting
`scored`/`calibrated` + `mapper_healthy==1`; (iii) cold restore of a raw pod stays raw:
`test_solo_exporter.py` (publish a raw scored tick, re-create the exporter over the same
SQLite, assert no canonical child + `raw`), **plus the migration leg** in
`test_solo_state.py` (pre-P3 schema + `scored` row → ALTER → `mapper_healthy` reads 0 → the
driver publishes raw on its next tick).

---

## 5. Environment for E (verified recipe + baseline)

`analyser/.venv_test` is unusable for the solo suites (no `sklearn`, `hickle`, `tabulate`,
`shared`). The image is python 3.10, installs `analyser/requirements.txt` + `pip install
git+https://github.com/appthrust/pipelineml-shared.git` (`analyser/Dockerfile:41-42`), and
`# [full]` adds `pydantic/kubernetes/matplotlib/tabulate/hickle/scikit-learn/requests`;
`shared` is the sibling `../pipelineml-shared` (commit `942b…`, same as the deployed image).

Minimal, repo-untouched recipe (created and verified today):

```bash
python3.10 -m venv /tmp/solo-p3-venv
/tmp/solo-p3-venv/bin/pip install -q -r analyser/requirements.txt
/tmp/solo-p3-venv/bin/pip install -q tabulate hickle requests matplotlib
cd analyser
PYTHONPATH=/Users/obenomar/Work/langGraph/appthrust/pipelineml-shared \
  /tmp/solo-p3-venv/bin/python -m pytest tests/unit/test_solo_driver.py -q
```

`PYTHONPATH` (not `pip install -e`, which rewrites the sibling tree) supplies `shared`;
`matplotlib`/`requests`/`tabulate` are needed at *runtime* by the exporter tests, not only
at import.

**Baseline (P1/P2 in the tree; `git status`: only `AGENTS.md` + `dashboard_assets/index.html`
modified — no P3 edit).**

| file | result | wall |
|---|---|---|
| `tests/unit/test_solo_fusion.py` | **20 passed** | 0.8 s |
| `tests/unit/test_solo_state.py` | **38 passed** | 0.5 s |
| `tests/unit/test_solo_window_store.py` | **35 passed** | 0.6 s |
| `tests/unit/test_solo_driver.py` | **42 passed** | 51.5 s |
| `tests/unit/test_solo_exporter.py` | **21 passed** | 11.2 s |
| `tests/integration/test_canonical_route_contracts.py` | **21 passed** | 0.5 s |
| `tests/unit/test_solo_scenarios.py -k "not run_scenario_slow"` | **36 passed** | 1.8 s |
| `tests/unit/test_solo_scenarios.py -k "run_scenario_slow"` | **1 FAILED / 19 pending**, and each of the 3 `20261012-*` params **fails at ~417-420 s** | ≈7 min each |

All four `20261012-*` slow fixtures are **pre-existing calibration-timing failures**
(`fixture_unscorable`, `solo_mode/scenarios/synth.py:1677`), measured today one process per
fixture (3 in parallel, each ~417-420 s):
`one_metric` → gate committed AFTER onset (block_end 324600 ≥ onset 270000);
`group3` → same (333300); `slow_drift` → "native healthy calibration gate never committed
(L_cal contiguous scored window absent); zero held-out denominator"; `healthy` → same class
earlier (290400, 395 s). **Budget ≈ 28 min serially (7 min × 4, parallel is fine, CPU-bound
~1.4 s/tick); deselect `run_scenario_slow` for fast loops.** P3 changes gate commit timing,
so these are the fixtures most likely to move — reconcile them as part of P3, not before.

**"Established native cold/warm restart smoke"** (gate records
`evidence/solo-mode-gates/R-card6-restart-identity.md`, `E-card6d/…`): a smoke that drives
the **real Deployment** — `kubectl -n rtx-4000-test rollout restart
deploy/pipelineml-anomaly-detector-solo` + `kubectl rollout status … --timeout 300s`, then a
read-only `curl` of `/api/dashboard/pods/<pod>/solo?namespace=ml-components&cluster=`
proving the pod key, the scored history and the calibration survive (E-card6d stores the
exact `resolve_restart`/`mtime` comparison). For P3 the same style with a different
assertion: after the restart the restored `probability_label`/`calibration_state` equals the
pre-restart value and no canonical child re-appears for a raw pod.

---

## 6. Risks P must not walk into

1. **Guard the isotonic mapper only.** `slope_intercept` is affine over the whole domain
   (ramp ≡ 1.0 → ratio 100 π) and two shipped tests adopt it
   (`test_default_288tick_healthy_reaches_scored`, `test_calibration_warms_then_scored_on_lcal_plus_one`).
2. **`p_raw` must not move.** The refit changes only *which* mapper is applied (`_apply_mapper`
   / raw passthrough) and *when* the fit runs; any recompute of `p_raw` touches the Markov
   posterior, Simes, strike window or sojourn → protected law, stop.
3. **`DEFAULT 0` is the live acceptance and it flips all 10 pods at once.** `indicator A` then
   reads `p_published = p_raw`: calm 0.0013 → `normal` ✓, but **spike ticks (3.5-11 %) still
   read `p_raw > 0.8` → `critical`**, exactly as today (`map(0.99)=1.0`). P3 does **not** fix
   indicator flicker (Issues 1/3) — do not claim it does.
4. **Canonical Prometheus gauge empties for all 10** (fraction-only path, vision §2 accepted);
   `solo_mode_degraded_fraction` keeps publishing and `_solo_model_availability`
   (`dashboard_routes.py:2065-2095`) keys on `probability` presence → pods stay
   `solo_statistical_available`. Add no warning/error counter for it.
5. **`analysis_state` will read `degraded` on every surface** for the 10 raw pods
   (`_solo_analysis_state`, `dashboard_routes.py:2110-2148`; callers `:3033`, `:4055`, `:4303`)
   and the pod-card badges turn `warn` (`index.html:2449-2452`) — this is the *pre-existing*
   warmup semantics ("raw is never ready"), already visible for warmup pods; it is not a P3
   regression, but the acceptance must not read "degraded = broken" and P must **not** rewrite
   this helper to make the pods look `ready`.
6. **`status` must stay `scored`** (`_pipeline_status_payload`,
   `dashboard_routes.py:2699-2732`); flipping raw pods to `warning` re-opens P1's freshness
   semantics and collides with the owner's `status` field.
7. **`_solo_cleanup_stale` is safe as is** (`exporter.py:2882-2889`: only `not calibrated` +
   *canonical child* pods are reaped). Keep the exporter's `calibrated =
   (probability_label == "calibrated")` label-driven (`exporter.py:2233-2235`); deriving it from
   `calibration_state` would publish raw pods as canonical.
8. **Cost is per-pod, not per-metric, and trivial.** One isotonic map per pod over the fused
   `p_raw` (`solo_pod_calibration.pod_key`); a refit is a 144-value sort + 48-bin binning + one
   gate evaluation ≈ 1 ms, once per 24 h per pod → 10 refits/day; the only new persisted bytes
   are two columns.
8. **Do not demote a healthy mapper** (a later degenerate window keeps the validated map — no
   label flapping), and **keep `provenance_json`'s keys** (`warmup_assumption` et al.) — the
   carry-forward path and two state tests decode it.

---

## 7. Summary for P / E

- **Contradictions: none.** Refinements only: the live windows are near-constant in their
  *calm mass*, not in `max−min` (8-11 % of ticks exceed 0.2); the existing held-out gate
  is the operator's criterion and already rejects the live windows (exceedance
  0.083-0.111 > τ=0.02), so **re-gating alone can never fix the 10 pods**.
- **Q1:** refit at the existing scored-tick block (`driver.py:1644`), once `tick_epoch −
  last_fit_attempt_epoch ≥ L_cal·T` → **288 ticks = 24 h**; no new timer, no new key.
- **Q2:** guard `calm_span_ratio = (x_(m) − x_(1)) / π` (uses `calibration_order_index`),
  floor **`min_calm_span_ratio: 1.0`** — rejects 10/10 live maps (0.000-0.003 π) and 8/10
  live windows; accepts a 144-sample uniform (95 π) and any calm spread ≥ 1 π.
- **Q3:** no new state value: `state='scored' + mapper_healthy=0` → publish raw
  (`mapper_healthy INTEGER NOT NULL DEFAULT 0`, `last_fit_attempt_epoch REAL`); label
  stays `raw`/`calibrated`; stale-cleanup, availability (`solo_statistical_available`),
  indicator A and restore need no logic change — `analysis_state` reads `degraded` and the
  badge `warn` by pre-existing P1 rules (raw is never "ready"); that is expected, not a bug.
- **Q4:** `warmup_assumption` stays the *last-pass* record (+`fit_count`,
  `calm_span_ratio` inside the JSON); attempt time in the new column.
- **Q5a:** restore already reproduces the live path (label-driven `_persisted_analysis`);
  only a test is missing. **Q5b: the fit sample is not persisted — migrate with
  `DEFAULT 0`**, which makes all 10 live pods publish raw on their first post-rollout
  tick and self-heal at the next window that passes gate + guard.
- **Degenerate-mapper pods live: 10/10.**
- **Tests:** baseline 20/38/35/42/21 + 21 integration + 36 fast scenarios **all pass**; the
  4 `20261012-*` slow fixtures **already fail** (`fixture_unscorable`: gate commits after
  onset / never commits), ~7 min each - the fixtures P3 must reconcile.
- **Top risks:** isotonic-only guard, no `p_raw` change, `DEFAULT 0` is the acceptance and
  flips all 10 at once, canonical gauge empties, indicator flicker on spike ticks remains.
