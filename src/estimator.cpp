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

bool PassthroughEstimator::initialized() const {
    return initialized_;
}

Estimate PassthroughEstimator::initialize(const Measurement& first) {
    est_ = Estimate{first.t_s, first.position_m, 0.0, Mat2{}};
    initialized_ = true;
    return est_;
}

Estimate PassthroughEstimator::predict(double dt_s) {
    if (!initialized_) {
        throw std::logic_error("estimator: predict called before initialize");
    }
    est_.t_s += dt_s;  // no motion model: the position is held, only the clock moves
    return est_;
}

Estimate PassthroughEstimator::update(const Measurement& z) {
    if (!initialized_) {
        throw std::logic_error("estimator: update called before initialize");
    }
    est_.t_s = z.t_s;
    est_.position_m = z.position_m;
    return est_;
}

}  // namespace sim
