#include "simulator/estimator.hpp"

#include <stdexcept>

namespace sim {

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
