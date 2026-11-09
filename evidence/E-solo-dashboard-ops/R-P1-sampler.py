#!/usr/bin/env python3
"""P1 freshness sampler: GET /api/dashboard/pods every ~10s for ~12 min -> timestamped JSONL."""
import json, sys, time, urllib.request
from datetime import datetime, timezone

URL = "http://127.0.0.1:8080/api/dashboard/pods"
OUT = "/Users/obenomar/Work/langGraph/appthrust/agent-orchestration/evidence/E-solo-dashboard-ops/R-P1-pods-samples.jsonl"
DURATION = 740   # seconds
PERIOD = 10.0

def now():
    return datetime.now(timezone.utc).isoformat()

def main():
    t0 = time.time()
    n = 0
    with open(OUT, "w", encoding="utf-8") as fh:
        while time.time() - t0 < DURATION:
            rec = {"sample_ts": now(), "sample_epoch": time.time(), "ok": False}
            try:
                with urllib.request.urlopen(URL, timeout=15) as r:
                    body = json.loads(r.read().decode())
                rec["ok"] = True
                rec["payload_freshness_state"] = body.get("freshness_state")
                rec["generated_at"] = body.get("generated_at") or body.get("timestamp")
                pods = []
                for p in body.get("pod_families") or []:
                    pods.append({
                        "id": p.get("id") or p.get("pod_id") or p.get("name"),
                        "name": p.get("name"),
                        "labels": p.get("labels"),
                        "phase": p.get("phase"),
                        "last_seen_data_age_seconds": p.get("last_seen_data_age_seconds"),
                        "last_seen_data_ts": p.get("last_seen_data_ts"),
                        "data_freshness_state": p.get("data_freshness_state"),
                        "data_freshness_reason": p.get("data_freshness_reason"),
                        "indicator_b_state": p.get("indicator_b_state"),
                        "indicator_b_label": p.get("indicator_b_label"),
                        "data_time_drift_seconds": p.get("data_time_drift_seconds"),
                        "analysis_state": p.get("analysis_state"),
                        "alert_state": p.get("alert_state"),
                        "active_model_family": p.get("active_model_family"),
                    })
                rec["pods"] = pods
                rec["n_pods"] = len(pods)
            except Exception as e:
                rec["error"] = repr(e)
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            n += 1
            # keep cadence near PERIOD
            nxt = t0 + n * PERIOD
            slp = nxt - time.time()
            if slp > 0:
                time.sleep(slp)
    print("done samples=%d" % n)

if __name__ == "__main__":
    main()
