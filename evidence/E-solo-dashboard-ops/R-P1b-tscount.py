#!/usr/bin/env python3
"""P1b: per-pod /timeseries point-count probe every 15s for ~5.5 min -> JSONL."""
import json, time, urllib.request
from datetime import datetime, timezone

BASE = "http://127.0.0.1:8080/api/dashboard/pods"
OUT = "/Users/obenomar/Work/langGraph/appthrust/agent-orchestration/evidence/E-solo-dashboard-ops/R-P1b-tscount.jsonl"
PERIOD = 15.0
DURATION = 330.0


def get(url, timeout=20):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def main():
    t0 = time.time()
    n = 0
    with open(OUT, "w", encoding="utf-8") as fh:
        while time.time() - t0 < DURATION:
            ts = datetime.now(timezone.utc).isoformat()
            try:
                fams = get(BASE)["pod_families"]
            except Exception as exc:  # noqa: BLE001
                fh.write(json.dumps({"t": ts, "error": str(exc)}) + "\n")
                time.sleep(PERIOD)
                continue
            rec = {"t": ts, "pods": {}}
            for p in fams:
                pn = p["pod"]
                try:
                    d = get(BASE + "/" + pn + "/timeseries?namespace=ml-components&cluster=")
                    pts = d.get("points") or []
                    rec["pods"][pn] = {
                        "n": len(pts),
                        "last": pts[-1].get("t") if pts else None,
                        "state": p.get("data_freshness_state"),
                    }
                except Exception as exc:  # noqa: BLE001
                    rec["pods"][pn] = {"error": str(exc)}
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            n += 1
            nxt = t0 + n * PERIOD
            slp = nxt - time.time()
            if slp > 0:
                time.sleep(slp)
    print("done probes=%d" % n)


if __name__ == "__main__":
    main()
