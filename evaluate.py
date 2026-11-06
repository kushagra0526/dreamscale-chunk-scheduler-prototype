"""python evaluate.py dev|heldout"""
import json
import os
import sys
from chunksched.sim import evaluate

name = sys.argv[1] if len(sys.argv) > 1 else "dev"
cfg = {"dev": (60, 1, False, 50), "heldout": (100, 9001, True, 25)}[name]
res = evaluate(*cfg)
os.makedirs("results", exist_ok=True)
json.dump(res, open(f"results/{name}.json", "w"), indent=1)
print(f"{name}: {cfg[0]} one-minute runs, chunk H={cfg[3]}, hard={cfg[2]}")
print(f"{'policy':10} {'stall %':>8} {'p95 stall %':>11} {'lag ms':>7} {'rmse':>6} {'req/s':>6}")
for p, r in res.items():
    print(f"{p:10} {r['stall_pct']:8.2f} {r['worst_stall_pct']:11.2f} {r['lag_ms']:7.0f} {r['rmse']:6.3f} {r['req_per_s']:6.2f}")
