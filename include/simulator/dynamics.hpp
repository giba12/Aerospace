#pragma once

#include <cstdint>

#include "simulator/config.hpp"
#include "simulator/state.hpp"

namespace sim {

// The state at step 0 (t = 0).
TrueState initial_state(const DynamicsConfig& cfg);

// IF-03: a pure function. `k` is the index of the NEW state and t = k * dt, computed by
// multiplication rather than accumulated, so rounding error does not grow (SIM-002).
// Explicit Euler with constant acceleration (SIM-004): the position step uses the PREVIOUS
// velocity, then the velocity is updated. After n steps this differs from the exact
// x0 + v0*t + a*t^2/2 by exactly a*t*dt/2 (t = n*dt), so the error bound is known and
// grows linearly in t and dt. With a = 0 the result is exact (SIM-003).
TrueState propagate(const TrueState& prev, const DynamicsConfig& cfg, std::int64_t k);

}  // namespace sim
