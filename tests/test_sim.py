import unittest
from chunksched.sim import run, make_net, evaluate
import random

CLEAN = dict(base=0.05, p_spike=0.0, p_bad=0.0, p_stay_bad=0.7)


class T(unittest.TestCase):
    def test_adaptive_aligned_no_lag_on_clean_net(self):
        r = run("adaptive", CLEAN, 1, 50)
        self.assertAlmostEqual(r["lag_ms"], 0.0, delta=1.0)
        self.assertLess(r["stall"], 0.05)

    def test_prefetch_lags_by_round_trip(self):
        r = run("prefetch", CLEAN, 1, 50)
        self.assertGreater(r["lag_ms"], 40)          # executes stale actions from index 0

    def test_blocking_stalls(self):
        self.assertGreater(run("blocking", CLEAN, 1, 50)["stall"], 0.03)

    def test_hedging_costs_requests(self):
        net = make_net(random.Random(3), True)
        self.assertGreaterEqual(run("hedged", net, 5, 25)["req_per_s"], run("adaptive", net, 5, 25)["req_per_s"])

    def test_adaptive_beats_blocking(self):
        r = evaluate(8, 4, False, 50)
        self.assertLess(r["adaptive"]["rmse"], r["blocking"]["rmse"])


if __name__ == "__main__":
    unittest.main()
