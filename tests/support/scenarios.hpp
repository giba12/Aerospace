#pragma once

#include <cstdint>

#include "simulator/config.hpp"
#include "simulator/dynamics.hpp"
#include "simulator/state.hpp"

namespace sim::testing {

inline DynamicsConfig make_cfg(double x0_m, double v0_mps, double accel_mps2, double dt_s,
                               std::int64_t steps) {
    return DynamicsConfig{dt_s, steps, x0_m, v0_mps, accel_mps2};
}

// t = k * dt, computed by multiplication as in SIM-002.
inline double time_s(const DynamicsConfig& cfg, std::int64_t k) {
    return static_cast<double>(k) * cfg.dt_s;
}

// Exact kinematics, the independent oracle for SIM-003 (a = 0) and SIM-004 (a != 0). This is the
// true physics, NOT what Euler computes; they differ by euler_error_m().
inline double analytic_position_m(const DynamicsConfig& cfg, std::int64_t k) {
    const double t = time_s(cfg, k);
    return cfg.x0_m + cfg.v0_mps * t + 0.5 * cfg.accel_mps2 * t * t;
}

inline double analytic_velocity_mps(const DynamicsConfig& cfg, std::int64_t k) {
    return cfg.v0_mps + cfg.accel_mps2 * time_s(cfg, k);
}

// SIM-004: exact position minus Euler position = a * t * dt / 2 (signed; its magnitude is the
// documented bound 0.5*|a|*t*dt).
inline double euler_error_m(const DynamicsConfig& cfg, std::int64_t k) {
    return 0.5 * cfg.accel_mps2 * time_s(cfg, k) * cfg.dt_s;
}

// Runs the truth model for cfg.steps steps, calling visit(state, k) after each one, and returns
// the final state. Reusable by any test that needs a trajectory (sensor, estimator).
template <typename Visit>
TrueState walk_truth(const DynamicsConfig& cfg, Visit visit) {
    TrueState s = initial_state(cfg);
    for (std::int64_t k = 1; k <= cfg.steps; ++k) {
        s = propagate(s, cfg, k);
        visit(s, k);
    }
    return s;
}

inline TrueState walk_truth(const DynamicsConfig& cfg) {
    return walk_truth(cfg, [](const TrueState&, std::int64_t) {});
}

}  // namespace sim::testing
