"""Client-side scheduler for action chunks streamed from a cloud robot policy.
Simulated 50 Hz robot, chunk of H actions per reply, jittery/lossy network. Stdlib only.

Ideal motion a(t) is known, so a chunk computed from the observation at tick o gives
action a(o + i) at index i. Executing index i at tick k means the arm follows a(o + i);
error = |a(o + i) - a(k)|. Holding still when no action is available is a stall."""
import math
import random

HZ = 50


def ideal(t):
    return math.sin(2 * math.pi * 0.7 * t / HZ) + 0.5 * math.sin(2 * math.pi * 1.9 * t / HZ)


def make_net(rng, hard):
    return dict(
        base=rng.uniform(0.08, 0.20) if hard else rng.uniform(0.04, 0.10),   # s, round trip + compute
        p_spike=0.06 if hard else 0.02,
        p_bad=0.04 if hard else 0.01,          # chance a request enters a loss burst
        p_stay_bad=0.7,
    )


def run(policy, net, seed, H, secs=60):
    rng = random.Random(seed)
    n = secs * HZ
    pending = []                 # (arrive_tick, obs_tick, req_id)
    served, req_id = set(), 0
    sent_at = {}
    cur = None                   # (arrive_tick, obs_tick, start_idx)
    rtts = [net["base"]] * 10    # recent observed round trips (s)
    bad = False
    stall = lag_sum = lag_n = 0
    sq = 0.0
    last_phase = 0.0
    requests = 0
    outstanding = None           # req_id awaited

    def send(k):
        nonlocal req_id, bad, requests
        requests += 1
        req_id += 1
        bad = rng.random() < (net["p_stay_bad"] if bad else net["p_bad"])
        sent_at[req_id] = k
        if not bad:
            rtt = net["base"] * rng.lognormvariate(0, 0.25)
            if rng.random() < net["p_spike"]:
                rtt += rng.uniform(0.3, 1.5)
            pending.append((k + math.ceil(rtt * HZ), k, req_id))
        return req_id

    def q95():
        s = sorted(rtts[-50:])
        return s[int(0.95 * (len(s) - 1))]

    for k in range(n):
        for item in sorted(x for x in pending if x[0] <= k):
            pending.remove(item)
            arr, obs, rid = item
            if rid in served:
                continue
            served.add(rid)
            rtts.append((arr - obs) / HZ)
            if cur is None or obs > cur[1]:
                aligned = policy in ("adaptive", "hedged")
                start = (k - obs) if aligned else 0
                if start < H:
                    cur = (k, obs, start)
            if outstanding == rid:
                outstanding = None
        idx = None
        if cur is not None:
            i = cur[2] + (k - cur[0])
            if i < H:
                idx = i
        remaining = 0 if idx is None else H - idx
        if policy == "blocking":
            want = remaining <= 0
        elif policy == "prefetch":
            want = remaining <= 10
        else:
            want = remaining <= math.ceil(q95() * HZ) + 3
        age = None if outstanding is None else (k - sent_at[outstanding]) / HZ
        timeout = 1.0 if policy in ("blocking", "prefetch") else 2 * q95() + 0.1
        if want and (outstanding is None or age > timeout):
            outstanding = send(k)
        elif policy == "hedged" and want and outstanding is not None and age > 1.3 * q95() \
                and not any(sent_at[r] > sent_at[outstanding] for r in sent_at if r != outstanding and r > outstanding):
            send(k)
        if idx is None:
            stall += 1
            phase = last_phase
        else:
            phase = cur[1] + idx
            lag_sum += k - phase
            lag_n += 1
            last_phase = phase
        sq += (ideal(phase) - ideal(k)) ** 2
    return dict(stall=stall / n, lag_ms=1000 * lag_sum / max(1, lag_n) / HZ,
                rmse=math.sqrt(sq / n), req_per_s=requests / secs)


POLICIES = ("blocking", "prefetch", "adaptive", "hedged")


def evaluate(n, seed, hard, H):
    rng = random.Random(seed)
    nets = [(make_net(rng, hard), rng.randrange(10**9)) for _ in range(n)]
    out = {}
    for p in POLICIES:
        rs = [run(p, net, s, H) for net, s in nets]
        m = lambda key: sum(r[key] for r in rs) / n
        out[p] = dict(stall_pct=100 * m("stall"), lag_ms=m("lag_ms"), rmse=m("rmse"),
                      req_per_s=m("req_per_s"),
                      worst_stall_pct=100 * sorted(r["stall"] for r in rs)[int(0.95 * (n - 1))])
    return out
