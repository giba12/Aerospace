#pragma once

#include <cstdint>

#include "simulator/config.hpp"
#include "simulator/state.hpp"

namespace sim::testing {

// Exact kinematics: x(t) = x0 + v0*t + a*t^2/2 and v(t) = v0 + a*t, with t = k*dt. The
// independent oracle for SIM-003 (a = 0) and SIM-004 (a != 0). It is the true physics, NOT
// what Euler computes: they differ by euler_error_bound_m().
inline double analytic_position_m(const DynamicsConfig& cfg, std::int64_t k) {
    const double t = static_cast<double>(k) * cfg.dt_s;
    return cfg.x0_m + cfg.v0_mps * t + 0.5 * cfg.accel_mps2 * t * t;
}

inline double analytic_velocity_mps(const DynamicsConfig& cfg, std::int64_t k) {
    return cfg.v0_mps + cfg.accel_mps2 * (static_cast<double>(k) * cfg.dt_s);
}

// The documented SIM-004 bound: exact position minus Euler position = a * t * dt / 2.
inline double euler_error_bound_m(const DynamicsConfig& cfg, std::int64_t k) {
    return 0.5 * cfg.accel_mps2 * (static_cast<double>(k) * cfg.dt_s) * cfg.dt_s;
}

}  // namespace sim::testing
