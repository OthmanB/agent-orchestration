# E-P1 — SOLO-OPS-P1 completion record (freshness window, ConfigMap values only)

Date: 2026-11-06 · Repo: `pipelineml-anomaly-detector` @ `feature/cnn2dlstm-bayesian-statistical-detector-v2`
Workcard: `evidence/omp-workcards/solo-ops-P1.md` · Only file modified: `deploy/k8s/solo-card6/configmap.yaml`

## E acceptance 1 — `git diff --stat` (from `analyser/`)

```
$ git diff --stat
AGENTS.md                            |  8 ++++++++
 deploy/k8s/solo-card6/configmap.yaml | 11 ++++++-----
 2 files changed, 14 insertions(+), 5 deletions(-)
```

Fidelity note: the `AGENTS.md` entry is a pre-existing uncommitted modification in the working tree (unrelated to this workcard, explicitly out of my scope, left exactly as found). It predates this change; nothing in this workcard touches it. Scoped check:

```
$ git diff --stat -- deploy/k8s/solo-card6/configmap.yaml
 deploy/k8s/solo-card6/configmap.yaml | 11 ++++++-----
 1 file changed, 6 insertions(+), 5 deletions(-)
```

## E acceptance 2 — validation helper (from `analyser/`)

```
$ .venv_test/bin/python /tmp/solo-ops-p1/validate_configmap.py ../deploy/k8s/solo-card6/configmap.yaml
OK degraded=11.0 stale=13.0 cadence=30s ttl=900s (needs >= 720s)
```

Exit code 0. (Loader `load_split_config` + `validate_split_config` pass on the edited ConfigMap; value asserts hold: `11.0 < 13.0`, `ttl 900 ≥ 13×30 + 300 + 30 = 720`.)

## Exact diff hunk summary — `deploy/k8s/solo-card6/configmap.yaml` (`git diff -U0`, 6 insertions / 5 deletions, 4 hunks)

| Hunk | Location | Change |
| --- | --- | --- |
| `@@ -3,2 +3,2 @@` | header lines 3–4 (outside the `\|` block) | `...with ONLY the / # workcard-mandated standalone adaptations (card-6d step 3):` → `...with the / # workcard-mandated standalone adaptations (card-6d step 3) plus the solo-ops P1 freshness values:` |
| `@@ -9,0 +10 @@` | header, new line 10 (after the card-6d bullet list) | `+` bullet: `solo-ops P1 freshness values: exporter.ttl_seconds 300 -> 900, data_flow_health degraded 1.0 -> 11.0 / stale 2.0 -> 13.0` (with the workcard's why: publish once per 300 s scoring tick, measured max 303 s; UI-green window = `stale_age_multiplier × refresh_interval_seconds` = 390 s; ttl must exceed it by one tick + one poll or the snapshot is purged first) |
| `@@ -96 +97 @@` | `exporter:` | `ttl_seconds: 300` → `ttl_seconds: 900` |
| `@@ -169,2 +170,2 @@` | `dashboard.data_flow_health:` | `degraded_age_multiplier: 1.0` → `11.0`; `stale_age_multiplier: 2.0` → `13.0` |

The header's "All other values … UNCHANGED" sentence is kept (still true). No other keys, no `applied-models.yaml` entry, no code, no other ConfigMap touched. No `kubectl`/apply, no commit.
