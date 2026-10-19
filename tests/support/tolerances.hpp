#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>

#include "scenarios.hpp"

// Tolerances from baseline 6.3. One definition, so no test invents its own.
namespace sim::testing {

inline constexpr double kPositionTol_m = 1e-9;  // the floor of the position tolerance
inline constexpr double kTimeTol_s = 1e-9;
inline constexpr double kUnitRoundoff = std::numeric_limits<double>::epsilon() / 2;  // 2^-53

// Position tolerance after k steps (CR-24, baseline 6.3): max(1e-9 m, 2 * k * u * X), where u is
// the unit roundoff and X = |x0| + |v0|*t + |a|*t^2/2 bounds |position| up to step k. The second
// term is the worst-case growth of floating-point rounding over k additions; it exceeds the
// 1e-9 floor only when k * X is above about 4.5e6, so small runs keep the plain 1e-9.
inline double position_tol_m(const DynamicsConfig& cfg, std::int64_t k) {
    const double t = time_s(cfg, k);
    const double x_max_m =
        std::abs(cfg.x0_m) + std::abs(cfg.v0_mps) * t + 0.5 * std::abs(cfg.accel_mps2) * t * t;
    return std::max(kPositionTol_m, 2.0 * static_cast<double>(k) * kUnitRoundoff * x_max_m);
}

}  // namespace sim::testing
