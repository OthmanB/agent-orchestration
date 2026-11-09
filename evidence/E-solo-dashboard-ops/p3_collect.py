#!/usr/bin/env python3
"""SOLO-OPS P3 observation-window collector / measurer (read-only GETs).

Usage:
  p3_collect.py collect [--base http://127.0.0.1:18086]   # append new ticks of all pods to the store
  p3_collect.py report  --rollout-epoch <epoch_s>          # measure the P3 acceptance from the store

The solo `/solo` history ring holds 288 ticks (= 24 h at 5 min), so `collect`
must run at least every 12 h; ticks are de-duplicated by (pod, tick_epoch).
The store survives across sessions: evidence/E-solo-dashboard-ops/p3-ticks.jsonl
Acceptance (vision §3-P3): over unique ticks with tick_epoch >= rollout epoch,
per pod frac(p_published < normal_threshold) >= 0.95, no ~2 h sawtooth, degenerate-fit
pods publish probability_label == "raw". Spike ticks count as they are; no retuning.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "p3-ticks.jsonl")
NS = "ml-components"


def get(base: str, path: str, timeout: int = 120):
    with urllib.request.urlopen(base + path, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def pod_names(base: str) -> list[str]:
    body = get(base, "/api/dashboard/pods")
    names = []
    for row in body.get("pod_families") or []:
        labels = row.get("labels") or []
        if len(labels) >= 4:
            names.append(labels[3])
    return sorted(set(names))


def load_store() -> dict[tuple[str, float], dict]:
    out: dict[tuple[str, float], dict] = {}
    if os.path.exists(STORE):
        with open(STORE, encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                out[(rec["pod"], rec["tick_epoch"])] = rec
    return out


def collect(base: str) -> None:
    have = load_store()
    new = 0
    with open(STORE, "a", encoding="utf-8") as fh:
        for pod in pod_names(base):
            payload = get(base, f"/api/dashboard/pods/{pod}/solo?namespace={NS}&cluster=")
            thresholds = ((payload.get("tick") or {}).get("details") or {}).get("thresholds") or {}
            for row in payload.get("history") or []:
                key = (pod, float(row["tick_epoch"]))
                if key in have:
                    continue
                details = row.get("details") or {}
                rec = {
                    "pod": pod,
                    "tick_epoch": float(row["tick_epoch"]),
                    "p_raw": row.get("p_raw"),
                    "p_published": row.get("p_published"),
                    "label": details.get("probability_label"),
                    "calibration_state": details.get("calibration_state"),
                    "normal_threshold": thresholds.get("normal"),
                    "anomaly_threshold": thresholds.get("anomaly"),
                }
                fh.write(json.dumps(rec) + "\n")
                have[key] = rec
                new += 1
    print(f"store={STORE} new_ticks={new} total={len(have)}")


def report(rollout_epoch: float) -> None:
    store = load_store()
    per: dict[str, list[dict]] = {}
    for (pod, tick), rec in store.items():
        if tick >= rollout_epoch:
            per.setdefault(pod, []).append(rec)
    print(f"rollout_epoch={rollout_epoch} pods={len(per)}")
    all_ok = True
    for pod in sorted(per):
        rows = sorted(per[pod], key=lambda r: r["tick_epoch"])
        n = len(rows)
        thr = next((r["normal_threshold"] for r in rows if r["normal_threshold"] is not None), None)
        valid = [r for r in rows if r["p_published"] is not None]
        below = sum(1 for r in valid if thr is not None and r["p_published"] < thr)
        raw_gt02 = sum(1 for r in valid if (r["p_raw"] or 0) > 0.2)
        raw_gt08 = sum(1 for r in valid if (r["p_raw"] or 0) > 0.8)
        labels: dict[str, int] = {}
        for r in rows:
            labels[str(r["label"])] = labels.get(str(r["label"]), 0) + 1
        frac = below / len(valid) if valid else float("nan")
        span_h = (rows[-1]["tick_epoch"] - rows[0]["tick_epoch"]) / 3600.0 if n > 1 else 0.0
        ok = frac >= 0.95
        all_ok &= ok and span_h >= 24.0 - 1e-6
        print(
            f"{pod[-34:]:34s} n={n:4d} span={span_h:5.1f}h frac(p_pub<{thr})={frac:.3f} "
            f"raw>0.2={raw_gt02} raw>0.8={raw_gt08} labels={labels} {'OK' if ok else 'BELOW 95%'}"
        )
    print("WINDOW COMPLETE (>=24h on every pod) AND >=95% everywhere:", all_ok)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--base", default="http://127.0.0.1:18086")
    r = sub.add_parser("report")
    r.add_argument("--rollout-epoch", type=float, required=True)
    args = ap.parse_args()
    if args.cmd == "collect":
        collect(args.base)
    else:
        report(args.rollout_epoch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
