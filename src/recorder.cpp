#include "simulator/recorder.hpp"

#include <cmath>
#include <filesystem>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <system_error>

namespace sim {

const char* const kCsvHeader =
    "step,t_s,true_pos_m,true_vel_mps,meas_pos_m,est_pos_m,est_vel_mps,"
    "est_pos_var_m2,est_vel_var_m2s2";

namespace {

// 17 significant digits round-trips any double exactly (OUT-002). The classic locale pins
// the decimal separator to '.'.
std::string number(double value, const char* column) {
    if (!std::isfinite(value)) {
        // OUT-005: "nan" and "inf" must never reach the file.
        throw std::runtime_error(std::string("non-finite value in column ") + column);
    }
    std::ostringstream os;
    os.imbue(std::locale::classic());
    os.precision(17);
    os << value;
    return os.str();
}

}  // namespace

CsvRecorder::CsvRecorder(const std::string& path)
    : path_(path), tmp_path_(path + ".tmp"), out_(tmp_path_, std::ios::trunc) {
    if (!out_) {
        throw std::runtime_error(path_ + ": cannot open for writing");
    }
    out_ << kCsvHeader << '\n';
}

CsvRecorder::~CsvRecorder() {
    if (!committed_) {
        out_.close();
        std::error_code ignored;
        std::filesystem::remove(tmp_path_, ignored);
    }
}

void CsvRecorder::write_row(std::int64_t step, const TrueState& truth,
                            const std::optional<Measurement>& meas,
                            const std::optional<Estimate>& est) {
    std::string row = std::to_string(step) + ',' + number(truth.t_s, "t_s") + ',' +
                      number(truth.position_m, "true_pos_m") + ',' +
                      number(truth.velocity_mps, "true_vel_mps");
    // A missing value is an empty field (OUT-005).
    row += ',' + (meas ? number(meas->position_m, "meas_pos_m") : std::string());
    if (est) {
        row += ',' + number(est->position_m, "est_pos_m") + ',' +
               number(est->velocity_mps, "est_vel_mps") + ',' +
               number(est->P.m00, "est_pos_var_m2") + ',' +
               number(est->P.m11, "est_vel_var_m2s2");
    } else {
        row += ",,,,";
    }
    out_ << row << '\n';
}

void CsvRecorder::commit() {
    if (committed_) {
        return;
    }
    out_.flush();
    const bool ok = static_cast<bool>(out_);
    out_.close();
    if (!ok) {
        throw std::runtime_error(path_ + ": write failed");
    }
    std::error_code ec;
    std::filesystem::rename(tmp_path_, path_, ec);  // atomic on POSIX
    if (ec) {
        throw std::runtime_error(path_ + ": " + ec.message());
    }
    committed_ = true;
}

}  // namespace sim
