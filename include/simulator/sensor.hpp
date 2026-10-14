#pragma once

#include <cstdint>
#include <optional>

#include "simulator/config.hpp"
#include "simulator/state.hpp"

namespace sim {

// IF-04. The sensor owns the sampling schedule (DD-002), and truth is const (SEN-006).
class ISensor {
public:
    virtual ~ISensor() = default;
    virtual std::optional<Measurement> observe(const TrueState& truth, std::int64_t step) = 0;
};

// M0 stand-in: reports the true position exactly, every `every_n_steps` steps, starting at
// step 0 (SEN-002). Replaced by a seeded noisy sensor in M2.
class PassthroughSensor final : public ISensor {
public:
    explicit PassthroughSensor(const SensorConfig& cfg);
    std::optional<Measurement> observe(const TrueState& truth, std::int64_t step) override;

private:
    SensorConfig cfg_;
};

}  // namespace sim
