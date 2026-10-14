#pragma once

// Tolerances from baseline 6.3. One definition, so no test invents its own.
namespace sim::testing {

inline constexpr double kPositionTol_m = 1e-9;
inline constexpr double kTimeTol_s = 1e-9;

}  // namespace sim::testing
