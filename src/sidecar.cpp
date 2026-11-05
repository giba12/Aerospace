#include "simulator/sidecar.hpp"

#include <cstdio>
#include <string>
#include <utility>
#include <vector>

#include "simulator/output_util.hpp"

namespace sim {
namespace {

// A JSON string literal: quotes, backslashes and control characters are escaped.
std::string json_string(const std::string& text) {
    std::string out = "\"";
    for (const char c : text) {
        if (c == '"' || c == '\\') {
            out += '\\';
            out += c;
        } else if (static_cast<unsigned char>(c) < 0x20) {
            char buf[8];
            std::snprintf(buf, sizeof buf, "\\u%04x", static_cast<unsigned>(c));
            out += buf;
        } else {
            out += c;
        }
    }
    return out + '"';
}

std::string compiler_id() {
#if defined(__clang__)
    return std::string("clang ") + __clang_version__;
#elif defined(__GNUC__)
    return std::string("gcc ") + __VERSION__;
#else
    return "unknown";
#endif
}

}  // namespace

std::string sidecar_path(const std::string& out_path) {
    return out_path + ".config.json";
}

std::string sidecar_json(const RunConfig& cfg) {
    const DynamicsConfig& d = cfg.dynamics;
    const SensorConfig& s = cfg.sensor;
    const EstimatorConfig& e = cfg.estimator;
#ifdef SIM_SOURCE_REVISION
    const std::string revision = json_string(SIM_SOURCE_REVISION);
#else
    const std::string revision = "null";
#endif
    const std::vector<std::pair<const char*, std::string>> fields = {
        {"schema_version", "1"},
        {"steps", std::to_string(d.steps)},
        {"dt_s", format_double(d.dt_s, "dt_s")},
        {"x0_m", format_double(d.x0_m, "x0_m")},
        {"v0_mps", format_double(d.v0_mps, "v0_mps")},
        {"accel_mps2", format_double(d.accel_mps2, "accel_mps2")},
        {"meas_every", std::to_string(s.every_n_steps)},
        {"sigma_m", format_double(s.sigma_m, "sigma_m")},
        {"seed", std::to_string(s.seed)},
        {"sensor_id", json_string(s.sensor_id)},
        {"est_q_m2ps3", format_double(e.q_m2ps3, "est_q_m2ps3")},
        {"est_r_m2", format_double(e.r_m2, "est_r_m2")},
        {"est_p0_pos_m2", format_double(e.p0_pos_m2, "est_p0_pos_m2")},
        {"est_p0_vel_m2ps2", format_double(e.p0_vel_m2ps2, "est_p0_vel_m2ps2")},
        {"compiler", json_string(compiler_id())},
        {"source_revision", revision},
    };
    std::string out = "{\n";
    for (std::size_t i = 0; i < fields.size(); ++i) {
        out += std::string("  \"") + fields[i].first + "\": " + fields[i].second;
        out += (i + 1 < fields.size()) ? ",\n" : "\n";
    }
    return out + "}\n";
}

}  // namespace sim
