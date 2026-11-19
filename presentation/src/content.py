"""Words shared by the LinkedIn carousel and the slide deck. Numbers come from the repository."""
from common import metrics, seeds, test_counts, requirements, loc

M = metrics()
SEEDS = seeds()
CPP, PY = test_counts()
REQ = requirements()
N_REQ = sum(t for _, t in REQ.values())
N_MUST = sum(m for m, _ in REQ.values())
N_TESTS = CPP + PY
RATIO_MEAN = sum(r[3] for r in SEEDS) / len(SEEDS)
RATIO_WORST = max(r[3] for r in SEEDS)
RATIO_BEST = min(r[3] for r in SEEDS)
COV_POOLED = 9807 / 10050          # docs/VALIDATION.md, pooled over the 50 held-out seeds

DISCLAIMER = "Educational simulation. Not flight software; no flight qualification is claimed."

DESIGN = [
    ("Truth firewall", "The estimator only ever receives measurements. A static_assert stops the build if any "
                       "overload could accept ground truth (SYS-002)."),
    ("Small interfaces", "ISensor, IEstimator and IRecorder let the Runner be tested with fakes and keep each "
                         "part replaceable."),
    ("Maths as pure functions", "kalman_predict and kalman_update take and return a belief; the estimator class "
                                "is a thin state machine around them."),
    ("Deterministic by design", "Seeded mt19937_64, time computed as t = k·dt (never accumulated), 17-digit CSV: "
                                "same inputs give identical output."),
    ("Fail closed", "Outputs are written to a temp file then renamed. Bad input is refused with a clear error, "
                    "never silently patched."),
    ("Reproducible build", "Pinned Python packages, GoogleTest fetched by SHA-256, container base image pinned "
                           "by digest."),
]

# (requirement ids, test name, given / expect, why it matters)
TESTCASES = [
    ("EST-001 · EST-011", "KalmanMath.UpdateMatches\nVvEst01IncludingTheJosephForm",
     "Given x̂=[0,10], P=diag(25,100), dt=0.1, q=0.1, R=25, reading z=3 (worked by hand in a separate prototype).",
     "Expect position 2.0196 m, velocity 10.392 m/s, P₀₀ 12.745 within 1e-9.",
     "Catches sign, ordering and covariance-form mistakes."),
    ("SYS-002 · EST-002", "Interfaces.\nEstimatorCannotAcceptTruth",
     "A static_assert checks, at compile time, that the estimator interface can take a Measurement and cannot take a TrueState.",
     "Expect the test binary to compile.",
     "If anyone adds a truth overload, the build breaks."),
    ("EST-001 · VAL-04", "test_cpp_filter_agrees_with_\nthe_independent_oracle",
     "9 scenarios (high noise, accelerating truth, 20,000-step gap...). Python recomputes every estimate in 60-digit decimals.",
     "Expect agreement within max(1e-9, 2·k·u·|value|).",
     "A sabotage test nudges one estimate by 1e-6 and requires the check to catch it."),
    ("EST-008 · EST-012", "test_estimator_performance\n(50 held-out seeds)",
     "Run the real sim once per seed (1001–1050), seeds never used for tuning.",
     f"Expect ratio ≤ 0.75 on every seed (worst {RATIO_WORST:.3f}) and ≥ 90 % pooled coverage ({COV_POOLED:.3f}).",
     "Proves the filter helps and its error bars are honest."),
    ("SEN-003", "NoisySensor.NoiseHasThe\nRequestedMeanAndSpread",
     "σ = 5 m, 10,000 samples, fixed seed. σ = 0 must return the exact position.",
     "Expect mean within ±0.25 m and std within ±5 % of σ.",
     "Same seed, different σ gives the same pattern, scaled."),
    ("SIM-004 · SIM-002", "Dynamics.EulerWithAcceleration\nMatchesVvSim01",
     "x₀=0, v₀=10 m/s, a=1 m/s², dt=0.1 s, 1,000 steps.",
     "Expect 5995.0 m and 110.0 m/s. Exact answer is 6000.0 m; the gap is a·t·dt/2 = 5 m.",
     "A mutation test confirmed a swapped Euler order is caught."),
]

STACK = [
    ("Core", ["C++17", "GCC 13 · Clang 18", "CMake 3.28 + Ninja"]),
    ("Analysis", ["Python 3.12", "matplotlib 3.10", "pytest 8.3"]),
    ("Quality", ["GoogleTest 1.17", "ASan + UBSan", "gcovr coverage"]),
    ("Delivery", ["GitHub Actions CI", "Docker / Podman", "pinned dependencies"]),
]

KEY_NUMBERS = [
    (f"{N_REQ}", f"requirements, {N_MUST} of them Must, each traced to a test"),
    (f"{N_TESTS}", f"automated tests ({CPP} C++ · {PY} Python)"),
    ("94 %", "line coverage; 100 % of functions"),
    ("50", "held-out seeds, kept apart from tuning"),
]
