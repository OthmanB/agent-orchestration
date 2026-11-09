#!/usr/bin/env python3
"""Capture, for each solo pod, the newest /timeseries point timestamp (= live publish wall clock)
plus its /solo reference_tick_epoch. Read-only GETs. Appends one JSON line per pod to R-P1-publish.jsonl."""
import json, sys, time, urllib.request
from datetime import datetime, timezone

BASE = "http://127.0.0.1:8080/api/dashboard"
OUT = "/Users/obenomar/Work/langGraph/appthrust/agent-orchestration/evidence/E-solo-dashboard-ops/R-P1-publish.jsonl"

def get(url):
    with urllib.request.urlopen(url, timeout=25) as r:
        return json.loads(r.read().decode())

def main():
    pods_payload = get(BASE + "/pods")
    rec = {"sample_ts": datetime.now(timezone.utc).isoformat(), "pods": []}
    for p in pods_payload.get("pod_families") or []:
        name = p.get("pod") or (p.get("labels") or [None]*4)[3]
        q = "?namespace=%s&cluster=%s" % (
            urllib.parse.quote(str(p.get("namespace") or "")),
            urllib.parse.quote(str(p.get("cluster") or "")),
        )
        row = {
            "pod": name,
            "last_seen_data_ts": p.get("last_seen_data_ts"),
            "last_seen_data_age_seconds": p.get("last_seen_data_age_seconds"),
            "data_freshness_state": p.get("data_freshness_state"),
            "pipeline_state": p.get("pipeline_state"),
        }
        try:
            ts = get(BASE + "/pods/" + name + "/timeseries" + q + "&window_hours=6&interval_seconds=60")
            pts = ts.get("points") or []
            row["n_points"] = len(pts)
            row["newest_point_t"] = pts[-1].get("t") if pts else None
            row["newest_point_prob"] = pts[-1].get("probability") if pts else None
        except Exception as e:
            row["timeseries_error"] = repr(e)
        try:
            solo = get(BASE + "/pods/" + name + "/solo" + q)
            row["reference_tick_epoch"] = solo.get("reference_tick_epoch")
            hist = solo.get("history") or []
            row["last_history_tick_epoch"] = hist[-1].get("tick_epoch") if hist else None
            row["n_history"] = len(hist)
            details = (solo.get("tick") or {}).get("details") or {}
            metrics = details.get("metrics") or {}
            stamps = []
            for m in metrics.values():
                ba = (m or {}).get("block_attribution") or {}
                if ba.get("last_stamp") is not None:
                    stamps.append(float(ba["last_stamp"]))
            row["max_block_last_stamp"] = max(stamps) if stamps else None
        except Exception as e:
            row["solo_error"] = repr(e)
        rec["pods"].append(row)
    with open(OUT, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    print("wrote", len(rec["pods"]), "pod rows")

if __name__ == "__main__":
    import urllib.parse
    main()
