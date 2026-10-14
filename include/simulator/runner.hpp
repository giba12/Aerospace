#pragma once

#include "simulator/config.hpp"
#include "simulator/estimator.hpp"
#include "simulator/recorder.hpp"
#include "simulator/sensor.hpp"

namespace sim {

// Owns the time loop and the call order (RUN-001, baseline 7.4). Components are passed in as
// interfaces so tests can substitute fakes (TST-007). Throws on invalid config before any
// component is touched. Calls recorder.commit() only after the last row.
void run(const DynamicsConfig& cfg, ISensor& sensor, IEstimator& estimator, IRecorder& recorder);

}  // namespace sim
