#include <gtest/gtest.h>

#include <limits>
#include <string>

#include "simulator/sidecar.hpp"

using namespace sim;

namespace {
bool contains(const std::string& text, const std::string& piece) {
    return text.find(piece) != std::string::npos;
}
}  // namespace

TEST(Sidecar, PathIsTheCsvPathPlusConfigJson) {
    RecordProperty("requirements", "OUT-003");
    EXPECT_EQ(sidecar_path("out/run.csv"), "out/run.csv.config.json");
}

TEST(Sidecar, RecordsEffectiveSettingsAndTheSeed) {
    RecordProperty("requirements", "OUT-003");
    RunConfig cfg;
    cfg.sensor.sigma_m = 2.5;
    cfg.sensor.seed = std::numeric_limits<std::uint64_t>::max();
    const std::string json = sidecar_json(cfg);
    EXPECT_EQ(json.rfind("{\n  \"schema_version\": 1,\n", 0), 0u);
    EXPECT_TRUE(contains(json, "\"sigma_m\": 2.5"));
    EXPECT_TRUE(contains(json, "\"seed\": 18446744073709551615"));  // full 64 bits, as an integer
    EXPECT_TRUE(contains(json, "\"steps\": 1000"));
    EXPECT_TRUE(contains(json, "\"est_r_m2\": 25"));  // the filter's assumed variance, recorded as a number
    EXPECT_EQ(json.substr(json.size() - 2), "}\n");
}

TEST(Sidecar, EscapesQuotesBackslashesAndControlCharacters) {
    RecordProperty("requirements", "OUT-003");
    RunConfig cfg;
    cfg.sensor.sensor_id = "a\"b\\c\nd";
    EXPECT_TRUE(contains(sidecar_json(cfg), "\"sensor_id\": \"a\\\"b\\\\c\\u000ad\""));
}
