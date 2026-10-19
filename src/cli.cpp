#include "simulator/cli.hpp"

#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "simulator/config.hpp"
#include "simulator/estimator.hpp"
#include "simulator/recorder.hpp"
#include "simulator/runner.hpp"
#include "simulator/sensor.hpp"

namespace sim {
namespace {

struct UsageError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

double parse_double(const std::string& flag, const std::string& text) {
    errno = 0;
    char* end = nullptr;
    const double value = std::strtod(text.c_str(), &end);
    if (text.empty() || end != text.c_str() + text.size() || errno == ERANGE) {
        throw UsageError(flag + ": not a number: '" + text + "'");
    }
    return value;  // finiteness is checked by validate()
}

std::int64_t parse_int(const std::string& flag, const std::string& text) {
    errno = 0;
    char* end = nullptr;
    const long long value = std::strtoll(text.c_str(), &end, 10);
    if (text.empty() || end != text.c_str() + text.size() || errno == ERANGE) {
        throw UsageError(flag + ": not an integer: '" + text + "'");
    }
    return value;
}

// One row per flag. --help is generated from this table, so the documentation cannot drift
// from the parser (CFG-001, baseline 8.3).
struct FlagSpec {
    const char* name;
    const char* unit;
    const char* default_text;
    std::string help;
    std::function<void(RunConfig&, const std::string& flag, const std::string& value)> apply;
};

const std::vector<FlagSpec>& flags() {
    static const std::vector<FlagSpec> table = {
        {"--steps", "steps", "1000", "number of time steps N (integer, 0 to " + std::to_string(kMaxSteps) + ")",
         [](RunConfig& c, const std::string& f, const std::string& v) {
             c.dynamics.steps = parse_int(f, v);
         }},
        {"--dt", "s", "0.1", "time step (finite, > 0)",
         [](RunConfig& c, const std::string& f, const std::string& v) {
             c.dynamics.dt_s = parse_double(f, v);
         }},
        {"--x0", "m", "0", "initial position (finite)",
         [](RunConfig& c, const std::string& f, const std::string& v) {
             c.dynamics.x0_m = parse_double(f, v);
         }},
        {"--v0", "m/s", "10", "initial velocity (finite)",
         [](RunConfig& c, const std::string& f, const std::string& v) {
             c.dynamics.v0_mps = parse_double(f, v);
         }},
        {"--meas-every", "steps", "5", "sensor reports every M steps (integer >= 1)",
         [](RunConfig& c, const std::string& f, const std::string& v) {
             c.sensor.every_n_steps = parse_int(f, v);
         }},
        {"--accel", "m/s^2", "0", "constant acceleration (finite)",
         [](RunConfig& c, const std::string& f, const std::string& v) {
             c.dynamics.accel_mps2 = parse_double(f, v);
         }},
        {"--sensor-id", "-", "pos0", "sensor name (non-empty, no commas)",
         [](RunConfig& c, const std::string&, const std::string& v) { c.sensor.sensor_id = v; }},
        {"--out", "path", "run.csv", "output CSV path",
         [](RunConfig& c, const std::string&, const std::string& v) { c.out_path = v; }},
    };
    return table;
}

void print_help(std::ostream& out) {
    out << "usage: sim [flags]\n"
           "Educational sensor and state-estimation simulation (not flight software).\n\n"
           "flags:\n";
    for (const FlagSpec& f : flags()) {
        out << "  " << f.name << " <value>  [" << f.unit << "]  default " << f.default_text
            << "  " << f.help << '\n';
    }
    out << "  --help  print this text\n";
}

// Returns false if --help was requested.
bool parse(const std::vector<std::string>& args, RunConfig& cfg) {
    for (std::size_t i = 0; i < args.size(); ++i) {
        std::string name = args[i];
        if (name == "--help") {
            return false;
        }
        std::string value;
        bool has_value = false;
        const std::size_t eq = name.find('=');
        if (eq != std::string::npos) {
            value = name.substr(eq + 1);
            name = name.substr(0, eq);
            has_value = true;
        }
        const FlagSpec* spec = nullptr;
        for (const FlagSpec& f : flags()) {
            if (name == f.name) {
                spec = &f;
            }
        }
        if (spec == nullptr) {
            throw UsageError(name + ": unknown flag (see --help)");
        }
        if (!has_value) {
            if (i + 1 >= args.size()) {
                throw UsageError(name + ": missing value");
            }
            value = args[++i];
        }
        spec->apply(cfg, name, value);
    }
    return true;
}

}  // namespace

int cli_main(const std::vector<std::string>& args, std::ostream& out, std::ostream& err) {
    try {
        RunConfig cfg;
        if (!parse(args, cfg)) {
            print_help(out);
            return kExitOk;
        }
        cfg.dynamics.validate();
        cfg.sensor.validate();

        PassthroughSensor sensor(cfg.sensor);
        PassthroughEstimator estimator;
        CsvRecorder recorder(cfg.out_path);
        run(cfg.dynamics, sensor, estimator, recorder);
        return kExitOk;
    } catch (const UsageError& e) {
        err << "sim: error: " << e.what() << '\n';
        return kExitUsageError;
    } catch (const std::invalid_argument& e) {  // failed validate()
        err << "sim: error: " << e.what() << '\n';
        return kExitUsageError;
    } catch (const std::exception& e) {  // I/O or runtime failure; the recorder cleans up
        err << "sim: error: " << e.what() << '\n';
        return kExitRuntimeError;
    }
}

}  // namespace sim
