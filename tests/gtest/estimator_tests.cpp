#include <gtest/gtest.h>

#include <stdexcept>

#include "simulator/estimator.hpp"

using namespace sim;

TEST(PassthroughEstimator, PredictBeforeInitializeIsRejected) {
    RecordProperty("requirements", "EST-009");
    PassthroughEstimator e;
    EXPECT_FALSE(e.initialized());
    EXPECT_THROW(e.predict(0.1), std::logic_error);
    EXPECT_FALSE(e.initialized());  // the rejected call changed nothing
}
