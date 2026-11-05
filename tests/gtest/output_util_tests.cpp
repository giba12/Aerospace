#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

#include "simulator/output_util.hpp"

using namespace sim;
namespace fs = std::filesystem;

namespace {
struct TempPath {
    fs::path path;
    explicit TempPath(const std::string& name) : path(fs::temp_directory_path() / ("sim_test_" + name)) {
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
}  // namespace

TEST(AtomicFile, AppearsOnlyAtCommitAndCommitIsIdempotent) {
    RecordProperty("requirements", "OUT-004");
    TempPath tp("atomic_commit.txt");
    AtomicFile file(tp.path.string());
    file.stream() << "hello\n";
    EXPECT_FALSE(fs::exists(tp.path));  // nothing is published before commit()
    file.commit();
    EXPECT_EQ(slurp(tp.path), "hello\n");
    file.commit();                      // a second commit must change nothing and must not throw
    EXPECT_EQ(slurp(tp.path), "hello\n");
    EXPECT_FALSE(fs::exists(tp.path.string() + ".tmp"));
}

TEST(AtomicFile, RenamingOntoADirectoryThrowsAndLeavesNoTempFile) {
    RecordProperty("requirements", "OUT-004");
    TempPath tp("atomic_dir");
    fs::create_directory(tp.path);       // the destination is a directory, so the final rename fails
    {
        AtomicFile file(tp.path.string());
        file.stream() << "x";
        EXPECT_THROW(file.commit(), std::runtime_error);
    }
    EXPECT_TRUE(fs::is_directory(tp.path));
    EXPECT_FALSE(fs::exists(tp.path.string() + ".tmp"));
}
