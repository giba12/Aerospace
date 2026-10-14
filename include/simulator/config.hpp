#pragma once

#include <cstdint>
#include <string>

namespace sim {

// Settings for the truth model. M0 carries only what the skeleton uses.
// M1 adds accel_mps2 (SIM-004).
struct DynamicsConfig {
    double dt_s{0.1};
    std::int64_t steps{1000};
    double x0_m{0.0};
    double v0_mps{10.0};

    // Throws std::invalid_argument naming the offending parameter (SIM-006, DD-007).
    void validate() const;
};

// Settings for the sensor. M2 adds sigma_m and seed (SEN-003, SEN-004).
struct SensorConfig {
    std::int64_t every_n_steps{5};
    std::string sensor_id{"pos0"};

    // Throws std::invalid_argument naming the offending parameter (SEN-007).
    void validate() const;
};

// Everything one run of `sim` needs.
struct RunConfig {
    DynamicsConfig dynamics;
    SensorConfig sensor;
    std::string out_path{"run.csv"};
};

}  // namespace sim
