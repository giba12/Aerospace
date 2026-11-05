#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <stdexcept>

#include "scenarios.hpp"
#include "simulator/dynamics.hpp"
#include "simulator/estimator.hpp"
#include "simulator/kalman.hpp"
#include "tolerances.hpp"

using namespace sim;
using namespace sim::testing;

namespace {

constexpr double kTol = 1e-9;  // baseline 6.3: covariance and C++-vs-oracle agreement

// A reading helper: the sensor_id is irrelevant to the filter.
Measurement reading(double t_s, double position_m) {
    return Measurement{t_s, position_m, "test"};
}

void expect_state(const KalmanState& got, double x, double v, double p00, double p01, double p10,
                  double p11, double tol = kTol) {
    EXPECT_NEAR(got.x.v0, x, tol);
    EXPECT_NEAR(got.x.v1, v, tol);
    EXPECT_NEAR(got.P.m00, p00, tol);
    EXPECT_NEAR(got.P.m01, p01, tol);
    EXPECT_NEAR(got.P.m10, p10, tol);
    EXPECT_NEAR(got.P.m11, p11, tol);
}

}  // namespace

// ---- The maths: VV-EST-01 (baseline 6.6), worked independently in a throwaway prototype ----
// x = [0, 10], P = diag(25, 100), dt = 0.1, q = 0.1, R = 25, z = 3.

TEST(KalmanMath, PredictMatchesVvEst01) {
    RecordProperty("requirements", "EST-001,EST-003");
    const KalmanState start{Vec2{0.0, 10.0}, Mat2{25.0, 0.0, 0.0, 100.0}};
    const KalmanState p = kalman_predict(start, 0.1, 0.1);
    expect_state(p, 1.0, 10.0, 26.0000333333, 10.0005, 10.0005, 100.01);
}

TEST(KalmanMath, UpdateMatchesVvEst01IncludingTheJosephForm) {
    RecordProperty("requirements", "EST-001,EST-011");
    // Start from the exact predicted belief rather than the baseline's 10-decimal rounding of it.
    const KalmanState predicted =
        kalman_predict({Vec2{0.0, 10.0}, Mat2{25.0, 0.0, 0.0, 100.0}}, 0.1, 0.1);
    const KalmanState u = kalman_update(predicted, 3.0, 25.0);
    expect_state(u, 2.0196084839, 10.3921762143, 12.7451060490, 4.9022026783, 4.9022026783,
                 98.0490208846);
}

TEST(KalmanMath, PredictOnlyMovesTheGuessForwardAndGrowsTheDoubt) {
    RecordProperty("requirements", "EST-003");
    const KalmanState start{Vec2{100.0, 10.0}, Mat2{4.0, 0.0, 0.0, 1.0}};
    const KalmanState p = kalman_predict(start, 0.5, 0.1);
    EXPECT_NEAR(p.x.v0, 100.0 + 10.0 * 0.5, kTol);  // position advances by v * dt
    EXPECT_DOUBLE_EQ(p.x.v1, 10.0);                 // velocity is held
    EXPECT_GT(p.P.m00, start.P.m00);                // doubt grows
    EXPECT_GT(p.P.m11, start.P.m11);
}

TEST(KalmanMath, UpdateMovesTowardTheReadingAndShrinksTheDoubt) {
    RecordProperty("requirements", "EST-004");
    const KalmanState start{Vec2{10.0, 0.0}, Mat2{25.0, 0.0, 0.0, 100.0}};
    const KalmanState u = kalman_update(start, 20.0, 25.0);
    EXPECT_GT(u.x.v0, 10.0);   // moved toward 20 ...
    EXPECT_LT(u.x.v0, 20.0);   // ... but not all the way: the filter does not fully trust the sensor
    EXPECT_LT(u.P.m00, start.P.m00);
    EXPECT_NEAR(u.x.v0, 15.0, kTol);  // equal doubt in guess and sensor (25 and 25): halfway
}

// ---- The estimator: state machine, rejected input, long-run health ----

TEST(KalmanEstimator, InitializesFromTheFirstReadingWithoutPredicting) {
    RecordProperty("requirements", "EST-009");
    KalmanEstimator e(EstimatorConfig{});
    EXPECT_FALSE(e.initialized());
    const Estimate est = e.initialize(reading(0.5, 7.0));
    EXPECT_TRUE(e.initialized());
    EXPECT_DOUBLE_EQ(est.position_m, 7.0);   // exactly the reading: no predict step happened
    EXPECT_DOUBLE_EQ(est.velocity_mps, 0.0);
    EXPECT_DOUBLE_EQ(est.P.m00, 25.0);       // P0 = diag(25, 100)
    EXPECT_DOUBLE_EQ(est.P.m11, 100.0);
    EXPECT_DOUBLE_EQ(est.P.m01, 0.0);
    EXPECT_DOUBLE_EQ(est.t_s, 0.5);
}

TEST(KalmanEstimator, PredictOrUpdateBeforeInitializeAreRejectedAndChangeNothing) {
    RecordProperty("requirements", "EST-009");
    KalmanEstimator e(EstimatorConfig{});
    EXPECT_THROW(e.predict(0.1), std::logic_error);
    EXPECT_THROW(e.update(reading(0.0, 1.0)), std::logic_error);
    EXPECT_FALSE(e.initialized());
    // The rejected calls changed nothing: the estimator still starts cleanly from a first reading.
    EXPECT_DOUBLE_EQ(e.initialize(reading(0.0, 1.0)).position_m, 1.0);
}

TEST(KalmanEstimator, SecondInitializeIsRejected) {
    RecordProperty("requirements", "EST-009");
    KalmanEstimator e(EstimatorConfig{});
    e.initialize(reading(0.0, 1.0));
    EXPECT_THROW(e.initialize(reading(0.1, 9.0)), std::logic_error);
    EXPECT_DOUBLE_EQ(e.predict(0.1).position_m, 1.0);  // still the first reading's estimate
}

TEST(KalmanEstimator, RejectsBadSettingsAndBadTimeSteps) {
    RecordProperty("requirements", "EST-010");
    EstimatorConfig bad;
    bad.r_m2 = 0.0;
    EXPECT_THROW(KalmanEstimator{bad}, std::invalid_argument);

    KalmanEstimator e(EstimatorConfig{});
    e.initialize(reading(0.0, 1.0));
    for (const double dt : {0.0, -0.1, std::nan(""), std::numeric_limits<double>::infinity()}) {
        EXPECT_THROW(e.predict(dt), std::invalid_argument) << dt;
    }
}

TEST(KalmanEstimator, RejectedReadingsLeaveTheStateUnchanged) {
    RecordProperty("requirements", "EST-013");
    const double nan = std::nan("");
    const double inf = std::numeric_limits<double>::infinity();

    // `e` receives garbage in between; `twin` never sees it. They must stay identical.
    KalmanEstimator e(EstimatorConfig{});
    KalmanEstimator twin(EstimatorConfig{});
    e.initialize(reading(1.0, 10.0));
    twin.initialize(reading(1.0, 10.0));
    e.predict(0.1);
    twin.predict(0.1);

    EXPECT_THROW(e.update(reading(1.1, nan)), std::invalid_argument);
    EXPECT_THROW(e.update(reading(1.1, inf)), std::invalid_argument);
    EXPECT_THROW(e.update(reading(nan, 10.0)), std::invalid_argument);
    EXPECT_THROW(e.update(reading(0.5, 10.0)), std::invalid_argument);  // older than t = 1.0

    const Estimate a = e.update(reading(1.1, 11.0));
    const Estimate b = twin.update(reading(1.1, 11.0));
    EXPECT_DOUBLE_EQ(a.position_m, b.position_m);
    EXPECT_DOUBLE_EQ(a.velocity_mps, b.velocity_mps);
    EXPECT_DOUBLE_EQ(a.P.m00, b.P.m00);
    EXPECT_DOUBLE_EQ(a.P.m01, b.P.m01);
    EXPECT_DOUBLE_EQ(a.P.m11, b.P.m11);
}

TEST(KalmanEstimator, NonFiniteFirstReadingIsRejected) {
    RecordProperty("requirements", "EST-013");
    KalmanEstimator e(EstimatorConfig{});
    EXPECT_THROW(e.initialize(reading(0.0, std::nan(""))), std::invalid_argument);
    EXPECT_FALSE(e.initialized());
}

TEST(KalmanEstimator, CovarianceStaysSymmetricWithNonNegativeDiagonalOver1000Steps) {
    RecordProperty("requirements", "EST-006");
    const DynamicsConfig dyn = make_cfg(0.0, 10.0, 0.0, 0.1, 1000);
    KalmanEstimator e(EstimatorConfig{});
    TrueState truth = initial_state(dyn);
    e.initialize(reading(truth.t_s, truth.position_m));
    for (std::int64_t k = 1; k <= dyn.steps; ++k) {
        truth = propagate(truth, dyn, k);
        Estimate est = e.predict(dyn.dt_s);
        if (k % 5 == 0) {
            est = e.update(reading(truth.t_s, truth.position_m + ((k % 10 == 0) ? 3.0 : -3.0)));
        }
        ASSERT_LT(std::fabs(est.P.m01 - est.P.m10), 1e-9) << "step " << k;
        ASSERT_GE(est.P.m00, 0.0) << "step " << k;
        ASSERT_GE(est.P.m11, 0.0) << "step " << k;
    }
}

// EST-007: with a perfect sensor and a filter that trusts it (R = 1e-6), the estimate of BOTH
// position and velocity must reach the truth. Velocity is the one a wrong filter gets wrong:
// the sensor never measures it, so it has to be inferred.
TEST(KalmanEstimator, NoiseFreeRunConvergesToTruthInPositionAndVelocity) {
    RecordProperty("requirements", "EST-007");
    EstimatorConfig cfg;
    cfg.r_m2 = 1e-6;
    KalmanEstimator e(cfg);

    const DynamicsConfig dyn = make_cfg(0.0, 10.0, 0.0, 0.1, 100);
    TrueState truth = initial_state(dyn);
    Estimate est{};
    int readings = 0;
    for (std::int64_t k = 0; readings < 10; ++k) {
        if (k > 0) {
            truth = propagate(truth, dyn, k);
        }
        const bool due = (k % 5 == 0);
        if (!e.initialized()) {
            est = e.initialize(reading(truth.t_s, truth.position_m));
            ++readings;
        } else {
            est = e.predict(dyn.dt_s);
            if (due) {
                est = e.update(reading(truth.t_s, truth.position_m));
                ++readings;
            }
        }
    }
    EXPECT_LT(std::fabs(est.position_m - truth.position_m), 1e-3);
    EXPECT_LT(std::fabs(est.velocity_mps - truth.velocity_mps), 1e-3);
}
