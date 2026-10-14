#pragma once

#include <string>

#include "simulator/mat2.hpp"

// Data dictionary (baseline 7.7). SI units, with the unit in every field name (NFR-005).
namespace sim {

// What is really true. Owned by the runner and NEVER given to the estimator (SYS-002).
struct TrueState {
    double t_s;
    double position_m;
    double velocity_mps;
};

// What a sensor reports. Position only (SEN-001): no velocity field exists.
struct Measurement {
    double t_s;
    double position_m;
    std::string sensor_id;
};

// What the estimator believes. P is the covariance of [position, velocity].
struct Estimate {
    double t_s;
    double position_m;
    double velocity_mps;
    Mat2 P;
};

}  // namespace sim
