#pragma once

#include "simulator/state.hpp"

namespace sim {

// IF-05. No method accepts a TrueState, so the estimator cannot see the truth (EST-002).
// The states are Uninitialized -> Tracking (DD-003). Calling predict/update while
// Uninitialized throws std::logic_error and changes nothing.
class IEstimator {
public:
    virtual ~IEstimator() = default;
    virtual bool initialized() const = 0;
    virtual Estimate initialize(const Measurement& first) = 0;  // EST-009: no predict step
    virtual Estimate predict(double dt_s) = 0;
    virtual Estimate update(const Measurement& z) = 0;
};

// M0 stand-in: the estimate IS the latest measurement, with velocity 0 and P = 0. It has
// no model, so it is not a filter. Replaced by the Kalman filter in M3.
class PassthroughEstimator final : public IEstimator {
public:
    bool initialized() const override;
    Estimate initialize(const Measurement& first) override;
    Estimate predict(double dt_s) override;
    Estimate update(const Measurement& z) override;

private:
    bool initialized_{false};
    Estimate est_{0.0, 0.0, 0.0, Mat2{}};
};

}  // namespace sim
