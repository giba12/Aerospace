#include "simulator/sensor.hpp"

#include <cmath>
#include <stdexcept>

namespace sim {

void SensorConfig::validate() const {
    if (!std::isfinite(sigma_m) || sigma_m < 0.0) {
        throw std::invalid_argument("sigma_m: must be finite and >= 0");
    }
    if (every_n_steps < 1) {
        throw std::invalid_argument("every_n_steps: must be >= 1");
    }
    if (sensor_id.empty() || sensor_id.find(',') != std::string::npos) {
        throw std::invalid_argument("sensor_id: must be non-empty and contain no commas");
    }
}

NoisySensor::NoisySensor(const SensorConfig& cfg) : cfg_(cfg), rng_(cfg.seed) {
    cfg_.validate();
}

std::optional<Measurement> NoisySensor::observe(const TrueState& truth, std::int64_t step) {
    if (step % cfg_.every_n_steps != 0) {
        return std::nullopt;
    }
    const double noise_m = cfg_.sigma_m * unit_normal_(rng_);
    return Measurement{truth.t_s, truth.position_m + noise_m, cfg_.sensor_id};
}

}  // namespace sim
