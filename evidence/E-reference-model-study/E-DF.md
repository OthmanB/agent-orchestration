# E-DF — hardware-normalized B2 read-off (operator D-F)

Executor record, campaign SOLO-REFM / leaf DF. One section per slice.

## DF-1.1 (config slice; commit `c5fba0f`)

Scope: 3 files, config only; suite stays green. Lab repo `pipelineml-model-exploratory-work`, study dir `reference-model-study/`.

Files:
- `src/refstudy/compute/refresh_config.py`:
  - new frozen dataclass `NormalizeSpec{timesfm_config: Path, b1_scaling: Path}` + `b1_scaling_path(device)` helper (the `b1_scaling` template carries the `{device}` placeholder, resolved against the study base exactly like `outputs`);
  - `RefreshConfig.normalize: NormalizeSpec` (parsed via `require`, both keys required; `b1_scaling` must contain `{device}` — `ValueError` naming `normalize.b1_scaling` otherwise);
  - `OutputsSpec.fig_normalized: Path` — the loader's generic `outputs.{field}` loop makes the key required, so no further loader change; verified `RefreshConfig(`/`OutputsSpec(` are constructed only in this loader.
- `config/refresh_study.yaml`: new `normalize:` block (`timesfm_config: config/timesfm3.yaml`, `b1_scaling: "results/b1-scaling-{device}.json"`) + `outputs.fig_normalized: figures/b2-normalized.png`.
- `tests/test_compute_refresh_config.py`: `test_loads_real_yaml` asserts `cfg.normalize.timesfm_config`/`b1_scaling_path("cuda")`/`outputs.fig_normalized`; `_MISSING` gains `normalize.timesfm_config`, `normalize.b1_scaling`, `outputs.fig_normalized` (missing key named, parametrisation); `test_validation_errors` gains `normalize.b1_scaling` without `{device}` → match `placeholder`.

Verification (all in the lab repo, venv `.venv`, py3.12):
- `pytest tests/test_compute_refresh_config.py -q`: 64 passed, 0 failed, 0 skipped (60 before; +3 parametrised missing-key cases + 1 validation case).
- `pytest tests/test_compute_*.py -q`: 265 passed (collect-only count), 0 failed, 0 skipped (gate per card; progress line all dots, exit 0).
- `ruff check` on the two owned Python paths: All checks passed (YAML is not a ruff target; no ruff config change).
- `git diff --check`: clean.
- Commit `c5fba0f` `feat(refstudy): add D-F normalize config block and fig_normalized output (DF 1.1)`, exactly the 3 owned files (explicit `git add`; pre-existing sibling modifications on harness/plotting paths left unstaged).

No CUDA probe numbers are involved in this slice (config only); planner-probe reproduction belongs to DF-1.2/2.1. No new measurement (D-F re-derivation only).

Open issues: none for DF-1.1. Note for DF-1.2: `load_normalizer`/`build_table` will read `cfg.normalize.b1_scaling_path(device)` for devices whose B1 file exists (currently only `results/b1-scaling-cuda.json`; Mac files arrive in the exclusive Mac window, D-S4).

## DF-1.2 (table library + caller migration; commit `e9d612f`)

Scope: 5 files, the D-F hardware-normalized table library plus migration of ALL `build_table` callers so the suite stays green. Re-derivation only; inputs are the committed `results/b2-refresh-cuda.json` + the cuda B1 scaling cells (`n5760-v4`, `n11520-v4`). No new measurement.

Files:
- `src/refstudy/compute/sustain.py`:
  - new frozen dataclass `Normalizer{pod_gflop: Callable[[int], float], n_variates: int, horizon: int, b1: Mapping[str, Mapping[str, Any]]}`; `pod_gflop(N)` is the per-pod refresh FLOP `F(N)` (GFLOP, analytic matmul-only law, one forecast per pod per pass).
  - `load_normalizer(cfg, settings, results_dir)`: `pod_gflop(N) = forecast_flops(N, len(cfg.data.metrics), settings.runtime.horizon, settings.cost)/1e9`; B1 docs loaded ONLY for devices whose `cfg.normalize.b1_scaling_path(dev)` filename exists under `results_dir` (mirrors `load_docs`; the on-disk `b1_scaling` resolves against the study base, so only the device-substituted filename is joined to `results_dir`). Currently only `cuda` has a B1 file.
  - `_b1_cell(b1_doc, n, v)` → the `n{n}-v{v}` cell (or `None`).
  - `_norm_fields(device, ctx, pods_eff, mean_w, budget_s, norm)` → the per-row normalized fields: `pod_gflop=F(ctx)`, `g_b1_gflops_s`=G (`gflops_s_analytic` of the `n{ctx}-v{V}` cell), `pods_per_tflops_s = pods_eff/(G/1000)` (measured), `closed_form_pods = budget_s*G/F`, `pods_per_tflops_s_closed_form = budget_s*1000/F` (the G-independent transferable constant, set in EVERY case), `consistency_ratio = pods_eff/closed_form_pods`, `pods_per_watt = pods_eff/mean_w` (G-independent, set whenever `pods_eff` and `mean_w` are present — so it is carried even without a B1 cell), `norm_status ∈ {"ok","no_b1_cell","no_power"}`. Missing B1 doc/cell → `g_b1_gflops_s=None` + `"no_b1_cell"`; present B1 cell but no run power → `"no_power"`; else `"ok"`. Cross-check: raises `ValueError` naming `{device} cell n{ctx}-v{V}` if `pod_gflop(ctx)` disagrees with the cell `gflop_analytic` (rel 1e-9).
  - rows gain `pods_basis ∈ {"adjusted","knee"}` (`adjusted` iff `pods_adjusted` is set) and every field above; `accelerator_bound` entries gain `pod_gflop`, `achieved_gflops_s_probe = pods_per_s*F` (at `b_star`), `g_b1_gflops_s`, `batch_gain_vs_b1`; `batched_overlap` rows at `probe.context_pts` gain `consistency_ratio_probe = pods_eff/(budget_s*G_probe/F)` (null elsewhere).
  - `build_table(docs, cfg, norm)` now REQUIRES `norm` (clean cutover). `headline()` records gain `pod_gflop, g_b1_gflops_s, pods_per_tflops_s, closed_form_pods, consistency_ratio, pods_per_watt, norm_status`.
- `config/refresh_study.yaml`: `headline.template` now appends `; {pods_per_tflops_s:.1f} pods per TFLOP/s; {pods_per_watt:.2f} pods/W [{power_scope}]` (both new placeholders render `nan` when `None`, mirroring `joules_per_pod`).
- `scripts/plot_refresh.py`: `main` loads `settings = load_settings(cfg.base / cfg.normalize.timesfm_config)`, `norm = load_normalizer(cfg, settings, results_dir)`, and passes `norm` to `build_table(docs, cfg, norm)` (the one caller in this slice).
- `tests/test_compute_sustain.py`: all 12 `build_table` call sites migrated to a module-level synthetic `Normalizer` (`NORM`: `F(N)=N/10`, `G_cuda=2000`, `mps` has no B1 doc); added hand-arithmetic for every new field, the `no_b1_cell`/`no_power` paths, a second Mac-like `system_whole` device with a different G and F-law flowing through with no code change, the closed-form constant being G-independent, F-mismatch `ValueError` naming device/cell, the accelerator normalized fields, `load_normalizer` reading only existing B1 docs + the `pod_gflop`==`gflop_analytic` cross-check, and `test_cuda_planner_probe_reproduction` which re-derives the card's CUDA planner probe from the committed result files.
- `tests/test_compute_refresh_plots.py`: all 6 `mod.build_table` call sites migrated to a module-level synthetic `Normalizer` (`NORM`).

Verification (all in the lab repo, venv `.venv`, py3.12):
- `pytest tests/test_compute_*.py -q`: 272 passed, 0 failed, 0 skipped (gate per card; up from 265).
- `pytest tests/test_compute_sustain.py tests/test_compute_refresh_plots.py -q`: all green (sustain now 17 tests including 6 new + the reproduction; plots unchanged count).
- `ruff check` on `src/refstudy/compute/sustain.py scripts/plot_refresh.py tests/test_compute_sustain.py tests/test_compute_refresh_plots.py` (and the full `src tests scripts`): All checks passed.
- `git diff --check`: clean.
- Planner-probe reproduction (no new measurement; inputs = committed `results/b2-refresh-cuda.json` + cuda B1 cells): `F(5760)=500.975439872`, `F(11520)=1017.897101312` (= B1 `gflop_analytic`, rel 1e-9). At the 300 s tick budget — sequential 734 → 298.4 pods/TFLOP/s, ratio 0.498; 416 (adjusted) → 160.1, 0.543. overlap 1234 → 501.7, 0.838; 706 → 271.8, 0.922. batched_overlap 2965 → 1205.6, 2.013; 1429 (adjusted) → 550.0, 1.866. Closed form 598.8 (5760) / 294.7 (11520) pods per TFLOP/s = 1472.8 / 765.7 closed-form pods. Probe b*=32, 5.0597 pods/s → 5150.2 GFLOP/s = 1.98× the B1 batch-1 G (2597.947); batched `consistency_ratio_probe` = 0.941. All reproduced by `test_cuda_planner_probe_reproduction` (asserted `rel≈1e-3` on the rounded card values; the batch gain asserted against the exact ratio of the two computed fields, not the rounded "1.98×").
- Additive-only regression (regenerated the table to a throwaway dir via `plot_refresh.py --table-only` and diffed against `git show HEAD:...`): every pre-existing row/accelerator/stability/headline field is byte-identical to HEAD; only additive keys appear (rows: the 10 new normalized fields incl. `consistency_ratio_probe`; accelerator: 4; headline: 7; the headline `text` differs only by the new template clause). No Mac number appears (only `cuda` has a B1 doc; `mps`/`mlx`/`cpu` would be `no_b1_cell`).

Open issues: none for DF-1.2. The 6 full-suite failures observed while running `pytest tests` (`KeyError: 'mechanism'` in `src/refstudy/harness/aggregate.py` / `src/refstudy/refcompare/sidebyside.py`) are OUTSIDE the card gate (`test_compute_*.py`), outside my owned paths, and in the concurrent DB slice's territory (`harness/*`, `refcompare/*`); they do not touch `sustain.build_table`. The suite stays green on the card gate and on every file I own.

## DF-1.3 (figures slice; commit `60628d1`)

Scope: 2 files, the D-F normalized figure plus the per-panel read-off text boxes; `main` now writes `cfg.outputs.fig_normalized`. No regeneration of committed results/figures (that is DF-2.1); all figure generation here went to `throwaway/df13/` (git-ignored). Re-derivation only; inputs = the committed `results/b2-refresh-cuda.json` + cuda B1 cells.

Files:
- `scripts/plot_refresh.py`:
  - `_textbox(ax, text)`: bottom-left white box (font 6.5, alpha 0.92) shared by all three read-off boxes; bottom-left so it never collides with the legend (upper left) or the budget labels (right edge).
  - `_primary_budget(cfg)`, `_row_at_primary(table, dev, variant, ctx, cfg)`: primary (`tick`) budget row lookup.
  - NEW `fig_normalized(docs, table, cfg)`: 2 rows x one column per device (column order = `load_docs` order; a device column with no table rows gets `no data`). Row 1 "pods per TFLOP/s at tick 300 s": marker per variant = the measured `pods_per_tflops_s`, one grey short horizontal tick per context = the G-independent closed-form constant `budget*1000/F`, ratio annotated as `x{consistency_ratio:.2f}` beside the tick. Row 2 "pods per W (mean power incl. idle)": one marker per variant per context, hollow (`mfc="none"`) when `power_resolved is not True or extrapolated`. Every title and y label carries the device, the scope (`(gpu_board)` / `[gpu_board]`) and the budget. Device without a B1 document: both panels labelled 'no B1 cell' while the closed-form ticks stay drawn (they need only F).
  - `_norm_box_text(...)`: the D-F box of one refresh panel — `F = {pod_gflop:.1f} GFLOP/pod`, `G = {g:.1f} GFLOP/s` or `no B1 cell`, then each variant's `{variant}: {pps:.1f} pods/TFLOP/s` at the primary budget; `None` when the panel has no table row.
  - `_power_box_text(...)`: the D-F box of one power column — `[{power_scope}]`, `at tick 300 s, {days} ({ctx} pts)`, then each variant's `{pwr:.2f} pods/W` at the primary context/budget.
  - `fig_refresh`: every non-empty panel now carries the `_norm_box_text` box.
  - `fig_power`: signature gains the `table` argument (2nd position); the W panel carries the `_power_box_text` box when power runs exist.
  - `main`: figures tuple gains `(cfg.outputs.fig_normalized, fig_normalized(docs, table, cfg))`; `--table-only` is unchanged.
- `tests/test_compute_refresh_plots.py`:
  - the 3 `fig_power` call sites migrated to `fig_power(docs, table, cfg, xlims)`; `test_three_figures_table_and_analytic_knees` now also asserts `b2-normalized.png` is written and PNG-magic-valid.
  - NEW helpers `_textbox_texts(fig)` (texts of white-boxed artists), `_is_closed_form_tick(ln)`, `_norm_axis(fig, dev, kind)`.
  - NEW `test_normalized_figure_builds_with_mac_like_device_lacking_b1`: cuda+mps synthetic docs (mps has no B1 doc in `NORM`) — 2x2 axes, scope in every title/ylabel, 'no B1 cell' in both mps panels, 2 closed-form ticks still drawn for mps, and a 'no B1 cell' line in a refresh-figure text box. This is the Mac-flow-through check required by the card (the mps doc is a synthetic second device; no Mac number is invented).
  - NEW `test_normalized_row1_markers_closed_form_and_ratio`: tick y-values equal `300*1000/F` at both contexts (synthetic `F=N/10`), and the ratio annotations equal `x{pps/cf:.2f}` for all 6 measured markers.
  - NEW `test_normalized_row2_hollow_when_unresolved_or_extrapolated`: all 6 pods/W markers hollow when `power_resolved` is False; after resolving power, the interpolated knee becomes solid while extrapolated knees stay hollow.
  - NEW `test_refresh_and_power_figures_carry_readoff_boxes`: both refresh panels carry a box with the exact F/G and per-variant pods/TFLOP/s table values; the power figure carries one box with `[gpu_board]` and the exact `sequential: {pods_per_watt:.2f} pods/W` table value.

Verification (all in the lab repo, venv `.venv`, py3.12):
- `pytest tests/test_compute_*.py -q`: 276 passed, 0 failed, 0 skipped (up from 272; +4 new plot tests).
- `ruff check scripts/plot_refresh.py tests/test_compute_refresh_plots.py` (and the full `src tests scripts` tree): All checks passed.
- `git diff --check`: clean.
- Figures generated to `throwaway/df13/` (git-ignored) from the committed result files and inspected artist-by-artist:
  - `b2-normalized.png` (single cuda column today): row-1 title/ylabel "cuda (gpu_board): pods per TFLOP/s at tick 300 s [gpu_board]"; closed-form ticks at 598.8 (1 d) / 294.7 (2 d) pods per TFLOP/s; measured markers 298.4/501.7/1205.6 (1 d) and 160.1/271.8/550.0 (2 d); ratio annotations x0.50/x0.84/x2.01 and x0.54/x0.92/x1.87; row-2 pods/W markers 20.03/26.70/43.59 and 10.59/14.35/20.82, all hollow (power_resolved True but every tick-300 knee is extrapolated — hollow state asserted by the program, not by eye; the vision model was unavailable in this environment, so all figure content was verified by dumping titles/labels/box texts/line data and checking pairwise text-bbox overlaps: 0 overlaps in the normalized and power figures).
  - `b2-refresh-vs-pods.png`: both context panels carry the box, e.g. "F = 1017.9 GFLOP/pod / G = 2597.9 GFLOP/s / sequential: 160.1 pods/TFLOP/s / overlap: 271.8 / batched_overlap: 550.0". One pre-existing overlap remains in that figure (knee label '1783' vs the 'strict120' budget label at the 1 d panel) — it predates this slice (present in the committed figure geometry) and is out of scope here.
  - `b2-power-vs-pods.png`: box "[gpu_board] / at tick 300 s, 2 d (11520 pts) / sequential: 10.59 pods/W / overlap: 14.35 / batched_overlap: 20.82".
  - Throwaway JSON: this slice changed ONLY the plotting (`plot_refresh.py`), not `build_table`, so the throwaway table/records are byte-identical to what DF-1.2's `build_table` produces; they differ from the committed `results/b2-*.json` ONLY by the additive normalized fields introduced in DF-1.2 (rows/accelerator/headline) and the DF-1.2 headline-template clause — i.e. the committed results are still pre-DF-1.2 and are exactly what DF-2.1 regenerates. No DF-1.3-specific key is added to the JSON.

Open issues: none for DF-1.3. Note for DF-2.1: `main` now writes a 4th figure; when the Mac B1/B2 windows land, `mps`/`mlx`/`cpu` columns appear in `b2-normalized.png` automatically (closed-form ticks + pods/W from their own files, 'no B1 cell' only until their B1 files exist).

## Stage 2 (regenerate + note; commits `b2a8165`, `3f3ac04`)

### DF-2.1 regenerate (data commit `b2a8165`)

Ran `.venv/bin/python scripts/plot_refresh.py --config config/refresh_study.yaml` against the committed `results/b2-refresh-cuda.json` (no new measurement; 1.8 s CPU). Wrote `results/b2-sustainable.json` (30 rows), `results/b2-headline.json`, `figures/b2-{refresh-vs-pods,power-vs-pods,queue-backpressure,normalized}.png`. `b2-queue-backpressure.png` regenerated byte-identical (hence absent from the commit); `b2-normalized.png` is new; `b2-refresh-vs-pods.png` and `b2-power-vs-pods.png` regenerated with the DF-1.3 read-off boxes.

Additive-only assertion vs `git show HEAD:`: pre-study snapshot of both JSONs equals HEAD exactly; after regeneration, key-set diff over all rows/accelerator_bound/stability/budgets/headline records: **0 removed keys, 0 changed pre-existing values** — the only changed pre-existing values are the two headline `text` strings, which gain the DF-1.2 template clause (`; {pps:.1f} pods per TFLOP/s; {ppw:.2f} pods/W [gpu_board]`). Added keys: rows x30 each of `pod_gflop, g_b1_gflops_s, pods_per_tflops_s, closed_form_pods, pods_per_tflops_s_closed_form, consistency_ratio, pods_per_watt, norm_status, pods_basis, consistency_ratio_probe`; accelerator_bound x5: `pod_gflop, achieved_gflops_s_probe, g_b1_gflops_s, batch_gain_vs_b1`; headline x2: the 7 normalized fields. No Mac number appears (only cuda present).

Planner probe reproduced exactly at the 300 s tick (all within card tolerance; 416/1429 are the adjusted knees as the card says): sequential 734 → 298.4 pods/TFLOP/s, ratio 0.498, 20.03 pods/W; 416 → 160.1, 0.543, 10.59; overlap 1234 → 501.7, 0.838, 26.70; 706 → 271.8, 0.922, 14.35; batched_overlap 2965 → 1205.6, 2.013, 43.59; 1429 → 550.0, 1.866, 20.82. Closed form 598.8 / 294.7 pods per TFLOP/s = 1472.8 / 765.7 closed-form pods. Probe b*=32, 5.0597 pods/s ⇒ 5150.2 GFLOP/s = 1.98× the B1 batch-1 G (2597.947); batched `consistency_ratio_probe` = 0.941. **No differences.**

Figure check (vision model unavailable in this environment; verified artist-by-artist by regenerating in-memory and dumping artists): `b2-normalized.png` = 2 axes, 1 cuda column. Row 1 title `cuda (gpu_board): pods per TFLOP/s at tick 300 s`, ylabel `[gpu_board]`: measured markers 160.1/298.4 (sequential), 271.8/501.7 (overlap), 550.0/1205.6 (batched); closed-form ticks at 294.7 (2 d) / 598.8 (1 d); ratio annotations x0.50/x0.84/x2.01 (1 d) and x0.54/x0.92/x1.87 (2 d). Row 2 `pods per W (mean power incl. idle) [gpu_board]`: markers 10.59/14.35/20.82 (2 d) and 20.03/26.70/43.59 (1 d), all hollow (`mfc=none`, every tick-300 knee is `extrapolated`). 0 text/label overlaps. `b2-refresh-vs-pods.png`: both context panels carry the D-F box, e.g. `F = 1017.9 GFLOP/pod | G = 2597.9 GFLOP/s | sequential: 160.1 | overlap: 271.8 | batched_overlap: 550.0 pods/TFLOP/s`; the one pre-existing label overlap (knee '1783' vs 'strict120' budget label at 1 d) predates this slice. `b2-power-vs-pods.png` carries the `[gpu_board] ... pods/W` box.

Gates: `pytest tests/test_compute_*.py -q` 276 passed, 0 skipped; `ruff check src tests scripts` clean; `git diff --check` clean.

### Normalized CUDA table (for the campaign log)

Pods at 300/180/120 s; pods/TFLOP/s and consistency ratio at all three budgets; pods/W at 300 s. `norm_status=ok` on all rows; tick-300 rows `extrapolated=true`.

| context | variant | pods 300/180/120 s | pods/TFLOP/s (300 s) | ratio vs closed form (300/180/120 s) | pods/W [gpu_board] (300 s) |
|---|---|---|---|---|---|
| 5760 (1 d) | sequential | 734 / 441 / 293 | 298.4 | 0.498 / 0.499 / 0.497 | 20.03 |
| 5760 | overlap | 1234 / 741 / 497 | 501.7 | 0.838 / 0.839 / 0.844 | 26.70 |
| 5760 | batched_overlap | 2965 / 1783 / 1188 | 1205.6 | 2.013 / 2.018 / 2.017 | 43.59 |
| 11520 (2 d) | sequential | 416 / 249 / 166 | 160.1 | 0.543 / 0.542 / 0.542 | 10.59 |
| 11520 | overlap | 706 / 423 / 287 | 271.8 | 0.922 / 0.921 / 0.937 | 14.35 |
| 11520 | batched_overlap | 1429 / 856 / 571 | 550.0 | 1.866 / 1.863 / 1.864 | 20.82 |

Closed form `budget*1000/F` pods/TFLOP/s: 598.8 / 294.7 at 300 s (1 d / 2 d), 359.3 / 176.8 at 180 s, 239.5 / 117.9 at 120 s (= 1472.8 / 765.7 closed-form pods at 300 s). J/pod at 300 s: sequential 7.8/15.0, overlap 6.9/12.9, batched 4.9/10.3 (1 d / 2 d). B1 energy n11520-v4: 0.01207 J/GFLOP board excess over the 19.0 W idle floor.

### DF-2.2 note (docs commit `3f3ac04`)

Created `markdown/phase-b-compute-study.md` (3-line header + section `## Hardware-normalized read-off (operator D-F)`, section exactly 80 lines; whole file 84). Contents, all numbers copied from the regenerated JSON / B1 cells: (a) host-accident rationale (rtx-4000-test, gpu_board, never deployed); (b) the unit — F(5760)=500.975 / F(11520)=1017.897 GFLOP, G=2459.446/2597.947, closed form `budget*G/F`, transferable constant `budget*1000/F`, J/pod and pods/W with scope; (c) the CUDA table above + ratio reading (sequential < 1: modelled fetch 0.27 s + 10 ms chain on the serial path; batched > 1: probe 5.0597 pods/s = 5150.2 GFLOP/s = 1.98× batch-1 G, `consistency_ratio_probe` 0.941 — pipeline effects, not hardware); (d) transfer recipe (measure B1 (N, V=4) ⇒ G; predict `budget*G/F`; scale by the variant-class ratio; energy `J/pod = F × joules_per_gflop` of ITS B1 energy cell, CUDA n11520-v4 = 0.01207 J/GFLOP); (e) non-transferables (fetch/chain modelled, host load, power scope gpu_board vs system_whole, `mean_w` includes idle floor, extrapolated knees); (f) Mac cpu/mps/mlx flow-through (no code change, `no_b1_cell` until B1 files land, no Mac number invented); (g) limits.

Gates: no code touched in this slice; `git diff --check` clean; commit is the single owned file.

Open issues: none. DF is complete (5 commits: c5fba0f, e9d612f, 60628d1, b2a8165, 3f3ac04); when the Mac B1/B2 windows land, rerunning the plot script adds their normalized columns automatically.

## Doc fixes (RV-CB-DF-P6: DF-F1, DF-F2, DF-F3; 2026-11-10)

Documentation/provenance corrections to the D-F read-off, applied after the RV review; no new
measurement, no change to any committed result. Lab commit `fix(refstudy): bound D-F transfer
claims and label extrapolated figure values (RV DF-F1 DF-F2 DF-F3)`; the P6 card line and this
evidence file are uncommitted orchestration files.

### DF-F1 — the batched ratio is batch gain × efficiency, can be below 1 (not "> 1 by construction")

- `markdown/phase-b-compute-study.md` (ratio paragraph): with a batch-1 G in the denominator the
  consistency ratio is the batch gain (achieved GFLOP/s ÷ batch-1 G) times the end-to-end
  efficiency, so it can sit above OR below 1. The **two-day** batched row (1.87) is explained by
  the measured N = 11520 probe (b* = 32): 5.0597 pods/s = 5150.2 GFLOP/s = 1.9824× the batch-1 G;
  against that probe its own consistency ratio is 0.9414, and 1.9824 × 0.9414 = 1.8663 reproduces
  the two-day ratio. There is **no one-day (N = 5760) batch probe** in the committed results, so
  the one-day batched ratio (2.013) has no same-context probe to split into gain × efficiency —
  its mechanism attribution is inference; batching efficiency depends on hardware/backend as well
  as pipeline scheduling.
- `markdown/phase-b-compute-study.md` (Limits): "batched ratios are > 1 by construction" → "a
  batched ratio is the batch gain times the end-to-end efficiency and can be above or below 1";
  the ratios are conditional scenario estimates for this host, not a machine-invariant transfer factor.
- `evidence/omp-workcards/refm-DF.md` (planner risk line): "makes batched ratios > 1 by
  construction" → "makes a batched ratio the batch gain × end-to-end efficiency, which can sit
  above OR below 1 (a batch-1 denominator permits > 1 but does not guarantee it)".

### DF-F2 — the consistency ratio is NOT a machine-invariant transfer factor

- `markdown/phase-b-compute-study.md` (transfer recipe, retitled "per machine"): the fixed
  fetch/chain time `c` does not scale with the model latency (a serial `pods ≈ budget_s/(F/G + c)`
  gives ratio `1/(1 + c·G/F)`, which changes with G at unchanged c), and the batch gain is
  machine-dependent. The recipe is restated as: (1) predict F/G per pod from the FLOP law and the
  target's own measured B1; (2) the model-bound `budget_s·G/F` is the transferable prediction;
  (3) apply the measured variant ratios **only as a same-host calibration** (conditional scenario
  estimates, not validated transferable factors); (4) re-measure the pipeline on the target
  hardware before any wall-clock pod claim; (5) energy as before.
- The "What does not transfer" section already listed fetch/chain constants, host load, power
  scope, and extrapolated knees; it now reads consistently with the recipe above.

### DF-F3 — figure labels fitted/extrapolated read-offs and stops clipping the suptitle

- `scripts/plot_refresh.py` `fig_normalized`:
  - row-1 (pods per TFLOP/s) markers are now per-point read-off markers — a connecting line plus
    one marker per read-off, **hollow when the knee is `extrapolated`** (previously a single solid
    marker line; the committed tick-300 s read-offs are all extrapolated, so all six are now hollow).
    (Per-point `mfc` on a single `plot` call does not render under the Agg backend, hence one
    marker artist per read-off, matching the row-2 construction.)
  - the row-1 marker legend now carries the read-off status in its title:
    "read-offs; hollow = extrapolated / unresolved".
  - the suptitle no longer says "markers measured"; it now says "read-offs fitted / extrapolated,
    ticks closed form; hollow = extrapolated / unresolved", and is wrapped onto two lines so every
    line stays within the figure width (verified on the narrowest 1-column figure: span 2.6–477.4
    px inside 0–480 px) so the qualification survives saving instead of being clipped.
- `tests/test_compute_refresh_plots.py`: NEW `test_normalized_readoff_labels_and_suptitle_not_clipped`
  (+ helper `_doc_all_extrapolated` and `_suptitle_bbox_in_figure`): builds a synthetic all-extrapolated
  document and asserts the row-1 legend labels + status title, the suptitle read-off/hollow text,
  that all six top-panel read-off markers are hollow, and that the suptitle's figure-x span stays
  within [0, 1] (non-clipping).
- `markdown/phase-b-compute-study.md` (table heading): "CUDA table (measured, …)" → "CUDA table
  (read-offs, …)" with a note that the tick-300 s (primary) row of every variant is a fitted /
  extrapolated read-off (`extrapolated_linear`, `extrapolated: true`) while the 180 s / 120 s
  budgets are interpolated; the 34-line note heading that called the values "measured" is now
  consistent with the extrapolation.

### Regeneration + gates

- Regenerated ONLY `figures/b2-normalized.png` from the committed `results/b2-refresh-cuda.json`
  (+ the B1 cuda cells and the D-F normalizer). Verified `build_table` output is **byte-identical**
  to the committed `results/b2-sustainable.json`; `results/b2-sustainable.json`, `results/b2-headline.json`
  and the three other `figures/b2-*.png` are unchanged (only `b2-normalized.png` is rewritten — its
  text is the only thing that changed). No new measurement.
- `pytest tests/test_compute_*.py tests/test_reference_*.py -q` green (0 skipped; parity-marker
  tests excluded via the card's `-m "not parity"` selection — see gate below), ruff clean on
  `scripts/plot_refresh.py` and `tests/test_compute_refresh_plots.py`, `git diff --check` clean.

