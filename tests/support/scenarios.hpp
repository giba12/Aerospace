#pragma once

#include <cstdint>

#include "simulator/config.hpp"
#include "simulator/state.hpp"

namespace sim::testing {

// Analytic truth for constant velocity: x(t) = x0 + v0 * t (the independent oracle for SIM-003).
inline double analytic_position_m(const DynamicsConfig& cfg, std::int64_t k) {
    return cfg.x0_m + cfg.v0_mps * (static_cast<double>(k) * cfg.dt_s);
}

}  // namespace sim::testing
