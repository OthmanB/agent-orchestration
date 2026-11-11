# E-P6-repin2 — P6 re-pin LAB slice, second and FINAL run (workcard `solo-ops-P6`, section `## P6-repin`)

Executor: RefmP6RepinFinal (lab agent). Date: 2026-11-11.
Lab repo: `/Users/obenomar/Work/langGraph/appthrust/pipelineml-model-exploratory-work` (branch `main`, local commit only, never pushed).
Production repo: read-only for this slice.
`cd reference-model-study`, `PY=.venv/bin/python` (pytest 9.2.0).

## 0. Preconditions (all PASS)

- `P6=$(git -C <prod> rev-parse HEAD)` = **`c6ec9a22b7cf5da42be082f70e2a36a8f207c0d0`** (short `c6ec9a2`). ✓
- `git -C <prod> status --porcelain -- <the 9 used_files>` → **empty** (rc 0). ✓
- `git -C <prod> diff 5bcc7f9..HEAD -- analyser/solo_mode/driver.py` contains ONLY the 4 permitted hunks (no scoring-math hunk):
  1. import line: `from solo_mode.state import SoloStateStore, metric_tick_rows`
  2. `metric_ticks = metric_tick_rows(...)` block after `metrics_out = outcome["metrics"]`
  3. three `metric_ticks=metric_ticks,` kwargs (mandatory skip, no-eligible skip, `complete_scored_tick`)
  4. the `SoloRetention` block in `start_solo_runtime` incl. its 15-line comment
  ⇒ **no STOP condition met**. ✓
- `git -C <prod> diff 7e4014e..HEAD -- analyser/solo_mode/driver.py` → **comment lines only**: one 15-line comment block added above the existing `from solo_mode import retention as _retention` line inside `start_solo_runtime` (sweep-schedule doc). No code or docstring change. ✓
- Chain line numbers in production `driver.py` at `c6ec9a2`:
  - `candidate = bool(p_simes >= alpha_fuse)` → line **1650** (unchanged vs first repin `3f97c8e`)
  - first `float(markov_prev["p_posterior"]) if markov_prev else 0.0` → line **1516** (unchanged; the second occurrence at 1544 sits below the cited range, not cited, as before)
  ⇒ all `1486-1613` / `driver.py:1516` citations in `chain.py:15,354,496`, `prod_runner.py:13,152`, `test_p3_chain.py:4`, `reference-port.md:15` remain correct; **no comment refresh needed**. ✓
- used_files changed between first repin (`7e4014e`) and `c6ec9a2`: **only `analyser/solo_mode/driver.py`** (`163506f`, `197a122`, `e30ddb0`, `c6ec9a2` are all docs/comments in driver.py). `config.py` and `configmap.yaml` unchanged vs first repin. ✓
- Shared repo head still `942b8807f63e614fe3542ed2ba1268046291bfeb` (pin unchanged). ✓
- Baseline JSON: `git show 3f97c8e:reference-model-study/results/a1a-parity.json > /tmp/solo-p6-repin2/pre.json` (**1,575,309 bytes**; `provenance.head.production` = `7e4014e…`; `head.shared` = `942b880…`). Taken from the committed first-repin blob, never the working copy. ✓
- Working-tree hygiene: at start the lab tree carried three modified pin files pinning `e30ddb0` (the superseded in-flight attempt of peer `RefmP6Repin2`; that attempt's stage-1 had failed on the then-dirty production driver.py). They were stashed (`git stash push -m "superseded e30ddb0 pin …"`) so the pre-edit run was clean at `3f97c8e`. Stash preserved (`git stash list` at commit time: `stash@{1}: superseded e30ddb0 pin …`) — nothing dropped; peer was messaged before the stash.

## 1. Edits (3 files; 4th = regenerated JSON)

- `reference-model-study/config/reference.yaml:99` `expected_production_head` → `c6ec9a22b7cf5da42be082f70e2a36a8f207c0d0`
- `reference-model-study/tests/test_reference_config.py:78` same literal
- `markdown/reference-port.md:3` short sha `7e4014e` → `c6ec9a2`
- No line-range comment refresh needed (see §0).

## 2. Runs (all exit 0)

- `PY -m pytest -m "not parity" -q` **PRE** edits (tree clean at `3f97c8e`) → **1430 passed, 0 failed**, EXIT=0 (504 s wall).
- `PY -m pytest -m "not parity" -q` **POST** edits → **1430 passed, 0 failed**, EXIT=0 (510 s wall; `-rA` tally: 1430 PASSED, 0 FAILED/ERROR). **Pass count unchanged (1430 == 1430). ✓**
- `PY scripts/run_parity.py --config config/reference.yaml --stage 1` → EXIT=0 (4.20 s wall). ✓
- `PY scripts/run_parity.py --config config/reference.yaml --stage 2` → EXIT=0 (120.40 s wall). ✓

**ANOMALY (record, not a gate breach):** the workcard quoted "762 passed before the edit". Measured pre- and post-edit counts are **1430** both times. Verified: non-parity test-file set at `3f97c8e` and at final HEAD is identical (78 files; no test file added/removed by this slice, no untracked test files, no parity tests collected), so the slice itself did not change the count — the 762 figure recorded by the first repin (`E-P6-repin.md` §2) does not reproduce against the same tree. Possible cause: the first repin's pre-run was measured while its `git stash` of 6 files was in effect / under a different collection state; the `E-P6-repin.md` note also records that run was re-done after a "transient startup hang". Suggestion for S/Main: treat 1430 as the current true non-parity count and optionally re-baseline the 762 reference in `E-P6-repin.md`; no slice gate depends on the absolute number, only on pre==post equality (holds).

## 3. Comparison of regenerated `results/a1a-parity.json` vs `/tmp/solo-p6-repin2/pre.json`

Script `/tmp/solo-p6-repin2/compare.py` (drops top-level `provenance` and every `*wall_seconds` key; first run of the script had a bug — it did not drop `provenance` itself — fixed and re-run; final result below):

- **BODY_EQUAL: True** — P0–P4b numeric values bit-identical after dropping `provenance` + all `wall_seconds` keys. ✓ **No numeric parity value differs → no STOP.**
- `provenance.head.production` == **`c6ec9a22b7cf5da42be082f70e2a36a8f207c0d0`**. ✓
- `provenance.head.shared` unchanged (`942b880…`). ✓
- `blob_ids` vs first repin: ADDED none, REMOVED none; **CHANGED only `analyser/solo_mode/driver.py`** (`06912ec…` → `a8dfe52…`, the comment hunk); `config.py` and `configmap.yaml` unchanged vs first repin (as expected; all four fix commits are docs/comments in driver.py). ✓
- VERDICT: **PASS**

## 4. Commit

- `git diff --check` → clean (rc 0).
- Explicit `git add` of exactly the 4 files (`config/reference.yaml`, `tests/test_reference_config.py`, `../markdown/reference-port.md`, `results/a1a-parity.json`); `git status --porcelain` after commit = clean.
- Commit: **`ed249a49cf88d3410423a9b7f1606b18bbcf6a9b`** (short `ed249a4`)
  - message: `chore(refstudy): re-pin parity to production c6ec9a2 after SOLO-OPS P6 review fixes`
  - `4 files changed, 65 insertions(+), 65 deletions(-)`
  - no trailers.

## 5. Campaign-log line for S to append to `CAMPAIGN-CONTEXT.md` (decisions block; orchestration commits wait for the operator)

- **D-P6-repin2 (2026-11-11, final):** production pin moved 7e4014e -> c6ec9a2 after the SOLO-OPS P6 review fixes (163506f F1, 197a122 F2/F4, e30ddb0 F3/F5/F6, c6ec9a2 RV-b R1-R4 — all docs/comments in driver.py); first repin 3f97c8e (7e4014e) superseded, lab commit ed249a4; parity stage 1+2 green, a1a-parity.json differs only in provenance (head.production + driver.py blob_id; body bit-identical). Any further production commit (incl. the deploy digest-pin) needs another re-pin.
