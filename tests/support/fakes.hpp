#pragma once

// Framework-neutral test support (TST-006): no gtest/catch2 headers in this directory.
// The fakes record what the runner does to them, so tests can check the call ORDER.

#include <cstdint>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include "simulator/estimator.hpp"
#include "simulator/recorder.hpp"
#include "simulator/sensor.hpp"

namespace sim::testing {

// Shared, ordered log of "what happened" across all fakes in one run.
using CallLog = std::vector<std::string>;

// Reports on exactly the steps listed, with position = truth + 0.5 so a test can tell a
// measurement from the truth.
class ScriptedSensor final : public ISensor {
public:
    ScriptedSensor(CallLog& log, std::set<std::int64_t> steps_with_reading)
        : log_(log), steps_(std::move(steps_with_reading)) {}

    std::optional<Measurement> observe(const TrueState& truth, std::int64_t step) override {
        log_.push_back("observe(" + std::to_string(step) + ")");
        if (steps_.count(step) == 0) {
            return std::nullopt;
        }
        return Measurement{truth.t_s, truth.position_m + 0.5, "fake"};
    }

private:
    CallLog& log_;
    std::set<std::int64_t> steps_;
};

class RecordingEstimator final : public IEstimator {
public:
    explicit RecordingEstimator(CallLog& log) : log_(log) {}

    bool initialized() const override { return initialized_; }
    Estimate initialize(const Measurement& first) override {
        log_.push_back("initialize");
        initialized_ = true;
        return Estimate{first.t_s, first.position_m, 0.0, Mat2{}};
    }
    Estimate predict(double) override {
        log_.push_back("predict");
        return Estimate{};
    }
    Estimate update(const Measurement& z) override {
        log_.push_back("update");
        return Estimate{z.t_s, z.position_m, 0.0, Mat2{}};
    }

private:
    CallLog& log_;
    bool initialized_{false};
};

class RecordingRecorder final : public IRecorder {
public:
    explicit RecordingRecorder(CallLog& log) : log_(log) {}

    void write_row(std::int64_t step, const TrueState&, const std::optional<Measurement>& meas,
                   const std::optional<Estimate>& est) override {
        log_.push_back("write_row(" + std::to_string(step) + ")");
        ++rows;
        if (est) {
            ++rows_with_estimate;
        }
        if (meas) {
            ++rows_with_measurement;
        }
    }
    void commit() override { log_.push_back("commit"); }

    int rows{0};
    int rows_with_estimate{0};
    int rows_with_measurement{0};

private:
    CallLog& log_;
};

}  // namespace sim::testing
