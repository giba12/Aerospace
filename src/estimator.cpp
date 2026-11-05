#include "simulator/estimator.hpp"

#include <cmath>
#include <stdexcept>

namespace sim {

void EstimatorConfig::validate() const {
    if (!std::isfinite(r_m2) || r_m2 <= 0.0) {
        // R = 0 would make the gain divide by zero when the doubt is also zero.
        throw std::invalid_argument("r_m2: must be finite and > 0");
    }
    if (!std::isfinite(q_m2ps3) || q_m2ps3 < 0.0) {
        throw std::invalid_argument("q_m2ps3: must be finite and >= 0");
    }
    if (!std::isfinite(p0_pos_m2) || p0_pos_m2 < 0.0) {
        throw std::invalid_argument("p0_pos_m2: must be finite and >= 0");
    }
    if (!std::isfinite(p0_vel_m2ps2) || p0_vel_m2ps2 < 0.0) {
        throw std::invalid_argument("p0_vel_m2ps2: must be finite and >= 0");
    }
}

KalmanEstimator::KalmanEstimator(const EstimatorConfig& cfg) : cfg_(cfg) {
    cfg_.validate();
}

bool KalmanEstimator::initialized() const {
    return initialized_;
}

Estimate KalmanEstimator::estimate() const {
    return Estimate{t_s_, state_.x.v0, state_.x.v1, state_.P};
}

Estimate KalmanEstimator::initialize(const Measurement& first) {
    if (initialized_) {
        throw std::logic_error("estimator: initialize called twice");
    }
    if (!std::isfinite(first.t_s) || !std::isfinite(first.position_m)) {
        throw std::invalid_argument("measurement: position and time must be finite");
    }
    state_ = KalmanState{Vec2{first.position_m, 0.0}, Mat2{cfg_.p0_pos_m2, 0.0, 0.0, cfg_.p0_vel_m2ps2}};
    t_s_ = first.t_s;
    last_reading_t_s_ = first.t_s;
    initialized_ = true;
    return estimate();
}

Estimate KalmanEstimator::predict(double dt_s) {
    if (!initialized_) {
        throw std::logic_error("estimator: predict called before initialize");
    }
    if (!std::isfinite(dt_s) || dt_s <= 0.0) {
        throw std::invalid_argument("dt_s: must be finite and > 0");
    }
    state_ = kalman_predict(state_, dt_s, cfg_.q_m2ps3);  // assigned only after it succeeded
    t_s_ += dt_s;
    return estimate();
}

Estimate KalmanEstimator::update(const Measurement& z) {
    if (!initialized_) {
        throw std::logic_error("estimator: update called before initialize");
    }
    if (!std::isfinite(z.t_s) || !std::isfinite(z.position_m)) {
        throw std::invalid_argument("measurement: position and time must be finite");
    }
    if (z.t_s < last_reading_t_s_) {
        throw std::invalid_argument("measurement: timestamp is older than the last reading");
    }
    state_ = kalman_update(state_, z.position_m, cfg_.r_m2);
    t_s_ = z.t_s;
    last_reading_t_s_ = z.t_s;
    return estimate();
}

}  // namespace sim
