#include <gtest/gtest.h>

#include <cmath>

#include "scenarios.hpp"
#include "simulator/dynamics.hpp"
#include "tolerances.hpp"

using namespace sim;

TEST(Dynamics, ConstantVelocityMatchesAnalyticSolution) {
    RecordProperty("requirements", "SIM-003,SIM-002");
    DynamicsConfig cfg;  // dt 0.1, v0 10
    cfg.steps = 1000;
    TrueState s = initial_state(cfg);
    for (std::int64_t k = 1; k <= cfg.steps; ++k) {
        s = propagate(s, cfg, k);
    }
    EXPECT_NEAR(s.position_m, sim::testing::analytic_position_m(cfg, cfg.steps),
                sim::testing::kPositionTol_m);
    EXPECT_NEAR(s.t_s, 100.0, sim::testing::kTimeTol_s);  // k * dt, not accumulated
}

// VV-SIM-01 (baseline 6.6): x0 = 0, v0 = 10, a = 1, dt = 0.1, 1000 steps. Euler gives
// x = 5995.0 and v = 110.0; the exact kinematic answer is 6000.0; the gap is a*t*dt/2 = 5.0.
TEST(Dynamics, EulerWithAccelerationMatchesVvSim01) {
    RecordProperty("requirements", "SIM-004,SIM-002");
    DynamicsConfig cfg;
    cfg.x0_m = 0.0;
    cfg.v0_mps = 10.0;
    cfg.accel_mps2 = 1.0;
    cfg.dt_s = 0.1;
    cfg.steps = 1000;
    TrueState s = initial_state(cfg);
    for (std::int64_t k = 1; k <= cfg.steps; ++k) {
        s = propagate(s, cfg, k);
    }
    EXPECT_NEAR(s.position_m, 5995.0, sim::testing::kPositionTol_m);  // the hand-derived Euler value
    EXPECT_NEAR(s.velocity_mps, 110.0, sim::testing::kPositionTol_m);
    EXPECT_NEAR(s.t_s, 100.0, sim::testing::kTimeTol_s);

    const double exact = sim::testing::analytic_position_m(cfg, cfg.steps);
    EXPECT_NEAR(exact, 6000.0, sim::testing::kPositionTol_m);
    // The documented error bound is attained exactly, and it is the whole difference.
    EXPECT_NEAR(exact - s.position_m, 5.0, sim::testing::kPositionTol_m);
    EXPECT_NEAR(exact - s.position_m, sim::testing::euler_error_bound_m(cfg, cfg.steps),
                sim::testing::kPositionTol_m);
    EXPECT_NEAR(s.velocity_mps, sim::testing::analytic_velocity_mps(cfg, cfg.steps),
                sim::testing::kPositionTol_m);  // velocity has no Euler error for constant a
}

TEST(Dynamics, EulerErrorBoundHoldsAtEveryStep) {
    RecordProperty("requirements", "SIM-004");
    DynamicsConfig cfg;
    cfg.v0_mps = -3.0;       // negative velocity and negative acceleration as well
    cfg.accel_mps2 = -0.25;
    cfg.dt_s = 0.05;
    TrueState s = initial_state(cfg);
    for (std::int64_t k = 1; k <= 400; ++k) {
        s = propagate(s, cfg, k);
        EXPECT_NEAR(sim::testing::analytic_position_m(cfg, k) - s.position_m,
                    sim::testing::euler_error_bound_m(cfg, k), sim::testing::kPositionTol_m)
            << "step " << k;
    }
}

TEST(Dynamics, ZeroAccelerationLeavesVelocityUnchanged) {
    RecordProperty("requirements", "SIM-003,SIM-004");
    DynamicsConfig cfg;  // accel_mps2 defaults to 0
    EXPECT_EQ(cfg.accel_mps2, 0.0);
    const TrueState s1 = propagate(initial_state(cfg), cfg, 1);
    EXPECT_EQ(s1.velocity_mps, cfg.v0_mps);  // exactly, not approximately
}

TEST(Dynamics, RejectsNonFiniteAcceleration) {
    RecordProperty("requirements", "SIM-006");
    DynamicsConfig cfg;
    cfg.accel_mps2 = std::nan("");
    EXPECT_THROW(cfg.validate(), std::invalid_argument);
    cfg.accel_mps2 = INFINITY;
    EXPECT_THROW(cfg.validate(), std::invalid_argument);
    cfg.accel_mps2 = -9.81;  // any finite value, including negative, is accepted
    EXPECT_NO_THROW(cfg.validate());
}

TEST(Dynamics, StepsAreBoundedAboveAndBelow) {
    RecordProperty("requirements", "SIM-006");
    DynamicsConfig cfg;
    cfg.steps = kMaxSteps;
    EXPECT_NO_THROW(cfg.validate());
    cfg.steps = kMaxSteps + 1;
    EXPECT_THROW(cfg.validate(), std::invalid_argument);
    cfg.steps = -1;
    EXPECT_THROW(cfg.validate(), std::invalid_argument);
}

TEST(Dynamics, RejectsNonFiniteOrNonPositiveDt) {
    RecordProperty("requirements", "SIM-006");
    DynamicsConfig cfg;
    cfg.dt_s = 0.0;
    EXPECT_THROW(cfg.validate(), std::invalid_argument);
    cfg.dt_s = std::nan("");
    EXPECT_THROW(cfg.validate(), std::invalid_argument);
}
