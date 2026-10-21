#include "simulator/recorder.hpp"

namespace sim {

const char* const kCsvHeader =
    "step,t_s,true_pos_m,true_vel_mps,meas_pos_m,est_pos_m,est_vel_mps,"
    "est_pos_var_m2,est_vel_var_m2s2";

CsvRecorder::CsvRecorder(const std::string& path) : file_(path) {
    file_.stream() << kCsvHeader << '\n';
}

void CsvRecorder::write_row(std::int64_t step, const TrueState& truth,
                            const std::optional<Measurement>& meas,
                            const std::optional<Estimate>& est) {
    std::string row = std::to_string(step) + ',' + format_double(truth.t_s, "t_s") + ',' +
                      format_double(truth.position_m, "true_pos_m") + ',' +
                      format_double(truth.velocity_mps, "true_vel_mps");
    // A missing value is an empty field (OUT-005).
    row += ',' + (meas ? format_double(meas->position_m, "meas_pos_m") : std::string());
    if (est) {
        row += ',' + format_double(est->position_m, "est_pos_m") + ',' +
               format_double(est->velocity_mps, "est_vel_mps") + ',' +
               format_double(est->P.m00, "est_pos_var_m2") + ',' +
               format_double(est->P.m11, "est_vel_var_m2s2");
    } else {
        row += ",,,,";
    }
    file_.stream() << row << '\n';
}

void CsvRecorder::commit() {
    file_.commit();
}

}  // namespace sim
