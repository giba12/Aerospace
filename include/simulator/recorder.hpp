#pragma once

#include <cstdint>
#include <fstream>
#include <optional>
#include <string>

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

// Writes rows to `<path>.tmp` and renames it onto `<path>` only in commit(). If the object is
// destroyed without commit() (for example because an exception unwound the run), the temp
// file is deleted, so a failed run leaves no partial CSV (OUT-004, RAII).
class CsvRecorder final : public IRecorder {
public:
    explicit CsvRecorder(const std::string& path);  // throws std::runtime_error if unwritable
    ~CsvRecorder() override;
    CsvRecorder(const CsvRecorder&) = delete;
    CsvRecorder& operator=(const CsvRecorder&) = delete;

    void write_row(std::int64_t step, const TrueState& truth,
                   const std::optional<Measurement>& meas,
                   const std::optional<Estimate>& est) override;
    void commit() override;

private:
    std::string path_;
    std::string tmp_path_;
    std::ofstream out_;
    bool committed_{false};
};

}  // namespace sim
