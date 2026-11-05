#include <gtest/gtest.h>

#include <cmath>
#include <limits>
#include <stdexcept>
#include <string>

#include "simulator/estimator.hpp"

using namespace sim;

// ---- EstimatorConfig (EST-010) ----

namespace {

void expect_rejected(const char* parameter, const EstimatorConfig& c) {
    try {
        c.validate();
        ADD_FAILURE() << "accepted a bad " << parameter;
    } catch (const std::invalid_argument& e) {
        EXPECT_NE(std::string(e.what()).find(parameter), std::string::npos) << e.what();
    }
}

}  // namespace

TEST(EstimatorConfig, ReferenceScenarioDefaultsAreValid) {
    RecordProperty("requirements", "EST-010");
    const EstimatorConfig c;
    EXPECT_NO_THROW(c.validate());
    EXPECT_DOUBLE_EQ(c.q_m2ps3, 0.1);
    EXPECT_DOUBLE_EQ(c.r_m2, 25.0);
    EXPECT_DOUBLE_EQ(c.p0_pos_m2, 25.0);
    EXPECT_DOUBLE_EQ(c.p0_vel_m2ps2, 100.0);
}

TEST(EstimatorConfig, RejectsNonPositiveOrNonFiniteR) {
    RecordProperty("requirements", "EST-010");
    const double nan = std::nan("");
    const double inf = std::numeric_limits<double>::infinity();
    for (const double bad : {0.0, -1.0, nan, inf}) {
        EstimatorConfig c;
        c.r_m2 = bad;
        expect_rejected("r_m2", c);
    }
}

TEST(EstimatorConfig, RejectsNegativeOrNonFiniteQAndStartingDoubt) {
    RecordProperty("requirements", "EST-010");
    const double nan = std::nan("");
    const double inf = std::numeric_limits<double>::infinity();
    for (const double bad : {-1e-12, nan, inf}) {
        EstimatorConfig q;
        q.q_m2ps3 = bad;
        expect_rejected("q_m2ps3", q);
        EstimatorConfig p0;
        p0.p0_pos_m2 = bad;
        expect_rejected("p0_pos_m2", p0);
        EstimatorConfig v0;
        v0.p0_vel_m2ps2 = bad;
        expect_rejected("p0_vel_m2ps2", v0);
    }
}

TEST(EstimatorConfig, ZeroIsAllowedForQAndStartingDoubt) {
    RecordProperty("requirements", "EST-010");
    // q = 0 means "no unmodelled jiggle" and P0 = 0 means "certain start"; both are legal.
    // Only R must be strictly positive.
    EstimatorConfig c;
    c.q_m2ps3 = 0.0;
    c.p0_pos_m2 = 0.0;
    c.p0_vel_m2ps2 = 0.0;
    EXPECT_NO_THROW(c.validate());
}
