# agent-threat-detector-v2 (Tier C untangling & consolidation) — vision / design-intent note

**Date:** 2026-11-02
**Author:** Observer (read-only author; this is design *intent*, not an implementation).
**For:** the agent-orchestration pipeline (R → P → E → RV). This file is the
**VISION / INPUT**, not a directive: R resolves the open questions (§8), P writes
the packages from the sketch (§7), E implements, RV reviews.
**Also read:** `agent-orchestration/AGENTS.md`, `markdown/00-orchestration-model.md`,
`markdown/04-experimental-environment.md`, `raw-text-preprocessor-vision.md`
(the pre-processor lane this vision moves, unchanged in behavior).

> This campaign **moves and untangles an existing system**. It builds no new
> detection capability. The Tier C system (the retained path) is implemented
> today across three repositories and is **functionally entangled with the
> abandoned Tier 2 path**: the demo controller executes Tier 2 code, ships in a
> Tier 2 image, and cross-validates against a Tier 2 route config. The goal is a
> single self-contained repository `agent-threat-detector-v2` with **no mention
> of and no dependency on Tier 2**, two documented operating modes, and the old
> repositories frozen or archived.

---

## 1. Goal (plain English)

Tier C converts natural-language operator intents into structured JSON using an
isolated LLM, then feeds that JSON into the analysis system (analyser →
Prometheus → detector). That is the retained path. Tier 2 (the first attempt:
compare operator input against actual cluster actions, no semantic
understanding) is abandoned — it cannot act pre-emptively and its mechanics are
too complex.

The problem: the Tier C code that was built on the way to that conclusion is
*physically inside* the Tier 2 repository and *executes* Tier 2 modules. The
user wants to be able to abandon Tier 2 completely without touching Tier C, and
wants the Tier C system — demo mode and pre-processor ("production") mode alike
— to be self-contained in one own repository with its own images and its own
documentation.

**Done =** one new repository `agent-threat-detector-v2` that:

1. contains all Tier C source (T-layer classifier, pre-processor, demo
   controller, dashboard), all Tier C configuration, all image builds (three
   images), and all Tier C documentation — with zero Tier 2 references;
2. deploys two modes against the existing analyser/detector (unchanged, their
   repos stay put — only their Helm *values* are referenced):
   - **Mode 1 — demo:** controller paces scenario text through the LLM, trains
     a reference, runs an attack, dashboard + CLI drive it end to end;
   - **Mode 2 — pre-processor:** raw operator text POSTed to the pod's API,
     normalized by the LLM, forwarded to the analyser — for staging/production;
3. is proven live on `kind-michel-cluster` with a **fresh generation** (full
   demo lifecycle + pre-processor smoke), so the trained old generation is
   never mutated;
4. leaves the old repositories frozen/archived (nothing Tier C remains in
   Tier 2-named places).

## 2. What already exists (do not re-invent)

Verified against source on 2026-11-02 (this is the dependency map R must
re-confirm, not re-derive):

**The pieces (all working, all live in `threat-detection-tierc`):**

| Piece | Lives in today | State |
|---|---|---|
| T-layer classifier (`tier_c_intent`: contract, model_client, processor, sink, transport, runner_config) + `config/tier-c-intent.yaml` | `agent-threat-tier-c` | Clean; no Tier 2 code |
| Pre-processor app (`tier_c_preprocessor`) + `config/tier-c-preprocessor.yaml` + Dockerfile + image workflow | `agent-threat-tier-c` | Clean; one Tier 2 string: `cluster: tier2-local-demo` |
| Demo controller (`tier_c_demo`: cli, config, controller, pipeline, results + tests) | `agent-threat-detection/scripts/demo/` | **4 functional Tier 2 imports** |
| Demo authorities + generator (`demo.yaml`, `dashboard.yaml`, `preprocessor.yaml`, `generate_demo.py`, `dashboard_config.py`, `preprocessor_config.py`) | `agent-threat-detection/deploy/demo/tier2/tier-c-demo/` | **Imports Tier 2 + tester + tier-c loaders** |
| Dashboard app (`pipelineml_tester.tier_c`: api, auth, bridge, config, contracts, export, staging, ui, views + tests) + `config/tier-c.yaml` | `pipelineml-tester` | Tier C code hosted in the tester repo |
| Demo delivery plumbing: in-pod mTLS gateway + Vector external listener + VRL tier-c branch + ledger | `agent-threat-detection` (`tier2_gateway`, `tier2_gateway_session`, `vector/`, bootstrap) | **Retired from the demo lane (D1)** |
| Analyser + detector (shared ML services) | own repos | **Out of scope; only their Helm charts + image digests are referenced** |

**The functional entanglements (why this is a real migration, not a rename):**

1. `tier_c_demo/pipeline.py` imports `tier2_tier_c_live_sender` (delivery),
   `tier2_gateway_session.TierCGatewaySession` (mTLS session to Vector), and
   `tier2_console.tier_c_external_envelope` (event envelope builder).
2. `tier_c_demo/controller.py` imports `tier2_config.load_and_validate` — the
   2,631-line Tier 2 loader — to cross-validate `demo.yaml` against
   `tier2-config.yaml` at boot.
3. The controller **image is a Tier 2 program**
   (`ghcr.io/appthrust/agent-threat-detection/tier2-source-simulator`,
   ENTRYPOINT = Tier 2 worker, overridden for Tier C). Its ConfigMap additionally
   stages ~20 Tier 2 modules the Tier C path never imports (the whole
   `tier2_local` tool-proxy machinery, experiment collector, …).
4. `generate_demo.py` imports the Tier 2 `external-pipeline` generator to build
   the analyser/detector Helm values, the pipelineml-tester config loader to
   validate the dashboard runtime YAML, and the agent-threat-tier-c loader for
   the pre-processor runtime YAML.
5. The dashboard's staging step re-assembles a **synthetic two-repo tree**
   (`/work/app/agent-threat-detection/…` + `/work/app/agent-threat-tier-c/…`)
   from the controller ConfigMap; `bridge.py` verifies the staged
   `tier2-config.yaml` bytes.
6. Cosmetic only (renames, not code): `deploy/demo/tier2/` directory,
   `tier2-local-demo` cluster identity, `tier2-demo` namespace in scenario
   texts, `tier2-source-upstream-tls` secret name, image names, generation ids.

**What the pre-processor lane already proves (must keep working):** raw text →
`POST /api/items` → T-layer classify → 9-key analyser event
(`message_body, pod_family, pod, namespace, cluster, container, level,
event_time, event_kind`) → direct HTTP `POST /ingest` to the analyser. The demo
lane's new direct delivery (D1) reuses exactly this event shape.

## 3. Hard constraints

- **Scored pipeline unchanged.** Analyser, detector, feature computation,
  thresholds, and the Prometheus route are NOT modified in any package. Only
  their Helm *values* (new generation, new cluster-identity string) change.
- **Productize, don't fork the T-layer.** `tc_intent` is moved, not copied; the
  pre-processor keeps importing it unchanged in behavior.
- **The pre-processor live path must keep passing its smoke after the move**
  (same event shape byte-parity against the proven live body; same `/api/*`
  surface; same closed outcome vocabulary).
- **YAML-first, closed schemas.** Every tunable in YAML, every key required,
  unknown/duplicate keys rejected, no runtime defaults. The move must not
  silently change any validated value.
- **Fail-closed LLM pass preserved.** T-layer semantics unchanged.
- **No local docker builds.** All three images are built by GitHub workflows in
  the new repository (campaign policy).
- **Experimental test environment.** The only constraint is scope (repos under
  `appthrust/`, cluster `kind-michel-cluster`, ns `threat-detection-tierc`), not
  method. No invented production hardening.
- **Old generation untouched.** All cluster work happens on a fresh generation;
  `tierc-dashboard-incluster-g1` state stays read-only throughout.
- **Live proof runs from monstera, not through Tailscale** (D6).

## 4. Target state (the new repository)

```
agent-threat-detector-v2/
├── src/
│   ├── tc_intent/        ← moved from agent-threat-tier-c:src/tier_c_intent
│   ├── tc_preprocessor/  ← moved from agent-threat-tier-c:src/tier_c_preprocessor
│   ├── tc_demo/          ← moved + renamed from agent-threat-detection:scripts/demo/tier_c_demo;
│   │                       the 4 Tier 2 imports replaced by tc_delivery
│   ├── tc_delivery/      ← NEW small module: renders the proven 9-key event and POSTs it
│   │                       to the analyser /ingest (shared by tc_demo; shape = pre-processor's)
│   └── tc_dashboard/     ← moved from pipelineml-tester:src/pipelineml_tester/tier_c;
│                           staging/bridge rewritten for the single-repo layout
├── config/
│   ├── tier-c-intent.yaml        ← moved verbatim
│   ├── tier-c-preprocessor.yaml  ← moved; cluster identity renamed (D8)
│   ├── demo.yaml                 ← moved; self-contained: pipeline section replaces
│   │                               the tier2-config.yaml cross-pinning; no gateway/vector keys
│   ├── dashboard.yaml            ← moved (deployment authority)
│   ├── preprocessor.yaml         ← moved (deployment authority)
│   ├── tier-c.yaml               ← moved from pipelineml-tester (dashboard runtime authority);
│   │                               single source root instead of the detection/reference pair
│   ├── pipeline.yaml             ← NEW compact Tier C-only spec (release names, scope identity,
│   │                               Prometheus URL, analyser/detector image pins, timing inventory)
│   │                               replacing tier2-config.yaml + the tier_c_* extracts of
│   │                               external-pipeline.yaml for this campaign's needs
│   └── timing-inventory.yaml     ← moved (the measured 67 s bucket contract)
├── deploy/
│   ├── generate_demo.py          ← rewritten: single-repo, no Tier 2 imports
│   ├── generated/                ← the rendered artifacts (committed, --check-deterministic)
│   ├── bootstrap-tierc.yaml      ← NEW: ns-level bootstrap (Secrets, pull secret) for
│   │                               threat-detection-tierc (replaces the Tier 2 bootstrap's
│   │                               Tier C-relevant subset)
│   └── Dockerfiles               ← three: tc-demo-controller, tc-dashboard, tc-preprocessor
├── .github/workflows/            ← three image publish workflows (GHCR, appthrust org)
└── markdown/
    ├── operator-guide.md         ← Mode 1 (demo, dashboard) + Mode 2 (pre-processor,
    │                               staging/production), each: fresh install, daily use, teardown
    ├── config-reference.md       ← key parameters, plain English
    └── plans/…                   ← (campaign docs stay in agent-orchestration, see §9)
```

Images: `ghcr.io/appthrust/agent-threat-detector-v2/{tc-demo-controller,tc-dashboard,tc-preprocessor}`
(digest-pinned everywhere; digests read from the workflow job logs).

## 5. The two modes (what the docs must describe, directly usable)

**Mode 1 — demo (capability assessment).**
Fresh generation → `helm upgrade --install` the two releases with the generated
values → apply controller + dashboard (+ preprocessor) manifests → dashboard
browser / CLI drives: `validate` → normal run (48 buckets ≈ 54 min) → explicit
reference acceptance (40 distinct scores, 3 stable ticks) → attack run
(20 buckets ≈ 22 min) → expected `critical`. The controller now delivers
validated intents **directly to the analyser `/ingest`** — the mTLS gateway,
the Vector hop, the TLS Secret, and the Tier 2 sender/gateway modules are
gone (D1). Everything else the demo does (pacing 67 s buckets, 1–3 events per
cycle, scenario classification, results query, identity watch, evidence
archives) is preserved.

**Mode 2 — pre-processor (staging/production).**
`POST /api/items` (port-forward) → bounded queue → T-layer classify →
`tc_delivery`-shaped event → analyser `/ingest` → Prometheus → detector.
Own HTTP API, LLM catalog page, probes, status counters. Documented with the
shared-baseline caveat: its events reuse the demo's pod family, so never feed it
during a demo run, and a constant-rate feed cannot reach a stationary baseline.

## 6. What is NOT in scope (this campaign)

- Any change to analyser/detector **code** or to scored semantics.
- Tier 2 development of any kind (frozen, historical).
- The Vector external pipeline itself (retired from Tier C; it stays in the
  frozen Tier 2 repo as history; Tier 2's own namespace/demo is untouched).
- Portable-baseline work, security strategy, new alerting consumers.
- Production hardening beyond the existing demo security posture
  (non-root, read-only root fs, egress NetworkPolicies, digest pinning).
- Moving Prometheus or any `monitoring`-namespace infrastructure.
- The live-runner one-shot jobs (`agent-threat-tier-c/deploy/live-runner`):
  experimental side lane, not used by the demo or the pre-processor; R records
  its disposition (recommend: archive with the old repo, do not move).

## 7. Package sketch (input for P — refine, don't relitigate)

| Id | Objective (one line) | Wave |
|---|---|---|
| V2-0 | Bootstrap: create `appthrust/agent-threat-detector-v2`, scaffold layout, move campaign docs target, tag/freeze-source baselines of all source repos, snapshot live cluster state | W1 |
| V2-1 | Move T-layer + pre-processor (code, configs, tests, Dockerfile, image workflow) into the new repo; rename `tc_*`; `cluster` identity rename in preprocessor YAML; archive old repo's image path | W1 (after V2-0) |
| V2-2 | Move demo controller (`tc_demo`) + new `tc_delivery` module; replace the 4 Tier 2 imports; self-contained `demo.yaml` (pipeline section); move `dashboard.yaml`/`preprocessor.yaml` | W2 |
| V2-3 | Move dashboard app (`tc_dashboard`) + `config/tier-c.yaml`; rewrite staging/bridge for the single-repo layout | W2 (∥ V2-2, disjoint files) |
| V2-4 | Rewrite the generator (single repo, `pipeline.yaml` values generation moved in, no Tier 2 imports) + `bootstrap-tierc.yaml` + three Dockerfiles + three image workflows; publish images; digest pins | W3 |
| V2-5 | Naming/generation: new generation id + feature root, `tier-c-local-demo` identity, re-authored scenario texts, egress rule trims, secret strategy | W4 |
| V2-6 | Docs: operator guide (two modes), config reference; test-coverage review pass (D5) | W4 (∥ V2-5) |
| V2-7 | **Live proof (S-only):** fresh generation rollout on `kind-michel-cluster` **from monstera**; full demo lifecycle; pre-processor smoke; evidence record | W5 |
| V2-8 | Decommission: remove `tier_c` + `config/tier-c.yaml` from pipelineml-tester, archive `agent-threat-tier-c`, freeze `agent-threat-detection` (Tier C pieces out of its living tree); final record | W6 |

Scheduling notes: max 2 leaves; git commits on the canonical branch and all
cluster mutations serialized; V2-7 is a single serialized S lane (~1.5 h).
Test policy per D5: port only currently-green tests; record the known baseline
failures; V2-6 includes the deliberate coverage review.

## 8. Open questions for R (step 1)

1. **Import audit:** confirm the exact set of Tier 2 symbols `tier_c_demo`
   actually uses (today's map: sender, gateway session, envelope,
   `tier2_config.load_and_validate`); confirm the ~20 other staged `tier2_*`
   modules are never imported on any demo path (including the dashboard
   bridge's exec commands).
2. **`pipeline.yaml` content:** the exact minimal key set that replaces
   `tier2-config.yaml` cross-pinning for the demo (release names, scope
   identity values, Prometheus URL, provider identity, timing inventory) and
   which `external-pipeline.yaml` sections the new generator needs for the two
   Helm values files.
3. **Baseline test state:** per-repo list of currently-failing tests that are
   *known baseline* (e.g. `agent-threat-detection` `test_generate_demo.py` has
   3 recorded baseline failures tied to the old two-repo layout) — these are
   the ones D5 says not to port.
4. **New-repo CI prerequisites:** what the three image workflows need that the
   source repos' workflows already prove (GHCR login via `GITHUB_TOKEN`,
   buildx platforms, digest-print step) and whether `appthrust` org permissions
   for a new repo need any setup.
5. **Cluster objects:** the exact current Secret/ConfigMap/NetworkPolicy
   inventory in `threat-detection-tierc` that a fresh install from the new repo
   must reproduce or replace (including whether `regcred` and
   `tier-c-live-runner-credentials` are reused as-is).
6. **Live-runner disposition:** confirm the `agent-threat-tier-c/deploy/live-runner`
   jobs are not referenced by any demo/pre-processor path.
7. **Digest discrepancy:** the live detector deployment image
   (`sha256:ea031f…`) differs from the local generated values
   (`sha256:4ef9cd…`); determine which is current so the cutover pins the right
   one (or supersedes both).

## 9. Campaign artifacts & execution environment

- **Vision:** this file.
- **Plan + workcards + gates + record:**
  `agent-orchestration/markdown/plans/tier-c-v2-migration/` (the campaign spans
  repo creation/freeze, so it lives in the orchestration repo; precedent:
  `tier-c-end-to-end-demo`, `tier-c-public-docs`). Binding decisions:
  `…/tier-c-v2-migration/s-decisions.md`.
- **Execution environment:** OMP Supervisor session **on monstera itself**
  (working dir `/home/michel/Work/appthrust`), inside tmux; no Tailscale in the
  loop. The environment-preparation runbook is
  `agent-orchestration/instructions/2026-11-02/omp-on-monstera-setup.md`
  (separate file, executed by an opencode session on monstera before the
  Supervisor is dispatched).

## 10. Out-of-vision notes (honest limits)

- This campaign **changes what the demo demonstrates**: after D1 the demo no
  longer routes through the gateway/Vector hop. The historical evidence
  (generation 5 proof, recorded in the frozen repo) was produced on the old
  route; the new live proof is on the direct route. Both are true statements
  about their respective configurations; the docs must say so.
- The move is large in line count but small in novelty: ~3 of the 4 code areas
  move with mechanical renames; the genuinely new logic is `tc_delivery`
  (small), the generator's values stage (a moved function), and the dashboard
  staging rewrite (bounded).
- If any package reveals a Tier 2 dependency not in §2, that is an R/P finding
  handled through the normal loop, not a reason to freeze the campaign.
