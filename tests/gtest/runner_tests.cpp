#include <gtest/gtest.h>

#include <algorithm>

#include "fakes.hpp"
#include "simulator/runner.hpp"

using namespace sim;
using sim::testing::CallLog;
using sim::testing::RecordingEstimator;
using sim::testing::RecordingRecorder;
using sim::testing::ScriptedSensor;

namespace {
DynamicsConfig steps(std::int64_t n) {
    DynamicsConfig cfg;
    cfg.steps = n;
    return cfg;
}
}  // namespace

// RUN-001: the order of calls IS the specification, so the test compares the whole log.
TEST(Runner, CallOrderMatchesSpecification) {
    RecordProperty("requirements", "RUN-001,EST-009");
    CallLog log;
    ScriptedSensor sensor(log, {1, 3});  // first reading arrives at step 1, not step 0
    RecordingEstimator estimator(log);
    RecordingRecorder recorder(log);

    run(steps(3), sensor, estimator, recorder);

    const CallLog expected = {
        "observe(0)", "write_row(0)",                                    // no reading, uninitialized
        "observe(1)", "initialize", "write_row(1)",                      // initialize, NO predict
        "observe(2)", "predict", "write_row(2)",                         // predict only
        "observe(3)", "predict", "update", "write_row(3)",               // predict then update
        "commit"};
    EXPECT_EQ(log, expected);
    EXPECT_EQ(recorder.rows_with_estimate, 3);  // step 0 has none (EST-009)
}

TEST(Runner, NSTepsProduceNPlusOneRows) {
    RecordProperty("requirements", "SIM-005");
    CallLog log;
    ScriptedSensor sensor(log, {});
    RecordingEstimator estimator(log);
    RecordingRecorder recorder(log);

    run(steps(10), sensor, estimator, recorder);

    EXPECT_EQ(recorder.rows, 11);
}

TEST(Runner, InvalidConfigTouchesNothing) {
    RecordProperty("requirements", "SIM-006");
    CallLog log;
    ScriptedSensor sensor(log, {});
    RecordingEstimator estimator(log);
    RecordingRecorder recorder(log);
    DynamicsConfig bad;
    bad.dt_s = -1.0;

    EXPECT_THROW(run(bad, sensor, estimator, recorder), std::invalid_argument);
    EXPECT_TRUE(log.empty());
}
