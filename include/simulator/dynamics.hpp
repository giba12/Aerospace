#pragma once

#include <cstdint>

#include "simulator/config.hpp"
#include "simulator/state.hpp"

namespace sim {

// The state at step 0 (t = 0).
TrueState initial_state(const DynamicsConfig& cfg);

// IF-03: a pure function. `k` is the index of the NEW state and t = k * dt, computed by
// multiplication rather than accumulated, so rounding error does not grow (SIM-002).
// M0 stub: constant velocity only. M1 adds acceleration (SIM-004).
TrueState propagate(const TrueState& prev, const DynamicsConfig& cfg, std::int64_t k);

}  // namespace sim
