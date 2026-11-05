#include "simulator/kalman.hpp"

namespace sim {

KalmanState kalman_predict(const KalmanState& s, double dt_s, double q_m2ps3) {
    const Mat2 F{1.0, dt_s, 0.0, 1.0};
    const double dt2 = dt_s * dt_s;
    const double dt3 = dt2 * dt_s;
    const Mat2 Q = q_m2ps3 * Mat2{dt3 / 3.0, dt2 / 2.0, dt2 / 2.0, dt_s};
    return KalmanState{F * s.x, F * s.P * transpose(F) + Q};
}

KalmanState kalman_update(const KalmanState& s, double z_m, double r_m2) {
    const Vec2 H{1.0, 0.0};                     // the sensor reads position only
    const double innovation = z_m - s.x.v0;     // y: how far off the prediction was
    const double S = s.P.m00 + r_m2;            // how much the innovation is expected to vary
    const Vec2 K{s.P.m00 / S, s.P.m10 / S};     // gain: how far to move each of position, velocity
    const Mat2 IKH = identity() - outer(K, H);
    return KalmanState{s.x + innovation * K,
                       IKH * s.P * transpose(IKH) + r_m2 * outer(K, K)};
}

}  // namespace sim
