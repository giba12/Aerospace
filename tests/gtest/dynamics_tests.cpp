#include <gtest/gtest.h>

#include <cmath>

#include "scenarios.hpp"
#include "tolerances.hpp"

using namespace sim;
using namespace sim::testing;

TEST(Dynamics, ConstantVelocityMatchesAnalyticSolution) {
    RecordProperty("requirements", "SIM-003,SIM-002");
    const DynamicsConfig cfg = make_cfg(0.0, 10.0, 0.0, 0.1, 1000);
    const TrueState s = walk_truth(cfg);
    EXPECT_NEAR(s.position_m, analytic_position_m(cfg, cfg.steps), kPositionTol_m);
    EXPECT_NEAR(s.t_s, 100.0, kTimeTol_s);  // k * dt, not accumulated
}

// VV-SIM-01 (baseline 6.6, tolerance 1e-9): Euler gives 5995.0 m and 110.0 m/s where the exact
// kinematic answer is 6000.0 m; the gap is a*t*dt/2 = 5.0.
TEST(Dynamics, EulerWithAccelerationMatchesVvSim01) {
    RecordProperty("requirements", "SIM-004,SIM-002");
    const DynamicsConfig cfg = make_cfg(0.0, 10.0, 1.0, 0.1, 1000);
    const TrueState s = walk_truth(cfg);
    EXPECT_NEAR(s.position_m, 5995.0, kPositionTol_m);
    EXPECT_NEAR(s.velocity_mps, 110.0, kPositionTol_m);
    EXPECT_NEAR(s.t_s, 100.0, kTimeTol_s);
    EXPECT_NEAR(analytic_position_m(cfg, cfg.steps), 6000.0, kPositionTol_m);
    EXPECT_NEAR(analytic_position_m(cfg, cfg.steps) - s.position_m, 5.0, kPositionTol_m);
}

// SIM-004 / SIM-003 over a sweep, checked at EVERY step: (exact - Euler) equals the documented
// signed bound a*t*dt/2 within the CR-24 rounding allowance, and velocity matches v0 + a*t.
// Equality is stricter than the requirement's "does not exceed" and also catches the
// semi-implicit variant, whose error has the same size but the opposite sign. The sweep includes
// the longest run the CLI accepts (kMaxSteps). One failure message per case, not per step.
TEST(Dynamics, EulerErrorIsTheDocumentedBoundWithinRoundingAllowance) {
    RecordProperty("requirements", "SIM-004,SIM-003");
    for (const double x0 : {0.0, 1e6}) {
        for (const double a : {-9.81, 0.0, 0.1, 1.0, 25.0}) {
            for (const double dt : {0.001, 0.1, 1.0}) {
                for (const double v0 : {10.0, -300.0}) {
                    for (const std::int64_t steps : {std::int64_t{1000}, kMaxSteps}) {
                        const DynamicsConfig cfg = make_cfg(x0, v0, a, dt, steps);
                        double worst = 0.0;  // largest error as a fraction of its allowance
                        walk_truth(cfg, [&](const TrueState& s, std::int64_t k) {
                            const double pos_err = analytic_position_m(cfg, k) - s.position_m;
                            worst = std::max(worst, std::abs(pos_err - euler_error_m(cfg, k)) /
                                                        position_tol_m(cfg, k));
                            worst = std::max(worst, std::abs(s.velocity_mps -
                                                             analytic_velocity_mps(cfg, k)) /
                                                        position_tol_m(cfg, k));
                        });
                        EXPECT_LE(worst, 1.0) << "x0=" << x0 << " a=" << a << " dt=" << dt
                                              << " v0=" << v0 << " steps=" << steps;
                    }
                }
            }
        }
    }
}

TEST(Dynamics, ZeroAccelerationLeavesVelocityUnchanged) {
    RecordProperty("requirements", "SIM-003,SIM-004");
    const DynamicsConfig cfg;  // accel_mps2 defaults to 0
    EXPECT_EQ(cfg.accel_mps2, 0.0);
    EXPECT_EQ(propagate(initial_state(cfg), cfg, 1).velocity_mps, cfg.v0_mps);  // exactly
}

namespace {
template <typename Mutate>
void expect_rejected(Mutate mutate) {
    DynamicsConfig cfg;
    mutate(cfg);
    EXPECT_THROW(cfg.validate(), std::invalid_argument);
}
}  // namespace

// SIM-006: dt finite and > 0, 0 <= steps <= kMaxSteps, and x0, v0, accel finite.
TEST(Dynamics, ValidateRejectsEachBadSetting) {
    RecordProperty("requirements", "SIM-006");
    const double nan = std::nan("");
    const double inf = INFINITY;
    expect_rejected([&](DynamicsConfig& c) { c.dt_s = 0.0; });
    expect_rejected([&](DynamicsConfig& c) { c.dt_s = -0.1; });
    expect_rejected([&](DynamicsConfig& c) { c.dt_s = nan; });
    expect_rejected([&](DynamicsConfig& c) { c.dt_s = inf; });
    expect_rejected([&](DynamicsConfig& c) { c.steps = -1; });
    expect_rejected([&](DynamicsConfig& c) { c.steps = kMaxSteps + 1; });
    expect_rejected([&](DynamicsConfig& c) { c.x0_m = nan; });
    expect_rejected([&](DynamicsConfig& c) { c.v0_mps = inf; });
    expect_rejected([&](DynamicsConfig& c) { c.accel_mps2 = nan; });
    expect_rejected([&](DynamicsConfig& c) { c.accel_mps2 = -inf; });
}

TEST(Dynamics, ValidateAcceptsBoundaryAndNegativeSettings) {
    RecordProperty("requirements", "SIM-006");
    EXPECT_NO_THROW(make_cfg(-5.0, -3.0, -9.81, 0.1, 0).validate());       // steps = 0
    EXPECT_NO_THROW(make_cfg(0.0, 0.0, 0.0, 1e-3, kMaxSteps).validate());  // steps at the cap
}
