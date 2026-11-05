#pragma once

#include "simulator/config.hpp"
#include "simulator/kalman.hpp"
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

// The linear Kalman filter for position and velocity (EST-001), a state machine around the
// pure maths in kalman.hpp. Every method that throws leaves the estimator exactly as it was
// (strong guarantee, DD-007, EST-013).
//   - wrong state (predict/update before initialize, initialize twice): std::logic_error
//   - bad input (non-finite number, dt <= 0, a timestamp older than the last reading, bad
//     settings): std::invalid_argument
class KalmanEstimator final : public IEstimator {
public:
    explicit KalmanEstimator(const EstimatorConfig& cfg);  // validates (EST-010)

    bool initialized() const override;
    // x = [z, 0] and P = diag(p0_pos, p0_vel), with NO predict step (EST-009).
    Estimate initialize(const Measurement& first) override;
    Estimate predict(double dt_s) override;
    Estimate update(const Measurement& z) override;

private:
    Estimate estimate() const;

    EstimatorConfig cfg_;
    bool initialized_{false};
    double t_s_{0.0};              // time of the current estimate
    double last_reading_t_s_{0.0};  // time of the newest accepted reading (EST-013)
    KalmanState state_{};
};

}  // namespace sim
