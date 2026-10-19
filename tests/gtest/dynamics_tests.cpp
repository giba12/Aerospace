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
