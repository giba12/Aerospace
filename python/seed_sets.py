"""Seed sets for the estimator acceptance tests (TST-012).

Two disjoint sets of random seeds for the sensor noise:

  TUNING_SEEDS    the only seeds anyone may look at while choosing the filter's settings
                  (q, R, P0) or re-measuring the thresholds (baseline OI-02).
  HELD_OUT_SEEDS  used ONLY by the acceptance tests EST-008 and EST-012. Never inspect results on
                  these while adjusting anything: that would turn "performs well on unseen data"
                  back into "was chosen to look good" (baseline CR-06, risk R-05).

If an acceptance test fails, the response is to fix the filter or to document the limit, never to
loosen a threshold or swap seeds until it passes. A test in tests/python checks that the two
sets stay disjoint and that the held-out set has at least 20 seeds (EST-012).
"""

TUNING_SEEDS = tuple(range(1, 201))          # 200 seeds, like the baseline's prototype run
HELD_OUT_SEEDS = tuple(range(1001, 1051))    # 50 seeds
