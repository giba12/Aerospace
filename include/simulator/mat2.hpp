#pragma once

namespace sim {

// 2x2 matrix value type (DD-004: hand-written, no linear-algebra dependency).
// M0 only needs it as a container for the covariance P. Arithmetic arrives with the
// Kalman filter in M3.
struct Mat2 {
    double m00{0.0}, m01{0.0};
    double m10{0.0}, m11{0.0};
};

}  // namespace sim
