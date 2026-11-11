# RV Review — SOLO-REFM / A2 + A3

- Date: 2026-11-09. Reviewer: RefmRVA2A3. Findings are **advisory**; S decides the gate.
- Overall disposition: **rejected**.
- A2 disposition: **accepted_with_findings** (evidence bookkeeping; no blocking access-layer defect found).
- A3 disposition: **rejected** (the required single-identity hard check is not implemented faithfully; additional oracle false-positive and read-only-enforcement weaknesses).
- Reviewed cards `refm-A2.md`, `refm-A3.md`; research `R-A2.md`, `R-A3.md`; executor evidence `E-A2.md`, `E-A2-live.md`, `E-A3.md`; campaign context and supervisor invariants; lab commits `150c0ad`, `1983666`, `eb49314`, `b1707f7`, `6d3c6e0` and their owned source/tests/results/docs. Other leaves' uncommitted work was excluded.
- Lab paths below are relative to `pipelineml-model-exploratory-work/`; `src/`, `tests/`, `scripts/`, `config/`, `results/`, `data/` abbreviate its `reference-model-study/`. Evidence paths are relative to `agent-orchestration/`.

## Findings

### F1 — blocker — A3 silently discards multiple identities, then certifies one

**Location:** `src/refstudy/data/package.py:417-421,477-483,518-520`; missing regression coverage in `tests/test_data_package.py:123-127`.

`fetch_series` constructs the complete sets of container/name identities but immediately reduces each with `next(iter(...))`. `Series` carries only these scalars. `validate_series` then unconditionally sets `n_name = n_container = 1`; it cannot reject a restart/multi-identity selection. `write_series` subsequently writes the arbitrarily selected identity on **every row**, losing the source identities. This violates the card's required `n_name != 1` / `n_container != 1` rejection and makes manifest identity assurance circular. It is not evidence that the actual export has multiple identities; it means the claimed hard check cannot establish otherwise.

**Executed counterexample:** a 480-row otherwise-valid source, alternating `identity-A`/`identity-B`, passed `fetch_series` → `validate_series`:

```text
MIXED IDENTITY accepted: {'rows': 480, 'n_name': 1, 'n_container': 1, 'name_id': 'identity-B'} input distinct names=2
```

**Fix:** preserve/check identity cardinalities before reducing to a scalar; reject multiple identities with pod/metric/check named in the exception, and only write a uniform identity after proving it. Add a fetch-through-validation test using two nonempty names (and two containers), not just a wrong scalar container. Re-establish the existing export's source-identity assurance independently, because the written CSVs already contain rewritten scalar identities.

### F2 — should-fix — A3 accepts NaN counter observations as exact parity

**Location:** `src/refstudy/data/oracle.py:186-205,329,341-343,364-365`; `decode_oracle:464-475` explicitly permits non-finite JSON constants.

`_rel_diff(finite, NaN)` returns NaN. `_counter_reproduces` rejects only when `diff > rel_tol`, which is false for NaN; matching attribution then returns true. The later `max(existing, NaN)` can leave the reported maximum at zero. Thus an oracle with an invalid observation receives a successful parity certificate.

**Executed counterexample:** replaced CPU `observed` with NaN on all three selected synthetic ticks, leaving their attribution unchanged:

```text
NaN observed counter accepted: {'exact': 3, 'lag-explained': 0, 'unexplained': 0} max_rel_diff= 0.0
```

**Fix:** reject non-finite observations, reproduced values, and numeric attribution fields before comparison; make a non-finite difference fail closed. Add NaN/Infinity negative tests for both laws. Existing perturbation tests exercise only finite +1% errors.

### F3 — should-fix — “lag-explained” is not independent proof of ingest lag

**Location:** `src/refstudy/data/oracle.py:344-355,396-419`; `tests/test_data_oracle.py:120-150,230-254`; `markdown/data-packaging.md:51-55`; `evidence/E-reference-model-study/E-A3.md:192-201`.

The counter branch replays raw truncated at the oracle's recorded `last_stamp` and checks value **and** `n_increments/first_prev/last_stamp`; this is materially stronger than value-only matching and does not admit an arbitrary scaling/error in the included increments. The gauge branch, however, tries dropping 1, 2, or 3 trailing samples **until the target value matches**, with no independently observed gauge cutoff. A genuine gauge boundary/omission-law error producing that same prefix mean is indistinguishable from ingest lag and passes. Counter truncation also does not independently establish the cause of missing trailing samples or bound the held-back count before accepting it.

**Executed counterexample (finite, no lag evidence):** changed a synthetic gauge oracle to the erroneous all-but-newest mean while keeping the complete raw series:

```text
WRONG gauge oracle (drops newest sample, no ingest evidence): correct= 1134.75 wrong= 1134.5 classification= {'exact': 2, 'lag-explained': 1, 'unexplained': 0}
```

The amendment was explicitly approved by S, so this finding is a limitation of the resulting proof, not an allegation that E ignored the approved amendment. The current gauge test deliberately enshrines this acceptance; the broad spot-check fixture also derives its oracle via the same `block_value` function being tested. Hand-computed unit tests do separately cover boundary/reset/gap semantics.

**Fix:** require an independent ingestion cutoff/provenance to call the mismatch explained; otherwise report it as a lag-*compatible* ambiguity rather than confirmed parity/cause, and have S explicitly disposition it. Add an independently computed wrong-boundary negative case. Do not advertise the current heuristic as unable to hide a real law mismatch.

### F4 — should-fix — GET-only transport is not enforced read-only SQL

**Location:** `src/refstudy/data/greptime.py:33-43`.

All inspected packaging call sites construct SELECTs, and both SQL/oracle HTTP clients explicitly use GET. However, `GreptimeClient.query` forwards arbitrary SQL without restricting statements; therefore the stronger requested assertion “no write was possible via the client” cannot be confirmed from this implementation. Using GET does not itself validate the SQL text. No actual cluster mutation was observed or attempted.

**Executed transport-only counterexample:** with `urlopen` replaced by an in-memory capture (no network), `query('DELETE FROM "synthetic_table"')` forwarded:

```text
('GET', 'http://invalid.example/v1/sql?db=public&sql=DELETE+FROM+%22synthetic_table%22')
```

**Fix:** enforce the narrowly needed single-statement read interface, and/or use independently enforced read-only database permissions if “cannot write” is the required guarantee. Add a test that rejects a mutation before opening the URL. Until then describe the proven property as “the exercised call paths issued SELECTs using GET,” not mutation impossibility.

### F5 — should-fix — A3 bypasses YAML-first required-key discipline

**Location:** `src/refstudy/data/oracle.py:291,320,398,431-433`; `scripts/package_flat_load.py:103`; `src/refstudy/data/package.py:311-316`.

The predecessor guard hardcodes `35.0` despite `validation.counter_max_gap_s` already being configurable. The gauge lag search hardcodes `(1,2,3)` without a YAML setting. Nested `spot_check.law` entries are neither required nor type/value validated, and `.get(..., suffix-derived-default)` silently supplies a missing law. This contradicts the card's required-key/no-hardcoded-tunable discipline, rather than being a formatting preference.

**Executed check:** removed `spot_check.law.cpu` from an in-memory copy of the parsed YAML; `load_settings` accepted it:

```text
Missing spot_check.law.cpu accepted: {'mem': 'gauge', 'rx_bytes': 'counter', 'tx_bytes': 'counter'}
```

**Fix:** use the existing configured tick/gap consistently in eligibility/warnings; put any retained lag-search bound in YAML; require and validate the per-continuous-metric laws (or obtain explicit S approval for a different suffix-only contract). Add missing/mistyped nested-law and non-default-gap tests.

### F6 — should-fix — A3 evidence/doc falsely say there are no >35-second raw gaps

**Location:** `markdown/data-packaging.md:30-33`; `evidence/E-reference-model-study/E-A3.md:85-90`. Contradiction: `data/packaged/MANIFEST-flat-load.json:448-452` and the following seven mjnlq network entries through line 599; `throwaway/a3-package.log:61-75`.

The evidence says `n_dt_gt_counter_max_gap = 0` in all 110 files and the doc concludes the 35-second law is never hit. The manifest correctly records **one gap in each of eight mjnlq network files**. I independently loaded `mjnlq.rx_bytes`: timestamps `1794162138.037` → `1794162173.579` differ by **35.54200005531311 s**, exceeding the configured 35 s. This is still below the packaging hard limit of 60 s, so it is not itself a packaging failure; it matters to downstream counter-block validity.

**Fix:** correct both evidence/doc statements, identify the affected files/interval, and distinguish the 60 s packaging bound from the 35 s counter invalidation law. Do not discard or resample that interval. Also qualify the doc's general “~17% ingest lag” cause assertion: this leaf's sample is 6 lag-compatible comparisons out of 120, while the ~15–16% null network-attribution counts are a different population and do not prove that cause.

### F7 — nit — A2 live evidence contains stale identifiers/time labels

**Location:** `evidence/E-reference-model-study/E-A2-live.md:25-28,36,112`.

The final reviewed live commit is `eb49314`, as documented by A3's rebase evidence (`E-A3.md:219-224`); the live record still calls it `97de27d`. Its `13:22 UTC`/`13:24` labels also do not match the local +0900 execution chronology: the surviving MPS/MLX logs are 13:30/13:31 local, and the manifest refresh is `2026-11-09T04:31:58+00:00`.

**Fix:** retain pre-rebase hashes only as explicitly historical identifiers, name `eb49314` as final, and make the timezone labels consistent. The device outcomes and tabulated parity/latency values themselves match the saved JSONs.

## Checks performed and literal results

### Common scope and hygiene

- Inspected `git log --stat -1 <hash>` / `git show --stat <hash>` for all five requested commits. Counts: A2 code **13 files**, CPU results **2**, live results **3**; A3 code **11**, data manifest/doc **2**. All are leaf-owned lab paths; no production detector files. No commits/pushes were made by this review.
- Inspected `git ls-files` and `git log --all --stat` (including all-ref merge diffs). Case-insensitive sensitive-path matches were **only** the original zero-byte `reference-model-study/artifacts/.gitkeep` and `reference-model-study/data/raw/.gitkeep`. No weights, `.safetensors`, artifact payloads, or raw-data payloads appeared. This is an explicit scaffold exception, not a claim that literally no tracked pathname contains `artifacts/` or `data/raw/`.
- `shasum -a 256 artifacts/timesfm3/model.safetensors`:

```text
a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da  artifacts/timesfm3/model.safetensors
```

  Matches YAML and manifest: 1,322,898,824 bytes; 330,710,976 parameters; `weights_committed: false`.
- Split the actual licence note's seven blockquotes at ` … `, removed outer quotation/elision markers, normalized whitespace, and required each fragment to occur in local `artifacts/timesfm3/LICENSE`:

```text
LICENSE: 7 quotes / 9 fragments verbatim after whitespace normalization
```

### A2 — concrete source, execution, and arithmetic checks

- Read `forecast.py:35-59`: keeps `(T,)` versus `(V,T)` call shape, casts input float32, passes only `horizon` + `return_quantiles=True`, verifies quantile shape, selects `quantiles[..., median_index]` with YAML index **4**, and never consumes `.forecast` or exposes the ignored attention switch. The test deliberately supplies a wrong `.forecast`, so it checks behaviour rather than merely echoing a method name.
- Read `loader.py:19-25,41-57` and both entrypoints: HF home is configured before lazy model/hub import; both torch and MLX local loaders pass `local_files_only=True`; MLX receives no device keyword.
- Read `smoke.py:105-121,174-195`: determinism really makes two calls on the same generated array; truncation compares the long array to **its own last 15,360 points**, not to a regenerated shorter signal. Flat reporting (`:127-169`) keeps finite flags, measured deltas/spreads, and `status: observed`; saved CPU deltas `7.15e-7`, `0`, `7.63e-6` support its constant-series observation, not a general real-data accuracy claim.
- Ran the requested A2/common tests with bytecode and pytest cache writes disabled:

```text
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider' .venv/bin/python -m pytest -q tests/test_timesfm_access.py tests/test_common_config.py
...............                                                          [100%]
exit 0 (15 passing test indicators; no skips; wall time 4.66 s)
```

- Ran `.venv/bin/ruff check --no-cache` over all A2/A3 owned source modules, their three scripts, and their five test files:

```text
All checks passed!
```

- Independently recomputed two CPU cells without calling `forecast_flops`. With `P=330710976,d=1280,L=20`, `n=ceil(min(N,15360)/32)+4`, used `F=2PVn+4n²dLV+4V²dLn`, then divided by recorded median wall seconds:

```text
CPU cell N=240 V=1: n=12, 7.953037824 GFLOP / 202.888499945 ms = 39.199056754 GFLOP/s, exact match
CPU cell N=11520 V=3: n=364, 763.311005184 GFLOP / 943.294083700 ms = 809.197278319 GFLOP/s, exact match
```

  Inspected horizon padding/clipping implementation and all five R-A2 cost-table test cells. The analytic convention is explicitly not measured hardware FLOPs.
- Compared CPU/MPS/MLX saved JSONs to their surviving smoke logs. All report `overall: ok`; shapes/determinism/truncation/latency `ok`, flat `observed`. MPS parity max quantile errors: `6.67572021484375e-06`, `1.1444091796875e-05`, `1.049041748046875e-05`; MLX: `8.58306884765625e-06`, `9.5367431640625e-06`, `9.5367431640625e-06`. No GPU work was rerun. The evidence discloses battery operation rather than AC and concurrent activity; these smoke observations are not an isolated Phase-B power/scaling experiment.

### A3 — concrete SQL, files, loader, and oracle checks

- Compared `package.py:355-375` with read-only production `analyser/data_fetcher.py:205-219,309-319`: same closed timestamp bounds, pod/namespace constraints, `container=<selector>`, `name <> ''`, ordered timestamps, no cluster filter for this extraction. Count-query predicates agree. The inspected packaging calls use SELECTs only; F4 limits the stronger transport-safety claim.
- Ran all four data test files plus common configuration tests, with cache writes disabled and default extra quietness overridden for a literal summary:

```text
.venv/bin/python -m pytest tests/test_data_greptime.py tests/test_data_package.py tests/test_data_oracle.py tests/test_data_loader.py tests/test_common_config.py -o addopts='' -q
.............................................                            [100%]
45 passed in 4.54s
```

  Tests include real localhost HTTP envelope/error behaviour, hand-computed reset/boundary/gap laws, awkward-float byte-stable serialization, real-file loader checks, and a finite perturbed-observation rejection. F1–F3 describe the gaps those passing tests miss.
- Manifest contains **110** flat files. Reproducible random sample: `random.Random(20261109).sample(manifest['files'],8)`. For each sampled file independently counted decompressed rows, calculated full sha256, compared size/rows/hash with manifest, then used `load_flat_series` to assert both arrays float64, strictly increasing timestamps, and first epoch-second timestamp equal to CSV milliseconds /1000. All passed:

| Pair | Rows | Full sha256 |
|---|---:|---|
| rzpzm.mem | 51870 | `4d1df4b66d8e9e61dd0403f8e5618b599043ea2577655b8fe93eef95544b60e9` |
| b4xkt.rx_dropped | 51962 | `2a26b03682da91bb52f35389f461a7871840d93023e2c094cfc745780d410c43` |
| 2vwwd.tx_bytes | 51845 | `ff137bbb11dd29e4dd5f7cd93696a650de83a1ef0792025142a1186b504deb74` |
| hcfj7.rx_packets | 51903 | `e09753654d358e5127554877ba99b18342293247fb79105dd0ab641c989a51a4` |
| c5bdh.oom | 51875 | `54763f396e509dcb48201eb6a05a2b585581438be04cb924358e2d2836673fb9` |
| mjnlq.rx_dropped | 51798 | `77262387896357dcbf30c30d6f19a3c6f4b02599b45938854d8e72a75f721bcf` |
| vlsl8.tx_dropped | 51874 | `8f1065e1c6f21ca82893965cacd4fad390a29f3025a1034e5f0dc7880fc61692` |
| vlsl8.rx_bytes | 51874 | `a5060697702c2a1cb0603a56b308817a836bdf2c7e1a1dd2dcd7dc0f030af96b` |

- Copied the manifest and `b4xkt.cpu.csv.gz` beneath `/tmp/refm-rv-a2a3-*`; loaded the untampered copy successfully, appended bytes **only to the copy**, and reloaded. Literal rejection:

```text
TAMPER COPY: sha256 mismatch for /tmp/refm-rv-a2a3-vgtcbwy7/data/raw/flat-load/b4xkt.cpu.csv.gz
```

  Temporary copy was confined to a temporary-directory context. Original lab data was not modified.
- Loaded the saved 10 SHA-verified oracle docs and 40 continuous raw series; reran the deterministic saved-data `spot_check` and compared the complete returned report to the tracked manifest:

```text
LIVE saved-data spot_check reproduces manifest: True
COUNTS: {'cpu': {'exact': 28, 'lag-explained': 2, 'unexplained': 0}, 'mem': {'exact': 28, 'lag-explained': 2, 'unexplained': 0}, 'rx_bytes': {'exact': 29, 'lag-explained': 1, 'unexplained': 0}, 'tx_bytes': {'exact': 29, 'lag-explained': 1, 'unexplained': 0}}
```

  All 10 saved histories have 288 entries and 300-second-aligned ticks. Null attribution counts reproduce CPU `0`, memory `2880`, rx `437`, tx `466`. This verifies reproducibility of the implemented classification, not independence/causal proof (F3).
- Manifest window: `2026-10-30T08:45:47.911Z` through `2026-11-09 04:29:32.132`, **235.72895027777778 h**, `warmup_rows_skipped: 0`. Flag exactly `burst-2026-11-06`, `2026-11-06T01:00:00Z` → `02:45:00Z`, label `recorded burst (detector-side; no metric excursion)`; manifest burst rows span **370–396** per file. No conversion/resampling is performed by the raw loader.
- Surviving packaging log starts 13:34:32 and ends 13:37:03 local; it confirms oracle-first extraction, all metric count cross-checks, four zero-difference aggregate lines, and manifest-last success. It has **282 lines**, not the 148 claimed by `E-A3.md:74`. Route teardown/no-restart statements were read in executor evidence; no live route/process/cluster probe was performed by this review.

## Campaign invariants — explicit disposition

| Invariant relevant to these leaves | Review statement |
|---|---|
| Production detector and scoring laws unchanged; no threshold/strike/fusion/calibration/sojourn/prior retuning | **Preserved in the reviewed diffs.** All changed paths are owned lab files; production `data_fetcher.py` was read only. No production commit/push by this review. |
| Cluster is a read-only data source, not an experiment bed; ten ml-components pods on rtx-4000-test/kind-rtx-4000-cluster; supervisor route protected | **Correct configured target and inspected SELECT-only call paths.** Executor evidence records PID-only teardown and surviving 18086 route; not independently reprobed. **Mutation impossibility is not enforced by the generic client** (F4). This reviewer made no cluster/service calls or GPU runs. |
| Licence checked; weights local-only/non-commercial/non-production; no raw data/weights committed | **Preserved for inspected history and downloaded licence.** Seven quotes/nine fragments match; checkpoint hash matches manifest; only initial zero-byte scaffold path exceptions exist. Production-commercial-licence requirement is stated, not treated as approval to deploy. |
| Candidate receives raw irregular series; shared five-minute counter/gauge hand-off; no unit conversion/resampling | **Preserved in packaged-file/loader path inspected and sampled.** Counter right-closed and gauge left-closed/right-open value laws are implemented and hand-tested; full downstream scoring-chain parity belongs to A1/C. Single-source-identity assurance is **not established** (F1), and lag-compatible value matches are not unconditional parity proof (F3). |
| Median quantile, shape-only univariate/multivariate; documented context truncation; no invented input-uncertainty API | **Preserved.** Median index 4; no ignored attention switch; last-context truncation comparison is correct; no uncertainty input interface was added. |
| Machine-independent cost convention, not measured FLOPs; feasibility/weighted judgment not premature categorical quality gates | **Preserved.** Cost law/table arithmetic checked; no adoption/feasibility decision is inferred from these smokes. CUDA-primary Phase B remains separate under superseding D7. |
| Flat control unchanged at campaign end | **Not yet established by these leaves.** A2 honestly records constant-input smoke observations; this is not the campaign-end promoted-detector flat-control assertion. That assertion remains with downstream campaign evaluation. |
| Real P3 detector-side burst retained and honestly flagged; no invented raw excursion | **Flag/window preserved.** The checked flag reports the detector-side episode; no synthetic episode was substituted in A3. The observed >35 s gap must remain in the package and be documented accurately (F6). |
| YAML-first required configuration, deterministic behavioural tests, typed/logged implementation, owned-file discipline | **Owned-file scope, logging, and lint preserved; behavioural tests exercised.** A2 uses required YAML tunables. A3's hardcoded/fallback configuration exceptions and non-independent oracle fixtures are identified in F3/F5 rather than waived by green tests. |

## Disposition rationale

A2 supplies a real runnable local model, correct quantile/call-shape handling, the prescribed analytic cost law, a matching checkpoint identity and verbatim licence note, and saved CPU/MPS/MLX smoke evidence consistent with the logs/JSONs. Its remaining finding is evidence bookkeeping. A3's sampled bytes, row counts, epoch-second loader behaviour, tamper rejection, and deterministic saved-data report are reproducible, but the required identity validator cannot detect the condition it certifies; NaN observations can also be labelled exact. Consequently the passing tests and `hard_checks_passed: true` are not sufficient for acceptance. S should disposition the specific defects and the approved-but-ambiguous ingest-lag heuristic before treating A3 as a trustworthy parity oracle. No lab implementation, data, production file, commit, cluster, or service was modified by this review; only this review record was written (plus isolated permitted temporary copies/test scratch).
