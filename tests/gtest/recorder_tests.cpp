#include <gtest/gtest.h>

#include <cmath>
#include <filesystem>
#include <fstream>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

#include "simulator/recorder.hpp"

using namespace sim;
namespace fs = std::filesystem;

namespace {

// A fresh path in the system temp directory, removed on destruction.
struct TempPath {
    fs::path path;
    explicit TempPath(const std::string& name)
        : path(fs::temp_directory_path() / ("sim_test_" + name)) {
        fs::remove(path);
        fs::remove(path.string() + ".tmp");
    }
    ~TempPath() {
        fs::remove(path);
        fs::remove(path.string() + ".tmp");
    }
};

std::string slurp(const fs::path& p) {
    std::ifstream in(p);
    std::ostringstream os;
    os << in.rdbuf();
    return os.str();
}

const TrueState kTruth{0.5, 5.0, 10.0};

}  // namespace

TEST(CsvRecorder, HeaderIsExact) {
    RecordProperty("requirements", "OUT-001");
    TempPath tp("header.csv");
    {
        CsvRecorder rec(tp.path.string());
        rec.commit();
    }
    EXPECT_EQ(slurp(tp.path), std::string(kCsvHeader) + "\n");
    EXPECT_STREQ(kCsvHeader,
                 "step,t_s,true_pos_m,true_vel_mps,meas_pos_m,est_pos_m,est_vel_mps,"
                 "est_pos_var_m2,est_vel_var_m2s2");
}

TEST(CsvRecorder, NoFileLeftBehindWithoutCommit) {
    RecordProperty("requirements", "OUT-004");
    TempPath tp("nocommit.csv");
    {
        CsvRecorder rec(tp.path.string());
        rec.write_row(0, kTruth, std::nullopt, std::nullopt);
        EXPECT_FALSE(fs::exists(tp.path));  // nothing is published before commit()
    }  // destroyed without commit(), as if the run had failed
    EXPECT_FALSE(fs::exists(tp.path));
    EXPECT_FALSE(fs::exists(tp.path.string() + ".tmp"));
}

TEST(CsvRecorder, MissingValuesAreEmptyAndNumbersRoundTrip) {
    RecordProperty("requirements", "OUT-005,OUT-002");
    TempPath tp("missing.csv");
    const double awkward = 0.1 + 0.2;  // 0.30000000000000004
    {
        CsvRecorder rec(tp.path.string());
        rec.write_row(1, TrueState{awkward, 1.0, 2.0}, std::nullopt, std::nullopt);
        rec.commit();
    }
    std::istringstream lines(slurp(tp.path));
    std::string header, row;
    std::getline(lines, header);
    std::getline(lines, row);
    std::vector<std::string> f;
    std::istringstream fields(row);
    for (std::string cell; std::getline(fields, cell, ',');) {
        f.push_back(cell);
    }
    f.resize(9);  // getline drops a trailing empty field; the header has 9 columns
    EXPECT_EQ(f[0], "1");
    EXPECT_EQ(std::stod(f[1]), awkward);  // 17 digits round-trips exactly
    EXPECT_EQ(f[2], "1");
    EXPECT_EQ(f[3], "2");
    for (int i = 4; i < 9; ++i) {
        EXPECT_EQ(f[i], "") << "column " << i;  // missing means empty, never "nan"
    }
    EXPECT_EQ(row.find("nan"), std::string::npos);
}

TEST(CsvRecorder, RejectsNonFiniteValues) {
    RecordProperty("requirements", "OUT-005");
    TempPath tp("nan.csv");
    CsvRecorder rec(tp.path.string());
    EXPECT_THROW(rec.write_row(0, TrueState{0.0, std::nan(""), 0.0}, std::nullopt, std::nullopt),
                 std::runtime_error);
}
