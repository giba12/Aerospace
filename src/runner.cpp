#include "simulator/runner.hpp"

#include <optional>

#include "simulator/dynamics.hpp"

namespace sim {

void run(const DynamicsConfig& cfg, ISensor& sensor, IEstimator& estimator, IRecorder& recorder) {
    cfg.validate();

    TrueState truth = initial_state(cfg);  // step 0, t = 0
    std::optional<Estimate> est;           // empty until the estimator is initialized (EST-009)

    for (std::int64_t k = 0; k <= cfg.steps; ++k) {
        if (k > 0) {
            truth = propagate(truth, cfg, k);
        }
        // The sensor decides whether a reading is due (DD-002). The estimator only ever
        // receives `meas`, never `truth` (SYS-002).
        const std::optional<Measurement> meas = sensor.observe(truth, k);

        if (!estimator.initialized()) {
            if (meas) {
                est = estimator.initialize(*meas);  // no predict on the first reading (EST-009)
            }
        } else {
            est = estimator.predict(cfg.dt_s);
            if (meas) {
                est = estimator.update(*meas);
            }
        }
        recorder.write_row(k, truth, meas, est);
    }
    recorder.commit();
}

}  // namespace sim
