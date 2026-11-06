# dreamscale-chunk-scheduler-prototype

**Problem.** Dreamscale runs the robot's model in the cloud: the robot sends camera frames and joint positions and gets actions back ([docs](https://docs.dreamscalelabs.com)). Policies like pi0.5 answer with a chunk of future actions, so the client must decide *when to ask for the next chunk* and *which index of it to start at* while the network jitters, spikes and drops requests. I could not find the chunk size, control rate or transport in their public docs, so those are my assumptions (50 Hz; chunk of 50 or 25 actions).

**What I built.** A stdlib-only simulator of a 50 Hz robot following a known motion, with four client policies:

- `blocking`: ask when the chunk is empty, wait.
- `prefetch`: ask 10 actions early, start the new chunk at index 0.
- `adaptive`: ask `p95 round-trip` early (from recent samples), and start the new chunk at the index that matches the time that passed since its observation (so no lag).
- `hedged`: adaptive, plus a duplicate request when the first is late (about 2.7x the requests in the hard case).

Metrics: stall (no action available, arm holds), lag (how old the executed action is), RMSE against the ideal motion, requests per second.

```
python -m unittest discover -s tests -t .   # 5 tests
python evaluate.py dev                       # 60 one-minute runs, H=50
python evaluate.py heldout                   # 100 harder runs, H=25
```

**Results.** The held-out config (seed 9001, base round trip 80-200 ms, 6% spikes of 0.3-1.5 s, 4% loss bursts, H=25) was committed before it was first run, and nothing was changed after (`results/`).

| held-out | stall % | lag ms | RMSE | requests/s |
|---|---|---|---|---|
| blocking | 40.4 | 176 | 0.907 | 1.4 |
| prefetch | 29.2 | 176 | 0.897 | 1.8 |
| adaptive | 41.8 | 0 | 0.696 | 3.1 |
| hedged | 28.5 | 0 | 0.550 | 3.8 |

Dev (milder network, H=50): stall 11.6 / 5.0 / 2.1 / 1.0 %, RMSE 0.52 / 0.50 / 0.10 / 0.06.

**What it shows and what it does not.** Aligning the chunk index removes the lag in every case. In the harsh network `adaptive` alone does *not* cut stalls (41.8% vs 40.4% for blocking): with a half-second chunk and 1.5 s spikes everyone runs dry. Only duplicate requests help there, at a request cost. Billing is per robot-hour connected, so extra requests cost bandwidth, not money, as far as their pricing page says.

**Limits.** Toy motion, perfect policy predictions (no error growing along the chunk), invented network parameters, no real robot or Dreamscale API call.

Unofficial prototype by Kushagra Pratap Singh. Not affiliated with Dreamscale Labs.
