#include "simulator/sensor.hpp"

#include <stdexcept>

namespace sim {

void SensorConfig::validate() const {
    if (every_n_steps < 1) {
        throw std::invalid_argument("every_n_steps: must be >= 1");
    }
    if (sensor_id.empty() || sensor_id.find(',') != std::string::npos) {
        throw std::invalid_argument("sensor_id: must be non-empty and contain no commas");
    }
}

PassthroughSensor::PassthroughSensor(const SensorConfig& cfg) : cfg_(cfg) {
    cfg_.validate();
}

std::optional<Measurement> PassthroughSensor::observe(const TrueState& truth, std::int64_t step) {
    if (step % cfg_.every_n_steps != 0) {
        return std::nullopt;
    }
    return Measurement{truth.t_s, truth.position_m, cfg_.sensor_id};
}

}  // namespace sim
