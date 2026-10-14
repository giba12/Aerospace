#include "simulator/dynamics.hpp"

#include <cmath>
#include <stdexcept>

namespace sim {

void DynamicsConfig::validate() const {
    if (!std::isfinite(dt_s) || dt_s <= 0.0) {
        throw std::invalid_argument("dt_s: must be finite and > 0");
    }
    if (steps < 0) {
        throw std::invalid_argument("steps: must be >= 0");
    }
    if (!std::isfinite(x0_m)) {
        throw std::invalid_argument("x0_m: must be finite");
    }
    if (!std::isfinite(v0_mps)) {
        throw std::invalid_argument("v0_mps: must be finite");
    }
}

TrueState initial_state(const DynamicsConfig& cfg) {
    return TrueState{0.0, cfg.x0_m, cfg.v0_mps};
}

TrueState propagate(const TrueState& prev, const DynamicsConfig& cfg, std::int64_t k) {
    // Explicit Euler. With no acceleration the velocity never changes, so this is exact.
    return TrueState{static_cast<double>(k) * cfg.dt_s,
                     prev.position_m + prev.velocity_mps * cfg.dt_s,
                     prev.velocity_mps};
}

}  // namespace sim
