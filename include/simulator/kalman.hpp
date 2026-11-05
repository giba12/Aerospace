#pragma once

#include "simulator/mat2.hpp"

namespace sim {

// The filter's belief: a best guess x = [position_m, velocity_mps] and the doubt about it,
// P (the covariance): P.m00 is the position variance in m^2, P.m11 the velocity variance in
// m^2/s^2, and the off-diagonals say how the two doubts are linked.
struct KalmanState {
    Vec2 x;
    Mat2 P;
};

// The filter's two steps as pure functions of their inputs (baseline 7.5). Keeping the maths
// free of any stored state is what lets VV-EST-01 start from an exact hand-picked belief and
// lets the Python cross-check (DD-012) mirror the same two functions. They do no validation:
// KalmanEstimator checks its inputs before calling them.

// Move the guess forward by dt_s and let the doubt grow.
//   x <- F x                     F = [[1, dt], [0, 1]]   (position += velocity * dt)
//   P <- F P F^T + Q             Q = q * [[dt^3/3, dt^2/2], [dt^2/2, dt]]
// q_m2ps3 is the process-noise intensity (m^2/s^3): the unmodelled jiggle the filter allows.
KalmanState kalman_predict(const KalmanState& s, double dt_s, double q_m2ps3);

// Pull the guess toward a position reading and shrink the doubt. The sensor sees position only,
// H = [1, 0].
//   S = H P H^T + R             K = P H^T / S             y = z - H x
//   x <- x + K y
//   P <- (I - K H) P (I - K H)^T + K R K^T                 (Joseph form, EST-011)
// r_m2 is the variance the filter ASSUMES the sensor has (CFG-003).
KalmanState kalman_update(const KalmanState& s, double z_m, double r_m2);

}  // namespace sim
