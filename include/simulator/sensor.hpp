#pragma once

#include <cstdint>
#include <optional>
#include <random>

#include "simulator/config.hpp"
#include "simulator/state.hpp"

namespace sim {

// IF-04. The sensor owns the sampling schedule (DD-002), and truth is const (SEN-006).
class ISensor {
public:
    virtual ~ISensor() = default;
    virtual std::optional<Measurement> observe(const TrueState& truth, std::int64_t step) = 0;
};

// Reports true position + sigma * z, where z is a standard-normal draw from an RNG seeded by
// cfg.seed (DD-005), every `every_n_steps` steps starting at step 0 (SEN-002). The draw is
// scaled by sigma rather than made from N(0, sigma^2), so sigma = 0 gives the exact position
// (SEN-003) and the same seed with a different sigma gives the same noise pattern, scaled.
// A draw is made only on steps that produce a reading. `std::normal_distribution` is
// implementation-defined, so identical output is promised for the same platform and build only.
class NoisySensor final : public ISensor {
public:
    explicit NoisySensor(const SensorConfig& cfg);  // throws std::invalid_argument (SEN-007)
    std::optional<Measurement> observe(const TrueState& truth, std::int64_t step) override;

private:
    SensorConfig cfg_;
    std::mt19937_64 rng_;
    std::normal_distribution<double> unit_normal_{0.0, 1.0};
};

}  // namespace sim
