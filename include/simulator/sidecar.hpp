#pragma once

#include <string>

#include "simulator/config.hpp"

namespace sim {

// IF-08 / OUT-003: where the settings of a run are recorded, next to the CSV.
std::string sidecar_path(const std::string& out_path);  // `<out>.config.json`

// The flat JSON object of baseline 8.5, schema_version 1: every effective setting, the seed,
// and build info. The estimator keys are `null` until the Kalman filter (M3) gives the stand-in
// estimator parameters to record. `source_revision` is `null` if git was unavailable when the
// project was configured. Throws std::runtime_error if a number is not finite.
std::string sidecar_json(const RunConfig& cfg);

}  // namespace sim
