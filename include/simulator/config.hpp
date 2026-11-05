#pragma once

#include <cstdint>
#include <string>

namespace sim {

// Upper bound on `steps`. This is an educational tool: the default run is 1000 steps. A row is
// about 45 bytes today and may reach roughly 200 bytes once noisy 17-digit values are
// recorded, so 100000 steps is a file of 5 to 20 MB that analyze.py can still hold in memory. The bound stops a typo such as --steps 1000000000000 from running
// for hours and filling the disk. Raise it here if a larger study is ever needed (SIM-006).
inline constexpr std::int64_t kMaxSteps = 100000;

// Settings for the truth model.
struct DynamicsConfig {
    double dt_s{0.1};
    std::int64_t steps{1000};
    double x0_m{0.0};
    double v0_mps{10.0};
    double accel_mps2{0.0};  // constant acceleration; 0 means constant velocity (SIM-004)

    // Throws std::invalid_argument naming the offending parameter (SIM-006, DD-007).
    void validate() const;
};

// Settings for the sensor.
struct SensorConfig {
    double sigma_m{5.0};  // standard deviation of the position noise; 0 means exact (SEN-003)
    std::int64_t every_n_steps{5};
    std::uint64_t seed{42};  // same seed and settings give the same readings (SEN-004)
    std::string sensor_id{"pos0"};

    // Throws std::invalid_argument naming the offending parameter (SEN-007).
    void validate() const;
};

// Settings for the estimator: the filter's own beliefs, deliberately separate from the sensor's
// true noise (CFG-003). `r_m2` is what the filter ASSUMES the sensor variance is; no default is
// ever derived from `SensorConfig::sigma_m`, so a mismatch can be tested on purpose.
// Defaults are the reference scenario (baseline 8.3).
struct EstimatorConfig {
    double q_m2ps3{0.1};          // process noise intensity: how much unmodelled jiggle to allow
    double r_m2{25.0};            // assumed variance of one position reading
    double p0_pos_m2{25.0};       // starting doubt about position
    double p0_vel_m2ps2{100.0};   // starting doubt about velocity

    // Throws std::invalid_argument naming the offending parameter (EST-010). The starting
    // covariance is diagonal, so it is symmetric by construction and its determinant is the
    // product of two non-negative numbers; checking each is enough.
    void validate() const;
};

// Everything one run of `sim` needs.
struct RunConfig {
    DynamicsConfig dynamics;
    SensorConfig sensor;
    EstimatorConfig estimator;
    std::string out_path{"run.csv"};
};

}  // namespace sim
