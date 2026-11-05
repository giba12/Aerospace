#include <gtest/gtest.h>

#include <cmath>
#include <string>
#include <vector>

#include "simulator/sensor.hpp"

using namespace sim;

namespace {

SensorConfig make_cfg(double sigma, std::int64_t every = 1, std::uint64_t seed = 42) {
    SensorConfig c;
    c.sigma_m = sigma;
    c.every_n_steps = every;
    c.seed = seed;
    return c;
}

// Readings of a stationary object at position 0, so each reading IS the noise, exactly.
std::vector<double> noise_series(const SensorConfig& c, int n) {
    NoisySensor sensor(c);
    const TrueState truth{0.0, 0.0, 0.0};
    std::vector<double> out;
    for (int k = 0; k < n; ++k) {
        out.push_back(sensor.observe(truth, k)->position_m);
    }
    return out;
}

void expect_rejected(const char* parameter, const SensorConfig& c) {
    try {
        c.validate();
        ADD_FAILURE() << "accepted a bad " << parameter;
    } catch (const std::invalid_argument& e) {
        EXPECT_NE(std::string(e.what()).find(parameter), std::string::npos) << e.what();
    }
    EXPECT_THROW(NoisySensor{c}, std::invalid_argument);
}

}  // namespace

TEST(NoisySensor, ReadsOnEveryMthStepStartingAtZero) {
    RecordProperty("requirements", "SEN-002");
    NoisySensor sensor(make_cfg(0.0, 5));
    std::vector<int> steps_with_reading;
    for (int k = 0; k <= 100; ++k) {
        if (sensor.observe(TrueState{0.1 * k, 0.0, 0.0}, k)) {
            steps_with_reading.push_back(k);
        }
    }
    ASSERT_EQ(steps_with_reading.size(), 21u);
    for (std::size_t i = 0; i < 21; ++i) {
        EXPECT_EQ(steps_with_reading[i], static_cast<int>(5 * i));
    }
}

TEST(NoisySensor, ZeroSigmaReturnsTheExactPosition) {
    RecordProperty("requirements", "SEN-003");
    NoisySensor sensor(make_cfg(0.0));
    int k = 0;
    for (const double x : {0.0, -3.5, 0.1 + 0.2, 1e12, 123456.789}) {
        EXPECT_EQ(sensor.observe(TrueState{0.0, x, 0.0}, k++)->position_m, x);  // exact, not near
    }
}

// SEN-003: sigma = 5, 10000 samples, fixed seed: mean within +/-0.25 m (5 standard errors) and
// standard deviation within +/-5% of sigma.
TEST(NoisySensor, NoiseHasTheRequestedMeanAndSpread) {
    RecordProperty("requirements", "SEN-003");
    const std::vector<double> noise = noise_series(make_cfg(5.0), 10000);
    double sum = 0.0;
    for (const double z : noise) {
        sum += z;
    }
    const double mean = sum / static_cast<double>(noise.size());
    double squares = 0.0;
    for (const double z : noise) {
        squares += (z - mean) * (z - mean);
    }
    const double stddev = std::sqrt(squares / static_cast<double>(noise.size() - 1));
    EXPECT_NEAR(mean, 0.0, 0.25);
    EXPECT_NEAR(stddev, 5.0, 0.05 * 5.0);
}

TEST(NoisySensor, SameSeedSameReadingsAndSigmaOnlyScalesThem) {
    RecordProperty("requirements", "SEN-004,SEN-003");
    const std::vector<double> a = noise_series(make_cfg(5.0, 1, 42), 200);
    EXPECT_EQ(a, noise_series(make_cfg(5.0, 1, 42), 200));  // identical, element for element
    EXPECT_NE(a, noise_series(make_cfg(5.0, 1, 43), 200));  // another seed, another sequence
    const std::vector<double> doubled = noise_series(make_cfg(10.0, 1, 42), 200);
    for (std::size_t i = 0; i < a.size(); ++i) {
        EXPECT_EQ(doubled[i], 2.0 * a[i]);  // same draws, scaled: sigma never reshuffles them
    }
}

TEST(NoisySensor, ReadingCarriesTruthTimeAndSensorId) {
    RecordProperty("requirements", "SEN-005");
    SensorConfig c = make_cfg(1.0);
    c.sensor_id = "imu7";
    NoisySensor sensor(c);
    const auto m = sensor.observe(TrueState{1.25, 9.0, 3.0}, 0);
    ASSERT_TRUE(m.has_value());
    EXPECT_EQ(m->t_s, 1.25);
    EXPECT_EQ(m->sensor_id, "imu7");
}

TEST(NoisySensor, ObservingDoesNotChangeTheTruth) {
    RecordProperty("requirements", "SEN-006");
    NoisySensor sensor(make_cfg(5.0));
    const TrueState truth{2.0, 7.0, -1.5};  // const: observe() cannot modify it, or this won't compile
    for (int k = 0; k < 50; ++k) {
        sensor.observe(truth, k);
    }
    EXPECT_EQ(truth.t_s, 2.0);
    EXPECT_EQ(truth.position_m, 7.0);
    EXPECT_EQ(truth.velocity_mps, -1.5);
}

TEST(NoisySensor, RejectsBadSettingsNamingTheParameter) {
    RecordProperty("requirements", "SEN-007");
    expect_rejected("sigma_m", make_cfg(-0.1));
    expect_rejected("sigma_m", make_cfg(std::nan("")));
    expect_rejected("sigma_m", make_cfg(INFINITY));
    expect_rejected("every_n_steps", make_cfg(1.0, 0));
    expect_rejected("every_n_steps", make_cfg(1.0, -5));
    SensorConfig bad_id = make_cfg(1.0);
    bad_id.sensor_id = "a,b";
    expect_rejected("sensor_id", bad_id);
    bad_id.sensor_id = "";
    expect_rejected("sensor_id", bad_id);
}
