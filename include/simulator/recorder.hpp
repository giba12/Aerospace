#pragma once

#include <cstdint>
#include <optional>
#include <string>

#include "simulator/output_util.hpp"
#include "simulator/state.hpp"

namespace sim {

// IF-06.
class IRecorder {
public:
    virtual ~IRecorder() = default;
    virtual void write_row(std::int64_t step, const TrueState& truth,
                           const std::optional<Measurement>& meas,
                           const std::optional<Estimate>& est) = 0;
    virtual void commit() = 0;  // OUT-004: publish the file atomically
};

// The exact CSV header, IF-07 schema_version 1 (OUT-001).
extern const char* const kCsvHeader;

// Writes rows through an AtomicFile, so nothing appears at `<path>` until commit() and a failed
// run leaves no partial CSV (OUT-004).
class CsvRecorder final : public IRecorder {
public:
    explicit CsvRecorder(const std::string& path);  // throws std::runtime_error if unwritable

    void write_row(std::int64_t step, const TrueState& truth,
                   const std::optional<Measurement>& meas,
                   const std::optional<Estimate>& est) override;
    void commit() override;

private:
    AtomicFile file_;
};

}  // namespace sim
